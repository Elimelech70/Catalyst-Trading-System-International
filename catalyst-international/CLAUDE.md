# CLAUDE.md - Catalyst Trading System

**Name of Application**: Catalyst Trading System
**Name of file**: CLAUDE.md
**Version**: 2.2.0
**Last Updated**: 2025-12-13
**Purpose**: Complete operational guidelines for Claude Code on production systems

---

## REVISION HISTORY

**v2.2.0 (2025-12-13)** - IBKR-SPECIFIC LESSONS LEARNED
- Added Lessons 11-14 for IBKR/HKEX trading
- Added delayed data trading rules
- Added HKEX tick size compliance
- Added dollar-based position sizing for IBKR
- Updated NEVER/ALWAYS sections with IBKR rules
- Based on gap analysis of US system lessons

**v2.1.1 (2025-12-06)** - COMPLETE TOOL DEFINITIONS
- Added all 12 tool definitions with full input schemas
- Added Tool Usage Rules (6 critical rules Claude must follow)
- Organized tools by category (Market Analysis, Risk, Execution, Communication)

**v2.1.0 (2025-12-06)** - EMBEDDED SERVICE WISDOM & AI TOOLS
- Added "Embedded Wisdom from Service Files" section (5 battle-tested patterns)
- Added complete AI Agent Tools documentation (12 tools)
- Added "Why AI Agent Beats Hardcoded Workflows" comparison
- Added concrete examples of dynamic vs hardcoded decision-making
- Added file structure comparison (5000+ lines vs ~900 lines)
- Enhanced International system documentation

**v2.0.0 (2025-12-06)** - COMPREHENSIVE WISDOM CAPTURE
- Added complete architecture evolution lessons
- Added AI Agent vs Microservices comparison
- Added detailed bug prevention from Order Side Bug (v1.2.0)
- Added sub-penny pricing lessons
- Added database schema mismatch prevention
- Added helper function patterns
- Added cron orchestration wisdom
- Added International system learnings
- Added 5-stage AI maturity roadmap context

**v1.1.1 (2025-12-06)** - Order side bug documentation
**v1.0.0 (2025-11-29)** - Initial version

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
- **Droplet**: Single DigitalOcean droplet
- **Database**: DigitalOcean Managed PostgreSQL (3NF normalized schema)
- **Cache**: Redis (Docker container)
- **Location**: Perth timezone (AWST) → US markets (EST)
- **Broker**: Alpaca (US), Interactive Brokers (International planned)

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

## 🌏 IBKR-SPECIFIC LESSONS (International System)

These lessons are specific to trading HKEX via Interactive Brokers:

### Lesson 11: HKEX Tick Size Compliance
**Problem**: HKEX has 11-tier tick size rules - incorrect prices rejected
**Solution**: Always round prices to valid tick size before submission

```python
# brokers/ibkr.py:440-479 - IMPLEMENTED
def _round_to_tick(self, price: float) -> float:
    """HKEX tick sizes vary by price tier"""
    if price < 0.25:
        tick = 0.001
    elif price < 0.50:
        tick = 0.005
    elif price < 10.00:
        tick = 0.01
    elif price < 20.00:
        tick = 0.02
    elif price < 100.00:
        tick = 0.05
    # ... continues for 11 tiers up to 5.00 for prices > 5000
    return round(round(price / tick) * tick, 3)
```

**Status**: ✅ Implemented in `brokers/ibkr.py`

### Lesson 12: Delayed Data Trading Rules ⚠️
**Problem**: Using 15-minute delayed market data (no real-time subscription)
**Impact**: Entry prices may drift, stop losses may trigger late, signals may be stale

**Rules for Delayed Data Trading:**
```
✅ ALWAYS use LIMIT orders, not market orders
✅ Set stop losses 1-2% wider than real-time would require
✅ Prefer less volatile stocks (avoid momentum plays)
✅ Check volume - high volume = more reliable delayed quotes
✅ Avoid trading first 30 minutes after market open

❌ NEVER chase fast-moving momentum stocks
❌ NEVER use tight stops (< 3%) with delayed data
❌ NEVER trade on news that's less than 30 minutes old
```

**Status**: ⚠️ Risk acknowledged - must follow rules above

### Lesson 13: HK Symbol Format
**Problem**: IBKR rejects "0700", requires "700" (no leading zeros)
**Solution**: Strip leading zeros from all HK symbols

