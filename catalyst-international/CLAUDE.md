# CLAUDE.md - Catalyst Trading System International

**Name of Application**: Catalyst Trading System  
**Name of file**: CLAUDE.md  
**Version**: 3.2.0  
**Last Updated**: 2026-01-06  
**Purpose**: Complete operational guidelines for Claude Code on HKEX production system

---

## REVISION HISTORY

**v3.2.0 (2026-01-06)** - FIRST TRADE MILESTONE
- First autonomous trade executed (BUY 1024 Kuaishou)
- Added patterns.py v1.1.0 pattern types
- Documented bug fixes from today
- Updated file versions table
- Added close position testing instructions

**v3.1.0 (2025-12-31)** - STREAMLINED
- Migrated lessons to database
- Removed verbose code examples

**v3.0.0 (2025-12-20)** - BROKER MIGRATION
- IBKR → Moomoo/Futu OpenD

---

## ⚠️ CRITICAL: READ BEFORE ANY ACTION

### The Three Questions You MUST Ask First

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

---

## 📁 Source of Truth: GitHub Design Documents

### Key Design Documents

| Document | Version | Purpose |
|----------|---------|---------|
| `architecture-international.md` | 5.2.0 | System architecture |
| `database-schema.md` | 8.0.0 | Database schema |
| `functional-specification.md` | 8.0.0 | Tool specifications |

---

## 🏗️ System Architecture

### Current File Versions

| File | Version | Last Updated | Purpose |
|------|---------|--------------|---------|
| `agent.py` | 2.2.0 | 2026-01-02 | Main agent with tiered criteria |
| `tool_executor.py` | 2.2.1 | 2026-01-06 | Tool routing (bug fixes) |
| `brokers/moomoo.py` | 1.2.1 | 2026-01-06 | Moomoo client (portfolio fixes) |
| `data/patterns.py` | 1.1.0 | 2026-01-06 | Relaxed pattern detection |
| `data/market.py` | 2.1.1 | 2026-01-06 | Quote field fixes |
| `data/news.py` | 1.0.0 | 2025-12-06 | News and sentiment |

### Pattern Types (v1.1.0)

| Pattern | Description | Use Case |
|---------|-------------|----------|
| `breakout` | Above resistance + volume | Tier 1/2 |
| `near_breakout` | Within 1% of resistance | Tier 2/3 |
| `momentum_continuation` | >3% daily + high volume | Tier 3 |
| `bull_flag` | Uptrend + consolidation | Tier 1/2 |
| `ascending_triangle` | Flat resistance, rising lows | Tier 1/2 |

### Entry Criteria (Tiered System)

**Tier 1 - Strong (Full Size)**: Volume >2x, RSI 30-70, Pattern AND Catalyst, R:R ≥2:1

**Tier 2 - Good (Full Size)**: Volume >1.5x, RSI 30-75, Pattern OR Catalyst, R:R ≥1.5:1

**Tier 3 - Learning (Half Size)**: Volume >1.3x, RSI 25-80, Momentum >3%, Any signal

---

## 🔧 Common Operations

### Check Portfolio
```python
from brokers.moomoo import MoomooClient
client = MoomooClient(paper_trading=True)
client.connect()
print(client.get_portfolio())
for p in client.get_positions():
    print(f"{p.symbol}: {p.quantity} @ {p.avg_cost:.2f}, P&L: {p.unrealized_pnl:.2f}")
client.disconnect()
```

### Close Position
```python
result = client.close_position("1024", reason="Taking profit")
print(result)
```

### Manual Agent Run
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
python3 agent.py --force
```

### Check Logs
```bash
tail -f logs/agent.log
tail -f /var/log/catalyst-intl.log
```

---

## 🐛 Known Issues & Fixes

### Bug Fixes Applied (2026-01-06)

| Component | Bug | Fix |
|-----------|-----|-----|
| tool_executor.py | OrderResult not subscriptable | Use `.status` not `["status"]` |
| tool_executor.py | has_position missing | Use `get_positions()` instead |
| tool_executor.py | AlertSender not callable | Check for `.send()` method |
| moomoo.py | Portfolio missing fields | Add positions, equity, position_count |
| market.py | Quote field mismatch | Map last_price → last |

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `MoomooClient not initialized` | OpenD not running | `systemctl start opend` |
| `Rate limit exceeded` | Too many API calls | Use batch APIs, add delays |
| `No position found` | Symbol format mismatch | Check .HK suffix handling |

---

## 📊 Current Portfolio Status

As of 2026-01-06:

| Symbol | Stock | Shares | P&L |
|--------|-------|--------|-----|
| 981 | SMIC | 2,500 | +$16,000 |
| 2382 | Sunny Optical | 2,700 | +$4,725 |
| 1810 | Xiaomi | 4,600 | $0 |
| 1024 | Kuaishou | 2,000 | -$100 |

**Total Unrealized P&L: +HKD 20,625**

---

## 🔗 Related Resources

- **Moomoo API Docs**: https://openapi.moomoo.com/moomoo-api-doc/en/intro/intro.html
- **OpenD Download**: https://www.moomoo.com/download/OpenAPI
- **HKEX Hours**: Morning 09:30-12:00, Afternoon 13:00-16:00 HKT

---

**END OF CLAUDE.md v3.2.0**
