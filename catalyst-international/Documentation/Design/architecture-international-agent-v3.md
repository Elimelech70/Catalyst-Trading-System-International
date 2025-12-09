# Catalyst Trading System International - Agent Architecture

**Name of Application:** Catalyst Trading System International  
**Name of File:** architecture-international-agent-v3.md  
**Version:** 3.0.0  
**Last Updated:** 2025-12-09  
**Target Exchange:** Hong Kong Stock Exchange (HKEX)  
**Broker:** Interactive Brokers (IBKR) via Web API  
**Architecture:** AI Agent Pattern (Simple Droplet + Claude API + IBeam)

---

## REVISION HISTORY

**v3.0.0 (2025-12-09)** - IBeam Web API Integration
- Replaced ib_insync socket API with IBKR Web API
- Added IBeam Docker container for authentication
- REST-based broker communication
- Automatic session management with IB Key 2FA
- Enhanced health monitoring and reconnection

**v2.0.0 (2025-12-03)** - Simplified Architecture
- Single $6 DigitalOcean droplet
- Direct Claude API calls (no Docker, no Gradient)
- Cron-triggered Python scripts
- IBKR direct connection
- Shared PostgreSQL database with US system

**v1.0.0 (2025-12-03)** - Initial Agent Architecture
- Conceptual agent pattern design

---

## 1. Architecture Overview

### 1.1 The Simple Truth

Minimal infrastructure with Web API broker access:

- **1 small droplet** ($6/month)
- **1 Python script** (the agent)
- **1 Docker container** (IBeam for IBKR auth)
- **Cron** (the trigger)
- **Claude API** (the brain)
- **IBKR Web API** (the broker)
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
│                    │ Claude API  │       │   IBeam     │            │
│                    │ (Anthropic) │       │ (Docker)    │            │
│                    └─────────────┘       └──────┬──────┘            │
│                                                 │                   │
│                                                 ▼                   │
│                                          ┌─────────────┐            │
│                                          │ IBKR Web API│            │
│                                          │ (REST/WSS)  │            │
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

### 1.2 Why IBeam Web API?

| Aspect | Socket API (ib_insync) | Web API (IBeam) |
|--------|------------------------|-----------------|
| **Connection** | TWS/Gateway required | REST endpoints |
| **Authentication** | Manual 2FA daily | Automatic via IB Key |
| **Reconnection** | Complex handling | IBeam manages it |
| **Firewall** | Port forwarding needed | HTTPS only |
| **Rate Limit** | No explicit limit | 10 req/sec |
| **Session** | 24hr with restarts | Auto-maintained |

### 1.3 The Agent Loop

