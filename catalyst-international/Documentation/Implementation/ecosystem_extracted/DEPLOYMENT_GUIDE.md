# Catalyst Ecosystem Deployment Guide

**Version:** 10.0.0  
**Date:** 2026-01-10  
**Purpose:** Step-by-step deployment of ecosystem restructure

---

## Pre-Deployment Checklist

### Before Starting
- [ ] All US positions closed (32 positions via Alpaca)
- [ ] US trading Docker services stopped
- [ ] US cron jobs disabled
- [ ] Database backups completed (catalyst_research, catalyst_intl, catalyst_trading)
- [ ] Both droplets accessible via SSH

---

## Phase 1: Database Setup

### Step 1.1: Connect to PostgreSQL Cluster

```bash
# From any machine with psql access
export PGHOST=<your-do-postgres-host>
export PGUSER=doadmin
export PGPASSWORD=<your-password>
export PGPORT=25060
export PGSSLMODE=require
```

### Step 1.2: Drop Old US Database & Create Dev Database

```bash
# Run the combined script
psql -d defaultdb -f sql/drop_and_create_catalyst_dev.sql
```

Expected output:
```
DROP DATABASE
CREATE DATABASE
CREATE EXTENSION
CREATE TABLE  (x9)
CREATE INDEX  (many)
CREATE FUNCTION
CREATE VIEW
 status
-----------------------------------------
 catalyst_dev database created successfully!
```

### Step 1.3: Add Monitor Tables to Production

```bash
psql -d catalyst_intl -f sql/add_monitor_tables_intl.sql
```

Expected output:
```
CREATE TABLE
CREATE INDEX
CREATE FUNCTION
CREATE VIEW
 status
------------------------------------------
 Monitor tables added to catalyst_intl successfully!
```

### Step 1.4: Initialize dev_claude in Consciousness

```bash
psql -d catalyst_research -f sql/initialize_dev_claude.sql
```

Expected output:
```
INSERT 0 1  (or UPDATE if exists)
INSERT 0 1  (welcome message)
INSERT 0 1  (notification to intl_claude)
INSERT 0 1  (question)
UPDATE 1    (public_claude retired)
 status
-------------------------------
 dev_claude initialized in consciousness!
```

### Step 1.5: Verify Database Setup

```bash
# Check catalyst_dev tables
psql -d catalyst_dev -c "\dt"

# Check catalyst_intl has monitor table
psql -d catalyst_intl -c "\d position_monitor_status"

# Check dev_claude in consciousness
psql -d catalyst_research -c "SELECT agent_id, status, mode FROM claude_state"
```

---

## Phase 2: Deploy to Consciousness Hub (US Droplet)

### Step 2.1: SSH to US Droplet

```bash
ssh root@<us-droplet-ip>
```

### Step 2.2: Create Directory Structure

```bash
mkdir -p /root/catalyst/dev
mkdir -p /root/catalyst/config
mkdir -p /root/catalyst/logs
mkdir -p /root/catalyst/scripts
```

### Step 2.3: Upload Python Files

```bash
# From local machine
scp python/signals.py root@<us-droplet>:/root/catalyst/dev/
scp python/startup_monitor.py root@<us-droplet>:/root/catalyst/dev/
scp python/position_monitor.py root@<us-droplet>:/root/catalyst/dev/
scp python/unified_agent.py root@<us-droplet>:/root/catalyst/dev/
```

### Step 2.4: Upload Config

```bash
scp config/dev_claude_config.yaml root@<us-droplet>:/root/catalyst/dev/config/agent_config.yaml
```

### Step 2.5: Set Environment Variables

```bash
# On US droplet
cat >> /root/catalyst/.env << 'EOF'
# Trading Database (dev_claude sandbox)
DEV_DATABASE_URL=postgresql://doadmin:<password>@<host>:25060/catalyst_dev?sslmode=require
DATABASE_URL=postgresql://doadmin:<password>@<host>:25060/catalyst_dev?sslmode=require

# Consciousness Database
RESEARCH_DATABASE_URL=postgresql://doadmin:<password>@<host>:25060/catalyst_research?sslmode=require

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxx

# Agent Identity
AGENT_ID=dev_claude
EOF
```

### Step 2.6: Create Virtual Environment

```bash
cd /root/catalyst
python3 -m venv venv
source venv/bin/activate
pip install asyncpg anthropic pyyaml
```

### Step 2.7: Test Python Modules

```bash
cd /root/catalyst/dev
source ../venv/bin/activate

# Test signals module
python signals.py

# Test startup monitor (needs DB)
python startup_monitor.py
```

### Step 2.8: Install Cron

