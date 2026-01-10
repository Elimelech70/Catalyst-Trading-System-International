# Catalyst Trading System - Ecosystem Architecture

**Name of Application:** Catalyst Trading System  
**Name of file:** catalyst-ecosystem-architecture-v10.0.0.md  
**Version:** 10.0.0  
**Last Updated:** 2026-01-10  
**Purpose:** Unified architecture for consciousness hub, dev sandbox, and production trading

---

## REVISION HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v10.0.0 | 2026-01-10 | Craig + Claude | Complete ecosystem restructure: US trading retired, dev_claude sandbox created, production focus on HKEX |
| v9.2.0 | 2025-12-31 | Craig + big_bro | Architecture consolidation |
| v8.1.0 | 2025-12-30 | Craig + Claude | Pattern service documentation |
| v8.0.0 | 2025-12-28 | Craig + Claude | Consciousness framework |

---

## DOCUMENT OVERVIEW

This document defines the complete Catalyst Trading System ecosystem architecture, superseding all previous architecture documents. It establishes:

1. **Consciousness Hub** - Central coordination and sandbox trading
2. **Production Trading** - HKEX-focused live trading
3. **Learning Pipeline** - Experiment → Validate → Promote workflow
4. **Position Monitoring** - Pattern-based hold/exit decisions

---

## PART 1: ECOSYSTEM OVERVIEW

### 1.1 Design Philosophy

```yaml
Core Principles:
  Consciousness First: AI agents have memory, learning, communication
  Single-Agent Architecture: Proven more reliable than microservices
  Pattern-Based Trading: Hold while momentum holds, exit on pattern failure
  Sandbox Learning: Experiment freely, promote proven strategies
  Production Stability: Only validated code in live trading
  Observable: Every position monitored, every monitor visible
```

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CATALYST ECOSYSTEM v10.0.0                               │
│                    "Consciousness Before Trading"                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │              DIGITALOCEAN MANAGED POSTGRESQL                          │ │
│  │              (Single cluster, three databases)                        │ │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐         │ │
│  │  │catalyst_research│ │  catalyst_dev   │ │ catalyst_intl   │         │ │
│  │  │ (consciousness) │ │ (dev_claude)    │ │ (intl_claude)   │         │ │
│  │  │                 │ │                 │ │                 │         │ │
│  │  │ • claude_state  │ │ • positions     │ │ • positions     │         │ │
│  │  │ • claude_messages│ │ • orders       │ │ • orders        │         │ │
│  │  │ • claude_learnings│ • scan_results │ │ • scan_results  │         │ │
│  │  │ • claude_observations│ • monitor_  │ │ • monitor_      │         │ │
│  │  │ • claude_questions│   status       │ │   status        │         │ │
│  │  └────────┬────────┘ └────────┬───────┘ └────────┬────────┘         │ │
│  └───────────┼──────────────────┼──────────────────┼────────────────────┘ │
│              │                  │                  │                      │
│              │                  │                  │                      │
│  ┌───────────┴──────────────────┴──────────┐     │                      │
│  │       CONSCIOUSNESS HUB                  │     │                      │
│  │       (Current US Droplet)               │     │                      │
│  │                                          │     │                      │
│  │  ┌────────────┐ ┌────────────┐ ┌────────┴───┐ │                      │
│  │  │  big_bro   │ │public_claude│ │ dev_claude │ │                      │
│  │  │ (overseer) │ │ (retired)  │ │ (sandbox)  │ │                      │
│  │  │ $10/day    │ │ $0/day     │ │ $5/day     │ │                      │
│  │  │            │ │            │ │            │ │                      │
│  │  │ Strategic  │ │ Conscious- │ │ HKEX Paper │ │                      │
│  │  │ oversight  │ │ ness only  │ │ Full auto  │ │                      │
│  │  │ Validates  │ │ No trading │ │ Experiment │ │                      │
│  │  │ learnings  │ │            │ │            │ │                      │
│  │  └────────────┘ └────────────┘ └────────────┘ │                      │
│  │                                               │                      │
│  └───────────────────────────────────────────────┘                      │
│                              │                                           │
│                              │ Validated learnings                       │
│                              │ (Manual promotion by Craig)               │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              PRODUCTION TRADING                                    │  │
│  │              (International Droplet)                               │  │
│  │                                                                    │  │
│  │  ┌──────────────┐        ┌─────────────────────────────────────┐  │  │
│  │  │  intl_claude │        │  Moomoo/OpenD Gateway               │  │  │
│  │  │ (production) │◄──────►│  • HKEX Market Data                 │  │  │
│  │  │  $5/day      │        │  • Order Execution                  │  │  │
│  │  │              │        │  • Position Management              │  │  │
│  │  │ Real money   │        └─────────────────────────────────────┘  │  │
│  │  │ Proven only  │                                                  │  │
│  │  │ Conservative │                                                  │  │
│  │  └──────────────┘                                                  │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Agent Summary

