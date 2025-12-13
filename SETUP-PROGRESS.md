# Catalyst Trading System International - Setup Progress

**Date**: 2025-12-09
**Status**: Ready for Configuration

---

## Implementation Complete

All core components have been implemented and verified:

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Main Agent | `agent.py` | ~500 | Complete |
| Tool Executor | `tool_executor.py` | ~450 | Complete |
| Tool Definitions | `tools.py` | ~400 | Complete (12 tools) |
| Safety Layer | `safety.py` | ~420 | Complete |
| IBKR Broker | `brokers/ibkr.py` | ~700 | Complete |
| Market Data | `data/market.py` | ~550 | Complete |
| Pattern Detection | `data/patterns.py` | ~650 | Complete (8 patterns) |
| News & Sentiment | `data/news.py` | ~450 | Complete |
| Database Client | `data/database.py` | ~500 | Complete |
| Email Alerts | `alerts.py` | ~275 | Complete |
| DB Schema | `scripts/schema.sql` | ~200 | Complete |

**Total**: ~4,900 lines of production-ready Python code

---

## Remaining Setup Steps

### Step 1: Create Database Schema

First, create the database tables in your PostgreSQL database:

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international

# Using DATABASE_URL
psql $DATABASE_URL < scripts/schema.sql

# Or with individual parameters
psql -h your-db-host.db.ondigitalocean.com -p 25060 -U your-user -d catalyst_trading < scripts/schema.sql
```

This creates:
- `exchanges` - Exchange configuration (HKEX)
- `securities` - Stock symbols
- `agent_cycles` - AI agent run tracking
- `agent_decisions` - Decision audit trail
- `positions` - Trade positions
- `trading_cycles` - Trading cycle records
- `get_or_create_security()` - Helper function
- Views for daily summary and performance

### Step 2: Create Environment File

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
cp .env.example .env
nano .env
```

**Required values:**
```
# Claude API (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Interactive Brokers (REQUIRED)
IBKR_HOST=127.0.0.1
IBKR_PORT=7497          # 7497=paper trading, 7496=live
IBKR_CLIENT_ID=1

# Database (REQUIRED)
DB_HOST=your-db-host.db.ondigitalocean.com
DB_PORT=25060
DB_NAME=catalyst_trading
DB_USER=your-db-user
DB_PASSWORD=your-db-password

# Email Alerts (optional but recommended)
ALERT_EMAIL=your-email@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASS=your-app-password
```

### Step 3: Start Interactive Brokers Gateway

- IBKR Gateway or TWS must be running
- Port 7497 for paper trading
- Port 7496 for live trading
- Enable API connections in settings

### Step 4: Test Run the Agent

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
python3 agent.py --force  # --force runs even if market is closed
```

### Step 5: Production Setup (Cron Jobs)

For automated trading during HKEX hours:

```bash
crontab -e
```

Add these lines (Hong Kong Time):
```
# Morning session: 9:30 AM - 12:00 PM HKT
30 9  * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
0  10 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
30 10 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
0  11 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
30 11 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1

# Afternoon session: 1:00 PM - 4:00 PM HKT
0  13 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
30 13 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
0  14 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
30 14 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
0  15 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
30 15 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
30 16 * * 1-5  cd /root/Catalyst-Trading-System-International/catalyst-international && python3 agent.py >> /var/log/catalyst-intl.log 2>&1
```

---

## Quick Reference

### File Locations
- Main agent: `agent.py`
- Config: `config/settings.yaml`
- DB Schema: `scripts/schema.sql`
- Docs: `CLAUDE.md`
- Logs: `logs/agent.log`

### Command Line Options
```bash
python3 agent.py --help                    # Show help
python3 agent.py --config custom.yaml      # Custom config
python3 agent.py --live                    # Live trading (default: paper)
python3 agent.py --force                   # Run even if market closed
```

### Check Logs
```bash
tail -f logs/agent.log                     # Local logs
tail -f /var/log/catalyst-intl.log         # Cron logs
```

### Verify Database
```bash
# Check tables exist
psql $DATABASE_URL -c "\dt"

# Check helper function exists
psql $DATABASE_URL -c "SELECT get_or_create_security('0700');"
```

---

## Architecture Summary

This is a **single AI agent** system (NOT microservices):

```
CRON triggers -> agent.py -> Claude API -> Tool calls -> IBKR Execution
                                |
                                v
                      12 Tools Available:
                      - scan_market, get_quote, get_technicals
                      - detect_patterns, get_news, check_risk
                      - get_portfolio, execute_trade, close_position
                      - close_all, send_alert, log_decision
```

- ~4,900 lines of Python code
- Claude API makes all trading decisions dynamically
- Uses Interactive Brokers for HKEX execution
- PostgreSQL for audit trail and trade logging
- Email alerts for notifications

---

## The 12 AI Tools

| Tool | Purpose |
|------|---------|
| `scan_market` | Find trading candidates by momentum/volume |
| `get_quote` | Current price, bid/ask, volume |
| `get_technicals` | RSI, MACD, MAs, ATR, Bollinger Bands |
| `detect_patterns` | 8 pattern types with entry/stop/target |
| `get_news` | News headlines with sentiment scoring |
| `check_risk` | Validate trade against all risk limits |
| `get_portfolio` | Cash, equity, positions, daily P&L |
| `execute_trade` | Submit orders to IBKR |
| `close_position` | Exit a single position |
| `close_all` | Emergency close all positions |
| `send_alert` | Email notifications |
| `log_decision` | Audit trail for ML training |

---

## Next Time You Return

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international

# Quick test (market closed is OK with --force)
python3 agent.py --force

# Check recent cycles
psql $DATABASE_URL -c "SELECT * FROM agent_cycles ORDER BY started_at DESC LIMIT 5;"
```
