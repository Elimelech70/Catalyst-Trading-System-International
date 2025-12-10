# IBKR IBeam Implementation Plan for Catalyst Trading System

---

## ⚠️ DEPRECATED - SUPERSEDED BY IBGA

**Status:** DEPRECATED as of 2025-12-10
**Replaced By:** IBGA (heshiming/ibga) with ib_async socket API
**See Instead:** `ibga/SETUP-STATUS.md` and `Documentation/Design/architecture-international-agent-v3.md`

**Why Deprecated:**
- IBeam Web API approach had authentication issues
- IBGA with socket API (ib_async) is more reliable
- Paper trading now fully operational with IBGA

---

## Overview (HISTORICAL)

This plan integrates Interactive Brokers Web API into the Catalyst Trading System using IBeam, a Docker container that automates Client Portal Gateway authentication. This enables automated trading via REST API endpoints.

## Prerequisites

- IBKR Pro account (funded)
- IBKR Mobile app installed with "IB Key" enabled for 2FA
- Paper trading account credentials (for testing)
- Existing Catalyst Docker infrastructure on DigitalOcean

---

## Phase 1: IBKR Account Configuration

### Step 1.1: Enable Paper Trading Account

1. Log into IBKR Client Portal: https://portal.interactivebrokers.com
2. Click the profile icon → Settings
3. Under "Account Configuration" select "Paper Trading Account"
4. Note your Paper Trading Username and Account Number
5. Click "Reset Paper Trading Password" to set a known password

### Step 1.2: Enable IB Key (2FA)

1. Open IBKR Mobile app on your phone
2. Go to Settings → Security → IB Key
3. Enable IB Key authentication
4. This allows IBeam to handle 2FA automatically

### Step 1.3: Configure API Settings

1. In Client Portal → Settings → API Settings
2. Ensure "Enable ActiveX and Socket Clients" is checked
3. Note: Web API doesn't require socket ports, but good to have enabled

---

## Phase 2: IBeam Container Setup

### Step 2.1: Create IBeam Configuration Directory

```bash
# On your DigitalOcean droplet
mkdir -p /opt/catalyst/ibeam
cd /opt/catalyst/ibeam
```

### Step 2.2: Create Environment File

Create `/opt/catalyst/ibeam/.env`:

```env
# IBKR Credentials (use paper trading first)
IBEAM_ACCOUNT=your_paper_username
IBEAM_PASSWORD=your_paper_password

# Gateway Configuration
IBEAM_GATEWAY_BASE_URL=https://localhost:5000
IBEAM_LOG_LEVEL=INFO

# Authentication Settings
IBEAM_REQUEST_RETRIES=10
IBEAM_REQUEST_TIMEOUT=15
IBEAM_PAGE_LOAD_TIMEOUT=60

# 2FA - Using IB Key (no manual intervention needed)
IBEAM_TWO_FA_HANDLER=IB_KEY
```

### Step 2.3: Create Docker Compose Service

Add to your existing `docker-compose.yml` or create `/opt/catalyst/ibeam/docker-compose.yml`:

```yaml
version: '3.8'

services:
  ibeam:
    image: voyzdev/ibeam:latest
    container_name: catalyst-ibeam
    env_file:
      - .env
    ports:
      - "5000:5000"
    volumes:
      # Persist gateway files across restarts
      - ibeam_data:/srv/clientportal.gw
      # Optional: custom config
      - ./conf.yaml:/srv/conf.yaml:ro
    healthcheck:
      test: ["CMD", "curl", "-k", "-f", "https://localhost:5000/v1/api/iserver/auth/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    restart: unless-stopped
    networks:
      - catalyst-network

volumes:
  ibeam_data:

networks:
  catalyst-network:
    external: true
```

### Step 2.4: Optional - Custom Gateway Configuration

Create `/opt/catalyst/ibeam/conf.yaml` for advanced settings:

```yaml
# IB Gateway Configuration
listenPort: 5000
listenSsl: true
svcEnvironment: v1
svcTimeout: 60000
authDelay: 3000
```

---

## Phase 3: IBKR Service Integration

### Step 3.1: Create IBKR Client Module

Create a new service or add to existing execution service. Example Python client:

