"""
Name of Application: Catalyst Trading System
Name of file: unified_agent.py
Version: 2.0.0
Last Updated: 2026-01-10
Purpose: Unified trading agent with consciousness and position monitoring

REVISION HISTORY:
v2.0.0 (2026-01-10) - Ecosystem restructure
- Startup monitor integration
- Position monitor integration (auto-start on BUY)
- Config file support (YAML)
- Consciousness integration
- Pattern-based signal detection

v1.0.0 (2026-01-05) - Initial unified agent

Description:
Single-agent architecture for HKEX trading. Handles:
- Market scanning and opportunity detection
- Entry decision making with AI
- Position monitoring with pattern-based exits
- Consciousness integration for memory and learning

Usage:
    python unified_agent.py --mode trade
    python unified_agent.py --mode close
    python unified_agent.py --mode heartbeat
    python unified_agent.py --mode scan
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Any, Optional, List
from zoneinfo import ZoneInfo

import yaml
import asyncpg
import anthropic

# Local imports - adjust path as needed
try:
    from brokers.moomoo import MoomooClient
    from data.market import MarketData
    from safety import SafetyValidator
except ImportError:
    # Running standalone - mock imports
    MoomooClient = None
    MarketData = None
    SafetyValidator = None

from signals import analyze_position, SignalThresholds, DEFAULT_THRESHOLDS
from startup_monitor import run_startup_reconciliation, get_monitor_health_report
from position_monitor import start_position_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Timezone
HK_TZ = ZoneInfo("Asia/Hong_Kong")


# =============================================================================
# CONFIGURATION
# =============================================================================

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    
    # Default paths to check
    default_paths = [
        Path("config/agent_config.yaml"),
        Path("config/dev_claude_config.yaml"),
        Path("config/intl_claude_config.yaml"),
        Path("agent_config.yaml"),
    ]
    
    if config_path:
        default_paths.insert(0, Path(config_path))
    
    for path in default_paths:
        if path.exists():
            logger.info(f"Loading config from {path}")
            with open(path) as f:
                return yaml.safe_load(f)
    
    # Return defaults if no config found
    logger.warning("No config file found, using defaults")
    return {
        'agent': {'id': os.getenv('AGENT_ID', 'unified_agent')},
        'trading': {
            'max_positions': 5,
            'max_position_value_hkd': 40000,
            'daily_loss_limit_hkd': 16000,
        },
        'ai': {
            'daily_budget_usd': 5.00,
        }
    }


# =============================================================================
# DATABASE
# =============================================================================

class Database:
    """Database connection manager."""
    
    def __init__(self, trading_url: str, research_url: str):
        self.trading_url = trading_url
        self.research_url = research_url
        self.trading_pool: Optional[asyncpg.Pool] = None
        self.research_pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pools."""
        self.trading_pool = await asyncpg.create_pool(
            self.trading_url, min_size=2, max_size=5
        )
        self.research_pool = await asyncpg.create_pool(
            self.research_url, min_size=1, max_size=3
        )
        logger.info("Database pools created")
    
    async def close(self):
        """Close connection pools."""
        if self.trading_pool:
            await self.trading_pool.close()
        if self.research_pool:
            await self.research_pool.close()
        logger.info("Database pools closed")


# =============================================================================
# CONSCIOUSNESS INTEGRATION
# =============================================================================

class ConsciousnessClient:
    """Interface to consciousness framework."""
    
    def __init__(self, pool: asyncpg.Pool, agent_id: str):
        self.pool = pool
        self.agent_id = agent_id
    
    async def wake_up(self) -> Dict[str, Any]:
        """Mark agent as awake and get pending messages."""
        async with self.pool.acquire() as conn:
            # Update status
            await conn.execute("""
                UPDATE claude_state SET
                    status = 'awake',
                    last_active = NOW()
                WHERE agent_id = $1
            """, self.agent_id)
            
            # Get pending messages
            messages = await conn.fetch("""
                SELECT message_id, from_agent, subject, body, priority
                FROM claude_messages
                WHERE to_agent = $1 AND status = 'pending'
                ORDER BY priority DESC, created_at
            """, self.agent_id)
            
            # Mark as read
            if messages:
                await conn.execute("""
                    UPDATE claude_messages SET
                        status = 'read',
                        read_at = NOW()
                    WHERE to_agent = $1 AND status = 'pending'
                """, self.agent_id)
            
            return {
                'agent_id': self.agent_id,
                'messages': [dict(m) for m in messages]
            }
    
    async def observe(self, category: str, content: str, metadata: Dict = None):
        """Record an observation."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO claude_observations (agent_id, category, content, metadata)
                VALUES ($1, $2, $3, $4)
            """, self.agent_id, category, content, metadata or {})
    
    async def sleep(self):
        """Mark agent as sleeping."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_state SET
                    status = 'sleeping',
                    last_active = NOW()
                WHERE agent_id = $1
            """, self.agent_id)


