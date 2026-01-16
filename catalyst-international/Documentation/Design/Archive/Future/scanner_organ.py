"""
Name of Application: Catalyst Trading System
Name of file: organs/scanner/scanner_organ.py
Version: 1.0.0
Last Updated: 2025-12-25
Purpose: Scanner Organ - finds trading opportunities

Description:
The Scanner is the "eyes" of the organism. It continuously 
watches markets for opportunities matching our criteria.
"""

import logging
from typing import Any

from base_organ import BaseOrgan, OrganConfig

logger = logging.getLogger(__name__)


class ScannerOrgan(BaseOrgan):
    """
    The Scanner Organ - finds trading opportunities.
    
    Responsibilities:
    - Monitor markets for volume spikes
    - Detect unusual activity
    - Filter and score opportunities
    - Surface candidates to Analyst
    """
    
    def __init__(self):
        config = OrganConfig(
            name="scanner",
            port=5001,
            model="claude-haiku-4-5-20251001",  # Fast for frequent scanning
            max_tokens=1024
        )
        super().__init__(config)
        
        # Scanner-specific state
        self.active_scans = []
        self.candidates = []
    
    def _register_tools(self):
        """Register scanner-specific tools."""
        self.tools = {
            "scan_market": self.scan_market,
            "scan_sector": self.scan_sector,
            "get_unusual_volume": self.get_unusual_volume,
            "get_premarket_movers": self.get_premarket_movers,
            "score_candidate": self.score_candidate,
        }
    
    # =========================================================================
    # Tools
    # =========================================================================
    
    def scan_market(self, market: str = "HKEX") -> list[dict]:
        """
        Full market scan for opportunities.
        
        Args:
            market: Market to scan (HKEX, NYSE, NASDAQ)
        
        Returns:
            List of potential candidates with scores
        """
        logger.info(f"Scanning {market} for opportunities...")
        
        # Get market data (would call market data API)
        # For now, placeholder
        raw_candidates = self._get_market_data(market)
        
        # Filter by volume
        volume_filtered = [c for c in raw_candidates if c.get("volume_ratio", 0) > 1.5]
        
        # Score candidates
        scored = []
        for candidate in volume_filtered:
            score = self.score_candidate(candidate)
            candidate["score"] = score
            scored.append(candidate)
        
        # Sort by score, take top N
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = scored[:10]
        
        # Ask Claude to evaluate the batch
        if top_candidates:
            evaluation = self.think(
                context=f"Market: {market}, Candidates: {len(top_candidates)}",
                question=f"""Evaluate these candidates for trading potential:
                
{top_candidates}

Which are the strongest 3-5 and why? 
Return as JSON list with symbol and brief reasoning."""
            )
            logger.info(f"Claude evaluation: {evaluation[:200]}...")
        
        return top_candidates
    
    def scan_sector(self, sector: str) -> list[dict]:
        """
        Sector-specific scan.
        
        Args:
            sector: Sector to scan (tech, finance, energy, etc.)
        
        Returns:
            Sector candidates
        """
        logger.info(f"Scanning sector: {sector}")
        # Would filter market data by sector
        return []
    
    def get_unusual_volume(self, threshold: float = 2.0) -> list[dict]:
        """
        Get stocks with unusual volume.
        
        Args:
            threshold: Volume ratio threshold (e.g., 2.0 = 2x normal)
        
        Returns:
            Stocks exceeding threshold
        """
        logger.info(f"Checking unusual volume > {threshold}x")
        # Would query volume data
        return []
    
    def get_premarket_movers(self, min_change: float = 2.0) -> list[dict]:
        """
        Get pre-market movers.
        
        Args:
            min_change: Minimum % change to include
        
        Returns:
            Pre-market movers
        """
        logger.info(f"Getting pre-market movers > {min_change}%")
        # Would query pre-market data
        return []
    
    def score_candidate(self, candidate: dict) -> float:
        """
        Score a candidate based on multiple factors.
        
        Args:
            candidate: Candidate data
        
        Returns:
            Score 0-1
        """
        score = 0.0
        
        # Volume component (0-0.3)
        volume_ratio = candidate.get("volume_ratio", 1.0)
        if volume_ratio > 3.0:
            score += 0.3
        elif volume_ratio > 2.0:
            score += 0.2
        elif volume_ratio > 1.5:
            score += 0.1
        
        # Price action component (0-0.3)
        change_pct = candidate.get("change_pct", 0)
        if 2 < change_pct < 10:
            score += 0.3
        elif 1 < change_pct < 2:
            score += 0.2
        elif 0 < change_pct < 1:
            score += 0.1
        
        # Gap component (0-0.2)
        gap_pct = candidate.get("gap_pct", 0)
        if 1 < gap_pct < 5:
            score += 0.2
        elif 0.5 < gap_pct < 1:
            score += 0.1
        
        # Float/liquidity component (0-0.2)
        avg_volume = candidate.get("avg_volume", 0)
        if avg_volume > 1_000_000:
            score += 0.2
        elif avg_volume > 500_000:
            score += 0.1
        
        return min(score, 1.0)
    
    # =========================================================================
    # Internal Methods
    # =========================================================================
    
    def _get_market_data(self, market: str) -> list[dict]:
        """Get raw market data. Would call actual data API."""
        # Placeholder - would integrate with market data provider
        return []
    
    # =========================================================================
    # Main Processing
    # =========================================================================
    
    def process(self, input_data: dict) -> dict:
        """
        Main entry point for scanner processing.
        
        Args:
            input_data: Contains scan type and parameters
        
        Returns:
            Scan results
        """
        scan_type = input_data.get("type", "full")
        market = input_data.get("market", "HKEX")
        
        if scan_type == "full":
            candidates = self.scan_market(market)
        elif scan_type == "sector":
            sector = input_data.get("sector", "tech")
            candidates = self.scan_sector(sector)
        elif scan_type == "volume":
            threshold = input_data.get("threshold", 2.0)
            candidates = self.get_unusual_volume(threshold)
        elif scan_type == "premarket":
            candidates = self.get_premarket_movers()
        else:
            candidates = []
        
        # Store candidates for other organs
        self.candidates = candidates
        
        # Send to Analyst if we have candidates
        if candidates:
            self.send_message(
                to_organ="analyst",
                msg_type="candidates",
                payload={"candidates": candidates}
            )
        
        return {
            "status": "complete",
            "scan_type": scan_type,
            "market": market,
            "candidates_found": len(candidates),
            "top_candidates": candidates[:5]
        }
    
    # =========================================================================
    # Learning
    # =========================================================================
    
    def learn_from_outcome(self, candidate: dict, trade_result: dict):
        """
        Learn from how a candidate performed.
        
        This is called after a trade is closed to help the scanner
        improve its filtering and scoring.
        """
        # Did we score this correctly?
        original_score = candidate.get("score", 0)
        actual_result = trade_result.get("pnl_pct", 0)
        
        # Reflect on the outcome
        reflection = self.reflect(
            action={
                "type": "candidate_selection",
                "symbol": candidate.get("symbol"),
                "score": original_score,
                "volume_ratio": candidate.get("volume_ratio"),
                "change_pct": candidate.get("change_pct")
            },
            outcome={
                "pnl_pct": actual_result,
                "win": actual_result > 0,
                "exit_reason": trade_result.get("exit_reason")
            }
        )
        
        # Store learning
        self.store_learning(reflection)
        
        logger.info(f"Scanner learned: {reflection.get('learning', '')[:100]}...")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    # For testing
    scanner = ScannerOrgan()
    
    result = scanner.process({
        "type": "full",
        "market": "HKEX"
    })
    
    print(f"Scan result: {result}")