Every trading cycle:

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
│ 3. Claude Returns │  ← "Call scan_market()"
│    Tool Request   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. Execute Tool   │  ← Your code runs (via IBeam)
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
│   ├── ibkr_client.py          # IBKR Web API client (REST)
│   └── session_manager.py      # Session keepalive manager
│
├── data/
│   ├── __init__.py
│   ├── market.py               # Market data fetching
│   ├── news.py                 # News/sentiment
│   ├── patterns.py             # Pattern detection (bull flag, ABCD, etc.)
│   └── database.py             # PostgreSQL client
│
├── config/
│   ├── settings.yaml           # All configuration
│   └── prompts/
│       └── system.md           # Claude's instructions
│
├── docker/
│   ├── docker-compose.yml      # IBeam container
│   └── .env                    # IBKR credentials
│
├── scripts/
│   ├── health_check.sh         # IBeam health monitoring
│   └── setup.sh                # Initial setup script
│
├── logs/                       # Daily log files
│
├── requirements.txt            # Python dependencies
└── README.md
```

**Total: ~15 files** vs US system's ~50+ files

---

## 3. IBeam Configuration

### 3.1 Docker Compose for IBeam

```yaml
# docker/docker-compose.yml
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
      - ibeam_data:/srv/clientportal.gw
    healthcheck:
      test: ["CMD", "curl", "-k", "-f", "https://localhost:5000/v1/api/iserver/auth/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    restart: unless-stopped

volumes:
  ibeam_data:
```

### 3.2 IBeam Environment File

```bash
# docker/.env

# IBKR Credentials
IBEAM_ACCOUNT=your_username
IBEAM_PASSWORD=your_password

# Gateway Configuration
IBEAM_GATEWAY_BASE_URL=https://localhost:5000
IBEAM_LOG_LEVEL=INFO

# Authentication Settings
IBEAM_REQUEST_RETRIES=10
IBEAM_REQUEST_TIMEOUT=15
IBEAM_PAGE_LOAD_TIMEOUT=60

# 2FA - Using IB Key (automatic, no manual intervention)
IBEAM_TWO_FA_HANDLER=IB_KEY
```

### 3.3 IBeam Prerequisites

Before IBeam will work:

1. **IBKR Pro Account** (funded)
2. **IB Key Enabled** on IBKR Mobile app:
   - Open IBKR Mobile → Settings → Security → IB Key → Enable
3. **Paper Trading Account** (for testing):
   - Client Portal → Settings → Paper Trading Account → Reset Password

---

## 4. Core Implementation

### 4.1 Main Agent Script

```python
#!/usr/bin/env python3
"""
Catalyst Trading System International - HKEX Agent
Single script that runs via cron during market hours.
Uses IBKR Web API via IBeam for broker access.
"""

import anthropic
import json
import logging
from datetime import datetime
from pathlib import Path

from tools import TOOLS
from tool_executor import execute_tool
from safety import SafetyLayer
from data.database import Database
from data.market import MarketData
from brokers.ibkr_client import IBKRClient
from brokers.session_manager import IBKRSessionManager

# ============================================================================
# CONFIGURATION
# ============================================================================

CLAUDE_MODEL = "claude-sonnet-4-5-20250514"
MAX_TOOL_ITERATIONS = 20
LOG_DIR = Path("/var/log/catalyst-intl")
IBEAM_URL = "https://localhost:5000"

# ============================================================================
# SETUP
# ============================================================================

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"agent-{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("agent")

# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """
You are an autonomous trading agent for Hong Kong Stock Exchange (HKEX).

## Your Mission
Find and execute momentum day trades following Ross Cameron's methodology.

## Available Tools
- scan_market: Find trading candidates
- get_quote: Get current price/volume
- get_technicals: RSI, MACD, moving averages
- detect_patterns: Bull flag, cup & handle, ABCD, breakout
- get_news: Recent news and sentiment
- check_risk: Validate trade against limits
- get_portfolio: Current positions and P&L
- execute_trade: Submit order to IBKR
- close_position: Exit a position
- close_all: Emergency exit all positions
- send_alert: Email notification
- log_decision: Record reasoning

## Trading Rules
1. Only trade during market hours (9:30-12:00, 13:00-16:00 HKT)
2. Skip lunch break (12:00-13:00)
3. Maximum 5 positions at once
4. Maximum 20% portfolio per position
5. Stop loss required on every trade
6. Risk/reward minimum 2:1
7. ALWAYS call check_risk before execute_trade

## Entry Criteria (ALL required)
- News catalyst with positive sentiment
- Volume > 1.5x average
- RSI between 40-70
- Clear pattern detected (bull_flag, breakout, ABCD, etc.)
- check_risk returns approved=true

## Exit Rules
- Stop loss: Set at entry, never move down
- Take profit: 2-3x the risk
- Time stop: Close before lunch if flat

## Risk Limits
- Daily loss limit: 2% of portfolio → triggers close_all
- Warning at 1.5% daily loss → become conservative

## Your Response Style
1. Briefly explain what you observe
2. State your decision and why
3. Call appropriate tools
4. After trades, summarize actions taken

## Current Context
Exchange: HKEX
Currency: HKD  
Lot Size: 100 shares (board lots)
Timezone: Asia/Hong_Kong (UTC+8)
Broker: Interactive Brokers (Web API)
Mode: Paper Trading
"""

# ============================================================================
# AGENT CLASS
# ============================================================================

class TradingAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.db = Database()
        self.market = MarketData()
        self.broker = IBKRClient(IBEAM_URL)
        self.safety = SafetyLayer()
        
        # Start session manager for keepalive
        self.session_mgr = IBKRSessionManager(self.broker)
        
        self.cycle_id = f"hkex_{datetime.now():%Y%m%d_%H%M%S}"
        self.tools_called = []
    
    def check_broker_connection(self) -> bool:
        """Verify IBeam is authenticated before trading."""
        try:
            status = self.broker.check_auth_status()
            if not status.get("authenticated"):
                log.error("IBeam not authenticated - cannot trade")
                return False
            
            # Get accounts to set account_id
            self.broker.get_accounts()
            log.info(f"Connected to IBKR account: {self.broker.account_id}")
            return True
            
        except Exception as e:
            log.error(f"Broker connection failed: {e}")
            return False
    
    def build_context(self) -> str:
        """Gather all context Claude needs to make decisions."""
        
        portfolio = self.broker.get_portfolio()
        daily_pnl = self.db.get_daily_pnl(exchange='HKEX')
        positions = self.db.get_open_positions(exchange='HKEX')
        market_status = self.market.get_status()
        
        return f"""
# Trading Cycle: {self.cycle_id}
**Time:** {datetime.now():%Y-%m-%d %H:%M:%S} HKT
**Market Status:** {market_status}
**Broker:** IBKR Web API (Connected)

## Portfolio
- Cash: HKD {portfolio['cash']:,.2f}
- Positions Value: HKD {portfolio['positions_value']:,.2f}
- Total Value: HKD {portfolio['total']:,.2f}

## Today's Performance
- Daily P&L: HKD {daily_pnl:,.2f}
- Open Positions: {len(positions)}

## Open Positions
{self._format_positions(positions)}

---
Analyze conditions and execute the trading strategy.
"""
    
    def _format_positions(self, positions: list) -> str:
        if not positions:
            return "None"
        
        lines = []
        for p in positions:
            lines.append(f"- {p['symbol']}: {p['quantity']} shares @ {p['entry_price']:.2f} (P&L: {p['unrealized_pnl']:+.2f})")
        return "\n".join(lines)
    
    def run(self) -> dict:
        """Execute one trading cycle."""
        
        log.info(f"Starting cycle: {self.cycle_id}")
        start_time = datetime.now()
        
        # Verify broker connection first
        if not self.check_broker_connection():
            return {
                "cycle_id": self.cycle_id,
                "error": "Broker not connected",
                "duration": 0,
                "tools_called": []
            }
        
        # Start session keepalive
        self.session_mgr.start()
        
        try:
            # Build initial context
            context = self.build_context()
            messages = [{"role": "user", "content": context}]
            
            # Agent loop
            iterations = 0
            final_text = ""
            
            while iterations < MAX_TOOL_ITERATIONS:
                iterations += 1
                
                # Call Claude
                response = self.client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages
                )
                
                log.debug(f"Iteration {iterations}: stop_reason={response.stop_reason}")
                
                if response.stop_reason == "tool_use":
                    # Process tool calls
                    tool_results = []
                    
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_input = block.input
                            
                            log.info(f"Tool: {tool_name}({json.dumps(tool_input)})")
                            self.tools_called.append(tool_name)
                            
                            # Safety check
                            allowed, reason = self.safety.check(tool_name, tool_input)
                            
                            if not allowed:
                                log.warning(f"Blocked: {reason}")
                                result = f"BLOCKED: {reason}"
                            else:
                                result = execute_tool(
                                    tool_name, 
                                    tool_input,
                                    broker=self.broker,
                                    db=self.db,
                                    market=self.market
                                )
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result) if not isinstance(result, str) else result
                            })
                    
                    # Add to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                
                else:
                    # Claude is done
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text
                    break
            
            # Log completion
            duration = (datetime.now() - start_time).total_seconds()
            log.info(f"Cycle complete: {duration:.1f}s, {len(self.tools_called)} tool calls")
            
            # Store cycle in database
            self.db.log_cycle(
                cycle_id=self.cycle_id,
                exchange='HKEX',
                duration=duration,
                tools_called=self.tools_called,
                summary=final_text[:500]
            )
            
            return {
                "cycle_id": self.cycle_id,
                "duration": duration,
                "tools_called": self.tools_called,
                "summary": final_text
            }
            
        finally:
            # Stop session keepalive
            self.session_mgr.stop()

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Entry point for cron."""
    try:
        agent = TradingAgent()
        result = agent.run()
        print(json.dumps(result, indent=2, default=str))
        return 0
    except Exception as e:
        log.exception(f"Agent failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
```

### 4.2 IBKR Web API Client

```python
# brokers/ibkr_client.py
"""
IBKR Web API client via IBeam gateway.
REST-based communication with Interactive Brokers.
"""

import os
import logging
import requests
from typing import Optional, Dict, Any, List
import urllib3

# Disable SSL warnings for IBeam's self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger("ibkr")


class IBKRClient:
    """IBKR Web API client via IBeam gateway."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("IBEAM_URL", "https://localhost:5000")
        self.session = requests.Session()
        self.session.verify = False  # IBeam uses self-signed cert
        self.account_id: Optional[str] = None
    
    # =========================================================================
    # Authentication
    # =========================================================================
    
    def check_auth_status(self) -> Dict[str, Any]:
        """Check if gateway is authenticated."""
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/auth/status"
        )
        return response.json()
    
    def tickle(self) -> Dict[str, Any]:
        """Keep session alive - call every 5 minutes."""
        response = self.session.post(f"{self.base_url}/v1/api/tickle")
        return response.json()
    
    def reauthenticate(self) -> Dict[str, Any]:
        """Re-initialize brokerage session."""
        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/reauthenticate"
        )
        return response.json()
    
    # =========================================================================
    # Account
    # =========================================================================
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get list of accounts."""
        response = self.session.get(
            f"{self.base_url}/v1/api/portfolio/accounts"
        )
        data = response.json()
        if data and len(data) > 0:
            self.account_id = data[0].get("accountId")
        return data
    
    def get_portfolio(self) -> Dict[str, Any]:
        """Get account summary and positions."""
        if not self.account_id:
            self.get_accounts()
        
        # Get account summary
        summary_resp = self.session.get(
            f"{self.base_url}/v1/api/portfolio/{self.account_id}/summary"
        )
        summary = summary_resp.json()
        
        # Get positions
        positions_resp = self.session.get(
            f"{self.base_url}/v1/api/portfolio/{self.account_id}/positions/0"
        )
        positions = positions_resp.json() if positions_resp.status_code == 200 else []
        
        # Extract HKD cash
        cash = 0.0
        if "availablefunds" in summary:
            cash = float(summary["availablefunds"].get("amount", 0))
        
        # Filter HKEX positions
        hkex_positions = []
        positions_value = 0.0
        
        for pos in positions:
            if pos.get("exchange") == "SEHK":
                market_value = float(pos.get("mktValue", 0))
                positions_value += market_value
                hkex_positions.append({
                    "symbol": pos.get("contractDesc", ""),
                    "conid": pos.get("conid"),
                    "quantity": pos.get("position", 0),
                    "avg_cost": pos.get("avgCost", 0),
                    "market_value": market_value,
                    "unrealized_pnl": pos.get("unrealizedPnl", 0)
                })
        
        return {
            "cash": cash,
            "positions_value": positions_value,
            "total": cash + positions_value,
            "positions": hkex_positions
        }
    
    # =========================================================================
    # Market Data
    # =========================================================================
    
    def search_contract(self, symbol: str, sec_type: str = "STK") -> List[Dict[str, Any]]:
        """Search for contract by symbol."""
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/secdef/search",
            params={"symbol": symbol, "secType": sec_type}
        )
        return response.json()
    
    def get_hkex_conid(self, symbol: str) -> Optional[int]:
        """Get conid for HKEX stock."""
        results = self.search_contract(symbol)
        
        for result in results:
            # Look for SEHK exchange
            sections = result.get("sections", [])
            for section in sections:
                if section.get("exchange") == "SEHK":
                    return result.get("conid")
        
        return None
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get current quote for HKEX stock."""
        conid = self.get_hkex_conid(symbol)
        if not conid:
            return {"error": f"Symbol {symbol} not found on HKEX"}
        
        return self.get_market_data([conid])
    
    def get_market_data(self, conids: List[int], fields: List[str] = None) -> Dict[str, Any]:
        """Get market data snapshot."""
        if fields is None:
            # 31=Last, 84=Bid, 86=Ask, 87=Volume, 7295=Open, 7296=High, 7297=Low
            fields = ["31", "84", "86", "87", "7295", "7296", "7297"]
        
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/marketdata/snapshot",
            params={
                "conids": ",".join(map(str, conids)),
                "fields": ",".join(fields)
            }
        )
        return response.json()
    
    # =========================================================================
    # Order Management
    # =========================================================================
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MKT",
        limit_price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        tif: str = "DAY"
    ) -> Dict[str, Any]:
        """Place an order on HKEX."""
        if not self.account_id:
            self.get_accounts()
        
        # Get conid for symbol
        conid = self.get_hkex_conid(symbol)
        if not conid:
            return {"error": f"Symbol {symbol} not found on HKEX"}
        
        # Build order
        order = {
            "conid": conid,
            "side": side.upper(),  # BUY or SELL
            "quantity": quantity,
            "orderType": order_type,  # MKT, LMT, STP
            "tif": tif,  # DAY, GTC, IOC
        }
        
        if limit_price and order_type == "LMT":
            order["price"] = limit_price
        
        # Place main order
        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/orders",
            json={"orders": [order]}
        )
        result = response.json()
        
        # Handle confirmation dialogs
        if isinstance(result, list) and len(result) > 0:
            if "id" in result[0]:
                # Needs confirmation
                confirm_result = self.confirm_order(result[0]["id"])
                return confirm_result
        
        log.info(f"Order placed: {symbol} {side} {quantity} @ {order_type}")
        
        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "result": result
        }
    
    def place_bracket_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        order_type: str = "LMT"
    ) -> Dict[str, Any]:
        """Place bracket order with stop loss and take profit."""
        if not self.account_id:
            self.get_accounts()
        
        conid = self.get_hkex_conid(symbol)
        if not conid:
            return {"error": f"Symbol {symbol} not found on HKEX"}
        
        exit_side = "SELL" if side.upper() == "BUY" else "BUY"
        
        orders = [
            # Parent order
            {
                "conid": conid,
                "side": side.upper(),
                "quantity": quantity,
                "orderType": order_type,
                "price": entry_price,
                "tif": "DAY",
                "cOID": "parent"
            },
            # Take profit
            {
                "conid": conid,
                "side": exit_side,
                "quantity": quantity,
                "orderType": "LMT",
                "price": take_profit,
                "tif": "GTC",
                "parentId": "parent"
            },
            # Stop loss
            {
                "conid": conid,
                "side": exit_side,
                "quantity": quantity,
                "orderType": "STP",
                "price": stop_loss,
                "tif": "GTC",
                "parentId": "parent"
            }
        ]
        
        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/orders",
            json={"orders": orders}
        )
        result = response.json()
        
        # Handle confirmations
        if isinstance(result, list):
            for item in result:
                if "id" in item:
                    self.confirm_order(item["id"])
        
        log.info(f"Bracket order: {symbol} {side} {quantity} @ {entry_price}, SL={stop_loss}, TP={take_profit}")
        
        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "result": result
        }
    
    def confirm_order(self, reply_id: str, confirmed: bool = True) -> Dict[str, Any]:
        """Confirm order after placement (handles order warnings)."""
        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/reply/{reply_id}",
            json={"confirmed": confirmed}
        )
        return response.json()
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get live orders."""
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/account/orders"
        )
        return response.json()
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        if not self.account_id:
            self.get_accounts()
        
        response = self.session.delete(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/order/{order_id}"
        )
        return response.json()
    
    # =========================================================================
    # Position Management
    # =========================================================================
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self.account_id:
            self.get_accounts()
        
        response = self.session.get(
            f"{self.base_url}/v1/api/portfolio/{self.account_id}/positions/0"
        )
        return response.json() if response.status_code == 200 else []
    
    def close_position(self, symbol: str, reason: str = "") -> Dict[str, Any]:
        """Close a specific position."""
        positions = self.get_positions()
        
        for pos in positions:
            if pos.get("contractDesc", "").startswith(symbol):
                conid = pos.get("conid")
                qty = abs(pos.get("position", 0))
                side = "SELL" if pos.get("position", 0) > 0 else "BUY"
                
                result = self.place_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    order_type="MKT"
                )
                
                log.info(f"Closing {symbol}: {reason}")
                
                return {
                    "symbol": symbol,
                    "closed": True,
                    "quantity": qty,
                    "reason": reason,
                    "result": result
                }
        
        return {"symbol": symbol, "closed": False, "reason": "Position not found"}
    
    def close_all_positions(self, reason: str) -> Dict[str, Any]:
        """Emergency: close all HKEX positions."""
        positions = self.get_positions()
        
        closed = []
        for pos in positions:
            if pos.get("exchange") == "SEHK" and pos.get("position", 0) != 0:
                symbol = pos.get("contractDesc", "").split()[0]
                result = self.close_position(symbol, reason)
                closed.append(result)
        
        log.critical(f"EMERGENCY CLOSE: {len(closed)} positions, reason: {reason}")
        
        return {
            "emergency": True,
            "reason": reason,
            "positions_closed": len(closed),
            "details": closed
        }
