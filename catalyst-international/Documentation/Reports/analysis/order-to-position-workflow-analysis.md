# Order-to-Position Workflow Analysis

**Date:** 2026-02-03
**Status:** CRITICALLY FLAWED
**Author:** Claude Code Analysis

---

## Executive Summary

The current order-to-position workflow is fundamentally broken. Today's sync found **6 phantom positions** in the database that don't exist in the broker, and **1 real position** (2269) that was missing from the database entirely. This indicates a systemic failure in the fill confirmation and position recording pipeline.

---

## Current Workflow (As Implemented)

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORDER EXECUTION FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

1. Claude AI calls execute_trade tool
         │
         ▼
2. tool_executor.py._execute_trade() receives the call
         │
         ├── Validates position size (HKD 10,000 max)
         ├── Auto-adjusts quantity if needed
         │
         ▼
3. broker.execute_trade() submits order to Moomoo
         │
         ▼
4. Moomoo returns OrderResult with status
         │
         ├── "SUBMITTED" - Order sent, NOT yet filled
         ├── "FILLED" - Order fully filled
         ├── "FILLED_PART" - Partially filled
         │
         ▼
5. IF status == "SUBMITTED":
         │
         ├── Poll order status for 5 seconds (5 attempts)
         │         │
         │         ├── Check every 1 second
         │         ├── If status becomes "FILLED" → proceed to record
         │         ├── If status stays "SUBMITTED" after 5s → LOG WARNING
         │         │         │
         │         │         └── "Will rely on auto-sync" ← THIS IS THE PROBLEM
         │
         ▼
6. IF filled (or partial):
         │
         ├── db.record_position() → Creates entry in positions table
         ├── db.record_order() → Creates entry in orders table
         │
         ▼
7. Return success to Claude

┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTO-SYNC FLOW (Start of Cycle)                     │
└─────────────────────────────────────────────────────────────────────────────┘

1. unified_agent.py calls executor.sync_positions_with_broker()
         │
         ▼
2. Get broker positions from Moomoo
         │
         ▼
3. Get DB positions (status='open')
         │
         ▼
4. Compare:
         │
         ├── Phantoms (in DB, not broker) → Close in DB
         ├── Missing (in broker, not DB) → Add to DB
         ├── Mismatches (qty differs) → Update DB quantity
```

---

## Identified Flaws

### Flaw #1: Position Created Before Fill Confirmed

**Location:** `tool_executor.py:579-601`

```python
if is_filled or is_partial or is_submitted:
    # ...
    if is_filled or is_partial:
        try:
            position_id = self.db.record_position(...)  # <-- ONLY IF FILLED
```

**Problem:** The code correctly only records positions when `is_filled` or `is_partial`, but there's a race condition. If the 5-second polling doesn't catch the fill, the position is never recorded even though the order may fill moments later.

**Evidence:** Position 2269 was filled in broker but never recorded in DB.

---

### Flaw #2: Polling Window Too Short

**Location:** `tool_executor.py:550-577`

```python
for attempt in range(5):  # Poll up to 5 times (5 seconds total)
    time.sleep(1)
    # ... check order status
```

**Problem:** Paper trading orders can take longer than 5 seconds to fill, especially during volatile periods or API delays. After 5 seconds, the system gives up and logs a warning.

**Reality:** Moomoo paper trading can take 10-30+ seconds to confirm fills.

---

### Flaw #3: Silent Failure Mode

**Location:** `tool_executor.py:576-577`

```python
if is_submitted:
    logger.warning(f"Order {order_id} still not filled after 5s - will rely on auto-sync")
```

**Problem:** The system assumes `auto-sync` will catch missed positions, but:
1. Auto-sync only runs at the START of each trading cycle
2. If no cycle runs before the order fills, position is orphaned
3. If multiple orders fail, they all become orphans

---

### Flaw #4: Phantom Positions from Order Status Misinterpretation

**Location:** `tool_executor.py:579`

```python
if is_filled or is_partial or is_submitted:
```

**Analysis of Today's Phantoms:**

| Symbol | DB Qty | Broker Qty | What Happened |
|--------|--------|------------|---------------|
| 6690   | 400    | 0          | Order cancelled/rejected after DB record |
| 9698   | 600 x3 | 0          | Multiple failed entries recorded |
| 1093   | 1000   | 0          | Order never actually filled |
| 1929   | 600    | 0          | Order never actually filled |

**Root Cause:** The code was recording positions BEFORE confirming fill in earlier versions. Even in v3.0.0, there may be edge cases where `is_submitted` gets recorded.

---

### Flaw #5: Auto-Sync Runs Too Infrequently

**Location:** `unified_agent.py:584-589`

```python
# Auto-sync positions with broker at start of cycle
try:
    sync_result = executor.sync_positions_with_broker()
