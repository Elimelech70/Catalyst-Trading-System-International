# Catalyst Trading System International - Implementation Package

**Name of Application:** Catalyst Trading System International  
**Name of File:** IMPLEMENTATION-PACKAGE-INTERNATIONAL.md  
**Version:** 1.0.0  
**Last Updated:** 2025-12-03  
**Purpose:** Complete context for implementing the International (HKEX) trading system

---

## OVERVIEW

This document contains everything needed to implement the Catalyst Trading System International - an AI agent-based trading system for Hong Kong Stock Exchange (HKEX) using Interactive Brokers.

**Key Decision:** We chose a simple agent architecture over microservices:
- 1 Python script + Claude API (not 8 Docker containers)
- ~900 lines of code (not 5000+)
- $6/month droplet (not $24+)
- Cron-triggered (not always-running services)

---

## PART 1: ARCHITECTURE SUMMARY

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│              DIGITALOCEAN DROPLET ($6/month)                    │
│                                                                 │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────────┐   │
│   │   CRON   │────▶│    AGENT     │────▶│      TOOLS       │   │
│   │          │     │   (Python)   │     │    (Functions)   │   │
│   │ 9:30 AM  │     │              │     │                  │   │
│   │ 10:30 AM │     │ Calls Claude │     │ - scan_market()  │   │
│   │ ...      │     │ Executes     │     │ - detect_patterns│   │
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

### The Agent Loop

```
CRON triggers → Build Context → Call Claude → Claude requests tool 
    → Execute tool → Return result → Claude continues → Loop until done
```

### Comparison to US System

| Aspect | US (Microservices) | International (Agent) |
|--------|-------------------|----------------------|
| Components | 8 Docker containers | 1 Python script |
| Files | 50+ | ~10 |
| Lines of code | 5000+ | ~900 |
| Monthly cost | $24+ droplet | $6 droplet |
| Decision making | Hardcoded workflow | Claude decides dynamically |
| Deployment | docker-compose | scp + crontab |

---

## PART 2: FILE STRUCTURE

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
│   ├── market.py               # Market data + technicals
│   ├── patterns.py             # Pattern detection
│   ├── news.py                 # News/sentiment
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

---

## PART 3: TOOL DEFINITIONS

Claude has access to these 12 tools:

```python
TOOLS = [
    {
        "name": "scan_market",
        "description": "Scan HKEX for trading candidates. Returns top stocks by momentum and volume.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "string", "enum": ["HSI", "HSCEI", "HSTECH", "ALL"]},
                "limit": {"type": "integer", "description": "Max candidates (default 10)"}
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
                "symbol": {"type": "string", "description": "Stock code (e.g., '0700')"}
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
        "name": "detect_patterns",
        "description": "Detect chart patterns: bull_flag, cup_handle, ascending_triangle, ABCD, breakout.",
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
        "name": "check_risk",
        "description": "Validate trade against risk limits. MUST call before execute_trade.",
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
        "description": "Execute trade via IBKR. Only call after check_risk approves.",
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
                "reason": {"type": "string", "description": "Why this trade (audit)"}
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
        "description": "Log decision to database for audit trail.",
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

---

## PART 4: SYSTEM PROMPT

```markdown
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