```python
# /opt/catalyst/services/ibkr_client/ibkr_client.py

import os
import time
import requests
from typing import Optional, Dict, Any
import urllib3

# Disable SSL warnings for self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IBKRClient:
    """IBKR Web API client via IBeam gateway."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("IBEAM_URL", "https://catalyst-ibeam:5000")
        self.session = requests.Session()
        self.session.verify = False  # IBeam uses self-signed cert
        self.account_id: Optional[str] = None
    
    def check_auth_status(self) -> Dict[str, Any]:
        """Check if gateway is authenticated."""
        response = self.session.get(f"{self.base_url}/v1/api/iserver/auth/status")
        return response.json()
    
    def tickle(self) -> Dict[str, Any]:
        """Keep session alive - call every 5 minutes."""
        response = self.session.post(f"{self.base_url}/v1/api/tickle")
        return response.json()
    
    def get_accounts(self) -> Dict[str, Any]:
        """Get list of accounts."""
        response = self.session.get(f"{self.base_url}/v1/api/portfolio/accounts")
        data = response.json()
        if data and len(data) > 0:
            self.account_id = data[0].get("accountId")
        return data
    
    def search_contract(self, symbol: str, sec_type: str = "STK") -> Dict[str, Any]:
        """Search for contract by symbol."""
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/secdef/search",
            params={"symbol": symbol, "secType": sec_type}
        )
        return response.json()
    
    def get_contract_details(self, conid: int) -> Dict[str, Any]:
        """Get contract details by conid."""
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/contract/{conid}/info"
        )
        return response.json()
    
    def get_market_data(self, conids: list, fields: list = None) -> Dict[str, Any]:
        """Get market data snapshot."""
        if fields is None:
            fields = ["31", "84", "86"]  # Last, Bid, Ask
        
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/marketdata/snapshot",
            params={
                "conids": ",".join(map(str, conids)),
                "fields": ",".join(fields)
            }
        )
        return response.json()
    
    def place_order(
        self,
        conid: int,
        side: str,
        quantity: float,
        order_type: str = "MKT",
        price: float = None,
        tif: str = "DAY"
    ) -> Dict[str, Any]:
        """Place an order."""
        if not self.account_id:
            self.get_accounts()
        
        order = {
            "conid": conid,
            "side": side.upper(),  # BUY or SELL
            "quantity": quantity,
            "orderType": order_type,  # MKT, LMT, STP, etc.
            "tif": tif,  # DAY, GTC, IOC, etc.
        }
        
        if price and order_type in ["LMT", "STP"]:
            order["price"] = price
        
        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/orders",
            json={"orders": [order]}
        )
        return response.json()
    
    def confirm_order(self, reply_id: str, confirmed: bool = True) -> Dict[str, Any]:
        """Confirm order after placement (handles order warnings)."""
        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/reply/{reply_id}",
            json={"confirmed": confirmed}
        )
        return response.json()
    
    def get_orders(self) -> Dict[str, Any]:
        """Get live orders."""
        response = self.session.get(f"{self.base_url}/v1/api/iserver/account/orders")
        return response.json()
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        if not self.account_id:
            self.get_accounts()
        
        response = self.session.delete(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/order/{order_id}"
        )
        return response.json()
    
    def get_positions(self) -> Dict[str, Any]:
        """Get current positions."""
        if not self.account_id:
            self.get_accounts()
        
        response = self.session.get(
            f"{self.base_url}/v1/api/portfolio/{self.account_id}/positions/0"
        )
        return response.json()
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary."""
        if not self.account_id:
            self.get_accounts()
        
        response = self.session.get(
            f"{self.base_url}/v1/api/portfolio/{self.account_id}/summary"
        )
        return response.json()


class IBKRSessionManager:
    """Manages IBKR session keepalive."""
    
    def __init__(self, client: IBKRClient, tickle_interval: int = 240):
        self.client = client
        self.tickle_interval = tickle_interval  # seconds (< 5 min)
        self.running = False
    
    def start(self):
        """Start session keepalive loop."""
        import threading
        self.running = True
        self.thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop session keepalive."""
        self.running = False
    
    def _keepalive_loop(self):
        """Background keepalive loop."""
        while self.running:
            try:
                status = self.client.check_auth_status()
                if status.get("authenticated"):
                    self.client.tickle()
                else:
                    print("Warning: IBKR session not authenticated")
            except Exception as e:
                print(f"Keepalive error: {e}")
            
            time.sleep(self.tickle_interval)
```

### Step 3.2: Create Requirements File

Create `/opt/catalyst/services/ibkr_client/requirements.txt`:

```
requests>=2.28.0
urllib3>=1.26.0
```

### Step 3.3: Add IBKR Client Service to Docker Compose

```yaml
  ibkr-client:
    build:
      context: ./services/ibkr_client
      dockerfile: Dockerfile
    container_name: catalyst-ibkr-client
    environment:
      - IBEAM_URL=https://catalyst-ibeam:5000
    depends_on:
      ibeam:
        condition: service_healthy
    networks:
      - catalyst-network
```

---

## Phase 4: Health Monitoring & Reconnection

