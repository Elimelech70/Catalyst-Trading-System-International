#!/bin/bash
# ============================================================================
# CATALYST INTERNATIONAL - HOURLY WORKFLOW DEPLOYMENT
# ============================================================================
#
# Name of Application: Catalyst Trading System
# Name of file: deploy-hourly-workflow.sh
# Version: 1.0.0
# Last Updated: 2026-01-06
# Purpose: Deploy hourly full trading workflow with position monitoring
#
# WHAT THIS DOES:
# 1. Updates cron to hourly schedule
# 2. Ensures position monitoring is integrated
# 3. Tests the configuration
#
# ============================================================================

set -e

echo "=============================================="
echo "CATALYST HOURLY WORKFLOW DEPLOYMENT"
echo "=============================================="
echo ""

# Configuration
CATALYST_DIR="/root/Catalyst-Trading-System-International/catalyst-international"
CRON_FILE="/etc/cron.d/catalyst-intl"
BACKUP_DIR="$CATALYST_DIR/backups/$(date +%Y%m%d_%H%M%S)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# STEP 1: Backup current configuration
# ============================================================================
echo -e "${YELLOW}Step 1: Creating backup...${NC}"

mkdir -p "$BACKUP_DIR"

if [ -f "$CRON_FILE" ]; then
    cp "$CRON_FILE" "$BACKUP_DIR/catalyst-intl.cron.backup"
    echo "  Backed up existing cron to $BACKUP_DIR/"
fi

if [ -f "$CATALYST_DIR/tool_executor.py" ]; then
    cp "$CATALYST_DIR/tool_executor.py" "$BACKUP_DIR/tool_executor.py.backup"
    echo "  Backed up tool_executor.py"
fi

echo -e "${GREEN}✓ Backup complete${NC}"
echo ""

# ============================================================================
# STEP 2: Verify position monitoring files exist
# ============================================================================
echo -e "${YELLOW}Step 2: Verifying position monitoring files...${NC}"

MISSING_FILES=()

if [ ! -f "$CATALYST_DIR/signals.py" ]; then
    MISSING_FILES+=("signals.py")
fi

if [ ! -f "$CATALYST_DIR/consciousness_notify.py" ]; then
    MISSING_FILES+=("consciousness_notify.py")
fi

if [ ! -f "$CATALYST_DIR/position_monitor.py" ]; then
    MISSING_FILES+=("position_monitor.py")
fi

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo -e "${RED}✗ Missing files: ${MISSING_FILES[*]}${NC}"
    echo "  Please deploy position monitoring files first."
    echo "  See: Documentation/Implementation/Position Monitoring Implementation.zip"
    exit 1
fi

echo -e "${GREEN}✓ All position monitoring files present${NC}"
echo ""

# ============================================================================
# STEP 3: Verify tool_executor.py has position monitoring integration
# ============================================================================
echo -e "${YELLOW}Step 3: Checking tool_executor.py integration...${NC}"

if grep -q "start_position_monitor" "$CATALYST_DIR/tool_executor.py"; then
    echo -e "${GREEN}✓ Position monitoring integrated in tool_executor.py${NC}"
else
    echo -e "${YELLOW}⚠ Position monitoring not found in tool_executor.py${NC}"
    echo "  The tool_executor.py needs to be updated to v2.2.1"
    echo "  Please apply the patch from tool_executor_patch.py"
fi
echo ""

# ============================================================================
# STEP 4: Check unified_agent.py or agent.py has agent=self
# ============================================================================
echo -e "${YELLOW}Step 4: Checking agent integration...${NC}"

AGENT_OK=false

if [ -f "$CATALYST_DIR/unified_agent.py" ]; then
    if grep -q "agent=self" "$CATALYST_DIR/unified_agent.py"; then
        echo -e "${GREEN}✓ unified_agent.py has agent=self${NC}"
        AGENT_OK=true
    else
        echo -e "${YELLOW}⚠ unified_agent.py missing agent=self parameter${NC}"
    fi
elif [ -f "$CATALYST_DIR/agent.py" ]; then
    if grep -q "agent=self" "$CATALYST_DIR/agent.py"; then
        echo -e "${GREEN}✓ agent.py has agent=self${NC}"
        AGENT_OK=true
    else
        echo -e "${YELLOW}⚠ agent.py missing agent=self parameter${NC}"
    fi
fi

if [ "$AGENT_OK" = false ]; then
    echo "  Add 'agent=self' to create_tool_executor() call"
fi
echo ""

# ============================================================================
# STEP 5: Install new cron schedule
# ============================================================================
echo -e "${YELLOW}Step 5: Installing hourly cron schedule...${NC}"

cat > "$CRON_FILE" << 'CRON_CONTENT'
# ============================================================================
# CATALYST INTERNATIONAL - HOURLY TRADING WORKFLOW
# Version: 2.0.0
# Updated: 2026-01-06
# ============================================================================

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""

