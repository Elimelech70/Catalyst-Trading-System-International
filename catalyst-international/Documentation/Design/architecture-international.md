# Catalyst Trading System International - Agent Architecture

**Name of Application:** Catalyst Trading System International
**Name of File:** architecture-international.md
**Version:** 5.0.0
**Last Updated:** 2025-12-20
**Target Exchange:** Hong Kong Stock Exchange (HKEX)
**Broker:** Moomoo/Futu via OpenD Gateway (migrated from IBKR Dec 2025)
**Architecture:** AI Agent Pattern (Simple Droplet + Claude API + OpenD)
**Status:** Broker Migration In Progress

---

## REVISION HISTORY

**v5.0.0 (2025-12-20)** - BROKER MIGRATION: IBKR → MOOMOO/FUTU
- **MAJOR**: Migrated from Interactive Brokers to Moomoo/Futu
- Replaced IBGA Docker container with OpenD Docker container
- Added `brokers/futu.py` (FutuClient) - simpler authentication
- Real-time market data included (no more 15-min delay)
- No more IB Key 2FA issues
- OpenD setup at `/root/opend/`
- IBKR code kept at `brokers/ibkr.py` for reference

**v4.2.0 (2025-12-13)** - Cron Scheduling Configured
- Added cron jobs for automated trading (morning & afternoon sessions)
- Updated system status to "Paper Trading Scheduled"
- Added operational schedule documentation

**v4.1.0 (2025-12-11)** - Production Ready Updates (IBKR)
- Updated IBKRClient to v2.2.0 (delayed data, HK symbol fix, NaN handling)
- Clarified: Uses own PostgreSQL database (not shared with US)

**v4.0.0 (2025-12-10)** - IBGA Socket API Integration
- Replaced IBeam Web API with IBGA (heshiming/ibga) Docker container
- Uses ib_async socket API for broker communication

**v3.0.0 (2025-12-09)** - IBeam Web API Integration (Deprecated)
**v2.0.0 (2025-12-03)** - Simplified Architecture
**v1.0.0 (2025-12-03)** - Initial Agent Architecture

---

## 1. Architecture Overview

### 1.1 Current Production Setup

Minimal infrastructure with Moomoo/Futu OpenD:

- **1 small droplet** ($6/month) - IP: 209.38.87.27
- **1 Python script** (the agent)
- **1 Docker container** (OpenD for Futu gateway)
- **Cron** (the trigger)
- **Claude API** (the brain)
- **Futu OpenAPI** (the broker via futu-api)
- **PostgreSQL** (own DO Managed DB)

### 1.2 Why Moomoo/Futu (Migrated from IBKR Dec 2025)

| Aspect | IBKR (Old) | Moomoo/Futu (New) |
|--------|------------|-------------------|
| **Gateway** | IBGA Docker + Java + VNC | OpenD native binary |
| **Authentication** | IB Key 2FA (constant failures) | Password + unlock |
| **Market Data** | 15-min delayed (no subscription) | Real-time included |
| **Container deps** | Docker, Java 17, JavaFX | Docker only |
| **Debug method** | VNC into container | Simple log files |
| **Reconnection** | Manual re-auth often | Auto-reconnect |
| **API Type** | ib_async socket | futu-api socket |

### 1.3 Operational Schedule

| Session | HK Time | UTC (Server) | Cron Expression |
|---------|---------|--------------|-----------------|
| Morning | 09:30 HKT | 01:30 UTC | `30 1 * * 1-5` |
| Afternoon | 13:00 HKT | 05:00 UTC | `0 5 * * 1-5` |

**Cron Jobs:**
```cron
# Morning session start (09:30 HKT = 01:30 UTC)
30 1 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1

# Afternoon session start (13:00 HKT = 05:00 UTC)
0 5 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1
```

**HK Market Hours:**
- Morning: 09:30 - 12:00 HKT
- Lunch Break: 12:00 - 13:00 HKT (no trading)
- Afternoon: 13:00 - 16:00 HKT

