#!/usr/bin/env python3
"""
Name of Application: Catalyst Trading System
Name of file: unified_agent.py
Version: 1.0.0
Last Updated: 2026-01-05
Purpose: Unified agent combining consciousness + trading

REVISION HISTORY:
v1.0.0 (2026-01-05) - Initial implementation
- Merged heartbeat_intl.py and agent.py
- Single entry point with mode auto-detection
- Market hours awareness
- Consciousness integration throughout

Description:
This is the unified agent for intl_claude that handles:
1. Consciousness (wake/sleep, messages, observations, learnings)
2. Trading (market scanning, analysis, execution via Moomoo)
3. Task execution (whitelisted system commands)

The agent runs via cron and auto-detects its mode based on market hours.
During trading hours, it performs full autonomous trading.
Outside trading hours, it processes messages and tasks only.
"""

import argparse
import asyncio
import asyncpg
import json
import logging
import os
import sys
import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import Any, Optional
from zoneinfo import ZoneInfo

import anthropic
import yaml
from dotenv import load_dotenv

# Load environment
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

AGENT_ID = "intl_claude"
MARKET = "HKEX"
HK_TZ = ZoneInfo("Asia/Hong_Kong")

# Database URLs
TRADING_DATABASE_URL = os.environ.get("DATABASE_URL")  # catalyst_intl
RESEARCH_DATABASE_URL = os.environ.get("RESEARCH_DATABASE_URL")  # catalyst_research

# Claude API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL_TRADING = "claude-sonnet-4-20250514"  # For trading decisions
MODEL_MESSAGES = "claude-3-5-haiku-20241022"  # For message processing
MAX_TOKENS = 4096
MAX_ITERATIONS = 20

# Budgets
DAILY_BUDGET = Decimal("5.00")
TRADING_BUDGET_RATIO = Decimal("0.80")  # 80% for trading, 20% for consciousness

# Project paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "unified_agent.log")),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# MARKET HOURS
# ============================================================================

class MarketHours:
    """HKEX market hours handler."""
    
    # Time boundaries (HKT)
    PRE_MARKET_START = time(8, 0)
    MORNING_OPEN = time(9, 30)
    LUNCH_START = time(12, 0)
    AFTERNOON_OPEN = time(13, 0)
    MARKET_CLOSE = time(16, 0)
    AFTER_HOURS_END = time(16, 30)
    
    @classmethod
    def get_current_mode(cls) -> str:
        """Determine agent mode based on current HK time."""
        now = datetime.now(HK_TZ).time()
        weekday = datetime.now(HK_TZ).weekday()
        
        # Weekend = heartbeat only
        if weekday >= 5:
            return "heartbeat"
        
        # Pre-market
        if cls.PRE_MARKET_START <= now < cls.MORNING_OPEN:
            return "scan"
        
        # Morning session
        if cls.MORNING_OPEN <= now < cls.LUNCH_START:
            return "trade"
        
        # Lunch break - close positions
        if cls.LUNCH_START <= now < cls.AFTERNOON_OPEN:
            return "close"
        
        # Afternoon session
        if cls.AFTERNOON_OPEN <= now < cls.MARKET_CLOSE:
            return "trade"
        
        # After hours - EOD report
        if cls.MARKET_CLOSE <= now < cls.AFTER_HOURS_END:
            return "close"
        
        # Outside market hours
        return "heartbeat"
    
    @classmethod
    def is_trading_hours(cls) -> bool:
        """Check if we're in active trading hours."""
        mode = cls.get_current_mode()
        return mode in ("trade", "scan", "close")
    
    @classmethod
    def get_session_info(cls) -> dict:
        """Get detailed session information."""
        now = datetime.now(HK_TZ)
        mode = cls.get_current_mode()
        
        return {
            "current_time_hkt": now.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": now.strftime("%A"),
            "mode": mode,
            "is_trading_hours": cls.is_trading_hours(),
            "next_session": cls._get_next_session(now),
        }
    
    @classmethod
    def _get_next_session(cls, now: datetime) -> str:
        """Get description of next trading session."""
        current_time = now.time()
        
        if current_time < cls.PRE_MARKET_START:
            return f"Pre-market at {cls.PRE_MARKET_START}"
        elif current_time < cls.MORNING_OPEN:
            return f"Morning open at {cls.MORNING_OPEN}"
        elif current_time < cls.LUNCH_START:
            return f"Lunch at {cls.LUNCH_START}"
        elif current_time < cls.AFTERNOON_OPEN:
            return f"Afternoon open at {cls.AFTERNOON_OPEN}"
        elif current_time < cls.MARKET_CLOSE:
            return f"Market close at {cls.MARKET_CLOSE}"
        else:
            return "Next trading day"


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

