# Catalyst Trading System International - Agent Architecture

**Name of Application:** Catalyst Trading System International
**Name of File:** architecture-international.md
**Version:** 4.0.0
**Last Updated:** 2025-12-10
**Target Exchange:** Hong Kong Stock Exchange (HKEX) + US Markets
**Broker:** Interactive Brokers (IBKR) via ib_async Socket API
**Architecture:** AI Agent Pattern (Simple Droplet + Claude API + IBGA)

---

## REVISION HISTORY

**v4.0.0 (2025-12-10)** - IBGA Socket API Integration
- Replaced IBeam Web API with IBGA (heshiming/ibga) Docker container
- Uses ib_async socket API for broker communication
- Custom Dockerfile with Zulu JDK 17.0.10 + JavaFX
- IB Key 2FA support with headless operation
- Multi-exchange support (HKEX + US stocks)
- Paper trading tested and verified

**v3.0.0 (2025-12-09)** - IBeam Web API Integration (Deprecated)
- REST-based broker communication via IBeam
- Automatic session management

**v2.0.0 (2025-12-03)** - Simplified Architecture
- Single $6 DigitalOcean droplet
- Direct Claude API calls

**v1.0.0 (2025-12-03)** - Initial Agent Architecture

---

## 1. Architecture Overview

### 1.1 Current Production Setup

Minimal infrastructure with socket-based broker access:

- **1 small droplet** ($6/month)
- **1 Python script** (the agent)
- **1 Docker container** (IBGA for headless IB Gateway)
- **Cron** (the trigger)
- **Claude API** (the brain)
- **IBKR Socket API** (the broker via ib_async)
- **PostgreSQL** (shared with US)

```
┌─────────────────────────────────────────────────────────────────────┐
│                DIGITALOCEAN DROPLET ($6/month)                       │
│                                                                      │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────────┐        │
│   │   CRON   │────▶│    AGENT     │────▶│      TOOLS       │        │
│   │          │     │   (Python)   │     │    (Functions)   │        │
│   │ 9:30 AM  │     │              │     │                  │        │
│   │ 10:30 AM │     │ Calls Claude │     │ - scan_market()  │        │
│   │ ...      │     │ Executes     │     │ - get_news()     │        │
│   │ 3:30 PM  │     │ Tools        │     │ - execute_trade()│        │
│   └──────────┘     └──────────────┘     │ - check_risk()   │        │
│                           │             └────────┬─────────┘        │
│                           │                      │                  │
│                           ▼                      ▼                  │
│                    ┌─────────────┐       ┌─────────────┐            │
│                    │ Claude API  │       │    IBGA     │            │
│                    │ (Anthropic) │       │  (Docker)   │            │
│                    └─────────────┘       └──────┬──────┘            │
│                                                 │                   │
│                                                 ▼                   │
│                                          ┌─────────────┐            │
│                                          │ IB Gateway  │            │
│                                          │ (Port 4000) │            │
│                                          └─────────────┘            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │ (DO Managed DB) │
                    │ Shared with US  │
                    └─────────────────┘
```

### 1.2 Why IBGA + Socket API?

| Aspect | IBeam Web API | IBGA Socket API |
|--------|---------------|-----------------|
| **Library** | requests (REST) | ib_async (socket) |
| **Connection** | REST/HTTPS | TCP socket |
| **Authentication** | IBeam handles | IBGA handles |
| **Reliability** | Moderate | High (native IB protocol) |
| **Market Data** | REST polling | Streaming |
| **Order Status** | Polling | Real-time callbacks |
| **Complexity** | Higher | Lower |

### 1.3 The Agent Loop

```
CRON triggers at market hour
        │
        ▼
┌───────────────────┐
│ 1. Build Context  │  ← Portfolio, market data, news
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. Call Claude    │  ← Send context + tools
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. Claude Returns │  ← "Call execute_trade()"
│    Tool Request   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. Execute Tool   │  ← IBKRClient calls ib_async
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 5. Return Result  │  ← Tool result to Claude
│    to Claude      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 6. Loop Until     │  ← Claude may call more tools
│    Claude Done    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 7. Log & Exit     │  ← Wait for next cron
└───────────────────┘
```

---

## 2. File Structure

