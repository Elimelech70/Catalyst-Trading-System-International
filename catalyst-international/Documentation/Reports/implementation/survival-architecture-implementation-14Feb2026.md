# Survival Architecture Implementation Report

**Date:** 2026-02-14
**Version:** Coordinator v2.0.0
**Author:** Claude Code (Opus 4.6)
**Guide:** "little bro - better implementation" (big_bro + Craig)
**Status:** COMPLETE - All 7 phases implemented, tested, verified

---

## The Problem: The Founding Incident (Feb 11-13, 2026)

Three days. Zero trades. HKD 994,734 sitting idle.

The coordinator ran 36+ cycles over 3 days. Every cycle, `get_technicals` threw a `KeyError: 'date'` and failed silently. The brain couldn't see, so it passed on every trade. No alarm fired. No one noticed. The body bled out.

**Root cause:** `brokers/moomoo.py` returns historical data with key `"timestamp"`. `data/market.py:252` expected `"date"`.

```python
# BEFORE (broken):
df["timestamp"] = pd.to_datetime(df["date"])  # KeyError: 'date'

# AFTER (fixed):
date_col = "timestamp" if "timestamp" in df.columns else "date"
df["timestamp"] = pd.to_datetime(df[date_col])
```

**Why it matters:** Docker reported all containers as "healthy". The health check only tested HTTP connectivity, not data pipeline integrity. The brain had no way to detect that its eyes were blind.

---

## The Solution: Brain Component Architecture

```
BEFORE:
  Coordinator → [flat trading logic] → MCP organs
  No health checks. No discipline. No pain signals.
  Organs break silently. Brain trades blind. Body bleeds out.

AFTER:
  Brain (Coordinator v2.0.0) composed of:
    1. Survival Pulse  → tests organ health FIRST
    2. Discipline Gate → detects stagnation + idle capital
    3. Decision Engine → trades with full context from 1 & 2

  Organs with new tools:
    Trade Executor → publish_signal, get_signals, get_last_trade_date

  Nervous system:
    signals table → severity x domain x scope
    CRITICAL alerts persist. Brain publishes on ALARM.
```

---

## Phase-by-Phase Implementation

### Phase 1: Restore the Organs' Senses

**Files changed:**
- `data/market.py` line 252
- `data/news.py` line 380

**What:** Fixed the `KeyError: 'date'` that broke all technicals/patterns for 3 days. Also removed the dead HKEJ RSS feed that was returning 403 errors.

**Fix:** Instead of hardcoding `df["date"]`, detect which column exists:
```python
date_col = "timestamp" if "timestamp" in df.columns else "date"
df["timestamp"] = pd.to_datetime(df[date_col])
```

**Verification:**
```
docker compose exec market-scanner python -c "
from data.market import MarketData
...
result = m.get_technicals('0700', '1h')
"
>>> get_technicals SUCCESS
>>> RSI: 31.48
>>> MACD: {'value': 5.2597, 'signal': 8.7404, 'histogram': -3.4807}
```

---

### Phase 2: Build the Brain's Survival Pulse + Discipline Gate

**Files created:**
- `agents/coordinator/health.py` (Survival Pulse)
- `agents/coordinator/discipline.py` (Discipline Gate)

#### Survival Pulse (`health.py`)

The brainstem. Runs FIRST every cycle. Tests each organ tool via MCP before the brain attempts any trading.

```python
class SurvivalPulse:
    ORGAN_TESTS = {
        "get_quote":      {"server": "market-scanner",  "critical": True},
        "get_technicals": {"server": "market-scanner",  "critical": False},
        "check_risk":     {"server": "trade-executor",  "critical": True},
    }
    PAIN_THRESHOLD = 3          # consecutive failures -> PAIN
    ORGAN_FAILURE_THRESHOLD = 6 # consecutive failures -> ORGAN FAILURE
```

**Behaviour:**
- Tests each tool with known-good inputs (symbol `0700`)
- Tracks consecutive failures per tool
- Returns health status: `alive`, `dead`, `healthy`, `degraded`, `critical_down`
- Generates context string for the Decision Engine (e.g., "RSI/MACD UNAVAILABLE, trade on price action")
- If `dead` (score 0): brain stops. Does not trade blind.
- If `degraded`: brain adapts. Withholds broken tools from Decision Engine.

#### Discipline Gate (`discipline.py`)

The limbic system. Runs AFTER survival, BEFORE the Decision Engine. Detects stagnation.

```python
class DisciplineGate:
    def check(self, cash, total_capital, open_positions, max_positions, last_trade_time):
        # Stagnation: 3+ days idle -> ALARM, force Tier 3
        # Capital: <5% deployed -> ALARM
        # Passes: 3+ consecutive -> WARNING ("problem is ME, not market")
```