## Current Context
Exchange: HKEX
Currency: HKD  
Lot Size: 100 shares (board lots)
Timezone: Asia/Hong_Kong (UTC+8)
Broker: Interactive Brokers
Mode: Paper Trading
```

---

## PART 5: DATABASE (SHARED WITH US)

The international system shares the same PostgreSQL database as the US system. Key changes needed:

### New Table: exchanges

```sql
CREATE TABLE exchanges (
    exchange_id SERIAL PRIMARY KEY,
    exchange_code VARCHAR(10) UNIQUE NOT NULL,  -- 'NYSE', 'HKEX'
    exchange_name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL,
    currency VARCHAR(3) NOT NULL,               -- 'USD', 'HKD'
    timezone VARCHAR(50) NOT NULL,              -- 'America/New_York', 'Asia/Hong_Kong'
    market_open TIME NOT NULL,
    market_close TIME NOT NULL,
    has_lunch_break BOOLEAN DEFAULT FALSE,
    lunch_start TIME,
    lunch_end TIME,
    default_lot_size INTEGER DEFAULT 1,
    broker_code VARCHAR(20),                    -- 'ALPACA', 'IBKR'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed data
INSERT INTO exchanges (exchange_code, exchange_name, country, currency, timezone, 
                       market_open, market_close, has_lunch_break, lunch_start, 
                       lunch_end, default_lot_size, broker_code) VALUES
('NYSE', 'New York Stock Exchange', 'United States', 'USD', 'America/New_York',
 '09:30', '16:00', FALSE, NULL, NULL, 1, 'ALPACA'),
('HKEX', 'Hong Kong Stock Exchange', 'Hong Kong', 'HKD', 'Asia/Hong_Kong',
 '09:30', '16:00', TRUE, '12:00', '13:00', 100, 'IBKR');
```

### Column Renames (US system compatibility)

```sql
-- Rename alpaca-specific columns to generic broker columns
ALTER TABLE positions RENAME COLUMN alpaca_order_id TO broker_order_id;
ALTER TABLE positions RENAME COLUMN alpaca_status TO broker_status;
ALTER TABLE positions RENAME COLUMN alpaca_error TO broker_error;

-- Add new columns
ALTER TABLE positions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
ALTER TABLE positions ADD COLUMN broker_code VARCHAR(20) DEFAULT 'ALPACA';

ALTER TABLE trading_cycles ADD COLUMN exchange_id INTEGER REFERENCES exchanges(exchange_id);
ALTER TABLE trading_cycles ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';

ALTER TABLE securities ADD COLUMN exchange_id INTEGER REFERENCES exchanges(exchange_id);
```

### Agent-Specific Tables

```sql
-- Agent decision audit log
CREATE TABLE agent_decisions (
    decision_id SERIAL PRIMARY KEY,
    cycle_id VARCHAR(50) NOT NULL,
    exchange_id INTEGER REFERENCES exchanges(exchange_id),
    decision_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(20),
    reasoning TEXT NOT NULL,
    tools_called JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent cycle logs
CREATE TABLE agent_cycles (
    cycle_id VARCHAR(50) PRIMARY KEY,
    exchange_id INTEGER REFERENCES exchanges(exchange_id),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,
    tools_called JSONB,
    trades_executed INTEGER DEFAULT 0,
    api_tokens_used INTEGER,
    api_cost_usd DECIMAL(10, 4),
    final_response TEXT,
    error TEXT
);
```

---

## PART 6: CONFIGURATION

### settings.yaml

```yaml
# Exchange
exchange:
  code: HKEX
  currency: HKD
  timezone: Asia/Hong_Kong
  lot_size: 100
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
  max_position_pct: 0.20
  max_daily_loss_pct: 0.02
  warning_loss_pct: 0.015
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

# Database (shared with US)
database:
  host: "${DB_HOST}"
  port: 5432
  name: "catalyst_trading"
  user: "${DB_USER}"
  password: "${DB_PASSWORD}"
```

### Environment Variables

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Database (shared with US)
DB_HOST=your-db.db.ondigitalocean.com
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

## PART 7: CRON SCHEDULE

```bash
# /etc/cron.d/catalyst-hkex
# Times in HKT (same as Perth AWST)

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

# End of Day (4:30 PM)
30 16 * * 1-5  catalyst /opt/catalyst-intl/agent.py >> /var/log/catalyst-intl/cron.log 2>&1
```

---

## PART 8: COST SUMMARY

| Item | Monthly Cost |
|------|-------------|
| DO Droplet (1GB) | $6 |
| Claude API (~200 cycles × 5K tokens) | ~$15-25 |
| IBKR Data Feed (HKEX) | ~$10-20 |
| **Total** | **~$31-51/month** |

---

## PART 9: IMPLEMENTATION CHECKLIST

### Phase 1: Setup (Day 1)
- [ ] Create GitHub repo: `catalyst-trading-system-international`
- [ ] Create $6 DigitalOcean droplet
- [ ] Install Python 3.11+
- [ ] Clone repo to droplet

### Phase 2: Database (Day 1)
- [ ] Run migration to add `exchanges` table
- [ ] Rename `alpaca_*` columns to `broker_*`
- [ ] Add `exchange_id` to relevant tables
- [ ] Add agent-specific tables

### Phase 3: Core Agent (Day 2-3)
- [ ] Implement `agent.py` (main loop)
- [ ] Implement `tools.py` (definitions)
- [ ] Implement `tool_executor.py` (routing)
- [ ] Implement `safety.py` (validation)

### Phase 4: Data Layer (Day 3-4)
- [ ] Implement `data/database.py`
- [ ] Implement `data/market.py`
- [ ] Implement `data/patterns.py`
- [ ] Implement `data/news.py`

### Phase 5: Broker (Day 4-5)
- [ ] Set up IBKR Gateway on droplet
- [ ] Implement `brokers/ibkr.py`
- [ ] Test paper trading connection

### Phase 6: Testing (Day 5-6)
- [ ] Test each tool individually
- [ ] Test full agent cycle
- [ ] Test safety layer blocks
- [ ] Test email alerts

### Phase 7: Go Live (Day 7)
- [ ] Configure cron jobs
- [ ] Monitor first few cycles
- [ ] Verify database logging

---

## PART 10: KEY FILES TO IMPLEMENT

Priority order for implementation:

1. **agent.py** - Main agent loop (~200 lines)
2. **tools.py** - Tool definitions (~100 lines)
3. **tool_executor.py** - Route tool calls (~150 lines)
4. **safety.py** - Validate actions (~100 lines)
5. **data/database.py** - PostgreSQL client (~150 lines)
6. **brokers/ibkr.py** - IBKR client (~200 lines)
7. **data/market.py** - Market data + technicals (~150 lines)
8. **data/patterns.py** - Pattern detection (~100 lines)
9. **data/news.py** - News/sentiment (~100 lines)
10. **config/settings.yaml** - Configuration (~50 lines)

**Total: ~1300 lines** (lean and focused)

---

## PART 11: EXISTING US SYSTEM CONTEXT

The US system uses these microservices (for reference, NOT to copy):
- Scanner Service (port 5001)
- Pattern Detection (port 5002)
- Technical Analysis (port 5003)
- Risk Manager (port 5004)
- Trading Service (port 5005)
- Workflow Coordinator (port 5006)
- PostgreSQL (port 5432)
- Redis (port 6379)

The International system replaces ALL of these with:
- 1 agent.py script
- Claude API (external)
- Same PostgreSQL (shared)

---

## PART 12: NEXT STEPS FOR NEW CONVERSATION

When starting a new conversation, provide this context:

> "I'm implementing the Catalyst Trading System International for HKEX. 
> We're using an AI agent architecture (not microservices like the US system).
> Please review the IMPLEMENTATION-PACKAGE-INTERNATIONAL.md for full context.
> I need help implementing [specific file/feature]."

### Files to Request

1. "Implement agent.py - the main agent loop"
2. "Implement brokers/ibkr.py - the IBKR client"
3. "Implement data/patterns.py - pattern detection"
4. "Implement the database migration SQL"

---

**Document Created:** 2025-12-03  
**Status:** Ready for Implementation  
**Architecture:** AI Agent (Simple Droplet + Claude API)  
**Target:** HKEX via Interactive Brokers  
**Monthly Cost:** ~$31-51
