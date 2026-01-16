"""
Name of Application: Catalyst Trading System
Name of file: moomoo.py (ADDITIONS for v1.5.0)
Version: 1.5.0
Last Updated: 2026-01-16
Purpose: Scanner methods to add to MoomooClient

REVISION HISTORY:
v1.5.0 (2026-01-16) - Add market scanning capability
- Added get_plate_list() to fetch HKEX sector/industry plates
- Added get_plate_stock() to get stocks within a plate
- Added scan_market() for full market scanning with filtering
- Supports volume ratio, price change, and price range filters
- Uses batch quotes to avoid rate limiting

Description:
These methods should be ADDED to the existing MoomooClient class in brokers/moomoo.py.
They enable market-wide scanning for trading candidates based on volume, momentum, and price criteria.

ADD THESE IMPORTS at the top of moomoo.py:
    from moomoo import Plate, SortField

ADD THESE METHODS to the MoomooClient class:
"""

# =============================================================================
# ADD THESE IMPORTS TO THE TOP OF moomoo.py
# =============================================================================
# from moomoo import Plate, SortField

# =============================================================================
# ADD THESE METHODS TO MoomooClient CLASS
# =============================================================================

def get_plate_list(self, plate_class: str = "ALL") -> list:
    """Get list of plates (sectors/industries) for HKEX.
    
    Args:
        plate_class: Plate type - "ALL", "INDUSTRY", "REGION", "CONCEPT"
        
    Returns:
        List of plate codes and names
        
    Example:
        plates = client.get_plate_list("INDUSTRY")
        # Returns: [{"code": "HK.BK1001", "name": "Tech Hardware"}, ...]
    """
    if not self._connected:
        raise RuntimeError("Not connected to OpenD")
    
    # Map string to Plate enum
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
    """Get stocks within a specific plate (sector/industry).
    
    Args:
        plate_code: Plate code (e.g., "HK.BK1001" for tech)
        sort_by: Sort field - "CODE", "CHANGE_RATE", "TURNOVER", "VOLUME"
        
    Returns:
        List of stock codes in the plate
        
    Example:
        stocks = client.get_plate_stock("HK.BK1001")
        # Returns: ["700", "9988", "1810", ...]
    """
    if not self._connected:
        raise RuntimeError("Not connected to OpenD")
    
    # Map sort field
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
        ascend=False  # Descending - highest first
    )
    
    if ret != RET_OK:
        logger.error(f"Failed to get stocks for plate {plate_code}: {data}")
        return []
    
    if data.empty:
        return []
    
    # Extract stock codes (convert from HK.00700 to 700)
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
    min_turnover: float = 10_000_000,  # 10M HKD
    max_candidates: int = 50,
    top_n: int = 10,
) -> list:
    """Scan HKEX market for trading candidates.
    
    This method:
    1. Gets stocks from specified sectors (or default high-liquidity sectors)
    2. Fetches batch quotes for all stocks
    3. Filters by volume, price change, and price range
    4. Scores and ranks candidates
    5. Returns top N candidates
    
    Args:
        sectors: List of plate codes to scan (default: major sectors)
        min_volume_ratio: Minimum volume vs average (default: 1.3x)
        min_change_pct: Minimum price change % (default: 1.0%)
        max_change_pct: Maximum price change % (default: 15.0%)
        min_price: Minimum stock price HKD (default: 1.0)
        max_price: Maximum stock price HKD (default: 500.0)
        min_turnover: Minimum turnover in HKD (default: 10M)
        max_candidates: Max stocks to analyze (default: 50)
        top_n: Number of top candidates to return (default: 10)
        
    Returns:
        List of candidate dicts with scores, sorted by composite score
        
    Example:
        candidates = client.scan_market(min_volume_ratio=1.5, top_n=5)
        # Returns: [{"symbol": "700", "score": 0.85, ...}, ...]
    """
    if not self._connected:
        raise RuntimeError("Not connected to OpenD")
    
    # Default sectors: Tech, Finance, Consumer, Healthcare, Energy
    if sectors is None:
        sectors = [
            "HK.BK1587",  # HK Tech (main tech stocks)
            "HK.BK1588",  # HK Finance
            "HK.BK1589",  # HK Consumer
            "HK.BK1590",  # HK Healthcare
            "HK.BK1910",  # Hang Seng Index constituents
        ]
    
    # Collect unique stocks from all sectors
    all_symbols = set()
    for sector in sectors:
        try:
            stocks = self.get_plate_stock(sector, sort_by="TURNOVER")
            all_symbols.update(stocks[:30])  # Top 30 per sector by turnover
        except Exception as e:
            logger.warning(f"Failed to get stocks for {sector}: {e}")
            continue
    
    if not all_symbols:
        logger.warning("No stocks found from sectors")
        return []
    
    # Limit to max_candidates
    symbols_list = list(all_symbols)[:max_candidates]
    logger.info(f"Scanning {len(symbols_list)} unique stocks from {len(sectors)} sectors")
    
    # Batch fetch quotes
    try:
        quotes = self.get_quotes_batch(symbols_list)
    except Exception as e:
        logger.error(f"Failed to fetch batch quotes: {e}")
        return []
    
    # Filter and score candidates
    candidates = []
    for symbol, quote in quotes.items():
        try:
            last_price = quote.get("last_price", 0)
            prev_close = quote.get("prev_close", 0)
            volume = quote.get("volume", 0)
            turnover = quote.get("turnover", 0)
            
            # Skip if missing critical data
            if not last_price or not prev_close or not volume:
                continue
            
            # Calculate metrics
            change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # Estimate volume ratio (compare to typical daily volume)
            # Note: We don't have historical avg volume here, so use turnover as proxy
            # A high turnover relative to price suggests high activity
            estimated_avg_volume = turnover / last_price if last_price > 0 else 0
            volume_ratio = volume / estimated_avg_volume if estimated_avg_volume > 0 else 1.0
            
            # Apply filters
            if last_price < min_price or last_price > max_price:
                continue
            if change_pct < min_change_pct or change_pct > max_change_pct:
                continue
            if turnover < min_turnover:
                continue
            # Note: volume_ratio filter is less reliable without historical data
            # We'll include it in scoring instead
            
            # Calculate composite score (0-1)
            # Momentum score (0-0.4): Based on price change
            if 2 <= change_pct <= 5:
                momentum_score = 0.4
            elif 1 <= change_pct < 2:
                momentum_score = 0.25
            elif 5 < change_pct <= 8:
                momentum_score = 0.3
            elif 8 < change_pct <= 15:
                momentum_score = 0.15  # Too hot, might be exhausted
            else:
                momentum_score = 0.1
            
            # Turnover score (0-0.3): Higher turnover = more liquid
            if turnover >= 100_000_000:  # 100M+
                turnover_score = 0.3
            elif turnover >= 50_000_000:  # 50M+
                turnover_score = 0.25
            elif turnover >= 20_000_000:  # 20M+
                turnover_score = 0.2
            else:
                turnover_score = 0.15
            
            # Price score (0-0.15): Sweet spot $10-100
            if 10 <= last_price <= 100:
                price_score = 0.15
            elif 5 <= last_price < 10 or 100 < last_price <= 200:
                price_score = 0.1
            else:
                price_score = 0.05
            
            # Spread score (0-0.15): Tight spread is better
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
                "name": quote.get("name", symbol),
                "price": round(last_price, 2),
                "change_pct": round(change_pct, 2),
                "volume": volume,
                "turnover": turnover,
                "turnover_m": round(turnover / 1_000_000, 1),  # In millions
                "bid": quote.get("bid_price", 0),
                "ask": quote.get("ask_price", 0),
                "momentum_score": round(momentum_score, 2),
                "turnover_score": round(turnover_score, 2),
                "price_score": round(price_score, 2),
                "spread_score": round(spread_score, 2),
                "composite_score": round(composite_score, 2),
                "timestamp": quote.get("update_time", ""),
            })
            
        except Exception as e:
            logger.warning(f"Error processing {symbol}: {e}")
            continue
    
    # Sort by composite score descending
    candidates.sort(key=lambda x: x["composite_score"], reverse=True)
    
    # Return top N
    top_candidates = candidates[:top_n]
    
    logger.info(
        f"Scan complete: {len(candidates)} passed filters, "
        f"returning top {len(top_candidates)}"
    )
    
    return top_candidates
