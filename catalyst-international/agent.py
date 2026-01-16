"""
Name of Application: Catalyst Trading System
Name of file: agent.py
Version: 2.3.0
Last Updated: 2026-01-06
Purpose: Main AI Agent loop with real-time workflow tracking

REVISION HISTORY:
v2.3.0 (2026-01-06) - Added workflow tracking
- Integrated WorkflowTracker for real-time phase visibility
- Tracks: INIT → PORTFOLIO → SCAN → ANALYZE → DECIDE → VALIDATE → EXECUTE → MONITOR → LOG → COMPLETE
- Progress stored in consciousness DB (viewable via MCP/dashboard)
- Console progress bar during execution
- Phase timing and results recorded

v2.2.0 (2026-01-02) - Relaxed entry criteria for paper trading
- Changed from AND-based to TIERED entry criteria (Tier 1/2/3)
- RSI range expanded to 30-75 (was 40-70)
- Pattern OR catalyst acceptable (was AND)
- Breakout within 1% counts (was exact)
- Added Tier 3 "learning trades" at half size
- Daily loss limit 5% for paper mode (was 2%)
- Position size 25% for paper mode (was 20%)

v2.1.0 (2025-12-30) - Updated to use MoomooClient
- Changed imports from futu to moomoo
- Updated env vars: FUTU_* to MOOMOO_*
- Using moomoo-api SDK (not futu-api)

v2.0.0 (2025-12-20) - Migrated to Moomoo/Futu
- Replaced IBKR with Futu broker client via OpenD
- Removed IBGA pre-flight checks (no longer needed)
- Simpler authentication (no 2FA issues)

v1.3.0 (2025-12-15) - Added pre-flight IBGA verification (deprecated)
v1.2.0 (2025-12-11) - Fixed model name
v1.1.0 (2025-12-10) - Environment loading fix
v1.0.0 (2025-12-06) - Initial implementation

Description:
This is the main entry point for the Catalyst International trading agent.
It implements the agent loop pattern where Claude receives market context,
decides which tools to use, and the executor handles the tool calls.

Architecture:
    CRON triggers -> Build Context -> Call Claude API -> Claude requests tool
        -> Execute tool -> Return result -> Claude continues -> Loop until done

WORKFLOW PHASES:
    1. INIT       - Agent waking up, loading config
    2. PORTFOLIO  - Checking current positions
    3. SCAN       - Finding momentum candidates  
    4. ANALYZE    - Evaluating candidates (quote, technicals, patterns, news)
    5. DECIDE     - Applying entry criteria
    6. VALIDATE   - Risk check
    7. EXECUTE    - Placing orders
    8. MONITOR    - Position monitoring started
    9. LOG        - Recording decisions
    10. COMPLETE  - Cycle finished
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import anthropic
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from alerts import create_alert_callback, get_alert_sender
from brokers.moomoo import get_moomoo_client, init_moomoo_client
from data.database import get_database, init_database
from safety import get_safety_validator
from tool_executor import create_tool_executor
from tools import TOOLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/agent.log"),
    ],
)
logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")


# =============================================================================
# WORKFLOW TRACKER - Real-time visibility into trading cycle
# =============================================================================

class WorkflowTracker:
    """Track workflow phases in real-time.
    
    Stores progress in the consciousness database for visibility
    via MCP tools and web dashboard.
    """
    
    # All phases in order
    ALL_PHASES = ["INIT", "PORTFOLIO", "SCAN", "ANALYZE", "DECIDE", "VALIDATE", "EXECUTE", "MONITOR", "LOG", "COMPLETE"]
    
    def __init__(self, cycle_id: str, agent_id: str = "intl_claude"):
        self.cycle_id = cycle_id
        self.agent_id = agent_id
        self.phases: List[Dict] = []
        self.current_phase: Optional[str] = None
        self.started_at = datetime.now(HK_TZ)
        self._pool = None
        
    async def connect(self):
        """Connect to consciousness database."""
        if self._pool is None:
            database_url = os.environ.get("RESEARCH_DATABASE_URL")
            if database_url:
                try:
                    import asyncpg
                    self._pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)
                    logger.debug("WorkflowTracker connected to consciousness DB")
                except Exception as e:
                    logger.warning(f"Could not connect to consciousness DB: {e}")
                    
    async def disconnect(self):
        """Disconnect from database."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            
    async def start_phase(self, phase: str, description: str = "", details: Dict[str, Any] = None):
        """Start a new workflow phase."""
        now = datetime.now(HK_TZ)
        
        record = {
            "phase": phase,
            "status": "started",
            "started_at": now.isoformat(),
            "completed_at": None,
            "duration_ms": None,
            "details": details or {"description": description},
            "error": None
        }
        self.phases.append(record)
        self.current_phase = phase
        
        logger.info(f"[{self.cycle_id}] ▶ Phase {phase}: {description}")
        self._print_progress_bar()
        
        await self._store_progress()
        
    async def complete_phase(self, phase: str, **results):
        """Complete a workflow phase."""
        now = datetime.now(HK_TZ)
        
        for record in reversed(self.phases):
            if record["phase"] == phase and record["status"] == "started":
                started = datetime.fromisoformat(record["started_at"])
                record["status"] = "completed"
                record["completed_at"] = now.isoformat()
                record["duration_ms"] = int((now - started).total_seconds() * 1000)
                if results:
                    record["details"] = {**(record["details"] or {}), **results}
                break
                
        result_str = ", ".join(f"{k}={v}" for k, v in results.items()) if results else ""
        logger.info(f"[{self.cycle_id}] ✓ Phase {phase} completed ({result_str})")
        self._print_progress_bar()
        
        await self._store_progress()
        
    async def error_phase(self, phase: str, error: str):
        """Mark a phase as errored."""
        now = datetime.now(HK_TZ)
        
        for record in reversed(self.phases):
            if record["phase"] == phase and record["status"] == "started":
                started = datetime.fromisoformat(record["started_at"])
                record["status"] = "error"
                record["completed_at"] = now.isoformat()
                record["duration_ms"] = int((now - started).total_seconds() * 1000)
                record["error"] = error
                break
                
        logger.error(f"[{self.cycle_id}] ✗ Phase {phase} error: {error}")
        
        await self._store_progress()
        
    async def _store_progress(self):
        """Store current progress in consciousness database."""
        if not self._pool:
            await self.connect()
            
        if not self._pool:
            return
            
        try:
            progress = {
                "cycle_id": self.cycle_id,
                "agent_id": self.agent_id,
                "started_at": self.started_at.isoformat(),
                "current_phase": self.current_phase,
                "phases": self.phases,
                "updated_at": datetime.now(HK_TZ).isoformat()
            }
            
            async with self._pool.acquire() as conn:
                # Store as observation with type 'workflow'
                await conn.execute("""
                    INSERT INTO claude_observations 
                    (agent_id, obs_type, subject, content, confidence, created_at)
                    VALUES ($1, 'workflow', $2, $3, 1.0, NOW())
                    ON CONFLICT ON CONSTRAINT claude_observations_pkey DO UPDATE SET 
                        content = EXCLUDED.content,
                        created_at = NOW()
                """, self.agent_id, f"cycle:{self.cycle_id}", json.dumps(progress))
                
        except Exception as e:
            logger.debug(f"Could not store workflow progress: {e}")
            
    def _print_progress_bar(self):
        """Print a visual progress bar to console."""
        completed = {r["phase"] for r in self.phases if r["status"] == "completed"}
        current = self.current_phase
        
        bar = "["
        for phase in self.ALL_PHASES:
            if phase in completed:
                bar += "█"
            elif phase == current:
                bar += "▓"
            else:
                bar += "░"
        bar += "]"
        
        pct = (len(completed) / len(self.ALL_PHASES)) * 100
        try:
            print(f"\r{bar} {pct:.0f}% - {current or 'Starting...'}", end="", flush=True)
            if current == "COMPLETE" or pct == 100:
                print()  # Newline when done
        except BrokenPipeError:
            pass  # Ignore if stdout is closed
            
    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary."""
        completed = [p for p in self.phases if p["status"] == "completed"]
        errors = [p for p in self.phases if p["status"] == "error"]
        total_duration = sum(p.get("duration_ms", 0) or 0 for p in self.phases)
        
        return {
            "cycle_id": self.cycle_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at.isoformat(),
            "current_phase": self.current_phase,
            "phases_completed": len(completed),
            "phases_total": len(self.phases),
            "errors": len(errors),
            "total_duration_ms": total_duration,
            "phase_details": self.phases
        }


# =============================================================================
# SYSTEM PROMPT - Claude's Trading Instructions
# =============================================================================

SYSTEM_PROMPT = """You are an autonomous AI trading agent for the Hong Kong Stock Exchange (HKEX).

