# Current Focus - Catalyst Trading System International

**Last Updated:** 2025-12-20
**Status:** Broker Migration In Progress
**Next Action:** Complete Moomoo account setup and test OpenD connection

---

## Executive Summary

Migrating from Interactive Brokers (IBKR) to Moomoo/Futu due to persistent IB Key 2FA authentication failures. OpenD infrastructure is ready; awaiting Moomoo account verification.

---

## Current State

### What's Working
| Component | Status | Notes |
|-----------|--------|-------|
| OpenD Docker image | ✅ Ready | `ghcr.io/manhinhang/futu-opend-docker:ubuntu-stable` |
| OpenD docker-compose | ✅ Ready | `/root/opend/docker-compose.yml` |
| FutuClient | ✅ Ready | `brokers/futu.py` v1.0.0 |
| Test script | ✅ Ready | `/root/opend/test_connection.py` |
| futu-api package | ✅ Installed | v9.6.5608 |
| Documentation | ✅ Updated | CLAUDE.md v3.0.0, architecture v5.0.0 |
| GitHub | ✅ Pushed | Commit `69e5785` |

### What's Pending
| Item | Status | Blocker |
|------|--------|---------|
| Moomoo AU account | ⏳ Pending | Account verification in progress |
| OpenD credentials | ⏳ Waiting | Need account ID + password |
| OpenD container | ⏳ Not started | Needs credentials in `/root/opend/.env` |
| Connection test | ⏳ Blocked | Needs OpenD running |
| Paper trading test | ⏳ Blocked | Needs connection |

### What Was Removed (Dec 20, 2025)
- IBKR broker (`brokers/ibkr.py`)
- IBGA Docker container + setup (`ibga/`)
- IBeam REST API (`ibeam/`)
- Old agent module (`agent/`)
- All IB-related scripts
- `ib_async` Python package
- Preflight checks (no longer needed)

---

## Infrastructure

### Droplet
- **IP:** 209.38.87.27
- **Provider:** DigitalOcean ($6/month)
- **OS:** Ubuntu

### OpenD Gateway (New)
```
/root/opend/
├── docker-compose.yml    # Container config
├── .env                  # Credentials (EMPTY - needs filling)
├── logs/                 # OpenD logs
└── test_connection.py    # Connection test
```

**Port:** 11111 (Futu API)

### Trading System
```
/root/Catalyst-Trading-System-International/catalyst-international/
├── agent.py              # Main entry point (v2.0.0)
├── brokers/futu.py       # Moomoo/Futu client (v1.0.0)
├── tool_executor.py      # Tool routing (v2.0.0)
├── tools.py              # Claude tool definitions
├── data/market.py        # Market data (v2.0.0)
└── config/settings.py    # Configuration
```

---

## Next Steps (In Order)

### 1. Complete Moomoo Account Setup
- [ ] Verify Moomoo AU account
- [ ] Get account ID (numeric)
- [ ] Set up trade password

### 2. Configure OpenD
```bash
# Fill in credentials
nano /root/opend/.env

# Add:
FUTU_USER=<your_account_id>
FUTU_PWD=<your_password>
FUTU_TRADE_PWD=<your_trade_password>
```

### 3. Start OpenD
```bash
cd /root/opend && docker compose up -d
docker logs catalyst-opend -f
```

### 4. Test Connection
```bash
source /root/Catalyst-Trading-System-International/catalyst-international/venv/bin/activate
python3 /root/opend/test_connection.py
```

### 5. Test Paper Trading
```bash
# Quick test
python3 -c "
from brokers.futu import FutuClient
client = FutuClient(paper_trading=True)
client.connect()
print(client.get_portfolio())
print(client.get_quote('700'))
client.disconnect()
"
```

### 6. Update Cron Jobs (if needed)
Current cron runs agent.py at:
- 01:30 UTC (09:30 HKT) - Morning session
- 05:00 UTC (13:00 HKT) - Afternoon session

---

## Key Files Reference

| File | Version | Purpose |
|------|---------|---------|
| `CLAUDE.md` | 3.0.0 | Claude Code instructions |
| `agent.py` | 2.0.0 | Main trading agent |
| `brokers/futu.py` | 1.0.0 | Moomoo/Futu client |
| `tool_executor.py` | 2.0.0 | Tool call routing |
| `data/market.py` | 2.0.0 | Market data provider |
| `architecture-international.md` | 5.0.0 | System architecture |

---

## Known Issues / Risks

1. **No native bracket orders** - Futu doesn't support parent-child linked SL/TP orders. Agent must manage stops manually.

2. **Paper trading API** - Need to verify Moomoo AU supports paper trading via OpenAPI.

3. **Account region** - If Moomoo AU doesn't support OpenAPI for HKEX, may need Futu HK account.

---

## Recent Changes

### 2025-12-20 - Broker Migration
- Removed all IBKR/IBGA code (7,517 lines deleted)
- Added FutuClient (`brokers/futu.py`)
- Updated all imports to use Futu
- Set up OpenD Docker infrastructure
- Updated documentation to v3.0.0/v5.0.0

### 2025-12-16 to 2025-12-19 - IBGA Failures
- Trading offline for 4 days due to IB Key 2FA failures
- IBGA stuck in authentication loop
- Decision made to migrate to Moomoo/Futu

---

## Contacts / Resources

- **Moomoo AU:** https://www.moomoo.com/au
- **Futu OpenAPI Docs:** https://openapi.futunn.com/futu-api-doc/
- **OpenD Docker:** https://github.com/manhinhang/futu-opend-docker

---

**Next Session:** Fill in Moomoo credentials → Start OpenD → Test connection
