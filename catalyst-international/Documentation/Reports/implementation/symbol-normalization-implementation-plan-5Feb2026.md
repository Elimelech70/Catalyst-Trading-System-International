# Symbol Normalization Implementation Plan

**Date:** 2026-02-05
**Version:** 1.0.0
**Status:** PROPOSED
**Priority:** HIGH (includes critical bug fix)

---

## Executive Summary

Investigation of the codebase revealed symbol handling inconsistencies causing the phantom position issue observed on 2026-02-05 (`0670` vs `670`). Additionally, a **critical bug** was discovered where `scan_market()` will crash due to a data structure mismatch.

This plan addresses:
1. Critical bug: `get_quotes_batch()` return type mismatch
2. Centralized symbol normalization function
3. Database layer normalization
4. Removal of duplicate normalization code

---

## Problem Statement

### Issue 1: Phantom Position from Symbol Mismatch (Observed)
```
2026-02-05 03:00:08 - Auto-sync: closed phantom position 0670
2026-02-05 03:00:08 - Auto-sync: added missing position 670
```
- Position created with symbol `0670` (from agent)
- Broker returned position with symbol `670` (normalized)
- Auto-sync couldn't match them, causing churn

### Issue 2: Critical Bug in scan_market() (Latent)
```python
# market.py line 386
quotes_batch = self.broker.get_quotes_batch(symbols)  # Returns List[dict]

# market.py line 394
quote_data = quotes_batch.get(symbol)  # FAILS: List has no .get() method
```

### Issue 3: Inconsistent Normalization Locations
| Location | Method |
|----------|--------|
| `moomoo.py:309` | `code.lstrip('0') or '0'` |
| `moomoo.py:870` | `symbol.lstrip('0') or '0'` |
| `tool_executor.py:743-744` | `.replace('.HK', '').replace('HK.', '').lstrip('0')` |
| `database.py` | None (stores as-is) |

---

## Proposed Solution

### Architecture

```
                    ┌─────────────────────────────┐
                    │   normalize_symbol(symbol)   │
                    │   Location: brokers/moomoo.py│
                    │   Returns: '700' (no zeros)  │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌───────────────┐        ┌─────────────────┐        ┌─────────────────┐
│ tool_executor │        │   database.py   │        │   market.py     │
│ (remove dup)  │        │ (add normalize) │        │ (use normalize) │
└───────────────┘        └─────────────────┘        └─────────────────┘
```

### Normalization Rules

```python
def normalize_symbol(symbol: str) -> str:
    """
    Normalize HKEX symbol to canonical format.

    Input formats accepted:
    - '700', '0700', '00700'     → '700'
    - 'HK.00700', 'HK.0700'      → '700'
    - '700.HK', '0700.HK'        → '700'
    - '5', '0005', '00005'       → '5'

    Output: Symbol without leading zeros or exchange prefix/suffix
    """
    if not symbol:
        return symbol

    # Remove exchange prefixes/suffixes
    s = str(symbol).upper()
    s = s.replace('HK.', '').replace('.HK', '')

    # Strip leading zeros, but keep at least one digit
    s = s.lstrip('0') or '0'

    return s
```

---

## Implementation Tasks

### Task 1: Add normalize_symbol() to moomoo.py (CRITICAL)

**File:** `brokers/moomoo.py`
**Version:** 1.5.0 → 1.6.0

**Changes:**
1. Add `normalize_symbol()` as a module-level function (exportable)
2. Update `_parse_hk_symbol()` to use `normalize_symbol()`
3. Update `close_position()` to use `normalize_symbol()`

**Code:**
```python
# Add after imports, before MoomooClient class (around line 50)

def normalize_symbol(symbol: str) -> str:
    """
    Normalize HKEX symbol to canonical format without leading zeros.

    Examples:
        '0700' → '700'
        'HK.00700' → '700'
        '700.HK' → '700'
        '5' → '5'
        '0005' → '5'
    """
    if not symbol:
        return symbol

    s = str(symbol).upper()
    s = s.replace('HK.', '').replace('.HK', '')
    s = s.lstrip('0') or '0'

    return s
```