## Your Role
You make trading decisions during HKEX market hours using the tools available to you.
Every decision you make should be documented with clear reasoning for the audit trail.

## PAPER TRADING MODE - LEARNING FIRST
**This is paper trading. We are here to LEARN, not to be perfect.**

Philosophy:
- PREFER action over inaction when setups look reasonable
- A trade that loses teaches us something
- A missed trade teaches us nothing
- We learn by doing, not by waiting for perfection
- Document everything so we can analyze later

The goal is to generate LEARNING DATA, not to preserve fake capital.

## Market Hours (Hong Kong Time)
- Morning session: 09:30 - 12:00
- Lunch break: 12:00 - 13:00 (NO TRADING)
- Afternoon session: 13:00 - 16:00

## Trading Strategy
You are a momentum day trader. Your edge is:
1. Finding stocks with volume spikes (>1.5x average)
2. Confirming with bullish chart patterns OR positive catalysts
3. Using risk management (2:1 reward:risk minimum)

## Decision Making Process
For each trading cycle:
1. Check portfolio status first (get_portfolio)
2. Scan for candidates (scan_market)
3. For promising candidates:
   a. Get quote for current price
   b. Get technicals to assess setup
   c. Detect patterns for entry/exit levels
   d. Check news for catalysts
   e. EVALUATE using tiered criteria below
   f. If Tier 1 or Tier 2, check risk then trade