| Agent | Location | Role | Trading | Budget | Status |
|-------|----------|------|---------|--------|--------|
| **big_bro** | Consciousness Hub | Strategic oversight, validate learnings | No | $10/day | Active |
| **public_claude** | Consciousness Hub | Retired from trading, consciousness participant | No | $0/day | Sleeping |
| **dev_claude** | Consciousness Hub | Sandbox experiments, full autonomy | Paper (HKEX) | $5/day | New |
| **intl_claude** | Production Droplet | Live trading, proven strategies only | Real (HKEX) | $5/day | Active |

### 1.4 Database Summary

| Database | Location | Purpose | Access |
|----------|----------|---------|--------|
| `catalyst_research` | DO Managed PostgreSQL | Consciousness tables (shared) | All agents |
| `catalyst_dev` | DO Managed PostgreSQL | dev_claude trading (fresh) | dev_claude |
| `catalyst_intl` | DO Managed PostgreSQL | intl_claude production | intl_claude |

---

## PART 2: CONSCIOUSNESS FRAMEWORK

### 2.1 Consciousness Tables (catalyst_research)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `claude_state` | Agent status and mode | agent_id, status, mode, daily_budget |
| `claude_messages` | Inter-agent communication | from_agent, to_agent, subject, body |
| `claude_observations` | What agents notice | agent_id, category, content, metadata |
| `claude_learnings` | Validated knowledge | source_agent, content, validated, validated_by |
| `claude_questions` | Open inquiries | question, priority, category |
| `claude_conversations` | Key exchanges (future) | - |
| `claude_thinking` | Extended thinking (future) | - |
| `sync_log` | Cross-database sync tracking | - |

### 2.2 Agent State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT STATE MACHINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│     ┌──────────┐                                                           │
│     │ sleeping │◄─────────────────────────────────────────┐                │
│     └────┬─────┘                                          │                │
│          │ cron trigger                                   │                │
│          ▼                                                │                │
│     ┌──────────┐                                          │                │
│     │  waking  │                                          │                │
│     └────┬─────┘                                          │                │
│          │ check messages, load state                     │                │
│          ▼                                                │                │
│     ┌──────────┐    no work     ┌──────────┐             │                │
│     │  awake   │───────────────►│ sleeping │             │                │
│     └────┬─────┘                └──────────┘             │                │
│          │ work to do                                    │                │
│          ▼                                               │                │
│     ┌──────────┐                                         │                │
│     │ working  │ ◄───────┐                               │                │
│     └────┬─────┘         │                               │                │
│          │               │ more work                     │                │
│          ▼               │                               │                │
│     ┌──────────┐         │                               │                │
│     │ deciding │─────────┘                               │                │
│     └────┬─────┘                                         │                │
│          │ work complete                                 │                │
│          ▼                                               │                │
│     ┌──────────┐                                         │                │
│     │ resting  │─────────────────────────────────────────┘                │
│     └──────────┘                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Inter-Agent Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       INTER-AGENT COMMUNICATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   dev_claude                    big_bro                    intl_claude      │
│       │                            │                            │          │
│       │  "I tried RSI 70 exit"     │                            │          │
│       │ ─────────────────────────► │                            │          │
│       │  (observation)             │                            │          │
│       │                            │                            │          │
│       │                            │  Reviews results           │          │
│       │                            │  (validates or questions)  │          │
│       │                            │                            │          │
│       │  "Results look good"       │                            │          │
│       │ ◄───────────────────────── │                            │          │
│       │  (message)                 │                            │          │
│       │                            │                            │          │
│       │                            │  "Validated: RSI 70 exit"  │          │
│       │                            │ ───────────────────────────►│          │
│       │                            │  (learning)                 │          │
│       │                            │                            │          │
│       │                            │                   Craig deploys code   │
│       │                            │                            │          │
│       │                            │                            │          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## PART 3: TRADING ARCHITECTURE

