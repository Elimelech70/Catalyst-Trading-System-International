# Lessons Learned Gap Analysis: US System → IBKR Implementation

**Date:** 2025-12-13
**Purpose:** Verify IBKR implementation addresses all US system lessons
**Status:** Analysis Complete

---

## Executive Summary

Analyzed 6 critical lessons from US system operations against the current IBKR implementation. Found **4 fully addressed**, **1 partially addressed**, and **1 new risk identified**.

---

## Lesson-by-Lesson Analysis

### Lesson 1: ORDER MAPPING BUG (Critical)

**US Problem:** Order side "long" was not mapped to "buy" - 81 positions failed

**IBKR Status: ✅ FULLY ADDRESSED**

```python
# ibkr.py line 338 - CORRECT implementation
action = "BUY" if side.lower() in ["buy", "long"] else "SELL"
```

The IBKR client properly handles both "buy"/"long" and "sell"/"short" input formats. This maps correctly to IBKR's "BUY"/"SELL" action strings.

**Verification:** Code at `brokers/ibkr.py:338` shows proper normalization.

---

### Lesson 2: DATABASE/BROKER RECONCILIATION (High)

**US Problem:** Database showed 25 positions, broker showed 16 - phantom positions

**IBKR Status: ✅ ADDRESSED BY ARCHITECTURE**

The International system treats **broker as source of truth**:
- `get_portfolio()` queries IBKR directly (`ibkr.py:558-616`)
- `get_positions()` queries IBKR directly (`ibkr.py:618-672`)
- Database stores decisions/reasoning, not position state
- No position cache that can drift from broker

**Key difference:** Agent architecture queries broker state on each cycle rather than maintaining a local database of positions.

---

### Lesson 3: POSITION SIZING INCONSISTENCY (Medium)

**US Problem:** All positions 200 shares regardless of price (10x exposure variance)

**IBKR Status: ⚠️ PARTIALLY ADDRESSED**

Current tools.py `check_risk` validates:
- Max 20% of portfolio per position
- Max 5 positions
- Risk/reward ratio min 2:1

**GAP IDENTIFIED:** No dollar-based position sizing calculation in tools. Claude must calculate quantity, and may make share-based rather than dollar-based decisions.

**Recommendation:** Add position sizing guidance to system prompt:
```
Target position size: 15-20% of portfolio value
Calculate: quantity = (target_value / current_price) rounded to lot size
```

---

### Lesson 4: NO PROFIT-TAKING MECHANISM (Medium)

**US Problem:** TE +22%, AAPL +37% still held - unrealized gains can evaporate

**IBKR Status: ✅ ADDRESSED BY AI AGENT**

The AI Agent architecture handles this dynamically:
- Claude evaluates each position on every cycle
- `get_portfolio()` returns `unrealized_pnl_pct` for each position
- Claude can decide to close based on % gain
- `close_position()` tool available with reason logging

**Advantage over US:** Claude can apply contextual judgment (news, market conditions) rather than rigid percentage rules.

**Enhancement:** Add profit-taking guidance to system prompt for first week:
```
Consider taking profits when:
- Unrealized gain > 15%
- Trailing stop: if gain > 10%, protect at least 50% of gain
```

---

### Lesson 5: DRAWDOWN INVESTIGATION GAP (Medium)

**US Problem:** Lost $1,759 in 2 days, no forensic analysis capability

**IBKR Status: ✅ ADDRESSED**

The `log_decision` tool captures all decisions with reasoning:
```python
# tools.py - log_decision tool
"decision": ["trade", "skip", "close", "emergency", "observation"]
"symbol": "Related symbol"
"reasoning": "Detailed explanation"
```

Combined with:
- All trades logged with `reason` parameter
- Daily P&L tracked in `get_portfolio()`
- Agent logs in `logs/agent.log`

**Investigation capability:** Can query decisions + reasoning to understand why losses occurred.

---

### Lesson 6: RISK LIMITS HELD (Positive)

**US Positive:** $2,000 daily limit never hit, system continued operating

**IBKR Status: ✅ MAINTAINED**

