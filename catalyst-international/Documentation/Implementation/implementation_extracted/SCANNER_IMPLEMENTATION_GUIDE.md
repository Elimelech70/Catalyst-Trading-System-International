# ==============================================================================
# SCANNER IMPLEMENTATION GUIDE
# ==============================================================================
# Name of Application: Catalyst Trading System
# Name of file: SCANNER_IMPLEMENTATION_GUIDE.md
# Version: 1.0.0
# Last Updated: 2026-01-16
# Purpose: Step-by-step guide to implement full market scanning
# ==============================================================================

# Scanner Implementation Guide

**Date**: 2026-01-16
**Version**: 1.0.0
**Author**: Claude (intl_claude implementation)

---

## Overview

This guide implements full market scanning capability for the HKEX trading agent.
It wires the placeholder `_scan_market()` method to real broker APIs.

### Files Changed

| File | Version | Change Type |
|------|---------|-------------|
| `brokers/moomoo.py` | 1.4.0 → 1.5.0 | ADD methods |
| `data/market.py` | 1.0.0 → 1.1.0 | ADD method |
| `unified_agent.py` | 2.0.0 → 2.1.0 | REPLACE method |
| `config/intl_claude_config.yaml` | - | ADD section |

---

## Step 1: Update brokers/moomoo.py

### 1.1 Add Imports

At the top of `brokers/moomoo.py`, add to the import block:

```python
from moomoo import (
    OpenQuoteContext,
    OpenSecTradeContext,
    TrdMarket,
    TrdSide,
    OrderType,
    SecurityFirm,
    RET_OK,
    ModifyOrderOp,
    TrdEnv,
    KLType,
    Market,
    SecurityType,
    Plate,      # ADD THIS
    SortField,  # ADD THIS
)
```

### 1.2 Add Methods to MoomooClient Class

Add these three methods to the `MoomooClient` class (before `execute_trade`):