```

### 4.3 Session Manager

```python
# brokers/session_manager.py
"""
IBKR session keepalive manager.
Maintains session by calling tickle endpoint periodically.
"""

import time
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ibkr_client import IBKRClient

log = logging.getLogger("session")


class IBKRSessionManager:
    """Manages IBKR session keepalive."""
    
    def __init__(self, client: "IBKRClient", tickle_interval: int = 240):
        self.client = client
        self.tickle_interval = tickle_interval  # seconds (must be < 5 min)
        self.running = False
        self.thread = None
    
    def start(self):
        """Start session keepalive loop."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        self.thread.start()
        log.info("Session keepalive started")
    
    def stop(self):
        """Stop session keepalive."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        log.info("Session keepalive stopped")
    
    def _keepalive_loop(self):
        """Background keepalive loop."""
        while self.running:
            try:
                status = self.client.check_auth_status()
                
                if status.get("authenticated"):
                    self.client.tickle()
                    log.debug("Session tickled")
                else:
                    log.warning("Session not authenticated, attempting reauthentication")
                    self.client.reauthenticate()
                    
            except Exception as e:
                log.error(f"Keepalive error: {e}")
            
            # Sleep in small increments for responsive shutdown
            for _ in range(self.tickle_interval):
                if not self.running:
                    break
                time.sleep(1)
