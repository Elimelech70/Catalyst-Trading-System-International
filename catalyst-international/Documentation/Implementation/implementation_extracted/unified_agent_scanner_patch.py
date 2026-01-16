"""
Name of Application: Catalyst Trading System
Name of file: unified_agent.py (PATCH for scanner integration)
Version: 2.1.0
Last Updated: 2026-01-16
Purpose: Wire _scan_market() to MarketData.scan_market()

REVISION HISTORY:
v2.1.0 (2026-01-16) - Scanner integration
- FIXED: _scan_market() now calls MarketData.scan_market()
- Added scan configuration from YAML config
- Returns actual trading candidates instead of empty list

Description:
This file contains the REPLACEMENT code for the _scan_market() method
in unified_agent.py. Find the existing placeholder method and replace it.

FIND THIS CODE in unified_agent.py:
----------------------------------------
async def _scan_market(self) -> List[Dict[str, Any]]:
    \"\"\"Scan market for trading candidates.\"\"\"
    # Implementation depends on your scanner logic
    logger.info("Scanning market...")
    # Placeholder - implement your scanning logic
    return []  # <-- Always returns empty!
----------------------------------------

REPLACE WITH THE CODE BELOW:
"""

# =============================================================================
# REPLACEMENT METHOD FOR unified_agent.py
# =============================================================================

async def _scan_market(self) -> List[Dict[str, Any]]:
    """Scan market for trading candidates.
    
    This method calls MarketData.scan_market() with configuration
    from the agent's YAML config file.
    
    Returns:
        List of trading candidates sorted by composite score
    """
    logger.info("Scanning market for trading candidates...")
    
    # Check if we have market data client
    if not self.market_data:
        logger.warning("No market data client - using broker directly")
        
        # Fallback: scan directly through broker if available
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
    
    # Get scan configuration from YAML config
    scan_config = self.config.get('scanner', {})
    
    try:
        # Call MarketData.scan_market() with config
        candidates = self.market_data.scan_market(scan_config)
        
        if candidates:
            logger.info(f"Scan found {len(candidates)} candidates")
            
            # Log top candidates for visibility
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


# =============================================================================
# ALSO ADD THIS TO __init__ METHOD (after self.market_data initialization)
# =============================================================================

# In the UnifiedAgent.__init__ method, ensure market_data is properly initialized:
"""
# After creating broker, ensure market_data is initialized
if self.broker:
    from data.market import MarketData, get_market_data
    self.market_data = get_market_data(self.broker)
else:
    self.market_data = None
"""