Current risk parameters (from tools.py):
- Max 20% portfolio per position
- Max 5 positions
- Daily loss limit 2% (triggers `close_all`)
- Stop loss max 5% per trade
- Min risk/reward 2:1

**Conservative approach maintained for paper trading phase.**

---

## NEW RISKS IDENTIFIED FOR IBKR

### Risk A: HKEX Tick Size Validation

**Status: ✅ IMPLEMENTED**

IBKR client has comprehensive tick size rounding (`ibkr.py:440-479`):
- 11 price tiers with correct tick sizes
- All prices rounded before submission
- Prevents order rejection for invalid prices

### Risk B: Delayed Data Trading (NEW RISK)

**Status: ⚠️ ACKNOWLEDGED BUT NOT MITIGATED**

Current system uses 15-minute delayed data:
```python
# ibkr.py line 128
self.ib.reqMarketDataType(3)  # Delayed data
```

**Implications:**
- Entry prices may drift from quote to fill
- Stop loss may trigger late
- Momentum signals may be stale

**Recommendation for CLAUDE.md:**
- Use limit orders, not market orders
- Set wider stop losses (account for 15-min drift)
- Don't chase fast-moving stocks

### Risk C: HK Symbol Format Handling

**Status: ✅ IMPLEMENTED**

IBKR requires "700" not "0700":
```python
# ibkr.py line 180
symbol = symbol.lstrip('0') or '0'
```

### Risk D: Currency Mismatch

**Status: ✅ HANDLED**

Account is AUD, stocks trade in HKD. Portfolio queries check both BASE and HKD currencies (`ibkr.py:575-597`).

---

## GAPS TO ADDRESS

### Gap 1: Dollar-Based Position Sizing Guidance

**Current:** Tools validate but don't calculate position size
**Fix:** Add to CLAUDE.md system prompt guidance

### Gap 2: Delayed Data Trading Rules

**Current:** No explicit guidance for 15-min delayed data
**Fix:** Add to CLAUDE.md "NEVER DO" and "ALWAYS DO" sections

### Gap 3: Profit-Taking Guidelines

**Current:** Relies on Claude's judgment
**Fix:** Add initial guidelines to system prompt (can be relaxed as AI matures)

---

## RECOMMENDED CLAUDE.md UPDATES

Add new section: **"IBKR-Specific Lessons"**

```markdown
### Lesson 11: HKEX Tick Size Compliance
**Problem**: HKEX has 11-tier tick size rules
**Solution**: Always use _round_to_tick() before price submission
**Implementation**: brokers/ibkr.py:440-479

### Lesson 12: Delayed Data Trading
**Problem**: Using 15-minute delayed market data
**Solution**:
- ALWAYS use limit orders, not market orders
- Set stop losses 1-2% wider than real-time would require
- NEVER chase momentum stocks (signal is stale)
- Prefer stocks with lower volatility

### Lesson 13: HK Symbol Format
**Problem**: IBKR rejects "0700", requires "700"
**Solution**: Always strip leading zeros from HK symbols
**Implementation**: brokers/ibkr.py:180

### Lesson 14: Dollar-Based Position Sizing (IBKR)
**Problem**: Share-based sizing creates uneven exposure
**Solution**: Calculate target value first, then convert to shares
- Target: 15-20% of portfolio per position
- quantity = int(target_value / price / 100) * 100  # Round to lot size
```

---

## SUMMARY TABLE

| Lesson | US Issue | IBKR Status | Action Needed |
|--------|----------|-------------|---------------|
| 1. Order Mapping | Critical bug | ✅ Fixed | None |
| 2. Reconciliation | Phantom positions | ✅ By architecture | None |
| 3. Position Sizing | Share-based | ⚠️ Partial | Add guidance |
| 4. Profit Taking | No rules | ✅ Claude decides | Add initial rules |
| 5. Drawdown Analysis | No capability | ✅ log_decision | None |
| 6. Risk Limits | Working | ✅ Maintained | None |
| NEW: Delayed Data | - | ⚠️ Risk exists | Add rules |

---

**Analysis Complete:** 2025-12-13
**Next Action:** Update CLAUDE.md with IBKR-specific lessons
