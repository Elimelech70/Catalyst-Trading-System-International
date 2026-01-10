"""
Name of Application: Catalyst Trading System
Name of file: position_monitor.py
Version: 2.0.0
Last Updated: 2026-01-10
Purpose: Trade-triggered position monitoring with status tracking

REVISION HISTORY:
v2.0.0 (2026-01-10) - Status table integration
- Records all state to position_monitor_status table
- Uses signals.py v2.0.0 for pattern-based detection
- Tracks high watermark, signals, recommendations
- Haiku consultation for uncertain decisions
- Health monitoring via v_monitor_health view

v1.1.0 (2026-01-06) - Production deployment
v1.0.0 (2025-01-01) - Initial implementation

Description:
Monitors a position from entry until exit. Runs in the same process as
the entry decision - no separate service or cron needed. Updates
position_monitor_status table for dashboard visibility.

Cost Model:
- Signal detection: FREE (rules-based via signals.py)
- Haiku consultation: ~$0.05/call (only for REVIEW recommendations)
- Expected per-trade cost: ~$0.05-0.15 for monitoring

Architecture:
- Called after execute_trade() for BUY orders
- Runs continuous loop checking every 5 minutes
- Updates position_monitor_status on every check
- Exits when: position closed, market closed, or error
"""

import asyncio
import logging
import os
from datetime import datetime, time
from typing import Any, Optional, Dict
from zoneinfo import ZoneInfo

import asyncpg

# Import our signal detection module
from signals import (
    analyze_position,
    SignalAnalysis,
    SignalThresholds,
    get_vwap_position,
    get_ema_position,
    get_macd_signal_str,
    DEFAULT_THRESHOLDS
)

logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")

# Configuration
CHECK_INTERVAL_SECONDS = 300  # 5 minutes
MAX_HAIKU_CALLS_PER_POSITION = 10  # Cost limit (~$0.50 max)
HAIKU_MODEL = "claude-3-haiku-20240307"

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("INTL_DATABASE_URL") or os.getenv("DEV_DATABASE_URL")


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

async def get_db_connection() -> asyncpg.Connection:
    """Get database connection."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return await asyncpg.connect(DATABASE_URL)


async def create_monitor_status(
    conn: asyncpg.Connection,
    position_id: int,
    symbol: str,
    entry_price: float
) -> int:
    """Create initial monitor status record."""
    monitor_id = await conn.fetchval("""
        INSERT INTO position_monitor_status (
            position_id,
            symbol,
            status,
            started_at,
            high_watermark,
            last_price,
            metadata
        ) VALUES ($1, $2, 'starting', NOW(), $3, $3, '{}')
        ON CONFLICT (position_id) DO UPDATE SET
            status = 'starting',
            started_at = NOW(),
            consecutive_errors = 0,
            last_error = NULL
        RETURNING monitor_id
    """, position_id, symbol, entry_price)
    
    return monitor_id


async def update_monitor_status(
    conn: asyncpg.Connection,
    monitor_id: int,
    status: str,
    last_price: float,
    high_watermark: float,
    pnl_pct: float,
    analysis: SignalAnalysis,
    technicals: Dict[str, Any],
    haiku_calls: int = 0,
    estimated_cost: float = 0,
    last_haiku_recommendation: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """Update monitor status with current state."""
    
    # Get technical positions as strings
    vwap_position = get_vwap_position(last_price, technicals.get('vwap'))
    ema_position = get_ema_position(last_price, technicals.get('ema20'))
    macd_signal = technicals.get('macd_signal', 'unknown')
    
    await conn.execute("""
        UPDATE position_monitor_status SET
            status = $2,
            last_check_at = NOW(),
            next_check_at = NOW() + INTERVAL '5 minutes',
            checks_completed = checks_completed + 1,
            last_price = $3,
            high_watermark = GREATEST(high_watermark, $4),
            current_pnl_pct = $5,
            last_rsi = $6,
            last_macd_signal = $7,
            last_vwap_position = $8,
            last_ema20_position = $9,
            hold_signals = $10,
            exit_signals = $11,
            signal_strength = $12,
            recommendation = $13,
            recommendation_reason = $14,
            haiku_calls = $15,
            estimated_cost = $16,
            last_haiku_recommendation = COALESCE($17, last_haiku_recommendation),
            last_error = $18,
            error_count = CASE WHEN $18 IS NOT NULL THEN error_count + 1 ELSE error_count END,
            consecutive_errors = CASE WHEN $18 IS NOT NULL THEN consecutive_errors + 1 ELSE 0 END,
            updated_at = NOW()
        WHERE monitor_id = $1
    """,
        monitor_id,
        status,
        last_price,
        high_watermark,
        pnl_pct,
        technicals.get('rsi'),
        macd_signal,
        vwap_position,
        ema_position,
        analysis.hold_signal_names,
        analysis.exit_signal_names,
        analysis.signal_strength,
        analysis.recommendation,
        analysis.reason,
        haiku_calls,
        estimated_cost,
        last_haiku_recommendation,
        error
    )


async def mark_monitor_stopped(
    conn: asyncpg.Connection,
    monitor_id: int,
    reason: str
) -> None:
    """Mark monitor as stopped."""
    await conn.execute("""
        UPDATE position_monitor_status SET
            status = 'stopped',
            recommendation_reason = $2,
            updated_at = NOW()
        WHERE monitor_id = $1
    """, monitor_id, reason)


async def mark_monitor_sleeping(
    conn: asyncpg.Connection,
    monitor_id: int,
    reason: str
) -> None:
    """Mark monitor as sleeping (off-hours)."""
    await conn.execute("""
        UPDATE position_monitor_status SET
            status = 'sleeping',
            recommendation_reason = $2,
            updated_at = NOW()
        WHERE monitor_id = $1
    """, monitor_id, reason)


async def update_position_high_watermark(
    conn: asyncpg.Connection,
    position_id: int,
    high_watermark: float
) -> None:
    """Update position's high watermark in positions table."""
    await conn.execute("""
        UPDATE positions SET
            high_watermark = GREATEST(COALESCE(high_watermark, 0), $2),
            updated_at = NOW()
        WHERE position_id = $1
    """, position_id, high_watermark)