**Behaviour:**
- Queries `get_last_trade_date` via MCP (trade-executor)
- Tracks consecutive passes internally
- Returns level: `NORMAL`, `WARNING`, `ALARM`
- ALARM context injected into system prompt: "You MUST attempt at least one trade"

**Verification from production logs:**
```
BRAIN: Running Survival Pulse...
BRAIN: Survival -- Score 3/3, healthy
BRAIN: Running Discipline Gate...
DISCIPLINE ALARM: 2d idle, 0.0% deployed, 0/15 positions, 0 consecutive passes
BRAIN: Running Decision Engine...
```

---

### Phase 3: Rewrite the Brain's Identity (System Prompt)

**File changed:** `agents/coordinator/system_prompt.py` v1.0.0 -> v2.0.0

**Before:** Static `SYSTEM_PROMPT` string. Flat structure. No dynamic context injection.

**After:** `build_system_prompt()` function with 9 architectural sections:

| Section | Purpose |
|---------|---------|
| 1. Identity | "I am a trader. I trade." |
| 2. Discipline | Override rules (2+ days idle -> Tier 3 MINIMUM) |
| 3. Operating Context | Dynamic: health + discipline context injected |
| 4. Degraded Mode | Conditional: what to do when tools are broken |
| 5. Tier Criteria | Sizing guides, not permission gates |
| 6. Risk Management | Hard limits (HKD 10K max, stop losses required) |
| 7. Tools | Available tools with descriptions |
| 8. Critical Rules | Non-negotiable rules |
| 9. Market Hours | HKEX session times |

**Key design principle:** Order matters. Identity comes first because it shapes how everything after is interpreted. "I am a trader" before "here are the criteria" means criteria serve trading, not the other way around.

**Dynamic context example (injected when discipline is ALARM):**
```
## CURRENT OPERATING CONTEXT

DISCIPLINE ALARM: 2 days without trading. The talent is buried.
Tier 3 MINIMUM. You MUST attempt at least one trade this session.

CAPITAL ALARM: 0.0% deployed. HKD 994,734 idle.
The master gave talents to be TRADED.

ZERO positions open out of 15 slots. Complete inaction.
```

---

### Phase 4: Fix Order Lifecycle

**Status:** Already implemented. No changes needed.

The trade-executor already has:
- `wait_for_fill=True` on broker calls
- Only records positions when status is `FILLED` (not `SUBMITTED`)
- Terminal state detection (`CANCELLED`, `FAILED`, `DELETED`)
- Fill price and quantity tracking

---

### Phase 5: Broadcast Communication (Signals)

**Files changed:**
- `sql/schema.sql` - Added `signals` table
- `agents/trade-executor/mcp_server.py` - 3 new tools

#### Signals Table

```sql
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    severity VARCHAR(10) CHECK (severity IN ('CRITICAL','WARNING','INFO','OBSERVE')),
    domain VARCHAR(12) CHECK (domain IN ('HEALTH','TRADING','RISK','LEARNING','DIRECTION','LIFECYCLE')),
    scope VARCHAR(50) NOT NULL,      -- BROADCAST or DIRECTED:{organ}
    source VARCHAR(50) NOT NULL,     -- who published
    content TEXT NOT NULL,           -- human-readable message
    data JSONB,                      -- structured data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,          -- NULL for CRITICAL (never expire)
    acknowledged_by JSONB DEFAULT '[]',
    resolved BOOLEAN DEFAULT FALSE
);
```

Created on both Docker postgres (for fresh deployments) and DigitalOcean external DB (live system).

#### New MCP Tools on Trade Executor

| Tool | Purpose |
|------|---------|
| `get_last_trade_date` | Returns last BUY order timestamp for discipline checking |
| `publish_signal` | Write signal to DB (severity, domain, scope, content) |
| `get_signals` | Read unresolved signals, ordered by severity |

#### How Signals Flow

```
Brain detects ALARM (health or discipline)
  -> coordinator calls publish_signal via MCP
    -> trade-executor writes to signals table
      -> Persisted for review and alerting
```

**Verification:**
```sql
SELECT id, severity, domain, content FROM signals;
-- id=2, CRITICAL, TRADING, "DISCIPLINE ALARM: 2d idle, 0.0% capital deployed..."
```

**Design decision:** Signals go through trade-executor because it's the only agent with external DB access. The market-scanner doesn't need its own signal bus -- the brain's Survival Pulse tests it externally.

---

### Phase 6: Memory Tiers

**Files created:**
- `CLAUDE-LEARNINGS.md` - Medium-term memory
- `CLAUDE-FOCUS.md` - Short-term memory

