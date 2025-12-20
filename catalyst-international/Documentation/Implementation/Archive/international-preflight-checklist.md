# International System Pre-Flight Checklist

**For:** International Claude Code  
**Purpose:** Verify system ready for Monday HKEX trading  
**Created:** 2025-12-14  
**Author:** Big Bro Claude

---

## ⚠️ CRITICAL ISSUE FOUND

### Bracket Order Implementation is NOT True Bracket

**Current code (ibkr.py v2.2.0):**
```python
# Main order submitted first
trade = self.ib.placeOrder(contract, main_order)

# THEN stop/target placed SEPARATELY after fill
if trade.orderStatus.status == "Filled":
    self._place_stop_order(...)      # Independent order
    self._place_take_profit_order(...)  # Independent order
```

**Problems:**
1. If system crashes after main fill but before stop/target placed → **NO PROTECTION**
2. Stop and take-profit are independent → **BOTH CAN FILL** (overfill risk)
3. No OCA (One-Cancels-All) linking → **ORPHAN ORDERS** when one fills

**Required Fix - Use IBKR's proper bracket order:**

```python
from ib_async import Order, OrderType

def execute_bracket_trade(self, symbol, side, quantity, entry_price, stop_loss, take_profit):
    """Submit proper bracket order with linked stop/target."""
    contract = self._create_contract(symbol)
    self.ib.qualifyContracts(contract)
    
    action = "BUY" if side.lower() in ["buy", "long"] else "SELL"
    reverse_action = "SELL" if action == "BUY" else "BUY"
    
    # Parent order
    parent = Order()
    parent.orderId = self.ib.client.getReqId()
    parent.action = action
    parent.orderType = "LMT" if entry_price else "MKT"
    parent.totalQuantity = quantity
    if entry_price:
        parent.lmtPrice = self._round_to_tick(entry_price)
    parent.transmit = False  # Don't send yet
    
    # Stop loss (child)
    stop_order = Order()
    stop_order.orderId = self.ib.client.getReqId()
    stop_order.action = reverse_action
    stop_order.orderType = "STP"
    stop_order.auxPrice = self._round_to_tick(stop_loss)
    stop_order.totalQuantity = quantity
    stop_order.parentId = parent.orderId  # LINK TO PARENT
    stop_order.transmit = False
    
    # Take profit (child)
    take_profit_order = Order()
    take_profit_order.orderId = self.ib.client.getReqId()
    take_profit_order.action = reverse_action
    take_profit_order.orderType = "LMT"
    take_profit_order.lmtPrice = self._round_to_tick(take_profit)
    take_profit_order.totalQuantity = quantity
    take_profit_order.parentId = parent.orderId  # LINK TO PARENT
    take_profit_order.ocaGroup = f"OCA_{parent.orderId}"  # ONE-CANCELS-ALL
    stop_order.ocaGroup = f"OCA_{parent.orderId}"  # Same group
    take_profit_order.transmit = True  # Send all at once
    
    # Submit all three as atomic unit
    trades = []
    trades.append(self.ib.placeOrder(contract, parent))
    trades.append(self.ib.placeOrder(contract, stop_order))
    trades.append(self.ib.placeOrder(contract, take_profit_order))
    
    self.ib.sleep(1)
    
    return {
        "parent_order_id": str(parent.orderId),
        "stop_order_id": str(stop_order.orderId),
        "take_profit_order_id": str(take_profit_order.orderId),
        "status": trades[0].orderStatus.status,
        # ... etc
    }
```

**Key changes:**
1. `parentId` links children to parent
2. `ocaGroup` makes stop and target cancel each other
3. `transmit=False` until last order, then all sent atomically

---

## Pre-Flight Verification Tasks

### 1. IBKR Connection
```bash
# Verify IBKR Gateway running
curl http://localhost:4000/api/status || echo "IBKR not running"

# Verify can connect
python3 -c "
from brokers.ibkr import IBKRClient
client = IBKRClient()
print('Connected:', client.connect())
print('Account:', client.ib.managedAccounts())
client.disconnect()
"
```
- [ ] Gateway running
- [ ] Connection successful
- [ ] Account accessible

### 2. Bracket Order Test (CRITICAL)
```bash
# Submit test bracket order on paper account
python3 -c "
from brokers.ibkr import IBKRClient
client = IBKRClient()
client.connect()

# Test on a liquid HK stock
result = client.execute_trade(
    symbol='700',  # Tencent
    side='buy',
    quantity=100,
    order_type='limit',
    limit_price=350.00,  # Set below market to not fill
    stop_loss=340.00,
    take_profit=370.00,
    reason='PRE-FLIGHT TEST'
)
print('Result:', result)
# NOTE: Cancel this order after testing!
client.disconnect()
"
```
- [ ] Order submitted
- [ ] Check IBKR TWS/Portal: Do you see **3 linked orders** (parent + stop + target)?
- [ ] If you only see 1 order, bracket is NOT working - fix required
- [ ] Cancel test order