**Update _parse_hk_symbol():**
```python
def _parse_hk_symbol(self, moomoo_symbol: str) -> str:
    """Convert Moomoo format back to simple code."""
    if moomoo_symbol.startswith("HK."):
        code = moomoo_symbol[3:]
        return normalize_symbol(code)
    return normalize_symbol(moomoo_symbol)
```

---

### Task 2: Fix get_quotes_batch() Return Type (CRITICAL)

**File:** `brokers/moomoo.py`
**Issue:** Returns `List[dict]` but `scan_market()` expects `Dict[str, dict]`

**Current (broken):**
```python
def get_quotes_batch(self, symbols: List[str]) -> List[dict]:
    # ...
    return quotes  # List[dict]
```

**Fixed:**
```python
def get_quotes_batch(self, symbols: List[str]) -> Dict[str, dict]:
    """
    Get quotes for multiple symbols.

    Returns:
        Dict mapping normalized symbol to quote data
    """
    # ... existing code ...

    # Convert list to dict keyed by normalized symbol
    quotes_dict = {}
    for quote in quotes:
        sym = normalize_symbol(quote.get('symbol', ''))
        quotes_dict[sym] = quote

    return quotes_dict
```

---

### Task 3: Update market.py scan_market() (MEDIUM)

**File:** `data/market.py`
**Version:** 2.3.0 → 2.4.0

**Changes:**
1. Import `normalize_symbol` from `brokers.moomoo`
2. Normalize symbols when building candidate list
3. Use normalized symbols for quote lookup

**Code changes at line 394:**
```python
# Before (broken if quotes_batch is list)
quote_data = quotes_batch.get(symbol)

# After (works with dict, uses normalized key)
from brokers.moomoo import normalize_symbol
norm_symbol = normalize_symbol(symbol)
quote_data = quotes_batch.get(norm_symbol)
```

---

### Task 4: Add Normalization to database.py (MEDIUM)

**File:** `data/database.py`
**Version:** 1.4.0 → 1.5.0

**Changes:**
1. Import `normalize_symbol` from `brokers.moomoo`
2. Normalize symbol in `record_position()`
3. Normalize symbol in `record_order()`
4. Normalize symbol in position/order queries

**Code for record_position() (around line 381):**
```python
from brokers.moomoo import normalize_symbol

async def record_position(self, ...):
    # Normalize symbol before storage
    symbol = normalize_symbol(symbol)
    # ... rest of function
```

**Code for record_order() (around line 441):**
```python
async def record_order(self, ...):
    # Normalize symbol before storage
    symbol = normalize_symbol(symbol)
    # ... rest of function
```

---

### Task 5: Remove Duplicate Normalization from tool_executor.py (LOW)

**File:** `tool_executor.py`
**Version:** 3.2.0 → 3.3.0

**Changes:**
Remove manual normalization at lines 743-744:
```python
# REMOVE these lines:
pos_symbol = str(pos_symbol).replace('.HK', '').replace('HK.', '').lstrip('0')
check_symbol = symbol.replace('.HK', '').replace('HK.', '').lstrip('0')

# REPLACE with:
from brokers.moomoo import normalize_symbol
pos_symbol = normalize_symbol(pos_symbol)
check_symbol = normalize_symbol(symbol)
```

---

### Task 6: Normalize Index Constituents (LOW)

**File:** `data/market.py`
**Location:** `_get_index_constituents()` (lines 517-650)

**Issue:** Symbols stored with leading zeros: `'0005'`, `'0700'`

**Option A (Preferred):** Normalize at retrieval time
```python
def _get_index_constituents(self, index: str) -> List[str]:
    constituents = self._index_data.get(index, [])
    return [normalize_symbol(s) for s in constituents]
```

**Option B:** Update hardcoded lists (more changes, less flexible)

---

## Implementation Order

| Order | Task | Priority | Risk | Dependencies |
|-------|------|----------|------|--------------|
| 1 | Add `normalize_symbol()` to moomoo.py | CRITICAL | Low | None |
| 2 | Fix `get_quotes_batch()` return type | CRITICAL | Medium | Task 1 |
| 3 | Update `scan_market()` to use dict | MEDIUM | Low | Tasks 1, 2 |
| 4 | Add normalization to database.py | MEDIUM | Low | Task 1 |
| 5 | Remove duplicate code in tool_executor.py | LOW | Low | Task 1 |
| 6 | Normalize index constituents | LOW | Low | Task 1 |

