# Catalyst Trading System International - Agent Architecture

**Name of Application:** Catalyst Trading System International  
**Name of File:** architecture-international-agent-v2.md  
**Version:** 2.0.0  
**Last Updated:** 2025-12-03  
**Target Exchange:** Hong Kong Stock Exchange (HKEX)  
**Broker:** Interactive Brokers (IBKR)  
**Architecture:** AI Agent Pattern (Simple Droplet + Claude API)

---

## REVISION HISTORY

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

No Docker. No microservices. No complex platform.

Just:
- **1 small droplet** ($6/month)
- **1 Python script** (the agent)
- **Cron** (the trigger)
- **Claude API** (the brain)
- **IBKR API** (the broker)
- **PostgreSQL** (shared with US)

```
┌─────────────────────────────────────────────────────────────────┐
│              DIGITALOCEAN DROPLET ($6/month)                    │
│                                                                 │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────────┐   │
│   │   CRON   │────▶│    AGENT     │────▶│      TOOLS       │   │
│   │          │     │   (Python)   │     │    (Functions)   │   │
│   │ 9:30 AM  │     │              │     │                  │   │
│   │ 10:30 AM │     │ Calls Claude │     │ - scan_market()  │   │
│   │ ...      │     │ Executes     │     │ - get_news()     │   │
│   │ 3:30 PM  │     │ Tools        │     │ - execute_trade()│   │
│   └──────────┘     └──────────────┘     │ - check_risk()   │   │
│                           │             └────────┬─────────┘   │
│                           │                      │             │
│                           ▼                      ▼             │
│                    ┌─────────────┐       ┌─────────────┐       │
│                    │ Claude API  │       │  IBKR API   │       │
│                    │ (Anthropic) │       │  (Broker)   │       │
│                    └─────────────┘       └─────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │ (DO Managed DB) │
                    │ Shared with US  │
                    └─────────────────┘
```

### 1.2 Why This Approach?