CATALYST_DIR=/root/Catalyst-Trading-System-International/catalyst-international
VENV_PYTHON=/root/Catalyst-Trading-System-International/catalyst-international/venv/bin/python3
LOG_DIR=/root/Catalyst-Trading-System-International/catalyst-international/logs

# ============================================================================
# TRADING SCHEDULE (Monday-Friday)
# ============================================================================

# Pre-market scan (09:00 HKT = 01:00 UTC)
0 1 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode scan >> $LOG_DIR/cron.log 2>&1

# Morning session - HOURLY FULL WORKFLOW
# 09:30 HKT (01:30 UTC) - Market opens
30 1 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode trade >> $LOG_DIR/cron.log 2>&1
# 10:00 HKT (02:00 UTC)
0 2 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode trade >> $LOG_DIR/cron.log 2>&1
# 11:00 HKT (03:00 UTC)
0 3 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode trade >> $LOG_DIR/cron.log 2>&1

# Lunch break close (12:00 HKT = 04:00 UTC)
0 4 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode close >> $LOG_DIR/cron.log 2>&1

# Afternoon session - HOURLY FULL WORKFLOW
# 13:00 HKT (05:00 UTC)
0 5 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode trade >> $LOG_DIR/cron.log 2>&1
# 14:00 HKT (06:00 UTC)
0 6 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode trade >> $LOG_DIR/cron.log 2>&1
# 15:00 HKT (07:00 UTC)
0 7 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode trade >> $LOG_DIR/cron.log 2>&1

# EOD close (16:00 HKT = 08:00 UTC)
0 8 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode close >> $LOG_DIR/cron.log 2>&1

# ============================================================================
# OFF-HOURS HEARTBEAT (every 2 hours, weekdays)
# ============================================================================
0 9,11,13,15,17,19,21,23 * * 1-5 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode heartbeat >> $LOG_DIR/cron.log 2>&1

# Weekend heartbeat (every 4 hours)
0 0,4,8,12,16,20 * * 0,6 cd $CATALYST_DIR && $VENV_PYTHON unified_agent.py --mode heartbeat >> $LOG_DIR/cron.log 2>&1

# ============================================================================
# MAINTENANCE
# ============================================================================
# Log rotation (daily at midnight UTC)
0 0 * * * find $LOG_DIR -name "*.log" -mtime +7 -delete 2>/dev/null
CRON_CONTENT

chmod 644 "$CRON_FILE"

echo -e "${GREEN}✓ Cron schedule installed${NC}"
echo ""

# ============================================================================
# STEP 6: Restart cron service
# ============================================================================
echo -e "${YELLOW}Step 6: Restarting cron service...${NC}"

systemctl restart cron

if systemctl is-active --quiet cron; then
    echo -e "${GREEN}✓ Cron service running${NC}"
else
    echo -e "${RED}✗ Cron service failed to start${NC}"
    exit 1
fi
echo ""

# ============================================================================
# STEP 7: Display new schedule
# ============================================================================
echo -e "${YELLOW}Step 7: Verifying installation...${NC}"
echo ""
echo "Current cron schedule:"
echo "──────────────────────────────────────────────────────────────"
cat "$CRON_FILE" | grep -v "^#" | grep -v "^$" | grep -v "^SHELL" | grep -v "^PATH" | grep -v "^MAILTO" | grep -v "^CATALYST" | grep -v "^VENV" | grep -v "^LOG"
echo "──────────────────────────────────────────────────────────────"
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "=============================================="
echo -e "${GREEN}DEPLOYMENT COMPLETE${NC}"
echo "=============================================="
echo ""
echo "HOURLY TRADING SCHEDULE (HKT):"
echo ""
echo "  09:00  Pre-market scan"
echo "  09:30  Trading cycle #1 (market open)"
echo "  10:00  Trading cycle #2"
echo "  11:00  Trading cycle #3"
echo "  12:00  Lunch break close"
echo "  13:00  Trading cycle #4 (afternoon open)"
echo "  14:00  Trading cycle #5"
echo "  15:00  Trading cycle #6"
echo "  16:00  EOD close"
echo ""
echo "POSITION MONITORING:"
echo "  After each BUY order, continuous monitoring runs"
echo "  until position is closed or market closes."
echo ""
echo "WORKFLOW PER CYCLE:"
echo "  1. Check portfolio"
echo "  2. Scan market for opportunities"
echo "  3. Analyze candidates (quote, technicals, patterns, news)"
echo "  4. Execute trades if criteria met"
echo "  5. Position monitor starts for new positions"
echo "  6. Log all decisions"
echo ""
echo "NEXT STEPS:"
echo "  1. Monitor first cycle: tail -f $LOG_DIR/cron.log"
echo "  2. Check consciousness: catalyst-consciousness:get_trading_overview"
echo "  3. Review positions after market close"
echo ""
echo "ROLLBACK (if needed):"
echo "  cp $BACKUP_DIR/catalyst-intl.cron.backup $CRON_FILE"
echo "  systemctl restart cron"
echo ""
