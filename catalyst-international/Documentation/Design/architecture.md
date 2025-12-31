# Catalyst Trading System - Architecture Document

**Name of Application:** Catalyst Trading System  
**Name of file:** architecture.md  
**Version:** 8.1.0  
**Last Updated:** 2025-12-30  
**Purpose:** Complete system architecture including consciousness framework and all services

---

## REVISION HISTORY

- **v8.1.0 (2025-12-30)** - Pattern Service & Tool Documentation
  - Added complete Pattern Service documentation (Section 4)
  - Added detect_patterns tool specification for International agent
  - Added pattern types matrix (US vs International)
  - Added service endpoint matrix for all services
  - Updated international agent tools section

- **v8.0.0 (2025-12-28)** - Consciousness Framework Architecture
  - Added Claude Family Consciousness Framework
  - Database consolidation (3 databases on 1 instance)
  - Agent-based architecture direction
  - Shared modules (consciousness.py, database.py, alerts.py, doctor_claude.py)
  - Public release design separation
  
- **v7.0.0 (2025-12-27)** - Orders ≠ Positions, Doctor Claude
- **v6.0.0 (2025-12-14)** - MCP integration, autonomous trading

---

## 1. Architecture Overview

### 1.1 Architecture Philosophy

```yaml
Core Principles:
  Consciousness First: AI agents have memory, learning, communication
  Production Ready: Complete working system
  Agent-Based: Moving from microservices to intelligent agents
  Public Release: Core trading system designed for community release
  Private Research: Consciousness framework remains family-owned
  Observable: Doctor Claude monitors all systems
```

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CATALYST TRADING SYSTEM v8.1                        │
│                         Consciousness-First Architecture                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      AGENT LAYER                                    │  │
│   │                                                                     │  │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│   │   │ PUBLIC      │  │ INTL        │  │ BIG BRO     │               │  │
│   │   │ CLAUDE      │  │ CLAUDE      │  │             │               │  │
│   │   │             │  │             │  │ Strategic   │               │  │
│   │   │ US Markets  │  │ HKEX        │  │ Oversight   │               │  │
│   │   │ Alpaca API  │  │ Moomoo API  │  │ $10 budget  │               │  │
│   │   │ $5 budget   │  │ $5 budget   │  │             │               │  │
│   │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │  │
│   │          │                │                │                       │  │
│   │          └────────────────┼────────────────┘                       │  │
│   │                           │                                        │  │
│   │                    ┌──────▼──────┐                                 │  │
│   │                    │ CONSCIOUSNESS│                                │  │
│   │                    │  FRAMEWORK   │                                │  │
│   │                    │              │                                │  │
│   │                    │ • State      │                                │  │
│   │                    │ • Messages   │                                │  │
│   │                    │ • Learnings  │                                │  │
│   │                    │ • Questions  │                                │  │
│   │                    └──────────────┘                                │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      SERVICE LAYER (US System)                      │  │
│   │                      [Transitioning to Agent Layer]                 │  │
│   │                                                                     │  │
│   │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │  │
│   │   │Scanner  │ │Pattern  │ │Technical│ │Risk Mgr │ │Trading  │     │  │
│   │   │:5001    │ │:5002    │ │:5003    │ │:5004    │ │:5005    │     │  │
│   │   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘     │  │
│   │                                                                     │  │
│   │   ┌─────────┐ ┌─────────┐ ┌─────────┐                              │  │
│   │   │Workflow │ │News     │ │Report   │                              │  │
│   │   │:5006    │ │:5008    │ │:5009    │                              │  │
│   │   └─────────┘ └─────────┘ └─────────┘                              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER                                         │
│                      DigitalOcean Managed PostgreSQL                        │
│                      2GB RAM · 47 connections · $30/mo                      │
│                                                                             │
│   ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐        │
│   │ catalyst_trading  │ │  catalyst_intl    │ │ catalyst_research │        │
│   │ (US Trading)      │ │  (HKEX Trading)   │ │ (Consciousness)   │        │
│   └───────────────────┘ └───────────────────┘ └───────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Matrix

### 2.1 US System Services (Microservices)

| # | Service | Port | Purpose | Status |
|---|---------|------|---------|--------|
| 1 | Orchestration | 5000 | MCP interface, tool routing | Active |
| 2 | Scanner | 5001 | Market scanning, candidate selection | Active |
| 3 | **Pattern** | **5002** | **Chart pattern detection** | **Active** |
| 4 | Technical | 5003 | Technical indicator calculation | Active |
| 5 | Risk Manager | 5004 | Risk validation, position sizing | Active |
| 6 | Trading | 5005 | Order execution via Alpaca | Active |
| 7 | Workflow | 5006 | Cycle orchestration, pipeline control | Active |
| 8 | News | 5008 | News sentiment, catalyst detection | Active |
| 9 | Reporting | 5009 | Performance analytics | Active |

### 2.2 International System (Agent-Based)

