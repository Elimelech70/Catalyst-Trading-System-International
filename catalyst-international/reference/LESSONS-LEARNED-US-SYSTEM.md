# Lessons Learned - US System Operations

**Source:** Catalyst Trading System (US)
**Period:** November 7 - December 8, 2025
**Status:** Production Paper Trading
**Purpose:** Knowledge transfer to International System

---

## Executive Summary

The US system completed ~4 weeks of autonomous paper trading. Starting equity $100,142.13, ending $98,688.52 (-1.45%). Key learning: **the system works, but refinement needed in execution and exit strategy.**

---

## Critical Lessons

### 1. ORDER MAPPING BUG (Severity: Critical)

**What Happened:**
- Order side "long" was not properly mapped to "buy" in broker API
- 81 positions failed to execute correctly
- 54 rejected by broker, 27 cancelled

**Root Cause:**
```python
# WRONG (v1.2.0)
order = submit_order(side="long", ...)  # Broker doesn't understand "long"

# CORRECT (v1.3.0)
side_map = {"long": "buy", "short": "sell"}
order = submit_order(side=side_map[internal_side], ...)
```

**Lesson:**
> Always verify broker API expects exact values you're sending. Test order submission in isolation before going live.

**Prevention:**
- Unit tests for order mapping
- Log actual broker request/response
- Reconcile database with broker positions daily

---

### 2. DATABASE/BROKER RECONCILIATION (Severity: High)

**What Happened:**
- Database showed 25 open positions
- Broker (Alpaca) showed 16 open positions
- 9 "phantom" positions existed only in database

**Root Cause:**
- Database updated before broker confirmation
- Failed orders not rolled back in database

**Lesson:**
> Treat broker as source of truth. Database is cache, not authority.

**Prevention:**
```python
# Pattern: Confirm then record
broker_response = submit_order(...)
if broker_response.status == "filled":
    database.create_position(broker_order_id=broker_response.id)
else:
    database.log_failed_order(reason=broker_response.error)
```

---

### 3. POSITION SIZING INCONSISTENCY (Severity: Medium)

**What Happened:**
- All positions were 200 shares regardless of stock price
- HAL position: $5,616 (200 × $28.08)
- AAPL position: $554 (2 × $277.15)
- 10x difference in dollar exposure

**Impact:**
- Uneven risk distribution
- Large positions in cheaper stocks dominated P&L
- Win/loss on AAPL barely mattered despite good performance (+37%)

**Lesson:**
> Position sizing should be dollar-based, not share-based.

**Recommended Fix:**
```python
# Dollar-based sizing
target_position_size = 3000  # USD
shares = int(target_position_size / current_price)

# With ATR adjustment for volatility
atr_multiplier = base_atr / current_atr  # Reduce size for volatile stocks
adjusted_shares = int(shares * atr_multiplier)
```

---

### 4. NO PROFIT-TAKING MECHANISM (Severity: Medium)

**What Happened:**
- TE position: +22.10% gain, still held
- AAPL position: +37.53% gain, still held
- System holds winners indefinitely

**Impact:**
- Unrealized gains can evaporate
- No compounding of realized profits
- Drawdown includes giving back open profits

**Lesson:**
> Define exit rules for winners, not just losers.

**Recommended Fix:**
```python
# Profit-taking rules
if unrealized_pnl_pct >= 20:
    close_position(reason="profit_target_hit")
    
# Or trailing stop after profit threshold
if unrealized_pnl_pct >= 10:
    new_stop = current_price * 0.95  # 5% trailing
    if new_stop > current_stop:
        update_stop_loss(new_stop)
```

---

### 5. DRAWDOWN INVESTIGATION GAP (Severity: Medium)

**What Happened:**
- Dec 3: -$729.37 (-0.73%)
- Dec 4: -$1,029.90 (-1.04%)
- Combined: -$1,759.27 in 2 days

**What We Don't Know:**
- Which positions caused the losses?
- Was it market-wide or stock-specific?
- Did any patterns fail systematically?
- Were there news catalysts that should have triggered exits?

**Lesson:**
> After significant drawdowns, conduct forensic analysis immediately.

**Investigation Protocol:**
```
1. List all positions open during drawdown period
2. Calculate individual position P&L contribution
3. Check if correlated (all tech? all momentum?)
4. Review news/catalysts during period
5. Assess if risk manager should have intervened
6. Document findings in lessons learned
```

---

### 6. RISK LIMITS HELD (Positive Lesson)

**What Happened:**
- Max drawdown: 1.76%
- Daily loss limit ($2,000) never hit
- System continued operating through volatility

**Lesson:**
> Conservative risk limits are correct for initial deployment. Better to miss upside than blow up.

**Keep:**
- $2,000 daily loss limit
- 5 max positions
- Required stop losses on all positions

---

## Performance Data Reference

### Week 49 (Dec 2-8, 2025)

| Day | Equity | Daily P&L | Cumulative |
|-----|--------|-----------|------------|
| Mon Dec 2 | $100,234.09 | +$82.86 | +$82.86 |
| Tue Dec 3 | $99,504.72 | -$729.37 | -$646.51 |
| Wed Dec 4 | $98,474.82 | -$1,029.90 | -$1,676.41 |
| Thu Dec 5 | $98,723.52 | +$248.70 | -$1,427.71 |
| Sun Dec 8 | $98,688.52 | -$35.00 | -$1,462.71 |

### Position Performance (Dec 8 Snapshot)

**Winners:**
| Symbol | P&L | P&L % | Insight |
|--------|-----|-------|---------|
| AAPL | +$151.26 | +37.53% | Held too long - should take profits |
| TE | +$219.00 | +22.10% | Same - need exit rules |
| HPE | +$136.00 | +2.93% | Reasonable hold |

**Losers:**
| Symbol | P&L | P&L % | Insight |
|--------|-----|-------|---------|
| SANA | -$112.00 | -10.81% | Exceeded reasonable stop - investigate |
| HPQ | -$102.00 | -1.99% | Normal variance |
| HAL | -$50.00 | -0.88% | Normal variance |

---

## Architectural Lessons

### What Worked (Keep for International)
1. **Cron-based automation** - Reliable, predictable execution
2. **Risk manager as gatekeeper** - Every trade validated
3. **Structured logging** - Essential for debugging
4. **Paper trading first** - Found bugs without losing money

### What Was Overcomplicated (Simplify for International)
1. **8 microservices** - Coordination overhead significant
2. **MCP protocol** - Added complexity, HTTP 406 issues
3. **Multiple databases schemas** - v6.0 migration painful
4. **Separate services for pattern/technical** - Could be combined

### International Architecture Advantage
- Single Python script vs 8 services
- Claude API calls vs inter-service REST
- ~900 lines vs 5000+ lines
- $6/month vs $24+/month

---

## Open Questions (For Investigation)

See `OPEN-QUESTIONS-FOR-INVESTIGATION.md` for active research items derived from these lessons.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-09 | Initial capture from Week 49 reports |

---

*This document captures expensive lessons. Read before building.*
