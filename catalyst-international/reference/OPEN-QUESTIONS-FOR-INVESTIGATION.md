# Open Questions for Investigation

**System:** Catalyst Trading System - International
**Created:** 2025-12-09
**Source:** US System Week 49 Analysis
**Status:** Active Investigation Items

---

## How To Use This Document

These are open questions that emerged from the US system's first month of trading. Each represents an opportunity to:
1. Investigate the root cause
2. Test hypotheses
3. Propose solutions
4. Validate with data

When you investigate a question:
1. Document your methodology
2. Show your data/evidence
3. State your conclusion with confidence level
4. Propose action items
5. Move completed investigations to `INVESTIGATIONS-COMPLETED.md`

---

## Priority 1: Immediate (Before Live Trading)

### Q0: Historical Pattern Recognition Development

**Question:** How do we build intuition for recognizing when historical manipulation patterns are repeating?

**Context:**
- GFC, Asian Financial Crisis, LTCM - these playbooks get reused
- The goal is "this looks familiar... they did this before"
- But the players have shifted - East now using Western playbook in reverse
- Hong Kong sits at the intersection of both systems

**Investigation Steps:**
1. [ ] Study each historical crisis in STRATEGIC-PATTERNS-REFERENCE.md
2. [ ] Identify the setup signals that preceded each crisis
3. [ ] Build checklist of early warning indicators
4. [ ] Create "pattern matching" framework for news/events
5. [ ] Track current events against historical patterns
6. [ ] Document when pattern recognition triggers and outcomes

**Patterns to Internalize:**
- GFC (2008): Complexity hiding risk, misaligned incentives
- Asian Crisis (1997): Currency attacks, IMF "rescue", asset acquisition
- LTCM (1998): Leverage concentration, "can't lose" strategies
- Repo Crisis (2019): Plumbing failures, forced intervention

**East vs West Framework:**
- When news breaks, ask: Is this Western-style (direct, short-term) or Eastern-style (indirect, positional)?
- Watch for reversal patterns: Western tactics being used on Western targets
- BRICS coordination, de-dollarization signals, gold accumulation

**Expected Output:**
- Internalized pattern library
- Recognition triggers documented
- Framework for East vs West strategic analysis

**Status:** 🔴 Not Started (But study reference document immediately)

---

### Q1: Dec 3-4 Drawdown Root Cause

**Question:** What caused the $1,759 drawdown over Dec 3-4?

**Context:**
- Dec 3: -$729.37 (-0.73%)
- Dec 4: -$1,029.90 (-1.04%)
- No emergency stop triggered (under $2,000 limit)
- No documented analysis of what went wrong

**Investigation Steps:**
1. [ ] Get list of all positions open Dec 3-4
2. [ ] Calculate each position's P&L contribution
3. [ ] Check for correlation (sector, momentum, beta)
4. [ ] Review market conditions (SPY, VIX) those days
5. [ ] Check if any news catalysts should have triggered exits
6. [ ] Determine if pattern selection failed or exit timing failed

**Hypothesis to Test:**
- H1: Market-wide selloff affected all positions equally
- H2: Specific sector(s) drove the loss
- H3: Entry timing was poor (bought at local highs)
- H4: Stop losses were too wide

**Expected Output:**
- Root cause identification
- Recommendation for prevention
- Update to risk parameters if needed

**Status:** 🔴 Not Started

---

### Q2: SANA -10.81% Loss Analysis

**Question:** Why did SANA lose 10.81% and why wasn't it stopped out earlier?

**Context:**
- Entry: $5.18
- Current: $4.62
- Loss: -$112.00 (-10.81%)
- This exceeds reasonable stop loss levels

**Investigation Steps:**
1. [ ] Find SANA entry date and entry reasoning
2. [ ] Determine what stop loss was set (if any)
3. [ ] Track price action from entry to current
4. [ ] Identify if stop should have triggered
5. [ ] Check if this was a bug or intentional hold

**Hypothesis to Test:**
- H1: Stop loss was set but didn't trigger (bug)
- H2: Stop loss was too wide (10%+)
- H3: No stop loss was set (process failure)
- H4: Stop was hit but position reopened (duplicate order)

**Expected Output:**
- Explanation of why loss exceeded normal parameters
- Fix if bug found
- Policy update if process gap

**Status:** 🔴 Not Started

---

### Q3: Order Execution Verification Protocol

**Question:** How do we ensure every order is correctly executed before going live on HKEX?

**Context:**
- US system had 81 failed orders due to side mapping bug
- Database and broker got out of sync
- Problem discovered only through reconciliation

**Investigation Steps:**
1. [ ] Document IBKR order API requirements
2. [ ] Create test cases for all order types
3. [ ] Build verification script that confirms order execution
4. [ ] Design reconciliation process for daily use
5. [ ] Define alerting for order failures

**Expected Output:**
- Order verification test suite
- Daily reconciliation script
- Monitoring/alerting setup

**Status:** 🔴 Not Started

---

## Priority 2: Strategy Improvement

### Q4: Optimal Position Sizing Method

**Question:** What position sizing method maximizes risk-adjusted returns?

**Context:**
- US system uses fixed 200 shares
- Creates 10x variance in dollar exposure
- AAPL: $554 vs HAL: $5,616

**Options to Test:**
1. Fixed dollar amount (e.g., $3,000 per position)
2. ATR-based sizing (larger positions in low volatility)
3. Kelly Criterion (based on win rate and payoff ratio)
4. Equal risk (position size inversely proportional to stop distance)

**Investigation Steps:**
1. [ ] Backtest each method on US system's trade history
2. [ ] Calculate Sharpe ratio for each approach
3. [ ] Assess impact on max drawdown
4. [ ] Determine implementation complexity
5. [ ] Recommend optimal method for international system