```
catalyst-international/
│
├── agent.py                    # Main agent script (runs via cron)
├── tools.py                    # Tool definitions for Claude
├── tool_executor.py            # Executes tool requests
├── safety.py                   # Validates all actions
│
├── brokers/
│   ├── __init__.py
│   └── ibkr.py                 # IBKR client via ib_async (v2.1.0)
│
├── data/
│   ├── __init__.py
│   ├── market.py               # Market data fetching
│   ├── news.py                 # News/sentiment
│   └── database.py             # PostgreSQL client
│
├── config/
│   ├── settings.yaml           # All configuration
│   └── prompts/
│       └── system.md           # Claude's instructions
│
├── ibga/
│   ├── Dockerfile              # Custom image with Java 17 + JavaFX
│   ├── docker-compose.yml      # IBGA container config
│   ├── .env                    # IBKR credentials
│   ├── run/                    # Persisted gateway data
│   └── SETUP-STATUS.md         # Current setup status
│
├── scripts/
│   ├── test_ibga_connection.py # Connection test
│   └── health_check.sh         # Health monitoring
│
├── logs/                       # Daily log files
│
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 3. IBGA Configuration

### 3.1 Custom Dockerfile

```dockerfile
# ibga/Dockerfile
# Custom IBGA image with exact Zulu JDK 17.0.10 + JavaFX required by IBGateway 10.41
FROM heshiming/ibga

USER root

# Install curl and ca-certificates for downloading
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Download and install Zulu JDK 17.0.10 WITH JavaFX (needed for GUI)
# Install to /opt/java which won't be overwritten by volume mounts
RUN mkdir -p /opt/java && \
    cd /tmp && \
    curl -L -o zulu17fx.tar.gz "https://cdn.azul.com/zulu/bin/zulu17.48.15-ca-fx-jdk17.0.10-linux_x64.tar.gz" && \
    tar -xzf zulu17fx.tar.gz && \
    mv zulu17.48.15-ca-fx-jdk17.0.10-linux_x64 /opt/java/zulu17.0.10-fx && \
    rm -rf /tmp/zulu17* && \
    chmod -R 755 /opt/java

# Set INSTALL4J_JAVA_HOME_OVERRIDE to bypass IBGateway's strict version checking
ENV INSTALL4J_JAVA_HOME_OVERRIDE=/opt/java/zulu17.0.10-fx