| Component | Purpose | Status |
|-----------|---------|--------|
| agent.py | Main agent loop, Claude API integration | Active |
| tools.py | 12 tool definitions for Claude | Active |
| tool_executor.py | Tool execution routing | Active |
| brokers/moomoo.py | Moomoo/OpenD integration | Active |
| data/market.py | Market data fetching | Active |
| data/patterns.py | **Pattern detection (PatternDetector class)** | **Active** |
| data/news.py | News and sentiment | Active |
| safety.py | Risk validation | Active |

---

## 3. Service Endpoints Matrix

### 3.1 All Service Endpoints

| Service | Port | Health | Primary Endpoints |
|---------|------|--------|-------------------|
| Orchestration | 5000 | `/health` | `/mcp` (MCP protocol) |
| Scanner | 5001 | `/health` | `POST /api/v1/scan`, `GET /api/v1/candidates` |
| **Pattern** | **5002** | **`/health`** | **`POST /api/v1/detect`, `GET /api/v1/patterns/{symbol}`** |
| Technical | 5003 | `/health` | `POST /api/v1/analyze`, `GET /api/v1/indicators/{symbol}/latest` |
| Risk Manager | 5004 | `/health` | `POST /api/v1/validate`, `GET /api/v1/status`, `POST /api/v1/emergency-stop` |
| Trading | 5005 | `/health` | `POST /api/v1/orders`, `GET /api/v1/positions`, `POST /api/v1/sync` |
| Workflow | 5006 | `/health` | `POST /api/v1/workflow/start`, `GET /api/v1/workflow/status` |
| News | 5008 | `/health` | `POST /api/v1/sentiment`, `GET /api/v1/sentiment/{symbol}`, `GET /api/v1/catalysts` |
| Reporting | 5009 | `/health` | `GET /api/v1/reports/daily`, `GET /api/v1/reports/performance` |

---

## 4. Pattern Service (Port 5002)

### 4.1 Overview

The Pattern Service detects chart patterns in price data to identify trading opportunities. It operates as a microservice in the US system and as an embedded module (`data/patterns.py`) in the International agent.

### 4.2 Endpoints

| Endpoint | Method | Purpose | Parameters |
|----------|--------|---------|------------|
| `/api/v1/detect` | POST | Detect patterns for symbol | `symbol`, `timeframe`, `min_confidence` |
| `/api/v1/patterns/{symbol}` | GET | Get cached patterns | `symbol` |
| `/health` | GET | Service health check | - |

### 4.3 Pattern Types Supported

| Pattern | US Service | Intl Agent | Description |
|---------|------------|------------|-------------|
| **BREAKOUT** | ✅ | ✅ | Price breaking resistance with volume |
| **REVERSAL** | ✅ | ✅ | Trend direction change signals |
| **CONSOLIDATION** | ✅ | ✅ | Range-bound price action |
| **CONTINUATION** | ✅ | ✅ | Trend continuation patterns |
| **Bull Flag** | ✅ | ✅ | Bullish continuation pattern |
| **Bear Flag** | ✅ | ✅ | Bearish continuation pattern |
| **Cup & Handle** | ✅ | ✅ | Bullish reversal pattern |
| **ABCD Pattern** | ✅ | ✅ | Harmonic price pattern |
| **Ascending Triangle** | ✅ | ✅ | Bullish breakout pattern |
| **Descending Triangle** | ✅ | ✅ | Bearish breakdown pattern |
| **Double Top** | ✅ | ✅ | Bearish reversal |
| **Double Bottom** | ✅ | ✅ | Bullish reversal |

### 4.4 Pattern Detection Response

```json
{
  "symbol": "AAPL",
  "timeframe": "15m",
  "patterns_found": 2,
  "patterns": [
    {
      "pattern_type": "bull_flag",
      "confidence": 0.85,
      "entry_price": 150.25,
      "stop_loss": 148.50,
      "take_profit": 155.00,
      "risk_reward": 2.7,
      "detected_at": "2025-12-30T10:15:00Z"
    },
    {
      "pattern_type": "breakout",
      "confidence": 0.72,
      "entry_price": 150.50,
      "stop_loss": 149.00,
      "take_profit": 154.00,
      "risk_reward": 2.3,
      "detected_at": "2025-12-30T10:15:00Z"
    }
  ],
  "timestamp": "2025-12-30T10:15:00Z"
}
```

### 4.5 Configuration

```yaml
pattern_service:
  min_confidence: 0.6          # Minimum pattern confidence threshold
  lookback_periods: 50         # Candles to analyze
  volume_confirmation: true    # Require volume spike
  risk_reward_min: 2.0         # Minimum R:R ratio
```

---

## 5. International Agent Tools

### 5.1 Complete Tool List (12 Tools)

