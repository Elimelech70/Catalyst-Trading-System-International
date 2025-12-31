# CLAUDE.md - Catalyst Trading System

**Name of Application**: Catalyst Trading System
**Name of file**: CLAUDE.md
**Version**: 3.1.0
**Last Updated**: 2025-12-31
**Purpose**: Complete operational guidelines for Claude Code on production systems

---

## REVISION HISTORY

**v3.1.0 (2025-12-31)** - STREAMLINED FOR INTL
- Migrated lessons 11-15 to `claude_learnings` database table
- Removed verbose code examples (reference actual files)
- Removed US-specific content (this is INTL system)
- Reduced file size by ~40%

**v3.0.0 (2025-12-20)** - BROKER MIGRATION: IBKR → MOOMOO/FUTU
- Migrated from Interactive Brokers to Moomoo/Futu OpenD
- Added `brokers/futu.py` client implementation

*Full history in git commits*

---

## ⚠️ CRITICAL: READ BEFORE ANY ACTION

### The Three Questions You MUST Ask First

Before touching ANY code or making ANY recommendation:

1. **What is my PURPOSE right now?**
   - 🎯 Designing? → Need architecture docs, requirements, schemas
   - 🔧 Implementing? → Need specific design doc, authoritative sources, exact specs
   - 🐛 Troubleshooting? → Need logs, error messages, current state, what changed

2. **What QUALITY information do I need?**
   - 📚 For design: Architecture docs, database schema, functional specs
   - 📖 For implementation: Authoritative sources (Tier 1 only!), design doc version
   - 🔍 For troubleshooting: Recent logs, error traces, last working state

3. **Am I FOCUSED or scattered?**
   - ✅ Focused: One clear goal, minimal information, specific outcome
   - ❌ Scattered: Multiple goals, too much context, vague direction

**NEVER do a quick solution if the issue is complex.** Complex = impacts multiple services, requires architecture changes, affects database schema.

---

## 📁 Source of Truth: GitHub Design Documents

Design documents and code files live in GitHub. **ALWAYS check these FIRST.**

### Design Document Naming Convention
```
{design-document-name}.md

Examples:
  architecture.md
  database-schema.md
  functional-specification.md
```

**Finding the Latest Version**: Each design document contains a **header** with version information. Always check:
- `Version:` field in header
- `Last Updated:` date
- `REVISION HISTORY:` section

### Service File Naming Convention
```
{service-name}-service.py

Examples:
  orchestration-service.py
  scanner-service.py
  trading-service.py
  risk-manager-service.py
```

### Key Design Documents (Read BEFORE implementing)

| Document | Purpose | Location |
|----------|---------|----------|
| `architecture.md` | System architecture, service matrix | GitHub: Documentation/Design/ |
| `database-schema.md` | 3NF normalized schema, helper functions | GitHub: Documentation/Design/ |
| `functional-specification.md` | Functional specs, MCP tools, cron jobs | GitHub: Documentation/Design/ |

**IMPORTANT**: Always check the header inside each file to confirm the current version.

---

## 🏗️ Architecture Evolution: Key Lessons

### Two Architecture Patterns We Use

**US System: Microservices (8 Docker Containers)**
```
Pros: Fault isolation, independent scaling, well-established
Cons: 5000+ lines, $24+ monthly, 8 logs to check
```

**International System: AI Agent (Single Script + Claude API)**
```
Pros: ~900 lines, $6 monthly, 1 log file, Claude decides
Cons: Single point of failure, requires Claude API
```

### Architecture Selection Wisdom

| Factor | Choose Microservices | Choose AI Agent |
|--------|---------------------|-----------------|
| **Complexity** | High, many decision branches | Simpler, flow-based |
| **Existing Code** | Already built, working | Starting fresh |
| **Debug Needs** | Need isolated service logs | Single unified log |
| **AI Decision Making** | Hardcoded workflow | Claude decides dynamically |
| **Team Size** | Multiple developers | Solo developer |

### The Beautiful Insight

> **"Microservices encode decisions in code. AI Agents let Claude make decisions at runtime."**

For the International system, instead of encoding "if news positive AND volume > 1.5x AND RSI < 70 THEN trade" in code, we give Claude tools and let it decide based on context.

---

## 🏛️ System Architecture Overview

### Current US Operational Model

**CRON runs the trading system. Claude Code generates reports. GitHub is the bridge.**

