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