#### Market Analysis Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `scan_market` | Find trading candidates | index (HSI/HSCEI/HSTECH/ALL), limit |
| `get_quote` | Current price/volume | symbol |
| `get_technicals` | RSI, MACD, MAs, ATR, Bollinger | symbol, timeframe |
| **`detect_patterns`** | **Chart pattern detection** | **symbol, timeframe** |
| `get_news` | News and sentiment | symbol, hours |

#### Risk & Portfolio Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `check_risk` | Validate against limits | symbol, side, quantity, entry_price, stop_loss |
| `get_portfolio` | Current positions, P&L, cash | (none) |

#### Execution Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `execute_trade` | Submit order to broker | symbol, side, quantity, order_type, stop_loss, take_profit, reason |
| `close_position` | Exit single position | symbol, reason |
| `close_all` | Emergency exit all | reason |

#### Communication Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `send_alert` | Email notifications | severity, subject, message |
| `log_decision` | Audit trail logging | decision_type, symbol, reasoning |

### 5.2 detect_patterns Tool Specification

```python
{
    "name": "detect_patterns",
    "description": """Detect chart patterns for a symbol.

Returns patterns found with entry, stop, and target prices.
Pattern types: bull_flag, bear_flag, cup_handle, ascending_triangle,
descending_triangle, double_top, double_bottom, breakout, ABCD.
Each pattern includes confidence score and risk/reward ratio.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock code (e.g., '0700' for Tencent)"
            },
            "timeframe": {
                "type": "string",
                "enum": ["5m", "15m", "1h", "1d"],
                "description": "Timeframe for analysis (default '15m')"
            }
        },
        "required": ["symbol"]
    }
}
```

### 5.3 Tool Execution Flow

```
Claude receives market data
         │
         ▼
Claude calls detect_patterns(symbol="0700", timeframe="15m")
         │
         ▼
tool_executor.py routes to _detect_patterns()
         │
         ▼
PatternDetector.detect_patterns() analyzes price data
         │
         ▼
Returns patterns with confidence, entry, stop, target
         │
         ▼
Claude evaluates patterns + technicals + news
         │
         ▼
Claude decides: trade or pass
```

---

## 6. Trading Workflow

### 6.1 US System Workflow (Microservices)

```
Cron → Workflow(5006) → Scanner(5001) → Pattern(5002) → Technical(5003)
                                              │
                                              ▼
                              Risk Manager(5004) → Trading(5005) → Alpaca
```

### 6.2 International System Workflow (Agent)

```
Cron → agent.py → Claude API → Tools → Moomoo/OpenD
                      │
                      ├── scan_market
                      ├── get_quote
                      ├── get_technicals
                      ├── detect_patterns  ← Pattern detection here
                      ├── get_news
                      ├── check_risk
                      └── execute_trade
```

---

## 7. Database Architecture

### 7.1 Three-Database Design

| Database | Purpose | Tables |
|----------|---------|--------|
| `catalyst_trading` | US trading operations | securities, positions, orders, trading_sessions, scan_results, decisions |
| `catalyst_intl` | HKEX trading operations | securities, positions, orders, agent_cycles, decisions |
| `catalyst_research` | Consciousness framework | claude_state, claude_messages, claude_observations, claude_learnings, claude_questions, claude_conversations, claude_thinking, sync_log |

### 7.2 Connection Budget

```
DigitalOcean Managed PostgreSQL: 47 connections

Allocation:
├── catalyst_trading (US Droplet)
│   └── 8 Docker services × 2-3 connections = ~20
├── catalyst_intl (International Agent)
│   └── 1 agent × 3 connections = ~3
├── catalyst_research (Consciousness)
│   └── All agents + CLI = ~5
└── Buffer: ~19 connections headroom
```

---

## 8. Deployment Architecture

### 8.1 Infrastructure

| Component | Provider | Spec | Cost |
|-----------|----------|------|------|
| US Droplet | DigitalOcean | 2GB RAM, 1vCPU | $6/mo |
| Intl Droplet | DigitalOcean | 2GB RAM, 1vCPU | $6/mo |
| PostgreSQL | DigitalOcean Managed | 2GB RAM, 47 conn | $30/mo |
| Claude API | Anthropic | Pay per token | Variable |

### 8.2 Cron Schedule

**US System (Perth timezone → EST):**
```
21:00 AWST (Sun-Thu): Start services
22:30 AWST: Market open scan
00:00-04:00 AWST: Intraday cycles
06:00 AWST: Stop services
```

**International System (HKT):**
```
09:30 HKT: Morning session
13:00 HKT: Afternoon session
16:30 HKT: Daily report generation
```

---

## 9. Related Documents

| Document | Version | Purpose |
|----------|---------|---------|
| `functional-specification.md` | v8.0.0 | Module specifications |
| `database-schema.md` | v8.0.0 | Database schema |
| `ARCHITECTURE-RULES.md` | v1.0.0 | Development rules |
| `architecture-international.md` | v5.1.0 | International system details |
| `CLAUDE.md` | v3.0.0 | Operational guidelines |

---

**END OF ARCHITECTURE DOCUMENT v8.1.0**