```
┌─────────────────────────────────────────────────────────────────┐
│  CRON (PRIMARY)     →  Services execute  →  Data in Database    │
│         ↓                                                       │
│  Claude Code        →  Queries DB        →  Generates Reports   │
│         ↓                                                       │
│  GitHub             ←  Reports pushed    ←  Analysis docs       │
│         ↓                                                       │
│  Claude Desktop     →  Reads from GitHub →  Reviews performance │
└─────────────────────────────────────────────────────────────────┘
```

### Role Definitions

| Component | Role | What It Does |
|-----------|------|--------------|
| **Cron** | PRIMARY Operator | Schedules and triggers all trading workflows |
| **Claude Code** | Analysis & Reporting | Generates reports, analysis docs, pushes to GitHub |
| **GitHub** | Central Hub | Stores design docs, reports, analysis |
| **Claude Desktop** | Monitoring | Reads reports from GitHub (NO direct droplet connection) |
| **Services** | Execution | Execute trading logic when triggered by cron |

### What Does NOT Happen (Current State)
❌ Claude Desktop does NOT connect directly to droplet services  
❌ Claude Code does NOT run the trading system (cron does)  
❌ No MCP protocol connection between Claude Desktop and droplet  
❌ No Nginx/HTTPS exposure needed  

### 8-Service Microservices Architecture (US)

| # | Service | Port | Purpose | Triggered By |
|---|---------|------|---------|--------------|
| 1 | Workflow | 5006 | Orchestrates trading workflows | Cron |
| 2 | Scanner | 5001 | Stock scanning & candidate filtering | Workflow |
| 3 | Pattern | 5002 | Chart pattern recognition | Scanner |
| 4 | Technical | 5003 | Technical indicators (RSI, MACD, etc.) | Scanner |
| 5 | Risk Manager | 5004 | Position validation, emergency stops | Trading |
| 6 | Trading | 5005 | Alpaca API execution | Workflow |
| 7 | News | 5008 | News sentiment analysis | Scanner |
| 8 | Reporting | 5009 | Performance reports | Cron, Claude Code |

**Note**: Redis (6379) runs as infrastructure, not counted as a service.

### Infrastructure
- **Droplet**: Single DigitalOcean droplet (IP: 209.38.87.27)
- **Database**: DigitalOcean Managed PostgreSQL (3NF normalized schema)
- **Cache**: Redis (Docker container)
- **Location**: Perth timezone (AWST) → US markets (EST), HK markets (HKT)
- **Broker US**: Alpaca
- **Broker International**: Moomoo/Futu via OpenD gateway (migrated from IBKR Dec 2025)

---

## 🗄️ Database Schema Rules (3NF Normalized)

### CRITICAL: Normalization Rules

**Rule #1: Symbol stored ONLY in `securities` table**
```sql
-- ✅ CORRECT: Use security_id everywhere
SELECT s.symbol, th.close
FROM trading_history th
JOIN securities s ON s.security_id = th.security_id;

-- ❌ WRONG: No symbol column in fact tables
SELECT symbol, close FROM trading_history;  -- ERROR!
```

**Rule #2: Use Helper Functions**
```python
# Get or create security_id
security_id = await db.fetchval(
    "SELECT get_or_create_security($1)", symbol
)

# Get or create time_id  
time_id = await db.fetchval(
    "SELECT get_or_create_time($1)", timestamp
)
```

**Rule #3: Verify Column Names Against ACTUAL Database**

Before writing any INSERT/UPDATE:
1. Check actual table schema: `\d table_name`
2. Verify column names match exactly
3. Test query against dev/paper database first

### Known Schema Mismatches (Lessons Learned)

| Design Doc Column | Actual DB Column | Table |
|------------------|------------------|-------|
| `price_at_scan` | `price` | scan_results |
| `volume_at_scan` | `volume` | scan_results |
| `rank_in_scan` | `rank` | scan_results |
| `final_candidate` | `selected_for_trading` | scan_results |
| `cycle_date` | (removed) | trading_cycles |
| `cycle_number` | (removed) | trading_cycles |
| `session_mode` | `mode` | trading_cycles |
| `scan_completed_at` | `stopped_at` | trading_cycles |

**ALWAYS verify against deployed database, not just design docs.**

---

## 📜 File Header Standard

ALL artifacts MUST have this header:

```python
"""
Name of Application: Catalyst Trading System
Name of file: {filename}.py
Version: X.Y.Z
Last Updated: YYYY-MM-DD
Purpose: Brief description

REVISION HISTORY:
vX.Y.Z (YYYY-MM-DD) - Description of changes
- Specific change 1
- Specific change 2

Description:
Extended description of what this file does.
"""
```

