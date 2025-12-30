# Catalyst Trading System International - Agent Architecture

**Name of Application:** Catalyst Trading System International  
**Name of File:** architecture-international.md  
**Version:** 5.1.0  
**Last Updated:** 2025-12-29  
**Target Exchange:** Hong Kong Stock Exchange (HKEX)  
**Broker:** Moomoo via OpenD Gateway  
**Architecture:** AI Agent Pattern (Simple Droplet + Claude API + OpenD)  
**Status:** Production Ready

---

## REVISION HISTORY

**v5.1.0 (2025-12-29)** - MOOMOO BRANDING CLEANUP
- **BREAKING**: Removed all Futu references - use Moomoo terminology only
- **BREAKING**: Removed Docker approach - OpenD runs as native binary
- Fixed Python SDK: `moomoo-api` (not `futu-api`)
- Fixed imports: `from moomoo import ...` (not `from futu import ...`)
- Fixed config format: `<moomoo_opend>` root element
- Fixed SecurityFirm: `MOOMOOAU` for Australian accounts
- Download OpenD from: https://www.moomoo.com/download/OpenAPI
- Official docs: https://openapi.moomoo.com/moomoo-api-doc/en/intro/intro.html

**v5.0.0 (2025-12-20)** - BROKER MIGRATION: IBKR → MOOMOO
- Migrated from Interactive Brokers to Moomoo
- Replaced IBGA Docker container with OpenD
- No more IB Key 2FA issues
- Real-time market data included

**v4.2.0 (2025-12-13)** - Cron Scheduling Configured  
**v4.1.0 (2025-12-11)** - Production Ready Updates  
**v4.0.0 (2025-12-10)** - IBGA Socket API Integration  
**v3.0.0 (2025-12-09)** - Deprecated  
**v2.0.0 (2025-12-03)** - Simplified Architecture  
**v1.0.0 (2025-12-03)** - Initial Agent Architecture

---

## 1. Architecture Overview

### 1.1 Current Production Setup

Minimal infrastructure with Moomoo OpenD (native binary):

- **1 small droplet** ($6/month) - IP: 209.38.87.27
- **1 Python script** (the agent)
- **OpenD** (native binary gateway - NO Docker)
- **Cron** (the trigger)
- **Claude API** (the brain)
- **Moomoo API** (the broker via `moomoo-api` Python SDK)
- **PostgreSQL** (own DO Managed DB)

### 1.2 Why Moomoo (Migrated from IBKR Dec 2025)

| Aspect | IBKR (Old) | Moomoo (New) |
|--------|------------|--------------|
| **Gateway** | IBGA Docker + Java + VNC | OpenD native binary |
| **Authentication** | IB Key 2FA (constant failures) | Password + unlock |
| **Market Data** | 15-min delayed (without subscription) | Real-time included |
| **Container deps** | Docker, Java 17, JavaFX | None (native Linux) |
| **Debug method** | VNC into container | Simple log files |
| **Reconnection** | Manual re-auth often | Auto-reconnect |
| **API Type** | ib_async socket | moomoo-api socket |

### 1.3 Operational Schedule

| Session | HK Time | UTC (Server) | Cron Expression |
|---------|---------|--------------|-----------------|
| Morning | 09:30 HKT | 01:30 UTC | `30 1 * * 1-5` |
| Afternoon | 13:00 HKT | 05:00 UTC | `0 5 * * 1-5` |

**Cron Jobs:**
```cron
# Morning session start (09:30 HKT = 01:30 UTC)
30 1 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1

# Afternoon session start (13:00 HKT = 05:00 UTC)
0 5 * * 1-5 cd /root/Catalyst-Trading-System-International/catalyst-international && ./venv/bin/python3 agent.py >> logs/cron.log 2>&1
```

**HK Market Hours:**
- Morning: 09:30 - 12:00 HKT
- Lunch Break: 12:00 - 13:00 HKT (no trading)
- Afternoon: 13:00 - 16:00 HKT

