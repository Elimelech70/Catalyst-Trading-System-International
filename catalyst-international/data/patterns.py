"""
Chart pattern detection for the Catalyst Trading Agent.

This module detects common momentum day trading patterns:
- Bull Flag
- Bear Flag
- Cup and Handle
- Ascending Triangle
- Descending Triangle
- ABCD Pattern
- Breakout/Breakdown
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Detected chart pattern."""

    pattern_type: str
    confidence: float  # 0-1
    entry_price: float
    stop_loss: float
    target_price: float
    risk_reward: float
    description: str
    timestamp: datetime


class PatternDetector:
    """Detects chart patterns in price data."""

    def __init__(self, market_data: Any = None):
        """Initialize pattern detector.

        Args:
            market_data: MarketData instance for price data
        """
        self.market_data = market_data

    def set_market_data(self, market_data: Any):
        """Set the market data provider."""
        self.market_data = market_data

    def detect_patterns(self, symbol: str, timeframe: str = "15m") -> list[dict]:
        """Detect all patterns for a symbol.

        Args:
            symbol: Stock code
            timeframe: Analysis timeframe

        Returns:
            List of detected patterns
        """
        if not self.market_data:
            raise RuntimeError("Market data provider not initialized")

        # Get price data
        df = self.market_data.get_historical(symbol, timeframe, bars=100)

        if len(df) < 50:
            return []

        patterns = []

        # Detect each pattern type
        detectors = [
            self._detect_bull_flag,
            self._detect_bear_flag,
            self._detect_cup_handle,
            self._detect_ascending_triangle,
            self._detect_descending_triangle,
            self._detect_abcd,
            self._detect_breakout,
            self._detect_breakdown,
        ]

        for detector in detectors:
            try:
                result = detector(df)
                if result:
                    patterns.append(result)
            except Exception as e:
                logger.warning(f"Pattern detection error: {e}")
                continue

        # Sort by confidence
        patterns.sort(key=lambda x: x["confidence"], reverse=True)

        return patterns

    def _detect_bull_flag(self, df: pd.DataFrame) -> dict | None:
        """Detect bull flag pattern.

        Bull flag: Strong upward move (pole) followed by consolidation (flag)
        that slopes slightly downward or sideways.
        """
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        # Look for pole in last 20-40 bars
        lookback = min(40, len(df) - 10)
        recent = df.tail(lookback)

        # Find the pole (strong upward move)
        max_idx = recent["high"].idxmax()
        pole_start_idx = max(0, df.index.get_loc(max_idx) - 10)
        pole_start = df.index[pole_start_idx]

        pole_move = df.loc[max_idx, "high"] - df.loc[pole_start, "low"]
        pole_pct = pole_move / df.loc[pole_start, "low"]

        # Need at least 5% pole
        if pole_pct < 0.05:
            return None

        # Check for consolidation after pole (flag)
        flag_bars = df.loc[max_idx:]

        if len(flag_bars) < 5:
            return None

        # Flag should be tightening range
        flag_high = flag_bars["high"].max()
        flag_low = flag_bars["low"].min()
        flag_range = (flag_high - flag_low) / flag_high

        # Flag range should be < 50% of pole
        if flag_range > pole_pct * 0.5:
            return None

        # Flag should be near highs (not more than 50% retracement)
        current = close[-1]
        retracement = (flag_high - current) / pole_move

        if retracement > 0.5:
            return None

        # Calculate confidence based on pattern quality
        confidence = self._calculate_pattern_confidence(
            pole_pct=pole_pct, flag_range=flag_range, retracement=retracement
        )

        if confidence < 0.5:
            return None

        # Entry, stop, target
        entry_price = flag_high * 1.001  # Breakout above flag high
        stop_loss = flag_low * 0.99  # Below flag low
        target_price = entry_price + pole_move  # Pole extension

        risk = entry_price - stop_loss
        reward = target_price - entry_price
        risk_reward = reward / risk if risk > 0 else 0

        return {
            "pattern_type": "bull_flag",
            "confidence": round(confidence, 2),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "risk_reward": round(risk_reward, 2),
            "description": f"Bull flag with {pole_pct*100:.1f}% pole, {flag_range*100:.1f}% consolidation",
            "timestamp": datetime.now().isoformat(),
        }

    def _detect_bear_flag(self, df: pd.DataFrame) -> dict | None:
        """Detect bear flag pattern (inverse of bull flag)."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        lookback = min(40, len(df) - 10)
        recent = df.tail(lookback)

        # Find the pole (strong downward move)
        min_idx = recent["low"].idxmin()
        pole_start_idx = max(0, df.index.get_loc(min_idx) - 10)
        pole_start = df.index[pole_start_idx]

        pole_move = df.loc[pole_start, "high"] - df.loc[min_idx, "low"]
        pole_pct = pole_move / df.loc[pole_start, "high"]

        if pole_pct < 0.05:
            return None

        # Check for consolidation
        flag_bars = df.loc[min_idx:]

        if len(flag_bars) < 5:
            return None

        flag_high = flag_bars["high"].max()
        flag_low = flag_bars["low"].min()
        flag_range = (flag_high - flag_low) / flag_low

        if flag_range > pole_pct * 0.5:
            return None

        current = close[-1]
        retracement = (current - flag_low) / pole_move

        if retracement > 0.5:
            return None

        confidence = self._calculate_pattern_confidence(
            pole_pct=pole_pct, flag_range=flag_range, retracement=retracement
        )

        if confidence < 0.5:
            return None

        entry_price = flag_low * 0.999
        stop_loss = flag_high * 1.01
        target_price = entry_price - pole_move

        risk = stop_loss - entry_price
        reward = entry_price - target_price
        risk_reward = reward / risk if risk > 0 else 0

        return {
            "pattern_type": "bear_flag",
            "confidence": round(confidence, 2),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "risk_reward": round(risk_reward, 2),
            "description": f"Bear flag with {pole_pct*100:.1f}% pole",
            "timestamp": datetime.now().isoformat(),
        }

    def _detect_cup_handle(self, df: pd.DataFrame) -> dict | None:
        """Detect cup and handle pattern.

        Cup and handle: U-shaped cup followed by small downward drift (handle)
        before breaking out.
        """
        if len(df) < 30:
            return None

        close = df["close"].values
        high = df["high"].values

        # Find potential cup (U-shape in last 50 bars)
        lookback = min(50, len(df))
        cup_data = df.tail(lookback)

        # Find left rim, bottom, right rim
        left_rim_idx = cup_data["high"].head(10).idxmax()
        bottom_idx = cup_data["low"].idxmin()
        right_rim_idx = cup_data["high"].tail(15).idxmax()

        # Validate cup shape
        left_rim = cup_data.loc[left_rim_idx, "high"]
        bottom = cup_data.loc[bottom_idx, "low"]
        right_rim = cup_data.loc[right_rim_idx, "high"]

        # Cup depth should be 12-35%
        cup_depth = (left_rim - bottom) / left_rim
        if cup_depth < 0.12 or cup_depth > 0.35:
            return None

        # Rims should be relatively equal (within 5%)
        rim_diff = abs(left_rim - right_rim) / left_rim
        if rim_diff > 0.05:
            return None

        # Check for handle (small pullback after right rim)
        handle_data = cup_data.loc[right_rim_idx:]
        if len(handle_data) < 3:
            return None

        handle_low = handle_data["low"].min()
        handle_depth = (right_rim - handle_low) / right_rim

        # Handle should be < 50% of cup depth
        if handle_depth > cup_depth * 0.5:
            return None

        confidence = 0.5 + (1 - rim_diff) * 0.2 + (1 - handle_depth / cup_depth) * 0.3

        if confidence < 0.6:
            return None

        entry_price = right_rim * 1.001
        stop_loss = handle_low * 0.99
        target_price = entry_price + (left_rim - bottom)

        risk = entry_price - stop_loss
        reward = target_price - entry_price
        risk_reward = reward / risk if risk > 0 else 0

        return {
            "pattern_type": "cup_handle",
            "confidence": round(confidence, 2),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "risk_reward": round(risk_reward, 2),
            "description": f"Cup & Handle with {cup_depth*100:.1f}% cup depth",
            "timestamp": datetime.now().isoformat(),
        }

    def _detect_ascending_triangle(self, df: pd.DataFrame) -> dict | None:
        """Detect ascending triangle pattern.

        Ascending triangle: Flat resistance with rising support (higher lows).
        """
        if len(df) < 20:
            return None

        recent = df.tail(30)
        high = recent["high"].values
        low = recent["low"].values

        # Find local highs and lows
        high_peaks = argrelextrema(high, np.greater, order=3)[0]
        low_troughs = argrelextrema(low, np.less, order=3)[0]

        if len(high_peaks) < 3 or len(low_troughs) < 3:
            return None

        # Check for flat resistance (peaks at similar level)
        peak_prices = high[high_peaks[-3:]]
        resistance_std = np.std(peak_prices) / np.mean(peak_prices)

        if resistance_std > 0.02:  # Resistance should be flat
            return None

        # Check for rising support (higher lows)
        trough_prices = low[low_troughs[-3:]]

        if not (trough_prices[1] > trough_prices[0] and trough_prices[2] > trough_prices[1]):
            return None

        resistance = np.mean(peak_prices)
        current = recent["close"].iloc[-1]

        # Price should be near resistance for breakout
        if current < resistance * 0.97:
            return None

        confidence = 0.6 + (1 - resistance_std * 10) * 0.2

        entry_price = resistance * 1.005
        stop_loss = trough_prices[-1] * 0.99
        target_price = entry_price + (resistance - trough_prices[0])

        risk = entry_price - stop_loss
        reward = target_price - entry_price
        risk_reward = reward / risk if risk > 0 else 0

        return {
            "pattern_type": "ascending_triangle",
            "confidence": round(min(confidence, 0.9), 2),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "risk_reward": round(risk_reward, 2),
            "description": "Ascending triangle with flat resistance and rising lows",
            "timestamp": datetime.now().isoformat(),
        }

    def _detect_descending_triangle(self, df: pd.DataFrame) -> dict | None:
        """Detect descending triangle (bearish pattern)."""
        if len(df) < 20:
            return None

        recent = df.tail(30)
        high = recent["high"].values
        low = recent["low"].values

        high_peaks = argrelextrema(high, np.greater, order=3)[0]
        low_troughs = argrelextrema(low, np.less, order=3)[0]

        if len(high_peaks) < 3 or len(low_troughs) < 3:
            return None

        # Flat support
        trough_prices = low[low_troughs[-3:]]
        support_std = np.std(trough_prices) / np.mean(trough_prices)

        if support_std > 0.02:
            return None

        # Lower highs
        peak_prices = high[high_peaks[-3:]]

        if not (peak_prices[1] < peak_prices[0] and peak_prices[2] < peak_prices[1]):
            return None

        support = np.mean(trough_prices)
        current = recent["close"].iloc[-1]

        if current > support * 1.03:
            return None

        confidence = 0.6 + (1 - support_std * 10) * 0.2

        entry_price = support * 0.995
        stop_loss = peak_prices[-1] * 1.01
        target_price = entry_price - (peak_prices[0] - support)

        risk = stop_loss - entry_price
        reward = entry_price - target_price
        risk_reward = reward / risk if risk > 0 else 0

        return {
            "pattern_type": "descending_triangle",
            "confidence": round(min(confidence, 0.9), 2),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "risk_reward": round(risk_reward, 2),
            "description": "Descending triangle with flat support and lower highs",
            "timestamp": datetime.now().isoformat(),
        }

    def _detect_abcd(self, df: pd.DataFrame) -> dict | None:
        """Detect ABCD pattern.

        ABCD: A to B move, B to C retracement (38-62%), C to D move equal to A-B.
        """
        if len(df) < 20:
            return None

        recent = df.tail(40)
        high = recent["high"].values
        low = recent["low"].values

        # Find swing points
        high_peaks = argrelextrema(high, np.greater, order=3)[0]
        low_troughs = argrelextrema(low, np.less, order=3)[0]

        if len(high_peaks) < 2 or len(low_troughs) < 2:
            return None

        # Bullish ABCD: A(low) -> B(high) -> C(low) -> D(high)
        try:
            # Get most recent swings
            a_idx = low_troughs[-2] if len(low_troughs) >= 2 else low_troughs[0]
            b_idx = high_peaks[-2] if len(high_peaks) >= 2 else high_peaks[0]

            # Ensure A comes before B
            if a_idx >= b_idx:
                return None

            c_idx = low_troughs[-1]

            # Ensure B comes before C
            if b_idx >= c_idx:
                return None

            a = low[a_idx]
            b = high[b_idx]
            c = low[c_idx]

            # AB move
            ab = b - a

            # BC retracement should be 38-62%
            bc_retrace = (b - c) / ab
            if bc_retrace < 0.38 or bc_retrace > 0.62:
                return None

            # Project D (CD = AB)
            d = c + ab

            current = recent["close"].iloc[-1]

            # Should be approaching D
            if current < c or current > d * 1.05:
                return None

            confidence = 0.6 + (0.5 - abs(bc_retrace - 0.5)) * 0.4

            entry_price = current
            stop_loss = c * 0.99
            target_price = d

            risk = entry_price - stop_loss
            reward = target_price - entry_price
            risk_reward = reward / risk if risk > 0 else 0

            if risk_reward < 1.5:
                return None

            return {
                "pattern_type": "ABCD",
                "confidence": round(confidence, 2),
                "entry_price": round(entry_price, 2),
                "stop_loss": round(stop_loss, 2),
                "target_price": round(target_price, 2),
                "risk_reward": round(risk_reward, 2),
                "description": f"ABCD with {bc_retrace*100:.0f}% retracement",
                "timestamp": datetime.now().isoformat(),
            }

        except (IndexError, ValueError):
            return None

    def _detect_breakout(self, df: pd.DataFrame) -> dict | None:
        """Detect breakout above resistance."""
        if len(df) < 20:
            return None

        recent = df.tail(30)

        # Find recent resistance (high of consolidation)
        consolidation = recent.head(25)
        resistance = consolidation["high"].max()

        # Current price should be breaking out
        current = recent["close"].iloc[-1]
        prev_close = recent["close"].iloc[-2]

        # Must be breaking above resistance
        if current <= resistance:
            return None

        # Previous bar should have been below resistance
        if prev_close > resistance:
            return None

        # Volume confirmation
        avg_volume = consolidation["volume"].mean()
        current_volume = recent["volume"].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        if volume_ratio < 1.5:
            return None

        confidence = 0.5 + min(volume_ratio - 1.5, 1.5) * 0.2

        # Support from consolidation
        support = consolidation["low"].min()
        breakout_range = resistance - support

        entry_price = current
        stop_loss = resistance * 0.99  # Stop below breakout level
        target_price = resistance + breakout_range

        risk = entry_price - stop_loss
        reward = target_price - entry_price
        risk_reward = reward / risk if risk > 0 else 0

        return {
            "pattern_type": "breakout",
            "confidence": round(min(confidence, 0.85), 2),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "risk_reward": round(risk_reward, 2),
            "description": f"Breakout above {resistance:.2f} with {volume_ratio:.1f}x volume",
            "timestamp": datetime.now().isoformat(),
        }

    def _detect_breakdown(self, df: pd.DataFrame) -> dict | None:
        """Detect breakdown below support (bearish)."""
        if len(df) < 20:
            return None

        recent = df.tail(30)
        consolidation = recent.head(25)
        support = consolidation["low"].min()

        current = recent["close"].iloc[-1]
        prev_close = recent["close"].iloc[-2]

        if current >= support:
            return None

        if prev_close < support:
            return None

        avg_volume = consolidation["volume"].mean()
        current_volume = recent["volume"].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        if volume_ratio < 1.5:
            return None

        confidence = 0.5 + min(volume_ratio - 1.5, 1.5) * 0.2

        resistance = consolidation["high"].max()
        breakdown_range = resistance - support

        entry_price = current
        stop_loss = support * 1.01
        target_price = support - breakdown_range

        risk = stop_loss - entry_price
        reward = entry_price - target_price
        risk_reward = reward / risk if risk > 0 else 0

        return {
            "pattern_type": "breakdown",
            "confidence": round(min(confidence, 0.85), 2),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "risk_reward": round(risk_reward, 2),
            "description": f"Breakdown below {support:.2f} with {volume_ratio:.1f}x volume",
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_pattern_confidence(
        self, pole_pct: float, flag_range: float, retracement: float
    ) -> float:
        """Calculate pattern confidence score."""
        # Higher pole = better
        pole_score = min(pole_pct / 0.1, 1.0) * 0.3

        # Tighter flag = better
        flag_score = max(0, 1 - flag_range / 0.05) * 0.4

        # Lower retracement = better
        retrace_score = max(0, 1 - retracement / 0.5) * 0.3

        return 0.5 + pole_score + flag_score + retrace_score


# Singleton instance
_pattern_detector: PatternDetector | None = None


def get_pattern_detector(market_data: Any = None) -> PatternDetector:
    """Get or create pattern detector singleton."""
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = PatternDetector(market_data)
    elif market_data and _pattern_detector.market_data is None:
        _pattern_detector.set_market_data(market_data)
    return _pattern_detector
