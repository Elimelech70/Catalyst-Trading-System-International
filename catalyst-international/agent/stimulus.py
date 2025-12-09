"""
Name of Application: Catalyst Trading System
Name of file: agent/stimulus.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Evaluate market conditions and generate stimuli for thinking

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Stimulus detection and classification
- Condition-triggered thinking
- Temporal event detection

Description:
The stimulus evaluator determines what deserves Claude's attention.
Rather than thinking about everything constantly, it identifies specific
conditions that warrant analysis - volume spikes, price moves, pattern
completions, news events, position updates, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any, Optional
from zoneinfo import ZoneInfo

import structlog

logger = structlog.get_logger()


class StimulusType(Enum):
    """Types of stimuli that trigger thinking."""

    VOLUME_SPIKE = "VOLUME_SPIKE"
    PRICE_MOVE = "PRICE_MOVE"
    PATTERN_SIGNAL = "PATTERN_SIGNAL"
    NEWS_EVENT = "NEWS_EVENT"
    POSITION_UPDATE = "POSITION_UPDATE"
    STOP_TRIGGERED = "STOP_TRIGGERED"
    TARGET_REACHED = "TARGET_REACHED"
    TIME_STOP = "TIME_STOP"
    SCHEDULED = "SCHEDULED"
    RISK_WARNING = "RISK_WARNING"


@dataclass
class Stimulus:
    """A stimulus that requires thought."""

    type: StimulusType
    symbol: Optional[str] = None
    level: str = "TACTICAL"  # TACTICAL, ANALYTICAL, STRATEGIC
    urgency: str = "normal"  # low, normal, high, critical
    data: dict = field(default_factory=dict)
    timestamp: str = ""


class StimulusEvaluator:
    """Evaluates market conditions and generates stimuli."""

    def __init__(
        self,
        strategy: Optional[dict] = None,
        timezone: str = "Asia/Hong_Kong",
    ):
        """Initialize stimulus evaluator.

        Args:
            strategy: Current strategy parameters
            timezone: Market timezone
        """
        self.strategy = strategy or {}
        self.tz = ZoneInfo(timezone)

        # Thresholds from strategy
        self.volume_threshold = self.strategy.get("volume_threshold", 1.5)
        self.price_threshold = self.strategy.get("price_threshold", 2.0)
        self.max_daily_loss_pct = self.strategy.get("max_daily_loss_pct", 2.0)

        # State tracking
        self.last_prices: dict = {}
        self.last_volumes: dict = {}
        self.alerted_symbols: set = set()

    def evaluate(self, market_state, portfolio) -> list[Stimulus]:
        """Evaluate market state and return stimuli for processing.

        Args:
            market_state: Current market state snapshot
            portfolio: Current portfolio state

        Returns:
            List of stimuli requiring thought
        """
        stimuli = []

        # Skip if market is closed
        if not market_state.is_market_open:
            return stimuli

        # Check each quote for volume/price spikes
        for symbol, quote in market_state.quotes.items():
            # Volume spike detection
            volume_stim = self._check_volume_spike(symbol, quote)
            if volume_stim:
                stimuli.append(volume_stim)

            # Price move detection
            price_stim = self._check_price_move(symbol, quote)
            if price_stim:
                stimuli.append(price_stim)

        # Check position updates
        position_stimuli = self._check_positions(portfolio)
        stimuli.extend(position_stimuli)

        # Check risk limits
        risk_stim = self._check_risk_limits(portfolio)
        if risk_stim:
            stimuli.append(risk_stim)

        return stimuli

    def _check_volume_spike(
        self, symbol: str, quote
    ) -> Optional[Stimulus]:
        """Check for volume spike."""
        # Get volume ratio from quote
        volume = getattr(quote, "volume", 0) if hasattr(quote, "volume") else quote.get("volume", 0)

        # Compare to last known volume
        last_volume = self.last_volumes.get(symbol, volume)
        self.last_volumes[symbol] = volume

        if last_volume == 0:
            return None

        volume_change = (volume - last_volume) / last_volume if last_volume > 0 else 0

        # Significant volume increase
        if volume_change > self.volume_threshold:
            return Stimulus(
                type=StimulusType.VOLUME_SPIKE,
                symbol=symbol,
                level="TACTICAL",
                urgency="high",
                data={
                    "current_volume": volume,
                    "previous_volume": last_volume,
                    "volume_change_pct": round(volume_change * 100, 2),
                    "threshold": self.volume_threshold,
                },
                timestamp=datetime.now(self.tz).isoformat(),
            )

        return None

    def _check_price_move(
        self, symbol: str, quote
    ) -> Optional[Stimulus]:
        """Check for significant price move."""
        # Get current price
        if hasattr(quote, "last"):
            current_price = quote.last
            change_pct = quote.change_pct
        else:
            current_price = quote.get("last", 0)
            change_pct = quote.get("change_pct", 0)

        # Track price
        last_price = self.last_prices.get(symbol, current_price)
        self.last_prices[symbol] = current_price

        # Check for significant move
        if abs(change_pct) > self.price_threshold:
            # Only alert once per symbol per session
            if symbol in self.alerted_symbols:
                return None

            self.alerted_symbols.add(symbol)

            return Stimulus(
                type=StimulusType.PRICE_MOVE,
                symbol=symbol,
                level="TACTICAL",
                urgency="high" if abs(change_pct) > 5 else "normal",
                data={
                    "current_price": current_price,
                    "change_pct": change_pct,
                    "threshold": self.price_threshold,
                    "direction": "up" if change_pct > 0 else "down",
                },
                timestamp=datetime.now(self.tz).isoformat(),
            )

        return None

    def _check_positions(self, portfolio) -> list[Stimulus]:
        """Check positions for stop/target triggers."""
        stimuli = []

        positions = portfolio.get("positions", [])

        for pos in positions:
            symbol = pos.get("symbol")
            current_price = pos.get("current_price", 0)
            entry_price = pos.get("avg_cost", 0)
            unrealized_pnl_pct = pos.get("unrealized_pnl_pct", 0)

            # Check for significant loss (potential stop)
            if unrealized_pnl_pct < -5:
                stimuli.append(
                    Stimulus(
                        type=StimulusType.STOP_TRIGGERED,
                        symbol=symbol,
                        level="TACTICAL",
                        urgency="critical",
                        data={
                            "current_price": current_price,
                            "entry_price": entry_price,
                            "unrealized_pnl_pct": unrealized_pnl_pct,
                        },
                        timestamp=datetime.now(self.tz).isoformat(),
                    )
                )

            # Check for target approach (> 10% gain)
            elif unrealized_pnl_pct > 10:
                stimuli.append(
                    Stimulus(
                        type=StimulusType.TARGET_REACHED,
                        symbol=symbol,
                        level="TACTICAL",
                        urgency="high",
                        data={
                            "current_price": current_price,
                            "entry_price": entry_price,
                            "unrealized_pnl_pct": unrealized_pnl_pct,
                        },
                        timestamp=datetime.now(self.tz).isoformat(),
                    )
                )

        return stimuli

    def _check_risk_limits(self, portfolio) -> Optional[Stimulus]:
        """Check portfolio risk limits."""
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0)

        # Check daily loss limit
        if daily_pnl_pct < -self.max_daily_loss_pct * 100:
            return Stimulus(
                type=StimulusType.RISK_WARNING,
                symbol=None,
                level="TACTICAL",
                urgency="critical",
                data={
                    "daily_pnl_pct": daily_pnl_pct,
                    "limit_pct": -self.max_daily_loss_pct * 100,
                    "action_required": "CLOSE_ALL",
                },
                timestamp=datetime.now(self.tz).isoformat(),
            )

        # Warning at 75% of limit
        elif daily_pnl_pct < -self.max_daily_loss_pct * 75:
            return Stimulus(
                type=StimulusType.RISK_WARNING,
                symbol=None,
                level="TACTICAL",
                urgency="high",
                data={
                    "daily_pnl_pct": daily_pnl_pct,
                    "limit_pct": -self.max_daily_loss_pct * 100,
                    "warning": "Approaching daily loss limit",
                },
                timestamp=datetime.now(self.tz).isoformat(),
            )

        return None

    # =========================================================================
    # Temporal Events
    # =========================================================================

    def is_session_start(self) -> bool:
        """Check if it's the start of a trading session."""
        now = datetime.now(self.tz)
        current_time = now.time()

        # Morning session start (09:30)
        morning_start = time(9, 30)
        if time(9, 30) <= current_time <= time(9, 35):
            return True

        # Afternoon session start (13:00)
        if time(13, 0) <= current_time <= time(13, 5):
            return True

        return False

    def is_session_end(self) -> bool:
        """Check if it's the end of a trading session."""
        now = datetime.now(self.tz)
        current_time = now.time()

        # Morning session end (11:55-12:00)
        if time(11, 55) <= current_time <= time(12, 0):
            return True

        # Afternoon session end (15:55-16:00)
        if time(15, 55) <= current_time <= time(16, 0):
            return True

        return False

    def is_week_start(self) -> bool:
        """Check if it's the start of trading week (Monday morning)."""
        now = datetime.now(self.tz)
        return now.weekday() == 0 and now.hour == 9 and now.minute < 35

    def is_week_end(self) -> bool:
        """Check if it's the end of trading week (Friday close)."""
        now = datetime.now(self.tz)
        return now.weekday() == 4 and now.hour == 16 and now.minute < 5

    def is_lunch_approaching(self) -> bool:
        """Check if lunch break is approaching (should close positions)."""
        now = datetime.now(self.tz)
        current_time = now.time()
        return time(11, 45) <= current_time <= time(11, 55)

    def reset_session(self):
        """Reset session state (called at session start)."""
        self.alerted_symbols.clear()
        self.last_prices.clear()
        self.last_volumes.clear()
