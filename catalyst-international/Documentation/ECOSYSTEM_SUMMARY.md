# Catalyst Ecosystem v10.0.0 - Summary

**Generated:** 2026-01-10
**Source:** Ecosystem.zip
**Purpose:** Quick reference summary of the v10.0.0 ecosystem restructure

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
│   ├── catalyst_dev       → dev_claude sandbox (NEW)             │
│   └── catalyst_intl      → intl_claude production               │
│                                                                 │
│   AGENTS                                                        │
│   ├── big_bro      → Strategic oversight    ($10/day)           │
│   ├── dev_claude   → Sandbox experiments    ($5/day)  [NEW]     │
│   ├── intl_claude  → Production trading     ($5/day)            │
│   └── public_claude → Retired               ($0/day)            │
│                                                                 │
│   DROPLETS                                                      │
│   ├── Consciousness Hub (US) → big_bro, dev_claude              │
│   └── Production (International) → intl_claude                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files Included in Ecosystem.zip

### Python Modules

| File | Version | Purpose |
|------|---------|---------|
| `unified_agent.py` | 2.0.0 | Main trading agent with consciousness integration |
| `signals.py` | 1.0.0 | Pattern-based signal detection for entries/exits |
| `startup_monitor.py` | 1.0.0 | Startup reconciliation and health checks |
| `position_monitor.py` | 1.0.0 | Background position monitoring with exit signals |

### Configuration Files

| File | Target Agent | Key Settings |
|------|--------------|--------------|
| `intl_claude_config.yaml` | intl_claude | Conservative: 5 max positions, 3% stop loss |
| `dev_claude_config.yaml` | dev_claude | Experimental: 8 max positions, full autonomy |

### SQL Scripts

| File | Database | Action |
|------|----------|--------|
| `drop_and_create_catalyst_dev.sql` | catalyst_dev | Create fresh sandbox DB |
| `add_monitor_tables_intl.sql` | catalyst_intl | Add position_monitor_status table |
| `initialize_dev_claude.sql` | catalyst_research | Register dev_claude in consciousness |

### Cron Schedules

| File | Droplet | Schedule |
|------|---------|----------|
| `catalyst-intl-production.cron` | International | Production trading hours (HKEX) |
| `catalyst-consciousness-hub.cron` | US | Sandbox trading + oversight |

### Documentation

| File | Version | Purpose |
|------|---------|---------|
| `catalyst-ecosystem-architecture-v10.0.0.md` | 10.0.0 | Full architecture specification |
| `database-schema-v10.0.0.md` | 10.0.0 | Complete database schema |
| `DEPLOYMENT_GUIDE.md` | 10.0.0 | Step-by-step deployment instructions |

---

## Key Changes from v9.x

| Component | v9.x | v10.0.0 |
|-----------|------|---------|
| US Trading | Active (Alpaca) | Retired |
| catalyst_trading DB | US positions | Dropped |
| catalyst_dev DB | N/A | NEW (sandbox) |
| dev_claude agent | N/A | NEW (paper trading) |
| public_claude | Active | Sleeping (retired) |
| Position monitoring | Basic | Pattern-based signals |

---

## Agent Comparison

| Feature | intl_claude (Production) | dev_claude (Sandbox) |
|---------|-------------------------|---------------------|
| Trading | Real money | Paper trading |
| Max Positions | 5 | 8 |
| Max Position Value | 40,000 HKD | 50,000 HKD |
| Stop Loss | 3% | 5% |
| Daily Loss Limit | 16,000 HKD | 25,000 HKD |
| Autonomy | proven_only | full |
| Strategies | Validated only | Experimental allowed |

---

## Consciousness Tables (catalyst_research)

| Table | Purpose |
|-------|---------|
| `claude_state` | Agent status, mode, budget |
| `claude_messages` | Inter-agent communication |
| `claude_observations` | What agents notice |
| `claude_learnings` | Validated knowledge |
| `claude_questions` | Open inquiries |

---

## Deployment Phases

1. **Database Setup** - Create catalyst_dev, add monitor tables to catalyst_intl
2. **Consciousness Hub Deploy** - Install dev_claude on US droplet
3. **Production Deploy** - Update intl_claude on international droplet
4. **Verification** - Test all agents and connections

---

## Quick Start Commands

```bash
# Check database state
psql -d catalyst_research -c "SELECT agent_id, status, mode FROM claude_state"

# Manual agent run (production)
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
python3 agent.py --force

# View monitor health
psql -d catalyst_intl -c "SELECT * FROM v_monitor_health"
```

---

## Next Steps

1. Review `DEPLOYMENT_GUIDE.md` for detailed deployment steps
2. Execute SQL scripts in order (drop_and_create, add_monitor, initialize)
3. Deploy Python files to appropriate droplets
4. Configure cron schedules
5. Verify inter-agent communication

---

*Summary generated from Ecosystem.zip v10.0.0*