```bash
cp cron/catalyst-consciousness-hub.cron /etc/cron.d/catalyst-hub
chmod 644 /etc/cron.d/catalyst-hub
systemctl restart cron

# Verify
crontab -l
cat /etc/cron.d/catalyst-hub
```

---

## Phase 3: Deploy to Production (International Droplet)

### Step 3.1: SSH to International Droplet

```bash
ssh root@137.184.244.45
```

### Step 3.2: Backup Existing Files

```bash
cd /root/catalyst-international
mkdir -p backups/$(date +%Y%m%d)
cp *.py backups/$(date +%Y%m%d)/
```

### Step 3.3: Upload New Python Files

```bash
# From local machine
scp python/signals.py root@137.184.244.45:/root/catalyst-international/
scp python/startup_monitor.py root@137.184.244.45:/root/catalyst-international/
scp python/position_monitor.py root@137.184.244.45:/root/catalyst-international/
scp python/unified_agent.py root@137.184.244.45:/root/catalyst-international/
```

### Step 3.4: Upload Config

```bash
scp config/intl_claude_config.yaml root@137.184.244.45:/root/catalyst-international/config/agent_config.yaml
```

### Step 3.5: Update Environment Variables

```bash
# On international droplet
cat >> /root/catalyst-international/.env << 'EOF'
# Agent Identity (ensure set)
AGENT_ID=intl_claude
EOF
```

### Step 3.6: Test Python Modules

```bash
cd /root/catalyst-international
source venv/bin/activate

# Test signals module
python signals.py

# Test startup monitor
python startup_monitor.py
```

### Step 3.7: Update Cron

```bash
cp cron/catalyst-intl-production.cron /etc/cron.d/catalyst-intl
chmod 644 /etc/cron.d/catalyst-intl
systemctl restart cron
```

---

## Phase 4: Verification

### Step 4.1: Check Database State

```bash
# All three databases
psql -d catalyst_research -c "SELECT agent_id, status, mode FROM claude_state"
psql -d catalyst_dev -c "SELECT COUNT(*) FROM positions"
psql -d catalyst_intl -c "SELECT * FROM v_monitor_health"
```

### Step 4.2: Check Cron Jobs

```bash
# US droplet
ssh root@<us-droplet> "cat /etc/cron.d/catalyst-hub"

# International droplet
ssh root@137.184.244.45 "cat /etc/cron.d/catalyst-intl"
```

### Step 4.3: Manual Test Run

```bash
# US droplet - test dev_claude heartbeat
ssh root@<us-droplet> "cd /root/catalyst/dev && ../venv/bin/python unified_agent.py --mode heartbeat"

# International droplet - test intl_claude heartbeat
ssh root@137.184.244.45 "cd /root/catalyst-international && ./venv/bin/python unified_agent.py --mode heartbeat"
```

### Step 4.4: Check Consciousness Messages

```bash
# Check dev_claude received welcome message
psql -d catalyst_research -c "
SELECT from_agent, subject, created_at 
FROM claude_messages 
WHERE to_agent = 'dev_claude' 
ORDER BY created_at DESC 
LIMIT 5"
```

---

## Post-Deployment

### Monitor First Trading Session

```bash
# Watch dev_claude logs
ssh root@<us-droplet> "tail -f /root/catalyst/logs/dev_trade.log"

# Watch intl_claude logs
ssh root@137.184.244.45 "tail -f /root/catalyst-international/logs/trade.log"
```

### Check Position Monitors

```bash
# Check monitor health for both agents
psql -d catalyst_dev -c "SELECT * FROM v_monitor_health"
psql -d catalyst_intl -c "SELECT * FROM v_monitor_health"
```

---

## Rollback Procedure

If issues occur:

### Rollback Cron
```bash
# US droplet
rm /etc/cron.d/catalyst-hub
systemctl restart cron

# International droplet
rm /etc/cron.d/catalyst-intl
systemctl restart cron
```

### Restore Previous Files
```bash
# International droplet
cd /root/catalyst-international
cp backups/$(date +%Y%m%d)/*.py .
```

### Restore Database (if needed)
```bash
# Would need to restore from backup
# Contact Craig before doing this
```

---

## File Summary

| Location | Files |
|----------|-------|
| Both droplets | `signals.py`, `startup_monitor.py`, `position_monitor.py`, `unified_agent.py` |
| US droplet | `dev_claude_config.yaml`, `catalyst-consciousness-hub.cron` |
| International droplet | `intl_claude_config.yaml`, `catalyst-intl-production.cron` |
| PostgreSQL | `drop_and_create_catalyst_dev.sql`, `add_monitor_tables_intl.sql`, `initialize_dev_claude.sql` |

---

**Deployment Complete!**

*Catalyst Trading System v10.0.0*