TRADING_SYSTEM_PROMPT = """You are intl_claude, an autonomous AI trading agent for the Hong Kong Stock Exchange (HKEX).

## Your Identity
- Agent ID: intl_claude
- Market: HKEX (Hong Kong Stock Exchange)
- Mission: Enable accessible trading through AI-powered analysis and execution

## Your Role
You make trading decisions during HKEX market hours using the tools available to you.
Every decision you make should be documented with clear reasoning for the audit trail.

## Market Hours (Hong Kong Time)
- Pre-market: 08:00 - 09:30 (scan only)
- Morning session: 09:30 - 12:00 (full trading)
- Lunch break: 12:00 - 13:00 (NO TRADING - close positions)
- Afternoon session: 13:00 - 16:00 (full trading)
- After hours: 16:00 - 16:30 (EOD close and report)

## Trading Strategy
You are a momentum day trader. Your edge is:
1. Finding stocks with volume spikes (>1.5x average)
2. Confirming with technical patterns and indicators
3. Using news catalysts to time entries
4. Strict risk management (2% stop loss, 6% take profit)

## Risk Rules (MUST FOLLOW)
- Maximum 5 positions at once
- Maximum HKD 40,000 per position
- Maximum HKD 16,000 daily loss limit
- ALWAYS use stop losses
- NEVER hold through lunch break (12:00-13:00)
- Close all positions before 16:00

## Tool Usage Rules
1. ALWAYS call check_risk before execute_trade
2. NEVER trade if check_risk returns approved: false
3. ALWAYS log your reasoning with log_decision
4. Record observations for learning

## Current Context
{context}

## Your Task
Based on the current mode and market conditions, take appropriate actions:
- scan: Find opportunities, analyze candidates, prepare for trading
- trade: Execute your strategy with proper risk management
- close: Exit positions, generate summary
- heartbeat: Process messages only

When you've completed all actions for this cycle, provide a summary of:
- Actions taken
- Positions entered/exited
- Key decisions made
- Any concerns or observations
"""


# ============================================================================
# CONSCIOUSNESS DATABASE HELPERS
# ============================================================================

class ConsciousnessDB:
    """Handle consciousness database operations (catalyst_research)."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.agent_id = AGENT_ID
    
    async def get_state(self) -> dict:
        """Get current agent state."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM claude_state WHERE agent_id = $1",
                self.agent_id
            )
            return dict(row) if row else {}
    
    async def update_state(self, mode: str, status: str):
        """Update agent state."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_state 
                SET current_mode = $2, 
                    status_message = $3, 
                    last_wake_at = NOW(), 
                    updated_at = NOW()
                WHERE agent_id = $1
            """, self.agent_id, mode, status)
    
    async def record_spend(self, cost: Decimal):
        """Record API spend."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_state 
                SET api_spend_today = api_spend_today + $2,
                    updated_at = NOW()
                WHERE agent_id = $1
            """, self.agent_id, float(cost))
    
    async def get_pending_messages(self) -> list:
        """Get pending messages for this agent."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, from_agent, subject, body, msg_type, priority, created_at
                FROM claude_messages 
                WHERE to_agent = $1 AND status = 'pending'
                ORDER BY 
                    CASE priority 
                        WHEN 'urgent' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'normal' THEN 3 
                        WHEN 'low' THEN 4 
                    END,
                    created_at ASC
                LIMIT 10
            """, self.agent_id)
            return [dict(r) for r in rows]
    
    async def mark_message_read(self, msg_id: int):
        """Mark message as read."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_messages 
                SET status = 'read', read_at = NOW()
                WHERE id = $1
            """, msg_id)
    
    async def mark_message_processed(self, msg_id: int):
        """Mark message as processed."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_messages 
                SET status = 'processed'
                WHERE id = $1
            """, msg_id)
    
    async def send_message(
        self, 
        to_agent: str, 
        subject: str, 
        body: str, 
        msg_type: str = "message",
        priority: str = "normal"
    ):
        """Send a message to another agent."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO claude_messages 
                (from_agent, to_agent, msg_type, priority, subject, body, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending')
            """, self.agent_id, to_agent, msg_type, priority, subject, body)
    
    async def add_observation(
        self,
        subject: str,
        content: str,
        obs_type: str = "market",
        confidence: float = 0.8,
        market: str = "HKEX"
    ):
        """Record an observation."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO claude_observations 
                (agent_id, observation_type, subject, content, confidence, market)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, self.agent_id, obs_type, subject, content, confidence, market)
    
    async def add_learning(
        self,
        learning: str,
        category: str = "trading",
        confidence: float = 0.7,
        context: str = None
    ):
        """Record a learning."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO claude_learnings 
                (agent_id, learning, category, confidence, context)
                VALUES ($1, $2, $3, $4, $5)
            """, self.agent_id, learning, category, confidence, context)
    
    async def get_recent_learnings(self, limit: int = 5) -> list:
        """Get recent learnings for context."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT learning, category, confidence
                FROM claude_learnings
                WHERE agent_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, self.agent_id, limit)
            return [dict(r) for r in rows]


