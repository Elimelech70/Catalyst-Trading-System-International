#!/bin/bash
#
# IBKR IBeam Health Check Script
# Checks authentication status and restarts if needed
#

IBEAM_URL="https://localhost:5000"
LOG_FILE="/var/log/catalyst/ibkr_health.log"

# Ensure log directory exists
mkdir -p /var/log/catalyst

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check authentication status
STATUS=$(curl -sk "${IBEAM_URL}/v1/api/iserver/auth/status" 2>/dev/null | jq -r '.authenticated // "error"')

if [ "$STATUS" == "true" ]; then
    log "IBKR authenticated OK"

    # Also tickle to keep session alive
    curl -sk -X POST "${IBEAM_URL}/v1/api/tickle" > /dev/null 2>&1

elif [ "$STATUS" == "false" ]; then
    log "IBKR not authenticated, attempting reauthentication..."

    # Try reauthenticate endpoint first
    curl -sk -X POST "${IBEAM_URL}/v1/api/iserver/reauthenticate" > /dev/null 2>&1
    sleep 30

    # Check again
    STATUS=$(curl -sk "${IBEAM_URL}/v1/api/iserver/auth/status" 2>/dev/null | jq -r '.authenticated // "error"')

    if [ "$STATUS" != "true" ]; then
        log "Reauthentication failed, restarting IBeam container..."
        docker restart catalyst-ibeam

        # Wait for restart
        sleep 120

        # Final check
        STATUS=$(curl -sk "${IBEAM_URL}/v1/api/iserver/auth/status" 2>/dev/null | jq -r '.authenticated // "error"')
        if [ "$STATUS" != "true" ]; then
            log "CRITICAL: IBKR still not authenticated after restart!"
            # TODO: Send alert via webhook/email
        else
            log "IBKR authenticated after restart"
        fi
    else
        log "IBKR reauthenticated successfully"
    fi

else
    log "ERROR: Cannot reach IBeam gateway (status: $STATUS)"

    # Check if container is running
    CONTAINER_STATUS=$(docker ps --filter "name=catalyst-ibeam" --format "{{.Status}}" 2>/dev/null)

    if [ -z "$CONTAINER_STATUS" ]; then
        log "IBeam container not running, starting..."
        cd /opt/catalyst/ibeam && docker-compose up -d
    else
        log "Container status: $CONTAINER_STATUS"
        log "Restarting IBeam container..."
        docker restart catalyst-ibeam
    fi

    sleep 120

    # Check again
    STATUS=$(curl -sk "${IBEAM_URL}/v1/api/iserver/auth/status" 2>/dev/null | jq -r '.authenticated // "error"')
    if [ "$STATUS" == "true" ]; then
        log "IBKR recovered and authenticated"
    else
        log "CRITICAL: IBKR gateway recovery failed!"
    fi
fi