### Version Numbering
- **Major (X)**: Breaking changes, architecture changes
- **Minor (Y)**: New features, significant updates
- **Patch (Z)**: Bug fixes, schema alignment fixes

---

## 🚨 CRITICAL LESSONS LEARNED (DO NOT REPEAT)

### Lesson 1: Schema Mismatch Disasters
**Problem**: Code referenced columns that don't exist in deployed DB  
**Solution**: ALWAYS verify schema against actual database before coding

```bash
# Check actual table structure
psql $DATABASE_URL -c "\d scan_results"
psql $DATABASE_URL -c "\d trading_cycles"
```

### Lesson 2: Version Sync Between Local/GitHub/Droplet
**Problem**: Different versions in different places  
**Solution**: After ANY fix, push to GitHub immediately

```bash
# Check version in running container
docker exec catalyst-scanner-1 head -20 /app/scanner-service.py

# Compare with GitHub
# If different, sync immediately
```

### Lesson 3: Quick Fixes Cause More Problems
**Problem**: "Quick fix" without understanding root cause  
**Solution**: If complex, STOP and make a prioritized list

### Lesson 4: Missing Foreign Keys
**Problem**: Inserting data without security_id FK  
**Solution**: ALWAYS use `get_or_create_security(symbol)` first

### Lesson 5: Time Zone Confusion
**Problem**: Perth (AWST) vs US (EST) time calculations wrong
**Solution**: Always store UTC, convert for display only

### Lesson 6: Order Side Bug (v1.2.0) - CRITICAL ⚠️
**Problem**: "long" positions placed as SHORT sells (81 positions affected Nov-Dec 2025)
**Root Cause**: `side == "buy"` didn't handle `side="long"` from workflow
**Solution**: Use `_normalize_side()` + `_validate_order_side_mapping()` in alpaca_trader.py v1.3.0
**Prevention**: Run `python3 scripts/test_order_side.py` before trading

**The Bug:**
```python
# ❌ WRONG: Simple ternary doesn't handle "long"/"short"
order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
# "long" → OrderSide.SELL (DISASTER!)

# ✅ CORRECT: Normalize first
def _normalize_side(side: str) -> str:
    side_lower = side.lower()
    if side_lower in ['buy', 'long']:
        return 'buy'
    elif side_lower in ['sell', 'short']:
        return 'sell'
    raise ValueError(f"Invalid side: {side}")
```

**Full details**: See `Documentation/Implementation/order-side-testing.md`

### Lesson 7: Sub-Penny Pricing Errors
**Problem**: Alpaca rejects orders with sub-penny prices (e.g., $15.123)
**Root Cause**: Price calculations producing more than 2 decimal places
**Solution**: Round all prices to 2 decimal places before submission

```python
# ❌ WRONG: Raw calculation
entry_price = current_price * 1.001  # Could be 15.1234567

# ✅ CORRECT: Round to valid tick size
entry_price = round(current_price * 1.001, 2)  # 15.12
stop_loss = round(entry_price * 0.98, 2)
take_profit = round(entry_price * 1.04, 2)
```

### Lesson 8: Error Handling Anti-Patterns
**Problem**: Bare `except:` statements hide critical errors
**Solution**: Use specific exception types, never bare except

```python
# ❌ WRONG: Bare except hides all errors
try:
    result = execute_trade()
except:
    return None  # What went wrong? Nobody knows!

# ✅ CORRECT: Specific exceptions with logging
try:
    result = execute_trade()
except ValueError as e:
    logger.error(f"Invalid parameters: {e}", extra={...})
    raise HTTPException(status_code=400, detail=str(e))
except asyncpg.PostgresError as e:
    logger.critical(f"Database error: {e}", exc_info=True)
    raise HTTPException(status_code=503, detail="Database unavailable")
```

### Lesson 9: Helper Function Verification
**Problem**: Services start without checking if DB helpers exist
**Solution**: Fail startup if helpers not found

```python
# At service startup
has_helper = await db.fetchval("""
    SELECT EXISTS (
        SELECT FROM pg_proc WHERE proname = 'get_or_create_security'
    )
""")
if not has_helper:
    raise RuntimeError("Missing get_or_create_security() - schema not deployed!")
```

### Lesson 10: Dynamic Security Discovery
**Problem**: Hardcoded stock lists don't adapt to market conditions
**Solution**: Use Alpaca Assets API for dynamic universe selection