```

### 4.4 Tool Definitions

```python
# tools.py
"""Tool definitions for Claude."""

TOOLS = [
    {
        "name": "scan_market",
        "description": "Scan HKEX for trading candidates. Returns top stocks by momentum and volume.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "string",
                    "enum": ["HSI", "HSCEI", "HSTECH", "ALL"],
                    "description": "Which index to scan"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max candidates to return (default 10)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_quote",
        "description": "Get current price and volume for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock code (e.g., '0700' for Tencent)"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_technicals",
        "description": "Get technical indicators: RSI, MACD, moving averages, ATR.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "timeframe": {"type": "string", "enum": ["5m", "15m", "1h", "1d"]}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_news",
        "description": "Get recent news and sentiment for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "hours": {"type": "integer", "description": "Hours back (default 24)"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "detect_patterns",
        "description": "Detect chart patterns: bull_flag, cup_handle, ABCD, breakout, consolidation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "timeframe": {"type": "string", "enum": ["5m", "15m", "1h"]}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "check_risk",
        "description": "Validate proposed trade against risk limits. MUST call before execute_trade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "quantity": {"type": "integer"},
                "entry_price": {"type": "number"},
                "stop_loss": {"type": "number"}
            },
            "required": ["symbol", "side", "quantity", "entry_price", "stop_loss"]
        }
    },
    {
        "name": "get_portfolio",
        "description": "Get current portfolio: cash, positions, P&L.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "execute_trade",
        "description": "Submit order to IBKR. Only call after check_risk approves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "quantity": {"type": "integer"},
                "order_type": {"type": "string", "enum": ["market", "limit"]},
                "limit_price": {"type": "number"},
                "stop_loss": {"type": "number"},
                "take_profit": {"type": "number"}
            },
            "required": ["symbol", "side", "quantity", "stop_loss", "take_profit"]
        }
    },
    {
        "name": "close_position",
        "description": "Exit a specific position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "reason": {"type": "string", "description": "Why closing"}
            },
            "required": ["symbol", "reason"]
        }
    },
    {
        "name": "close_all",
        "description": "EMERGENCY: Close all positions immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why emergency close"}
            },
            "required": ["reason"]
        }
    },
    {
        "name": "send_alert",
        "description": "Send email notification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "message": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]}
            },
            "required": ["subject", "message"]
        }
    },
    {
        "name": "log_decision",
        "description": "Record trading decision and reasoning for later review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "decision": {"type": "string"},
                "reasoning": {"type": "string"},
                "confidence": {"type": "number", "description": "0-1 confidence level"}
            },
            "required": ["decision", "reasoning"]
        }
    }
]
```

---

## 5. Configuration

### 5.1 Settings File

```yaml
# config/settings.yaml