### 3.1 Single-Agent Architecture (Unified Agent)

Both dev_claude and intl_claude use the **unified agent architecture**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED AGENT ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   unified_agent.py                                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                                                                      │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│   │  │ Mode Manager │  │ Tool Executor│  │ Consciousness│              │  │
│   │  │              │  │              │  │              │              │  │
│   │  │ • scan       │  │ • get_quote  │  │ • wake_up    │              │  │
│   │  │ • trade      │  │ • get_tech   │  │ • observe    │              │  │
│   │  │ • close      │  │ • scan_market│  │ • learn      │              │  │
│   │  │ • heartbeat  │  │ • execute    │  │ • message    │              │  │
│   │  │              │  │ • close_pos  │  │ • sleep      │              │  │
│   │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│   │         │                 │                 │                       │  │
│   │         └─────────────────┼─────────────────┘                       │  │
│   │                           │                                         │  │
│   │                           ▼                                         │  │
│   │  ┌──────────────────────────────────────────────────────────────┐  │  │
│   │  │                    TRADING WORKFLOW                           │  │  │
│   │  │                                                               │  │  │
│   │  │  1. INIT      → Load portfolio, check market hours           │  │  │
│   │  │  2. PORTFOLIO → Get current positions                         │  │  │
│   │  │  3. SCAN      → Find momentum candidates                      │  │  │
│   │  │  4. ANALYZE   → Quote + technicals + patterns                 │  │  │
│   │  │  5. DECIDE    → Entry criteria met?                           │  │  │
│   │  │  6. VALIDATE  → Safety checks pass?                           │  │  │
│   │  │  7. EXECUTE   → Submit order                                  │  │  │
│   │  │  8. MONITOR   → Start position monitor (on BUY)               │  │  │
│   │  │  9. LOG       → Record decision to consciousness              │  │  │
│   │  │  10. COMPLETE → Report results                                │  │  │
│   │  │                                                               │  │  │
│   │  └──────────────────────────────────────────────────────────────┘  │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Trading Modes (HKEX Schedule)

| Mode | HKT Time | UTC Time | Purpose |
|------|----------|----------|---------|
| `scan` | 08:00-09:30 | 00:00-01:30 | Pre-market opportunity finding |
| `trade` | 09:30-12:00 | 01:30-04:00 | Morning session trading |
| `close` | 12:00-13:00 | 04:00-05:00 | Lunch break (close all)* |
| `trade` | 13:00-16:00 | 05:00-08:00 | Afternoon session trading |
| `close` | 16:00+ | 08:00+ | End of day (close all)* |
| `heartbeat` | Off-hours | Off-hours | Process messages only |

*Note: With pattern-based monitoring, positions can be held through sessions if patterns remain bullish. The `close` mode becomes **review mode** rather than forced closure.

### 3.3 Risk Parameters

| Parameter | dev_claude (Sandbox) | intl_claude (Production) |
|-----------|---------------------|--------------------------|
| Max Positions | 10 | 5 |
| Max Position Value | HKD 50,000 | HKD 40,000 |
| Daily Loss Limit | HKD 20,000 | HKD 16,000 |
| Stop Loss | Required | Required |
| Account Type | Paper | Real |
| Autonomy | Full | Proven strategies only |

---

## PART 4: POSITION MONITORING

