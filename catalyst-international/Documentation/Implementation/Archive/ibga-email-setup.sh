#!/bin/bash
# =============================================================================
# IBGA Monitoring & Email Alert Setup Script
# =============================================================================
# Run this script on the International droplet to set up:
# 1. IBGA monitoring scripts
# 2. Gmail SMTP email alerts
# 3. Cron schedules
# 4. Test email functionality
#
# Usage: bash ibga-email-setup.sh
# =============================================================================

set -e  # Exit on error

# Configuration
CATALYST_DIR="/root/Catalyst-Trading-System-International/catalyst-international"
SCRIPTS_DIR="$CATALYST_DIR/scripts"
LOG_DIR="/var/log/catalyst"
IBGA_DIR="$CATALYST_DIR/ibga"

# Email Configuration - Pre-configured
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_FROM="elimelech970@gmail.com"
SMTP_TO="craigjcolley@gmail.com"
SMTP_PASSWORD="qjpslctbahqchapg"

echo "============================================================================="
echo "  IBGA Monitoring & Email Alert Setup"
echo "============================================================================="
echo ""

# =============================================================================
# STEP 1: Create directories
# =============================================================================
echo "[1/8] Creating directories..."
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$LOG_DIR"
echo "  ✓ Created $SCRIPTS_DIR"
echo "  ✓ Created $LOG_DIR"

# =============================================================================
# STEP 2: Install mail utilities
# =============================================================================
echo ""
echo "[2/8] Installing email utilities..."
apt-get update -qq
apt-get install -y -qq msmtp msmtp-mta mailutils netcat-openbsd jq
echo "  ✓ Installed msmtp, mailutils, netcat, jq"

# =============================================================================
# STEP 3: Configure msmtp for sending emails
# =============================================================================
echo ""
echo "[3/8] Configuring email (msmtp)..."

cat > /etc/msmtprc << EOF
# Gmail SMTP Configuration for Catalyst Alerts
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /var/log/catalyst/msmtp.log

account        gmail
host           ${SMTP_HOST}
port           ${SMTP_PORT}
from           ${SMTP_FROM}
user           ${SMTP_FROM}
password       ${SMTP_PASSWORD}

account default : gmail
EOF

chmod 600 /etc/msmtprc
echo "  ✓ Configured /etc/msmtprc"

# Link msmtp as sendmail
ln -sf /usr/bin/msmtp /usr/sbin/sendmail 2>/dev/null || true
echo "  ✓ Linked msmtp as sendmail"

# =============================================================================
# STEP 4: Create monitoring script
# =============================================================================
echo ""
echo "[4/8] Creating IBGA monitoring script..."

cat > "$SCRIPTS_DIR/monitor-ibga.sh" << 'MONITOR_SCRIPT'
#!/bin/bash
# =============================================================================
# IBGA Gateway Monitor
# =============================================================================
# Checks IBGA container, port, and authentication status
# Sends email alerts when attention needed
# =============================================================================

LOG_FILE="/var/log/catalyst/ibga-monitor.log"
STATUS_FILE="/tmp/ibga-status.json"
IBGA_DIR="/root/Catalyst-Trading-System-International/catalyst-international/ibga"
ALERT_EMAIL="craigjcolley@gmail.com"

# Timestamp helper
ts() {
    date '+%Y-%m-%d %H:%M:%S'
}

log() {
    echo "$(ts) - $1" | tee -a "$LOG_FILE"
}

send_alert() {
    local subject="$1"
    local body="$2"
    echo "$body" | mail -s "$subject" "$ALERT_EMAIL"
    log "Alert sent: $subject"
}

# ============================================================================
# CHECK 1: Container Running?
# ============================================================================
check_container() {
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "catalyst-ibga"; then
        echo "running"
    else
        echo "stopped"
    fi
}

# ============================================================================
# CHECK 2: Port 4000 Responding?
# ============================================================================
check_port() {
    if nc -z localhost 4000 2>/dev/null; then
        echo "open"
    else
        echo "closed"
    fi
}

# ============================================================================
# CHECK 3: Gateway Authenticated?
# ============================================================================
check_auth() {
    local recent_logs=$(docker logs catalyst-ibga --tail 100 2>&1)
    
    # Check for successful login
    if echo "$recent_logs" | grep -q "Client login succeeds\|session is connected"; then
        # Verify no recent disconnection
        local login_line=$(echo "$recent_logs" | grep -n "Client login succeeds\|session is connected" | tail -1 | cut -d: -f1)
        local error_line=$(echo "$recent_logs" | grep -n "disconnected\|connection lost\|Not authenticated" | tail -1 | cut -d: -f1)
        
        if [ -z "$error_line" ] || [ "${login_line:-0}" -gt "${error_line:-0}" ]; then
            echo "authenticated"
            return
        fi
    fi
    
    # Check for 2FA waiting
    if echo "$recent_logs" | grep -q "Waiting.*IB Key\|Two Factor\|2FA\|second factor"; then
        echo "needs_2fa"
        return
    fi
    
    # Check for connection in progress
    if echo "$recent_logs" | grep -q "Connecting to server\|Attempt [0-9]"; then
        echo "connecting"
        return
    fi
    
    # Check for weekend/maintenance
    if echo "$recent_logs" | grep -q "maintenance\|outside.*hours"; then
        echo "maintenance"
        return
    fi
    
    echo "unknown"
}