### 1.4 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                DIGITALOCEAN DROPLET ($6/month)                       │
│                IP: 209.38.87.27                                      │
│                                                                      │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────────┐        │
│   │   CRON   │────▶│    AGENT     │────▶│      TOOLS       │        │
│   │          │     │   (Python)   │     │    (Functions)   │        │
│   │ 9:30 AM  │     │              │     │                  │        │
│   │ 1:00 PM  │     │ Calls Claude │     │ - scan_market()  │        │
│   │          │     │ Executes     │     │ - get_news()     │        │
│   └──────────┘     │ Tools        │     │ - execute_trade()│        │
│                    └──────────────┘     │ - check_risk()   │        │
│                           │             └────────┬─────────┘        │
│                           │                      │                  │
│                           ▼                      ▼                  │
│                    ┌─────────────┐       ┌─────────────┐            │
│                    │ Claude API  │       │   OpenD     │            │
│                    │ (Anthropic) │       │  (Docker)   │            │
│                    └─────────────┘       └──────┬──────┘            │
│                                                 │                   │
│                                                 ▼                   │
│                                          ┌─────────────┐            │
│                                          │Futu Gateway │            │
│                                          │ (Port 11111)│            │
│                                          └─────────────┘            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │ (DO Managed DB) │
                    │  International  │
                    └─────────────────┘
```

### 1.5 The Agent Loop

```
CRON triggers at market hour
        │
        ▼
┌───────────────────┐
│ 1. Build Context  │  ← Portfolio, market data, news
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. Call Claude    │  ← Send context + tools
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. Claude Returns │  ← "Call execute_trade()"
│    Tool Request   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. Execute Tool   │  ← FutuClient calls OpenD
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 5. Return Result  │  ← Tool result to Claude
│    to Claude      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 6. Loop Until     │  ← Claude may call more tools
│    Claude Done    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 7. Log & Exit     │  ← Wait for next cron
└───────────────────┘
```

---

## 2. File Structure

```
catalyst-international/
│
├── agent.py                    # Main agent script (runs via cron)
├── tools.py                    # Tool definitions for Claude
├── tool_executor.py            # Executes tool requests
├── safety.py                   # Validates all actions
│
├── brokers/
│   ├── __init__.py
│   └── futu.py                 # Moomoo/Futu client via OpenD (v1.0.0)
│
├── data/
│   ├── __init__.py
│   ├── market.py               # Market data fetching
│   ├── news.py                 # News/sentiment
│   └── database.py             # PostgreSQL client
│
├── config/
│   ├── settings.yaml           # All configuration
│   └── prompts/
│       └── system.md           # Claude's instructions
│
├── scripts/
│   └── health_check.sh         # Health monitoring
│
├── logs/                       # Daily log files
│
├── requirements.txt            # Python dependencies
└── README.md

/root/opend/                    # OpenD gateway (separate directory)
├── docker-compose.yml          # OpenD container config
├── .env                        # FUTU_USER, FUTU_PWD, FUTU_TRADE_PWD
├── logs/                       # OpenD logs
└── test_connection.py          # Connection verification script
```

---

## 3. OpenD Configuration

### 3.1 Docker Compose

```yaml
# /root/opend/docker-compose.yml
version: "3.8"

services:
  opend:
    image: ghcr.io/manhinhang/futu-opend-docker:ubuntu-stable
    container_name: catalyst-opend
    restart: unless-stopped
    ports:
      - "11111:11111"  # API port
    environment:
      - FUTU_USER=${FUTU_USER}
      - FUTU_PWD=${FUTU_PWD}
      - FUTU_RSA=
      - FUTU_TRADE_PWD=${FUTU_TRADE_PWD:-}
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "11111"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### 3.2 Environment Variables

```bash
# /root/opend/.env
FUTU_USER=<your_moomoo_account_id>
FUTU_PWD=<your_password>
FUTU_TRADE_PWD=<your_trade_unlock_password>
```

---

## 4. FutuClient Implementation

### 4.1 brokers/futu.py (v1.0.0)

Key features:
- Simple password-based authentication (no 2FA)
- Real-time market data included
- HKEX tick size rounding (`_round_to_tick()`)
- Symbol format conversion (`_format_hk_symbol()`)
- Position and order management
- Auto-reconnect support

