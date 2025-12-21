#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/root/logs/opend"
LOG_FILE="$LOG_DIR/startup.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

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
./OpenD > "$LOG_DIR/opend.log" 2>&1 &
OPEND_PID=$!

echo "$(date '+%Y-%m-%d %H:%M:%S') - OpenD started with PID: $OPEND_PID" | tee -a "$LOG_FILE"
echo "$OPEND_PID" > "$LOG_DIR/opend.pid"

# Wait a moment and check if it's still running
sleep 3
if kill -0 "$OPEND_PID" 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - OpenD is running successfully" | tee -a "$LOG_FILE"
    echo "Logs available at: $LOG_DIR/opend.log"
    echo "API endpoint: http://127.0.0.1:11111"
    echo "WebSocket endpoint: ws://127.0.0.1:33333"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: OpenD failed to start" | tee -a "$LOG_FILE"
    exit 1
fi