# Current Focus - Catalyst Trading System International

**Last Updated:** 2025-12-20
**Status:** Broker Migration In Progress - Account Setup Required
**Next Action:** Enable HK stock trading on Moomoo AU account

---

## Executive Summary

Migrating from Interactive Brokers (IBKR) to Moomoo/Futu due to persistent IB Key 2FA authentication failures. OpenD infrastructure is ready; **account requires HK trading enablement**.

---

## Current Blocker: HK Trading Account

**Issue:** OpenD login fails with "账号密码不匹配" (password mismatch)

**Root Cause (Research Findings):**
1. Moomoo AU **DOES support OpenAPI** for HK/US stock trading
2. Your account needs **HK stock trading specifically enabled** (not just a general AU account)
3. First-time OpenD login requires completing **API Questionnaire and Agreements**
4. The OpenAPI option is NOT in the desktop app menu - it's activated via OpenD itself

---

### ⚠️ ACTION REQUIRED: Enable HK Trading

**Step 1: Enable Hong Kong Stock Trading**
1. Log into **Moomoo AU mobile app** or https://www.moomoo.com/au
2. Go to: **Me** → **Account & Security** → **Trading Permissions**
   - Or: **Account** → **Market Access** → **Hong Kong Stocks**
3. Click **Enable** or **Apply** for Hong Kong Stock Trading (HKEX)
4. Complete identity verification if prompted
5. Accept the HK stock trading agreements

**Step 2: Complete OpenAPI Setup (First Login)**
- Once HK trading is enabled, OpenD will prompt for:
  - API Questionnaire (basic questions about API usage)
  - OpenAPI User Agreement
- This happens automatically on first successful OpenD login

**Step 3: Test Connection**
```bash
cd /root/opend && docker compose up -d
docker logs catalyst-opend -f
```

---

### Research Sources
- [Moomoo AU - Hong Kong Stocks](https://www.moomoo.com/au/invest/hk-stock) - "Trade 3500+ HK shares/ETFs"
- [OpenAPI Authorities](https://openapi.moomoo.com/moomoo-api-doc/en/intro/authority.html) - Market requirements
- [OpenAPI Introduction](https://openapi.futunn.com/futu-api-doc/en/intro/intro.html) - "Finish opening trading accounts before logging into OpenAPI"

---

**Credentials Configured:**
- Account ID: `152537501`
- Password: `Thisissecure1234!`
- Location: `/root/opend/.env`

---

## Current State

### What's Working
| Component | Status | Notes |
|-----------|--------|-------|
| OpenD Docker image | ✅ Ready | `ghcr.io/manhinhang/futu-opend-docker:ubuntu-stable` |
| OpenD docker-compose | ✅ Ready | `/root/opend/docker-compose.yml` |
| OpenD .env | ✅ Configured | Account ID + password set |
| FutuClient | ✅ Ready | `brokers/futu.py` v1.0.0 |
| Test script | ✅ Ready | `/root/opend/test_connection.py` |
| futu-api package | ✅ Installed | v9.6.5608 |
| Documentation | ✅ Updated | CLAUDE.md v3.0.0, architecture v5.0.0 |
| GitHub | ✅ Pushed | Commit `69e5785` |

### What's Pending
| Item | Status | Blocker |
|------|--------|---------|
| HK Trading Permission | ⚠️ REQUIRED | Enable in Moomoo app/website |
| OpenAPI Questionnaire | ⏳ Pending | Complete on first OpenD login |
| OpenD Connection | ⏳ Blocked | Needs HK trading enabled |
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
├── .env                  # Credentials (CONFIGURED ✅)
├── logs/                 # OpenD logs
└── test_connection.py    # Connection test
```

**Port:** 11111 (Futu API)
**Status:** Waiting for HK trading to be enabled on account

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

### 1. ⚠️ Enable HK Stock Trading (CURRENT BLOCKER)
- [ ] Log into Moomoo AU app/website
- [ ] Navigate to Account → Trading Permissions
- [ ] Enable Hong Kong Stock Trading (HKEX)
- [ ] Complete any identity verification
- [ ] Accept HK trading agreements

### 2. ✅ OpenD Credentials (DONE)
```
/root/opend/.env:
FUTU_ACCOUNT_ID=152537501
FUTU_ACCOUNT_PWD=Thisissecure1234!
```

### 3. Start OpenD & Complete API Setup
```bash
cd /root/opend && docker compose up -d
docker logs catalyst-opend -f
# First login will prompt for API questionnaire + agreement
```

### 4. Test Connection
```bash
source /root/Catalyst-Trading-System-International/catalyst-international/venv/bin/activate
python3 /root/opend/test_connection.py
```

### 5. Test Paper Trading
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
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

3. ~~**Account region** - If Moomoo AU doesn't support OpenAPI for HKEX, may need Futu HK account.~~ **RESOLVED:** Research confirms Moomoo AU supports HKEX trading via OpenAPI.

4. **HK Trading Must Be Enabled** - Standard Moomoo AU accounts need HK stock trading permission enabled separately before OpenD will authenticate.

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

**Next Session:** Enable HK trading on Moomoo AU account → Start OpenD → Complete API questionnaire → Test connection
