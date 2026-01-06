"""
Name of Application: Catalyst Trading System
Name of file: signals.py
Version: 1.1.0
Last Updated: 2026-01-06
Purpose: Exit signal detection - RULES BASED (no Claude cost)

REVISION HISTORY:
v1.1.0 (2026-01-06) - Production deployment
- Added trailing stop logic
- Improved HKEX-specific timing
- Better logging for debugging
- Added signal scoring for priority

v1.0.0 (2025-01-01) - Initial implementation

Description:
Detects exit signals based on rules. These are FREE checks that don't
require Claude API calls. Only uncertain/moderate signals trigger a
cheap Haiku consultation.

Signal Strength Levels:
- NONE (0): No signal
- WEAK (1): Note but don't act
- MODERATE (2): Uncertain - consult Haiku
- STRONG (3): Act immediately - no Claude needed
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")


class SignalStrength(Enum):
    """Signal strength levels."""
    NONE = 0        # No signal detected
    WEAK = 1        # Note but don't act
    MODERATE = 2    # Uncertain - ask Haiku
    STRONG = 3      # Act immediately (no Claude needed)


@dataclass
class ExitSignals:
    """Collection of exit signals for a position."""
    
    # P&L signals (most important)
    stop_loss_hit: SignalStrength = SignalStrength.NONE
    take_profit_hit: SignalStrength = SignalStrength.NONE
    trailing_stop_hit: SignalStrength = SignalStrength.NONE
    
    # Technical signals
    rsi_overbought: SignalStrength = SignalStrength.NONE
    rsi_divergence: SignalStrength = SignalStrength.NONE
    macd_bearish_cross: SignalStrength = SignalStrength.NONE
    below_vwap: SignalStrength = SignalStrength.NONE
    below_ema9: SignalStrength = SignalStrength.NONE
    
    # Volume signals  
    volume_dying: SignalStrength = SignalStrength.NONE
    volume_spike_down: SignalStrength = SignalStrength.NONE
    
    # Pattern signals
    pattern_failed: SignalStrength = SignalStrength.NONE
    lower_high_formed: SignalStrength = SignalStrength.NONE
    support_broken: SignalStrength = SignalStrength.NONE
    
    # Time signals
    market_closing: SignalStrength = SignalStrength.NONE
    lunch_break: SignalStrength = SignalStrength.NONE
    time_stop: SignalStrength = SignalStrength.NONE
    
    # Context
    timestamp: datetime = field(default_factory=lambda: datetime.now(HK_TZ))
    
    def strongest(self) -> SignalStrength:
        """Return the strongest signal."""
        all_signals = [
            self.stop_loss_hit, self.take_profit_hit, self.trailing_stop_hit,
            self.rsi_overbought, self.rsi_divergence, self.macd_bearish_cross,
            self.below_vwap, self.below_ema9,
            self.volume_dying, self.volume_spike_down,
            self.pattern_failed, self.lower_high_formed, self.support_broken,
            self.market_closing, self.lunch_break, self.time_stop,
        ]
        return max(all_signals, key=lambda s: s.value)
    
    def needs_claude(self) -> bool:
        """Return True if should consult Claude Haiku."""
        strongest = self.strongest()
        return strongest == SignalStrength.MODERATE
    
    def immediate_exit(self) -> bool:
        """Return True if should exit immediately (no Claude needed)."""
        return self.strongest() == SignalStrength.STRONG
    
    def no_action_needed(self) -> bool:
        """Return True if no signals warrant action."""
        return self.strongest().value <= SignalStrength.WEAK.value
    
    def active_signals(self) -> list[str]:
        """Return list of active signal names with strength."""
        signals = []
        
        signal_map = {
            'stop_loss_hit': self.stop_loss_hit,
            'take_profit_hit': self.take_profit_hit,
            'trailing_stop_hit': self.trailing_stop_hit,
            'rsi_overbought': self.rsi_overbought,
            'rsi_divergence': self.rsi_divergence,
            'macd_bearish_cross': self.macd_bearish_cross,
            'below_vwap': self.below_vwap,
            'below_ema9': self.below_ema9,
            'volume_dying': self.volume_dying,
            'volume_spike_down': self.volume_spike_down,
            'pattern_failed': self.pattern_failed,
            'lower_high_formed': self.lower_high_formed,
            'support_broken': self.support_broken,
            'market_closing': self.market_closing,
            'lunch_break': self.lunch_break,
            'time_stop': self.time_stop,
        }
        
        for name, signal in signal_map.items():
            if signal.value > 0:
                signals.append(f"{name}:{signal.name}")
        
        return signals
    
    def summary(self) -> str:
        """Return human-readable summary."""
        active = self.active_signals()
        if not active:
            return "No active signals"
        return f"Active: {', '.join(active)}"
    
    def score(self) -> int:
        """Return numeric score for sorting/prioritization."""
        return sum(s.value for s in [
            self.stop_loss_hit, self.take_profit_hit, self.trailing_stop_hit,
            self.rsi_overbought, self.rsi_divergence, self.macd_bearish_cross,
            self.below_vwap, self.below_ema9,
            self.volume_dying, self.volume_spike_down,
            self.pattern_failed, self.lower_high_formed, self.support_broken,
            self.market_closing, self.lunch_break, self.time_stop,
        ])


def detect_exit_signals(
    position: dict,
    quote: dict,
    technicals: Optional[dict] = None,
    entry_volume: Optional[float] = None,
    entry_time: Optional[datetime] = None,
) -> ExitSignals:
    """
    Detect exit signals based on rules.
    
    This is FREE - no Claude API cost. Only MODERATE signals
    trigger a cheap Haiku consultation.
    
    Args:
        position: {symbol, entry_price, quantity, side, stop_price, target_price}
        quote: {price/last, bid, ask, volume}
        technicals: {rsi, macd, macd_signal, vwap, ema9, ema20}
        entry_volume: Volume at time of entry
        entry_time: Time position was entered
        
    Returns:
        ExitSignals with strength ratings
    """
    signals = ExitSignals()
    technicals = technicals or {}
    
    # Extract current price (handle various field names)
    current_price = float(
        quote.get('price') or 
        quote.get('last') or 
        quote.get('last_price') or 
        0
    )
    entry_price = float(position.get('entry_price', 0) or 0)
    
    if entry_price == 0 or current_price == 0:
        logger.warning(f"Invalid prices: entry={entry_price}, current={current_price}")
        return signals
    
    pnl_pct = (current_price - entry_price) / entry_price
    
    # Get stop/target from position
    stop_price = float(position.get('stop_price', 0) or 0)
    target_price = float(position.get('target_price', 0) or 0)
    
    # =========================================================================
    # P&L SIGNALS (Most important for risk management)
    # =========================================================================
    
    # Stop loss hit
    if stop_price > 0 and current_price <= stop_price:
        signals.stop_loss_hit = SignalStrength.STRONG
        logger.info(f"STOP HIT: {current_price:.2f} <= {stop_price:.2f}")
    elif pnl_pct <= -0.03:
        # Down 3%+ without explicit stop = STRONG exit
        signals.stop_loss_hit = SignalStrength.STRONG
        logger.info(f"STOP LOSS: P&L at {pnl_pct:.2%}")
    elif pnl_pct <= -0.02:
        # Down 2-3% = MODERATE (ask Claude)
        signals.stop_loss_hit = SignalStrength.MODERATE
    elif pnl_pct <= -0.01:
        # Down 1-2% = WEAK (note only)
        signals.stop_loss_hit = SignalStrength.WEAK
    
    # Take profit hit
    if target_price > 0 and current_price >= target_price:
        signals.take_profit_hit = SignalStrength.STRONG
        logger.info(f"TARGET HIT: {current_price:.2f} >= {target_price:.2f}")
    elif pnl_pct >= 0.08:
        # Up 8%+ = STRONG take profit
        signals.take_profit_hit = SignalStrength.STRONG
        logger.info(f"TAKE PROFIT: P&L at {pnl_pct:.2%}")
    elif pnl_pct >= 0.05:
        # Up 5-8% = MODERATE (consider taking)
        signals.take_profit_hit = SignalStrength.MODERATE
    elif pnl_pct >= 0.03:
        # Up 3-5% = WEAK
        signals.take_profit_hit = SignalStrength.WEAK
    
    # Trailing stop (if position was up but now giving back)
    high_since_entry = float(position.get('high_since_entry', current_price) or current_price)
    if high_since_entry > entry_price * 1.03:  # Was up 3%+
        drawdown_from_high = (high_since_entry - current_price) / high_since_entry
        if drawdown_from_high >= 0.03:  # Given back 3% from high
            signals.trailing_stop_hit = SignalStrength.STRONG
            logger.info(f"TRAILING STOP: Drawdown {drawdown_from_high:.2%} from high")
        elif drawdown_from_high >= 0.02:
            signals.trailing_stop_hit = SignalStrength.MODERATE
    
    # =========================================================================
    # TECHNICAL SIGNALS
    # =========================================================================
    
    rsi = technicals.get('rsi')
    if rsi is not None:
        rsi = float(rsi)
        if rsi >= 85:
            signals.rsi_overbought = SignalStrength.STRONG
            logger.info(f"RSI OVERBOUGHT: {rsi:.1f}")
        elif rsi >= 75:
            signals.rsi_overbought = SignalStrength.MODERATE
        elif rsi >= 70:
            signals.rsi_overbought = SignalStrength.WEAK
    
    # MACD bearish cross
    macd = technicals.get('macd')
    macd_signal = technicals.get('macd_signal')
    if macd is not None and macd_signal is not None:
        macd = float(macd)
        macd_signal = float(macd_signal)
        if macd < macd_signal and macd > 0:
            # Bearish cross while still positive = MODERATE
            signals.macd_bearish_cross = SignalStrength.MODERATE
    
    # Below VWAP
    vwap = technicals.get('vwap')
    if vwap is not None and float(vwap) > 0:
        vwap = float(vwap)
        if current_price < vwap * 0.98:
            signals.below_vwap = SignalStrength.MODERATE
        elif current_price < vwap:
            signals.below_vwap = SignalStrength.WEAK
    
    # Below EMA9 (short-term trend)
    ema9 = technicals.get('ema9') or technicals.get('ema_9')
    if ema9 is not None and float(ema9) > 0:
        ema9 = float(ema9)
        if current_price < ema9 * 0.98:
            signals.below_ema9 = SignalStrength.MODERATE
        elif current_price < ema9:
            signals.below_ema9 = SignalStrength.WEAK
    
    # =========================================================================
    # VOLUME SIGNALS
    # =========================================================================
    
    current_volume = float(quote.get('volume', 0) or 0)
    if entry_volume and entry_volume > 0 and current_volume > 0:
        volume_ratio = current_volume / entry_volume
        
        if volume_ratio < 0.25:
            # Volume collapsed to <25% = STRONG exit signal
            signals.volume_dying = SignalStrength.STRONG
            logger.info(f"VOLUME DYING: {volume_ratio:.2%} of entry")
        elif volume_ratio < 0.40:
            signals.volume_dying = SignalStrength.MODERATE
        elif volume_ratio < 0.60:
            signals.volume_dying = SignalStrength.WEAK
    
    # =========================================================================
    # TIME SIGNALS (HKEX specific)
    # =========================================================================
    
    now = datetime.now(HK_TZ)
    now_time = now.time()
    
    # Market closing (16:00 HKT)
    market_close = time(16, 0)
    if now_time >= time(15, 50):
        signals.market_closing = SignalStrength.STRONG
        logger.info("MARKET CLOSING: < 10 min remaining")
    elif now_time >= time(15, 30):
        signals.market_closing = SignalStrength.MODERATE
    elif now_time >= time(15, 0):
        signals.market_closing = SignalStrength.WEAK
    
    # Lunch break approaching (12:00-13:00 HKT)
    if time(11, 50) <= now_time < time(12, 0):
        signals.lunch_break = SignalStrength.STRONG
        logger.info("LUNCH BREAK: Close before 12:00")
    elif time(11, 30) <= now_time < time(11, 50):
        signals.lunch_break = SignalStrength.MODERATE
    
    # Time stop (position held too long without movement)
    if entry_time:
        hold_duration = now - entry_time
        hold_minutes = hold_duration.total_seconds() / 60
        
        # If flat (< 1% gain) after extended time
        if abs(pnl_pct) < 0.01:
            if hold_minutes > 120:  # > 2 hours flat
                signals.time_stop = SignalStrength.STRONG
                logger.info(f"TIME STOP: Flat for {hold_minutes:.0f} min")
            elif hold_minutes > 90:
                signals.time_stop = SignalStrength.MODERATE
            elif hold_minutes > 60:
                signals.time_stop = SignalStrength.WEAK
    
    logger.debug(f"Signals detected: {signals.summary()}")
    return signals


def combine_signals_for_decision(signals: ExitSignals) -> dict:
    """
    Combine signals into a decision recommendation.
    
    Args:
        signals: ExitSignals from detect_exit_signals()
        
    Returns:
        {
            'recommendation': 'EXIT' | 'HOLD' | 'ASK_HAIKU',
            'confidence': float 0-1,
            'reasons': list[str],
            'priority': 'high' | 'normal' | 'low'
        }
    """
    active = signals.active_signals()
    strongest = signals.strongest()
    score = signals.score()
    
    if strongest == SignalStrength.STRONG:
        return {
            'recommendation': 'EXIT',
            'confidence': 0.95,
            'reasons': [s for s in active if 'STRONG' in s],
            'priority': 'high',
        }
    
    elif strongest == SignalStrength.MODERATE:
        # Count moderate signals
        moderate_count = sum(1 for s in active if 'MODERATE' in s)
        
        if moderate_count >= 3 or score >= 6:
            # Multiple moderate signals = lean toward exit
            return {
                'recommendation': 'EXIT',
                'confidence': 0.75,
                'reasons': active,
                'priority': 'normal',
            }
        else:
            # Few moderate signals = ask Claude
            return {
                'recommendation': 'ASK_HAIKU',
                'confidence': 0.50,
                'reasons': active,
                'priority': 'normal',
            }
    
    else:
        return {
            'recommendation': 'HOLD',
            'confidence': 0.85,
            'reasons': active if active else ['No concerning signals'],
            'priority': 'low',
        }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    """Test signal detection."""
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Testing Exit Signal Detection v1.1.0")
    print("=" * 60)
    
    # Test case 1: Stop loss hit
    print("\nTest 1: Position down 3% (should EXIT immediately)")
    position = {'entry_price': 100, 'symbol': '0700'}
    quote = {'price': 97, 'volume': 50000}
    technicals = {'rsi': 45}
    
    signals = detect_exit_signals(position, quote, technicals, 100000)
    decision = combine_signals_for_decision(signals)
    print(f"  Signals: {signals.active_signals()}")
    print(f"  Decision: {decision['recommendation']} (confidence: {decision['confidence']:.0%})")
    
    # Test case 2: Take profit
    print("\nTest 2: Position up 8% (should EXIT - take profit)")
    position = {'entry_price': 100, 'symbol': '0700'}
    quote = {'price': 108, 'volume': 80000}
    technicals = {'rsi': 72}
    
    signals = detect_exit_signals(position, quote, technicals, 100000)
    decision = combine_signals_for_decision(signals)
    print(f"  Signals: {signals.active_signals()}")
    print(f"  Decision: {decision['recommendation']} (confidence: {decision['confidence']:.0%})")
    
    # Test case 3: RSI overbought + volume dying
    print("\nTest 3: RSI overbought + volume dying (should ASK_HAIKU)")
    position = {'entry_price': 100, 'symbol': '0700'}
    quote = {'price': 103, 'volume': 30000}  # 30% of entry volume
    technicals = {'rsi': 78}
    
    signals = detect_exit_signals(position, quote, technicals, 100000)
    decision = combine_signals_for_decision(signals)
    print(f"  Signals: {signals.active_signals()}")
    print(f"  Decision: {decision['recommendation']} (confidence: {decision['confidence']:.0%})")
    
    # Test case 4: Healthy position
    print("\nTest 4: Healthy position (should HOLD)")
    position = {'entry_price': 100, 'symbol': '0700'}
    quote = {'price': 102, 'volume': 120000}
    technicals = {'rsi': 58}
    
    signals = detect_exit_signals(position, quote, technicals, 100000)
    decision = combine_signals_for_decision(signals)
    print(f"  Signals: {signals.active_signals()}")
    print(f"  Decision: {decision['recommendation']} (confidence: {decision['confidence']:.0%})")
    
    print("\n" + "=" * 60)
    print("Tests complete")
