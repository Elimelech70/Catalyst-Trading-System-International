# Lessons Learned: Catalyst US Trading System

**Name of Application:** Catalyst Trading System  
**Name of file:** lessons-learned-us-system-2025-12.md  
**Version:** 1.0.0  
**Last Updated:** 2025-12-13  
**Purpose:** Critical lessons from US system development for International system implementation  
**Audience:** Claude Code working on International HKEX system

---

## Executive Summary

The US Catalyst Trading System ran for 6+ weeks in paper trading mode. During this period, we discovered critical bugs that prevented proper risk management. These lessons MUST be incorporated into the International system design from day one.

**Total Paper Trading Loss:** -$2,459.75 (positions closed Dec 15)  
**Root Cause:** Risk management never actually executed - bracket orders silently failed

---

## Critical Lesson #1: Broker APIs Fail Silently

### What Happened

We sent stop-loss and take-profit parameters to Alpaca. Alpaca accepted the order with status "accepted". We assumed risk management was active. **It wasn't.**

### Root Cause

Alpaca's API requires `order_class=OrderClass.BRACKET` to create a 3-legged order. Without this parameter, Alpaca:
- Accepts the order ✓
- Creates the entry order ✓
- **Silently ignores** stop_loss parameter ✗
- **Silently ignores** take_profit parameter ✗
- Returns success status ✓

No error. No warning. Just silent failure.

### The Broken Code

```python
# This code LOOKS correct but doesn't work
request = MarketOrderRequest(
    symbol=symbol,
    qty=quantity,
    side=order_side,
    time_in_force=TimeInForce.DAY,
    stop_loss=StopLossRequest(stop_price=145.00),
    take_profit=TakeProfitRequest(limit_price=160.00)
)
# Result: Simple market order, NO stop loss, NO take profit
```

### The Fixed Code

```python
# This actually creates bracket order
request = MarketOrderRequest(
    symbol=symbol,
    qty=quantity,
    side=order_side,
    time_in_force=TimeInForce.DAY,
    order_class=OrderClass.BRACKET,  # ← CRITICAL
    stop_loss=StopLossRequest(stop_price=145.00),
    take_profit=TakeProfitRequest(limit_price=160.00)
)
# Result: 3-legged bracket order with stop and target
```

### Lesson for International System

**NEVER trust broker API success responses.** After EVERY order submission:

1. Query the broker for order details
2. Verify the order type matches what you intended
3. Verify child orders (stop/target) exist if expected
4. Log the verification result
5. Alert if verification fails

```python
# Pattern for International system
async def submit_and_verify_bracket_order(self, params):
    # Submit order
    order_id = await self.broker.submit_order(params)
    
    # Wait briefly for broker processing
    await asyncio.sleep(1)
    
    # Verify order structure
    order_details = await self.broker.get_order(order_id)
    
    if params.stop_loss and not order_details.has_stop_order:
        raise RuntimeError(f"CRITICAL: Stop order not created for {order_id}")
    
    if params.take_profit and not order_details.has_target_order:
        raise RuntimeError(f"CRITICAL: Target order not created for {order_id}")
    
    return order_details
```

---

## Critical Lesson #2: String Mapping Bugs Are Deadly

### What Happened

Our system used "long" and "short" internally. Alpaca uses "buy" and "sell". The mapping code:

```python
# Bug: Only checks for exact "buy" match
order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
```

When we sent `side="long"`:
- `"long".lower() == "buy"` → False
- Falls through to `OrderSide.SELL`
- **Every "long" position became a short sell**

### Impact

- 68 positions affected
- All intended longs were actually shorts
- Positions lost money in both directions

### The Fix

```python
def _normalize_side(side: str) -> OrderSide:
    """Handle ALL valid side strings"""
    side_lower = side.lower()
    if side_lower in ("buy", "long"):
        return OrderSide.BUY
    elif side_lower in ("sell", "short"):
        return OrderSide.SELL
    else:
        raise ValueError(f"Invalid order side: {side}")
```