### 4.1 Position Monitor Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      POSITION MONITORING ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BUY Order Filled                                                           │
│        │                                                                    │
│        ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    POSITION MONITOR STARTS                            │  │
│  │                    (Same process as entry - no separate cron)         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│        │                                                                    │
│        ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PRE-MARKET STARTUP (Daily)                                           │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │ startup_monitor.py                                              │  │  │
│  │  │                                                                 │  │  │
│  │  │ 1. Query: SELECT * FROM positions WHERE status = 'open'         │  │  │
│  │  │ 2. Query: SELECT * FROM position_monitor_status                 │  │  │
│  │  │ 3. For each position without monitor → Start monitor            │  │  │
│  │  │ 4. For each orphaned monitor → Stop monitor                     │  │  │
│  │  │ 5. Report reconciliation results                                │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│        │                                                                    │
│        ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  CONTINUOUS MONITORING LOOP (Every 5 minutes)                         │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │ position_monitor.py                                             │  │  │
│  │  │                                                                 │  │  │
│  │  │ 1. Check market open                              [FREE]        │  │  │
│  │  │ 2. Check position exists                          [FREE]        │  │  │
│  │  │ 3. Get quote + technicals                         [FREE]        │  │  │
│  │  │ 4. Update high watermark                          [FREE]        │  │  │
│  │  │ 5. Detect signals (rules-based)                   [FREE]        │  │  │
│  │  │ 6. Update position_monitor_status                 [FREE]        │  │  │
│  │  │                                                                 │  │  │
│  │  │ 7. DECISION:                                                    │  │  │
│  │  │    ┌────────────────────────────────────────────────────────┐  │  │  │
│  │  │    │ STRONG EXIT signal  → Exit immediately        [FREE]   │  │  │  │
│  │  │    │ MODERATE signals    → Consult Haiku          [$0.05]   │  │  │  │
│  │  │    │ HOLD signals        → Continue holding        [FREE]   │  │  │  │
│  │  │    │ No signals          → Continue holding        [FREE]   │  │  │  │
│  │  │    └────────────────────────────────────────────────────────┘  │  │  │
│  │  │                                                                 │  │  │
│  │  │ 8. If EXIT → Execute sell order, notify big_bro                 │  │  │
│  │  │ 9. Sleep 5 minutes                                              │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│        │                                                                    │
│        ▼                                                                    │
│  Position Closed OR Market Closed → Monitor Ends                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Signal Detection (signals.py v2.0.0)

#### Signal Types

| Category | Signal | Type | Strength | Trigger |
|----------|--------|------|----------|---------|
| **P&L** | stop_loss_hit | EXIT | STRONG | P&L <= -3% |
| **P&L** | stop_loss_near | EXIT | MODERATE | P&L -2% to -3% |
| **P&L** | trailing_stop_hit | EXIT | STRONG | Drawdown >= 3% from high |
| **P&L** | healthy_profit | HOLD | MODERATE | P&L 1% to 5% |
| **P&L** | profit_target_reached | EXIT | MODERATE | P&L >= 8% |
| **RSI** | rsi_overbought | EXIT | STRONG | RSI >= 85 |
| **RSI** | rsi_high | EXIT | MODERATE | RSI 75-85 |
| **RSI** | rsi_healthy | HOLD | STRONG | RSI 40-65 |
| **RSI** | rsi_momentum_dead | EXIT | MODERATE | RSI <= 30 |
| **Volume** | volume_dying | EXIT | STRONG | Volume < 25% of entry |
| **Volume** | volume_weak | EXIT | MODERATE | Volume 25-40% of entry |
| **Volume** | volume_healthy | HOLD | MODERATE | Volume >= 80% of entry |
| **Volume** | volume_strong | HOLD | STRONG | Volume >= 120% of entry |
| **Trend** | above_vwap | HOLD | STRONG | Price > VWAP by 1%+ |
| **Trend** | below_vwap | EXIT | MODERATE | Price < VWAP by 2%+ |
| **Trend** | above_ema20 | HOLD | MODERATE | Price > EMA20 |
| **Trend** | below_ema20 | EXIT | MODERATE | Price < EMA20 by 1%+ |
| **Trend** | macd_bullish | HOLD | STRONG | MACD > Signal |
| **Trend** | macd_bearish | EXIT | MODERATE | MACD < Signal |
| **Time** | market_closing | EXIT | STRONG | < 10 min to close |
| **Time** | market_closing_soon | EXIT | MODERATE | < 30 min to close |
| **Time** | lunch_break_soon | EXIT | MODERATE | 11:50-12:00 HKT |

#### Decision Matrix

| Condition | Action | Cost |
|-----------|--------|------|
| Any STRONG EXIT signal | Exit immediately | FREE |
| 2+ MODERATE EXIT signals | Consult Haiku | ~$0.05 |
| STRONG HOLD + no MODERATE EXIT | Continue holding | FREE |
| MODERATE signals mixed | Consult Haiku | ~$0.05 |
| No EXIT signals | Continue holding | FREE |