# Exchange
exchange:
  code: HKEX
  currency: HKD
  timezone: Asia/Hong_Kong
  lot_size: 100
  
  # Trading hours (HKT)
  morning_open: "09:30"
  morning_close: "12:00"
  afternoon_open: "13:00"
  afternoon_close: "16:00"

# Broker - IBeam Web API
broker:
  name: IBKR
  type: web_api
  ibeam_url: "https://localhost:5000"
  
  # Rate limiting
  max_requests_per_second: 10
  
  # Session management
  tickle_interval: 240  # seconds

# Risk Limits
risk:
  max_positions: 5
  max_position_pct: 0.20        # 20% of portfolio
  max_daily_loss_pct: 0.02      # 2% triggers emergency stop
  warning_loss_pct: 0.015       # 1.5% warning
  max_daily_trades: 10
  min_risk_reward: 2.0

# Claude
claude:
  model: "claude-sonnet-4-5-20250514"
  max_tokens: 4096
  max_iterations: 20

# Alerts
alerts:
  email: "craig@example.com"
  smtp_host: "smtp.gmail.com"
  smtp_port: 587

# Database
database:
  host: "${DB_HOST}"
  port: 5432
  name: "catalyst_trading"
  user: "${DB_USER}"
  password: "${DB_PASSWORD}"