# ============================================================================
# MAIN MONITORING LOGIC
# ============================================================================

log "=========================================="
log "IBGA Health Check Starting"
log "=========================================="

# Check container
CONTAINER_STATUS=$(check_container)
log "Container: $CONTAINER_STATUS"

# If container not running, start it
if [ "$CONTAINER_STATUS" = "stopped" ]; then
    log "ACTION: Starting IBGA container..."
    cd "$IBGA_DIR" && docker compose up -d >> "$LOG_FILE" 2>&1
    sleep 45  # Wait for startup
    CONTAINER_STATUS=$(check_container)
    log "Container after start: $CONTAINER_STATUS"
    
    if [ "$CONTAINER_STATUS" = "stopped" ]; then
        send_alert "🔴 IBGA CRITICAL - Container Failed" \
            "IBGA container failed to start on $(hostname) at $(ts).

Please SSH to the server and check:
  docker logs catalyst-ibga --tail 50

Server: International Droplet
Time: $(ts)"
        
        echo '{"container":"failed","port":"unknown","auth":"unknown","timestamp":"'$(ts)'","alert":"container_failed"}' > "$STATUS_FILE"
        exit 1
    else
        send_alert "🟢 IBGA Container Started" \
            "IBGA container was stopped and has been automatically started.

Status: Running
Time: $(ts)

The gateway may need IB Key approval. Watch for another notification."
    fi
fi

# Check port
PORT_STATUS=$(check_port)
log "Port 4000: $PORT_STATUS"

# Check authentication
AUTH_STATUS=$(check_auth)
log "Authentication: $AUTH_STATUS"

# ============================================================================
# STATUS-BASED ALERTS
# ============================================================================

case "$AUTH_STATUS" in
    "authenticated")
        log "✅ IBGA fully operational - ready to trade"
        ALERT_STATUS="healthy"
        ;;
        
    "needs_2fa")
        log "📱 IBGA needs IB Key approval!"
        
        # Only alert once per hour for 2FA
        LAST_2FA_ALERT=$(cat /tmp/ibga-last-2fa-alert 2>/dev/null || echo "0")
        NOW=$(date +%s)
        DIFF=$((NOW - LAST_2FA_ALERT))
        
        if [ $DIFF -gt 3600 ]; then
            send_alert "📱 IBGA Needs IB Key Approval" \
                "The IBKR Gateway needs your approval to authenticate.

ACTION REQUIRED:
1. Check your phone for IB Key notification
2. Approve within 2 minutes
3. Gateway will connect automatically

If no notification:
- Open IBKR Mobile app
- Check IB Key section
- May need to manually trigger from app

Server: International Droplet
Time: $(ts)"
            
            echo "$NOW" > /tmp/ibga-last-2fa-alert
        else
            log "  (2FA alert suppressed - sent within last hour)"
        fi
        ALERT_STATUS="needs_2fa"
        ;;
        
    "connecting")
        log "⏳ IBGA connecting to IBKR servers..."
        ALERT_STATUS="connecting"
        ;;
        
    "maintenance")
        log "🔧 IBKR servers in maintenance mode (normal for weekends)"
        ALERT_STATUS="maintenance"
        ;;
        
    *)
        log "❓ IBGA status unknown - checking container health..."
        
        # Check if container is healthy but just slow
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' catalyst-ibga 2>/dev/null || echo "no-healthcheck")
        log "Container health: $HEALTH"
        
        ALERT_STATUS="unknown"
        ;;
esac

# ============================================================================
# WRITE STATUS FILE
# ============================================================================

cat > "$STATUS_FILE" << EOF
{
    "container": "$CONTAINER_STATUS",
    "port": "$PORT_STATUS",
    "auth": "$AUTH_STATUS",
    "alert_status": "$ALERT_STATUS",
    "timestamp": "$(ts)",
    "hostname": "$(hostname)"
}
EOF

log "Status written to $STATUS_FILE"
log "=========================================="

exit 0
MONITOR_SCRIPT

chmod +x "$SCRIPTS_DIR/monitor-ibga.sh"
echo "  ✓ Created $SCRIPTS_DIR/monitor-ibga.sh"