USER ibg
```

### 3.2 Docker Compose

```yaml
# ibga/docker-compose.yml
services:
  ibga:
    build: .
    image: catalyst-ibga-java17
    container_name: catalyst-ibga
    restart: unless-stopped
    environment:
      - TERM=xterm
      - INSTALL4J_JAVA_HOME_OVERRIDE=/opt/java/zulu17.0.10-fx
      - IB_USERNAME=${IB_USERNAME}
      - IB_PASSWORD=${IB_PASSWORD}
      - IB_REGION=Asia
      - IB_TIMEZONE=Asia/Hong_Kong
      - IB_LOGINTAB=IB API
      - IB_LOGINTYPE=${IB_LOGINTYPE:-Paper Trading}
      - IB_LOGOFF=5:00 PM
      - IB_PREFER_IBKEY=true
    volumes:
      - ./run/program:/home/ibg
      - ./run/settings:/home/ibg_settings
    ports:
      - "5800:5800"    # VNC for debugging
      - "4000:4000"    # IB Gateway API
    healthcheck:
      test: ["CMD-SHELL", "nc -z localhost 4000 || exit 1"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 180s
```

### 3.3 Gateway Settings (Configured via VNC)

| Setting | Value |
|---------|-------|
| API Socket Port | 9000 (internal) |
| External Port | 4000 (via socat) |
| Trusted IPs | 127.0.0.1, 172.19.0.1 |
| Read-Only API | Disabled |
| Auto Logoff | 5:00 PM HKT |
| Auto Restart | Enabled |

---

## 4. IBKRClient Implementation

### 4.1 brokers/ibkr.py (v2.1.0)

Key features:
- Multi-exchange support (HKEX + US)
- Auto-detect exchange based on symbol format
- HKEX tick size rounding
- Bracket orders with stop loss/take profit
- Position and order management

```python
# Key methods in IBKRClient:

def _create_contract(self, symbol: str, exchange: str = None) -> Contract:
    """Auto-detect exchange: numeric = HKEX, alphabetic = US"""

def execute_trade(self, symbol, side, quantity, order_type, limit_price,
                  stop_loss, take_profit, reason) -> dict:
    """Execute trade with optional bracket orders"""

def get_portfolio(self) -> dict:
    """Get cash, equity, positions, P&L"""

def get_positions(self) -> list[dict]:
    """Get all open positions"""

def close_position(self, symbol, reason) -> dict:
    """Close a specific position"""

def close_all_positions(self, reason) -> list[dict]:
    """Emergency: close all positions"""
```

### 4.2 Exchange Auto-Detection

```python
# Numeric symbols (0700, 9988) → HKEX (SEHK)
# Alphabetic symbols (AAPL, MSFT) → US (SMART)

client._create_contract('AAPL')  # → Stock('AAPL', 'SMART', 'USD')
client._create_contract('0700')  # → Stock('0700', 'SEHK', 'HKD')
```

---

## 5. Test Results (2025-12-10)

### Connection Tests

| Test | Status |
|------|--------|
| Java 17 + JavaFX | ✅ Pass |
| IB Gateway Start | ✅ Pass |
| 2FA (IB Key) | ✅ Pass |
| API Connection | ✅ Pass |
| Account Detection | ✅ Pass (DUO931484) |

### IBKRClient Tests

| Test | Status |
|------|--------|
| connect() | ✅ Pass |
| is_connected() | ✅ Pass |
| get_portfolio() | ✅ Pass |
| get_positions() | ✅ Pass |
| get_open_orders() | ✅ Pass |
| execute_trade() | ✅ Pass |
| cancel_order() | ✅ Pass |
| _round_to_tick() | ✅ Pass (11 cases) |
| _create_contract() auto-detect | ✅ Pass |
| disconnect() | ✅ Pass |

### Paper Trading Tests

| Test | Status | Details |
|------|--------|---------|
| Contract Qualification | ✅ Pass | AAPL conId: 265598 |
| Place Limit Order | ✅ Pass | Order submitted |
| Cancel Order | ✅ Pass | Order cancelled |
| Position Tracking | ✅ Pass | Shows correctly |

---

## 6. Commands

### Start IBGA
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international/ibga
docker compose up -d
```

### Check Logs
```bash
docker logs catalyst-ibga --tail 50
```

### Test Connection
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
IBKR_PORT=4000 python3 scripts/test_ibga_connection.py
```

### Quick Connection Test
```bash
python3 -c "
from ib_async import IB
ib = IB()
ib.connect('127.0.0.1', 4000, clientId=1, timeout=15)
print('Connected:', ib.managedAccounts())
ib.disconnect()
"
```

### Test Paper Trade
```bash
python3 -c "
from ib_async import IB, Stock, LimitOrder
ib = IB()
ib.connect('127.0.0.1', 4000, clientId=1, timeout=15)
contract = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(contract)
order = LimitOrder('BUY', 1, 150.00)
trade = ib.placeOrder(contract, order)
ib.sleep(2)
print(f'Order {trade.order.orderId}: {trade.orderStatus.status}')
ib.cancelOrder(trade.order)
ib.disconnect()
"
```

### View VNC (for debugging)
```
http://209.38.87.27:5800
```

---

## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         IBGA CONTAINER                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │    Xvfb     │───▶│ IB Gateway  │───▶│   jauto     │             │
│  │  (Display)  │    │   (GUI)     │    │ (Automation)│             │
│  └─────────────┘    └──────┬──────┘    └─────────────┘             │
│                            │                                        │
│                     Port 9000 (internal)                            │
│                            │                                        │
│                     ┌──────┴──────┐                                 │
│                     │   socat     │                                 │
│                     │ 4000→9000   │                                 │
│                     └──────┬──────┘                                 │
│                            │                                        │
└────────────────────────────┼────────────────────────────────────────┘
                             │
                      Port 4000 (external)
                             │
              ┌──────────────┴──────────────┐
              │         ib_async            │
              │    (Python library)         │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │       brokers/ibkr.py       │
              │       IBKRClient v2.1.0     │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │         Agent Tools         │
              │  execute_trade, get_quote   │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │        Claude API           │
              │    (Decision Making)        │
              └─────────────────────────────┘
```

---

## 8. Cost Summary

| Item | Cost |
|------|------|
| DO Droplet (Basic, 1GB) | $6 |
| DO Managed PostgreSQL (shared) | $0 (already have) |
| Claude API (~200 cycles × 5K tokens) | ~$15-25 |
| IBKR Data (US included, HKEX extra) | ~$0-20 |
| **Total** | **~$21-51/month** |

---

## 9. Known Limitations

1. **Market data shows nan outside market hours** - Normal behavior
2. **Account balance may show 0** - Paper account needs reset in IBKR portal
3. **HKEX market data** - May require additional subscription

---

**Document Version:** 4.0.0
**Architecture:** Simple Droplet + Claude API + IBGA Socket API
**Monthly Cost:** ~$21-51
**Status:** Paper Trading Ready