```

### 5.2 Environment Variables

```bash
# /etc/environment or .env

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Database (shared with US)
DB_HOST=your-db-host.db.ondigitalocean.com
DB_USER=catalyst
DB_PASSWORD=xxxxx

# IBeam (IBKR Web API)
IBEAM_URL=https://localhost:5000

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=app-password
ALERT_EMAIL=craig@example.com
```

---

## 6. Health Monitoring

### 6.1 IBeam Health Check Script

```bash
#!/bin/bash
# scripts/health_check.sh

IBEAM_URL="https://localhost:5000"
LOG_FILE="/var/log/catalyst-intl/health.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

# Check authentication status
STATUS=$(curl -sk "${IBEAM_URL}/v1/api/iserver/auth/status" 2>/dev/null | jq -r '.authenticated // false')

if [ "$STATUS" != "true" ]; then
    log "ERROR: IBeam not authenticated, restarting..."
    
    cd /opt/catalyst-intl/docker
    docker-compose restart ibeam
    
    # Wait for restart
    sleep 120
    
    # Check again
    STATUS=$(curl -sk "${IBEAM_URL}/v1/api/iserver/auth/status" 2>/dev/null | jq -r '.authenticated // false')
    
    if [ "$STATUS" != "true" ]; then
        log "CRITICAL: IBeam still not authenticated after restart!"
        
        # Send alert email
        echo "IBeam authentication failed on $(hostname)" | mail -s "CATALYST ALERT: IBKR Down" "$ALERT_EMAIL"
    else
        log "OK: IBeam re-authenticated successfully"
    fi