**Expected Output:**
- Comparison table of sizing methods
- Recommended approach with rationale
- Implementation code

**Status:** 🔴 Not Started

---

### Q5: Profit-Taking Strategy

**Question:** When should we exit winning positions?

**Context:**
- AAPL: +37.53% unrealized, still held
- TE: +22.10% unrealized, still held
- No defined profit-taking rules
- Risk: Giving back gains in reversals

**Options to Test:**
1. Fixed target (exit at 10%, 15%, 20%)
2. Trailing stop after profit threshold
3. Time-based (exit after X hours regardless)
4. Technical-based (exit on reversal signal)
5. Partial exits (scale out)

**Investigation Steps:**
1. [ ] Analyze historical trades for optimal exit timing
2. [ ] Backtest each exit strategy
3. [ ] Calculate impact on win rate vs average win
4. [ ] Determine if one-size-fits-all or pattern-specific
5. [ ] Recommend exit rules for international system

**Expected Output:**
- Analysis of exit timing impact
- Recommended profit-taking rules
- Implementation code

**Status:** 🔴 Not Started

---

### Q6: Sector/Correlation Risk

**Question:** How should we manage correlation between positions?

**Context:**
- No explicit correlation checking in US system
- Unknown if Dec 3-4 drawdown was correlated positions
- HKEX has different sector dynamics than US

**Investigation Steps:**
1. [ ] Calculate correlation matrix for US system positions
2. [ ] Determine if losses were correlated
3. [ ] Research HKEX sector correlations
4. [ ] Design correlation limit (e.g., max 0.7 correlation)
5. [ ] Build correlation check into pre-trade validation

**Expected Output:**
- Correlation analysis of US system
- HKEX correlation research
- Correlation check implementation

**Status:** 🔴 Not Started

---

## Priority 3: System Enhancement

### Q7: Detecting News as Misdirection

**Question:** How can we identify when news/catalysts are being used to misdirect attention from larger player strategies?

**Context:**
- News is not just information - it can be a tool
- Sophisticated players may use news to create cover for their actual moves
- Retail tends to focus narrowly on catalysts while missing bigger picture
- "Everyone manipulates" - need to account for this in strategy

**Investigation Steps:**
1. [ ] Study historical cases where news preceded opposite moves
2. [ ] Analyze correlation between news volume and institutional positioning
3. [ ] Look for patterns: What happens in OTHER sectors during big news?
4. [ ] Track timing: When does smart money position vs when news breaks?
5. [ ] Build "misdirection score" - confidence that news is genuine vs cover

**Signals to Research:**
- Dark pool activity before/after news
- Options unusual activity timing
- Sector rotation patterns during "big news" days
- Block trade timing relative to headlines

**Expected Output:**
- Framework for evaluating news authenticity
- Signals that suggest misdirection
- Integration into catalyst scoring

**Status:** 🔴 Not Started

---

### Q8: Win Rate vs Profit Factor Optimization

**Question:** Should we optimize for win rate or profit factor?

**Context:**
- Current win rate: 56.25% (9/16 positions)
- Profit factor: Unknown (need to calculate)
- High win rate with small wins can underperform low win rate with large wins

**Investigation Steps:**
1. [ ] Calculate profit factor from US system data
2. [ ] Analyze average win vs average loss
3. [ ] Model different win rate / payoff combinations
4. [ ] Determine optimal target metrics
5. [ ] Adjust strategy parameters accordingly

**Expected Output:**
- US system profit factor calculation
- Analysis of win/loss distribution
- Target metrics for international system

**Status:** 🔴 Not Started

---

### Q8: Market Regime Detection

**Question:** Should the system behave differently in different market conditions?

**Context:**
- Dec 3-4 may have been a regime shift
- US system uses same parameters regardless of conditions
- VIX, trend, breadth could inform position sizing

**Investigation Steps:**
1. [ ] Define market regimes (trending up, down, range, volatile)
2. [ ] Analyze US system performance by regime
3. [ ] Determine if regime-specific parameters improve results
4. [ ] Build regime detection logic
5. [ ] Decide: Adapt parameters or same rules always?

**Expected Output:**
- Regime classification system
- Performance analysis by regime
- Recommendation on regime adaptation

**Status:** 🔴 Not Started

---

### Q9: HKEX-Specific Considerations

**Question:** What HKEX characteristics require different handling?

**Context:**
- Lunch break (12:00-13:00 HKT)
- Board lot trading (not fractional)
- Different volatility patterns
- Different news catalyst types
- T+2 settlement

**Investigation Steps:**
1. [ ] Research HKEX trading patterns
2. [ ] Understand board lot requirements by stock
3. [ ] Identify common HKEX catalysts
4. [ ] Map Perth time to HKEX market hours
5. [ ] Document differences from US markets

**Expected Output:**
- HKEX market guide
- Configuration adjustments for HKEX
- Risk parameter recommendations

**Status:** 🔴 Not Started

---

## Completed Investigations

*Move completed investigations here with summary of findings*

| ID | Question | Completed | Key Finding | Action Taken |
|----|----------|-----------|-------------|--------------|
| - | - | - | - | - |

---

## How to Add New Questions

When you identify a new question during trading:

```markdown
### Q[N]: [Short Title]

**Question:** [The specific question]

**Context:**
- [Why this matters]
- [What triggered this question]

**Investigation Steps:**
1. [ ] [Step 1]
2. [ ] [Step 2]
...

**Expected Output:**
- [What should result from investigation]

**Status:** 🔴 Not Started
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-09 | Initial questions from US Week 49 |

---

*Questions are opportunities. Investigate them.*