### Step 4.1: Create Health Check Script

Create `/opt/catalyst/scripts/ibkr_health_check.sh`:

```bash
#!/bin/bash

IBEAM_URL="https://localhost:5000"

# Check authentication status
STATUS=$(curl -sk "${IBEAM_URL}/v1/api/iserver/auth/status" | jq -r '.authenticated')

if [ "$STATUS" != "true" ]; then
    echo "$(date): IBKR not authenticated, restarting IBeam..."
    docker restart catalyst-ibeam
    
    # Wait for restart
    sleep 120
    
    # Check again
    STATUS=$(curl -sk "${IBEAM_URL}/v1/api/iserver/auth/status" | jq -r '.authenticated')
    if [ "$STATUS" != "true" ]; then
        echo "$(date): IBKR still not authenticated after restart!"
        # Send alert (integrate with your alerting system)
    fi
else
    echo "$(date): IBKR authenticated OK"
fi
```

### Step 4.2: Add Cron Job for Health Check

```bash
# Add to crontab
crontab -e

# Add line (check every 15 minutes):
*/15 * * * * /opt/catalyst/scripts/ibkr_health_check.sh >> /var/log/ibkr_health.log 2>&1
```

---

## Phase 5: Testing Procedure

### Step 5.1: Deploy IBeam Container

```bash
cd /opt/catalyst/ibeam
docker-compose up -d ibeam

# Watch logs for authentication
docker logs -f catalyst-ibeam
```

### Step 5.2: Verify Authentication

Wait for "Client login succeeds" in logs, then:

```bash
# Check auth status
curl -sk https://localhost:5000/v1/api/iserver/auth/status | jq

# Expected response:
# {"authenticated": true, "connected": true, ...}
```

### Step 5.3: Test API Endpoints

```bash
# Get accounts
curl -sk https://localhost:5000/v1/api/portfolio/accounts | jq

# Search for a symbol (e.g., AAPL)
curl -sk "https://localhost:5000/v1/api/iserver/secdef/search?symbol=AAPL&secType=STK" | jq

# Get market data (need conid from search)
curl -sk "https://localhost:5000/v1/api/iserver/marketdata/snapshot?conids=265598&fields=31,84,86" | jq
```

### Step 5.4: Test Paper Trade

```python
# test_paper_trade.py
from ibkr_client import IBKRClient

client = IBKRClient("https://localhost:5000")

# Check auth
print(client.check_auth_status())

# Get accounts
accounts = client.get_accounts()
print(f"Account: {client.account_id}")

# Search AAPL
results = client.search_contract("AAPL")
conid = results[0]["conid"]
print(f"AAPL conid: {conid}")

# Place paper market order for 1 share
order_result = client.place_order(
    conid=conid,
    side="BUY",
    quantity=1,
    order_type="MKT"
)
print(f"Order result: {order_result}")

# Handle confirmation if needed
if "id" in order_result[0]:
    confirm = client.confirm_order(order_result[0]["id"])
    print(f"Confirmation: {confirm}")
```

---

## Phase 6: Production Deployment

### Step 6.1: Switch to Live Account

Update `/opt/catalyst/ibeam/.env`:

```env
# Change to live credentials
IBEAM_ACCOUNT=your_live_username
IBEAM_PASSWORD=your_live_password
```

### Step 6.2: Restart Services

```bash
docker-compose down
docker-compose up -d
```

### Step 6.3: Verify Live Connection

```bash
# Confirm account type in response
curl -sk https://localhost:5000/v1/api/portfolio/accounts | jq
```

---

## API Rate Limits

- Global limit: 10 requests per second via CP Gateway
- Exceeding limit returns 429 status
- Violators put in penalty box for 15 minutes

Implement rate limiting in your client code.

---

## Session Management Notes

- Sessions reset daily at midnight (NY/Zug/HK based on region)
- Call `/tickle` endpoint every 5 minutes to keep alive
- IBeam handles re-authentication automatically with IB Key
- Monitor logs for authentication failures

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Session expired - IBeam should auto-reauthenticate |
| 429 Too Many Requests | Rate limited - implement backoff |
| Gateway not responding | Check Docker logs, restart container |
| 2FA timeout | Ensure IB Key is enabled on mobile app |
| Connection refused | IBeam still starting - wait 2 minutes |

---

## Integration Points for Catalyst

Connect this IBKR client to your existing Catalyst services:

1. **Signal Service** → Receives trading signals
2. **IBKR Client** → Executes trades via IBeam
3. **Position Manager** → Tracks positions via API
4. **Risk Manager** → Monitors account summary

The IBKR client should be called by your execution service when signals are generated.
