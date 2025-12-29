# Moomoo OpenD Migration: Cleanup Implementation Guide

**Name of Application:** Catalyst Trading System International  
**Name of File:** opend-migration-implementation.md  
**Version:** 1.0.0  
**Created:** 2025-12-29  
**Purpose:** Step-by-step guide for intl_claude to remove Futu references and install OpenD correctly  
**Priority:** CRITICAL - Complete before HKEX trading

---

## Executive Summary

This document provides intl_claude with a complete checklist to:
1. Remove all incorrect "Futu" references from codebase
2. Install OpenD native binary correctly (NOT Docker)
3. Ensure `moomoo-api` Python SDK is used (NOT `futu-api`)
4. Verify connectivity before trading

**Key Corrections:**
| ❌ WRONG | ✅ CORRECT |
|----------|-----------|
| `futu-api` | `moomoo-api` |
| `from futu import ...` | `from moomoo import ...` |
| `FutuClient` | `MoomooClient` |
| `SecurityFirm.FUTUSECURITIES` | `SecurityFirm.MOOMOOAU` |
| Docker container for OpenD | Native binary at `/root/opend/OpenD` |
| `<config>` root element | `<moomoo_opend>` root element |

---

## Phase 1: Stop Services & Backup

### 1.1 Stop Any Running Docker Containers

```bash
# Check for any Futu/OpenD containers
docker ps -a | grep -i futu
docker ps -a | grep -i opend

# Stop and remove if found
docker stop catalyst-opend 2>/dev/null
docker rm catalyst-opend 2>/dev/null

# Remove docker-compose if exists
rm -f /root/opend/docker-compose.yml
```

### 1.2 Backup Current Code

```bash
cd /root/Catalyst-Trading-System-International
git status
git add -A
git commit -m "Backup before Moomoo migration cleanup"
git push origin main
```

---

## Phase 2: Remove Futu References from Code

### 2.1 Delete Old Broker Files

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international

# Delete futu.py if it exists
rm -f brokers/futu.py

# Verify deletion
ls -la brokers/
```

### 2.2 Update brokers/__init__.py

Replace contents with:

```python
"""
Broker integrations for the Catalyst Trading Agent.

This package provides broker connectivity for:
- Moomoo for HKEX trading via OpenD gateway
"""

from brokers.moomoo import MoomooClient, get_moomoo_client, init_moomoo_client

__all__ = ["MoomooClient", "get_moomoo_client", "init_moomoo_client"]
```

### 2.3 Copy New moomoo.py

Copy the new `moomoo.py` file (provided separately) to:
```
/root/Catalyst-Trading-System-International/catalyst-international/brokers/moomoo.py
```

### 2.4 Update requirements.txt

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international

# Remove futu-api, add moomoo-api
sed -i 's/futu-api/moomoo-api/g' requirements.txt

# Verify
grep -i "moomoo\|futu" requirements.txt
# Should show: moomoo-api (NOT futu-api)
```

### 2.5 Reinstall Python Dependencies

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate

# Uninstall old package
pip uninstall futu-api -y 2>/dev/null

# Install correct package
pip install moomoo-api --break-system-packages

# Verify installation
pip show moomoo-api
python -c "from moomoo import OpenQuoteContext; print('moomoo-api OK')"
```

### 2.6 Search and Replace in All Files

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international

# Find all files with "futu" references
grep -ril "futu" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" .

# For each file found, update imports:
# OLD: from futu import ...
# NEW: from moomoo import ...

# OLD: FutuClient
# NEW: MoomooClient

# OLD: FUTU_HOST, FUTU_PORT, FUTU_TRADE_PWD
# NEW: MOOMOO_HOST, MOOMOO_PORT, MOOMOO_TRADE_PWD

# OLD: SecurityFirm.FUTUSECURITIES
# NEW: SecurityFirm.MOOMOOAU
```

### 2.7 Update .env File

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international

# Update environment variables
cat > .env << 'EOF'
# Moomoo OpenD Configuration
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
MOOMOO_TRADE_PWD=your_trade_unlock_password

# Database
DATABASE_URL=postgresql://...

# Claude API
ANTHROPIC_API_KEY=...
EOF
```

### 2.8 Update agent.py Imports

Find and replace in `agent.py`:

```python
# OLD
from brokers.futu import FutuClient, get_futu_client, init_futu_client

# NEW
from brokers.moomoo import MoomooClient, get_moomoo_client, init_moomoo_client
```

### 2.9 Update tool_executor.py

Find and replace broker references:

```python
# OLD
client = get_futu_client()

