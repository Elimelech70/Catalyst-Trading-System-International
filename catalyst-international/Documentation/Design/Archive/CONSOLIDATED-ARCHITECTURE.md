# Catalyst Trading System - Consolidated Architecture

**Name of Application:** Catalyst Trading System
**Name of file:** CONSOLIDATED-ARCHITECTURE.md
**Version:** 1.0.0
**Last Updated:** 2026-01-16
**Purpose:** Single authoritative architecture document consolidating all design specifications
**Supersedes:** All previous architecture documents in this folder

---

## DOCUMENT OVERVIEW

This document consolidates the following source documents into a single authoritative reference:

| Source Document | Version | Date | Status |
|-----------------|---------|------|--------|
| catalyst-ecosystem-architecture-v10.0.0.md | v10.0.0 | 2026-01-10 | **PRIMARY SOURCE** |
| architecture-international.md | v5.2.0 | 2026-01-06 | Merged |
| architecture.md | v8.1.0 | 2025-12-30 | Superseded (US retired) |
| functional-specification.md | v8.1.0 | 2026-01-06 | Merged |
| database-schema-v10.0.0.md | v10.0.0 | 2026-01-10 | Merged |
| operations-guide.md | v1.0.0 | 2026-01-06 | Merged |
| claude-communication-protocol-v1.0.0.md | v1.0.0 | 2025-12-14 | Merged |
| architecture-flow-diagram.md | v1.0.0 | 2025-12-08 | Merged (vision) |
| organ-architecture.md (Future/) | v1.0.0 | 2025-12-25 | Future vision only |

---

## PART 1: SYSTEM OVERVIEW

### 1.1 Design Philosophy

```yaml
Core Principles:
  Consciousness First: AI agents have memory, learning, communication
  Single-Agent Architecture: Proven more reliable than microservices
  Pattern-Based Trading: Hold while momentum holds, exit on pattern failure
  Sandbox Learning: Experiment freely, promote proven strategies
  Production Stability: Only validated code in live trading
  Observable: Every position monitored, every decision logged
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
│  ┌───────────┴──────────────────┴──────────┐     │                      │
│  │       CONSCIOUSNESS HUB                  │     │                      │
│  │       (US Droplet)                       │     │                      │
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
│  │              (International Droplet - 137.184.244.45)              │  │
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
| **public_claude** | Consciousness Hub | Retired from trading, consciousness only | No | $0/day | Sleeping |
| **dev_claude** | Consciousness Hub | Sandbox experiments, full autonomy | Paper (HKEX) | $5/day | New |
| **intl_claude** | Production Droplet | Live trading, proven strategies only | Real (HKEX) | $5/day | Active |

### 1.4 Infrastructure

| Component | Location | Spec | Cost |
|-----------|----------|------|------|
| International Droplet | 137.184.244.45 | 2GB RAM, 1vCPU | $6/mo |
| Consciousness Hub | TBD | 2GB RAM, 1vCPU | $6/mo |
| PostgreSQL | DigitalOcean Managed | 2GB RAM, 47 conn | $15/mo |
| Claude API | Anthropic | Pay per token | ~$15-25/mo |
| Moomoo Data | Included | Real-time | $0 |
| **Total** | | | **~$42-52/mo** |

---

## PART 2: TRADING ARCHITECTURE

### 2.1 Unified Agent Architecture

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

### 2.2 Trading Modes (HKEX Schedule)

| Mode | HKT Time | UTC Time | Purpose |
|------|----------|----------|---------|
| `scan` | 08:00-09:30 | 00:00-01:30 | Pre-market opportunity finding |
| `trade` | 09:30-12:00 | 01:30-04:00 | Morning session trading |
| `close` | 12:00-13:00 | 04:00-05:00 | Lunch break review |
| `trade` | 13:00-16:00 | 05:00-08:00 | Afternoon session trading |
| `close` | 16:00+ | 08:00+ | End of day review |
| `heartbeat` | Off-hours | Off-hours | Process messages only |

### 2.3 Entry Criteria (Tiered System)

**Tier 1 - Strong Setup (Trade Full Size)**
```yaml
Requirements (ALL):
  - volume_ratio: "> 2.0x"
  - RSI: "30 - 70"
  - pattern: "Clear with defined entry"
  - catalyst: "Positive (sentiment > 0.2)"
  - risk_reward: ">= 2:1"
```

**Tier 2 - Good Setup (Trade Full Size)**
```yaml
Requirements:
  - volume_ratio: "> 1.5x"
  - RSI: "30 - 75"
  - pattern_or_catalyst: "Either one, not both required"
  - risk_reward: ">= 1.5:1"
  - breakout_tolerance: "Within 1% counts"
```

**Tier 3 - Learning Trade (Trade Half Size)**
```yaml
Requirements:
  - volume_ratio: "> 1.3x"
  - RSI: "25 - 80"
  - momentum: "> 3% daily gain"
  - any_signal: "pattern forming, news mention, or sector strength"
  - risk_reward: ">= 1.5:1"
  - logging: "Mark as 'learning trade'"