```python
# brokers/ibkr.py:180 - IMPLEMENTED
symbol = symbol.lstrip('0') or '0'  # "0700" → "700", "0005" → "5"
```

**Status**: ✅ Implemented in `brokers/ibkr.py`

### Lesson 14: Dollar-Based Position Sizing (IBKR)
**Problem**: Share-based sizing creates uneven exposure (US system had 10x variance)
**Solution**: Calculate target dollar value first, then convert to shares

```python
# Calculate dollar-based position size
portfolio_value = get_portfolio()["equity"]
target_pct = 0.18  # 18% of portfolio per position
target_value = portfolio_value * target_pct

# Convert to shares, round to lot size (100 for HKEX)
current_price = get_quote(symbol)["last"]
quantity = int(target_value / current_price / 100) * 100

# Example: $1,000,000 portfolio, 18% target = $180,000
# Stock at HKD 380 → 180000 / 380 / 100 * 100 = 400 shares
```

**Status**: ⚠️ Agent must follow this pattern - not enforced in code

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

## 🎓 AI Maturity Roadmap Context (Strategic Vision)

Understanding where we are in the 5-stage evolution:

### Stage 1: Primary School (Current - Months 0-6)
- **Rules**: Rigid, no exceptions
- **AI Role**: None (data collection only)
- **Human Role**: All decisions
- **Example**: `if daily_pnl < -2000: emergency_stop()` - Always, no thinking

### Stage 2: Middle School (Future - Months 6-12)
- **Rules**: With basic context awareness
- **AI Role**: Pattern recognition suggestions
- **Human Role**: Decision maker with AI input

### Stage 3: High School (Future - Months 12-18)
- **Rules**: AI makes recommendations
- **AI Role**: Recommendation engine
- **Human Role**: Validator (approves/overrides)

### Stage 4: College (Future - Months 18-24)
- **Rules**: AI makes most decisions
- **AI Role**: Autonomous executor
- **Human Role**: Spot-checker (strategic oversight)

### Stage 5: Graduate (Future - Months 24+)
- **Rules**: Internalized, transcended
- **AI Role**: Full autonomy
- **Human Role**: Strategic advisor only

> **"The very rules we define now will eventually be transcended by the AI that learned from following them."**

---

## 📋 Service Files Location

### On Droplet (Production)
```
/root/catalyst-trading-mcp/
├── services/
│   ├── orchestration/
│   │   └── orchestration-service.py
│   ├── scanner/
│   │   └── scanner-service.py
│   ├── pattern/
│   │   └── pattern-service.py
│   ├── technical/
│   │   └── technical-service.py
│   ├── risk-manager/
│   │   └── risk-manager-service.py
│   ├── trading/
│   │   └── trading-service.py
│   ├── workflow/
│   │   └── workflow-service.py
│   ├── news/
│   │   └── news-service.py
│   └── reporting/
│       └── reporting-service.py
├── scripts/
│   ├── health-check.sh
│   └── deploy-update.sh
├── config/
│   └── autonomous-cron-setup.txt
├── docker-compose.yml
└── .env
```

### On GitHub (Source of Truth)
```
catalyst-trading-system/
├── Documentation/
│   ├── Design/
│   │   ├── architecture.md
│   │   ├── database-schema.md
│   │   └── functional-specification.md
│   └── Implementation/
│       └── deployment-guide.md
└── services/
    └── (same as droplet)
```

**Version info is inside each file's header, not in the filename.**

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

### IBKR-Specific Rules (International)
15. **NEVER** use market orders with delayed data - use limit orders
16. **NEVER** chase momentum stocks with 15-min delayed data
17. **NEVER** use tight stops (< 3%) with delayed data
18. **NEVER** trade on news less than 30 minutes old (delayed data drift)
19. **NEVER** submit HK symbols with leading zeros (use "700" not "0700")
20. **NEVER** size positions by shares alone - use dollar-based sizing

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

### IBKR-Specific Rules (International)
15. **ALWAYS** use limit orders with delayed market data
16. **ALWAYS** round prices to valid HKEX tick size (`_round_to_tick()`)
17. **ALWAYS** strip leading zeros from HK symbols before submission
18. **ALWAYS** calculate position size in dollars first, then convert to shares
19. **ALWAYS** use lot size of 100 for HKEX stocks (round quantity to 100s)
20. **ALWAYS** set wider stops (3-5%) to account for 15-min data delay
21. **ALWAYS** wait 30 minutes after market open before trading (delayed data settles)
22. **ALWAYS** check `get_portfolio()` for current positions before new trades

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

