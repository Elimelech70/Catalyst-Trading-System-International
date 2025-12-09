"""
Name of Application: Catalyst Trading System
Name of file: agent/monitor.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Real-time market monitoring via IBKR

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Market state monitoring
- Quote and technical data retrieval
- Market hours checking

Description:
This module handles continuous market monitoring through the IBKR connection.
It provides the market state that feeds into stimulus evaluation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

import structlog

logger = structlog.get_logger()

HK_TZ = ZoneInfo("Asia/Hong_Kong")


@dataclass
class Quote:
    """Market quote data."""

    symbol: str
    last: float
    bid: float
    ask: float
    volume: int
    high: float
    low: float
    open: float
    prev_close: float
    change: float
    change_pct: float
    timestamp: str = ""


@dataclass
class Technicals:
    """Technical indicators."""

    symbol: str
    timeframe: str
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    ema_9: float = 0.0
    ema_21: float = 0.0
    atr: float = 0.0
    volume_ratio: float = 0.0  # vs 20-day average
    timestamp: str = ""


@dataclass
class MarketState:
    """Current market state snapshot."""

    timestamp: str
    is_market_open: bool
    session: str  # 'pre_market', 'morning', 'lunch', 'afternoon', 'after_hours'

    # Index data
    hsi_last: float = 0.0
    hsi_change_pct: float = 0.0

    # Watchlist quotes
    quotes: dict = field(default_factory=dict)

    # Active positions data
    position_updates: list = field(default_factory=list)

    # Market breadth
    advancing: int = 0
    declining: int = 0
    unchanged: int = 0


class MarketMonitor:
    """Real-time market monitoring via IBKR."""

    def __init__(self, ib_client):
        """Initialize market monitor.

        Args:
            ib_client: Connected IB client instance
        """
        self.ib = ib_client
        self.watchlist: list[str] = []
        self.last_state: Optional[MarketState] = None

    async def initialize(self):
        """Initialize market monitoring."""
        logger.info("Initializing market monitor...")

        # Default watchlist - top HKEX stocks
        self.watchlist = [
            "0700",  # Tencent
            "0941",  # China Mobile
            "0005",  # HSBC
            "1299",  # AIA
            "0388",  # HKEX
            "2318",  # Ping An
            "0939",  # CCB
            "1398",  # ICBC
            "0883",  # CNOOC
            "0027",  # Galaxy Entertainment
        ]

        logger.info("Market monitor initialized", watchlist_size=len(self.watchlist))

    async def disconnect(self):
        """Disconnect from market data."""
        logger.info("Market monitor disconnected")

    async def get_state(self) -> MarketState:
        """Get current market state."""
        now = datetime.now(HK_TZ)

        # Determine session
        session = self._get_session(now)
        is_open = session in ("morning", "afternoon")

        state = MarketState(
            timestamp=now.isoformat(),
            is_market_open=is_open,
            session=session,
        )

        if is_open:
            # Get HSI data
            try:
                hsi_quote = await self._get_index_quote("HSI")
                state.hsi_last = hsi_quote.get("last", 0)
                state.hsi_change_pct = hsi_quote.get("change_pct", 0)
            except Exception as e:
                logger.warning("Failed to get HSI quote", error=str(e))

            # Get watchlist quotes
            for symbol in self.watchlist[:5]:  # Limit to reduce API calls
                try:
                    quote = await self.get_quote(symbol)
                    state.quotes[symbol] = quote
                except Exception as e:
                    logger.warning("Failed to get quote", symbol=symbol, error=str(e))

        self.last_state = state
        return state

    async def get_quote(self, symbol: str) -> Quote:
        """Get current quote for a symbol."""
        try:
            # Use IBKR client to get quote
            quote_data = self.ib.get_quote(symbol)

            return Quote(
                symbol=symbol,
                last=quote_data.get("last", 0),
                bid=quote_data.get("bid", 0),
                ask=quote_data.get("ask", 0),
                volume=quote_data.get("volume", 0),
                high=quote_data.get("high", 0),
                low=quote_data.get("low", 0),
                open=quote_data.get("open", 0),
                prev_close=quote_data.get("prev_close", 0),
                change=quote_data.get("change", 0),
                change_pct=quote_data.get("change_pct", 0),
                timestamp=datetime.now(HK_TZ).isoformat(),
            )

        except Exception as e:
            logger.error("Failed to get quote", symbol=symbol, error=str(e))
            return Quote(
                symbol=symbol,
                last=0,
                bid=0,
                ask=0,
                volume=0,
                high=0,
                low=0,
                open=0,
                prev_close=0,
                change=0,
                change_pct=0,
            )

    async def get_technicals(self, symbol: str, timeframe: str = "15m") -> Technicals:
        """Get technical indicators for a symbol."""
        try:
            # Get historical data from IBKR
            bars = self._get_historical_bars(symbol, timeframe)

            if not bars:
                return Technicals(symbol=symbol, timeframe=timeframe)

            # Calculate indicators
            closes = [b["close"] for b in bars]
            highs = [b["high"] for b in bars]
            lows = [b["low"] for b in bars]
            volumes = [b["volume"] for b in bars]

            return Technicals(
                symbol=symbol,
                timeframe=timeframe,
                rsi=self._calculate_rsi(closes, 14),
                macd=self._calculate_macd(closes)[0],
                macd_signal=self._calculate_macd(closes)[1],
                macd_histogram=self._calculate_macd(closes)[2],
                sma_20=self._calculate_sma(closes, 20),
                sma_50=self._calculate_sma(closes, 50),
                ema_9=self._calculate_ema(closes, 9),
                ema_21=self._calculate_ema(closes, 21),
                atr=self._calculate_atr(highs, lows, closes, 14),
                volume_ratio=self._calculate_volume_ratio(volumes),
                timestamp=datetime.now(HK_TZ).isoformat(),
            )

        except Exception as e:
            logger.error("Failed to get technicals", symbol=symbol, error=str(e))
            return Technicals(symbol=symbol, timeframe=timeframe)

    async def _get_index_quote(self, index: str) -> dict:
        """Get index quote (HSI, HSCEI, etc.)."""
        # For now, return placeholder
        # In production, would query IBKR for index data
        return {"last": 0, "change_pct": 0}

    def _get_historical_bars(self, symbol: str, timeframe: str) -> list:
        """Get historical bars for technical calculation."""
        try:
            duration = "5 D" if timeframe == "15m" else "1 M"
            bar_size = "15 mins" if timeframe == "15m" else "1 day"

            bars = self.ib.get_historical_data(symbol, duration, bar_size)
            return bars

        except Exception as e:
            logger.warning("Failed to get historical data", symbol=symbol, error=str(e))
            return []

    def _get_session(self, now: datetime) -> str:
        """Determine current market session."""
        hour = now.hour
        minute = now.minute

        if hour < 9 or (hour == 9 and minute < 30):
            return "pre_market"
        elif hour < 12:
            return "morning"
        elif hour == 12:
            return "lunch"
        elif hour < 16:
            return "afternoon"
        else:
            return "after_hours"

    # =========================================================================
    # Technical Indicator Calculations
    # =========================================================================

    def _calculate_rsi(self, closes: list, period: int = 14) -> float:
        """Calculate RSI."""
        if len(closes) < period + 1:
            return 50.0

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    def _calculate_macd(
        self, closes: list, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple:
        """Calculate MACD, Signal, Histogram."""
        if len(closes) < slow + signal:
            return (0.0, 0.0, 0.0)

        ema_fast = self._calculate_ema(closes, fast)
        ema_slow = self._calculate_ema(closes, slow)
        macd = ema_fast - ema_slow

        # For signal line, would need full EMA of MACD values
        # Simplified here
        signal_line = macd * 0.9  # Placeholder
        histogram = macd - signal_line

        return (round(macd, 4), round(signal_line, 4), round(histogram, 4))

    def _calculate_sma(self, closes: list, period: int) -> float:
        """Calculate Simple Moving Average."""
        if len(closes) < period:
            return closes[-1] if closes else 0.0

        return round(sum(closes[-period:]) / period, 4)

    def _calculate_ema(self, closes: list, period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(closes) < period:
            return closes[-1] if closes else 0.0

        multiplier = 2 / (period + 1)
        ema = closes[0]

        for price in closes[1:]:
            ema = (price - ema) * multiplier + ema

        return round(ema, 4)

    def _calculate_atr(
        self, highs: list, lows: list, closes: list, period: int = 14
    ) -> float:
        """Calculate Average True Range."""
        if len(closes) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        atr = sum(true_ranges[-period:]) / period
        return round(atr, 4)

    def _calculate_volume_ratio(self, volumes: list, period: int = 20) -> float:
        """Calculate volume ratio vs average."""
        if len(volumes) < period + 1:
            return 1.0

        avg_volume = sum(volumes[-period - 1 : -1]) / period
        current_volume = volumes[-1]

        if avg_volume == 0:
            return 1.0

        return round(current_volume / avg_volume, 2)
