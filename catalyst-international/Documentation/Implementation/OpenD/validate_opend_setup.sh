#!/bin/bash
# OpenD Configuration Validation Script

OPEND_DIR="/home/craig/Downloads/OpenD"
CONFIG_FILE="$OPEND_DIR/OpenD.xml"
LOG_DIR="/home/craig/logs/opend"

echo "🧪 OpenD Configuration Validation"
echo "================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check network port
check_port() {
    local port=$1
    local name=$2

    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo "   ⚠️  Port $port ($name) is already in use"
        netstat -tuln | grep ":$port "
        return 1
    else
        echo "   ✅ Port $port ($name) is available"
        return 0
    fi
}

# 1. Check file structure
echo ""
echo "📁 Checking file structure..."
required_files=(
    "$OPEND_DIR/OpenD"
    "$OPEND_DIR/WebSocket"
    "$CONFIG_FILE"
    "$OPEND_DIR/start_opend.sh"
    "$OPEND_DIR/stop_opend.sh"
)

all_files_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file - MISSING"
        all_files_exist=false
    fi
done

# 2. Check executables
echo ""
echo "🔧 Checking executable permissions..."
executables=("$OPEND_DIR/OpenD" "$OPEND_DIR/WebSocket" "$OPEND_DIR/start_opend.sh" "$OPEND_DIR/stop_opend.sh")

for exec in "${executables[@]}"; do
    if [ -x "$exec" ]; then
        echo "   ✅ $(basename "$exec") - executable"
    else
        echo "   ❌ $(basename "$exec") - NOT executable"
        chmod +x "$exec" 2>/dev/null && echo "      🔧 Fixed permissions"
    fi
done

# 3. Check log directory
echo ""
echo "📝 Checking log directory..."
if [ -d "$LOG_DIR" ]; then
    if [ -w "$LOG_DIR" ]; then
        echo "   ✅ $LOG_DIR - exists and writable"
    else
        echo "   ⚠️  $LOG_DIR - exists but not writable"
        sudo chown $USER:$USER "$LOG_DIR" 2>/dev/null && echo "      🔧 Fixed ownership"
    fi
else
    echo "   ❌ $LOG_DIR - does not exist"
    sudo mkdir -p "$LOG_DIR" && sudo chown $USER:$USER "$LOG_DIR" && echo "      🔧 Created directory"
fi

# 4. Check configuration
echo ""
echo "⚙️  Checking OpenD configuration..."
if [ -f "$CONFIG_FILE" ]; then
    # Check for placeholder values
    if grep -q "YOUR_MOOMOO_ACCOUNT" "$CONFIG_FILE"; then
        echo "   ⚠️  Account placeholder not configured"
        echo "      Run: ./configure_opend_credentials.sh"
    else
        echo "   ✅ Account configured"
    fi

    if grep -q "YOUR_MOOMOO_PASSWORD" "$CONFIG_FILE"; then
        echo "   ⚠️  Password placeholder not configured"
        echo "      Run: ./configure_opend_credentials.sh"
    else
        echo "   ✅ Password configured"
    fi

    # Extract configuration values
    api_port=$(grep -o '<api_port>[0-9]*</api_port>' "$CONFIG_FILE" | grep -o '[0-9]*' || echo "11111")
    websocket_port=$(grep -o '<websocket_port>[0-9]*</websocket_port>' "$CONFIG_FILE" | grep -o '[0-9]*' || echo "33333")
    telnet_port=$(grep -o '<telnet_port>[0-9]*</telnet_port>' "$CONFIG_FILE" | grep -o '[0-9]*' || echo "22222")

    echo "   📊 API Port: $api_port"
    echo "   🌐 WebSocket Port: $websocket_port"
    echo "   📞 Telnet Port: $telnet_port"

else
    echo "   ❌ Configuration file not found"
    api_port="11111"
    websocket_port="33333"
    telnet_port="22222"
fi