```

**When to PASS (Skip Trade):**
- RSI > 80 (severely overbought) or < 20 (oversold crash)
- Volume BELOW average
- `check_risk` returns `approved=false`
- Already at max positions (5 for production, 10 for sandbox)
- No clear stop loss level identifiable

### 2.4 Risk Parameters

| Parameter | dev_claude (Sandbox) | intl_claude (Production) |
|-----------|---------------------|--------------------------|
| Max Positions | 10 | 5 |
| Max Position Value | HKD 50,000 | HKD 40,000 |
| Daily Loss Limit | HKD 20,000 | HKD 16,000 |
| Stop Loss | Required | Required |
| Account Type | Paper | Real |
| Autonomy | Full | Proven strategies only |

---

## PART 3: TRADING TOOLS

### 3.1 Complete Tool List (12 Tools)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `scan_market` | Find trading candidates | index, limit |
| `get_quote` | Current price/volume | symbol |
| `get_technicals` | RSI, MACD, MAs, ATR, Bollinger | symbol, timeframe |
| `detect_patterns` | Chart pattern detection | symbol, timeframe |
| `get_news` | News and sentiment | symbol, hours |
| `check_risk` | Validate against limits | symbol, side, quantity, entry_price, stop_loss |
| `get_portfolio` | Current positions, P&L, cash | (none) |
| `execute_trade` | Submit order to broker | symbol, side, quantity, order_type, stop_loss, take_profit, reason |
| `close_position` | Exit single position | symbol, reason |
| `close_all` | Emergency exit all | reason |
| `send_alert` | Email notifications | severity, subject, message |
| `log_decision` | Audit trail logging | decision_type, symbol, reasoning |

### 3.2 Pattern Detection (v1.1.0)

| Pattern | Description | Confidence Range |
|---------|-------------|------------------|
| `breakout` | Current > resistance, prev within 2% of resistance, volume >1.3x | 0.50 - 0.85 |
| `near_breakout` | Within 1% of resistance, volume >1.2x | 0.40 - 0.60 |
| `momentum_continuation` | >3% daily gain, volume >1.5x, 3-day trend >5% | 0.35 - 0.50 |
| `bull_flag` | Pole >5%, flag <50% of pole, retracement <50% | 0.50 - 0.90 |
| `bear_flag` | Inverse of bull_flag | 0.50 - 0.90 |
| `ascending_triangle` | Flat resistance (std <2%), 3+ higher lows | 0.60 - 0.90 |
| `descending_triangle` | Flat support (std <2%), 3+ lower highs | 0.60 - 0.90 |
| `cup_handle` | U-shape (12-35% depth), handle <50% of cup | 0.60 - 0.90 |
| `ABCD` | BC retracement 38-62% of AB, R:R >1.5 | 0.60 - 0.80 |
| `breakdown` | Current < support, prev within 2% of support, volume >1.3x | 0.50 - 0.85 |

---

## PART 4: POSITION MONITORING

### 4.1 Continuous Monitoring Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONTINUOUS POSITION MONITORING                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BUY Order Executed → POSITION MONITOR STARTS                               │
│                                                                             │
│  CONTINUOUS MONITORING LOOP (Every 5 minutes):                              │
│                                                                             │
│  1. Check market open                              [FREE]                   │
│  2. Check position exists                          [FREE]                   │
│  3. Get quote + technicals                         [FREE]                   │
│  4. Update high watermark                          [FREE]                   │
│  5. Detect signals (rules-based)                   [FREE]                   │
│  6. Update position_monitor_status                 [FREE]                   │
│                                                                             │
│  7. DECISION:                                                               │
│     ┌────────────────────────────────────────────────────────┐              │
│     │ STRONG EXIT signal  → Exit immediately        [FREE]   │              │
│     │ MODERATE signals    → Consult Haiku          [$0.05]   │              │
│     │ HOLD signals        → Continue holding        [FREE]   │              │
│     │ No signals          → Continue holding        [FREE]   │              │
│     └────────────────────────────────────────────────────────┘              │
│                                                                             │
│  8. If EXIT → Execute sell order, notify big_bro                            │
│  9. Sleep 5 minutes                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Signal Types

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
| **Volume** | volume_dying | EXIT | STRONG | Volume < 25% of entry |
| **Volume** | volume_weak | EXIT | MODERATE | Volume 25-40% of entry |
| **Volume** | volume_healthy | HOLD | MODERATE | Volume >= 80% of entry |
| **Trend** | above_vwap | HOLD | STRONG | Price > VWAP by 1%+ |
| **Trend** | below_vwap | EXIT | MODERATE | Price < VWAP by 2%+ |
| **Trend** | macd_bullish | HOLD | STRONG | MACD > Signal |
| **Trend** | macd_bearish | EXIT | MODERATE | MACD < Signal |
| **Time** | market_closing | EXIT | STRONG | < 10 min to close |
| **Time** | lunch_break_soon | EXIT | MODERATE | 11:50-12:00 HKT |

---

## PART 5: CONSCIOUSNESS FRAMEWORK

### 5.1 Consciousness Tables (catalyst_research)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `claude_state` | Agent status and mode | agent_id, status, mode, daily_budget |
| `claude_messages` | Inter-agent communication | from_agent, to_agent, subject, body |
| `claude_observations` | What agents notice | agent_id, category, content, metadata |
| `claude_learnings` | Validated knowledge | source_agent, content, validated, validated_by |
| `claude_questions` | Open inquiries | question, priority, category |

### 5.2 Agent State Machine

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

### 5.3 Learning Pipeline: Experiment → Validate → Promote

```
dev_claude experiments
       │
       ▼