# =============================================================================
# STEP 5: Create quick status check script
# =============================================================================
echo ""
echo "[5/8] Creating status check script..."

cat > "$SCRIPTS_DIR/ibga-status.sh" << 'STATUS_SCRIPT'
#!/bin/bash
# Quick IBGA status check - human readable output

STATUS_FILE="/tmp/ibga-status.json"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  IBGA Gateway Status"
echo "═══════════════════════════════════════════════════════════"

if [ -f "$STATUS_FILE" ]; then
    CONTAINER=$(jq -r '.container' "$STATUS_FILE")
    PORT=$(jq -r '.port' "$STATUS_FILE")
    AUTH=$(jq -r '.auth' "$STATUS_FILE")
    TIMESTAMP=$(jq -r '.timestamp' "$STATUS_FILE")
    
    # Container status
    if [ "$CONTAINER" = "running" ]; then
        echo "  Container:      🟢 Running"
    else
        echo "  Container:      🔴 $CONTAINER"
    fi
    
    # Port status
    if [ "$PORT" = "open" ]; then
        echo "  Port 4000:      🟢 Open"
    else
        echo "  Port 4000:      🔴 $PORT"
    fi
    
    # Auth status
    case "$AUTH" in
        "authenticated")
            echo "  Authentication: 🟢 Authenticated"
            ;;
        "needs_2fa")
            echo "  Authentication: 📱 Needs IB Key Approval"
            ;;
        "connecting")
            echo "  Authentication: ⏳ Connecting..."
            ;;
        "maintenance")
            echo "  Authentication: 🔧 IBKR Maintenance"
            ;;
        *)
            echo "  Authentication: ❓ $AUTH"
            ;;
    esac
    
    echo ""
    echo "  Last Check:     $TIMESTAMP"
else
    echo "  No status file found. Run monitor first:"
    echo "  /root/Catalyst-Trading-System-International/catalyst-international/scripts/monitor-ibga.sh"
fi

echo "═══════════════════════════════════════════════════════════"
echo ""

# Show recent container logs
echo "Recent IBGA Logs:"
echo "─────────────────"
docker logs catalyst-ibga --tail 10 2>&1 | head -15
echo ""
STATUS_SCRIPT

chmod +x "$SCRIPTS_DIR/ibga-status.sh"
echo "  ✓ Created $SCRIPTS_DIR/ibga-status.sh"

# =============================================================================
# STEP 6: Create email test script
# =============================================================================
echo ""
echo "[6/8] Creating email test script..."

cat > "$SCRIPTS_DIR/test-email.sh" << 'TEST_SCRIPT'
#!/bin/bash
# Test email configuration

ALERT_EMAIL="craigjcolley@gmail.com"

echo "Sending test email to $ALERT_EMAIL..."

