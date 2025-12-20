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