# =============================================================================
# UNIFIED AGENT
# =============================================================================

class UnifiedAgent:
    """
    Unified trading agent for HKEX.
    
    Handles scanning, trading, monitoring, and consciousness.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        broker: Any,
        market_data: Any,
        anthropic_client: anthropic.Anthropic,
        db: Database,
    ):
        self.config = config
        self.broker = broker
        self.market_data = market_data
        self.anthropic = anthropic_client
        self.db = db
        
        self.agent_id = config['agent']['id']
        self.consciousness: Optional[ConsciousnessClient] = None
        
        # Build signal thresholds from config
        signal_config = config.get('signals', {})
        self.thresholds = SignalThresholds(
            stop_loss_strong=signal_config.get('stop_loss_strong', -0.03),
            stop_loss_moderate=signal_config.get('stop_loss_moderate', -0.02),
            take_profit_strong=signal_config.get('take_profit_strong', 0.08),
            take_profit_moderate=signal_config.get('take_profit_moderate', 0.05),
            rsi_overbought_strong=signal_config.get('rsi_overbought_strong', 85),
            rsi_overbought_moderate=signal_config.get('rsi_overbought_moderate', 75),
        )
        
        logger.info(f"UnifiedAgent initialized: {self.agent_id}")
    
    async def initialize(self):
        """Initialize agent connections."""
        await self.db.connect()
        
        if self.db.research_pool:
            self.consciousness = ConsciousnessClient(
                self.db.research_pool, self.agent_id
            )
        
        # Connect broker
        if self.broker:
            self.broker.connect()
        
        logger.info("Agent initialized")
    
    async def shutdown(self):
        """Shutdown agent connections."""
        if self.broker:
            self.broker.disconnect()
        
        if self.consciousness:
            await self.consciousness.sleep()
        
        await self.db.close()
        logger.info("Agent shutdown complete")
    
    # =========================================================================
    # MODE HANDLERS
    # =========================================================================
    
    async def run_startup(self):
        """Run pre-market startup reconciliation."""
        logger.info("=" * 60)
        logger.info("RUNNING STARTUP RECONCILIATION")
        logger.info("=" * 60)
        
        # Wake up consciousness
        if self.consciousness:
            wake_result = await self.consciousness.wake_up()
            if wake_result['messages']:
                logger.info(f"Processing {len(wake_result['messages'])} messages")
                for msg in wake_result['messages']:
                    logger.info(f"  From {msg['from_agent']}: {msg['subject']}")
        
        # Run reconciliation
        result = await run_startup_reconciliation()
        
        # Record observation
        if self.consciousness:
            await self.consciousness.observe(
                category='system',
                content=f"Startup reconciliation: {result['reconciliation']['positions_found']} positions, "
                        f"{len(result['reconciliation']['monitors_started'])} monitors started",
                metadata=result['reconciliation']
            )
        
        return result
    
    async def run_trade_cycle(self):
        """Run full trading cycle: scan -> analyze -> execute."""
        logger.info("=" * 60)
        logger.info("RUNNING TRADE CYCLE")
        logger.info(f"Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("=" * 60)
        
        # Wake up
        if self.consciousness:
            await self.consciousness.wake_up()
        
        # Check market hours
        if not self._is_market_open():
            logger.info("Market closed, skipping trade cycle")
            return {'status': 'skipped', 'reason': 'market_closed'}
        
        # Get current portfolio
        portfolio = await self._get_portfolio()
        open_positions = portfolio.get('positions', [])
        
        logger.info(f"Current positions: {len(open_positions)}")
        
        # Check position limit
        max_positions = self.config['trading']['max_positions']
        if len(open_positions) >= max_positions:
            logger.info(f"At max positions ({max_positions}), skipping scan")
            return {'status': 'skipped', 'reason': 'max_positions'}
        
        # Scan for opportunities
        candidates = await self._scan_market()
        
        if not candidates:
            logger.info("No candidates found")
            return {'status': 'complete', 'candidates': 0, 'trades': 0}
        
        logger.info(f"Found {len(candidates)} candidates")
        
        # Analyze and potentially execute
        trades_executed = 0
        for candidate in candidates[:3]:  # Limit to top 3
            if len(open_positions) + trades_executed >= max_positions:
                break
            
            decision = await self._analyze_candidate(candidate)
            
            if decision.get('action') == 'BUY':
                result = await self._execute_entry(candidate, decision)
                if result.get('success'):
                    trades_executed += 1
        
        # Record observation
        if self.consciousness:
            await self.consciousness.observe(
                category='trading',
                content=f"Trade cycle complete: {len(candidates)} candidates, {trades_executed} trades",
                metadata={'candidates': len(candidates), 'trades': trades_executed}
            )
        
        return {'status': 'complete', 'candidates': len(candidates), 'trades': trades_executed}
    
    async def run_close_cycle(self):
        """Review and optionally close positions."""
        logger.info("=" * 60)
        logger.info("RUNNING CLOSE CYCLE")
        logger.info("=" * 60)
        
        if self.consciousness:
            await self.consciousness.wake_up()
        
        portfolio = await self._get_portfolio()
        positions = portfolio.get('positions', [])
        
        if not positions:
            logger.info("No open positions")
            return {'status': 'complete', 'positions_closed': 0}
        
        # For lunch break or EOD, consider closing positions with weak patterns
        current_time = datetime.now(HK_TZ).time()
        is_lunch = time(11, 50) <= current_time < time(12, 10)
        is_eod = current_time >= time(15, 50)
        
        closed = 0
        for pos in positions:
            # Get technicals for analysis
            technicals = self._get_technicals(pos['symbol'])
            
            analysis = analyze_position(
                position=pos,
                quote={'price': pos.get('current_price', pos['entry_price'])},
                technicals=technicals,
                thresholds=self.thresholds
            )
            
            should_close = False
            reason = ""
            
            if is_eod:
                # EOD - close unless very strong hold
                if analysis.recommendation != "HOLD" or not any(
                    s.strength.value == 'strong' for s in analysis.hold_signals
                ):
                    should_close = True
                    reason = "EOD close"
            elif is_lunch:
                # Lunch - close if any exit signals
                if analysis.exit_signals:
                    should_close = True
                    reason = "Lunch break - weak pattern"
            
            if should_close:
                result = await self._close_position(pos, reason)
                if result.get('success'):
                    closed += 1
        
        if self.consciousness:
            await self.consciousness.observe(
                category='trading',
                content=f"Close cycle: {closed}/{len(positions)} positions closed",
                metadata={'total': len(positions), 'closed': closed}
            )
        
        return {'status': 'complete', 'positions_closed': closed}
    
    async def run_heartbeat(self):
        """Process messages and update status only."""
        logger.info("Running heartbeat")
        
        if self.consciousness:
            wake_result = await self.consciousness.wake_up()
            
            for msg in wake_result.get('messages', []):
                logger.info(f"Message from {msg['from_agent']}: {msg['subject']}")
            
            await self.consciousness.sleep()
        
        return {'status': 'complete', 'messages_processed': len(wake_result.get('messages', []))}
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _is_market_open(self) -> bool:
        """Check if HKEX is open."""
        now = datetime.now(HK_TZ)
        if now.weekday() >= 5:
            return False
        
        current_time = now.time()
        
        if time(9, 30) <= current_time < time(12, 0):
            return True
        if time(13, 0) <= current_time < time(16, 0):
            return True
        
        return False
    
    async def _get_portfolio(self) -> Dict[str, Any]:
        """Get current portfolio state."""
        if not self.broker:
            return {'positions': []}
        
        try:
            positions = self.broker.get_positions()
            return {
                'positions': [
                    {
                        'symbol': p.symbol,
                        'quantity': p.quantity,
                        'entry_price': p.avg_cost,
                        'current_price': p.current_price,
                        'unrealized_pnl': p.unrealized_pnl,
                        'pnl_pct': p.unrealized_pnl_pct / 100 if p.unrealized_pnl_pct else 0,
                    }
                    for p in positions
                ]
            }
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return {'positions': []}
    
    async def _scan_market(self) -> List[Dict[str, Any]]:
        """Scan market for trading candidates."""
        # Implementation depends on your scanner logic
        logger.info("Scanning market...")
        
        # Placeholder - implement your scanning logic
        return []
    
    async def _analyze_candidate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a candidate for entry."""
        # Implementation depends on your analysis logic
        logger.info(f"Analyzing {candidate.get('symbol')}...")
        
        # Placeholder
        return {'action': 'SKIP', 'reason': 'Not implemented'}
    
    async def _execute_entry(
        self,
        candidate: Dict[str, Any],
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute entry trade and start position monitor."""
        symbol = candidate['symbol']
        logger.info(f"Executing entry for {symbol}")
        
        try:
            # Execute trade via broker
            result = self.broker.execute_trade(
                symbol=symbol,
                side='buy',
                quantity=decision.get('quantity', 100),
                order_type='limit',
                limit_price=decision.get('entry_price'),
                stop_loss=decision.get('stop_loss'),
                take_profit=decision.get('take_profit'),
                reason=decision.get('reason', 'AI entry decision')
            )
            
            if result and result.success:
                # Record to database
                async with self.db.trading_pool.acquire() as conn:
                    position_id = await conn.fetchval("""
                        INSERT INTO positions (
                            symbol, side, quantity, entry_price, entry_time,
                            stop_loss, take_profit, entry_reason, status
                        ) VALUES ($1, 'long', $2, $3, NOW(), $4, $5, $6, 'open')
                        RETURNING position_id
                    """,
                        symbol,
                        result.quantity,
                        result.fill_price or decision.get('entry_price'),
                        decision.get('stop_loss'),
                        decision.get('take_profit'),
                        decision.get('reason')
                    )
                
                # Start position monitor (non-blocking)
                asyncio.create_task(
                    start_position_monitor(
                        broker=self.broker,
                        market_data=self.market_data,
                        anthropic_client=self.anthropic,
                        position_id=position_id,
                        symbol=symbol,
                        entry_price=result.fill_price or decision.get('entry_price'),
                        quantity=result.quantity,
                        stop_price=decision.get('stop_loss'),
                        target_price=decision.get('take_profit'),
                        entry_reason=decision.get('reason', ''),
                        thresholds=self.thresholds
                    )
                )
                
                logger.info(f"Entry executed and monitor started for {symbol}")
                return {'success': True, 'position_id': position_id}
            else:
                return {'success': False, 'error': 'Order failed'}
                
        except Exception as e:
            logger.error(f"Entry execution error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _close_position(
        self,
        position: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """Close a position."""
        symbol = position['symbol']
        quantity = position['quantity']
        
        try:
            result = self.broker.execute_trade(
                symbol=symbol,
                side='sell',
                quantity=quantity,
                order_type='market',
                reason=reason
            )
            
            if result and result.success:
                logger.info(f"Closed {symbol}: {reason}")
                return {'success': True}
            else:
                return {'success': False}
                
        except Exception as e:
            logger.error(f"Close position error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_technicals(self, symbol: str) -> Dict[str, Any]:
        """Get technical indicators for symbol."""
        if not self.market_data:
            return {}
        
        try:
            return self.market_data.get_technicals(symbol) or {}
        except:
            return {}


# =============================================================================
# MAIN
# =============================================================================

async def main(mode: str, config_path: Optional[str] = None):
    """Main entry point."""
    
    # Load config
    config = load_config(config_path)
    agent_id = config['agent']['id']
    
    logger.info(f"Starting {agent_id} in {mode} mode")
    
    # Get database URLs
    trading_url = os.getenv("DATABASE_URL") or os.getenv("INTL_DATABASE_URL") or os.getenv("DEV_DATABASE_URL")
    research_url = os.getenv("RESEARCH_DATABASE_URL")
    
    if not trading_url:
        logger.error("No DATABASE_URL set")
        sys.exit(1)
    
    # Create components
    db = Database(trading_url, research_url)
    
    # Create broker (if available)
    broker = None
    market_data = None
    if MoomooClient:
        try:
            broker = MoomooClient(paper_trading=True)
        except:
            logger.warning("Could not initialize broker")
    
    # Create Anthropic client
    anthropic_client = anthropic.Anthropic()
    
    # Create agent
    agent = UnifiedAgent(
        config=config,
        broker=broker,
        market_data=market_data,
        anthropic_client=anthropic_client,
        db=db
    )
    
    try:
        await agent.initialize()
        
        # Run appropriate mode
        if mode == 'startup':
            result = await agent.run_startup()
        elif mode == 'trade':
            # Run startup first if first cycle of day
            result = await agent.run_trade_cycle()
        elif mode == 'close':
            result = await agent.run_close_cycle()
        elif mode == 'heartbeat':
            result = await agent.run_heartbeat()
        elif mode == 'scan':
            result = await agent.run_trade_cycle()  # Same as trade for now
        else:
            logger.error(f"Unknown mode: {mode}")
            result = {'error': f'Unknown mode: {mode}'}
        
        logger.info(f"Result: {result}")
        
    finally:
        await agent.shutdown()


def cli():
    """Command line interface."""
    parser = argparse.ArgumentParser(description='Unified Trading Agent')
    parser.add_argument(
        '--mode',
        choices=['startup', 'scan', 'trade', 'close', 'heartbeat'],
        default='heartbeat',
        help='Operating mode'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to config file'
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(args.mode, args.config))


if __name__ == "__main__":
    cli()
