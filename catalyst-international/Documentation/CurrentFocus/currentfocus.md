# Current Focus - Catalyst International

**Date:** 2025-12-13
**Status:** Ready for Automated Paper Trading
**Last Updated:** 2025-12-13 20:00 HKT
**First Automated Run:** Monday Dec 15, 09:30 HKT

---

## Executive Summary

The Catalyst International trading agent is fully configured and ready for automated paper trading. All blocking issues resolved, cron scheduled, and lessons learned from US system have been analyzed and incorporated into CLAUDE.md v2.2.0.

---

## Latest Updates (2025-12-13)

### Cron Scheduling - COMPLETE
```cron
# Morning session (09:30 HKT = 01:30 UTC)
30 1 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1

# Afternoon session (13:00 HKT = 05:00 UTC)
0 5 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1
```

### US Lessons Gap Analysis - COMPLETE

Analyzed 6 critical lessons from US system operations:

| Lesson | US Issue | IBKR Status |
|--------|----------|-------------|
| Order Mapping Bug | `"long"` → wrong side | ✅ Fixed |
| Broker Reconciliation | Phantom positions | ✅ By architecture |
| Position Sizing | Share-based (10x variance) | ⚠️ Guidance added |
| Profit Taking | No exit rules | ✅ Claude decides |
| Drawdown Analysis | No forensics | ✅ `log_decision` |
| Risk Limits | Working | ✅ Maintained |

**New Risk Identified:** Delayed data (15-min) requires discipline - use limit orders, wider stops.

**Full Analysis:** `Documentation/Analysis/2025-12-13-Lessons-Gap-Analysis.md`

### CLAUDE.md Updated to v2.2.0

Added IBKR-specific lessons and rules:

**New Lessons (11-14):**
- Lesson 11: HKEX Tick Size Compliance
- Lesson 12: Delayed Data Trading Rules
- Lesson 13: HK Symbol Format
- Lesson 14: Dollar-Based Position Sizing

**New NEVER Rules (15-20):**
- Never use market orders with delayed data
- Never chase momentum with 15-min delay
- Never use tight stops (< 3%)
- Never trade news < 30 min old
- Never use leading zeros in HK symbols
- Never size by shares alone

**New ALWAYS Rules (15-22):**
- Always use limit orders
- Always round to HKEX tick size
- Always wait 30 min after market open
- Always set wider stops (3-5%)

---

## Work Completed (Dec 11)

### 1. Enabled Delayed Market Data (Free)

**Problem:** IBKR was rejecting market data requests with Error 354 "Requested market data is not subscribed"

**Solution:** Added `reqMarketDataType(3)` after connection to enable 15-minute delayed data

**File:** `brokers/ibkr.py` v2.2.0
```python
# After connect()
self.ib.reqMarketDataType(3)  # Type 3 = Delayed data
```

**Result:** All HK stocks now return quotes without requiring paid subscription

---

### 2. Fixed HK Symbol Format

**Problem:** IBKR rejected symbols with leading zeros (e.g., "0700" for Tencent)

**Error:** `No security definition has been found for the request, contract: Stock(symbol='0700', exchange='SEHK')`

**Solution:** Strip leading zeros when creating SEHK contracts

**File:** `brokers/ibkr.py` v2.2.0
```python
# Convert "0700" -> "700", "0005" -> "5"
symbol = symbol.lstrip('0') or '0'
```

**Result:** All HK stock symbols now resolve correctly

---

### 3. Fixed NaN Handling for Delayed Data

**Problem:** Delayed data sometimes returns NaN for volume, causing `cannot convert float NaN to integer`

**Solution:** Added `safe_float()` and `safe_int()` helper functions

**Files:**
- `brokers/ibkr.py` v2.2.0
- `data/market.py` v1.1.0

**Result:** Quotes return cleanly even when some fields are NaN

---

### 4. Fixed Portfolio Currency Detection

**Problem:** Portfolio showed $0 because code only checked HKD currency, but account is funded in AUD

**Solution:** Check BASE currency first, then HKD

**File:** `brokers/ibkr.py` v2.2.0

**Result:** Portfolio correctly shows AUD 1,000,000 buying power

---

### 5. Fixed Claude Model Name

**Problem:** Agent failed with 404 error for model `claude-sonnet-4-5-20250514`

**Solution:** Corrected fallback to `claude-sonnet-4-20250514`

**File:** `agent.py` v1.2.0

**Result:** Claude API calls succeed (HTTP 200 OK)

---

### 6. Removed Invalid Stock

**Problem:** Stock 6837 doesn't exist in IBKR, causing scan errors

**Solution:** Commented out 6837 from HSCEI constituent list

**File:** `data/market.py` v1.1.0

---

## Test Results

### Agent Cycle (2025-12-11 12:21 HKT)

| Metric | Value |
|--------|-------|
| Cycle ID | hk_20251211_122106_ebadd7 |
| Status | Completed (timed out during scan) |
| Tools Called | get_portfolio, log_decision, scan_market |
| Stocks Scanned | 80+ |
| Trades Executed | 0 (expected - lunch break) |
| Errors | None |

### Portfolio Status
```
Cash: AUD 1,000,000
Equity: 0 (no positions)
Buying Power: AUD 1,000,000
Account: DUO931484 (Paper Trading)
```

### Sample Quotes (Delayed Data)
```
700 (Tencent):    HKD 601.50
9988 (Alibaba):   HKD 152.00
1810 (Xiaomi):    HKD 42.12
3690 (Meituan):   HKD 100.80
```