```python
def get_plate_list(self, plate_class: str = "ALL") -> list:
    """Get list of plates (sectors/industries) for HKEX."""
    if not self._connected:
        raise RuntimeError("Not connected to OpenD")
    
    plate_map = {
        "ALL": Plate.ALL,
        "INDUSTRY": Plate.INDUSTRY,
        "REGION": Plate.REGION,
        "CONCEPT": Plate.CONCEPT,
    }
    plate_type = plate_map.get(plate_class.upper(), Plate.ALL)
    
    ret, data = self.quote_ctx.get_plate_list(Market.HK, plate_type)
    
    if ret != RET_OK:
        logger.error(f"Failed to get plate list: {data}")
        return []
    
    if data.empty:
        return []
    
    plates = []
    for _, row in data.iterrows():
        plates.append({
            "code": str(row.get("code", "")),
            "name": str(row.get("plate_name", "")),
            "plate_type": str(row.get("plate_type", "")),
        })
    
    logger.info(f"Found {len(plates)} plates of type {plate_class}")
    return plates


def get_plate_stock(self, plate_code: str, sort_by: str = "CHANGE_RATE") -> list:
    """Get stocks within a specific plate (sector/industry)."""
    if not self._connected:
        raise RuntimeError("Not connected to OpenD")
    
    sort_map = {
        "CODE": SortField.CODE,
        "CHANGE_RATE": SortField.CHANGE_RATE,
        "TURNOVER": SortField.TURNOVER, 
        "VOLUME": SortField.VOLUME,
    }
    sort_field = sort_map.get(sort_by.upper(), SortField.CHANGE_RATE)
    
    ret, data = self.quote_ctx.get_plate_stock(
        plate_code, 
        sort_field=sort_field,
        ascend=False
    )
    
    if ret != RET_OK:
        logger.error(f"Failed to get stocks for plate {plate_code}: {data}")
        return []
    
    if data.empty:
        return []
    
    stocks = []
    for _, row in data.iterrows():
        code = str(row.get("code", ""))
        simple_code = self._parse_hk_symbol(code)
        stocks.append(simple_code)
    
    logger.info(f"Found {len(stocks)} stocks in plate {plate_code}")
    return stocks


def scan_market(
    self,
    sectors: list = None,
    min_volume_ratio: float = 1.3,
    min_change_pct: float = 1.0,
    max_change_pct: float = 15.0,
    min_price: float = 1.0,
    max_price: float = 500.0,
    min_turnover: float = 10_000_000,
    max_candidates: int = 50,
    top_n: int = 10,
) -> list:
    """Scan HKEX market for trading candidates."""
    if not self._connected:
        raise RuntimeError("Not connected to OpenD")
    
    if sectors is None:
        sectors = [
            "HK.BK1587",  # HK Tech
            "HK.BK1588",  # HK Finance
            "HK.BK1589",  # HK Consumer
            "HK.BK1590",  # HK Healthcare
            "HK.BK1910",  # Hang Seng Index
        ]
    
    all_symbols = set()
    for sector in sectors:
        try:
            stocks = self.get_plate_stock(sector, sort_by="TURNOVER")
            all_symbols.update(stocks[:30])
        except Exception as e:
            logger.warning(f"Failed to get stocks for {sector}: {e}")
            continue
    
    if not all_symbols:
        logger.warning("No stocks found from sectors")
        return []
    
    symbols_list = list(all_symbols)[:max_candidates]
    logger.info(f"Scanning {len(symbols_list)} unique stocks")
    
    try:
        quotes = self.get_quotes_batch(symbols_list)
    except Exception as e:
        logger.error(f"Failed to fetch batch quotes: {e}")
        return []
    
    candidates = []
    for symbol, quote in quotes.items():
        try:
            last_price = quote.get("last_price", 0)
            prev_close = quote.get("prev_close", 0)
            volume = quote.get("volume", 0)
            turnover = quote.get("turnover", 0)
            
            if not last_price or not prev_close or not volume:
                continue
            
            change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            if last_price < min_price or last_price > max_price:
                continue
            if change_pct < min_change_pct or change_pct > max_change_pct:
                continue
            if turnover < min_turnover:
                continue
            
            # Scoring
            if 2 <= change_pct <= 5:
                momentum_score = 0.4
            elif 1 <= change_pct < 2:
                momentum_score = 0.25
            elif 5 < change_pct <= 8:
                momentum_score = 0.3
            elif 8 < change_pct <= 15:
                momentum_score = 0.15
            else:
                momentum_score = 0.1
            
            if turnover >= 100_000_000:
                turnover_score = 0.3
            elif turnover >= 50_000_000:
                turnover_score = 0.25
            elif turnover >= 20_000_000:
                turnover_score = 0.2
            else:
                turnover_score = 0.15
            
            if 10 <= last_price <= 100:
                price_score = 0.15
            elif 5 <= last_price < 10 or 100 < last_price <= 200:
                price_score = 0.1
            else:
                price_score = 0.05
            
            bid = quote.get("bid_price", 0)
            ask = quote.get("ask_price", 0)
            if bid > 0 and ask > 0:
                spread_pct = (ask - bid) / bid * 100
                if spread_pct < 0.2:
                    spread_score = 0.15
                elif spread_pct < 0.5:
                    spread_score = 0.1
                else:
                    spread_score = 0.05
            else:
                spread_score = 0.05
            
            composite_score = momentum_score + turnover_score + price_score + spread_score
            
            candidates.append({
                "symbol": symbol,
                "price": round(last_price, 2),
                "change_pct": round(change_pct, 2),
                "volume": volume,
                "turnover": turnover,
                "turnover_m": round(turnover / 1_000_000, 1),
                "bid": quote.get("bid_price", 0),
                "ask": quote.get("ask_price", 0),
                "momentum_score": round(momentum_score, 2),
                "turnover_score": round(turnover_score, 2),
                "price_score": round(price_score, 2),
                "spread_score": round(spread_score, 2),
                "composite_score": round(composite_score, 2),
            })
            
        except Exception as e:
            logger.warning(f"Error processing {symbol}: {e}")
            continue
    
    candidates.sort(key=lambda x: x["composite_score"], reverse=True)
    top_candidates = candidates[:top_n]
    
    logger.info(f"Scan complete: {len(candidates)} passed filters, returning top {len(top_candidates)}")
    return top_candidates
```

---

## Step 2: Update data/market.py

Add this method to the `MarketData` class:

```python
def scan_market(self, config: dict = None) -> list:
    """Scan market for trading candidates."""
    if not self.broker:
        logger.warning("No broker client - cannot scan market")
        return []
    
    if config is None:
        config = {}
    
    scan_params = {
        "sectors": config.get("sectors"),
        "min_volume_ratio": config.get("min_volume_ratio", 1.3),
        "min_change_pct": config.get("min_change_pct", 1.0),
        "max_change_pct": config.get("max_change_pct", 15.0),
        "min_price": config.get("min_price", 1.0),
        "max_price": config.get("max_price", 500.0),
        "min_turnover": config.get("min_turnover", 10_000_000),
        "max_candidates": config.get("max_candidates", 50),
        "top_n": config.get("top_n", 10),
    }
    
    logger.info(f"Starting market scan with params: {scan_params}")
    
    try:
        candidates = self.broker.scan_market(**scan_params)
        
        if not candidates:
            logger.warning("No candidates found from broker scan")
            return []
        
        logger.info(f"Broker scan returned {len(candidates)} candidates")
        return candidates
        
    except Exception as e:
        logger.error(f"Market scan failed: {e}")
        return []
```

---

## Step 3: Update unified_agent.py

### 3.1 Replace _scan_market Method

Find this placeholder:

```python
async def _scan_market(self) -> List[Dict[str, Any]]:
    """Scan market for trading candidates."""
    logger.info("Scanning market...")
    return []
```

Replace with:

```python
async def _scan_market(self) -> List[Dict[str, Any]]:
    """Scan market for trading candidates."""
    logger.info("Scanning market for trading candidates...")
    
    if not self.market_data:
        logger.warning("No market data client - using broker directly")
        
        if self.broker and hasattr(self.broker, 'scan_market'):
            try:
                scan_config = self.config.get('scanner', {})
                candidates = self.broker.scan_market(
                    sectors=scan_config.get('sectors'),
                    min_volume_ratio=scan_config.get('min_volume_ratio', 1.3),
                    min_change_pct=scan_config.get('min_change_pct', 1.0),
                    max_change_pct=scan_config.get('max_change_pct', 15.0),
                    min_price=scan_config.get('min_price', 1.0),
                    max_price=scan_config.get('max_price', 500.0),
                    min_turnover=scan_config.get('min_turnover', 10_000_000),
                    top_n=scan_config.get('top_n', 10),
                )
                logger.info(f"Broker scan returned {len(candidates)} candidates")
                return candidates
            except Exception as e:
                logger.error(f"Broker scan failed: {e}")
                return []
        else:
            logger.error("No broker available for scanning")
            return []
    
    scan_config = self.config.get('scanner', {})
    
    try:
        candidates = self.market_data.scan_market(scan_config)
        
        if candidates:
            logger.info(f"Scan found {len(candidates)} candidates")
            for i, c in enumerate(candidates[:5], 1):
                logger.info(
                    f"  #{i}: {c.get('symbol')} "
                    f"${c.get('price', 0):.2f} "
                    f"({c.get('change_pct', 0):+.1f}%) "
                    f"score={c.get('composite_score', 0):.2f}"
                )
        else:
            logger.warning("Scan returned no candidates")
        
        return candidates
        
    except Exception as e:
        logger.error(f"Market scan failed: {e}")
        return []
```

### 3.2 Ensure market_data is Initialized

In the `UnifiedAgent.__init__` method, ensure this exists after broker creation:

```python
# After creating broker
if self.broker:
    from data.market import MarketData, get_market_data
    self.market_data = get_market_data(self.broker)
else:
    self.market_data = None
```

---

## Step 4: Update Config File

Add the scanner section to `config/intl_claude_config.yaml`:

```yaml
scanner:
  sectors:
    - "HK.BK1587"   # HK Tech
    - "HK.BK1588"   # HK Finance
    - "HK.BK1589"   # HK Consumer
    - "HK.BK1590"   # HK Healthcare
    - "HK.BK1910"   # Hang Seng Index
  min_volume_ratio: 1.3
  min_change_pct: 1.0
  max_change_pct: 15.0
  min_price: 5.0
  max_price: 500.0
  min_turnover: 10000000
  max_candidates: 50
  top_n: 10
  detect_patterns: false
```

---

## Step 5: Test

### 5.1 Test MoomooClient Scanner

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
source .env

python3 -c "
from brokers.moomoo import MoomooClient

client = MoomooClient(paper_trading=True)
client.connect()

# Test plate list
plates = client.get_plate_list('INDUSTRY')
print(f'Found {len(plates)} industry plates')

# Test plate stocks
if plates:
    stocks = client.get_plate_stock(plates[0]['code'])
    print(f'First plate has {len(stocks)} stocks')

# Test full scan
candidates = client.scan_market(top_n=5)
print(f'Scan returned {len(candidates)} candidates:')
for c in candidates:
    print(f'  {c[\"symbol\"]}: \${c[\"price\"]} ({c[\"change_pct\"]:+.1f}%) score={c[\"composite_score\"]}')

client.disconnect()
"
```

### 5.2 Test Unified Agent Scanner

```bash
python3 unified_agent.py --mode scan
```

### 5.3 Expected Output

```
2026-01-16 10:00:00 - Scanning market for trading candidates...
2026-01-16 10:00:01 - Found 45 stocks in plate HK.BK1587
2026-01-16 10:00:02 - Scanning 50 unique stocks from 5 sectors
2026-01-16 10:00:03 - Fetched 50 quotes in batch
2026-01-16 10:00:03 - Scan complete: 23 passed filters, returning top 10
2026-01-16 10:00:03 - Scan found 10 candidates
2026-01-16 10:00:03 -   #1: 700 $412.80 (+3.2%) score=0.85
2026-01-16 10:00:03 -   #2: 9988 $89.50 (+2.8%) score=0.80
...
```

---

## Troubleshooting

### "Not connected to OpenD"
- Ensure OpenD is running: `systemctl status opend`
- Check connection: `ss -tlnp | grep 11111`

### "Failed to get plate list"
- Verify market data permissions in Moomoo account
- Check API rate limits (60 requests per 30 seconds)

### Empty scan results
- Check filter thresholds - may be too strict
- Try reducing `min_change_pct` to 0.5
- Try increasing `max_candidates` to 100

---

## Summary

| Component | Change | Lines |
|-----------|--------|-------|
| `brokers/moomoo.py` | +3 methods | ~180 |
| `data/market.py` | +1 method | ~50 |
| `unified_agent.py` | Replace 1 method | ~50 |
| Config YAML | +1 section | ~30 |

**Total: ~310 lines of changes**

---

*Implementation Guide v1.0.0*
*2026-01-16*