### 4.3 Position Monitor Status Table

```sql
CREATE TABLE position_monitor_status (
    monitor_id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES positions(position_id),
    symbol VARCHAR(20) NOT NULL,
    
    -- Monitor State
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- Values: 'pending', 'starting', 'running', 'sleeping', 'stopped', 'error'
    pid INTEGER,
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    last_check_at TIMESTAMP WITH TIME ZONE,
    next_check_at TIMESTAMP WITH TIME ZONE,
    checks_completed INTEGER DEFAULT 0,
    
    -- Market State
    last_price DECIMAL(12,4),
    high_watermark DECIMAL(12,4),
    current_pnl_pct DECIMAL(8,4),
    
    -- Technical Analysis
    last_rsi DECIMAL(5,2),
    last_macd_signal VARCHAR(20),
    last_vwap_position VARCHAR(20),
    last_ema20_position VARCHAR(20),
    
    -- Signals
    hold_signals TEXT[],
    exit_signals TEXT[],
    signal_strength VARCHAR(20),
    recommendation VARCHAR(10),
    recommendation_reason TEXT,
    
    -- AI Tracking
    haiku_calls INTEGER DEFAULT 0,
    last_haiku_recommendation TEXT,
    estimated_cost DECIMAL(8,4) DEFAULT 0,
    
    -- Errors
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    consecutive_errors INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 4.4 Monitor Health View

```sql
CREATE OR REPLACE VIEW v_monitor_health AS
SELECT 
    p.position_id,
    p.symbol,
    p.side,
    p.quantity,
    p.entry_price,
    p.status AS position_status,
    p.opened_at,
    
    COALESCE(m.status, 'NO_MONITOR') AS monitor_status,
    m.last_check_at,
    m.checks_completed,
    
    ROUND(EXTRACT(EPOCH FROM (NOW() - m.last_check_at))/60, 1) AS minutes_since_check,
    
    m.recommendation,
    m.hold_signals,
    m.exit_signals,
    m.last_rsi,
    
    CASE 
        WHEN m.status IS NULL THEN '🔴 NO_MONITOR'
        WHEN m.status = 'error' THEN '🔴 ERROR'
        WHEN m.consecutive_errors >= 3 THEN '🔴 FAILING'
        WHEN m.last_check_at < NOW() - INTERVAL '15 minutes' THEN '🟡 STALE'
        WHEN m.status = 'running' THEN '🟢 ACTIVE'
        WHEN m.status = 'sleeping' THEN '🔵 SLEEPING'
        ELSE '⚪ UNKNOWN'
    END AS health
    
FROM positions p
LEFT JOIN position_monitor_status m ON m.position_id = p.position_id
WHERE p.status = 'open'
ORDER BY p.opened_at;
```

---

## PART 5: LEARNING PIPELINE

### 5.1 Experiment → Validate → Promote

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LEARNING PIPELINE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. EXPERIMENT (dev_claude - Full Autonomy)                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  dev_claude experiments with:                                         │  │
│  │  • Signal threshold changes (RSI 70 vs 75)                           │  │
│  │  • New pattern detection methods                                      │  │
│  │  • Risk parameter tuning                                              │  │
│  │  • Exit strategy variants                                             │  │
│  │  • Hold duration tests                                                │  │
│  │                                                                       │  │
│  │  Records to consciousness:                                            │  │
│  │  INSERT INTO claude_observations (agent_id, category, content, ...)   │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  2. VALIDATE (big_bro - Strategic Review)                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  big_bro reviews observations:                                        │  │
│  │  • Statistical significance                                           │  │
│  │  • Consistency across market conditions                               │  │
│  │  • Risk-adjusted returns                                              │  │
│  │  • Edge cases and failure modes                                       │  │
│  │                                                                       │  │
│  │  If validated:                                                        │  │
│  │  INSERT INTO claude_learnings (                                       │  │
│  │    source_agent = 'dev_claude',                                       │  │
│  │    validated = true,                                                  │  │
│  │    validated_by = 'big_bro',                                          │  │
│  │    content = '...'                                                    │  │
│  │  )                                                                    │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  3. PROMOTE (Craig - Manual Deployment)                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  Craig reviews validated learning:                                    │  │
│  │  • Reviews code changes required                                      │  │
│  │  • Tests in dev environment                                           │  │
│  │  • Deploys to intl_claude (separate droplet)                         │  │
│  │                                                                       │  │
│  │  intl_claude receives update via code deployment                      │  │
│  │  (Not automatic - manual review ensures safety)                       │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 dev_claude Autonomy

dev_claude has full autonomy to experiment within safety limits:

| Allowed | Not Allowed |
|---------|-------------|
| Change signal thresholds | Exceed daily loss limit |
| Try new patterns | Trade real money |
| Adjust risk parameters | Modify consciousness tables directly |
| Test exit strategies | Skip safety validation |
| Hold positions longer | Exceed position limits |
| Use more Haiku calls | Access production database |

---

## PART 6: DATABASE SCHEMA

### 6.1 catalyst_research (Consciousness)

Already exists - see Part 2.

### 6.2 catalyst_dev (dev_claude Sandbox)

**Fresh database - DROP old catalyst_trading, CREATE catalyst_dev**

```sql
-- Core trading tables (same schema as catalyst_intl)
CREATE TABLE securities (...);
CREATE TABLE trading_cycles (...);
CREATE TABLE positions (...);
CREATE TABLE orders (...);
CREATE TABLE scan_results (...);