```python
# ❌ OLD: Hardcoded list (v6.0)
STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', ...]  # Always same 10

# ✅ NEW: Dynamic from Alpaca (v6.1+)
assets = alpaca_client.get_all_assets(
    asset_class=AssetClass.US_EQUITY,
    status=AssetStatus.ACTIVE
)
# Returns 4,129 tradable stocks, select top 200 by volume
```

---

## 🌏 HKEX TRADING LESSONS (International System - Moomoo/Futu)

> **MIGRATED TO DATABASE:** Lessons 11-15 have been moved to the `claude_learnings` table in the consciousness database for cross-agent sharing.
>
> Query learnings: `SELECT * FROM claude_learnings WHERE agent_id = 'intl_claude' AND category = 'trading';`

Key implementations remain in `brokers/futu.py`:
- `_round_to_tick()` - HKEX 11-tier tick size compliance
- `_format_hk_symbol()` / `_parse_hk_symbol()` - HK.00700 format conversion

---

## 🔧 Implementation Workflow

### Before ANY Code Change

1. **Identify the service(s) affected**
2. **Read the relevant design doc** from GitHub
3. **Check current deployed version** in Docker container
4. **Verify database schema** matches your expectations

### For Troubleshooting

1. **Check logs first**:
   ```bash
   docker logs catalyst-{service}-1 --tail 100
   tail -n 100 /var/log/catalyst/{service}.log
   ```

2. **Check service health**:
   ```bash
   curl http://localhost:{port}/health
   docker-compose ps
   ```

3. **Check database state**:
   ```bash
   psql $DATABASE_URL -c "SELECT * FROM {table} ORDER BY created_at DESC LIMIT 10;"
   ```

4. **What changed recently?**:
   ```bash
   git log --oneline -10
   docker-compose logs --since 1h
   ```

### For New Implementation

1. **Copy existing similar service as template**
2. **Follow established patterns** - don't invent new ones
3. **Test locally/paper first** before production
4. **Update version header** in file
5. **Commit with descriptive message**:
   ```bash
   git commit -m "fix(scanner): v6.0.1 - align column names with deployed schema"
   ```

---

## 📋 INTL System File Locations

```
/root/Catalyst-Trading-System-International/catalyst-international/
├── agent.py              # Main trading agent
├── brokers/futu.py       # Moomoo/Futu client
├── tools.py              # Tool definitions
├── scripts/              # Utilities (heartbeat, reports)
├── config/               # Settings
└── Documentation/        # Design docs
```

**Version info is inside each file's header.**

---

## 🔄 Common Operations

### Pre-Trading Session Checklist
```bash
# Run order side test (CRITICAL - see Lesson 6)
python3 scripts/test_order_side.py
```
**Full checklist**: See `Documentation/Implementation/order-side-testing.md`

### Check Service Status
```bash
docker-compose ps
curl http://localhost:5001/health  # Scanner
curl http://localhost:5006/health  # Workflow
```

### Restart Single Service
```bash
docker-compose restart scanner
docker-compose logs scanner --tail 50
```

### Deploy Update (Zero Downtime)
```bash
# Update single service
docker-compose up -d --no-deps --build scanner

# Verify
curl http://localhost:5001/health
```

### View Logs
```bash
# Service logs
docker logs catalyst-scanner-1 --tail 100 -f

# System logs
tail -f /var/log/catalyst/trading.log
```

### Database Queries
```bash
# Quick query
psql $DATABASE_URL -c "SELECT * FROM trading_cycles ORDER BY started_at DESC LIMIT 5;"

# Interactive
psql $DATABASE_URL
```

### Download Files from Droplet to Local
```bash
# From VSCode terminal (local machine)
scp -i ~/.ssh/id_rsa root@<DROPLET_IP>:/root/catalyst-trading-mcp/services/*/*.py ./local-backup/
```

---

## ⛔ NEVER DO THESE

### General Rules (US + International)
1. **NEVER** modify production database schema without backup
2. **NEVER** deploy to production without testing on paper first
3. **NEVER** ignore version headers - always update them
4. **NEVER** assume design doc matches deployed schema
5. **NEVER** make "quick fixes" to complex multi-service issues
6. **NEVER** skip the three questions at the top of this file
7. **NEVER** use symbol VARCHAR in queries - use security_id FK
8. **NEVER** hardcode API keys - use environment variables
9. **NEVER** use simple ternary for order side conversion - handle "long"/"short"
10. **NEVER** trust that "buy"/"sell" is the only valid input
11. **NEVER** submit prices with more than 2 decimal places (US) or invalid tick sizes (HKEX)
12. **NEVER** use bare `except:` statements - use specific exceptions
13. **NEVER** start services without verifying helper functions exist
14. **NEVER** hardcode stock lists - use dynamic discovery