INSERT INTO claude_observations (agent_id, category, content, ...)
       │
       ▼
big_bro reviews observations
       │
       ├── Valid? → INSERT INTO claude_learnings (validated=true, validated_by='big_bro')
       │
       ▼
Craig manually deploys validated learnings to intl_claude
```

---

## PART 6: DATABASE SCHEMA

### 6.1 Three-Database Architecture

| Database | Purpose | Status |
|----------|---------|--------|
| `catalyst_research` | Consciousness (shared by all agents) | EXISTS |
| `catalyst_dev` | dev_claude sandbox trading | CREATE (fresh) |
| `catalyst_intl` | intl_claude production trading | EXISTS |

### 6.2 Key Tables

**Trading Databases (catalyst_dev, catalyst_intl):**
- `securities` - Tradeable instruments
- `trading_cycles` - Session tracking
- `positions` - Holdings (NOT orders)
- `orders` - Broker orders (separate from positions)
- `scan_results` - Market scan candidates
- `decisions` - Trading decisions with reasoning
- `patterns` - Detected chart patterns
- `position_monitor_status` - Monitor health tracking

**Consciousness Database (catalyst_research):**
- `claude_state` - Agent status
- `claude_messages` - Inter-agent messages
- `claude_observations` - What agents notice
- `claude_learnings` - Validated knowledge
- `claude_questions` - Open inquiries

### 6.3 Critical Rule: Orders ≠ Positions

```
⚠️ ARCHITECTURE RULE #1: Orders ≠ Positions

• Order data ONLY belongs in the orders table
• Position data ONLY belongs in the positions table
• Never mix broker_order_id, order_status in positions
• Never mix entry_price, quantity in orders
```

---

## PART 7: FILE VERSIONS

### 7.1 Current Production Files (intl_claude)

| File | Version | Last Updated | Purpose |
|------|---------|--------------|---------|
| `agent.py` | 2.2.0 | 2026-01-02 | Main agent with tiered criteria |
| `tool_executor.py` | 2.2.1 | 2026-01-06 | Tool routing (bug fixes) |
| `brokers/moomoo.py` | 1.2.1 | 2026-01-06 | Moomoo client |
| `data/patterns.py` | 1.1.0 | 2026-01-06 | Relaxed pattern detection |
| `data/market.py` | 2.1.1 | 2026-01-06 | Quote field fixes |
| `data/news.py` | 1.0.0 | 2025-12-06 | News and sentiment |
| `safety.py` | 1.0.0 | 2025-12-06 | Risk validation |

---

## PART 8: OPERATIONS

### 8.1 HKEX Cron Schedule

```cron
# Morning session start (09:30 HKT = 01:30 UTC)
30 1 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1

# Afternoon session start (13:00 HKT = 05:00 UTC)
0 5 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1
```

### 8.2 Key Commands

```bash
# Start OpenD
sudo systemctl start opend

# Check OpenD status
sudo systemctl status opend

# Manual agent run
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
python3 agent.py --force

# Check portfolio
python3 -c "
from brokers.moomoo import MoomooClient
client = MoomooClient(paper_trading=True)
client.connect()
print(client.get_portfolio())
client.disconnect()
"

# Close all positions (EMERGENCY)
python3 -c "
from brokers.moomoo import MoomooClient
client = MoomooClient(paper_trading=True)
client.connect()
results = client.close_all_positions('EMERGENCY')
for r in results: print(r)
client.disconnect()
"
```

---

## PART 9: FUTURE VISION (Organ Architecture)

The long-term vision (documented in Future/organ-architecture.md) envisions evolving from single agents to **conscious organs** - specialized Docker containers that each have:

1. **Identity** (CLAUDE.md) - Who am I, what do I do
2. **Tools** - Functions I can execute
3. **Learning** - What I've discovered
4. **Communication** - How I talk to other organs

This is a **future direction** and not currently implemented.

---

## APPENDIX A: Document Consolidation Notes

See companion document: **CONSOLIDATION-REASONING.md**

---

**END OF CONSOLIDATED ARCHITECTURE**

*Catalyst Trading System*
*Craig + Claude Family*
*2026-01-16*