# NEW
client = get_moomoo_client()
```

---

## Phase 3: Install OpenD Native Binary

### 3.1 Download OpenD

Go to: **https://www.moomoo.com/download/OpenAPI**

Select: **Ubuntu/Linux** version

```bash
# Create directory
mkdir -p /root/opend
cd /root/opend

# Download (version number may vary)
# Use browser or wget with the actual download URL from the website
# Example:
wget "https://download.moomoo.com/..." -O OpenD_Ubuntu.tar.gz

# Extract
tar -xzf OpenD_Ubuntu.tar.gz

# Find and move the OpenD binary
find . -name "OpenD" -type f
mv ./OpenD_*/OpenD .

# Make executable
chmod +x OpenD

# Verify
ls -la OpenD
./OpenD --version
```

### 3.2 Create OpenD.xml Configuration

```bash
cat > /root/opend/OpenD.xml << 'EOF'
<moomoo_opend>
    <!-- Basic parameters -->
    <ip>127.0.0.1</ip>
    <api_port>11111</api_port>
    
    <!-- Login credentials - use your Moomoo account -->
    <login_account>your_email@example.com</login_account>
    
    <!-- Use MD5 hash for security -->
    <login_pwd_md5>YOUR_32_CHAR_MD5_HASH</login_pwd_md5>
    
    <!-- Language -->
    <lang>en</lang>
    
    <!-- Logging -->
    <log_level>info</log_level>
    
    <!-- API Settings -->
    <push_proto_type>0</push_proto_type>
    <price_reminder_push>1</price_reminder_push>
    <auto_hold_quote_right>1</auto_hold_quote_right>
    
    <!-- Timezone -->
    <future_trade_api_time_zone>UTC+8</future_trade_api_time_zone>
    
    <!-- Protections -->
    <pdt_protection>1</pdt_protection>
    <dtcall_confirmation>1</dtcall_confirmation>
</moomoo_opend>
EOF
```

**Generate MD5 hash:**
```bash
echo -n "your_password" | md5sum | cut -d' ' -f1
```

### 3.3 Create Systemd Service

```bash
cat > /etc/systemd/system/opend.service << 'EOF'
[Unit]
Description=Moomoo OpenD Gateway
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/opend
ExecStart=/root/opend/OpenD
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable opend

# Start service
sudo systemctl start opend

# Check status
sudo systemctl status opend
```

### 3.4 Verify OpenD is Running

```bash
# Check process
ps aux | grep OpenD

# Check port
netstat -tlnp | grep 11111
# OR
ss -tlnp | grep 11111

