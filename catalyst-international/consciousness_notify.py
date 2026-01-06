"""
Name of Application: Catalyst Trading System
Name of file: consciousness_notify.py
Version: 1.1.0
Last Updated: 2026-01-06
Purpose: Notify big_bro via consciousness database (FREE - no API cost)

REVISION HISTORY:
v1.1.0 (2026-01-06) - Production deployment
- Simplified connection handling
- Added retry logic
- Better error messages
- Sync fallback for async contexts

v1.0.0 (2025-01-01) - Initial implementation

Description:
Sends notifications to big_bro by writing to the consciousness database.
This is FREE - no Claude API calls, just database writes.

Notification Types:
- Entry executed (new position)
- Exit executed (position closed)
- Monitor started/ended
- High severity signals
- Haiku decisions
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")

# Agent identities
INTL_CLAUDE = "intl_claude"
BIG_BRO = "big_bro"

# Connection pool (lazy initialized)
_pool = None


async def get_pool():
    """Get or create database connection pool."""
    global _pool
    
    if _pool is not None:
        return _pool
    
    try:
        import asyncpg
        
        db_url = os.environ.get("RESEARCH_DATABASE_URL")
        if not db_url:
            logger.warning("RESEARCH_DATABASE_URL not set - notifications disabled")
            return None
        
        _pool = await asyncpg.create_pool(
            db_url,
            min_size=1,
            max_size=3,
            command_timeout=10,
        )
        logger.info("Consciousness database pool created")
        return _pool
        
    except ImportError:
        logger.error("asyncpg not installed - run: pip install asyncpg")
        return None
    except Exception as e:
        logger.error(f"Failed to create pool: {e}")
        return None


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Consciousness database pool closed")


async def send_message(
    to_agent: str,
    subject: str,
    body: str,
    msg_type: str = "message",
    priority: str = "normal",
) -> bool:
    """
    Send a message to another agent via consciousness database.
    
    Args:
        to_agent: Recipient agent ID
        subject: Message subject
        body: Message body
        msg_type: 'message', 'task', 'response'
        priority: 'low', 'normal', 'high', 'urgent'
        
    Returns:
        True if sent successfully
    """
    pool = await get_pool()
    if not pool:
        logger.warning(f"Cannot send message - no database connection")
        return False
    
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO claude_messages 
                (from_agent, to_agent, msg_type, subject, body, priority, status, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending', NOW())
            """, INTL_CLAUDE, to_agent, msg_type, subject, body, priority)
        
        logger.debug(f"Message sent to {to_agent}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False


async def add_observation(
    subject: str,
    content: str,
    observation_type: str = "system",
    confidence: float = 0.8,
    market: str = "HKEX",
) -> bool:
    """
    Add an observation to the consciousness database.
    
    Args:
        subject: Observation subject
        content: Observation content
        observation_type: 'market', 'system', 'pattern', 'insight'
        confidence: 0.0 - 1.0
        market: 'HKEX', 'US', 'global'
        
    Returns:
        True if added successfully
    """
    pool = await get_pool()
    if not pool:
        return False
    
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO claude_observations
                (agent_id, observation_type, subject, content, confidence, market, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """, INTL_CLAUDE, observation_type, subject, content, confidence, market)
        
        logger.debug(f"Observation added: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add observation: {e}")
        return False


# =============================================================================
# HIGH-LEVEL NOTIFICATION FUNCTIONS
# =============================================================================

async def notify_entry_executed(
    symbol: str,
    side: str,
    quantity: int,
    entry_price: float,
    stop_price: float,
    target_price: float,
    entry_reason: str,
) -> bool:
    """Notify big_bro that a position was entered."""
    
    subject = f"[ENTRY] {side} {symbol}"
    body = f"""Position Entered:
Symbol: {symbol}
Side: {side}
Quantity: {quantity:,}
Entry Price: ${entry_price:.2f}
Stop Loss: ${stop_price:.2f} ({(stop_price/entry_price - 1)*100:.1f}%)
Target: ${target_price:.2f} ({(target_price/entry_price - 1)*100:.1f}%)
Reason: {entry_reason}
Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT"""
    
    return await send_message(BIG_BRO, subject, body, priority="normal")


async def notify_exit_executed(
    position: dict,
    exit_reason: str,
    exit_price: float,
    pnl: float,
    pnl_pct: float,
) -> bool:
    """Notify big_bro that a position was exited."""
    
    symbol = position.get('symbol', 'UNKNOWN')
    entry_price = position.get('entry_price', 0)
    quantity = position.get('quantity', 0)
    
    emoji = "🟢" if pnl >= 0 else "🔴"
    subject = f"[EXIT] {symbol} {emoji} ${pnl:+,.2f} ({pnl_pct:+.2%})"
    
    body = f"""Position Closed:
Symbol: {symbol}
Entry: ${entry_price:.2f}
Exit: ${exit_price:.2f}
Quantity: {quantity:,}
P&L: ${pnl:+,.2f} ({pnl_pct:+.2%})
Reason: {exit_reason}
Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT"""
    
    # Also add as observation for learning
    await add_observation(
        subject=f"Trade Result: {symbol}",
        content=f"Exit {symbol} @ ${exit_price:.2f}. P&L: ${pnl:+,.2f} ({pnl_pct:+.2%}). Reason: {exit_reason}",
        observation_type="market",
        confidence=0.9,
    )
    
    return await send_message(BIG_BRO, subject, body, priority="high")


async def notify_monitor_started(
    symbol: str,
    entry_price: float,
    quantity: int,
) -> bool:
    """Notify that position monitoring has started."""
    
    subject = f"[MONITOR] Started: {symbol}"
    body = f"""Position monitoring started:
Symbol: {symbol}
Entry: ${entry_price:.2f}
Quantity: {quantity:,}
Check Interval: 5 minutes
Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT"""
    
    return await send_message(BIG_BRO, subject, body, priority="low")


async def notify_monitor_ended(
    symbol: str,
    reason: str,
    total_checks: int,
    haiku_calls: int,
) -> bool:
    """Notify that position monitoring has ended."""
    
    subject = f"[MONITOR] Ended: {symbol}"
    body = f"""Position monitoring ended:
Symbol: {symbol}
Reason: {reason}
Total Checks: {total_checks}
Haiku Consultations: {haiku_calls}
Estimated Cost: ${haiku_calls * 0.05:.2f}
Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT"""
    
    return await send_message(BIG_BRO, subject, body, priority="low")


async def notify_high_severity_signal(
    position: dict,
    signals: Any,
    details: str = "",
) -> bool:
    """Notify big_bro of high severity exit signals."""
    
    symbol = position.get('symbol', 'UNKNOWN')
    pnl_pct = position.get('pnl_pct', 0)
    
    subject = f"[SIGNAL] High Severity: {symbol}"
    body = f"""High severity signals detected:
Symbol: {symbol}
Current P&L: {pnl_pct:.2%}
Signals: {signals.summary() if hasattr(signals, 'summary') else str(signals)}
{details}
Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT"""
    
    return await send_message(BIG_BRO, subject, body, priority="normal")


async def notify_haiku_decision(
    symbol: str,
    question: str,
    decision: str,
    reasoning: str,
    cost: float,
) -> bool:
    """Notify big_bro of a Haiku consultation result."""
    
    subject = f"[HAIKU] Decision: {symbol}"
    body = f"""Haiku Consultation:
Symbol: {symbol}
Question: {question}
Decision: {decision}
Reasoning: {reasoning}
Cost: ${cost:.4f}
Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT"""
    
    return await send_message(BIG_BRO, subject, body, priority="normal")


async def notify_error(
    context: str,
    error: str,
    details: str = "",
) -> bool:
    """Notify big_bro of an error."""
    
    subject = f"[ERROR] {context}"
    body = f"""Error in position monitor:
Context: {context}
Error: {error}
Details: {details}
Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT

Note: Wide bracket orders remain in place as backup protection."""
    
    return await send_message(BIG_BRO, subject, body, priority="high")


# =============================================================================
# SYNC WRAPPERS (for non-async contexts)
# =============================================================================

def notify_sync(coro):
    """Run async notification in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - create task
            asyncio.create_task(coro)
            return True
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop - create new one
        return asyncio.run(coro)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    """Test consciousness notifications."""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test():
        print("Testing Consciousness Notifications v1.1.0")
        print("=" * 60)
        
        # Check for database URL
        if not os.environ.get("RESEARCH_DATABASE_URL"):
            print("\nRESEARCH_DATABASE_URL not set")
            print("Set it to test: export RESEARCH_DATABASE_URL='postgresql://...'")
            return
        
        # Test entry notification
        print("\nTest 1: Entry notification")
        result = await notify_entry_executed(
            symbol='1024',
            side='BUY',
            quantity=2000,
            entry_price=76.35,
            stop_price=74.85,
            target_price=79.35,
            entry_reason='Momentum breakout +3.67% on high volume',
        )
        print(f"  Result: {'✅ Sent' if result else '❌ Failed'}")
        
        # Test exit notification
        print("\nTest 2: Exit notification")
        position = {
            'symbol': '1024',
            'entry_price': 76.35,
            'quantity': 2000,
        }
        result = await notify_exit_executed(
            position=position,
            exit_reason='Take profit - target reached',
            exit_price=79.35,
            pnl=6000.0,
            pnl_pct=0.039,
        )
        print(f"  Result: {'✅ Sent' if result else '❌ Failed'}")
        
        # Cleanup
        await close_pool()
        
        print("\n" + "=" * 60)
        print("Tests complete - check consciousness dashboard for messages")
    
    asyncio.run(test())
