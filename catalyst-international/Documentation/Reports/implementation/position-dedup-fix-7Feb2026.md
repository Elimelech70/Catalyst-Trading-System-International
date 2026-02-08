# Position Deduplication Fix

**Date**: 2026-02-07
**Version**: CLAUDE.md v3.12.0
**Files Modified**: database.py v1.6.0, tool_executor.py v3.4.0, sql/schema.sql

## Problem

Despite symbol normalization (v3.11.0) and order fill confirmation (v3.10.0), positions were still being duplicated. The database had 22 open position rows for only ~11 actual broker positions. Symbol 9866 alone had 5 duplicate open rows.

**Root cause**: No code path checked for an existing open position before INSERT, and the database had no unique constraint to prevent it.

## Changes Made

### 1. Data Cleanup
- Closed 11 duplicate open position rows, keeping only the oldest (original) row per symbol
- SQL: `UPDATE positions SET status='closed' WHERE position_id IN (SELECT ... ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY created_at ASC) ... WHERE rn > 1)`

### 2. Partial Unique Index (sql/schema.sql)
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_unique_open_symbol
  ON positions(symbol) WHERE status = 'open';
```
Database-level safety net — even if code bugs exist, duplicate open positions for the same symbol are impossible.

### 3. database.py v1.6.0 - Upsert Logic
- `record_position()` now checks for an existing open position before INSERT
- If found: updates quantity (adds) and recalculates weighted average entry price
- If not found: performs normal INSERT (same as before)
- Added `close_position_by_id()` for targeted position closure by ID
- Normalized `side` to uppercase on entry

### 4. tool_executor.py v3.4.0 - Sync Deduplication
- `sync_positions_with_broker()` now deduplicates DB positions before comparison
- Uses `normalize_symbol()` on both broker and DB symbols during sync
- Closes duplicate DB rows via `close_position_by_id()`
- Normalized `side` to uppercase in `_execute_trade()`

## Verification

1. `SELECT symbol, count(*) FROM positions WHERE status='open' GROUP BY symbol HAVING count(*)>1` — returns 0 rows
2. Unique index prevents future duplicates at database level (IntegrityError on INSERT)
3. Application-level upsert prevents duplicates before they reach the database
