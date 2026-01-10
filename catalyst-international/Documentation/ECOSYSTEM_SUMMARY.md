# Catalyst Ecosystem v10.0.0 - Summary

**Generated:** 2026-01-10
**Last Updated:** 2026-01-10
**Purpose:** Quick reference summary of the v10.0.0 ecosystem restructure

---

## Deployment Status

| Component | Status | Notes |
|-----------|--------|-------|
| **intl_claude (Production)** | **DEPLOYED** | v2.0.0 files live |
| Database tables | **DEPLOYED** | position_monitor_status + view |
| Cron schedule | **DEPLOYED** | /etc/cron.d/catalyst-intl |
| dev_claude (Sandbox) | NOT DEPLOYED | Needs US droplet |
| Consciousness Hub | NOT DEPLOYED | Needs US droplet |
| big_bro oversight | NOT DEPLOYED | Needs US droplet |

---

## Overview

The Catalyst Trading System v10.0.0 introduces a major ecosystem restructure:
- **US trading retired** - All 32 Alpaca positions closed
- **dev_claude sandbox created** - New paper trading environment for experiments
- **HKEX production focus** - intl_claude continues live trading with proven strategies

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                 CATALYST ECOSYSTEM v10.0.0                      │
│                 "Consciousness Before Trading"                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   DATABASES (DigitalOcean Managed PostgreSQL)                   │
│   ├── catalyst_research  → Consciousness (shared by all)        │
│   ├── catalyst_dev       → dev_claude sandbox (NOT DEPLOYED)    │
│   └── catalyst_intl      → intl_claude production [ACTIVE]      │
│                                                                 │
│   AGENTS                                                        │
│   ├── big_bro      → Strategic oversight    (NOT DEPLOYED)      │
│   ├── dev_claude   → Sandbox experiments    (NOT DEPLOYED)      │
│   ├── intl_claude  → Production trading     [ACTIVE]            │
│   └── public_claude → Retired               ($0/day)            │
│                                                                 │
│   DROPLETS                                                      │
│   ├── Consciousness Hub (US) → NOT SET UP                       │
│   └── Production (International) → intl_claude [ACTIVE]         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployed Files (Production)

| File | Version | Deployed | Location |
|------|---------|----------|----------|
| `unified_agent.py` | 2.0.0 | 2026-01-10 | /root/.../catalyst-international/ |
| `position_monitor.py` | 2.0.0 | 2026-01-10 | /root/.../catalyst-international/ |
| `signals.py` | 2.0.0 | 2026-01-10 | /root/.../catalyst-international/ |
| `startup_monitor.py` | 1.0.0 | 2026-01-10 | /root/.../catalyst-international/ |
| `intl_claude_config.yaml` | 1.0.0 | 2026-01-10 | /root/.../catalyst-international/config/ |

### Database Objects (catalyst_intl)

| Object | Type | Status |
|--------|------|--------|
| `position_monitor_status` | Table | CREATED |
| `v_monitor_health` | View | CREATED |
| `update_monitor_timestamp()` | Function | CREATED |
| `trg_monitor_updated` | Trigger | CREATED |

### Cron Schedule (Production)

```
/etc/cron.d/catalyst-intl

Pre-market:   01:00 UTC (09:00 HKT) - startup_monitor.py
Morning:      01:30, 02:00, 03:00 UTC - trade mode
Lunch:        04:00 UTC - close mode
Afternoon:    05:00, 06:00, 07:00 UTC - trade mode
EOD:          08:00 UTC - close mode
Heartbeat:    09,12,15,18,21,00 UTC - heartbeat mode
```

---

## Current Open Positions

| Symbol | Stock | Monitor Status |
|--------|-------|----------------|
| 9868 | XPeng | NO_MONITOR |
| 1211 | BYD | NO_MONITOR |
| 1024 | Kuaishou | NO_MONITOR |
| 2382 | Sunny Optical | NO_MONITOR |

**Note:** Run `startup_monitor.py` to start monitors for all positions.

---

## Files Pending Deployment

### For US Droplet (Consciousness Hub)

| File | Purpose |
|------|---------|
| `dev_claude_config.yaml` | Sandbox configuration |
| `catalyst-consciousness-hub.cron` | US droplet cron schedule |
| `drop_and_create_catalyst_dev.sql` | Create sandbox database |
| `initialize_dev_claude.sql` | Register dev_claude |

---

## Agent Comparison

| Feature | intl_claude (Production) | dev_claude (Sandbox) |
|---------|-------------------------|---------------------|
| Status | **ACTIVE** | NOT DEPLOYED |
| Trading | Real money | Paper trading |
| Max Positions | 5 | 8 |
| Max Position Value | 40,000 HKD | 50,000 HKD |
| Stop Loss | 3% | 5% |
| Daily Loss Limit | 16,000 HKD | 25,000 HKD |
| Autonomy | proven_only | full |
| Strategies | Validated only | Experimental allowed |

---

## Quick Commands

```bash
# Check monitor health
source .env && psql "$DATABASE_URL" -c "SELECT * FROM v_monitor_health"

# Manual startup monitor (starts monitors for all positions)
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
python3 startup_monitor.py

# Manual agent run
python3 unified_agent.py --mode trade

# Check cron
cat /etc/cron.d/catalyst-intl
```

---

## Backups

Pre-deployment backups stored in:
```
backups/pre-ecosystem-v2/
├── position_monitor.py  (v1.1.0)
├── signals.py           (v1.1.0)
└── unified_agent.py     (v1.0.0)
```

---

## Next Steps to Complete Ecosystem

1. **Set up US droplet** for Consciousness Hub
2. **Deploy dev_claude** sandbox environment
3. **Create catalyst_dev database** with SQL scripts
4. **Install consciousness hub cron** schedule
5. **Register dev_claude** in consciousness tables
6. **Configure big_bro** oversight agent

---

*Summary updated 2026-01-10 after production deployment*