```

**Problem:** Sync only runs when a new trade cycle starts (every 30 minutes). Positions can be out of sync for the entire period between cycles.

---

### Flaw #6: No Fill Callback/Push Notification

**Current Design:** The system uses polling to check order status.

**Better Design:** Moomoo API supports push notifications for order updates:
- `on_recv_rsp` callback for trade context
- Real-time fill notifications

**Impact:** Polling is unreliable and creates race conditions.

---

### Flaw #7: Symbol Format Inconsistency

**Location:** Multiple files

The system uses inconsistent symbol formats:
- Broker returns: `2269` (stripped leading zeros)
- Some DB records have: `02269`
- Some code expects: `HK.02269`

This can cause `get_positions()` to miss matches during sync.

---

## Evidence from Today (2026-02-03)

### Before Sync
```
DATABASE POSITIONS (6 open):
  ID:97  | 6690: 400 shares   | NOT IN BROKER
  ID:95  | 9698: 600 shares   | NOT IN BROKER
  ID:96  | 9698: 600 shares   | NOT IN BROKER
  ID:98  | 9698: 600 shares   | NOT IN BROKER
  ID:100 | 1093: 1000 shares  | NOT IN BROKER
  ID:99  | 1929: 600 shares   | NOT IN BROKER

MOOMOO BROKER (1 position):
  2269: 500 shares @ 37.10    | NOT IN DATABASE
```

### After Manual Sync
```
DATABASE POSITIONS (1 open):
  ID:101 | 2269: 500 shares @ 37.10 | MATCHES BROKER
```

---

## Recommended Fixes

### Fix #1: Extend Polling Window
```python
# Change from 5 seconds to 30 seconds
for attempt in range(30):  # Poll up to 30 times
    time.sleep(1)
```

### Fix #2: Implement Fill Callback
Use Moomoo's push notification system instead of polling:
```python
def on_order_update(self, data):
    if data['order_status'] in ['FILLED', 'FILLED_PART']:
        self.db.record_position(...)
```

### Fix #3: Run Sync More Frequently
Add sync at:
- End of each cycle (not just start)
- After each execute_trade call
- As a separate cron job (every 5 minutes)

### Fix #4: Never Record Position Until Fill Confirmed
Remove the `is_submitted` path entirely:
```python
# ONLY record if actually filled
if is_filled or is_partial:
    position_id = self.db.record_position(...)
```

### Fix #5: Add Order Tracking Table
Track pending orders separately:
```sql
CREATE TABLE pending_orders (
    order_id TEXT PRIMARY KEY,
    symbol TEXT,
    side TEXT,
    quantity INT,
    submitted_at TIMESTAMP,
    last_checked TIMESTAMP,
    check_count INT
);
```
Then reconcile pending orders against broker.

### Fix #6: Normalize Symbol Format
Create a single `normalize_symbol()` function used everywhere:
```python
def normalize_symbol(symbol: str) -> str:
    """Always return format: '700' (no prefix, no leading zeros)"""
    symbol = symbol.replace('HK.', '').replace('.HK', '')
    return symbol.lstrip('0') or '0'
```

---

## File References

| File | Version | Relevant Code |
|------|---------|---------------|
| tool_executor.py | 3.1.0 | `_execute_trade()` lines 472-730 |
| unified_agent.py | 3.2.0 | `sync_positions_with_broker()` call at line 584 |
| brokers/moomoo.py | 1.4.0 | `execute_trade()` lines 513-617 |
| data/database.py | 1.4.0 | `record_position()` lines 343-394 |

---

## Conclusion

The order-to-position workflow has multiple critical flaws that result in:
1. **Phantom positions** - DB shows positions that don't exist
2. **Missing positions** - Real positions not tracked in DB
3. **Stale data** - Sync runs too infrequently to catch issues

The core issue is **optimistic recording** - the system records positions hoping they'll fill, instead of **waiting for confirmation** that they actually filled.

**Priority:** HIGH - This affects all trading operations and P&L tracking.