# 5. Check network ports
echo ""
echo "🌐 Checking network ports..."
check_port "$api_port" "API"
check_port "$websocket_port" "WebSocket"
check_port "$telnet_port" "Telnet"

# 6. Check system dependencies
echo ""
echo "🔍 Checking system dependencies..."

# Check for Python (for WebSocket testing)
if command_exists python3; then
    echo "   ✅ Python3 available"
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo "      Version: $python_version"
else
    echo "   ⚠️  Python3 not found"
    echo "      Install with: sudo apt install python3 python3-pip"
fi

# Check for curl (for API testing)
if command_exists curl; then
    echo "   ✅ curl available"
else
    echo "   ⚠️  curl not found"
    echo "      Install with: sudo apt install curl"
fi

# Check for netstat (for port checking)
if command_exists netstat; then
    echo "   ✅ netstat available"
else
    echo "   ⚠️  netstat not found"
    echo "      Install with: sudo apt install net-tools"
fi

# 7. Check timezone
echo ""
echo "⏰ Checking timezone configuration..."
current_tz=$(timedatectl show --property=Timezone --value)
echo "   Current timezone: $current_tz"
echo "   Current time: $(date)"

if [ "$current_tz" = "Asia/Hong_Kong" ] || [ "$current_tz" = "Asia/Shanghai" ]; then
    echo "   ✅ Timezone suitable for Asian markets"
else
    echo "   ⚠️  Consider setting timezone to Asia/Hong_Kong for Asian markets"
    echo "      sudo timedatectl set-timezone Asia/Hong_Kong"
fi

# 8. Memory and system resources
echo ""
echo "💾 Checking system resources..."
total_mem=$(free -h | awk '/^Mem:/ {print $2}')
available_mem=$(free -h | awk '/^Mem:/ {print $7}')
echo "   Total memory: $total_mem"
echo "   Available memory: $available_mem"

# Check disk space
disk_usage=$(df -h "$OPEND_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 90 ]; then
    echo "   ✅ Disk space sufficient ($disk_usage% used)"
else
    echo "   ⚠️  Disk space low ($disk_usage% used)"
fi

# 9. Generate summary
echo ""
echo "📋 Configuration Summary"
echo "======================="

# Determine overall status
issues=0

if [ "$all_files_exist" = false ]; then
    issues=$((issues + 1))
fi

if grep -q "YOUR_MOOMOO" "$CONFIG_FILE" 2>/dev/null; then
    issues=$((issues + 1))
fi

if [ ! -d "$LOG_DIR" ] || [ ! -w "$LOG_DIR" ]; then
    issues=$((issues + 1))
fi

if [ "$issues" -eq 0 ]; then
    echo "✅ OpenD appears to be configured correctly"
    echo ""
    echo "🚀 Ready to start OpenD:"
    echo "   $OPEND_DIR/start_opend.sh"
    echo ""
    echo "🧪 Test connections:"
    echo "   ./test_opend_websocket.py"
    echo "   curl http://127.0.0.1:$api_port (after OpenD starts)"
else
    echo "⚠️  $issues issue(s) found that need attention"
    echo ""
    echo "🔧 Recommended actions:"

    if [ "$all_files_exist" = false ]; then
        echo "   - Check OpenD installation"
    fi

    if grep -q "YOUR_MOOMOO" "$CONFIG_FILE" 2>/dev/null; then
        echo "   - Run: ./configure_opend_credentials.sh"
    fi

    if [ ! -d "$LOG_DIR" ] || [ ! -w "$LOG_DIR" ]; then
        echo "   - Run: ./setup_opend_environment.sh"
    fi
fi

echo ""
echo "📚 Available Scripts:"
echo "==================="
echo "Environment setup:    ./setup_opend_environment.sh"
echo "Credential config:    ./configure_opend_credentials.sh"
echo "WebSocket test:       ./test_opend_websocket.py"
echo "This validation:      ./validate_opend_setup.sh"
echo ""
echo "Start OpenD:          $OPEND_DIR/start_opend.sh"
echo "Stop OpenD:           $OPEND_DIR/stop_opend.sh"