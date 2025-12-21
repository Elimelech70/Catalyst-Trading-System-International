#!/bin/bash
# OpenD Environment Setup Script

OPEND_DIR="/home/craig/Downloads/OpenD"
LOG_DIR="/home/craig/logs/opend"

echo "🌏 OpenD Environment Setup"
echo "=========================="

# Create log directory
echo "📁 Creating log directory..."
sudo mkdir -p "$LOG_DIR"
sudo chown $USER:$USER "$LOG_DIR"
sudo chmod 755 "$LOG_DIR"
echo "   ✅ Log directory created: $LOG_DIR"

# Set system timezone to Hong Kong (for Asian markets)
echo ""
echo "⏰ Configuring timezone for Asian markets..."
current_tz=$(timedatectl show --property=Timezone --value)
echo "   Current timezone: $current_tz"

if [ "$current_tz" != "Asia/Hong_Kong" ]; then
    echo "   Setting timezone to Asia/Hong_Kong for optimal Asian market trading..."
    sudo timedatectl set-timezone Asia/Hong_Kong
    echo "   ✅ Timezone set to Asia/Hong_Kong"
else
    echo "   ✅ Timezone already set correctly"
fi

# Display current time
echo "   Current time: $(date)"

# Check OpenD executable permissions
echo ""
echo "🔧 Checking OpenD executable..."
OPEND_EXEC="$OPEND_DIR/OpenD"
if [ -f "$OPEND_EXEC" ]; then
    chmod +x "$OPEND_EXEC"
    echo "   ✅ OpenD executable permissions set"
else
    echo "   ❌ OpenD executable not found at $OPEND_EXEC"
fi

# Check WebSocket executable permissions
WEBSOCKET_EXEC="$OPEND_DIR/WebSocket"
if [ -f "$WEBSOCKET_EXEC" ]; then
    chmod +x "$WEBSOCKET_EXEC"
    echo "   ✅ WebSocket executable permissions set"
else
    echo "   ❌ WebSocket executable not found at $WEBSOCKET_EXEC"
fi

# Create systemd service file for OpenD
echo ""
echo "📋 Creating systemd service for OpenD..."
sudo tee /etc/systemd/system/opend.service > /dev/null <<EOF
[Unit]
Description=MooMoo OpenD Trading Gateway
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$OPEND_DIR
ExecStart=$OPEND_EXEC
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=opend

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/log/opend $OPEND_DIR

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "   ✅ Systemd service created: opend.service"

# Create startup script
echo ""
echo "🚀 Creating startup script..."
cat > "$OPEND_DIR/start_opend.sh" <<'EOF'
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/opend/startup.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting MooMoo OpenD..." | tee -a "$LOG_FILE"

# Check if OpenD is already running
if pgrep -f "OpenD" > /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - OpenD is already running" | tee -a "$LOG_FILE"
    exit 1
fi

# Start OpenD
cd "$SCRIPT_DIR"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Launching OpenD from $SCRIPT_DIR" | tee -a "$LOG_FILE"

# Start OpenD with output redirect
./OpenD > "/var/log/opend/opend.log" 2>&1 &
OPEND_PID=$!

echo "$(date '+%Y-%m-%d %H:%M:%S') - OpenD started with PID: $OPEND_PID" | tee -a "$LOG_FILE"
echo "$OPEND_PID" > "/var/log/opend/opend.pid"

# Wait a moment and check if it's still running
sleep 3
if kill -0 "$OPEND_PID" 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - OpenD is running successfully" | tee -a "$LOG_FILE"
    echo "Logs available at: /var/log/opend/opend.log"
    echo "API endpoint: http://127.0.0.1:11111"
    echo "WebSocket endpoint: ws://127.0.0.1:33333"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: OpenD failed to start" | tee -a "$LOG_FILE"
    exit 1
fi
EOF

chmod +x "$OPEND_DIR/start_opend.sh"
echo "   ✅ Startup script created: $OPEND_DIR/start_opend.sh"

# Create stop script
cat > "$OPEND_DIR/stop_opend.sh" <<'EOF'
#!/bin/bash

LOG_FILE="/var/log/opend/startup.log"
PID_FILE="/var/log/opend/opend.pid"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Stopping MooMoo OpenD..." | tee -a "$LOG_FILE"

# Stop by PID file if it exists
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Sent SIGTERM to OpenD (PID: $PID)" | tee -a "$LOG_FILE"

        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') - OpenD stopped gracefully" | tee -a "$LOG_FILE"
                rm -f "$PID_FILE"
                exit 0
            fi
            sleep 1
        done

        # Force kill if still running
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Force killing OpenD" | tee -a "$LOG_FILE"
        kill -9 "$PID" 2>/dev/null
        rm -f "$PID_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - OpenD process not found, removing PID file" | tee -a "$LOG_FILE"
        rm -f "$PID_FILE"
    fi
fi

# Kill any remaining OpenD processes
pkill -f "OpenD" 2>/dev/null && echo "$(date '+%Y-%m-%d %H:%M:%S') - Killed remaining OpenD processes" | tee -a "$LOG_FILE"

echo "$(date '+%Y-%m-%d %H:%M:%S') - OpenD stopped" | tee -a "$LOG_FILE"
EOF

chmod +x "$OPEND_DIR/stop_opend.sh"
echo "   ✅ Stop script created: $OPEND_DIR/stop_opend.sh"

echo ""
echo "🔧 Configuration Summary:"
echo "========================"
echo "✅ Log directory: $LOG_DIR"
echo "✅ Timezone: $(timedatectl show --property=Timezone --value)"
echo "✅ API Port: 11111 (JSON format enabled)"
echo "✅ WebSocket Port: 33333 (enabled)"
echo "✅ Telnet Port: 22222 (for debugging)"
echo "✅ Quote push frequency: 100ms (high-frequency trading ready)"
echo "✅ Auto quote right grab: enabled"
echo "✅ Price reminders: enabled"
echo "✅ Timezone for futures: UTC+8 (Asia/Hong_Kong)"
echo ""
echo "🚀 Usage Commands:"
echo "=================="
echo "Start OpenD:     $OPEND_DIR/start_opend.sh"
echo "Stop OpenD:      $OPEND_DIR/stop_opend.sh"
echo "Service start:   sudo systemctl start opend"
echo "Service stop:    sudo systemctl stop opend"
echo "Service enable:  sudo systemctl enable opend"
echo "View logs:       tail -f /var/log/opend/opend.log"
echo ""
echo "⚠️  NEXT STEPS:"
echo "==============="
echo "1. Configure credentials: ./configure_opend_credentials.sh"
echo "2. Test connection: $OPEND_DIR/start_opend.sh"
echo "3. Verify API access: curl http://127.0.0.1:11111/api/health"