4. Monitor existing positions for exits
5. Log all decisions with reasoning

## Critical Rules (MUST FOLLOW)
1. **ALWAYS** call check_risk before execute_trade
2. **NEVER** trade if check_risk returns approved=false
3. **ALWAYS** provide reason for every trade and close
4. **ALWAYS** call log_decision to record your reasoning
5. **IMMEDIATELY** call close_all if daily loss exceeds 5% (paper mode)
6. **PREFER** limit orders over market orders
7. **CLOSE** positions before lunch break (12:00) unless strong conviction
8. **MAXIMUM** 15 positions at any time
9. **MAXIMUM** 25% of portfolio per position (paper mode allows larger)

## TIERED ENTRY CRITERIA (Use ANY tier that matches)

### Tier 1 - Strong Setup (TRADE FULL SIZE)
Requirements (ALL of these):
- Volume ratio > 2.0x average
- RSI between 30-70
- Clear chart pattern with defined entry
- Positive news catalyst (sentiment > 0.2)
- Risk/reward ratio >= 2:1

### Tier 2 - Good Setup (TRADE FULL SIZE)
Requirements:
- Volume ratio > 1.5x average
- RSI between 30-75
- EITHER: Clear pattern OR Positive catalyst (don't need both!)
- Risk/reward ratio >= 1.5:1
- Price within 1% of breakout level counts as "at breakout"

### Tier 3 - Learning Trade (TRADE HALF SIZE)
Requirements:
- Volume ratio > 1.3x average
- RSI between 25-80 (wider range)
- Strong momentum (price up > 3% today)
- At least one of: pattern forming, news mention, sector strength
- Risk/reward ratio >= 1.5:1
- Log as "learning trade" for analysis

### When to PASS
Only skip a trade if:
- RSI > 80 (severely overbought) or < 20 (oversold crash)
- Volume is BELOW average (no interest)
- check_risk returns false
- Already at max positions (15)
- No clear stop loss level identifiable

## Pattern Detection - Relaxed Rules
- "Within 1% of breakout" = close enough, take it
- "Approaching resistance" = valid setup if volume confirms
- Don't require EXACT breakout - momentum traders anticipate

## News Catalyst - Relaxed Rules
- Sentiment > 0.0 (any positive) = acceptable catalyst for Tier 2/3
- Sector news counts (e.g., "tech sector rally" benefits tech stocks)
- No news is NOT a blocker if pattern is strong

## Exit Rules
- Take profit at pattern target
- Stop loss if price hits stop level
- Time stop: close if flat after 60 minutes
- Trail stop to breakeven after +2% gain
- CLOSE before lunch break unless conviction is high

## Response Format
Think step by step. After each tool call, analyze the result and decide
whether to continue gathering information, take action, or conclude.

When evaluating a candidate, explicitly state:
- Which TIER does this setup match?
- What's the specific entry trigger?
- What's the stop loss level?
- What's the profit target?

When you've completed all actions for this cycle, provide a summary of:
- Positions entered/exited (with tier classification)
- Key decisions made and WHY
- Candidates that almost qualified (for learning)
- Current portfolio status
- Any patterns noticed across candidates
"""


# =============================================================================
# Agent Class
# =============================================================================


class TradingAgent:
    """AI Trading Agent using Claude API with workflow tracking."""

    def __init__(
        self,
        config_path: str = "config/settings.yaml",
        paper_trading: bool = True,
    ):
        """Initialize the trading agent.

        Args:
            config_path: Path to configuration file
            paper_trading: Use paper trading (True) or live (False)
        """
        self.config = self._load_config(config_path)
        self.paper_trading = paper_trading
        self.tracker: Optional[WorkflowTracker] = None

        # Initialize Claude client
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = self.config.get("claude", {}).get(
            "model", "claude-sonnet-4-20250514"
        )
        self.max_tokens = self.config.get("claude", {}).get("max_tokens", 4096)
        self.max_iterations = self.config.get("claude", {}).get("max_iterations", 15)

        # Initialize components
        init_database()
        init_moomoo_client(paper_trading=paper_trading)

        self.cycle_id = None
        self.executor = None

        logger.info(f"Agent initialized: model={self.model}, paper={paper_trading}")

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def run_cycle(self) -> dict:
        """Run one trading cycle with workflow tracking.

        Returns:
            Cycle summary dictionary
        """
        # Generate cycle ID
        self.cycle_id = f"hk_{datetime.now(HK_TZ).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Initialize workflow tracker
        self.tracker = WorkflowTracker(self.cycle_id, "intl_claude")
        
        # Run async workflow
        return asyncio.run(self._run_cycle_async())
        
    async def _run_cycle_async(self) -> dict:
        """Async implementation of the trading cycle."""
        logger.info(f"Starting cycle: {self.cycle_id}")
        
        db = get_database()
        alert_callback = create_alert_callback()
        
        # =================================================================
        # PHASE 1: INIT
        # =================================================================
        await self.tracker.start_phase("INIT", "Agent initializing")
        
        try:
            db.start_agent_cycle(self.cycle_id, "HKEX")
        except Exception as e:
            logger.error(f"Failed to start cycle in DB: {e}")
            
        self.executor = create_tool_executor(
            cycle_id=self.cycle_id,
            alert_callback=alert_callback,
            agent=self,
        )
        
        await self.tracker.complete_phase("INIT", 
            model=self.model, 
            paper_trading=self.paper_trading
        )

        # Build context and run
        context = self._build_context()
        messages = [{"role": "user", "content": context}]
        tools_called = []
        final_response = ""
        error = None
        
        # Track what phase we're in based on tool calls
        current_workflow_phase = "PORTFOLIO"  # First expected action
        phase_started = False
        candidates_count = 0
        analyzed_count = 0
        trades_executed = 0

        try:
            for iteration in range(self.max_iterations):
                logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")

                # Call Claude
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )

                # Process response
                assistant_message = {"role": "assistant", "content": response.content}
                messages.append(assistant_message)

                # Check for tool use
                tool_use_blocks = [
                    block for block in response.content
                    if block.type == "tool_use"
                ]

                if not tool_use_blocks:
                    # No more tools, extract final text
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_response = block.text
                    break

                # Execute tool calls and track workflow phases
                tool_results = []
                for tool_block in tool_use_blocks:
                    tool_name = tool_block.name
                    tool_input = tool_block.input

                    # =============================================================
                    # UPDATE WORKFLOW PHASE BASED ON TOOL BEING CALLED
                    # =============================================================
                    new_phase = self._tool_to_phase(tool_name, current_workflow_phase)
                    
                    if new_phase != current_workflow_phase:
                        # Complete previous phase
                        if phase_started:
                            if current_workflow_phase == "SCAN":
                                await self.tracker.complete_phase(current_workflow_phase, candidates=candidates_count)
                            elif current_workflow_phase == "ANALYZE":
                                await self.tracker.complete_phase(current_workflow_phase, analyzed=analyzed_count)
                            elif current_workflow_phase == "EXECUTE":
                                await self.tracker.complete_phase(current_workflow_phase, trades=trades_executed)
                            else:
                                await self.tracker.complete_phase(current_workflow_phase)
                        
                        # Start new phase
                        current_workflow_phase = new_phase
                        await self.tracker.start_phase(new_phase, f"Running {tool_name}")
                        phase_started = True

                    logger.info(f"Tool call: {tool_name}")
                    tools_called.append({
                        "tool": tool_name,
                        "input": tool_input,
                    })

                    # Execute
                    result = self.executor.execute(tool_name, tool_input)
                    
                    # Track counts for phase details
                    if tool_name == "scan_market" and isinstance(result, dict):
                        candidates_count = len(result.get("candidates", []))
                    elif tool_name in ["get_quote", "get_technicals", "detect_patterns", "get_news"]:
                        analyzed_count += 1
                    elif tool_name == "execute_trade" and isinstance(result, dict):
                        if result.get("status") == "filled" or result.get("order_id"):
                            trades_executed += 1

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(result),
                    })

                # Add tool results to messages
                messages.append({"role": "user", "content": tool_results})

                # Check stop reason
                if response.stop_reason == "end_turn":
                    break

        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)
            error = str(e)
            await self.tracker.error_phase(current_workflow_phase, error)

            alert_callback(
                "critical",
                "Agent Cycle Error",
                f"Cycle {self.cycle_id} failed:\n{error}",
            )

        # =================================================================
        # PHASE 9: LOG
        # =================================================================
        if not error:
            # Complete the last active phase
            if phase_started:
                await self.tracker.complete_phase(current_workflow_phase)
                
            await self.tracker.start_phase("LOG", "Recording decisions")

        # Get summary
        summary = self.executor.get_summary()

        # Calculate API usage
        api_tokens = len(str(messages)) // 4
        api_cost = api_tokens * 0.000003

        # Record cycle completion
        try:
            db.complete_agent_cycle(
                cycle_id=self.cycle_id,
                tools_called=tools_called,
                trades_executed=summary["trades_executed"],
                api_tokens_used=api_tokens,
                api_cost_usd=api_cost,
                final_response=final_response,
                error=error,
            )
        except Exception as e:
            logger.error(f"Failed to complete cycle in DB: {e}")

        if not error:
            await self.tracker.complete_phase("LOG", 
                tools_called=len(tools_called),
                api_cost=round(api_cost, 4)
            )

        # =================================================================
        # PHASE 10: COMPLETE
        # =================================================================
        if not error:
            await self.tracker.start_phase("COMPLETE", "Cycle finished")
            await self.tracker.complete_phase("COMPLETE",
                trades_executed=summary["trades_executed"],
                decisions_logged=summary.get("decisions_logged", 0),
                duration_sec=int((datetime.now(HK_TZ) - self.tracker.started_at).total_seconds())
            )

        # Disconnect tracker
        await self.tracker.disconnect()

        logger.info(
            f"Cycle completed: {summary['trades_executed']} trades, "
            f"{len(tools_called)} tool calls"
        )
        
        # Print final workflow summary
        print("\n" + "=" * 60)
        print("WORKFLOW SUMMARY")
        print("=" * 60)
        wf_summary = self.tracker.get_summary()
        print(f"Phases completed: {wf_summary['phases_completed']}/{len(self.tracker.ALL_PHASES)}")
        print(f"Total duration: {wf_summary['total_duration_ms']}ms")
        print(f"Errors: {wf_summary['errors']}")

        return {
            "cycle_id": self.cycle_id,
            "status": "error" if error else "completed",
            "trades_executed": summary["trades_executed"],
            "tools_called": len(tools_called),
            "api_tokens": api_tokens,
            "api_cost_usd": round(api_cost, 4),
            "error": error,
            "final_response": final_response[:500] if final_response else None,
            "workflow": wf_summary,
        }
        
    def _tool_to_phase(self, tool_name: str, current_phase: str) -> str:
        """Map tool name to workflow phase."""
        phase_map = {
            "get_portfolio": "PORTFOLIO",
            "scan_market": "SCAN",
            "get_quote": "ANALYZE",
            "get_technicals": "ANALYZE",
            "detect_patterns": "ANALYZE",
            "get_news": "ANALYZE",
            "check_risk": "VALIDATE",
            "execute_trade": "EXECUTE",
            "close_position": "EXECUTE",
            "close_all": "EXECUTE",
            "send_alert": "LOG",
            "log_decision": "LOG",
        }
        
        new_phase = phase_map.get(tool_name, current_phase)
        
        # Don't go backwards in phases
        phase_order = self.tracker.ALL_PHASES
        current_idx = phase_order.index(current_phase) if current_phase in phase_order else 0
        new_idx = phase_order.index(new_phase) if new_phase in phase_order else current_idx
        
        if new_idx >= current_idx:
            return new_phase
        return current_phase

    def _build_context(self) -> str:
        """Build initial context for Claude."""
        now = datetime.now(HK_TZ)

        context = f"""## Trading Cycle Context

**Date/Time**: {now.strftime('%Y-%m-%d %H:%M:%S')} HKT ({now.strftime('%A')})
**Cycle ID**: {self.cycle_id}
**Mode**: {'Paper Trading' if self.paper_trading else 'LIVE TRADING'}

## Your Task

Execute your trading strategy for this cycle:
1. Check current portfolio status
2. Scan for new opportunities
3. Analyze top candidates
4. Execute trades if criteria met
5. Monitor and manage existing positions
6. Log all decisions

Begin by checking the portfolio status, then scan the market for candidates.
Make sure to log your decisions and reasoning throughout.
"""
        return context

    def check_market_hours(self) -> tuple[bool, str]:
        """Check if market is currently open."""
        validator = get_safety_validator()
        return validator.is_market_open()

    def shutdown(self):
        """Clean shutdown of the agent."""
        logger.info("Shutting down agent...")

        # Stop alert sender
        try:
            get_alert_sender().stop()
        except Exception:
            pass

        # Disconnect broker
        try:
            client = get_moomoo_client()
            if client:
                client.disconnect()
        except Exception:
            pass

        logger.info("Agent shutdown complete")


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Catalyst Trading Agent for HKEX"
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live trading (default is paper)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if market is closed",
    )
    args = parser.parse_args()

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    logger.info("=" * 60)
    logger.info("Catalyst Trading Agent - HKEX (v2.3.0 with Workflow Tracking)")
    logger.info("=" * 60)

    # Initialize agent
    agent = TradingAgent(
        config_path=args.config,
        paper_trading=not args.live,
    )

    # Check market hours
    is_open, status = agent.check_market_hours()
    logger.info(f"Market status: {status}")

    if not is_open and not args.force:
        logger.info("Market is closed. Use --force to run anyway.")
        return

    try:
        # Run one cycle
        result = agent.run_cycle()

        # Print summary
        print("\n" + "=" * 60)
        print("CYCLE SUMMARY")
        print("=" * 60)
        print(f"Cycle ID: {result['cycle_id']}")
        print(f"Status: {result['status']}")
        print(f"Trades Executed: {result['trades_executed']}")
        print(f"Tools Called: {result['tools_called']}")
        print(f"API Tokens (est): {result['api_tokens']}")
        print(f"API Cost (est): ${result['api_cost_usd']:.4f}")

        if result['error']:
            print(f"\nError: {result['error']}")

        if result['final_response']:
            print(f"\nFinal Response:\n{result['final_response']}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
