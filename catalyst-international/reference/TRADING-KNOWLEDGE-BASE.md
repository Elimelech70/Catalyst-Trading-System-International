# Trading Knowledge Base

**System:** Catalyst Trading System - International
**Created:** 2025-12-09
**Purpose:** Accumulated trading intelligence from operations

---

## How This Works

This document grows as the system learns. Every insight, pattern, or rule validated by data gets recorded here. This becomes the institutional memory that makes the system smarter over time.

### Adding Knowledge

When you discover something:
1. Validate with data (not just intuition)
2. Document the evidence
3. State the actionable insight
4. Track if it continues to hold

---

## Market Insights

### HKEX Characteristics
*Populate as you learn the market*

| Characteristic | US Market | HKEX | Implication |
|----------------|-----------|------|-------------|
| Trading Hours | 9:30-16:00 | 9:30-12:00, 13:00-16:00 | Lunch break gap risk |
| Settlement | T+2 | T+2 | Same |
| Lot Sizes | Fractional OK | Board lots required | Position sizing constraint |
| Volatility | - | - | TBD |
| Retail vs Institutional | ~20% retail | - | TBD |

### Sector Behavior
*Document how sectors behave differently*

| Sector | Typical Behavior | Best Catalysts | Avoid When |
|--------|------------------|----------------|------------|
| Technology | - | - | - |
| Financials | - | - | - |
| Property | - | - | - |
| Consumer | - | - | - |

---

## Pattern Performance

### Validated Patterns
*Patterns that work based on actual trading data*

| Pattern | Win Rate | Avg Win | Avg Loss | Profit Factor | Sample Size | Notes |
|---------|----------|---------|----------|---------------|-------------|-------|
| - | - | - | - | - | - | Need 30+ trades to validate |

### Failed Patterns
*Patterns that looked good but don't work in practice*

| Pattern | Why It Failed | Date Retired | Notes |
|---------|---------------|--------------|-------|
| - | - | - | - |

---

## Entry Rules

### Validated Entry Conditions
*Entry conditions that improve outcomes*

| Condition | Impact on Win Rate | Evidence | Status |
|-----------|-------------------|----------|--------|
| - | - | - | - |

### Invalidated Entry Ideas
*Entry conditions that don't help*

| Condition | Why Dropped | Date | Notes |
|-----------|-------------|------|-------|
| - | - | - | - |

---

## Exit Rules

### Profit Taking
*What works for taking profits*

| Rule | Result | Evidence | Status |
|------|--------|----------|--------|
| Exit at +20% | TBD | Need data | Testing |
| Trailing stop after +10% | TBD | Need data | Testing |

### Stop Losses
*Optimal stop loss strategies*

| Strategy | Result | Evidence | Status |
|----------|--------|----------|--------|
| 2x ATR stop | TBD | Need data | Testing |
| Fixed 5% stop | TBD | Need data | Testing |

### Time Exits
*When to exit based on time*

| Rule | Result | Evidence | Status |
|------|--------|----------|--------|
| Close before lunch | TBD | Need data | Testing |
| Max hold 3 hours | TBD | Need data | Testing |

---

## Risk Management

### Position Sizing
*What position sizing works*

| Method | Result | Evidence | Recommended |
|--------|--------|----------|-------------|
| Fixed shares | Poor (US data) | 10x exposure variance | No |
| Fixed dollars | TBD | - | Testing |
| ATR-adjusted | TBD | - | Testing |

### Correlation Limits
*How to manage correlated positions*

| Finding | Evidence | Action |
|---------|----------|--------|
| - | - | - |

---

## System Performance Benchmarks

### Weekly Performance Log
*Track weekly to spot trends*

| Week | Return % | Win Rate | Trades | Max DD | Notes |
|------|----------|----------|--------|--------|-------|
| US W49 | -1.55% | 56% | 83 | 1.76% | Order bug, no profit-taking |

### Monthly Performance Log

| Month | Return % | Win Rate | Trades | Max DD | Notes |
|-------|----------|----------|--------|--------|-------|
| US Nov | -1.45% | - | - | - | First full month |

---

## Bug / Issue Log

*Track issues to prevent recurrence*

| Date | Issue | Root Cause | Fix | Prevention |
|------|-------|------------|-----|------------|
| 2025-11-?? | Order side bug | "long" not mapped to "buy" | Fixed mapping | Unit tests |
| 2025-12-08 | DB/Broker mismatch | No confirmation before record | TBD | Reconciliation |

---

## Configuration Evolution

*Track how config changes affect performance*

| Date | Parameter | Old Value | New Value | Reason | Result |
|------|-----------|-----------|-----------|--------|--------|
| - | - | - | - | - | - |

---

## Key Quotes / Principles

*Trading wisdom validated by experience*

> "Never focus on one thing so closely that you miss the bigger picture. News is used by players to make you do this, so their strategy becomes less obvious."
> — Core principle from Craig

> "Treat broker as source of truth. Database is cache, not authority."
> — Lesson from US system DB/broker mismatch

> "Conservative risk limits are correct for initial deployment. Better to miss upside than blow up."
> — Lesson from US system risk management

### The Misdirection Framework

When evaluating news or catalysts, apply this filter:

```
1. WHO is this news helping?
   - Retail traders reacting emotionally?
   - Institutions who positioned beforehand?
   - Market makers capturing spread on volatility?

2. WHAT is happening elsewhere while attention is here?
   - Other sectors moving quietly?
   - Options unusual activity?
   - Large block trades in related securities?

3. WHEN was positioning established?
   - Did smart money move before the news?
   - Is the news "new" or just now public?
   - What's the lag between event and announcement?

4. WHY now?
   - Why is this news breaking at this moment?
   - Does timing benefit someone's exit or entry?
   - Is this covering for something else?
```

The goal isn't paranoia - it's awareness. Not every news item is manipulation, but assuming none are is naive. Zoom out before you zoom in.

*Add more as you learn*

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-09 | Initial structure with US system baseline |

---

*Knowledge compounds. Document everything.*
