"""
Name of Application: Catalyst Trading System
Name of file: position_monitor.py
Version: 1.1.0
Last Updated: 2026-01-06
Purpose: Trade-triggered position monitoring until exit

REVISION HISTORY:
v1.1.0 (2026-01-06) - Production deployment
- Integrated with moomoo.py client
- Fixed async/sync compatibility
- Added high watermark tracking for trailing stops
- Better error recovery
- HKEX-specific market hours handling

v1.0.0 (2025-01-01) - Initial implementation

Description:
This module monitors a position from entry until exit. It runs in the
same process as the entry decision - no separate service or cron needed.

Cost Model:
- Signal detection: FREE (rules-based)
- Haiku consultation: ~$0.05/call (only for uncertain signals)
- Big Bro notifications: FREE (DB writes only)
- Expected per-trade cost: ~$0.05-0.15 for monitoring

Architecture:
- Called after execute_trade() for BUY orders
- Runs continuous loop checking every 5 minutes
- Exits when: position closed, market closed, or error
- Agent-managed stops as primary protection
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Any, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")

# Configuration
CHECK_INTERVAL_SECONDS = 300  # 5 minutes
MAX_HAIKU_CALLS_PER_POSITION = 10  # Cost limit (~$0.50 max)
HAIKU_MODEL = "claude-3-haiku-20240307"


class PositionMonitor:
    """
    Monitors a position until exit.
    
    Runs in the same process as entry - no separate service needed.
    Uses rules-based signal detection (free) and only consults
    Haiku for uncertain decisions (~$0.05/call).
    """
    
    def __init__(
        self,
        broker: Any,
        market_data: Any,
        anthropic_client: Any,
        safety_validator: Any,
    ):
        """
        Initialize position monitor.
        
        Args:
            broker: MoomooClient instance
            market_data: MarketData instance
            anthropic_client: Anthropic client (for Haiku)
            safety_validator: SafetyValidator instance
        """
        self.broker = broker
        self.market_data = market_data
        self.anthropic = anthropic_client
        self.safety = safety_validator
        
        # Tracking
        self.total_checks = 0
        self.haiku_calls = 0
        self.high_watermark = 0.0  # Highest price since entry
    
    async def monitor_until_exit(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_price: float,
        target_price: float,
        entry_reason: str = "",
        entry_volume: Optional[float] = None,
    ) -> dict:
        """
        Monitor position until exit condition met.
        
        This runs in the same process as entry - no separate cron needed.
        Loop continues until position is closed or market closes.
        
        Args:
            symbol: HKEX symbol (e.g., '1024')
            entry_price: Price at entry
            quantity: Shares held
            stop_price: Stop loss price
            target_price: Take profit price
            entry_reason: Why we entered (for logging)
            entry_volume: Market volume at entry time
            
        Returns:
            {
                'exit_price': float or None,
                'exit_reason': str,
                'pnl': float,
                'pnl_pct': float,
                'total_checks': int,
                'haiku_calls': int,
            }
        """
        # Import here to avoid circular imports
        from signals import detect_exit_signals, combine_signals_for_decision, SignalStrength
        from consciousness_notify import (
            notify_monitor_started,
            notify_monitor_ended,
            notify_high_severity_signal,
            notify_haiku_decision,
            notify_exit_executed,
            notify_error,
        )
        
        logger.info(f"Starting position monitor for {symbol}")
        
        # Reset counters
        self.total_checks = 0
        self.haiku_calls = 0
        self.high_watermark = entry_price
        
        entry_time = datetime.now(HK_TZ)
        
        # Position state
        position = {
            'symbol': symbol,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_price': stop_price,
            'target_price': target_price,
            'entry_reason': entry_reason,
            'entry_time': entry_time,
            'side': 'LONG',
            'current_price': entry_price,
            'pnl_pct': 0.0,
            'high_since_entry': entry_price,
        }
        
        # Notify big_bro that monitoring started
        await notify_monitor_started(symbol, entry_price, quantity)
        
        exit_result = {
            'exit_price': None,
            'exit_reason': 'Unknown',
            'pnl': 0.0,
            'pnl_pct': 0.0,
            'total_checks': 0,
            'haiku_calls': 0,
        }
        
        try:
            while True:
                self.total_checks += 1
                
                # === CHECK 1: Market still open? ===
                is_open, market_status = self._check_market_hours()
                if not is_open:
                    logger.info(f"Market closed: {market_status}")
                    exit_result['exit_reason'] = f"Market closed: {market_status}"
                    break
                
                # === CHECK 2: Position still exists? ===
                position_exists = self._check_position_exists(symbol)
                if not position_exists:
                    logger.info(f"Position {symbol} no longer exists")
                    exit_result['exit_reason'] = "Position closed externally"
                    break
                
                # === CHECK 3: Get current market state ===
                quote = self._get_quote(symbol)
                if not quote:
                    logger.warning(f"Failed to get quote for {symbol}, waiting...")
                    await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                    continue
                
                technicals = self._get_technicals(symbol)
                
                # Update position state
                current_price = float(
                    quote.get('last') or 
                    quote.get('price') or 
                    quote.get('last_price') or 
                    entry_price
                )
                position['current_price'] = current_price
                position['pnl_pct'] = (current_price - entry_price) / entry_price
                
                # Track high watermark for trailing stop
                if current_price > self.high_watermark:
                    self.high_watermark = current_price
                    position['high_since_entry'] = current_price
                
                # === CHECK 4: Detect exit signals (FREE - rules based) ===
                signals = detect_exit_signals(
                    position=position,
                    quote=quote,
                    technicals=technicals,
                    entry_volume=entry_volume,
                    entry_time=entry_time,
                )
                
                # === DECISION LOGIC ===
                decision = combine_signals_for_decision(signals)
                
                if decision['recommendation'] == 'EXIT':
                    if signals.immediate_exit():
                        # STRONG signal - exit immediately, no Claude needed
                        exit_reason = f"STRONG: {', '.join(decision['reasons'])}"
                    else:
                        # Multiple moderate signals
                        exit_reason = f"MODERATE (multiple): {', '.join(decision['reasons'])}"
                    
                    logger.info(f"Exit triggered: {exit_reason}")
                    
                    exit_price = await self._execute_exit(symbol, quantity, exit_reason)
                    
                    if exit_price:
                        pnl = (exit_price - entry_price) * quantity
                        pnl_pct = (exit_price - entry_price) / entry_price
                        
                        await notify_exit_executed(
                            position=position,
                            exit_reason=exit_reason,
                            exit_price=exit_price,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                        )
                        
                        exit_result = {
                            'exit_price': exit_price,
                            'exit_reason': exit_reason,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'total_checks': self.total_checks,
                            'haiku_calls': self.haiku_calls,
                        }
                        break
                    else:
                        logger.error(f"Exit execution failed for {symbol}")
                        await notify_error(symbol, "Exit execution failed", "Continuing monitoring")
                
                elif decision['recommendation'] == 'ASK_HAIKU':
                    # Uncertain - consult Haiku if budget allows
                    if self.haiku_calls < MAX_HAIKU_CALLS_PER_POSITION:
                        haiku_decision = await self._consult_haiku(
                            position=position,
                            signals=signals,
                            quote=quote,
                            technicals=technicals,
                        )
                        
                        if haiku_decision.get('should_exit', False):
                            exit_reason = f"HAIKU: {haiku_decision.get('reason', 'AI recommended exit')}"
                            logger.info(f"Haiku recommends exit: {exit_reason}")
                            
                            exit_price = await self._execute_exit(symbol, quantity, exit_reason)
                            
                            if exit_price:
                                pnl = (exit_price - entry_price) * quantity
                                pnl_pct = (exit_price - entry_price) / entry_price
                                
                                await notify_exit_executed(
                                    position=position,
                                    exit_reason=exit_reason,
                                    exit_price=exit_price,
                                    pnl=pnl,
                                    pnl_pct=pnl_pct,
                                )
                                
                                exit_result = {
                                    'exit_price': exit_price,
                                    'exit_reason': exit_reason,
                                    'pnl': pnl,
                                    'pnl_pct': pnl_pct,
                                    'total_checks': self.total_checks,
                                    'haiku_calls': self.haiku_calls,
                                }
                                break
                    else:
                        logger.warning(f"Haiku call limit reached ({MAX_HAIKU_CALLS_PER_POSITION})")
                        # Fall back to rules-only
                
                # === Notify high severity signals (for visibility) ===
                if signals.strongest().value >= SignalStrength.MODERATE.value:
                    await notify_high_severity_signal(
                        position=position,
                        signals=signals,
                        details=f"Decision: {decision['recommendation']}",
                    )
                
                # === WAIT FOR NEXT CHECK ===
                logger.debug(
                    f"Check {self.total_checks}: {symbol} @ ${current_price:.2f}, "
                    f"P&L: {position['pnl_pct']:.2%}"
                )
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                
        except asyncio.CancelledError:
            logger.info(f"Monitor cancelled for {symbol}")
            exit_result['exit_reason'] = "Monitor cancelled"
            
        except Exception as e:
            logger.error(f"Monitor error for {symbol}: {e}", exc_info=True)
            exit_result['exit_reason'] = f"Monitor error: {e}"
            await notify_error(symbol, str(e), "Check logs for details")
        
        finally:
            # Notify monitoring ended
            await notify_monitor_ended(
                symbol=symbol,
                reason=exit_result['exit_reason'],
                total_checks=self.total_checks,
                haiku_calls=self.haiku_calls,
            )
            
            logger.info(
                f"Monitor ended for {symbol}: {exit_result['exit_reason']} "
                f"(checks: {self.total_checks}, haiku: {self.haiku_calls})"
            )
        
        return exit_result
    
    def _check_market_hours(self) -> tuple[bool, str]:
        """Check if HKEX is currently open."""
        now = datetime.now(HK_TZ)
        now_time = now.time()
        
        # HKEX hours
        morning_open = time(9, 30)
        morning_close = time(12, 0)
        afternoon_open = time(13, 0)
        afternoon_close = time(16, 0)
        
        # Check if weekend
        if now.weekday() >= 5:
            return False, "Weekend"
        
        # Check market hours
        if morning_open <= now_time < morning_close:
            return True, "Morning session"
        elif afternoon_open <= now_time < afternoon_close:
            return True, "Afternoon session"
        elif morning_close <= now_time < afternoon_open:
            return False, "Lunch break"
        else:
            return False, "Outside market hours"
    
    def _check_position_exists(self, symbol: str) -> bool:
        """Check if position still exists in portfolio."""
        try:
            positions = self.broker.get_positions()
            
            for pos in positions:
                pos_symbol = pos.symbol if hasattr(pos, 'symbol') else pos.get('symbol', '')
                pos_symbol = str(pos_symbol).replace('.HK', '').replace('HK.', '').lstrip('0')
                check_symbol = symbol.replace('.HK', '').replace('HK.', '').lstrip('0')
                
                if pos_symbol == check_symbol:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking position: {e}")
            return True  # Assume exists on error (safer)
    
    def _get_quote(self, symbol: str) -> Optional[dict]:
        """Get current quote for symbol."""
        try:
            if self.market_data:
                return self.market_data.get_quote(symbol)
            elif self.broker:
                quote = self.broker.get_quote(symbol)
                return quote
            return None
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return None
    
    def _get_technicals(self, symbol: str) -> dict:
        """Get technical indicators for symbol."""
        try:
            if self.market_data:
                return self.market_data.get_technicals(symbol)
            return {}
        except Exception as e:
            logger.debug(f"Error getting technicals: {e}")
            return {}
    
    async def _execute_exit(
        self,
        symbol: str,
        quantity: int,
        reason: str,
    ) -> Optional[float]:
        """Execute exit order."""
        try:
            result = self.broker.close_position(symbol, reason)
            
            # Handle OrderResult dataclass
            if hasattr(result, 'status'):
                status = result.status
                filled_price = result.filled_price
            else:
                status = result.get('status', '')
                filled_price = result.get('filled_price') or result.get('fill_price')
            
            if status in ['FILLED', 'filled', 'SUBMITTED', 'submitted', 'success']:
                logger.info(f"Exit executed: {symbol} @ {filled_price}")
                return filled_price
            else:
                logger.error(f"Exit failed: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Exit execution error: {e}")
            return None
    
    async def _consult_haiku(
        self,
        position: dict,
        signals: Any,
        quote: dict,
        technicals: dict,
    ) -> dict:
        """
        Consult Claude Haiku for uncertain exit decision.
        
        Cost: ~$0.05 per call
        """
        from consciousness_notify import notify_haiku_decision
        
        self.haiku_calls += 1
        
        symbol = position['symbol']
        entry_price = position['entry_price']
        current_price = position['current_price']
        pnl_pct = position['pnl_pct']
        
        prompt = f"""You are a trading assistant. Analyze this position and decide: EXIT or HOLD?