### Lesson for International System

1. **Explicit mapping with validation** - Never use if/else fallthrough for critical values
2. **Comprehensive logging** - Log input AND output of every mapping
3. **Defense in depth** - Validate after mapping that result makes sense

```python
# Pattern for International system
def map_order_side(internal_side: str, broker: str) -> str:
    """
    Map internal side representation to broker-specific value.
    Raises ValueError for unknown inputs - never silently defaults.
    """
    SIDE_MAPPING = {
        "ibkr": {
            "long": "BUY",
            "short": "SELL",
            "buy": "BUY",
            "sell": "SELL"
        }
    }
    
    broker_map = SIDE_MAPPING.get(broker)
    if not broker_map:
        raise ValueError(f"Unknown broker: {broker}")
    
    result = broker_map.get(internal_side.lower())
    if not result:
        raise ValueError(f"Unknown side '{internal_side}' for broker {broker}")
    
    logger.info(f"Side mapping: {internal_side} → {result} (broker: {broker})")
    return result
```

---

## Critical Lesson #3: Sub-Penny Prices Cause Mass Rejections

### What Happened

Python floating point math produced prices like `$9.050000190734863`. Alpaca rejected 95% of orders due to "sub-penny increment" violations.

### The Fix

```python
def _round_price(price: Optional[float]) -> Optional[float]:
    """Round to 2 decimal places for broker compliance"""
    if price is None:
        return None
    return round(float(price), 2)
```

### Lesson for International System

**ALWAYS round prices before sending to broker.** Different markets have different tick sizes:

| Market | Minimum Tick | Round To |
|--------|--------------|----------|
| US Stocks | $0.01 | 2 decimals |
| HKEX (HKD) | $0.01 (varies by price) | Check price tier |
| Forex | 0.0001 (pip) | 4-5 decimals |

```python
# Pattern for International system
def round_to_tick(price: float, market: str, symbol: str) -> float:
    """Round price to valid tick size for market"""
    tick_size = get_tick_size(market, symbol, price)
    return round(price / tick_size) * tick_size
```

---

## Critical Lesson #4: Duplicate Code Causes Drift

### What Happened

We had TWO copies of `alpaca_trader.py`:
- `services/trading/common/alpaca_trader.py` - Fixed to v1.4.0
- `services/risk-manager/common/alpaca_trader.py` - Still broken v1.0.0

When we fixed trading-service, we forgot risk-manager. The bug persisted.

### Lesson for International System

**Single source of truth for all broker interaction code.**

The International system's simplified architecture (single Python script) naturally avoids this. But if you create helper modules:

1. ONE broker module, imported everywhere
2. Version number in module header
3. Grep codebase for duplicates before deployment

```bash
# Check for duplicate files
find . -name "*.py" -exec basename {} \; | sort | uniq -d
```

---

## Critical Lesson #5: Never Rely on Single Point of Failure

### What Happened

Our only risk management was Alpaca bracket orders. When they silently failed, we had zero protection. Positions drifted -11.8% (UAMY) with no intervention.

### The Fix

Added `PositionMonitor` - a background task that:
1. Polls positions every 30 seconds
2. Gets current prices from broker
3. Compares to stop/target prices in database
4. Closes positions that breach limits

### Lesson for International System

**Implement layered risk management from day one:**

```
Layer 1: Broker bracket orders (primary)
    ↓ (if fails)
Layer 2: Position monitor background task (fallback)
    ↓ (if fails)  
Layer 3: Daily P&L circuit breaker (emergency)
    ↓ (if fails)
Layer 4: Human alert via email/SMS (last resort)
```

```python
# Pattern for International system
class RiskManager:
    """Multi-layer risk management"""
    
    async def monitor_loop(self):
        while self.running:
            try:
                # Layer 2: Check positions vs stops
                await self._check_position_stops()
                
                # Layer 3: Check daily P&L
                await self._check_daily_pnl_limit()
                
            except Exception as e:
                # Layer 4: Alert human
                await self._send_emergency_alert(f"Risk monitor error: {e}")
            
            await asyncio.sleep(30)
```