RESULT=$(echo "This is a test email from Catalyst Trading System.

If you receive this, email alerts are working correctly.

Server: $(hostname)
Time: $(date)
IP: $(curl -s ifconfig.me 2>/dev/null || echo 'unknown')

-- 
Catalyst International System" | mail -s "✅ Catalyst Email Test" "$ALERT_EMAIL" 2>&1)

if [ $? -eq 0 ]; then
    echo "✓ Email sent successfully!"
    echo "  Check craigjcolley@gmail.com inbox (and spam folder)"
else
    echo "✗ Email failed:"
    echo "$RESULT"
    echo ""
    echo "Check /var/log/catalyst/msmtp.log for details"
fi
TEST_SCRIPT

chmod +x "$SCRIPTS_DIR/test-email.sh"
echo "  ✓ Created $SCRIPTS_DIR/test-email.sh"

# =============================================================================
# STEP 7: Set up cron jobs
# =============================================================================
echo ""
echo "[7/8] Setting up cron jobs..."

# Create cron file
cat > /tmp/catalyst-ibga-cron << 'CRON_CONTENT'
# =============================================================================
# Catalyst IBGA Gateway Monitoring
# =============================================================================
# Times are in UTC (server time)
# HKT = UTC + 8

# Sunday 5:00 PM HKT (09:00 UTC) - Pre-startup before IBKR servers return
0 9 * * 0 /root/Catalyst-Trading-System-International/catalyst-international/scripts/monitor-ibga.sh >> /var/log/catalyst/cron-monitor.log 2>&1

# Sunday 8:00 PM HKT (12:00 UTC) - Check if authenticated
0 12 * * 0 /root/Catalyst-Trading-System-International/catalyst-international/scripts/monitor-ibga.sh >> /var/log/catalyst/cron-monitor.log 2>&1

# Sunday 10:00 PM HKT (14:00 UTC) - Final Sunday check
0 14 * * 0 /root/Catalyst-Trading-System-International/catalyst-international/scripts/monitor-ibga.sh >> /var/log/catalyst/cron-monitor.log 2>&1

# Monday-Friday 8:00 AM HKT (00:00 UTC) - Pre-market check
0 0 * * 1-5 /root/Catalyst-Trading-System-International/catalyst-international/scripts/monitor-ibga.sh >> /var/log/catalyst/cron-monitor.log 2>&1

# Monday-Friday 9:00 AM HKT (01:00 UTC) - Just before trading
0 1 * * 1-5 /root/Catalyst-Trading-System-International/catalyst-international/scripts/monitor-ibga.sh >> /var/log/catalyst/cron-monitor.log 2>&1

# During HK market hours - every hour (01:30-08:00 UTC = 09:30-16:00 HKT)
30 1-8 * * 1-5 /root/Catalyst-Trading-System-International/catalyst-international/scripts/monitor-ibga.sh >> /var/log/catalyst/cron-monitor.log 2>&1

# =============================================================================
# Trading Agent (already configured, shown for reference)
# =============================================================================
# Morning session (09:30 HKT = 01:30 UTC)
# 30 1 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1

# Afternoon session (13:00 HKT = 05:00 UTC)
# 0 5 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1
CRON_CONTENT

# Install cron jobs (merge with existing)
crontab -l 2>/dev/null | grep -v "monitor-ibga.sh" > /tmp/existing-cron || true
cat /tmp/existing-cron /tmp/catalyst-ibga-cron | crontab -
echo "  ✓ Installed cron jobs"

# Show installed crons
echo ""
echo "  Installed monitoring schedule:"
echo "  ─────────────────────────────────────────────"
crontab -l | grep -E "(monitor-ibga|agent.py)" | head -10
echo ""

# =============================================================================
# STEP 8: Test email
# =============================================================================
echo ""
echo "============================================================================="
echo "  Testing Email Configuration"
echo "============================================================================="
echo ""
echo "Sending test email to craigjcolley@gmail.com..."

echo "This is a test email from Catalyst Trading System International.

Email alerts are now configured and working.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IBGA Monitoring Active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You will receive alerts for:
• 📱 IB Key approval needed
• 🔴 IBGA container failures  
• 🟢 Container auto-recovery

Server: $(hostname)
Time: $(date)

--
Catalyst International Trading System" | mail -s "✅ Catalyst Alerts Configured" "$SMTP_TO"

if [ $? -eq 0 ]; then
    echo ""
    echo "  ✓ Test email sent!"
    echo ""
    echo "  📧 Check craigjcolley@gmail.com"
    echo "     (check spam folder if not in inbox)"
else
    echo ""
    echo "  ✗ Email send failed. Check /var/log/catalyst/msmtp.log"
fi

# =============================================================================
# STEP 9: Run initial monitor
# =============================================================================
echo ""
echo "============================================================================="
echo "  Running Initial IBGA Check"
echo "============================================================================="
echo ""
"$SCRIPTS_DIR/monitor-ibga.sh"

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo "============================================================================="
echo "  Setup Complete!"
echo "============================================================================="
echo ""
echo "  Scripts installed:"
echo "    • $SCRIPTS_DIR/monitor-ibga.sh  - Main monitoring script"
echo "    • $SCRIPTS_DIR/ibga-status.sh   - Quick status check"
echo "    • $SCRIPTS_DIR/test-email.sh    - Test email sending"
echo ""
echo "  Quick commands (after 'source ~/.bashrc'):"
echo "    ibga-status    - Check current status"
echo "    ibga-logs      - View IBGA container logs"
echo "    ibga-monitor   - Run monitor manually"
echo ""
echo "  Logs:"
echo "    • /var/log/catalyst/ibga-monitor.log"
echo "    • /var/log/catalyst/msmtp.log"
echo "    • /var/log/catalyst/cron-monitor.log"
echo ""
echo "  Cron schedule active - IBGA will be monitored automatically"
echo ""
echo "============================================================================="

# Add helpful aliases to bashrc
if ! grep -q "ibga-status" /root/.bashrc 2>/dev/null; then
    echo "" >> /root/.bashrc
    echo "# Catalyst IBGA shortcuts" >> /root/.bashrc
    echo "alias ibga-status='$SCRIPTS_DIR/ibga-status.sh'" >> /root/.bashrc
    echo "alias ibga-logs='docker logs catalyst-ibga --tail 50 -f'" >> /root/.bashrc
    echo "alias ibga-monitor='$SCRIPTS_DIR/monitor-ibga.sh'" >> /root/.bashrc
    echo "  ✓ Added aliases to .bashrc (ibga-status, ibga-logs, ibga-monitor)"
fi

echo ""
echo "  🎉 Done! Reload shell with: source ~/.bashrc"
echo ""