### 1.4 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                DIGITALOCEAN DROPLET ($6/month)                       │
│                IP: 209.38.87.27                                      │
│                                                                      │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────────┐        │
│   │   CRON   │────▶│    AGENT     │────▶│      TOOLS       │        │
│   │          │     │   (Python)   │     │    (Functions)   │        │
│   │ 9:30 AM  │     │              │     │                  │        │
│   │ 1:00 PM  │     │ Calls Claude │     │ - scan_market()  │        │
│   │          │     │ Executes     │     │ - get_news()     │        │
│   └──────────┘     │ Tools        │     │ - execute_trade()│        │
│                    └──────────────┘     │ - check_risk()   │        │
│                           │             └────────┬─────────┘        │
│                           │                      │                  │
│                           ▼                      ▼                  │
│                    ┌──────────────┐     ┌──────────────────┐        │
│                    │   CLAUDE     │     │   MOOMOO CLIENT  │        │
│                    │    API       │     │                  │        │
│                    │  (Anthropic) │     │  brokers/moomoo.py│       │
│                    └──────────────┘     └────────┬─────────┘        │
│                                                  │                  │
│                                                  ▼                  │
│                                         ┌──────────────────┐        │
│                                         │     OpenD        │        │
│                                         │  (Native Binary) │        │
│                                         │  Port 11111      │        │
│                                         └────────┬─────────┘        │
└──────────────────────────────────────────────────┼──────────────────┘
                                                   │
                      ┌────────────────────────────┼────────────────┐
                      │                            │                │
                      ▼                            ▼                ▼
              ┌──────────────┐           ┌──────────────┐   ┌──────────────┐
              │   MOOMOO     │           │  POSTGRESQL  │   │    HKEX      │
              │   SERVERS    │           │  (DO Managed)│   │   EXCHANGE   │
              └──────────────┘           └──────────────┘   └──────────────┘
```

### 1.5 Agent Loop Flow

```
┌───────────────────┐
│ 1. CRON Triggers  │  ← 09:30 HKT or 13:00 HKT
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. Build Context  │  ← Load positions, cash, market state
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. Call Claude    │  ← Send context + tools to Claude API
│    API            │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. Claude Request │  ← Claude decides which tool to use
│    Tool +         │
│    Execute Tool   │  ← MoomooClient calls OpenD
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 5. Return Result  │  ← Tool result to Claude
│    to Claude      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 6. Loop Until     │  ← Claude may call more tools
│    Claude Done    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 7. Log & Exit     │  ← Wait for next cron
└───────────────────┘
```

---

## 2. File Structure

```
catalyst-international/
│
├── agent.py                    # Main agent script (runs via cron)
├── tools.py                    # Tool definitions for Claude
├── tool_executor.py            # Executes tool requests
├── safety.py                   # Validates all actions
│
├── brokers/
│   ├── __init__.py
│   └── moomoo.py               # Moomoo client via OpenD (v1.0.0)
│
├── data/
│   ├── __init__.py
│   ├── market.py               # Market data fetching
│   ├── news.py                 # News/sentiment
│   └── database.py             # PostgreSQL client
│
├── config/
│   ├── settings.yaml           # All configuration
│   └── prompts/
│       └── system.md           # Claude's instructions
│
├── scripts/
│   └── health_check.sh         # Health monitoring
│
├── logs/                       # Daily log files
│
├── requirements.txt            # Python dependencies
└── README.md

/root/opend/                    # OpenD gateway (separate directory)
├── OpenD                       # Native binary executable
├── OpenD.xml                   # Configuration file
└── logs/                       # OpenD logs
```

---

## 3. OpenD Configuration

### 3.1 Download OpenD

Download from official Moomoo site: **https://www.moomoo.com/download/OpenAPI**

Select the Ubuntu/Linux version and extract to `/root/opend/`

```bash
# Create directory
mkdir -p /root/opend
cd /root/opend

# Extract downloaded archive (version may vary)
tar -xzf OpenD_*_Ubuntu.tar.gz

# Make executable
chmod +x OpenD
```

### 3.2 Configuration File (OpenD.xml)

```xml
<moomoo_opend>
    <!-- Basic parameters -->
    <ip>127.0.0.1</ip>
    <api_port>11111</api_port>
    
    <!-- Login credentials -->
    <login_account>your_email@example.com</login_account>
    
    <!-- Use MD5 hash for production (more secure) -->
    <login_pwd_md5>YOUR_32_CHAR_MD5_HASH</login_pwd_md5>
    
    <!-- OR plain text for testing (less secure) -->
    <!-- <login_pwd>your_password</login_pwd> -->
    
    <!-- Language: en or chs -->
    <lang>en</lang>
    
    <!-- Logging -->
    <log_level>info</log_level>
    
    <!-- API Settings -->
    <push_proto_type>0</push_proto_type>
    <price_reminder_push>1</price_reminder_push>
    <auto_hold_quote_right>1</auto_hold_quote_right>
    
    <!-- Timezone for HK trading -->
    <future_trade_api_time_zone>UTC+8</future_trade_api_time_zone>
    
    <!-- US-specific protections (if trading US stocks) -->
    <pdt_protection>1</pdt_protection>
    <dtcall_confirmation>1</dtcall_confirmation>