| Aspect | US System (Microservices) | International (Agent) |
|--------|---------------------------|----------------------|
| **Components** | 8 Docker containers | 1 Python script |
| **Infrastructure** | Docker, Redis, multiple ports | Just Python + cron |
| **Monthly Cost** | ~$24+ droplet | $6 droplet |
| **Decision Making** | Hardcoded workflow | Claude decides |
| **Maintenance** | 8 services to update | 1 script to update |
| **Debugging** | 8 logs to check | 1 log file |
| **Deployment** | docker-compose up | scp + crontab |

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
│ 4. Execute Tool   │  ← Your code runs
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
│   └── ibkr.py                 # Interactive Brokers client
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
├── logs/                       # Daily log files
│
├── requirements.txt            # Python dependencies
├── setup.sh                    # Initial setup script
└── README.md
```

**Total: ~10 files** vs US system's ~50+ files

---

## 3. Core Implementation

### 3.1 Main Agent Script

```python
#!/usr/bin/env python3
"""
Catalyst Trading System International - HKEX Agent
Single script that runs via cron during market hours.
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
from brokers.ibkr import IBKRClient

# ============================================================================
# CONFIGURATION
# ============================================================================

CLAUDE_MODEL = "claude-sonnet-4-5-20250514"
MAX_TOOL_ITERATIONS = 20
LOG_DIR = Path("/var/log/catalyst-intl")

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
Broker: Interactive Brokers
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
        self.broker = IBKRClient()
        self.safety = SafetyLayer()
        
        self.cycle_id = f"hkex_{datetime.now():%Y%m%d_%H%M%S}"
        self.tools_called = []
    
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
        
        # Build initial context
        context = self.build_context()
        messages = [{"role": "user", "content": context}]
        
        # Agent loop
        iterations = 0
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
                final_text = ""
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

### 3.2 Tool Definitions

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
        "description": "Detect chart patterns: bull_flag, cup_handle, ascending_triangle, ABCD, breakout. Returns patterns with confidence scores.",
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
        "name": "check_risk",
        "description": "Validate a trade against risk limits. MUST call before execute_trade.",
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
        "description": "Execute a trade via IBKR. Only call after check_risk approves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "quantity": {"type": "integer"},
                "order_type": {"type": "string", "enum": ["market", "limit"]},
                "limit_price": {"type": "number"},
                "stop_loss": {"type": "number"},
                "take_profit": {"type": "number"},
                "reason": {"type": "string", "description": "Why this trade (for audit)"}
            },
            "required": ["symbol", "side", "quantity", "order_type", "stop_loss", "take_profit", "reason"]
        }
    },
    {
        "name": "close_position",
        "description": "Close an existing position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "reason": {"type": "string"}
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
                "reason": {"type": "string"}
            },
            "required": ["reason"]
        }
    },
    {
        "name": "send_alert",
        "description": "Send email alert to operator.",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                "subject": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["severity", "subject", "message"]
        }
    },
    {
        "name": "log_decision",
        "description": "Log a decision to database for audit trail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["trade", "skip", "close", "emergency"]},
                "symbol": {"type": "string"},
                "reasoning": {"type": "string"}
            },
            "required": ["decision", "reasoning"]
        }
    }
]
```

### 3.3 Tool Executor

```python
# tool_executor.py
"""Execute tool requests from Claude."""

import logging
from typing import Any

log = logging.getLogger("tools")


def execute_tool(
    name: str, 
    params: dict,
    broker,
    db,
    market
) -> Any:
    """Route tool call to implementation."""
    
    try:
        if name == "scan_market":
            return market.scan(
                index=params.get("index", "HSI"),
                limit=params.get("limit", 10)
            )
        
        elif name == "get_quote":
            return market.get_quote(params["symbol"])
        
        elif name == "get_technicals":
            return market.get_technicals(
                params["symbol"],
                params.get("timeframe", "15m")
            )
        
        elif name == "get_news":
            return market.get_news(
                params["symbol"],
                params.get("hours", 24)
            )
        
        elif name == "detect_patterns":
            return market.detect_patterns(
                params["symbol"],
                params.get("timeframe", "15m")
            )
        
        elif name == "check_risk":
            return db.check_risk(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                entry_price=params["entry_price"],
                stop_loss=params["stop_loss"]
            )
        
        elif name == "get_portfolio":
            return broker.get_portfolio()
        
        elif name == "execute_trade":
            # Execute via broker
            order = broker.place_order(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                order_type=params["order_type"],
                limit_price=params.get("limit_price"),
                stop_loss=params["stop_loss"],
                take_profit=params["take_profit"]
            )
            
            # Log to database
            db.log_trade(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                order_id=order["order_id"],
                reason=params["reason"]
            )
            
            return order
        
        elif name == "close_position":
            return broker.close_position(
                params["symbol"],
                params["reason"]
            )
        
        elif name == "close_all":
            return broker.close_all_positions(params["reason"])
        
        elif name == "send_alert":
            return _send_email(
                params["severity"],
                params["subject"],
                params["message"]
            )
        
        elif name == "log_decision":
            return db.log_decision(
                decision=params["decision"],
                symbol=params.get("symbol"),
                reasoning=params["reasoning"]
            )
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        log.exception(f"Tool {name} failed")
        return {"error": str(e)}


def _send_email(severity: str, subject: str, message: str) -> dict:
    """Send email alert."""
    import smtplib
    from email.mime.text import MIMEText
    import os
    
    # Load from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    alert_to = os.getenv("ALERT_EMAIL")
    
    if not all([smtp_user, smtp_pass, alert_to]):
        log.warning("Email not configured")
        return {"sent": False, "reason": "Email not configured"}
    
    # Add severity emoji
    emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(severity, "")
    full_subject = f"{emoji} [HKEX] {subject}"
    
    msg = MIMEText(message)
    msg["Subject"] = full_subject
    msg["From"] = smtp_user
    msg["To"] = alert_to
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return {"sent": True}
    except Exception as e:
        log.error(f"Email failed: {e}")
        return {"sent": False, "error": str(e)}
```

### 3.4 Safety Layer

```python
# safety.py
"""Validate all actions before execution."""

import logging
from datetime import datetime, time

log = logging.getLogger("safety")


class SafetyLayer:
    """Validates all tool calls."""
    
    def __init__(self):
        self.daily_trades = 0
        self.last_reset = datetime.now().date()
        
        # Limits
        self.max_daily_trades = 10
        self.lot_size = 100  # HKEX board lot
    
    def check(self, tool: str, params: dict) -> tuple[bool, str]:
        """Check if tool call is allowed."""
        
        # Reset daily counter
        if datetime.now().date() != self.last_reset:
            self.daily_trades = 0
            self.last_reset = datetime.now().date()
        
        # Read-only tools always allowed
        read_only = ["scan_market", "get_quote", "get_technicals", 
                     "get_news", "get_portfolio", "log_decision"]
        if tool in read_only:
            return True, "OK"
        
        # Check market hours for trading
        if tool in ["execute_trade", "close_position"]:
            if not self._is_market_open():
                return False, "Market closed"
        
        # Validate execute_trade
        if tool == "execute_trade":
            return self._check_trade(params)
        
        # Alert rate limiting could go here
        if tool == "send_alert":
            return True, "OK"
        
        # Emergency close always allowed
        if tool == "close_all":
            log.critical(f"Emergency close: {params.get('reason')}")
            return True, "Emergency authorized"
        
        return True, "OK"
    
    def _is_market_open(self) -> bool:
        """Check HKEX market hours."""
        now = datetime.now()
        t = now.time()
        
        # Weekend check
        if now.weekday() >= 5:
            return False
        
        # Morning: 9:30 - 12:00
        morning = time(9, 30) <= t < time(12, 0)
        
        # Afternoon: 13:00 - 16:00
        afternoon = time(13, 0) <= t < time(16, 0)
        
        return morning or afternoon
    
    def _check_trade(self, params: dict) -> tuple[bool, str]:
        """Validate trade parameters."""
        
        # Daily limit
        if self.daily_trades >= self.max_daily_trades:
            return False, f"Daily trade limit ({self.max_daily_trades})"
        
        # Lot size
        qty = params.get("quantity", 0)
        if qty % self.lot_size != 0:
            return False, f"Quantity must be multiple of {self.lot_size}"
        
        # Required fields
        if not params.get("stop_loss"):
            return False, "Stop loss required"
        if not params.get("take_profit"):
            return False, "Take profit required"
        if not params.get("reason"):
            return False, "Trade reason required"
        
        self.daily_trades += 1
        return True, "OK"
```

---

## 4. IBKR Integration

### 4.1 IBKR Client

```python
# brokers/ibkr.py
"""Interactive Brokers client for HKEX trading."""

import logging
from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder, BracketOrder
from typing import Optional
import os

log = logging.getLogger("ibkr")


class IBKRClient:
    """Interactive Brokers connection for HKEX."""
    
    def __init__(self):
        self.ib = IB()
        self.connected = False
        
        # Connection settings
        self.host = os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = int(os.getenv("IBKR_PORT", "7497"))  # 7497=paper, 7496=live
        self.client_id = int(os.getenv("IBKR_CLIENT_ID", "1"))
    
    def connect(self):
        """Connect to IBKR TWS/Gateway."""
        if not self.connected:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            log.info(f"Connected to IBKR at {self.host}:{self.port}")
    
    def disconnect(self):
        """Disconnect from IBKR."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
    
    def get_portfolio(self) -> dict:
        """Get account summary and positions."""
        self.connect()
        
        # Account values
        account = self.ib.accountSummary()
        cash = float(next((a.value for a in account if a.tag == "CashBalance" and a.currency == "HKD"), 0))
        
        # Positions
        positions = []
        for pos in self.ib.positions():
            if pos.contract.exchange == "SEHK":
                positions.append({
                    "symbol": pos.contract.symbol,
                    "quantity": pos.position,
                    "avg_cost": pos.avgCost,
                    "market_value": pos.position * pos.avgCost  # Simplified
                })
        
        positions_value = sum(p["market_value"] for p in positions)
        
        return {
            "cash": cash,
            "positions_value": positions_value,
            "total": cash + positions_value,
            "positions": positions
        }
    
    def get_quote(self, symbol: str) -> dict:
        """Get current quote for HKEX stock."""
        self.connect()
        
        contract = Stock(symbol, "SEHK", "HKD")
        self.ib.qualifyContracts(contract)
        
        ticker = self.ib.reqMktData(contract)
        self.ib.sleep(1)  # Wait for data
        
        return {
            "symbol": symbol,
            "last": ticker.last,
            "bid": ticker.bid,
            "ask": ticker.ask,
            "volume": ticker.volume
        }
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str,
        limit_price: Optional[float] = None,
        stop_loss: float = None,
        take_profit: float = None
    ) -> dict:
        """Place bracket order on HKEX."""
        self.connect()
        
        contract = Stock(symbol, "SEHK", "HKD")
        self.ib.qualifyContracts(contract)
        
        action = "BUY" if side == "buy" else "SELL"
        
        # Create bracket order
        if order_type == "market":
            parent = MarketOrder(action, quantity)
        else:
            parent = LimitOrder(action, quantity, limit_price)
        
        # Stop loss
        stop_action = "SELL" if side == "buy" else "BUY"
        stop_order = StopOrder(stop_action, quantity, stop_loss)
        
        # Take profit
        profit_order = LimitOrder(stop_action, quantity, take_profit)
        
        # Link orders
        bracket = self.ib.bracketOrder(action, quantity, limit_price or 0, take_profit, stop_loss)
        
        # Place orders
        trades = []
        for order in bracket:
            trade = self.ib.placeOrder(contract, order)
            trades.append(trade)
        
        parent_trade = trades[0]
        
        log.info(f"Order placed: {symbol} {side} {quantity} @ {order_type}")
        
        return {
            "order_id": parent_trade.order.orderId,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "status": parent_trade.orderStatus.status,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def close_position(self, symbol: str, reason: str) -> dict:
        """Close a specific position."""
        self.connect()
        
        # Find position
        for pos in self.ib.positions():
            if pos.contract.symbol == symbol:
                contract = pos.contract
                qty = abs(pos.position)
                side = "SELL" if pos.position > 0 else "BUY"
                
                order = MarketOrder(side, qty)
                trade = self.ib.placeOrder(contract, order)
                
                log.info(f"Closing {symbol}: {reason}")
                
                return {
                    "symbol": symbol,
                    "closed": True,
                    "quantity": qty,
                    "order_id": trade.order.orderId
                }
        
        return {"symbol": symbol, "closed": False, "reason": "Position not found"}
    
    def close_all_positions(self, reason: str) -> dict:
        """Emergency: close all HKEX positions."""
        self.connect()
        
        closed = []
        for pos in self.ib.positions():
            if pos.contract.exchange == "SEHK" and pos.position != 0:
                result = self.close_position(pos.contract.symbol, reason)
                closed.append(result)
        
        log.critical(f"EMERGENCY CLOSE: {len(closed)} positions, reason: {reason}")
        
        return {
            "emergency": True,
            "reason": reason,
            "positions_closed": len(closed),
            "details": closed
        }
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

# Broker
broker:
  name: IBKR
  host: "127.0.0.1"
  port: 7497          # 7497=paper, 7496=live
  client_id: 1

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

# IBKR
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=app-password
ALERT_EMAIL=craig@example.com
```

---

## 6. Cron Schedule

```bash
# /etc/cron.d/catalyst-hkex

# ============================================================================
# CATALYST TRADING - HKEX
# Times in HKT (same as Perth AWST)
# ============================================================================

# Morning Session (9:30 AM - 12:00 PM)
30 9  * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
0  10 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 10 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
0  11 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 11 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1

# Lunch Break: 12:00 - 13:00 (NO TRADING)

# Afternoon Session (1:00 PM - 4:00 PM)
0  13 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 13 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
0  14 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 14 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
0  15 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
30 15 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1

# End of Day (4:30 PM) - Close any remaining positions
30 16 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
```

---

## 7. Deployment

### 7.1 Setup Script

```bash
#!/bin/bash
# setup.sh - Run on fresh $6 droplet

set -e

echo "=== Catalyst International Setup ==="

# Update system
apt update && apt upgrade -y

# Install Python
apt install -y python3 python3-pip python3-venv

# Create user
useradd -m -s /bin/bash catalyst
mkdir -p /opt/catalyst-intl
chown catalyst:catalyst /opt/catalyst-intl

# Create virtual environment
su - catalyst -c "
cd /opt/catalyst-intl
python3 -m venv venv
source venv/bin/activate
pip install anthropic ib_insync asyncpg pyyaml
"

# Create log directory
mkdir -p /var/log/catalyst-intl
chown catalyst:catalyst /var/log/catalyst-intl

# Install cron
cp /opt/catalyst-intl/cron.d/catalyst-hkex /etc/cron.d/
chmod 644 /etc/cron.d/catalyst-hkex

echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Copy code to /opt/catalyst-intl/"
echo "2. Configure /opt/catalyst-intl/config/settings.yaml"
echo "3. Set environment variables"
echo "4. Start IBKR Gateway"
echo "5. Test: /opt/catalyst-intl/agent.py"
```

### 7.2 Deploy Command

```bash
# From local machine
rsync -avz --exclude='venv' --exclude='__pycache__' \
  ./catalyst-international/ \
  root@your-droplet:/opt/catalyst-intl/
```

---

## 8. Cost Summary

### Monthly Costs

| Item | Cost |
|------|------|
| DO Droplet (Basic, 1GB) | $6 |
| DO Managed PostgreSQL (shared) | $0 (already have) |
| Claude API (~200 cycles × 5K tokens) | ~$15-25 |
| IBKR Data (HKEX) | ~$10-20 |
| **Total** | **~$31-51/month** |

### Comparison to US System

| Aspect | US (Microservices) | International (Agent) |
|--------|-------------------|----------------------|
| Droplet | $24/month | $6/month |
| Complexity | 8 containers | 1 script |
| Lines of code | ~5000+ | ~500 |
| Deployment | docker-compose | scp + cron |

---

## 9. Summary

### What We Built

- **1 Python script** that runs via cron
- **Claude API** makes all trading decisions
- **Simple tools** execute the decisions
- **IBKR** handles actual trading
- **Shared database** with US system

### Key Principles

1. **Claude is the brain** - No hardcoded workflow logic
2. **Tools are simple** - Just wrappers around APIs
3. **Safety first** - All actions validated
4. **Minimal infrastructure** - One cheap droplet

### Files to Create

```
catalyst-international/
├── agent.py              # 200 lines
├── tools.py              # 100 lines
├── tool_executor.py      # 100 lines  
├── safety.py             # 80 lines
├── brokers/ibkr.py       # 150 lines
├── data/database.py      # 100 lines
├── data/market.py        # 100 lines
├── config/settings.yaml  # 50 lines
└── setup.sh              # 30 lines
                          ─────────
                          ~900 lines total
```

vs US system: **~5000+ lines across 50+ files**

---

**Document Version:** 2.0.0  
**Architecture:** Simple Droplet + Claude API  
**Monthly Cost:** ~$31-51  
**Lines of Code:** ~900  
**Status:** Ready for Implementation
