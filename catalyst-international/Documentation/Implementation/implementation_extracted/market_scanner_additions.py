"""
Name of Application: Catalyst Trading System
Name of file: market.py (ADDITIONS for scan_market)
Version: 1.1.0
Last Updated: 2026-01-16
Purpose: Add scan_market method to MarketData class

REVISION HISTORY:
v1.1.0 (2026-01-16) - Add market scanning capability
- Added scan_market() method
- Wraps MoomooClient.scan_market() with additional filtering
- Adds pattern detection integration
- Supports configurable scan parameters

Description:
These methods should be ADDED to the existing MarketData class in data/market.py.
The scan_market method provides the interface that unified_agent.py calls.

ADD THIS METHOD to the MarketData class:
"""

# =============================================================================
# ADD THIS METHOD TO MarketData CLASS in data/market.py
# =============================================================================

def scan_market(
    self,
    config: dict = None,
) -> list:
    """Scan market for trading candidates.
    
    This is the main entry point for market scanning, called by unified_agent.py.
    It wraps the broker's scan_market() and adds additional filtering/scoring.
    
    Args:
        config: Scan configuration dict with optional keys:
            - sectors: List of sector plate codes
            - min_volume_ratio: Minimum volume vs average (default: 1.3)
            - min_change_pct: Minimum price change % (default: 1.0)
            - max_change_pct: Maximum price change % (default: 15.0)
            - min_price: Minimum price HKD (default: 1.0)
            - max_price: Maximum price HKD (default: 500.0)
            - min_turnover: Minimum turnover HKD (default: 10M)
            - top_n: Number of candidates to return (default: 10)
            - detect_patterns: Whether to run pattern detection (default: False)
            
    Returns:
        List of candidate dicts sorted by composite score
        
    Example:
        candidates = market_data.scan_market({
            "min_volume_ratio": 1.5,
            "min_change_pct": 2.0,
            "top_n": 5,
        })
    """
    if not self.broker:
        logger.warning("No broker client - cannot scan market")
        return []
    
    # Default config
    if config is None:
        config = {}
    
    # Extract parameters with defaults
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
        # Call broker's scan_market
        candidates = self.broker.scan_market(**scan_params)
        
        if not candidates:
            logger.warning("No candidates found from broker scan")
            return []
        
        logger.info(f"Broker scan returned {len(candidates)} candidates")
        
        # Optionally add pattern detection
        if config.get("detect_patterns", False):
            candidates = self._add_pattern_scores(candidates)
        
        return candidates
        
    except Exception as e:
        logger.error(f"Market scan failed: {e}")
        return []


def _add_pattern_scores(self, candidates: list) -> list:
    """Add pattern detection scores to candidates.
    
    This method runs pattern detection on each candidate and adjusts
    the composite score based on detected patterns.
    
    Args:
        candidates: List of candidate dicts from scan_market
        
    Returns:
        Updated candidates with pattern info and adjusted scores
    """
    from data.patterns import PatternDetector
    
    detector = PatternDetector(self)
    
    for candidate in candidates:
        symbol = candidate.get("symbol")
        try:
            patterns = detector.detect_patterns(symbol, days=30)
            
            if patterns:
                # Add pattern bonus (up to 0.2)
                pattern_bonus = min(len(patterns) * 0.05, 0.2)
                candidate["patterns"] = [p.get("pattern_type") for p in patterns]
                candidate["pattern_count"] = len(patterns)
                candidate["pattern_bonus"] = round(pattern_bonus, 2)
                
                # Adjust composite score
                old_score = candidate.get("composite_score", 0)
                candidate["composite_score"] = round(
                    min(old_score + pattern_bonus, 1.0), 2
                )
            else:
                candidate["patterns"] = []
                candidate["pattern_count"] = 0
                candidate["pattern_bonus"] = 0
                
        except Exception as e:
            logger.warning(f"Pattern detection failed for {symbol}: {e}")
            candidate["patterns"] = []
            candidate["pattern_count"] = 0
            candidate["pattern_bonus"] = 0
    
    # Re-sort by updated composite score
    candidates.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    
    return candidates
