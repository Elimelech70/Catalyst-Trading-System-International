#!/bin/bash

LOG_FILE="/home/craig/logs/opend/startup.log"
PID_FILE="/home/craig/logs/opend/opend.pid"

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