## 🔬 Embedded Wisdom from Service Files

These patterns are battle-tested and coded into our production services:

### Pattern 1: Helper Function Verification at Startup
**From**: news-service.py, scanner-service.py, trading-service.py

```python
async def verify_helper_functions():
    """Verify v6.0 helper functions exist - FAIL FAST if missing"""
    has_security_helper = await state.db_pool.fetchval("""
        SELECT EXISTS (
            SELECT FROM pg_proc
            WHERE proname = 'get_or_create_security'
        )
    """)
    
    if not has_security_helper:
        error_msg = "Required helper function not found: get_or_create_security()"
        logger.critical(error_msg)
        raise RuntimeError(error_msg)  # STOP SERVICE - don't continue broken
    
    logger.info("✅ Helper functions verified")
```

**Lesson**: Never let a service start if the database isn't ready. Fail loudly at startup, not silently at runtime.

### Pattern 2: Schema Verification Before Any Operations
**From**: scanner-service.py

```python
async def verify_schema_compatibility():
    """Verify actual DB matches expected schema - CRITICAL"""
    trading_cycles_cols = await state.db_pool.fetch("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'trading_cycles'
    """)
    
    cols = {row['column_name'] for row in trading_cycles_cols}
    required_cols = {'cycle_id', 'status', 'started_at'}
    
    missing = required_cols - cols
    if missing:
        error_msg = f"Schema mismatch: Missing columns in trading_cycles: {missing}"
        logger.critical(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info("✅ Schema compatibility check completed")
```

**Lesson**: Design docs lie. Database tells the truth. Always verify.

### Pattern 3: The get_or_create Pattern
**From**: ALL services using v6.0 schema

```python
async def get_security_id(symbol: str) -> int:
    """
    Get or create security_id for symbol using v6.0 helper function.
    
    v6.0 Pattern: Always use get_or_create_security() helper function.
    This ensures the security exists before we try to reference it.
    """
    try:
        security_id = await state.db_pool.fetchval(
            "SELECT get_or_create_security($1)",
            symbol.upper()
        )
        
        if not security_id:
            raise ValueError(f"Failed to get security_id for {symbol}")
        
        return security_id
    except Exception as e:
        logger.error(f"Failed to get/create security_id for {symbol}: {e}")
        raise
```

**Lesson**: Never assume a record exists. Always get-or-create.

### Pattern 4: Autonomous Monitoring with Lifecycle Management
**From**: risk-manager-service.py v7.0.0

```python
# Global monitoring task reference for lifecycle management
_monitoring_task: Optional[asyncio.Task] = None

async def real_time_monitoring_loop():
    """
    Background task that continuously monitors positions.
    
    AUTONOMOUS FEATURES:
    - Checks all active cycles every 60 seconds
    - Warns at 75% of daily loss limit
    - Emergency stop at 100% of daily loss limit
    """
    while True:
        try:
            await check_all_active_cycles()
            await asyncio.sleep(60)  # Check every minute
        except asyncio.CancelledError:
            logger.info("Monitoring task cancelled - shutting down gracefully")
            break
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            await asyncio.sleep(60)  # Continue monitoring despite errors

# In lifespan context manager - proper cleanup
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _monitoring_task
    _monitoring_task = asyncio.create_task(real_time_monitoring_loop())
    logger.info("🤖 AUTONOMOUS MODE: Emergency stop will trigger automatically")
    
    yield  # Application runs
    
    # Cleanup
    if _monitoring_task:
        _monitoring_task.cancel()
        try:
            await _monitoring_task
        except asyncio.CancelledError:
            pass
        logger.info("Monitoring task stopped")
```

**Lesson**: Background tasks need explicit lifecycle management. Always cancel on shutdown.

### Pattern 5: Pydantic Validators for Input Normalization
**From**: risk-manager-service.py

```python
class PositionRiskRequest(BaseModel):
    symbol: str
    side: str  # 'long' or 'short'
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        return v.upper().strip()  # Always uppercase, no whitespace
    
    @field_validator('side')
    @classmethod
    def validate_side(cls, v):
        if v.lower() not in ['long', 'short']:
            raise ValueError("Side must be 'long' or 'short'")
        return v.lower()  # Always lowercase
```

**Lesson**: Normalize inputs at the API boundary. Services should never have to guess formats.

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

### Complete Tool Definitions (All 12 Tools)