</moomoo_opend>
```

**Generate MD5 hash for password:**
```bash
echo -n "your_password" | md5sum | cut -d' ' -f1
```

### 3.3 Systemd Service

```ini
# /etc/systemd/system/opend.service
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
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable opend
sudo systemctl start opend
sudo systemctl status opend
```

### 3.4 Environment Variables

```bash
# /root/Catalyst-Trading-System-International/catalyst-international/.env
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
MOOMOO_TRADE_PWD=your_trade_unlock_password
```

---

## 4. MoomooClient Implementation

### 4.1 brokers/moomoo.py (v1.0.0)

Key features:
- Simple password-based authentication (no 2FA)
- Real-time market data included
- HKEX tick size rounding (`_round_to_tick()`)
- Symbol format conversion (`_format_hk_symbol()`)
- Position and order management
- Auto-reconnect support

```python
# Key methods in MoomooClient:

def connect(self) -> bool:
    """Connect to OpenD and unlock trading"""

def get_quote(self, symbol: str) -> dict:
    """Get real-time quote for a symbol"""

def get_portfolio(self) -> dict:
    """Get cash, equity, positions, P&L"""

def get_positions(self) -> list[Position]:
    """Get all open positions"""

def execute_trade(self, symbol, side, quantity, order_type, limit_price,
                  stop_loss, take_profit, reason) -> OrderResult:
    """Execute trade"""

def close_position(self, symbol, reason) -> OrderResult:
    """Close a specific position"""

def close_all_positions(self, reason) -> list[OrderResult]:
    """Emergency: close all positions"""

def _format_hk_symbol(self, symbol: str) -> str:
    """Format '700' -> 'HK.00700' for Moomoo API"""

def _round_to_tick(self, price: float) -> float:
    """Round to valid HKEX tick size (11 tiers)"""
```

### 4.2 Symbol Format Handling

```python
# Input formats → Moomoo format
client._format_hk_symbol('700')   # → 'HK.00700'
client._format_hk_symbol('0700')  # → 'HK.00700'
client._format_hk_symbol('9988')  # → 'HK.09988'

# Parse back from Moomoo format
client._parse_hk_symbol('HK.00700')  # → '700'
```

### 4.3 Key Difference: No Bracket Orders

Unlike IBKR, Moomoo doesn't support native bracket orders (parent-child linked orders).
Stop loss and take profit must be managed by:
- Option A: Conditional orders (if supported by account type)
- Option B: Agent-managed stops (Claude monitors and issues sell orders)

---

## 5. Commands

### Start OpenD
```bash
sudo systemctl start opend
# OR manually:
cd /root/opend && ./OpenD
```

### Check OpenD Status
```bash
sudo systemctl status opend
```

### Check OpenD Logs
```bash
tail -f /root/opend/logs/*.log
```

### Test Connection
```bash
source /root/Catalyst-Trading-System-International/catalyst-international/venv/bin/activate
python3 /root/opend/test_connection.py
```

### Quick Connection Test
```python
from brokers.moomoo import MoomooClient

client = MoomooClient(paper_trading=True)
client.connect()
print(client.get_portfolio())
client.disconnect()
```

---

## 6. Cost Summary

| Item | Cost |
|------|------|
| DO Droplet (Basic, 1GB) | $6 |
| DO Managed PostgreSQL | $15 |
| Claude API (~200 cycles × 5K tokens) | ~$15-25 |
| Moomoo Data (real-time included) | $0 |
| **Total** | **~$36-46/month** |

---

## 7. Key Resources

| Resource | URL |
|----------|-----|
| OpenD Download | https://www.moomoo.com/download/OpenAPI |
| Moomoo API Docs | https://openapi.moomoo.com/moomoo-api-doc/en/intro/intro.html |
| Python SDK (PyPI) | https://pypi.org/project/moomoo-api/ |
| Quick Start Guide | https://openapi.moomoo.com/moomoo-api-doc/en/quick/opend-base.html |

---

## 8. HKEX Tick Sizes

| Price Range (HKD) | Tick Size |
|-------------------|-----------|
| < 0.25 | 0.001 |
| 0.25 - 0.50 | 0.005 |
| 0.50 - 10.00 | 0.01 |
| 10.00 - 20.00 | 0.02 |
| 20.00 - 100.00 | 0.05 |
| 100.00 - 200.00 | 0.10 |
| 200.00 - 500.00 | 0.20 |
| 500.00 - 1000.00 | 0.50 |
| 1000.00 - 2000.00 | 1.00 |
| 2000.00 - 5000.00 | 2.00 |
| > 5000.00 | 5.00 |

Use `client._round_to_tick(price)` to ensure compliance.

---

## 9. Known Limitations

1. **No native bracket orders** - Moomoo doesn't support parent-child linked SL/TP orders
2. **Lot size** - HKEX requires trades in multiples of 100 shares
3. **Market hours only** - No pre/post market trading for HKEX

---

## End of Document