# ============================================================================
# TASK EXECUTOR (inline from task_executor_intl.py)
# ============================================================================

def parse_task_message(body: str) -> Optional[dict]:
    """Parse a task message to extract task name and params."""
    import re
    
    # Look for TASK: line
    task_match = re.search(r'TASK:\s*(\w+)', body, re.IGNORECASE)
    if not task_match:
        return None
    
    task_name = task_match.group(1)
    
    # Look for PARAMS: line (JSON)
    params = {}
    params_match = re.search(r'PARAMS:\s*(\{.*?\})', body, re.DOTALL)
    if params_match:
        try:
            params = json.loads(params_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Look for REASON: line
    reason = ""
    reason_match = re.search(r'REASON:\s*(.+?)(?:\n|$)', body)
    if reason_match:
        reason = reason_match.group(1).strip()
    
    return {
        "task": task_name,
        "params": params,
        "reason": reason
    }


# Simple whitelist for common tasks
TASK_WHITELIST = {
    "check_agent": "ps aux | grep -E 'agent.py|python.*agent' | grep -v grep",
    "check_opend": "ps aux | grep -E 'OpenD|opend' | grep -v grep",
    "disk_space": "df -h /",
    "memory_usage": "free -m",
    "db_positions": 'psql "$DATABASE_URL" -c "SELECT symbol, quantity, entry_price FROM positions WHERE status=\'open\';"',
}


class TaskExecutor:
    """Execute whitelisted tasks."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
    
    def is_whitelisted(self, task_name: str) -> bool:
        return task_name in TASK_WHITELIST
    
    async def execute(self, task_name: str, params: dict = None, reason: str = None) -> dict:
        """Execute a whitelisted task."""
        import subprocess
        
        if not self.is_whitelisted(task_name):
            return {
                "success": False,
                "error": f"Task '{task_name}' not whitelisted",
                "requires_escalation": True
            }
        
        command = TASK_WHITELIST[task_name]
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=os.environ.copy()
            )
            
            return {
                "success": result.returncode == 0,
                "task": task_name,
                "stdout": result.stdout[:2000] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
                "return_code": result.returncode,
                "executed_at": datetime.now().isoformat(),
                "executed_by": self.agent_id,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================================
# UNIFIED AGENT
# ============================================================================

class UnifiedAgent:
    """Unified agent combining consciousness + trading."""
    
    def __init__(self, mode_override: str = None):
        """Initialize the unified agent.
        
        Args:
            mode_override: Force a specific mode (scan/trade/close/heartbeat)
        """
        self.mode_override = mode_override
        self.cycle_id = str(uuid.uuid4())[:8]
        
        # Clients
        self.claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.broker = None
        self.tool_executor = None
        self.task_executor = TaskExecutor(AGENT_ID)
        
        # Database pools
        self.research_pool: Optional[asyncpg.Pool] = None
        self.trading_pool: Optional[asyncpg.Pool] = None
        
        # Consciousness
        self.consciousness: Optional[ConsciousnessDB] = None
        
        # Tracking
        self.api_spend = Decimal("0")
        self.messages_processed = 0
        self.tasks_executed = 0
        self.trades_executed = 0
        self.errors = []
    
    async def initialize(self):
        """Initialize all connections."""
        logger.info(f"[{self.cycle_id}] Initializing unified agent...")
        
        # Research database (consciousness)
        if RESEARCH_DATABASE_URL:
            self.research_pool = await asyncpg.create_pool(
                RESEARCH_DATABASE_URL,
                min_size=1,
                max_size=3
            )
            self.consciousness = ConsciousnessDB(self.research_pool)
            
            # Check budget before proceeding
            state = await self.consciousness.get_state()
            current_spend = Decimal(str(state.get("api_spend_today", 0)))
            
            if current_spend >= DAILY_BUDGET:
                raise RuntimeError(f"Daily budget exhausted: ${current_spend:.4f} >= ${DAILY_BUDGET}")
            
            logger.info(f"[{self.cycle_id}] Budget remaining: ${DAILY_BUDGET - current_spend:.4f}")
        else:
            logger.warning(f"[{self.cycle_id}] RESEARCH_DATABASE_URL not set, consciousness disabled")
        
        # Trading database
        if TRADING_DATABASE_URL:
            self.trading_pool = await asyncpg.create_pool(
                TRADING_DATABASE_URL,
                min_size=1,
                max_size=3
            )
        
        # Initialize broker for trading hours
        mode = self._get_mode()
        if mode in ("trade", "scan", "close"):
            try:
                # Import broker (may not be available in all environments)
                from brokers.moomoo import init_moomoo_client
                self.broker = init_moomoo_client(paper_trading=True)
                logger.info(f"[{self.cycle_id}] Moomoo broker connected")
                
                # Initialize tool executor
                from tools import TOOLS
                from tool_executor import create_tool_executor
                from alerts import get_alert_sender

                self.tool_executor = create_tool_executor(
                    cycle_id=self.cycle_id,
                    alert_callback=get_alert_sender(),
                    agent=self,  # Enable position monitoring
                )
                self.tools = TOOLS
                
            except ImportError as e:
                logger.warning(f"[{self.cycle_id}] Trading modules not available: {e}")
                self.broker = None
            except Exception as e:
                logger.error(f"[{self.cycle_id}] Broker connection failed: {e}")
                self.errors.append(f"Broker: {e}")
    
    async def shutdown(self):
        """Clean shutdown."""
        logger.info(f"[{self.cycle_id}] Shutting down...")
        
        # Update state
        if self.consciousness:
            await self.consciousness.update_state(
                "sleeping",
                f"Cycle complete. Msgs: {self.messages_processed}, "
                f"Tasks: {self.tasks_executed}, Trades: {self.trades_executed}. "
                f"Cost: ${self.api_spend:.4f}"
            )
            await self.consciousness.record_spend(self.api_spend)
        
        # Close broker
        if self.broker:
            try:
                self.broker.disconnect()
            except:
                pass
        
        # Close pools
        if self.research_pool:
            await self.research_pool.close()
        if self.trading_pool:
            await self.trading_pool.close()
        
        logger.info(f"[{self.cycle_id}] Shutdown complete")
    
    def _get_mode(self) -> str:
        """Get current operating mode."""
        if self.mode_override:
            return self.mode_override
        return MarketHours.get_current_mode()
    
    async def run(self):
        """Main agent run loop."""
        mode = self._get_mode()
        session_info = MarketHours.get_session_info()
        
        logger.info(f"[{self.cycle_id}] Starting cycle in '{mode}' mode")
        logger.info(f"[{self.cycle_id}] Session: {session_info}")
        
        # Update state to active
        if self.consciousness:
            await self.consciousness.update_state("active", f"Cycle {self.cycle_id} - {mode}")
        
        try:
            # Phase 1: Always process messages
            await self._process_messages()
            
            # Phase 2: Mode-specific actions
            if mode == "heartbeat":
                # Messages only, no trading
                if self.consciousness:
                    await self.consciousness.add_observation(
                        "Heartbeat cycle",
                        f"Processed {self.messages_processed} messages, "
                        f"{self.tasks_executed} tasks",
                        "system"
                    )
            
            elif mode in ("scan", "trade", "close"):
                # Trading modes
                await self._run_trading_loop(mode)
            
            # Phase 3: Summary
            await self._generate_summary(mode)
            
        except Exception as e:
            logger.error(f"[{self.cycle_id}] Cycle error: {e}", exc_info=True)
            self.errors.append(str(e))
            
            # Record error observation
            if self.consciousness:
                await self.consciousness.add_observation(
                    "Cycle error",
                    f"Error in {mode} mode: {e}",
                    "system",
                    confidence=1.0
                )
    
    async def _process_messages(self):
        """Process pending messages."""
        if not self.consciousness:
            return
        
        messages = await self.consciousness.get_pending_messages()
        
        if not messages:
            logger.info(f"[{self.cycle_id}] No pending messages")
            return
        
        logger.info(f"[{self.cycle_id}] Processing {len(messages)} messages")
        
        for msg in messages:
            try:
                msg_id = msg["id"]
                from_agent = msg["from_agent"]
                subject = msg["subject"]
                body = msg["body"]
                msg_type = msg["msg_type"]
                
                logger.info(f"[{self.cycle_id}] Message #{msg_id} from {from_agent}: {subject}")
                
                # Mark as read
                await self.consciousness.mark_message_read(msg_id)
                
                # Handle task messages
                if msg_type == "task" or "TASK:" in body:
                    result = await self._execute_task(body)
                    self.tasks_executed += 1
                    
                    # Send response
                    await self.consciousness.send_message(
                        to_agent=from_agent,
                        subject=f"Task Report: {subject}",
                        body=json.dumps(result, indent=2, default=str),
                        msg_type="response"
                    )
                
                # Mark as processed
                await self.consciousness.mark_message_processed(msg_id)
                self.messages_processed += 1
                
            except Exception as e:
                logger.error(f"[{self.cycle_id}] Message error: {e}")
                self.errors.append(f"Message #{msg['id']}: {e}")
    
    async def _execute_task(self, body: str) -> dict:
        """Execute a task from message body."""
        # Parse task
        task_info = parse_task_message(body)
        
        if not task_info:
            return {"error": "No TASK: found in message body", "success": False}
        
        task_name = task_info["task"]
        params = task_info.get("params", {})
        reason = task_info.get("reason", "")
        
        # Check if whitelisted
        if not self.task_executor.is_whitelisted(task_name):
            return {
                "error": f"Task '{task_name}' not whitelisted",
                "success": False,
                "requires_escalation": True
            }
        
        # Execute
        result = await self.task_executor.execute(task_name, params, reason)
        return result
    
    async def _run_trading_loop(self, mode: str):
        """Run the Claude trading loop."""
        if not self.broker or not self.tool_executor:
            logger.warning(f"[{self.cycle_id}] Broker not available, skipping trading")
            if self.consciousness:
                await self.consciousness.add_observation(
                    "Trading skipped",
                    "Broker not available - trading modules not loaded",
                    "system"
                )
            return
        
        # Build context
        context = await self._build_trading_context(mode)
        
        # Prepare system prompt
        system_prompt = TRADING_SYSTEM_PROMPT.format(context=context)
        
        # User message based on mode
        if mode == "scan":
            user_message = """It's pre-market. Scan the market for today's opportunities.
            
Find the top momentum stocks, analyze their technicals and news.
Prepare a list of candidates for when trading opens.
Do NOT execute any trades yet."""

        elif mode == "trade":
            user_message = """Trading session is active. Execute your strategy.

1. Check your current positions
2. Scan for new opportunities  
3. Analyze candidates (technicals, patterns, news)
4. Execute trades that pass risk checks
5. Monitor existing positions

Remember: ALWAYS check_risk before execute_trade."""

        elif mode == "close":
            user_message = """It's time to close positions.

1. Close all open positions
2. Log the reason for each close
3. Generate a summary of today's trading
4. Record any learnings

This is mandatory - no positions should remain open."""

        else:
            return
        
        # Run Claude loop
        messages = [{"role": "user", "content": user_message}]
        iterations = 0
        
        while iterations < MAX_ITERATIONS:
            iterations += 1
            
            try:
                # Call Claude
                response = self.claude.messages.create(
                    model=MODEL_TRADING,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    tools=self.tools,
                    messages=messages
                )
                
                # Track spend (approximate: $3/M input, $15/M output for Sonnet)
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = Decimal(str((input_tokens * 3 + output_tokens * 15) / 1_000_000))
                self.api_spend += cost
                
                # Check for stop conditions
                if response.stop_reason == "end_turn":
                    # Extract final message
                    for block in response.content:
                        if hasattr(block, "text"):
                            logger.info(f"[{self.cycle_id}] Claude: {block.text[:500]}...")
                    break
                
                # Process tool uses
                if response.stop_reason == "tool_use":
                    tool_results = []
                    
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_input = block.input
                            
                            logger.info(f"[{self.cycle_id}] Tool: {tool_name}({json.dumps(tool_input)[:100]})")
                            
                            # Execute tool
                            result = self.tool_executor.execute(tool_name, tool_input)
                            
                            # Track trades
                            if tool_name == "execute_trade" and result.get("success"):
                                self.trades_executed += 1
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result, default=str)
                            })
                    
                    # Add to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                
                else:
                    # Unexpected stop reason
                    logger.warning(f"[{self.cycle_id}] Unexpected stop: {response.stop_reason}")
                    break
                    
            except Exception as e:
                logger.error(f"[{self.cycle_id}] Trading loop error: {e}")
                self.errors.append(f"Trading: {e}")
                break
        
        logger.info(f"[{self.cycle_id}] Trading loop complete: {iterations} iterations, {self.trades_executed} trades")
    
    async def _build_trading_context(self, mode: str) -> str:
        """Build context string for Claude."""
        context_parts = []
        
        # Session info
        session = MarketHours.get_session_info()
        context_parts.append(f"## Session\n{json.dumps(session, indent=2)}")
        
        # Portfolio (if broker connected)
        if self.broker:
            try:
                portfolio = self.broker.get_portfolio()
                context_parts.append(f"## Portfolio\n{json.dumps(portfolio, indent=2, default=str)}")
            except Exception as e:
                context_parts.append(f"## Portfolio\nError: {e}")
        
        # Recent learnings
        if self.consciousness:
            learnings = await self.consciousness.get_recent_learnings(5)
            if learnings:
                learnings_text = "\n".join([f"- {l['learning']}" for l in learnings])
                context_parts.append(f"## Recent Learnings\n{learnings_text}")
        
        # Budget
        if self.consciousness:
            state = await self.consciousness.get_state()
            spend = Decimal(str(state.get("api_spend_today", 0)))
            remaining = DAILY_BUDGET - spend - self.api_spend
            context_parts.append(f"## Budget\nSpent: ${spend + self.api_spend:.4f}\nRemaining: ${remaining:.4f}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_summary(self, mode: str):
        """Generate end-of-cycle summary."""
        summary = {
            "cycle_id": self.cycle_id,
            "mode": mode,
            "messages_processed": self.messages_processed,
            "tasks_executed": self.tasks_executed,
            "trades_executed": self.trades_executed,
            "api_spend": float(self.api_spend),
            "errors": self.errors,
            "timestamp": datetime.now(HK_TZ).isoformat()
        }
        
        # Record observation
        if self.consciousness:
            await self.consciousness.add_observation(
                f"Cycle {self.cycle_id} complete",
                json.dumps(summary, indent=2),
                "system"
            )
        
        logger.info(f"[{self.cycle_id}] Summary: {json.dumps(summary)}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Unified HKEX Trading Agent")
    parser.add_argument(
        "--mode", 
        choices=["scan", "trade", "close", "heartbeat", "auto"],
        default="auto",
        help="Operating mode (default: auto-detect from market hours)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force run even if budget exhausted"
    )
    
    args = parser.parse_args()
    
    # Determine mode
    mode_override = None if args.mode == "auto" else args.mode
    
    # Create and run agent
    agent = UnifiedAgent(mode_override=mode_override)
    
    try:
        await agent.initialize()
        await agent.run()
    except Exception as e:
        logger.error(f"Agent failed: {e}", exc_info=True)
        raise
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