### Futu/HKEX-Specific Rules (International)
15. **NEVER** submit raw HK symbols - use `_format_hk_symbol()` for Futu format
16. **NEVER** size positions by shares alone - use dollar-based sizing
17. **NEVER** ignore lot size - HKEX requires multiples of 100 shares
18. **NEVER** assume bracket orders work - Futu doesn't support them natively
19. **NEVER** trade without checking `is_connected()` first
20. **NEVER** forget to call `disconnect()` when done

---

## ✅ ALWAYS DO THESE

### General Rules (US + International)
1. **ALWAYS** read design docs before implementing
2. **ALWAYS** verify database schema before INSERT/UPDATE
3. **ALWAYS** update version header after changes
4. **ALWAYS** push to GitHub after verified fixes
5. **ALWAYS** check logs first when troubleshooting
6. **ALWAYS** use helper functions for security_id/time_id
7. **ALWAYS** test on paper trading before live
8. **ALWAYS** make prioritized list for complex changes
9. **ALWAYS** verify order logs show correct side mapping (long→buy, short→sell)
10. **ALWAYS** use specific exception types with proper logging
11. **ALWAYS** verify helper functions exist at service startup

### US-Specific Rules (Alpaca)
12. **ALWAYS** run `python3 scripts/test_order_side.py` before trading sessions
13. **ALWAYS** round prices to 2 decimal places before Alpaca submission
14. **ALWAYS** use Alpaca Assets API for dynamic stock universe

### Futu/HKEX-Specific Rules (International)
15. **ALWAYS** call `client.connect()` before any trading operations
16. **ALWAYS** round prices to valid HKEX tick size (`_round_to_tick()`)
17. **ALWAYS** use `_format_hk_symbol()` for Futu's "HK.00700" format
18. **ALWAYS** calculate position size in dollars first, then convert to shares
19. **ALWAYS** use lot size of 100 for HKEX stocks (round quantity to 100s)
20. **ALWAYS** check `get_portfolio()` for current positions before new trades
21. **ALWAYS** implement agent-managed stops (Futu lacks bracket orders)
22. **ALWAYS** call `client.disconnect()` on exit or error

---

## 🎯 Quick Reference: Decision Tree

```
User Request
    │
    ▼
Is it a SIMPLE fix (single service, one file)?
    │
    ├── YES → Verify schema → Implement → Test → Deploy → Push to GitHub
    │
    └── NO (Complex: multi-service, architecture, schema change)
         │
         ▼
    STOP! Create prioritized action list:
         1. What services affected?
         2. What design docs to review?
         3. What's the rollback plan?
         4. Test sequence (unit → integration → paper → prod)
         5. Who needs to know?
```

---

## 📞 Emergency Procedures

### If System Goes Wrong

1. **Immediate Stop**:
   ```bash
   curl -X POST http://localhost:5004/api/v1/emergency-stop
   ```

2. **Disable Cron**:
   ```bash
   crontab -r  # Remove all cron jobs
   ```

3. **Stop Services**:
   ```bash
   docker-compose stop
   ```

4. **Review Logs**:
   ```bash
   tail -n 500 /var/log/catalyst/autonomous-trading.log
   ```

5. **Check Alpaca Directly**:
   - Log into Alpaca dashboard
   - Verify positions
   - Manually close if needed

---

## 🛠️ AI Agent Tools (Claude's Advantage)

These 12 tools give Claude dynamic decision-making power that hardcoded workflows can't match:

### Market Analysis Tools

| Tool | Purpose | Why Claude Does It Better |
|------|---------|---------------------------|
| `scan_market` | Find trading candidates | Claude interprets momentum + volume contextually |
| `get_quote` | Current price/volume | Claude decides when to check based on strategy |
| `get_technicals` | RSI, MACD, MAs, ATR | Claude weighs indicators based on market regime |
| `detect_patterns` | Chart patterns | Claude combines patterns with news context |
| `get_news` | News and sentiment | Claude understands nuance, not just scores |

### Risk & Portfolio Tools

| Tool | Purpose | Why Claude Does It Better |
|------|---------|---------------------------|
| `check_risk` | Validate against limits | Claude can explain WHY a trade is risky |
| `get_portfolio` | Current positions, P&L | Claude tracks mental model of exposure |