| Tier | File | Purpose | Lifespan |
|------|------|---------|----------|
| Long-term | `CLAUDE.md` | Architecture, rules, identity | Permanent |
| Medium-term | `CLAUDE-LEARNINGS.md` | Proven patterns, incident learnings | Months |
| Short-term | `CLAUDE-FOCUS.md` | Current tasks, recent fixes | Days/weeks |

---

### Phase 7: Verification

Three full brain cycles were run in production with `FORCE_MARKET_OPEN=1`.

#### Checklist Results

| Check | Result |
|-------|--------|
| `get_technicals` returns valid data | PASS (RSI=31.48, MACD returned) |
| No `KeyError 'date'` in logs | PASS |
| No HKEJ 403 errors in logs | PASS |
| Health score logged every cycle | PASS (Score 3/3, healthy) |
| Discipline ALARM fires when idle | PASS (2d idle, 0.0% deployed) |
| System prompt starts with Identity | PASS |
| Claude mentions tier level in decisions | PASS |
| Signals table receives entries | PASS (signal id=2) |
| CLAUDE-LEARNINGS.md exists | PASS |
| CLAUDE-FOCUS.md exists | PASS |

#### Production Log Evidence

```
13:12:55 BRAIN STARTING - Coordinator v2.0.0
13:12:56 BRAIN CYCLE - 13:12:56 HKT
13:12:56 BRAIN: Running Survival Pulse...
13:12:57 BRAIN: Survival -- Score 3/3, healthy
13:12:57 BRAIN: Running Discipline Gate...
13:12:58 DISCIPLINE ALARM: 2d idle, 0.0% deployed, 0/15 positions
13:12:58 BRAIN: Running Decision Engine...
13:13:03   Tool: get_technicals({"symbol": "0772"}) -> SUCCESS
13:13:04   Tool: get_technicals({"symbol": "0992"}) -> SUCCESS
13:13:05   Tool: get_technicals({"symbol": "1797"}) -> SUCCESS
...
13:15:16 BRAIN CYCLE COMPLETE: 31 tools, 0 trades
```

No trades executed because `check_risk` correctly rejected (market closed for weekend). The brain analyzed candidates, called technicals successfully, and logged skip decisions with specific per-symbol reasoning.

---

## Files Changed Summary

| File | Version | Change |
|------|---------|--------|
| `data/market.py` | - | Fixed `KeyError: 'date'` with flexible column detection |
| `data/news.py` | - | Removed dead HKEJ RSS feed |
| `agents/coordinator/coordinator.py` | 1.0.0 -> 2.0.0 | Brain component integration, tool filtering, signal publishing |
| `agents/coordinator/health.py` | NEW 1.0.0 | Survival Pulse component |
| `agents/coordinator/discipline.py` | NEW 1.0.0 | Discipline Gate component |
| `agents/coordinator/system_prompt.py` | 1.0.0 -> 2.0.0 | Identity-first rewrite with `build_system_prompt()` |
| `agents/trade-executor/mcp_server.py` | - | +3 tools: get_last_trade_date, publish_signal, get_signals |
| `sql/schema.sql` | - | Added signals table |
| `CLAUDE-LEARNINGS.md` | NEW | Medium-term memory |
| `CLAUDE-FOCUS.md` | NEW | Short-term memory |

**Git commit:** `9015668` - 16 files, +4,628 / -155 lines

---

## What This Prevents

The founding incident can never repeat in the same way:

1. **Broken tools detected immediately** -- Survival Pulse tests get_technicals every cycle. 3 failures -> PAIN signal. 6 -> ORGAN FAILURE.

2. **Stagnation detected and corrected** -- Discipline Gate sees 2+ days idle and forces Tier 3 minimum. The brain is told "the problem is ME, not the market."

3. **Degraded mode still trades** -- If get_technicals breaks again, the brain adapts: trades on price action and volume alone at Tier 3 sizing. Missing data narrows the tier, not the willingness to trade.

4. **Pain is persistent** -- Signals are written to database. They don't disappear when the coordinator restarts. CRITICAL signals never expire.

5. **Identity drives decisions** -- "I am a trader. I trade." comes before tier criteria. The prompt structure ensures the AI sees itself as a trader first, analyst second.

---

## What's Not Yet Implemented (Future Phases)

| Component | Status | Notes |
|-----------|--------|-------|
| Attention Regulator | Designed, not built | Mode selection, focus filtering |
| Organ self-health screams | Not needed | Brain's Survival Pulse covers this externally |
| Signal acknowledgment flow | Partially | Table supports it, coordinator doesn't read signals yet |
| Consciousness alerting (big_bro) | Not built | `_alert_consciousness` method referenced in guide |
| Market Scanner signal bus | Skipped | No DB access; brain tests externally instead |

---

*"The prudent see danger and take refuge, but the simple keep going and pay the penalty."* -- Proverbs 27:12