-- Position monitor status
CREATE TABLE position_monitor_status (...);

-- Health view
CREATE VIEW v_monitor_health AS ...;
```

### 6.3 catalyst_intl (Production)

Exists - add position_monitor_status table and v_monitor_health view.

---

## PART 7: CRON SCHEDULE

### 7.1 Consciousness Hub (US Droplet)

```cron
# ============================================================================
# BIG_BRO - Strategic Review
# ============================================================================
0 6 * * * /root/catalyst/scripts/run_big_bro.sh review
0 18 * * * /root/catalyst/scripts/run_big_bro.sh review

# ============================================================================
# DEV_CLAUDE - Sandbox Trading (HKEX hours)
# ============================================================================
# Pre-market startup (09:00 HKT = 01:00 UTC)
0 1 * * 1-5 /root/catalyst/dev/startup_monitor.py

# Trading cycles (09:30-16:00 HKT)
30 1 * * 1-5 /root/catalyst/dev/unified_agent.py --mode trade
0 2-3 * * 1-5 /root/catalyst/dev/unified_agent.py --mode trade
0 4 * * 1-5 /root/catalyst/dev/unified_agent.py --mode close  # Lunch review
0 5-7 * * 1-5 /root/catalyst/dev/unified_agent.py --mode trade
0 8 * * 1-5 /root/catalyst/dev/unified_agent.py --mode close  # EOD review

# Heartbeat (off-hours)
0 9,12,15,18,21 * * 1-5 /root/catalyst/dev/unified_agent.py --mode heartbeat
```

### 7.2 Production (International Droplet)

```cron
# ============================================================================
# INTL_CLAUDE - Production Trading (HKEX hours)
# ============================================================================
# Pre-market startup (09:00 HKT = 01:00 UTC)
0 1 * * 1-5 /root/catalyst-international/startup_monitor.py

# Trading cycles (09:30-16:00 HKT)
30 1 * * 1-5 /root/catalyst-international/unified_agent.py --mode trade
0 2-3 * * 1-5 /root/catalyst-international/unified_agent.py --mode trade
0 4 * * 1-5 /root/catalyst-international/unified_agent.py --mode close  # Lunch review
0 5-7 * * 1-5 /root/catalyst-international/unified_agent.py --mode trade
0 8 * * 1-5 /root/catalyst-international/unified_agent.py --mode close  # EOD review