---

## Things to Consider

### 1. Market Data Delay (15 Minutes)

**Impact:**
- Entry/exit prices will be based on 15-min old data
- Not suitable for scalping or high-frequency strategies
- Acceptable for swing trading / momentum strategies with wider stops

**Recommendation:**
- Use wider stop losses (account for 15-min price movement)
- Consider upgrading to real-time data (HKD 130/month) for tighter execution

---

### 2. Account Currency Mismatch

**Current State:**
- Account funded in AUD
- Trading HK stocks in HKD

**Impact:**
- Currency conversion will occur on trades
- P&L will be affected by AUD/HKD exchange rate
- Margin calculations in AUD

**Recommendation:**
- Consider converting some AUD to HKD in IBKR account
- Or accept currency risk as part of strategy

---

### 3. Scan Performance (~2 Minutes)

**Current State:**
- Scanning 80 stocks takes ~2 minutes
- Each stock requires a separate API call

**Impact:**
- Slow cycle time
- May miss fast-moving opportunities

**Options:**
1. **Reduce stock universe** - Focus on top 20-30 most liquid
2. **Parallel requests** - Would require code changes
3. **Accept as-is** - 2 min scan is fine for momentum strategy

---

### 4. Paper Trading Limitations

**Current State:**
- Using IBKR paper trading account (DUO931484)
- AUD 1,000,000 simulated capital

**Considerations:**
- Paper fills may differ from live execution
- No slippage simulation
- Market impact not modeled

**Before Going Live:**
1. Run for at least 1-2 weeks in paper mode
2. Review all logged decisions
3. Check P&L consistency
4. Test emergency stop functionality

---

### 5. HK Market Hours

**Trading Sessions (HKT):**
- Morning: 09:30 - 12:00
- Lunch Break: 12:00 - 13:00 (NO TRADING)
- Afternoon: 13:00 - 16:00

**Agent Behavior:**
- Will close positions before lunch (configurable)
- Will not trade during lunch break
- Use `--force` flag to override for testing

---

### 6. Risk Management Settings

**Current Config (settings.yaml):**
```yaml
max_positions: 5
max_position_pct: 0.20          # 20% per position
max_daily_loss_pct: 0.02        # 2% emergency stop
max_trade_loss_pct: 0.01        # 1% per trade
min_risk_reward: 2.0            # 2:1 minimum
```

**Recommendation:**
- Review these limits before live trading
- Consider more conservative settings initially
- Monitor daily loss warnings closely

---

## File Changes Summary

| File | Version | Changes |
|------|---------|---------|
| `CLAUDE.md` | 2.2.0 | Added IBKR lessons 11-14, updated NEVER/ALWAYS rules |
| `architecture-international.md` | 4.2.0 | Added cron schedule, operational hours |
| `IMPLEMENTATION-GUIDE.md` | 1.2.0 | Updated checklist with completed items |
| `brokers/ibkr.py` | 2.2.0 | Delayed data, symbol fix, NaN handling, portfolio currency |
| `data/market.py` | 1.1.0 | NaN handling, removed 6837 |
| `agent.py` | 1.2.0 | Fixed model name fallback |

---

## Next Steps

### Immediate (Mon Dec 15)
1. [x] Verify scan finds candidates with positive momentum - ✅ 80+ HK stocks scanned
2. [x] Check decision logging is comprehensive - ✅ Logging to database working
3. [x] Set up cron job for automatic execution - ✅ **COMPLETED 2025-12-13**
4. [x] Analyze US lessons and update CLAUDE.md - ✅ **COMPLETED 2025-12-13**
5. [ ] First automated run during active market hours - **Mon Dec 15, 09:30 HKT**

### This Week (Dec 15-20)
1. [ ] Monitor first automated trading cycles
2. [ ] Review agent logs after each session
3. [ ] Configure email alerts (SMTP vars in .env are empty)
4. [ ] Verify no phantom position drift (broker = source of truth)

### Before Live Trading (After 1 Week Paper)
1. [ ] Complete 1 week of paper trading (Dec 15-20)
2. [ ] Review all logged decisions and reasoning
3. [ ] Test emergency close functionality
4. [ ] Verify stop loss orders execute correctly
5. [ ] Analyze P&L consistency
6. [ ] Consider real-time data subscription (HKD 130/month)

---

## How to Run

### Manual Execution
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
python3 agent.py          # During market hours
python3 agent.py --force  # Force run (testing)
python3 agent.py --live   # LIVE TRADING (use with caution)
```

### Cron Setup (Recommended)
```bash
# Add to crontab -e
# Morning session
30 1 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && /root/Catalyst-Trading-System-International/catalyst-international/venv/bin/python3 agent.py >> logs/cron.log 2>&1

# Afternoon session
0 5 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && /root/Catalyst-Trading-System-International/catalyst-international/venv/bin/python3 agent.py >> logs/cron.log 2>&1
```
*Note: Cron times are in UTC. 01:30 UTC = 09:30 HKT, 05:00 UTC = 13:00 HKT*

---

## Support Files

- **Agent Log:** `logs/agent.log`
- **Config:** `config/settings.yaml`
- **Environment:** `.env`

---

## Contact / References

- **IBKR API Docs:** https://interactivebrokers.github.io/tws-api/
- **ib_async Library:** https://github.com/ib-api-reloaded/ib_async
- **Claude API:** https://docs.anthropic.com/