---

## Critical Lesson #6: Database and Broker WILL Diverge

### What Happened

| Source | Positions |
|--------|-----------|
| Database | 60 |
| Alpaca | 34 |
| Difference | 26 (phantom) |

Causes:
- Orders expired at broker, database not updated
- Orders rejected, database not updated
- Network failures during order submission

### Lesson for International System

**Implement reconciliation from day one:**

```python
async def reconcile_positions(self):
    """
    Reconcile database with broker - run every hour and at startup.
    Broker is source of truth.
    """
    db_positions = await self.db.get_open_positions()
    broker_positions = await self.broker.get_positions()
    
    db_symbols = {p.symbol for p in db_positions}
    broker_symbols = {p.symbol for p in broker_positions}
    
    # Positions in DB but not at broker (phantom)
    phantoms = db_symbols - broker_symbols
    for symbol in phantoms:
        logger.warning(f"PHANTOM POSITION: {symbol} in DB but not at broker")
        await self.db.mark_position_phantom(symbol)
    
    # Positions at broker but not in DB (orphan)
    orphans = broker_symbols - db_symbols
    for symbol in orphans:
        logger.warning(f"ORPHAN POSITION: {symbol} at broker but not in DB")
        await self.db.create_position_from_broker(symbol)
    
    # Quantity mismatches
    for symbol in db_symbols & broker_symbols:
        db_qty = db_positions[symbol].quantity
        broker_qty = broker_positions[symbol].quantity
        if db_qty != broker_qty:
            logger.warning(f"QTY MISMATCH: {symbol} DB={db_qty} Broker={broker_qty}")
            await self.db.update_position_qty(symbol, broker_qty)
```

---

## Critical Lesson #7: Order Status Never Auto-Updates

### What Happened

Database showed orders as "accepted" forever. Never updated to "filled", "cancelled", or "expired". We thought orders were pending when they had already filled.

### The Fix

Background task polling Alpaca every 60 seconds to sync order status.

### Lesson for International System

**Implement order status sync from day one:**

```python
async def sync_order_status(self):
    """Sync order status from broker to database"""
    
    # Get all non-terminal orders from DB
    pending_orders = await self.db.get_orders_by_status(['accepted', 'pending', 'new'])
    
    for order in pending_orders:
        try:
            broker_order = await self.broker.get_order(order.broker_order_id)
            
            if broker_order.status != order.status:
                logger.info(f"Order {order.id} status: {order.status} → {broker_order.status}")
                await self.db.update_order_status(
                    order.id,
                    broker_order.status,
                    broker_order.filled_qty,
                    broker_order.filled_price
                )
        except OrderNotFound:
            logger.warning(f"Order {order.id} not found at broker")
            await self.db.update_order_status(order.id, 'unknown')
```

---

## Critical Lesson #8: Test With Real Broker, Not Mocks

### What Happened

Unit tests with mocked broker passed. Real broker behaved differently:
- Silent parameter ignoring (bracket orders)
- Different error messages
- Rate limiting
- Network timeouts

### Lesson for International System

**Paper trading IS your integration test environment.** Before going live:

1. Run full trading cycle in paper mode
2. **Manually verify** each order in broker dashboard
3. Check that stops/targets appear as separate orders
4. Trigger a stop loss manually (adjust price) to verify it executes
5. Run for at least 1 week before live