# =============================================================================
# MARKET HOURS CHECK
# =============================================================================

def is_hkex_market_open() -> bool:
    """Check if HKEX is currently open."""
    now = datetime.now(HK_TZ)
    
    # Weekend check
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    current_time = now.time()
    
    # Morning session: 09:30 - 12:00
    morning_open = time(9, 30)
    morning_close = time(12, 0)
    
    # Afternoon session: 13:00 - 16:00
    afternoon_open = time(13, 0)
    afternoon_close = time(16, 0)
    
    if morning_open <= current_time < morning_close:
        return True
    if afternoon_open <= current_time < afternoon_close:
        return True
    
    return False


def get_market_status() -> str:
    """Get human-readable market status."""
    now = datetime.now(HK_TZ)
    
    if now.weekday() >= 5:
        return "closed_weekend"
    
    current_time = now.time()
    
    if current_time < time(9, 30):
        return "pre_market"
    elif time(9, 30) <= current_time < time(12, 0):
        return "morning_session"
    elif time(12, 0) <= current_time < time(13, 0):
        return "lunch_break"
    elif time(13, 0) <= current_time < time(16, 0):
        return "afternoon_session"
    else:
        return "after_hours"


# =============================================================================
# POSITION MONITOR CLASS
# =============================================================================

class PositionMonitor:
    """
    Monitors a position until exit.
    
    Runs in the same process as entry - no separate service needed.
    Uses signals.py for pattern-based detection and only consults
    Haiku for uncertain decisions (~$0.05/call).
    """
    
    def __init__(
        self,
        broker: Any,
        market_data: Any,
        anthropic_client: Any,
        thresholds: SignalThresholds = DEFAULT_THRESHOLDS
    ):
        """
        Initialize position monitor.
        
        Args:
            broker: MoomooClient instance for quotes and orders
            market_data: MarketData instance for technicals
            anthropic_client: Anthropic client for Haiku calls
            thresholds: Signal thresholds configuration
        """
        self.broker = broker
        self.market_data = market_data
        self.anthropic = anthropic_client
        self.thresholds = thresholds
        
        # Tracking
        self.monitor_id: Optional[int] = None
        self.total_checks = 0
        self.haiku_calls = 0
        self.estimated_cost = 0.0
        self.high_watermark = 0.0
    
    async def monitor_until_exit(
        self,
        position_id: int,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_price: float,
        target_price: float,
        entry_reason: str = "",
        entry_volume: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Monitor position until exit condition met.
        
        Args:
            position_id: Database position ID
            symbol: HKEX symbol (e.g., '1024')
            entry_price: Entry fill price
            quantity: Number of shares
            stop_price: Stop loss price
            target_price: Take profit price
            entry_reason: Why we entered
            entry_volume: Volume at entry time
            
        Returns:
            Exit result dict with price, reason, P&L
        """
        logger.info(f"Starting position monitor for {symbol} (position_id={position_id})")
        
        self.high_watermark = entry_price
        exit_result = None
        
        # Get database connection
        conn = await get_db_connection()
        
        try:
            # Create monitor status record
            self.monitor_id = await create_monitor_status(
                conn, position_id, symbol, entry_price
            )
            logger.info(f"Created monitor status record: {self.monitor_id}")
            
            # Main monitoring loop
            while True:
                self.total_checks += 1
                
                try:
                    # Check market hours
                    market_status = get_market_status()
                    
                    if market_status in ('closed_weekend', 'after_hours'):
                        logger.info(f"Market closed ({market_status}), sleeping monitor")
                        await mark_monitor_sleeping(conn, self.monitor_id, f"Market {market_status}")
                        # Sleep longer during off-hours
                        await asyncio.sleep(3600)  # 1 hour
                        continue
                    
                    if market_status == 'lunch_break':
                        logger.info("Lunch break, sleeping monitor")
                        await mark_monitor_sleeping(conn, self.monitor_id, "Lunch break")
                        await asyncio.sleep(300)  # 5 minutes
                        continue
                    
                    if market_status == 'pre_market':
                        logger.info("Pre-market, sleeping monitor")
                        await mark_monitor_sleeping(conn, self.monitor_id, "Pre-market")
                        await asyncio.sleep(300)
                        continue
                    
                    # Get current quote
                    quote = self._get_quote(symbol)
                    if not quote or not quote.get('price'):
                        logger.warning(f"No quote for {symbol}, skipping check")
                        await asyncio.sleep(60)
                        continue
                    
                    current_price = float(quote['price'])
                    
                    # Update high watermark
                    if current_price > self.high_watermark:
                        self.high_watermark = current_price
                        await update_position_high_watermark(conn, position_id, self.high_watermark)
                    
                    # Calculate P&L
                    pnl_pct = (current_price - entry_price) / entry_price
                    
                    # Get technicals
                    technicals = self._get_technicals(symbol)
                    
                    # Build position dict for analysis
                    position = {
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'pnl_pct': pnl_pct,
                        'high_watermark': self.high_watermark,
                        'entry_time': datetime.now(HK_TZ),  # Approximation
                    }
                    
                    # Analyze signals
                    analysis = analyze_position(
                        position=position,
                        quote=quote,
                        technicals=technicals,
                        entry_volume=entry_volume,
                        thresholds=self.thresholds
                    )
                    
                    logger.info(f"[{symbol}] Check #{self.total_checks}: {analysis.summary()}")
                    
                    # Update monitor status
                    await update_monitor_status(
                        conn=conn,
                        monitor_id=self.monitor_id,
                        status='running',
                        last_price=current_price,
                        high_watermark=self.high_watermark,
                        pnl_pct=pnl_pct,
                        analysis=analysis,
                        technicals=technicals,
                        haiku_calls=self.haiku_calls,
                        estimated_cost=self.estimated_cost
                    )
                    
                    # Decision based on recommendation
                    recommendation = analysis.recommendation
                    
                    if recommendation == "EXIT":
                        # Strong exit signal - exit immediately
                        exit_reason = analysis.reason
                        logger.info(f"[{symbol}] EXITING: {exit_reason}")
                        
                        exit_price = await self._execute_exit(symbol, quantity, exit_reason)
                        
                        if exit_price:
                            pnl = (exit_price - entry_price) * quantity
                            pnl_pct_final = (exit_price - entry_price) / entry_price
                            
                            exit_result = {
                                'exit_price': exit_price,
                                'exit_reason': exit_reason,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct_final,
                                'total_checks': self.total_checks,
                                'haiku_calls': self.haiku_calls,
                                'estimated_cost': self.estimated_cost
                            }
                            
                            await mark_monitor_stopped(conn, self.monitor_id, f"Exited: {exit_reason}")
                            break
                    
                    elif recommendation == "REVIEW":
                        # Uncertain - consult Haiku
                        if self.haiku_calls < MAX_HAIKU_CALLS_PER_POSITION:
                            haiku_decision = await self._consult_haiku(
                                position=position,
                                analysis=analysis,
                                technicals=technicals,
                                entry_reason=entry_reason
                            )
                            
                            if haiku_decision.get('should_exit'):
                                exit_reason = f"Haiku: {haiku_decision.get('reason', 'AI decision')}"
                                logger.info(f"[{symbol}] HAIKU EXIT: {exit_reason}")
                                
                                exit_price = await self._execute_exit(symbol, quantity, exit_reason)
                                
                                if exit_price:
                                    pnl = (exit_price - entry_price) * quantity
                                    pnl_pct_final = (exit_price - entry_price) / entry_price
                                    
                                    exit_result = {
                                        'exit_price': exit_price,
                                        'exit_reason': exit_reason,
                                        'pnl': pnl,
                                        'pnl_pct': pnl_pct_final,
                                        'total_checks': self.total_checks,
                                        'haiku_calls': self.haiku_calls,
                                        'estimated_cost': self.estimated_cost
                                    }
                                    
                                    await mark_monitor_stopped(conn, self.monitor_id, f"Exited: {exit_reason}")
                                    break
                            else:
                                # Haiku said hold - update status
                                await update_monitor_status(
                                    conn=conn,
                                    monitor_id=self.monitor_id,
                                    status='running',
                                    last_price=current_price,
                                    high_watermark=self.high_watermark,
                                    pnl_pct=pnl_pct,
                                    analysis=analysis,
                                    technicals=technicals,
                                    haiku_calls=self.haiku_calls,
                                    estimated_cost=self.estimated_cost,
                                    last_haiku_recommendation=f"HOLD: {haiku_decision.get('reason', 'Continue')}"
                                )
                        else:
                            logger.warning(f"[{symbol}] Haiku limit reached ({MAX_HAIKU_CALLS_PER_POSITION})")
                    
                    # HOLD - continue monitoring
                    # Sleep until next check
                    await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                    
                except Exception as e:
                    logger.error(f"[{symbol}] Check error: {e}")
                    
                    # Update status with error
                    try:
                        await update_monitor_status(
                            conn=conn,
                            monitor_id=self.monitor_id,
                            status='running',
                            last_price=self.high_watermark,
                            high_watermark=self.high_watermark,
                            pnl_pct=0,
                            analysis=SignalAnalysis(),
                            technicals={},
                            haiku_calls=self.haiku_calls,
                            estimated_cost=self.estimated_cost,
                            error=str(e)[:500]
                        )
                    except:
                        pass
                    
                    # Continue monitoring despite error
                    await asyncio.sleep(60)
                    
        except Exception as e:
            logger.error(f"[{symbol}] Monitor fatal error: {e}", exc_info=True)
            exit_result = {
                'error': str(e),
                'total_checks': self.total_checks,
                'haiku_calls': self.haiku_calls
            }
            
        finally:
            await conn.close()
        
        return exit_result or {
            'exit_reason': 'Monitor ended without exit',
            'total_checks': self.total_checks,
            'haiku_calls': self.haiku_calls
        }
    
    def _get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote from broker."""
        try:
            quote = self.broker.get_quote(symbol)
            return quote
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None
    
    def _get_technicals(self, symbol: str) -> Dict[str, Any]:
        """Get technical indicators."""
        try:
            technicals = self.market_data.get_technicals(symbol)
            return technicals or {}
        except Exception as e:
            logger.error(f"Error getting technicals for {symbol}: {e}")
            return {}
    
    async def _execute_exit(
        self,
        symbol: str,
        quantity: int,
        reason: str
    ) -> Optional[float]:
        """Execute market sell to exit position."""
        logger.info(f"Executing exit: {symbol} x {quantity} - {reason}")
        
        try:
            result = self.broker.execute_trade(
                symbol=symbol,
                side='sell',
                quantity=quantity,
                order_type='market',
                reason=reason
            )
            
            if result and result.success:
                fill_price = result.fill_price or result.limit_price
                logger.info(f"Exit executed: {symbol} @ HKD {fill_price:.2f}")
                return fill_price
            else:
                logger.error(f"Exit order failed: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Exit execution error: {e}")
            return None
    
    async def _consult_haiku(
        self,
        position: Dict[str, Any],
        analysis: SignalAnalysis,
        technicals: Dict[str, Any],
        entry_reason: str
    ) -> Dict[str, Any]:
        """
        Ask Haiku for exit decision on uncertain signals.
        
        Cost: ~$0.05 per call
        """
        self.haiku_calls += 1
        self.estimated_cost += 0.05
        
        symbol = position['symbol']
        entry_price = position['entry_price']
        current_price = position['current_price']
        pnl_pct = position['pnl_pct']
        high_watermark = position.get('high_watermark', current_price)
        
        # Build prompt
        prompt = f"""You are a trading assistant monitoring an HKEX position. Quick decision needed.

POSITION:
- Symbol: {symbol}
- Entry: HKD {entry_price:.2f}
- Current: HKD {current_price:.2f}
- P&L: {pnl_pct*100:+.2f}%
- High since entry: HKD {high_watermark:.2f}

TECHNICALS:
- RSI: {technicals.get('rsi', 'N/A')}
- MACD: {technicals.get('macd_signal', 'N/A')}
- vs VWAP: {technicals.get('vwap', 'N/A')}

SIGNALS DETECTED:
Hold: {', '.join(analysis.hold_signal_names) or 'None'}
Exit: {', '.join(analysis.exit_signal_names) or 'None'}

ENTRY REASON: {entry_reason}

Should we EXIT or HOLD?

Consider:
1. Are the exit signals indicating real weakness or just noise?
2. Is the original entry thesis still valid?
3. Risk of holding vs potential upside?

Respond in exactly this format:
DECISION: EXIT or HOLD
REASON: One sentence (max 20 words)
"""
        
        try:
            response = self.anthropic.messages.create(
                model=HAIKU_MODEL,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text
            logger.debug(f"Haiku response: {text}")
            
            # Parse response
            should_exit = False
            reason = "Haiku decision"
            
            lines = text.strip().split('\n')
            for line in lines:
                if line.startswith('DECISION:'):
                    decision = line.replace('DECISION:', '').strip().upper()
                    should_exit = 'EXIT' in decision
                elif line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()[:100]
            
            logger.info(f"Haiku for {symbol}: {'EXIT' if should_exit else 'HOLD'} - {reason}")
            
            return {
                'should_exit': should_exit,
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"Haiku consultation failed: {e}")
            return {
                'should_exit': False,
                'reason': f"Haiku error, defaulting to hold"
            }


# =============================================================================
# ENTRY POINT - Called from tool_executor.py
# =============================================================================

async def start_position_monitor(
    broker: Any,
    market_data: Any,
    anthropic_client: Any,
    position_id: int,
    symbol: str,
    entry_price: float,
    quantity: int,
    stop_price: float,
    target_price: float,
    entry_reason: str = "",
    entry_volume: Optional[float] = None,
    thresholds: SignalThresholds = DEFAULT_THRESHOLDS
) -> Dict[str, Any]:
    """
    Start monitoring a position.
    
    Call this after execute_trade() for BUY orders.
    
    Args:
        broker: MoomooClient instance
        market_data: MarketData instance
        anthropic_client: Anthropic client
        position_id: Database position ID
        symbol: HKEX symbol
        entry_price: Fill price
        quantity: Shares purchased
        stop_price: Stop loss price
        target_price: Take profit price
        entry_reason: Why we entered
        entry_volume: Volume at entry
        thresholds: Signal thresholds (optional)
        
    Returns:
        Exit result dict
    """
    monitor = PositionMonitor(
        broker=broker,
        market_data=market_data,
        anthropic_client=anthropic_client,
        thresholds=thresholds
    )
    
    result = await monitor.monitor_until_exit(
        position_id=position_id,
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
    
    print("=" * 60)
    print("Position Monitor v2.0.0")
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
    print("\nDatabase tables used:")
    print("  - position_monitor_status (updated on every check)")
    print("  - positions (high_watermark updated)")
    print("\nMarket status check:")
    print(f"  Current status: {get_market_status()}")
    print(f"  Market open: {is_hkex_market_open()}")
    print("=" * 60)