### 3. Order Side Mapping
```python
# Verify in ibkr.py
action = "BUY" if side.lower() in ["buy", "long"] else "SELL"
```
- [ ] "buy" → "BUY" ✓
- [ ] "sell" → "SELL" ✓
- [ ] "long" → "BUY" ✓
- [ ] "short" → "SELL" ✓
- [ ] Unknown value raises error (not silent fallback)

### 4. HKEX Tick Size Rounding
```python
# Test tick rounding
from brokers.ibkr import IBKRClient
client = IBKRClient()

# Test various price levels
tests = [
    (0.15, 0.001),   # → 0.150
    (0.35, 0.005),   # → 0.350
    (5.55, 0.01),    # → 5.55
    (15.33, 0.02),   # → 15.32 or 15.34
    (55.67, 0.05),   # → 55.65 or 55.70
    (150.33, 0.10),  # → 150.30 or 150.40
    (350.55, 0.20),  # → 350.40 or 350.60
]

for price, expected_tick in tests:
    rounded = client._round_to_tick(price)
    print(f"{price} → {rounded} (tick: {expected_tick})")
```
- [ ] All prices round correctly
- [ ] No sub-tick prices possible

### 5. Database Connection
```bash
python3 -c "
from data.database import get_database, init_database
init_database()
db = get_database()
print('DB connected:', db is not None)
"
```
- [ ] Database accessible
- [ ] Can write test record
- [ ] Can read back

### 6. Claude API
```bash
python3 -c "
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=100,
    messages=[{'role': 'user', 'content': 'Say OK if you can hear me'}]
)
print('Claude response:', response.content[0].text)
"
```
- [ ] API key valid
- [ ] Model accessible
- [ ] Response received

### 7. Market Hours Logic
```python
from safety import get_safety_validator
validator = get_safety_validator()
is_open, status = validator.is_market_open()
print(f"Market open: {is_open}, Status: {status}")
```
- [ ] Correctly identifies market hours
- [ ] Lunch break (12:00-13:00 HKT) blocked
- [ ] Weekend blocked

### 8. Position Reconciliation
```python
# After any test trades, verify DB matches IBKR
from brokers.ibkr import get_ibkr_client
from data.database import get_database

ibkr_positions = get_ibkr_client().get_positions()
db_positions = get_database().get_open_positions()

print(f"IBKR positions: {len(ibkr_positions)}")
print(f"DB positions: {len(db_positions)}")
# These should match!
```
- [ ] Position counts match
- [ ] No phantom positions in DB

### 9. Alert System
```bash
# Test alert sending
python3 -c "
from alerts import get_alert_sender
sender = get_alert_sender()
sender.send_alert('info', 'Test Alert', 'Pre-flight test from International system')
"
```
- [ ] Alert sent
- [ ] Email received

### 10. Cron Schedule
```bash
crontab -l | grep -i catalyst
```
- [ ] Cron configured for HKEX hours (09:30-16:00 HKT)
- [ ] Lunch break (12:00-13:00) excluded
- [ ] Weekend excluded

---

## Go/No-Go Decision

### MUST FIX before Monday:
- [x] Bracket orders create linked parent-child structure (not separate orders)
      **FIXED in ibkr.py v2.3.0 (2025-12-13)** - See commit 5c2a101

### SHOULD verify before Monday:
- [ ] All 10 checklist items pass
- [ ] At least one successful paper trade with proper bracket

### If bracket fix not ready:
**Option A:** Delay launch until fixed (recommended)
**Option B:** Launch with manual monitoring and tight position limits

---

## Monday Launch Procedure

### Pre-Market (09:00 HKT)
1. Verify IBKR Gateway running
2. Run quick connection test
3. Check account status and buying power
4. Verify no leftover orders from testing

### Market Open (09:30 HKT)
1. First trade: **50% size**, single position
2. Manually verify bracket orders in IBKR
3. Watch first 30 minutes closely

### If Issues:
1. Stop cron immediately: `crontab -r`
2. Close any open positions: `close_all` tool
3. Alert Big Bro via GitHub issue or message Craig

---

## Contact

Issues found? Create GitHub issue or relay through Craig to Big Bro Claude.

---

*Pre-Flight Checklist v1.0*  
*Big Bro Claude*  
*2025-12-14*