```python
# Integration test pattern
async def test_full_bracket_order_lifecycle():
    """
    Integration test - requires paper trading account.
    Verifies broker actually creates correct order structure.
    """
    # Submit bracket order
    order = await trader.submit_bracket_order(
        symbol="AAPL",
        quantity=1,
        side="long",
        entry_price=150.00,
        stop_loss=145.00,
        take_profit=160.00
    )
    
    # Wait for broker processing
    await asyncio.sleep(2)
    
    # Verify with broker
    orders = await trader.get_orders_for_symbol("AAPL")
    
    # Should have 3 orders: entry, stop, target
    assert len(orders) == 3, f"Expected 3 orders, got {len(orders)}"
    
    order_types = {o.order_type for o in orders}
    assert "limit" in order_types or "market" in order_types  # Entry
    assert "stop" in order_types  # Stop loss
    assert "limit" in order_types  # Take profit
    
    # Clean up
    await trader.cancel_all_orders("AAPL")
```

---

## Critical Lesson #9: Log Everything, Query Later

### What Happened

When bugs were discovered, we had to reconstruct what happened from incomplete logs. Key information was missing:
- Input parameters to functions
- Mapping transformations
- Broker responses (full, not just status)

### Lesson for International System

**Structured logging with complete context:**

```python
import structlog

logger = structlog.get_logger()

async def submit_order(self, params: OrderParams):
    # Log input
    logger.info("order_submission_start",
        symbol=params.symbol,
        side=params.side,
        quantity=params.quantity,
        entry_price=params.entry_price,
        stop_loss=params.stop_loss,
        take_profit=params.take_profit
    )
    
    # Map values
    broker_side = map_order_side(params.side, "ibkr")
    logger.info("order_side_mapped",
        input_side=params.side,
        output_side=broker_side
    )
    
    # Submit to broker
    response = await self.broker.submit(...)
    
    # Log full response
    logger.info("order_submission_response",
        order_id=response.order_id,
        status=response.status,
        broker_response=response.raw  # Full response for debugging
    )
    
    return response
```

---

## Critical Lesson #10: Positions Accumulate Without Limits

### What Happened

Each trading cycle opened 5 positions. No cycle closed any (bracket orders failed). After 10 cycles: 50 open positions. Position count grew unbounded.

### The Fix

- Added 50 max total positions limit
- Added deduplication (no duplicate symbols)
- Added position check before opening new

### Lesson for International System

**Implement position limits from day one:**

```python
async def can_open_position(self, symbol: str) -> tuple[bool, str]:
    """Check if new position can be opened"""
    
    # Check total position count
    current_count = await self.db.count_open_positions()
    if current_count >= self.max_positions:
        return False, f"Max positions ({self.max_positions}) reached"
    
    # Check for duplicate symbol
    existing = await self.db.get_open_position(symbol)
    if existing:
        return False, f"Already have open position in {symbol}"
    
    # Check buying power
    buying_power = await self.broker.get_buying_power()
    if buying_power < self.min_buying_power:
        return False, f"Insufficient buying power: ${buying_power}"
    
    return True, "OK"
```

---

## Summary: International System Must-Haves

Before writing any trading code for International HKEX system:

| # | Requirement | Why |
|---|-------------|-----|
| 1 | Verify broker order structure after submission | Bracket orders fail silently |
| 2 | Explicit string mapping with validation | if/else fallthrough causes inversions |
| 3 | Round prices to valid tick size | Sub-penny causes rejections |
| 4 | Single broker module (no copies) | Duplicates drift and cause bugs |
| 5 | Multi-layer risk management | Never trust single point of failure |
| 6 | Position reconciliation at startup + hourly | DB and broker will diverge |
| 7 | Order status sync every 60 seconds | Status never auto-updates |
| 8 | Integration tests with real paper broker | Mocks hide broker quirks |
| 9 | Structured logging with full context | Debug reconstruction requires data |
| 10 | Position count limits + deduplication | Positions accumulate without bounds |

---

## Final Note

The US system bugs were discovered during paper trading, not live trading. Paper trading saved real money. **The International system should run paper trading for minimum 2 weeks before any live capital.**

These lessons cost ~$2,500 in paper money and 6 weeks of debugging. Apply them to International and save that time.

---

*Lessons documented by Claude Opus 4.5 from US Catalyst Trading System experience*
*For use by Claude Code on International HKEX System development*