```python
# Key methods in FutuClient:

def connect(self) -> bool:
    """Connect to OpenD and unlock trading"""

def get_quote(self, symbol: str) -> dict:
    """Get real-time quote for a symbol"""

def get_portfolio(self) -> dict:
    """Get cash, equity, positions, P&L"""

def get_positions(self) -> list[Position]:
    """Get all open positions"""

def execute_trade(self, symbol, side, quantity, order_type, limit_price,
                  stop_loss, take_profit, reason) -> OrderResult:
    """Execute trade"""

def close_position(self, symbol, reason) -> OrderResult:
    """Close a specific position"""

def close_all_positions(self, reason) -> list[OrderResult]:
    """Emergency: close all positions"""

def _format_hk_symbol(self, symbol: str) -> str:
    """Format '700' -> 'HK.00700' for Futu API"""

def _round_to_tick(self, price: float) -> float:
    """Round to valid HKEX tick size (11 tiers)"""
```

### 4.2 Symbol Format Handling

```python
# Input formats → Futu format
client._format_hk_symbol('700')   # → 'HK.00700'
client._format_hk_symbol('0700')  # → 'HK.00700'
client._format_hk_symbol('9988')  # → 'HK.09988'

# Parse back from Futu format
client._parse_hk_symbol('HK.00700')  # → '700'
```

### 4.3 Key Difference: No Bracket Orders

Unlike IBKR, Futu doesn't support native bracket orders (parent-child linked orders).
Stop loss and take profit must be managed by:
- Option A: Conditional orders (if supported by account type)
- Option B: Agent-managed stops (Claude monitors and issues sell orders)

---

## 5. Commands

### Start OpenD
```bash
cd /root/opend && docker compose up -d
```

### Check OpenD Logs
```bash
docker logs catalyst-opend --tail 50
```

### Test Connection
```bash
source /root/Catalyst-Trading-System-International/catalyst-international/venv/bin/activate
python3 /root/opend/test_connection.py
```

### Quick Connection Test
```python
from brokers.futu import FutuClient

client = FutuClient(paper_trading=True)
client.connect()
print(client.get_portfolio())
client.disconnect()
```

---

## 6. Cost Summary

| Item | Cost |
|------|------|
| DO Droplet (Basic, 1GB) | $6 |
| DO Managed PostgreSQL | $15 |
| Claude API (~200 cycles × 5K tokens) | ~$15-25 |
| Moomoo Data (real-time included) | $0 |
| **Total** | **~$36-46/month** |

**Cost Reduction**: Removed ~$20/month IBKR real-time data subscription.

---

## 7. Migration Notes

### What Changed (IBKR → Futu)
- `brokers/ibkr.py` → `brokers/futu.py`
- IBGA Docker → OpenD Docker
- Port 4000 → Port 11111
- ib_async library → futu-api library
- IB Key 2FA → Password + trade unlock
- 15-min delayed data → Real-time data

### What Stayed the Same
- Agent architecture (agent.py, tools.py, etc.)
- Claude API integration
- PostgreSQL database
- Cron scheduling
- HKEX tick size rules (same exchange)
- Tool definitions (get_quote, execute_trade, etc.)

### Files Removed (Dec 2025 cleanup)
- `brokers/ibkr.py` - IBKR client (deleted)
- `ibga/` directory - IBGA Docker setup (deleted)
- `ibeam/` directory - IBeam REST API (deleted)
- `scripts/ibga_*.py` - IBGA status scripts (deleted)

---

## 8. Known Limitations

1. **No native bracket orders** - Futu doesn't support parent-child linked orders; SL/TP must be agent-managed
2. **Account verification pending** - Moomoo AU account being set up
3. **Paper trading API** - Needs verification that Moomoo AU supports paper trading API

### Resolved Issues (Migration)
- ~~IB Key 2FA failures~~ → No 2FA with Moomoo
- ~~15-min delayed data~~ → Real-time data included
- ~~VNC debugging required~~ → Simple log files
- ~~Manual re-auth often~~ → Auto-reconnect

---

**Document Version:** 5.0.0
**Architecture:** Simple Droplet + Claude API + OpenD
**Monthly Cost:** ~$36-46
**Status:** Broker Migration In Progress
