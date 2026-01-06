# Hourly Trading Workflow

**Name of Application:** Catalyst Trading System  
**Name of File:** hourly-trading-workflow.md  
**Version:** 1.0.0  
**Last Updated:** 2026-01-06  
**Purpose:** Document the complete hourly trading cycle from scan to monitoring

---

## Overview

The Catalyst Trading System runs a **complete trading workflow every hour** during HKEX market hours. Each cycle includes security selection, analysis, trade execution, and position monitoring.

---

## Daily Schedule

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HOURLY TRADING SCHEDULE (HKT)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  09:00 ─── PRE-MARKET SCAN ────────────────────────────────────────────    │
│            └── Find opportunities before market opens                       │
│                                                                             │
│  09:30 ─── TRADING CYCLE #1 (Market Open) ─────────────────────────────    │
│            └── Full workflow: scan → analyze → trade → monitor              │
│                                                                             │
│  10:00 ─── TRADING CYCLE #2 ───────────────────────────────────────────    │
│            └── Full workflow: scan → analyze → trade → monitor              │
│                                                                             │
│  11:00 ─── TRADING CYCLE #3 ───────────────────────────────────────────    │
│            └── Full workflow: scan → analyze → trade → monitor              │
│                                                                             │
│  12:00 ─── LUNCH BREAK CLOSE ──────────────────────────────────────────    │
│            └── Close all positions (HKEX closed 12:00-13:00)               │
│                                                                             │
│  13:00 ─── TRADING CYCLE #4 (Afternoon Open) ──────────────────────────    │
│            └── Full workflow: scan → analyze → trade → monitor              │
│                                                                             │
│  14:00 ─── TRADING CYCLE #5 ───────────────────────────────────────────    │
│            └── Full workflow: scan → analyze → trade → monitor              │
│                                                                             │
│  15:00 ─── TRADING CYCLE #6 ───────────────────────────────────────────    │
│            └── Full workflow: scan → analyze → trade → monitor              │
│                                                                             │
│  16:00 ─── END OF DAY CLOSE ───────────────────────────────────────────    │
│            └── Close all remaining positions, daily report                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Hourly Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     COMPLETE HOURLY TRADING CYCLE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CRON TRIGGER (every hour on the hour)                                      │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1: INITIALIZATION                                              │   │
│  │                                                                       │   │
│  │  • Wake up agent                                                      │   │
│  │  • Check API budget remaining                                         │   │
│  │  • Load cycle context                                                 │   │
│  │  • Connect to broker (OpenD/Moomoo)                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2: PORTFOLIO CHECK                                             │   │
│  │                                                                       │   │
│  │  Tool: get_portfolio                                                  │   │
│  │                                                                       │   │
│  │  • Current cash balance                                               │   │
│  │  • Open positions count                                               │   │
│  │  • Unrealized P&L                                                     │   │
│  │  • Daily P&L                                                          │   │
│  │                                                                       │   │
│  │  Decision: Can we take new positions?                                 │   │
│  │  • Max positions: 5                                                   │   │
│  │  • Max daily loss: HKD 16,000                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 3: SECURITY SELECTION (SCAN)                                   │   │
│  │                                                                       │   │
│  │  Tool: scan_market                                                    │   │
│  │                                                                       │   │
│  │  Filters:                                                             │   │
│  │  • Volume > 1.3x average (min_volume_ratio)                           │   │
│  │  • Price change significant                                           │   │
│  │  • Market cap appropriate                                             │   │
│  │                                                                       │   │
│  │  Output: Top 10-20 momentum candidates                                │   │
│  │                                                                       │   │
│  │  Example candidates:                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │ Symbol │ Name       │ Price  │ Change │ Volume Ratio │       │    │   │
│  │  │ 1024   │ Kuaishou   │ 76.35  │ +3.67% │ 2.1x         │       │    │   │
│  │  │ 9988   │ Alibaba    │ 85.20  │ +2.45% │ 1.8x         │       │    │   │
│  │  │ 0700   │ Tencent    │ 398.00 │ +1.92% │ 1.5x         │       │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 4: CANDIDATE ANALYSIS (For each candidate)                     │   │
│  │                                                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │ 4a. QUOTE DATA                                                 │   │   │
│  │  │     Tool: get_quote                                            │   │   │
│  │  │                                                                │   │   │
│  │  │     • Last price, bid, ask                                     │   │   │
│  │  │     • Volume (current vs average)                              │   │   │
│  │  │     • Daily high/low                                           │   │   │
│  │  │     • Spread analysis                                          │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                           │                                           │   │
│  │                           ▼                                           │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │ 4b. TECHNICAL ANALYSIS                                         │   │   │
│  │  │     Tool: get_technicals                                       │   │   │
│  │  │                                                                │   │   │
│  │  │     • RSI (30-70 ideal, avoid >80 or <20)                      │   │   │
│  │  │     • MACD and signal line                                     │   │   │
│  │  │     • Support/Resistance levels                                │   │   │
│  │  │     • VWAP position                                            │   │   │
│  │  │     • EMA 9/20/50                                              │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                           │                                           │   │
│  │                           ▼                                           │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │ 4c. PATTERN DETECTION                                          │   │   │
│  │  │     Tool: detect_patterns                                      │   │   │
│  │  │                                                                │   │   │
│  │  │     Patterns detected:                                         │   │   │
│  │  │     • breakout (above resistance + volume)                     │   │   │
│  │  │     • near_breakout (within 1% of resistance)                  │   │   │
│  │  │     • momentum_continuation (>3% + high volume)                │   │   │
│  │  │     • bull_flag (uptrend + consolidation)                      │   │   │
│  │  │     • ascending_triangle (flat top, rising lows)               │   │   │
│  │  │                                                                │   │   │
│  │  │     Output includes:                                           │   │   │
│  │  │     • Pattern type and confidence (0-1)                        │   │   │
│  │  │     • Entry price                                              │   │   │
│  │  │     • Stop loss level                                          │   │   │
│  │  │     • Target price                                             │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                           │                                           │   │
│  │                           ▼                                           │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │ 4d. NEWS & CATALYST CHECK                                      │   │   │
│  │  │     Tool: get_news                                             │   │   │
│  │  │                                                                │   │   │
│  │  │     • Recent headlines                                         │   │   │
│  │  │     • Sentiment score                                          │   │   │
│  │  │     • Catalyst identification:                                 │   │   │
│  │  │       - Earnings                                               │   │   │
│  │  │       - Product launch                                         │   │   │
│  │  │       - Analyst upgrade                                        │   │   │
│  │  │       - Industry news                                          │   │   │
│  │  │       - Partnership/deal                                       │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 5: ENTRY DECISION (Tiered Criteria)                            │   │
│  │                                                                       │   │
│  │  TIER 1 - STRONG SETUP (Full Size)                                   │   │
│  │  ✓ Volume > 2.0x                                                      │   │
│  │  ✓ RSI 30-70                                                          │   │
│  │  ✓ Pattern AND Catalyst                                               │   │
│  │  ✓ R:R >= 2:1                                                         │   │
│  │                                                                       │   │
│  │  TIER 2 - GOOD SETUP (Full Size)                                      │   │
│  │  ✓ Volume > 1.5x                                                      │   │
│  │  ✓ RSI 30-75                                                          │   │
│  │  ✓ Pattern OR Catalyst                                                │   │
│  │  ✓ R:R >= 1.5:1                                                       │   │
│  │                                                                       │   │
│  │  TIER 3 - LEARNING TRADE (Half Size)                                  │   │
│  │  ✓ Volume > 1.3x                                                      │   │
│  │  ✓ Momentum > 3%                                                      │   │
│  │  ✓ At least one signal                                                │   │
│  │  ✓ R:R >= 1.5:1                                                       │   │
│  │                                                                       │   │
│  │  PASS (Skip):                                                         │   │
│  │  ✗ RSI > 80 or < 20                                                   │   │
│  │  ✗ Volume below average                                               │   │
│  │  ✗ No clear stop loss                                                 │   │
│  │  ✗ Already at max positions                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 6: RISK VALIDATION                                             │   │
│  │                                                                       │   │
│  │  Tool: check_risk                                                     │   │
│  │                                                                       │   │
│  │  Validates:                                                           │   │
│  │  • Position size within limits (max HKD 40,000)                       │   │
│  │  • Daily loss limit not exceeded                                      │   │
│  │  • Stop loss defined                                                  │   │
│  │  • Risk/reward acceptable                                             │   │
│  │  • Not duplicate position                                             │   │
│  │                                                                       │   │
│  │  Output: approved=true/false, reason                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼ (if approved)                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 7: TRADE EXECUTION                                             │   │
│  │                                                                       │   │
│  │  Tool: execute_trade                                                  │   │
│  │                                                                       │   │
│  │  Parameters:                                                          │   │
│  │  • symbol: "1024"                                                     │   │
│  │  • side: "BUY"                                                        │   │
│  │  • quantity: 2000 (lot-adjusted)                                      │   │
│  │  • order_type: "LIMIT" or "MARKET"                                    │   │
│  │  • limit_price: 76.35                                                 │   │
│  │  • stop_loss: 74.85 (-2%)                                             │   │
│  │  • take_profit: 79.35 (+4%)                                           │   │
│  │  • reason: "Breakout + earnings catalyst"                             │   │
│  │                                                                       │   │
│  │  Order submitted to Moomoo/OpenD → HKEX                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼ (automatic on BUY)                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 8: POSITION MONITORING STARTS                                  │   │
│  │                                                                       │   │
│  │  Triggered by: tool_executor.py after successful BUY                  │   │
│  │                                                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │                  MONITORING LOOP                               │   │   │
│  │  │                  (Every 5 minutes)                             │   │   │
│  │  │                                                                │   │   │
│  │  │  1. Get current quote + technicals                             │   │   │
│  │  │  2. Detect exit signals (FREE - rules based):                  │   │   │
│  │  │     • P&L: stop loss (-3%), take profit (+8%)                  │   │   │
│  │  │     • Technical: RSI >85, MACD cross                           │   │   │
│  │  │     • Volume: dying (<25%)                                     │   │   │
│  │  │     • Time: market close, lunch break                          │   │   │
│  │  │                                                                │   │   │
│  │  │  3. Decision:                                                  │   │   │
│  │  │     STRONG signal → EXIT immediately                           │   │   │
│  │  │     MODERATE signals → Ask Haiku (~$0.05)                      │   │   │
│  │  │     WEAK/NONE → HOLD                                           │   │   │
│  │  │                                                                │   │   │
│  │  │  4. If EXIT: close_position()                                  │   │   │
│  │  │                                                                │   │   │
│  │  │  5. Notify big_bro with result                                 │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  Continues until:                                                     │   │
│  │  • Position closed (stop/target hit)                                  │   │
│  │  • Market closes (16:00 HKT)                                          │   │
│  │  • Error occurs (fallback to manual)                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 9: LOG & COMPLETE                                              │   │
│  │                                                                       │   │
│  │  Tool: log_decision                                                   │   │
│  │                                                                       │   │
│  │  Records:                                                             │   │
│  │  • Decision type (TRADE, PASS, CLOSE)                                 │   │
│  │  • Symbol analyzed                                                    │   │
│  │  • Reasoning                                                          │   │
│  │  • Tools called                                                       │   │
│  │  • API cost                                                           │   │
│  │                                                                       │   │
│  │  Updates consciousness:                                               │   │
│  │  • claude_state (mode, last_action, api_spend)                        │   │
│  │  • claude_observations (if notable)                                   │   │
│  │  • claude_learnings (if pattern confirmed)                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  CYCLE COMPLETE - Wait for next hourly trigger                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Model

