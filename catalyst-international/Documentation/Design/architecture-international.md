# Catalyst Trading System International - Agent Architecture

**Name of Application:** Catalyst Trading System International  
**Name of File:** architecture-international.md  
**Version:** 5.2.0  
**Last Updated:** 2026-01-06  
**Target Exchange:** Hong Kong Stock Exchange (HKEX)  
**Broker:** Moomoo via OpenD Gateway  
**Architecture:** AI Agent Pattern (Simple Droplet + Claude API + OpenD)  
**Status:** Production - First Autonomous Trade Executed

---

## REVISION HISTORY

**v5.2.0 (2026-01-06)** - FIRST AUTONOMOUS TRADE MILESTONE
- **MILESTONE**: First autonomous trade executed (BUY 1024 Kuaishou)
- Added patterns.py v1.1.0 with relaxed detection (near_breakout, momentum_continuation)
- Fixed 4 critical bugs in tool_executor.py:
  - OrderResult dataclass access (not subscriptable)
  - has_position method (doesn't exist, use get_positions)
  - AlertSender callable check (has .send() method)
  - Portfolio KeyError (use .get() with defaults)
- Fixed moomoo.py get_portfolio() missing fields (positions, equity, position_count, daily_pnl_pct)
- Fixed market.py quote field mapping (last_price not last)
- Portfolio: 4 positions, +HKD 20,625 unrealized P&L

**v5.1.0 (2025-12-29)** - MOOMOO BRANDING CLEANUP
- Removed all Futu references - use Moomoo terminology only
- Fixed Python SDK: `moomoo-api` (not `futu-api`)
- Fixed imports: `from moomoo import ...` (not `from futu import ...`)

**v5.0.0 (2025-12-20)** - BROKER MIGRATION: IBKR → MOOMOO
- Migrated from Interactive Brokers to Moomoo
- Replaced IBGA Docker container with OpenD native binary

---

## 1. Architecture Overview

### 1.1 Current Production Setup

Minimal infrastructure with Moomoo OpenD (native binary):

- **1 small droplet** ($6/month) - IP: 137.184.244.45
- **1 Python agent** (agent.py v2.2.0)
- **OpenD** (native binary gateway - NO Docker)
- **Cron** (the trigger)
- **Claude API** (the brain - Sonnet model)
- **Moomoo API** (the broker via `moomoo-api` Python SDK)
- **PostgreSQL** (DigitalOcean Managed DB)

### 1.2 Current Portfolio Status (2026-01-06)

| Symbol | Stock | Shares | Entry | Current | P&L | P&L % |
|--------|-------|--------|-------|---------|-----|-------|
| 981 | SMIC | 2,500 | $70.55 | $76.95 | +$16,000 | +9.1% |
| 2382 | Sunny Optical | 2,700 | $64.95 | $66.70 | +$4,725 | +2.7% |
| 1810 | Xiaomi | 4,600 | $38.88 | $38.88 | $0 | 0% |
| 1024 | Kuaishou | 2,000 | $76.35 | $76.30 | -$100 | -0.1% |

**Total Unrealized P&L: +HKD 20,625 (+2.0%)**

### 1.3 Operational Schedule

| Session | HK Time | UTC (Server) | Cron Expression |
|---------|---------|--------------|-----------------|
| Morning | 09:30 HKT | 01:30 UTC | `30 1 * * 1-5` |
| Afternoon | 13:00 HKT | 05:00 UTC | `0 5 * * 1-5` |

---

## 2. File Versions

### 2.1 Core Files

| File | Version | Last Updated | Purpose |
|------|---------|--------------|---------|
| `agent.py` | 2.2.0 | 2026-01-02 | Main trading agent with tiered entry criteria |
| `tool_executor.py` | 2.2.1 | 2026-01-06 | Tool routing with bug fixes |
| `brokers/moomoo.py` | 1.2.1 | 2026-01-06 | Moomoo client with portfolio fixes |
| `data/patterns.py` | 1.1.0 | 2026-01-06 | Relaxed pattern detection |
| `data/market.py` | 2.1.1 | 2026-01-06 | Quote field mapping fixes |
| `data/news.py` | 1.0.0 | 2025-12-06 | News and sentiment |
| `tools.py` | 1.0.0 | 2025-12-06 | Tool definitions |
| `safety.py` | 1.0.0 | 2025-12-06 | Risk validation |

### 2.2 Configuration Files

| File | Purpose |
|------|---------|
| `config/settings.yaml` | Trading parameters |
| `.env` | Environment variables |

---

## 3. Trading Strategy

### 3.1 SYSTEM_PROMPT - Tiered Entry Criteria (v2.2.0)

The agent uses a tiered approach instead of AND-based criteria:

**Tier 1 - Strong Setup (Full Size)**
- Volume > 2.0x, RSI 30-70, Pattern AND Catalyst, R:R >= 2:1

**Tier 2 - Good Setup (Full Size)**
- Volume > 1.5x, RSI 30-75, Pattern OR Catalyst, R:R >= 1.5:1
- Within 1% of breakout counts as breakout

**Tier 3 - Learning Trade (Half Size)**
- Volume > 1.3x, RSI 25-80, Strong momentum (>3% daily)
- At least one signal (pattern forming, news, sector)

### 3.2 Pattern Detection (v1.1.0)

| Pattern | Description | Confidence |
|---------|-------------|------------|
| `breakout` | Above resistance with volume (2% tolerance) | 0.5-0.85 |
| `near_breakout` | Within 1% of resistance | 0.4-0.6 |
| `momentum_continuation` | >3% daily gain + 1.5x volume | 0.35-0.5 |
| `bull_flag` | Uptrend + tight consolidation | 0.5-0.9 |
| `ascending_triangle` | Flat resistance, rising lows | 0.6-0.9 |
| `ABCD` | Harmonic pattern | 0.6-0.8 |

---

## 4. MoomooClient Implementation

### 4.1 Key Methods

```python
class MoomooClient:
    def connect(self) -> bool
    def disconnect(self)
    def get_quote(self, symbol: str) -> dict
    def get_quotes_batch(self, symbols: list) -> list  # v1.1.0
    def get_portfolio(self) -> dict  # Fixed in v1.2.1
    def get_positions(self) -> List[Position]
    def execute_trade(...) -> OrderResult
    def close_position(symbol, reason) -> OrderResult
    def close_all_positions(reason) -> List[OrderResult]
    def get_historical_data(symbol, days, ktype) -> pd.DataFrame  # v1.2.0
```

### 4.2 Portfolio Response (Fixed v1.2.1)

```python
{
    "cash": 315695.0,
    "total_assets": 1019608.0,
    "equity": 1019608.0,           # Added - alias for total_assets
    "market_value": 703913.0,
    "positions": [...],             # Added - list of position dicts
    "position_count": 4,            # Added
    "unrealized_pnl": 20625.0,
    "daily_pnl": 0.0,               # Added
    "daily_pnl_pct": 0.0,           # Added
    "currency": "HKD"
}
```

### 4.3 Quote Response (Fixed v2.1.1)

```python
{
    "symbol": "1024",
    "last": 76.30,          # Mapped from last_price
    "bid": 76.25,           # Mapped from bid_price
    "ask": 76.35,           # Mapped from ask_price
    "high": 77.50,          # Mapped from high_price
    "low": 75.80,           # Mapped from low_price
    "open": 76.00,          # Mapped from open_price
    "volume": 31000000,
    "change": 0.30,         # Calculated if not provided
    "change_pct": 0.39      # Calculated if not provided
}
```

---

## 5. Bug Fixes Applied (2026-01-06)

### 5.1 tool_executor.py

| Bug | Error | Fix |
|-----|-------|-----|
| OrderResult access | `TypeError: 'OrderResult' object is not subscriptable` | Use `result.status` not `result["status"]` |
| has_position | `AttributeError: 'MoomooClient' has no attribute 'has_position'` | Query `get_positions()` and check list |
| AlertSender | `TypeError: 'AlertSender' object is not callable` | Check for `.send()` method |
| Portfolio KeyError | `KeyError: 'daily_pnl_pct'` | Use `.get()` with defaults |

### 5.2 brokers/moomoo.py

| Bug | Fix |
|-----|-----|
| Missing `positions` field | Call `get_positions()` and include in response |
| Missing `equity` field | Add as alias for `total_assets` |
| Missing `position_count` | Add count of positions |
| Missing `daily_pnl_pct` | Add with default 0.0 |

### 5.3 data/market.py

| Bug | Fix |
|-----|-----|
| Field name mismatch | Map `last_price` → `last`, `bid_price` → `bid`, etc. |
| Missing change calculation | Calculate from `prev_close` if not provided |

---

## 6. Commands

### Start OpenD
```bash
sudo systemctl start opend
```

### Check Status
```bash
sudo systemctl status opend
```

### Manual Agent Run
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
python3 agent.py --force
```

### Test Close Position
```python
from brokers.moomoo import MoomooClient
client = MoomooClient(paper_trading=True)
client.connect()
result = client.close_position("1024", reason="Test close")
print(result)
client.disconnect()
```

---

## 7. Cost Summary

| Item | Cost |
|------|------|
| DO Droplet (Basic, 1GB) | $6 |
| DO Managed PostgreSQL | $15 |
| Claude API (~50 cycles × 4K tokens) | ~$5-10 |
| Moomoo Data (real-time included) | $0 |
| **Total** | **~$26-31/month** |

---

## 8. Related Documents

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Agent operational guidelines |
| `database-schema.md` | Database schema |
| `functional-specification.md` | Tool specifications |

---

**END OF ARCHITECTURE DOCUMENT v5.2.0**