else
    log "OK: IBeam authenticated"
    
    # Tickle to keep alive
    curl -sk -X POST "${IBEAM_URL}/v1/api/tickle" > /dev/null 2>&1
fi
```

### 6.2 Cron Jobs

```bash
# /etc/cron.d/catalyst-hkex

# ============================================================================
# CATALYST TRADING - HKEX (IBeam Web API)
# Times in HKT (same as Perth AWST)
# ============================================================================

# Health check every 5 minutes
*/5 * * * * root /opt/catalyst-intl/scripts/health_check.sh

# Morning Session (9:30 AM - 12:00 PM)
30 9  * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
0  10 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 10 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
0  11 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 11 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1

# Lunch Break: 12:00 - 13:00 (NO TRADING)

# Afternoon Session (1:00 PM - 4:00 PM)
0  13 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 13 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
0  14 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 14 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
0  15 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 15 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1

# End of Day (4:30 PM) - Close any remaining positions
30 16 * * 1-5  catalyst /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
```

---

## 7. Deployment

### 7.1 Setup Script

```bash
#!/bin/bash
# scripts/setup.sh - Run on fresh $6 droplet

set -e

echo "=== Catalyst International Setup (IBeam) ==="

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv docker.io docker-compose jq curl

# Enable Docker
systemctl enable docker
systemctl start docker

# Create user
useradd -m -s /bin/bash catalyst
usermod -aG docker catalyst

# Create directories
mkdir -p /opt/catalyst-intl
mkdir -p /var/log/catalyst-intl
chown -R catalyst:catalyst /opt/catalyst-intl
chown -R catalyst:catalyst /var/log/catalyst-intl