### Per Cycle

| Component | Cost |
|-----------|------|
| Claude API (Sonnet) | ~$0.01-0.02 |
| Tool calls (10-15) | Included |
| Position monitoring | FREE (rules) |
| Haiku consultation | ~$0.05 (if needed) |
| **Total per cycle** | **~$0.01-0.07** |

### Daily (6 trading cycles)

| Item | Cycles | Cost |
|------|--------|------|
| Trading cycles | 6 | ~$0.06-0.42 |
| Close cycles | 2 | ~$0.02-0.04 |
| Pre-market scan | 1 | ~$0.01-0.02 |
| Heartbeats | 8 | ~$0.00 (minimal) |
| Position monitoring | Variable | ~$0.00-0.50 |
| **Daily total** | | **~$0.10-1.00** |

### Monthly Budget

- Daily budget: $5.00
- Expected daily use: ~$0.50-1.50
- Surplus available for position monitoring

---

## Deployment

### Install

```bash
# 1. SSH to server
ssh root@137.184.244.45

# 2. Navigate to project
cd /root/Catalyst-Trading-System-International/catalyst-international

# 3. Run deployment script
chmod +x deploy-hourly-workflow.sh
./deploy-hourly-workflow.sh
```

### Verify

```bash
# Check cron installed
cat /etc/cron.d/catalyst-intl

# Monitor next cycle
tail -f logs/cron.log

# Check consciousness
# (via Claude Desktop MCP)
catalyst-consciousness:get_trading_overview
```

### Rollback

```bash
# If issues occur
cp backups/YYYYMMDD_HHMMSS/catalyst-intl.cron.backup /etc/cron.d/catalyst-intl
systemctl restart cron
```

---

## Summary Table

| Time (HKT) | Mode | Actions |
|------------|------|---------|
| 09:00 | scan | Pre-market scan only |
| 09:30 | trade | Full workflow (market open) |
| 10:00 | trade | Full workflow |
| 11:00 | trade | Full workflow |
| 12:00 | close | Close all (lunch break) |
| 13:00 | trade | Full workflow (afternoon open) |
| 14:00 | trade | Full workflow |
| 15:00 | trade | Full workflow |
| 16:00 | close | Close all (EOD) |

**Total: 6 full trading cycles per day**

---

**END OF DOCUMENT**