# Check logs
tail -f /root/opend/logs/*.log
```

---

## Phase 4: Create Test Connection Script

### 4.1 Create test_connection.py

```bash
cat > /root/opend/test_connection.py << 'EOF'
#!/usr/bin/env python3
"""
Test Moomoo OpenD Connection
Run this to verify OpenD is working before trading
"""

from moomoo import OpenQuoteContext, OpenSecTradeContext, TrdMarket, SecurityFirm, TrdEnv
import os

HOST = os.environ.get("MOOMOO_HOST", "127.0.0.1")
PORT = int(os.environ.get("MOOMOO_PORT", "11111"))
TRADE_PWD = os.environ.get("MOOMOO_TRADE_PWD", "")

def test_quote():
    """Test quote connection"""
    print("Testing Quote Connection...")
    ctx = OpenQuoteContext(host=HOST, port=PORT)
    ret, data = ctx.get_global_state()
    print(f"  Global State: ret={ret}")
    if ret == 0:
        print(f"  Data: {data}")
    ctx.close()
    return ret == 0

def test_market_data():
    """Test market data retrieval"""
    print("Testing Market Data...")
    ctx = OpenQuoteContext(host=HOST, port=PORT)
    ret, data = ctx.get_market_snapshot(["HK.00700"])  # Tencent
    print(f"  Snapshot: ret={ret}")
    if ret == 0 and not data.empty:
        print(f"  Tencent Last Price: {data.iloc[0]['last_price']}")
    ctx.close()
    return ret == 0

def test_trade():
    """Test trade connection"""
    print("Testing Trade Connection...")
    ctx = OpenSecTradeContext(
        filter_trdmarket=TrdMarket.HK,
        host=HOST,
        port=PORT,
        security_firm=SecurityFirm.MOOMOOAU  # For Moomoo Australia
    )
    
    # Try to unlock trade
    if TRADE_PWD:
        ret, data = ctx.unlock_trade(TRADE_PWD)
        print(f"  Trade Unlock: ret={ret}")
        if ret != 0:
            print(f"  Warning: {data}")
    
    # Get account info (paper trading)
    ret, data = ctx.accinfo_query(trd_env=TrdEnv.SIMULATE)
    print(f"  Account Query: ret={ret}")
    if ret == 0 and not data.empty:
        print(f"  Cash: {data.iloc[0]['cash']}")
    
    ctx.close()
    return ret == 0

if __name__ == "__main__":
    print("=" * 50)
    print("Moomoo OpenD Connection Test")
    print(f"Host: {HOST}, Port: {PORT}")
    print("=" * 50)
    
    results = {
        "Quote": test_quote(),
        "Market Data": test_market_data(),
        "Trade": test_trade(),
    }
    
    print("\n" + "=" * 50)
    print("Results:")
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(results.values())
    print("=" * 50)
    print(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    exit(0 if all_passed else 1)
EOF

chmod +x /root/opend/test_connection.py
```

### 4.2 Run Test

```bash
source /root/Catalyst-Trading-System-International/catalyst-international/venv/bin/activate
cd /root/opend
python3 test_connection.py
```

---

## Phase 5: Cleanup Old Files

### 5.1 Remove Docker Files

```bash
# Remove any old docker files
rm -f /root/opend/docker-compose.yml
rm -f /root/opend/Dockerfile

# Remove any futu references
rm -rf /root/opend/FutuOpenD* 2>/dev/null
```

### 5.2 Update Documentation Files

Update these files to remove Futu references:
- `brokers/README.md`
- `CLAUDE.md`
- Any other documentation

### 5.3 Verify No Futu References Remain

```bash
cd /root/Catalyst-Trading-System-International

# Search entire repo for futu (case insensitive)
grep -ril "futu" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.xml" --include="*.json" .

# Should return NO results (except maybe git history references)
```

---

## Phase 6: Final Verification Checklist

### 6.1 Pre-Trading Checklist

Run these commands and verify each passes:

```bash
# 1. OpenD service running
sudo systemctl status opend
# Expected: active (running)

# 2. OpenD port listening
ss -tlnp | grep 11111
# Expected: LISTEN on port 11111

# 3. moomoo-api installed (not futu-api)
pip show moomoo-api
# Expected: Name: moomoo-api

# 4. No futu-api installed
pip show futu-api
# Expected: WARNING: Package(s) not found: futu-api

# 5. Python import works
python -c "from moomoo import OpenQuoteContext; print('OK')"
# Expected: OK

# 6. Test connection script
python /root/opend/test_connection.py
# Expected: ALL TESTS PASSED

# 7. No futu references in code
grep -ril "futu" /root/Catalyst-Trading-System-International/catalyst-international --include="*.py"
# Expected: (no output)
```

### 6.2 Commit Changes

```bash
cd /root/Catalyst-Trading-System-International
git add -A
git commit -m "Migrate to Moomoo OpenD: Remove all Futu references

- Renamed futu.py to moomoo.py
- Changed imports from futu to moomoo
- Updated SecurityFirm to MOOMOOAU
- Changed env vars: FUTU_* to MOOMOO_*
- Installed native OpenD binary (no Docker)
- Created systemd service for OpenD
- Updated all documentation"

git push origin main
```

---

## Troubleshooting

### OpenD Won't Start

```bash
# Check logs
cat /root/opend/logs/*.log

# Common issues:
# - Wrong login credentials in OpenD.xml
# - Port 11111 already in use
# - Missing execute permission on OpenD binary
```

### Connection Refused

```bash
# Verify OpenD is running
ps aux | grep OpenD

# Verify port
netstat -tlnp | grep 11111

# Check firewall
ufw status
```

### Import Errors

```bash
# Reinstall moomoo-api
pip uninstall moomoo-api -y
pip install moomoo-api --break-system-packages

# Verify
python -c "from moomoo import OpenQuoteContext; print('OK')"
```

### SecurityFirm Error

If you see `SecurityFirm.FUTUSECURITIES` errors:
- Open the file mentioned in the error
- Change to `SecurityFirm.MOOMOOAU` for Australian accounts

---

## Resources

| Resource | URL |
|----------|-----|
| OpenD Download | https://www.moomoo.com/download/OpenAPI |
| API Documentation | https://openapi.moomoo.com/moomoo-api-doc/en/intro/intro.html |
| Python SDK | https://pypi.org/project/moomoo-api/ |
| Quick Start | https://openapi.moomoo.com/moomoo-api-doc/en/quick/opend-base.html |

---

## End of Document

**After completing all phases:**
1. Report completion to Craig
2. Run test_connection.py and share results
3. Wait for approval before live trading