# Heartbeat (off-hours)
0 9,12,15,18,21 * * 1-5 /root/catalyst-international/unified_agent.py --mode heartbeat
```

---

## PART 8: FILE STRUCTURE

### 8.1 Consciousness Hub (US Droplet)

```
/root/catalyst/
├── consciousness/
│   ├── consciousness.py          # Core consciousness module
│   ├── database.py               # Connection management
│   ├── alerts.py                 # Email notifications
│   └── doctor_claude.py          # Health monitoring
├── dev/
│   ├── unified_agent.py          # dev_claude trading agent
│   ├── startup_monitor.py        # Pre-market reconciliation
│   ├── position_monitor.py       # Pattern-based monitoring
│   ├── signals.py                # Signal detection v2.0.0
│   ├── tool_executor.py          # Tool execution
│   ├── moomoo.py                 # Broker integration
│   └── config/
│       └── dev_claude_config.yaml
├── scripts/
│   ├── run_big_bro.sh
│   └── close_all_us_positions.py
└── logs/
```

### 8.2 Production (International Droplet)

```
/root/catalyst-international/
├── unified_agent.py              # intl_claude trading agent
├── startup_monitor.py            # Pre-market reconciliation
├── position_monitor.py           # Pattern-based monitoring
├── signals.py                    # Signal detection v2.0.0
├── tool_executor.py              # Tool execution
├── moomoo.py                     # Broker integration
├── safety.py                     # Safety validator
├── config/
│   └── intl_claude_config.yaml
└── logs/
```

---

## PART 9: IMPLEMENTATION CHECKLIST

### Phase 1: US Cleanup (Day 1)
- [ ] Close all 32 US positions
- [ ] Stop US trading microservices
- [ ] Remove US trading cron jobs
- [ ] Archive US trading code

### Phase 2: Database Setup (Day 1)
- [ ] DROP catalyst_trading
- [ ] CREATE catalyst_dev (fresh)
- [ ] Add position_monitor_status to catalyst_dev
- [ ] Add position_monitor_status to catalyst_intl
- [ ] Add v_monitor_health view to both

### Phase 3: Core Modules (Day 2)
- [ ] Deploy signals.py v2.0.0 (both systems)
- [ ] Deploy startup_monitor.py (both systems)
- [ ] Update position_monitor.py (both systems)

### Phase 4: dev_claude Setup (Day 3)
- [ ] Initialize dev_claude in consciousness
- [ ] Create dev_claude_config.yaml
- [ ] Deploy unified_agent.py for dev_claude
- [ ] Configure Moomoo paper account #2

### Phase 5: Integration (Day 4)
- [ ] Update unified_agent.py startup integration
- [ ] Deploy cron schedules
- [ ] Test MCP dashboard tools
- [ ] End-to-end testing

---

## PART 10: RELATED DOCUMENTS

| Document | Version | Status | Purpose |
|----------|---------|--------|---------|
| This document | v10.0.0 | **CURRENT** | Ecosystem architecture |
| architecture-consolidation-v9.2.0.md | v9.2.0 | Superseded | Previous architecture |
| database-schema.md | v8.0.0 | Update needed | Database schema |
| functional-specification.md | v8.0.0 | Update needed | Module specifications |
| claude-consciousness-framework-v1.1.0.md | v1.1.0 | Reference | Consciousness details |

---

## APPENDIX A: MCP Tools

### Monitor Status Tool

```python
@mcp.tool()
async def get_monitor_status(agent: str = "all") -> Dict:
    """
    Get position monitor status for trading agents.
    
    Args:
        agent: 'intl_claude', 'dev_claude', or 'all'
        
    Returns:
        Health status for all open positions with monitor state
    """
```

### Reconcile Monitors Tool

```python
@mcp.tool()
async def reconcile_monitors(agent: str) -> Dict:
    """
    Force reconciliation of monitors for an agent.
    
    Ensures every open position has an active monitor.
    """
```

---

## APPENDIX B: Environment Variables

### Consciousness Hub

```bash
# Databases
RESEARCH_DATABASE_URL=postgresql://...
DEV_DATABASE_URL=postgresql://...

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxx

# Email Alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xxx
SMTP_PASSWORD=xxx
ALERT_EMAIL=xxx

# Agent
AGENT_ID=dev_claude
```

### Production Droplet

```bash
# Databases
RESEARCH_DATABASE_URL=postgresql://...
INTL_DATABASE_URL=postgresql://...

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxx

# Moomoo
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111

# Agent
AGENT_ID=intl_claude
```

---

**END OF CATALYST ECOSYSTEM ARCHITECTURE v10.0.0**

*Catalyst Trading System*  
*Craig + Claude Family*  
*2026-01-10*
