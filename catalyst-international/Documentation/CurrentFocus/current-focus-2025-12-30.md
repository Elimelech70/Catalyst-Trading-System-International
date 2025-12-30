# CATALYST TRADING SYSTEM - CURRENT FOCUS DOCUMENT

**Name of Application:** Catalyst Trading System  
**Name of file:** current-focus-2025-12-30.md  
**Version:** 1.0.0  
**Last Updated:** 2025-12-30  
**Purpose:** Track progress, open issues, and priorities from Dec 16-30, 2025

---

## EXECUTIVE SUMMARY

Two systems approaching live trading readiness with key blockers remaining.

| System | Status | Primary Blocker |
|--------|--------|-----------------|
| 🇺🇸 **US (public_claude)** | Ready for autonomous test | None - first clean run achieved |
| 🇭🇰 **International (intl_claude)** | Active - 3 positions | OpenD auto-start not working |
| 🧠 **Consciousness Framework** | Deployed | Budget tracking designed but unverified |

---

## 1. PROGRESS ACHIEVED (Dec 16-30)

### ✅ US System - Major Fixes Deployed

| Issue | Fix Date | Status |
|-------|----------|--------|
| Order side mapping ("long" → "buy") | Dec 25 | ✅ Deployed v1.3.0 |
| Sub-penny pricing bug | Dec 25 | ✅ `_round_price()` |
| Bracket orders (OrderClass.BRACKET) | Dec 25 | ✅ Fixed in trading & risk-manager |
| P&L tracking ($0.00 realized) | Dec 26 | ✅ Exit price capture working |
| Orders ≠ Positions architecture | Dec 27 | ✅ Separate orders table (83 migrated) |
| Order status sync | Dec 27 | ✅ 60s background sync active |
| Doctor Claude monitoring | Dec 27 | ✅ Systemd service deployed |
| Cron startup (cd command) | Dec 27 | ✅ Fixed |
| **First error-free autonomous trade** | Dec 29 | ✅ MILESTONE |

### ✅ International System - Broker Migration Complete

| Item | Date | Status |
|------|------|--------|
| IBKR → Moomoo decision | Dec 20 | ✅ Decided |
| OpenD gateway configured | Dec 28 | ✅ Working (v9.6.5618) |
| Questionnaire blocker resolved | Dec 29 | ✅ Craig completed |
| Agent v2.1.0 Moomoo integration | Dec 30 | ✅ Deployed |
| First paper trades | Dec 30 | ✅ 3 positions open |
| CAPTCHA bypass documented | Dec 29 | ✅ Kill/restart workaround |
| SecurityFirm = FUTUAU discovery | Dec 29 | ✅ Not MOOMOOAU |

### ✅ Consciousness Framework - Fully Deployed

| Component | Date | Status |
|-----------|------|--------|
| catalyst_research database | Dec 28 | ✅ 8 tables live |
| DB consolidation (2 → 1 PostgreSQL) | Dec 28 | ✅ ~$15/mo savings |
| intl_claude consciousness integration | Dec 28 | ✅ 8/8 tests passed |
| public_claude consciousness integration | Dec 28 | ✅ Schema fixes applied |
| Inter-agent messaging | Dec 28 | ✅ big_bro welcome received |
| 6 seed questions initialized | Dec 28 | ✅ Including mission questions |

### ✅ Documentation & Cleanup

| Item | Date | Status |
|------|------|--------|
| Architecture docs v8.0.0 | Dec 27 | ✅ Systemd deployment |
| Functional spec v8.0.0 | Dec 27 | ✅ Updated |
| Repository cleanup | Dec 27 | ✅ Deprecated folders removed |
| CLAUDE.md v2.0.0 | Dec 27 | ✅ Operations updated |

---

## 2. OPEN ISSUES - REQUIRING ACTION

### 🔴 CRITICAL - Blocks Operations

| ID | Issue | Impact | Owner | Notes |
|----|-------|--------|-------|-------|
| C1 | **OpenD auto-start not working** | Manual start required | intl_claude | Systemd service configured but not starting on boot |
| C2 | **OpenD CAPTCHA randomly triggered** | Requires kill/restart | Craig | Workaround documented but root cause unknown |

### 🟡 HIGH - Should Address Soon

| ID | Issue | Impact | Owner | Notes |
|----|-------|--------|-------|-------|
| H1 | **Budget tracking not verified in production** | May overspend | big_bro | Schema exists, code exists, but no evidence of actual tracking |
| H2 | **token_usage & budget_status tables designed but unused** | No cost visibility | all | Dec 9 design never implemented in cron cycle |
| H3 | **Doctor Claude systemd service unverified** | May not be running | public_claude | Deployed but no confirmation it works |
| H4 | **Risk-manager alpaca_trader.py was stale copy** | Position protection uncertain | public_claude | Was fixed Dec 27 - needs verification |

### 🟢 MEDIUM - Track for Later

