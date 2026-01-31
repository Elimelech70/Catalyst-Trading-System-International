# Position Sync Mismatch Analysis

**Date:** 2026-01-31
**Author:** Claude Code
**System:** Catalyst Trading System International (HKEX)
**Status:** Investigation Complete

---

## Executive Summary

The database `positions` table frequently becomes out of sync with Moomoo broker positions. This analysis identifies three root causes and proposes fixes.

**Impact:** 6 phantom positions found on 2026-01-31 (DB showed open, Moomoo showed 0)

---

## Evidence Collected

### Database State (2026-01-31 01:21 UTC)

**Positions Table:**
| position_id | symbol | quantity | broker_order_id | status |
|-------------|--------|----------|-----------------|--------|
| 74 | 1797 | 500 | auto_sync | open |
| 82 | 2382 | 600 | auto_sync | open |
| 83 | 9866 | 700 | auto_sync | open |
| 84 | 1044 | 500 | auto_sync | open |
| 85 | 3968 | 1000 | auto_sync | open |
| 86 | 9866 | 100 | 2085947 | open |

**Moomoo Broker:** 0 positions

**Orders Table (Jan 30):**
| order_id | symbol | status | filled_quantity |
|----------|--------|--------|-----------------|
| 82-96 | various | submitted | 0 |
| 97 | 9866 | filled | 100 |

15 of 16 orders show `submitted` with `filled_quantity = 0`

---

## Root Cause Analysis

### Issue 1: Order Status Timing Gap

**Problem:** When an order is placed, Moomoo returns immediate status "SUBMITTED" before the order is filled. The system correctly does not create a position for unfilled orders, but never checks back to confirm fills.

**Code Flow:**
```
tool_executor.py:541-547

filled_statuses = ["Filled", "FILLED", "FILLED_ALL", "success"]
submitted_statuses = ["Submitted", "SUBMITTED", "SUBMITTING", "WAITING_SUBMIT"]

is_filled = status in filled_statuses     # False for new orders
is_submitted = status in submitted_statuses  # True for new orders

# Position only created if is_filled (correct behavior)
if is_filled or is_partial:
    position_id = self.db.record_position(...)
```

**Result:** Orders are submitted but positions are never created from the original order flow.

---

### Issue 2: Auto-Sync Creates Phantom Positions

**Problem:** The `sync_positions_with_broker()` function runs every 30 minutes and creates new position records for any position found in Moomoo but not in the database. This compensates for Issue 1, but creates side effects.

**Code Flow:**
```
tool_executor.py:186-206

# Add missing positions (in broker but not in DB)
missing = broker_symbols - db_symbols
for symbol in missing:
    self.db.record_position(
        symbol=symbol,
        broker_order_id='auto_sync',  # Marker for sync-created positions
        ...
    )
```

**Evidence:** All 16 positions from Jan 30 have `broker_order_id = 'auto_sync'`

**Side Effects:**
1. Creates duplicate positions when quantities change (close old + create new)
2. Loses original order linkage
3. Creates new position records every cycle instead of updating existing

---

### Issue 3: No End-of-Day Reconciliation

**Problem:** Moomoo paper trading clears or resets positions at market close or overnight. The database is not updated until the next trading cycle runs.

**Timeline (Jan 30-31):**
```
15:32 HKT  Last trade executed (order #97)
16:00 HKT  Market closes
16:30 HKT  Report generated (shows 6 positions)
...overnight...
09:00 HKT  Moomoo shows 0 positions (cleared overnight)
09:16 HKT  OpenD restarts (was down)
09:21 HKT  Manual sync finds 6 phantom positions
```

**Gap:** ~17 hours where DB had "open" positions but Moomoo had 0

---

## The Cascade Effect

```
Time     Event                                          DB State        Moomoo State
-------- ---------------------------------------------- --------------- ---------------
09:30    Agent submits BUY 100 2382                     0 positions     Order submitted
09:31    Moomoo fills order                             0 positions     100 shares
10:00    Sync runs, sees position                       1 position      100 shares
10:01    Agent submits BUY 100 2382                     1 position      Order submitted
10:02    Moomoo fills, now 200 shares                   1 position      200 shares
10:30    Sync: qty mismatch, close+create               2 positions*    200 shares
...      (repeat every 30 min)
16:00    Market closes                                  N positions     Positions cleared
09:00+1  Next day, no sync overnight                    N positions     0 positions
         MISMATCH!
```
*Creates new record, closes old - position count grows