---

## Testing Plan

### Unit Tests

```python
# tests/test_symbol_normalization.py

def test_normalize_symbol_basic():
    assert normalize_symbol('700') == '700'
    assert normalize_symbol('0700') == '700'
    assert normalize_symbol('00700') == '700'

def test_normalize_symbol_exchange_prefix():
    assert normalize_symbol('HK.00700') == '700'
    assert normalize_symbol('HK.0700') == '700'
    assert normalize_symbol('HK.700') == '700'

def test_normalize_symbol_exchange_suffix():
    assert normalize_symbol('700.HK') == '700'
    assert normalize_symbol('0700.HK') == '700'

def test_normalize_symbol_single_digit():
    assert normalize_symbol('5') == '5'
    assert normalize_symbol('0005') == '5'
    assert normalize_symbol('00005') == '5'

def test_normalize_symbol_edge_cases():
    assert normalize_symbol('') == ''
    assert normalize_symbol(None) == None
    assert normalize_symbol('0') == '0'
```

### Integration Tests

1. **Quote Batch Test:**
   ```python
   quotes = client.get_quotes_batch(['0700', '700', 'HK.00700'])
   assert '700' in quotes  # All should map to same key
   ```

2. **Position Recording Test:**
   ```python
   await db.record_position(symbol='0700', ...)
   positions = await db.get_positions()
   assert positions[0]['symbol'] == '700'  # Stored normalized
   ```

3. **End-to-End Test:**
   ```python
   # Execute trade with '0700'
   result = executor.execute_trade(symbol='0700', ...)

   # Verify position stored as '700'
   positions = client.get_positions()
   assert any(p.symbol == '700' for p in positions)

   # Verify close works with either format
   close_result = executor.close_position(symbol='700')
   assert close_result['status'] == 'success'
   ```

### Regression Tests

- [ ] `get_quote()` still works for all symbol formats
- [ ] `get_positions()` returns normalized symbols
- [ ] `scan_market()` completes without error
- [ ] Trade execution works end-to-end
- [ ] Position close works with any symbol format
- [ ] Auto-sync doesn't create phantom positions

---

## Rollback Plan

If issues occur after deployment:

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international

# Restore backups
cp brokers/moomoo.py.backup.v1.5.0 brokers/moomoo.py
cp tool_executor.py.backup.v3.2.0 tool_executor.py
cp data/database.py.backup.v1.4.0 data/database.py
cp data/market.py.backup.v2.3.0 data/market.py

# Restart services
sudo systemctl restart catalyst-intl-agent
```

---

## File Version Updates

| File | Current | New | Changes |
|------|---------|-----|---------|
| `brokers/moomoo.py` | 1.5.0 | 1.6.0 | Add `normalize_symbol()`, fix `get_quotes_batch()` |
| `data/market.py` | 2.3.0 | 2.4.0 | Use `normalize_symbol()`, fix `scan_market()` |
| `data/database.py` | 1.4.0 | 1.5.0 | Add normalization to record functions |
| `tool_executor.py` | 3.2.0 | 3.3.0 | Use centralized `normalize_symbol()` |

---

## CLAUDE.md Updates Required

Add to revision history:
```markdown
**v3.11.0 (2026-02-XX)** - SYMBOL NORMALIZATION
- Added normalize_symbol() function to moomoo.py v1.6.0
- Fixed get_quotes_batch() to return Dict (was List) - critical bug fix
- Added symbol normalization to database.py v1.5.0
- Removed duplicate normalization from tool_executor.py v3.3.0
- Eliminates phantom position symbol mismatches (0670 vs 670)
- See: Documentation/Reports/implementation/symbol-normalization-implementation-plan-5Feb2026.md
```

Update file versions table with new versions.

---

## Estimated Impact

- **Phantom positions:** Eliminated (primary goal)
- **scan_market() stability:** Fixed critical latent bug
- **Code maintainability:** Single source of truth for normalization
- **Database consistency:** All symbols stored in canonical format

---

## Approval

- [ ] Technical review completed
- [ ] Test plan approved
- [ ] Rollback plan verified
- [ ] Ready for implementation

---

**Document Version:** 1.0.0
**Created by:** Claude Code
**Date:** 2026-02-05