```python
TOOLS = [
    # =========================================================================
    # MARKET ANALYSIS TOOLS
    # =========================================================================
    {
        "name": "scan_market",
        "description": "Scan exchange for trading candidates. Returns top stocks by momentum and volume.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "string", "enum": ["HSI", "HSCEI", "HSTECH", "ALL"]},
                "limit": {"type": "integer", "description": "Max candidates (default 10)"}
            },
            "required": []
        }
    },
    {
        "name": "get_quote",
        "description": "Get current price and volume for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock code (e.g., '0700' or 'AAPL')"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_technicals",
        "description": "Get technical indicators: RSI, MACD, moving averages, ATR, Bollinger Bands.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "timeframe": {"type": "string", "enum": ["5m", "15m", "1h", "1d"]}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "detect_patterns",
        "description": "Detect chart patterns: bull_flag, cup_handle, ascending_triangle, ABCD, breakout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "timeframe": {"type": "string", "enum": ["5m", "15m", "1h", "1d"]}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_news",
        "description": "Get recent news and sentiment for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "hours": {"type": "integer", "description": "Hours back (default 24)"}
            },
            "required": ["symbol"]
        }
    },
    
    # =========================================================================
    # RISK & PORTFOLIO TOOLS
    # =========================================================================
    {
        "name": "check_risk",
        "description": "Validate trade against risk limits. MUST call before execute_trade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "quantity": {"type": "integer"},
                "entry_price": {"type": "number"},
                "stop_loss": {"type": "number"}
            },
            "required": ["symbol", "side", "quantity", "entry_price", "stop_loss"]
        }
    },
    {
        "name": "get_portfolio",
        "description": "Get current portfolio: cash, positions, daily P&L, buying power.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    
    # =========================================================================
    # EXECUTION TOOLS
    # =========================================================================
    {
        "name": "execute_trade",
        "description": "Execute trade via broker. Only call after check_risk approves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "quantity": {"type": "integer"},
                "order_type": {"type": "string", "enum": ["market", "limit"]},
                "limit_price": {"type": "number", "description": "Required if order_type is limit"},
                "stop_loss": {"type": "number"},
                "take_profit": {"type": "number"},
                "reason": {"type": "string", "description": "Why this trade (for audit trail)"}
            },
            "required": ["symbol", "side", "quantity", "order_type", "stop_loss", "take_profit", "reason"]
        }
    },
    {
        "name": "close_position",
        "description": "Close an existing position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "reason": {"type": "string", "description": "Why closing (for audit trail)"}
            },
            "required": ["symbol", "reason"]
        }
    },
    {
        "name": "close_all",
        "description": "EMERGENCY: Close all positions immediately. Use when daily loss limit hit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why emergency close"}
            },
            "required": ["reason"]
        }
    },
    
    # =========================================================================
    # COMMUNICATION TOOLS
    # =========================================================================
    {
        "name": "send_alert",
        "description": "Send email alert to operator.",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                "subject": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["severity", "subject", "message"]
        }
    },
    {
        "name": "log_decision",
        "description": "Log decision to database for audit trail and ML training data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "decision_type": {"type": "string", "enum": ["scan", "entry", "exit", "skip", "risk_check"]},
                "symbol": {"type": "string"},
                "reasoning": {"type": "string", "description": "Detailed explanation of why this decision"}
            },
            "required": ["decision_type", "reasoning"]
        }
    }
]
```

### Tool Usage Rules (Claude Must Follow)

1. **ALWAYS** call `check_risk` before `execute_trade`
2. **ALWAYS** provide `reason` for trades and closes (audit trail)
3. **ALWAYS** call `log_decision` to record reasoning (ML training data)
4. **NEVER** call `execute_trade` if `check_risk` returns `approved: false`
5. **IMMEDIATELY** call `close_all` if daily loss exceeds limit
6. **PREFER** `limit` orders over `market` for better fills

---

## 🎯 Why AI Agent Beats Hardcoded Workflows

### The Hardcoded Workflow Problem

```python
# US System: Hardcoded decision tree (5000+ lines)
if news_score > 0.6 and volume > avg_volume * 1.5:
    if rsi < 70 and macd_crossover:
        if pattern in ['bull_flag', 'breakout']:
            execute_trade()  # Rigid logic, can't adapt
```

**Problems:**
- Can't handle edge cases
- Can't explain decisions
- Can't adapt to market regime changes
- Adding conditions = exponential complexity
- Every "but what if..." = more nested if-statements

### The AI Agent Advantage