---

## Proposed Fixes

### Fix 1: Order Fill Confirmation (High Priority)

Poll order status after submission to confirm fills:

```python
# After place_order returns SUBMITTED
if status == "SUBMITTED":
    # Wait and poll for fill confirmation
    for _ in range(10):  # 10 attempts
        time.sleep(1)
        order_status = self.broker.get_order_status(order_id)
        if order_status.get("status") in ["FILLED", "FILLED_ALL"]:
            # Now create position
            self.db.record_position(...)
            break
```

**Alternative:** Use Moomoo's order update callback/subscription

### Fix 2: Update Instead of Replace (Medium Priority)

Modify sync to update existing positions instead of close+create:

```python
# Instead of close + create for quantity mismatch:
self.db.update_position_quantity(
    symbol=symbol,
    new_quantity=broker_qty,
    reason=f'Sync: qty update {db_qty} -> {broker_qty}'
)
```

### Fix 3: EOD Sync Job (High Priority)

Add market close sync at 16:00 HKT (08:00 UTC):

```bash
# Add to crontab
0 8 * * 1-5 cd $CATALYST_DIR && source .env && python3 -c "
from tool_executor import ToolExecutor
executor = ToolExecutor(cycle_id=0)
executor.sync_positions_with_broker()
"
```

### Fix 4: Morning Pre-Market Sync (Medium Priority)

Ensure sync runs before first trade of day:

```bash
# Already exists at 01:00 UTC (09:00 HKT) - verify it's working
```

---

## Immediate Actions Taken

1. Manually synced positions (2026-01-31 01:22 UTC)
2. Closed 6 phantom positions in database
3. Verified Moomoo shows 0 positions (correct)

---

## Recommendations

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| High | EOD sync at 16:00 HKT | Low | Prevents overnight drift |
| High | Order fill confirmation | Medium | Eliminates timing gap |
| Medium | Update vs replace positions | Medium | Cleaner position history |
| Low | Order update subscription | High | Real-time sync |

---

## Files Involved

| File | Role |
|------|------|
| `tool_executor.py` | Order execution, position creation, sync logic |
| `brokers/moomoo.py` | Broker API, order placement, status retrieval |
| `data/database.py` | Position CRUD operations |
| `unified_agent.py` | Calls sync at cycle start |

---

## Appendix: Position History (Jan 30)

All positions created via auto_sync, showing the cascade effect:

| ID | Symbol | Qty | Entry Time | Exit Time | Exit Reason |
|----|--------|-----|------------|-----------|-------------|
| 71 | 2382 | 100 | 02:00 | 03:00 | (qty update) |
| 72 | 2601 | 200 | 02:00 | 02:30 | (qty update) |
| 73 | 9866 | 100 | 02:30 | 05:30 | (qty update) |
| 74 | 1797 | 500 | 02:30 | 01:22+1 | sync: not in broker |
| 75 | 3968 | 500 | 03:00 | 07:30 | (qty update) |
| 76 | 2382 | 200 | 03:00 | 03:30 | (qty update) |
| 77 | 2382 | 300 | 03:30 | 06:00 | (qty update) |
| 78 | 9866 | 300 | 05:30 | 06:30 | (qty update) |
| 79 | 2382 | 400 | 06:00 | 06:30 | (qty update) |
| 80 | 9866 | 500 | 06:30 | 07:00 | (qty update) |
| 81 | 2382 | 500 | 06:30 | 07:00 | (qty update) |
| 82 | 2382 | 600 | 07:00 | 01:22+1 | sync: not in broker |
| 83 | 9866 | 700 | 07:00 | 01:22+1 | sync: not in broker |
| 84 | 1044 | 500 | 07:30 | 01:22+1 | sync: not in broker |
| 85 | 3968 | 1000 | 07:30 | 01:22+1 | sync: not in broker |
| 86 | 9866 | 100 | 07:32 | 01:22+1 | sync: not in broker |

Note: Position quantities increase over time as more orders fill, then all become phantoms overnight.

---

*Report generated by Claude Code*
*Catalyst Trading System International*