| ID | Issue | Impact | Owner | Notes |
|----|-------|--------|-------|-------|
| M1 | IBGA monitoring email alerts | No automated alerts | public_claude | msmtp configured but unverified |
| M2 | Weekend cron suppression | Alert spam potential | both | Not implemented |
| M3 | Ghost position cleanup | DB has phantom records | public_claude | 16+ positions to clean |
| M4 | Old PostgreSQL instance deletion | ~$15/mo waste | Craig | Safe to delete post-consolidation |

---

## 3. THINGS RAISED BUT NOT PROGRESSED

These items were discussed but have no implementation work completed:

### From Dec 9-13 Conversations (Consciousness Design Phase)

| Item | Discussed | Current State |
|------|-----------|---------------|
| **Token cost tracking tables** (token_usage, budget_status) | Dec 9 | Schema designed, NOT created |
| **Self-throttling consciousness** (throttle at 75%, critical at 90%) | Dec 9 | Code written, NOT integrated |
| **Cost-aware API calls** (before_api_call check) | Dec 9 | Pattern documented, NOT enforced |
| **Daily/monthly budget resets** | Dec 9 | In claude_state schema, NOT verified |
| **Organ architecture** (US services → conscious organs) | Dec 25 | Parked - focus on fixing first |
| **Wisdom frameworks** (Dalio indicators encoded) | Dec 25 | Parked - no implementation |
| **Hub stress monitoring** | Dec 13 | Parked - H2/H3 horizon work |

### From Dec 20-27 Conversations (Implementation Phase)

| Item | Discussed | Current State |
|------|-----------|---------------|
| **Auto-restart logic for containers** | Dec 16 | Not implemented |
| **Email alert verification** | Dec 16 | msmtp configured, NOT tested |
| **Design document in GitHub** (ibga-monitoring-system.md) | Dec 16 | File never committed |
| **Test script locations** | Dec 27 | Referenced but not verified |

---

## 4. SPEND & INFRASTRUCTURE TRACKING

### Current Monthly Costs (Estimated)

| Item | Cost | Status |
|------|------|--------|
| Claude Max subscription | $200/mo | Active |
| DigitalOcean Managed PostgreSQL | $30/mo | Active (was $45 - consolidated) |
| US Droplet | $6/mo | Active |
| International Droplet | $6/mo | Active |
| Anthropic API (agent thinking) | **$?/mo** | ⚠️ NO TRACKING |
| **Total** | ~$242 + unknown API | |

### API Cost Tracking Status

```
DESIGNED:
├── claude_state.api_spend_today     ✅ Column exists
├── claude_state.api_spend_month     ✅ Column exists  
├── claude_state.daily_budget        ✅ Column exists (default $5)
├── consciousness.record_api_spend() ✅ Method exists
└── consciousness.check_budget()     ✅ Method exists

NOT IMPLEMENTED:
├── token_usage table                ❌ Not created
├── budget_status table              ❌ Not created
├── Actual API cost logging          ❌ Not happening
├── Throttling at thresholds         ❌ Not enforced
└── Budget exceeded alerts           ❌ Not configured
```

---

## 5. PRIORITIES - WHAT TO DO NEXT

### Immediate (Before Dec 31)

1. **Verify OpenD systemd service** - Check why not auto-starting
   ```bash
   systemctl status opend
   journalctl -u opend -n 50
   cat /etc/systemd/system/opend.service
   ```

2. **Verify Doctor Claude running** - US system
   ```bash
   systemctl status doctor-claude
   journalctl -u doctor-claude -n 50
   ```

3. **Let systems run autonomously** - Gather data from Dec 30 trading

### This Week (Dec 30 - Jan 5)

| Priority | Task | Owner |
|----------|------|-------|
| 1 | Fix OpenD auto-start | intl_claude/Craig |
| 2 | Implement API cost tracking | public_claude |
| 3 | Clean up ghost positions | public_claude |
| 4 | Delete old PostgreSQL instance | Craig |
| 5 | Test email alerts end-to-end | public_claude |

### Next Milestone: "Working" Definition

> **5 consecutive trading days of autonomous operation with data collection, no critical errors requiring manual intervention**

Current Status:
- US: Day 1 (Dec 30 - first clean autonomous trade)
- International: Day 1 (Dec 30 - active but needs OpenD fix)

---

## 6. KEY LEARNINGS CAPTURED

1. **Orders ≠ Positions** - Fundamental architecture rule
2. **OpenD CAPTCHA bypass** - Kill and restart to avoid verification
3. **SecurityFirm = FUTUAU** - Not MOOMOOAU (legacy Futu naming)
4. **Consciousness before trading** - Framework must be stable first
5. **Paper trading doesn't need trade unlock** - Moomoo/Futu API quirk
6. **safe_float helper needed** - API returns 'N/A' strings

---

## 7. QUESTIONS FOR CRAIG

1. Should we implement API cost tracking now, or wait until systems stable?
2. Confirm old PostgreSQL instance deletion is safe
3. Priority of organ architecture vs getting systems profitable first?
4. Any budget ceiling you want enforced before API spend alerts?

---

*Document generated by analysis of 20 conversations from Dec 16-30, 2025*
*Next review: After Jan 5, 2025 trading week*