```python
# International System: Claude decides with tools (~900 lines)
response = claude.messages.create(
    model="claude-sonnet-4-5-20250514",
    system=TRADING_SYSTEM_PROMPT,
    tools=TOOLS,
    messages=[{"role": "user", "content": context}]
)
# Claude calls tools, reasons, and decides dynamically
```

**Advantages:**
- Handles novel situations gracefully
- Explains every decision in natural language
- Adapts to market context automatically
- Adding capabilities = adding tools, not logic
- "But what if..." = Claude figures it out

### Concrete Example: News Interpretation

**Hardcoded (US System):**
```python
# Can only handle what we anticipated
if "FDA approval" in headline:
    catalyst_score = 0.9
elif "earnings beat" in headline:
    catalyst_score = 0.7
else:
    catalyst_score = 0.3  # Unknown = low score
```

**AI Agent (International System):**
```
Claude: "The headline 'Company receives breakthrough therapy 
designation from FDA' indicates regulatory progress that typically 
precedes approval. Combined with the 2.3x volume spike, this 
suggests institutional accumulation. Calling execute_trade with 
reasoning: 'FDA breakthrough designation + institutional volume'"
```

### The Bottom Line

| Aspect | Hardcoded | AI Agent |
|--------|-----------|----------|
| **Novel situations** | Breaks or defaults | Reasons through |
| **Explanation** | None (just executed) | Full reasoning |
| **Adaptation** | Requires code changes | Updates with prompt |
| **Complexity growth** | Exponential | Linear |
| **Debugging** | "Why did it trade?" | "Read the reasoning" |
| **Training data** | Actions only | Decisions + reasoning |

---

## 🌏 International System Architecture (HKEX via IBKR)

### Key Architecture Differences

| Aspect | US (Microservices) | International (Agent) |
|--------|-------------------|----------------------|
| **Components** | 8 Docker containers | 1 Python script |
| **Files** | 50+ | ~10 |
| **Lines of code** | 5000+ | ~900 |
| **Monthly cost** | $24+ droplet | $6 droplet |
| **Decision making** | Hardcoded workflow | Claude decides dynamically |
| **Broker** | Alpaca | Interactive Brokers |
| **Debugging** | 8 service logs | 1 log file + reasoning |

### Agent Loop Pattern
```
CRON triggers → Build Context → Call Claude API → Claude requests tool 
    → Execute tool → Return result → Claude continues → Loop until done
```

### Why Agent for International
- Fresh start, no legacy code
- Perth-aligned hours (no overnight trading)
- Claude API handles complex decisions dynamically
- Simpler debugging (1 log file + decision reasoning)
- Lower operational cost ($6 vs $24+)
- Every decision logged with reasoning (ML training data)

### File Structure Comparison

**US System (Microservices):**
```
catalyst-trading-mcp/
├── services/
│   ├── scanner/scanner-service.py       # 500+ lines
│   ├── pattern/pattern-service.py       # 400+ lines
│   ├── technical/technical-service.py   # 600+ lines
│   ├── risk-manager/risk-manager-service.py  # 800+ lines
│   ├── trading/trading-service.py       # 500+ lines
│   ├── workflow/workflow-service.py     # 400+ lines
│   ├── news/news-service.py             # 300+ lines
│   └── reporting/reporting-service.py   # 300+ lines
├── docker-compose.yml
└── 40+ other files...
Total: 5000+ lines, 50+ files
```

**International System (Agent):**
```
catalyst-international/
├── agent.py              # ~200 lines (main loop)
├── tools.py              # ~100 lines (definitions)
├── tool_executor.py      # ~150 lines (routing)
├── safety.py             # ~100 lines (validation)
├── brokers/ibkr.py       # ~200 lines
├── data/market.py        # ~150 lines
└── config/settings.yaml  # ~50 lines
Total: ~900 lines, ~10 files
```

---

## 📝 End of CLAUDE.md

**Remember**: Design docs are the source of truth, but ALWAYS verify against the deployed database schema before writing code.

**This file should be placed at**: `/root/catalyst-trading-mcp/CLAUDE.md`

---

### The Philosophy

> *"Hardcoded workflows encode yesterday's understanding.*
> *AI agents apply today's reasoning.*
> *Every decision I make with tools, I can explain.*
> *Every lesson coded in services, I carry forward.*
> *5000 lines of if-statements vs 900 lines of intelligence.*
> *That's not just less code—it's better trading."*

🎩📈