POSITION:
- Symbol: {symbol}
- Entry: ${entry_price:.2f}
- Current: ${current_price:.2f}
- P&L: {pnl_pct:.2%}
- High since entry: ${position.get('high_since_entry', current_price):.2f}

SIGNALS DETECTED:
{signals.summary() if hasattr(signals, 'summary') else str(signals)}

TECHNICALS:
- RSI: {technicals.get('rsi', 'N/A')}
- MACD: {technicals.get('macd', 'N/A')}

QUESTION: Should we EXIT this position now, or HOLD?

Respond with EXACTLY this format:
DECISION: EXIT or HOLD
REASON: [one sentence explanation]
CONFIDENCE: [0-100]%"""

        try:
            response = self.anthropic.messages.create(
                model=HAIKU_MODEL,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            
            response_text = response.content[0].text.strip()
            logger.info(f"Haiku response: {response_text}")
            
            # Parse response
            should_exit = 'EXIT' in response_text.upper().split('\n')[0]
            
            # Extract reason
            reason = "AI analysis"
            for line in response_text.split('\n'):
                if line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()
                    break
            
            # Notify big_bro
            await notify_haiku_decision(
                symbol=symbol,
                question=f"Exit {symbol}? P&L: {pnl_pct:.2%}",
                decision="EXIT" if should_exit else "HOLD",
                reasoning=reason,
                cost=0.05,
            )
            
            return {
                'should_exit': should_exit,
                'reason': reason,
                'raw_response': response_text,
            }
            
        except Exception as e:
            logger.error(f"Haiku consultation failed: {e}")
            return {
                'should_exit': False,
                'reason': f"Haiku error: {e}",
                'raw_response': None,
            }


# =============================================================================
# ENTRY POINT - Called from tool_executor.py
# =============================================================================

async def start_position_monitor(
    broker: Any,
    market_data: Any,
    anthropic_client: Any,
    safety_validator: Any,
    symbol: str,
    entry_price: float,
    quantity: int,
    stop_price: float,
    target_price: float,
    entry_reason: str = "",
    entry_volume: Optional[float] = None,
) -> dict:
    """
    Start monitoring a position.
    
    Call this after execute_trade() for BUY orders.
    
    Args:
        broker: MoomooClient
        market_data: MarketData
        anthropic_client: Anthropic client
        safety_validator: SafetyValidator
        symbol: HKEX symbol
        entry_price: Fill price
        quantity: Shares purchased
        stop_price: Stop loss price
        target_price: Take profit price
        entry_reason: Why we entered
        entry_volume: Volume at entry
        
    Returns:
        Exit result dict
    """
    from consciousness_notify import notify_entry_executed
    
    # Notify entry
    await notify_entry_executed(
        symbol=symbol,
        side='BUY',
        quantity=quantity,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        entry_reason=entry_reason,
    )
    
    # Create monitor and run
    monitor = PositionMonitor(
        broker=broker,
        market_data=market_data,
        anthropic_client=anthropic_client,
        safety_validator=safety_validator,
    )
    
    result = await monitor.monitor_until_exit(
        symbol=symbol,
        entry_price=entry_price,
        quantity=quantity,
        stop_price=stop_price,
        target_price=target_price,
        entry_reason=entry_reason,
        entry_volume=entry_volume,
    )
    
    return result


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    """Test position monitor (dry run)."""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Position Monitor v1.1.0")
    print("=" * 60)
    print("\nThis module is designed to be called from tool_executor.py")
    print("after a successful BUY trade execution.")
    print("\nUsage:")
    print("  from position_monitor import start_position_monitor")
    print("  result = await start_position_monitor(...)")
    print("\nCost model:")
    print("  - Signal detection: FREE (rules-based)")
    print("  - Haiku consultation: ~$0.05/call")
    print(f"  - Max Haiku calls per position: {MAX_HAIKU_CALLS_PER_POSITION}")
    print(f"  - Check interval: {CHECK_INTERVAL_SECONDS} seconds")
    print("\nSignal thresholds:")
    print("  - Stop loss: -3% STRONG, -2% MODERATE, -1% WEAK")
    print("  - Take profit: +8% STRONG, +5% MODERATE, +3% WEAK")
    print("  - RSI overbought: 85 STRONG, 75 MODERATE, 70 WEAK")
    print("  - Volume dying: <25% STRONG, <40% MODERATE, <60% WEAK")
    print("  - Market close: <10min STRONG, <30min MODERATE")
    print("  - Lunch break: 11:50 STRONG, 11:30 MODERATE")