# Create virtual environment
su - catalyst -c "
cd /opt/catalyst-intl
python3 -m venv venv
source venv/bin/activate
pip install anthropic requests pyyaml asyncpg urllib3
"

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy code to /opt/catalyst-intl/"
echo "2. Configure /opt/catalyst-intl/docker/.env with IBKR credentials"
echo "3. Set environment variables (ANTHROPIC_API_KEY, etc.)"
echo "4. Enable IB Key on IBKR Mobile app"
echo "5. Start IBeam: cd /opt/catalyst-intl/docker && docker-compose up -d"
echo "6. Test: curl -sk https://localhost:5000/v1/api/iserver/auth/status"
echo "7. Run agent: /opt/catalyst-intl/venv/bin/python /opt/catalyst-intl/agent.py"
echo "8. Install cron: cp /opt/catalyst-intl/cron.d/catalyst-hkex /etc/cron.d/"
```

### 7.2 Deploy Command

```bash
# From local machine
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='.env' \
  ./catalyst-international/ \
  root@your-droplet:/opt/catalyst-intl/

# Then on droplet
ssh root@your-droplet
cd /opt/catalyst-intl/docker
docker-compose up -d

# Verify
docker logs -f catalyst-ibeam
```

### 7.3 Testing Procedure

```bash
# 1. Check IBeam is running
docker ps | grep ibeam

# 2. Wait for authentication (watch logs)
docker logs -f catalyst-ibeam
# Look for "Client login succeeds"

# 3. Test API endpoints
curl -sk https://localhost:5000/v1/api/iserver/auth/status | jq

# 4. Run agent manually
cd /opt/catalyst-intl
source venv/bin/activate
python agent.py
```

---

## 8. API Rate Limits

| Endpoint | Limit |
|----------|-------|
| Global | 10 requests/second |
| Market data | 1 request/second per symbol |
| Orders | 50/second (Web API) |
| Violations | 15 min penalty box |

Implement rate limiting in your client:

```python
import time
from functools import wraps

def rate_limit(calls_per_second=10):
    min_interval = 1.0 / calls_per_second
    last_call = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_call[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 9. Cost Summary

### Monthly Costs

| Item | Cost |
|------|------|
| DO Droplet (Basic, 1GB) | $6 |
| DO Managed PostgreSQL (shared) | $0 (already have) |
| Claude API (~200 cycles × 5K tokens) | ~$15-25 |
| IBKR Data (HKEX) | ~$10-20 |
| **Total** | **~$31-51/month** |

### Comparison

| Aspect | v2.0 (ib_insync) | v3.0 (IBeam Web API) |
|--------|------------------|----------------------|
| Broker Connection | Socket (TWS required) | REST (IBeam Docker) |
| Authentication | Manual daily | Automatic (IB Key) |
| Reconnection | Complex | Auto-managed |
| Infrastructure | 1 script | 1 script + 1 container |
| Reliability | Moderate | High |

---

## 10. Summary

### What Changed in v3.0

1. **Replaced ib_insync with IBKR Web API** - REST-based instead of socket
2. **Added IBeam Docker container** - Handles authentication automatically
3. **Session management** - Automatic keepalive and reconnection
4. **Health monitoring** - Cron-based health checks with auto-restart
5. **Improved reliability** - No manual 2FA required (IB Key)

### Files to Create

```
catalyst-international/
├── agent.py                    # 250 lines
├── tools.py                    # 120 lines
├── tool_executor.py            # 100 lines
├── safety.py                   # 80 lines
├── brokers/
│   ├── ibkr_client.py          # 300 lines
│   └── session_manager.py      # 60 lines
├── data/database.py            # 100 lines
├── data/market.py              # 100 lines
├── docker/
│   ├── docker-compose.yml      # 25 lines
│   └── .env                    # 10 lines
├── scripts/
│   ├── health_check.sh         # 40 lines
│   └── setup.sh                # 35 lines
├── config/settings.yaml        # 50 lines
└── requirements.txt            # 10 lines
                                ─────────
                                ~1280 lines total
```

### Key Principles

1. **Claude is the brain** - No hardcoded workflow logic
2. **IBeam handles auth** - No manual intervention needed
3. **REST is simpler** - HTTP calls instead of socket management
4. **Safety first** - All actions validated
5. **Auto-recovery** - Health checks restart failed connections

---

**Document Version:** 3.0.0  
**Architecture:** Simple Droplet + Claude API + IBeam Web API  
**Monthly Cost:** ~$31-51  
**Lines of Code:** ~1280  
**Status:** Ready for Implementation