### Execution Tools

| Tool | Purpose | Why Claude Does It Better |
|------|---------|---------------------------|
| `execute_trade` | Submit order to broker | Claude provides reasoning for audit trail |
| `close_position` | Exit single position | Claude decides WHICH position and WHY |
| `close_all` | Emergency exit | Claude can explain the crisis in alert |

### Communication Tools

| Tool | Purpose | Why Claude Does It Better |
|------|---------|---------------------------|
| `send_alert` | Email notifications | Claude writes human-readable explanations |
| `log_decision` | Audit trail | Claude explains reasoning, not just actions |

**Full tool definitions:** See `tools.py`

### Tool Usage Rules (Claude Must Follow)

1. **ALWAYS** call `check_risk` before `execute_trade`
2. **ALWAYS** provide `reason` for trades and closes (audit trail)
3. **ALWAYS** call `log_decision` to record reasoning (ML training data)
4. **NEVER** call `execute_trade` if `check_risk` returns `approved: false`
5. **IMMEDIATELY** call `close_all` if daily loss exceeds limit
6. **PREFER** `limit` orders over `market` for better fills

---

## 🌏 International System Architecture (HKEX via Moomoo/Futu)

### Key Architecture Differences

| Aspect | US (Microservices) | International (Agent) |
|--------|-------------------|----------------------|
| **Components** | 8 Docker containers | 1 Python script + OpenD |
| **Files** | 50+ | ~10 |
| **Lines of code** | 5000+ | ~900 |
| **Monthly cost** | $24+ droplet | $6 droplet |
| **Decision making** | Hardcoded workflow | Claude decides dynamically |
| **Broker** | Alpaca | Moomoo/Futu via OpenD |
| **Debugging** | 8 service logs | 1 log file + reasoning |

### Why Moomoo/Futu (Migrated from IBKR Dec 2025)

| Aspect | IBKR (Old) | Moomoo/Futu (New) |
|--------|------------|-------------------|
| **Gateway** | IBGA Docker + Java + VNC | OpenD native binary |
| **Authentication** | IB Key 2FA (constant failures) | Password + unlock |
| **Market Data** | 15-min delayed (no subscription) | Real-time included |
| **Container deps** | Docker, Java 17, JavaFX | None (native) |
| **Debug method** | VNC into container | Simple log files |
| **Reconnection** | Manual re-auth often | Auto-reconnect |

### Agent Loop Pattern
```
CRON triggers → Build Context → Call Claude API → Claude requests tool
    → Execute tool → Return result → Claude continues → Loop until done
```

### OpenD Gateway Setup
```
/root/opend/
├── docker-compose.yml    # OpenD container config
├── .env                  # FUTU_USER, FUTU_PWD, FUTU_TRADE_PWD
├── logs/                 # OpenD logs
└── test_connection.py    # Connection verification script
```

**Start OpenD:**
```bash
cd /root/opend && docker compose up -d
```

**Test connection:**
```bash
source /root/Catalyst-Trading-System-International/catalyst-international/venv/bin/activate
python3 /root/opend/test_connection.py
```

### Why Agent for International
- Fresh start, no legacy code
- Perth-aligned hours (no overnight trading)
- Claude API handles complex decisions dynamically
- Simpler debugging (1 log file + decision reasoning)
- Lower operational cost ($6 vs $24+)
- Every decision logged with reasoning (ML training data)
- Real-time market data (no delayed data issues)

### File Structure

**International System (Agent):**
```
catalyst-international/
├── agent.py              # ~200 lines (main loop)
├── tools.py              # ~100 lines (definitions)
├── tool_executor.py      # ~150 lines (routing)
├── safety.py             # ~100 lines (validation)
├── brokers/
│   └── futu.py           # ~500 lines (Moomoo/Futu client)
├── data/market.py        # ~150 lines
└── config/settings.yaml  # ~50 lines
Total: ~1000 lines, ~10 files
```

**OpenD Gateway (separate directory):**
```
/root/opend/
├── docker-compose.yml
├── .env
└── test_connection.py
```

---

## 📝 End of CLAUDE.md

**Remember**: ALWAYS verify against the deployed database schema before writing code.

**Location**: `/root/Catalyst-Trading-System-International/catalyst-international/CLAUDE.md`

**Query learnings**: `SELECT * FROM claude_learnings WHERE agent_id = 'intl_claude';`
