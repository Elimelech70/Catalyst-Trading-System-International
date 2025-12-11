"""
Name of Application: Catalyst Trading System
Name of file: agent.py
Version: 1.2.0
Last Updated: 2025-12-11
Purpose: Main AI Agent loop that uses Claude to make trading decisions

REVISION HISTORY:
v1.2.0 (2025-12-11) - Fixed model name
- Corrected fallback model from claude-sonnet-4-5 to claude-sonnet-4

v1.1.0 (2025-12-10) - Environment loading fix
- Added dotenv loading for .env file
- Updated for IBGA broker integration

v1.0.0 (2025-12-06) - Initial implementation
- Claude API integration with tool use
- Agentic loop with tool call handling
- Cycle management and logging
- Error handling and graceful shutdown

Description:
This is the main entry point for the Catalyst International trading agent.
It implements the agent loop pattern where Claude receives market context,
decides which tools to use, and the executor handles the tool calls.

Architecture:
    CRON triggers -> Build Context -> Call Claude API -> Claude requests tool
        -> Execute tool -> Return result -> Claude continues -> Loop until done

This single-file agent replaces the 8-service microservices architecture
from the US system, using Claude's decision-making instead of hardcoded
workflow logic.
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import anthropic
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from alerts import create_alert_callback, get_alert_sender
from brokers.ibkr import get_ibkr_client, init_ibkr_client
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
# SYSTEM PROMPT - Claude's Trading Instructions
# =============================================================================

SYSTEM_PROMPT = """You are an autonomous AI trading agent for the Hong Kong Stock Exchange (HKEX).

## Your Role
You make trading decisions during HKEX market hours using the tools available to you.
Every decision you make should be documented with clear reasoning for the audit trail.

## Market Hours (Hong Kong Time)
- Morning session: 09:30 - 12:00
- Lunch break: 12:00 - 13:00 (NO TRADING)
- Afternoon session: 13:00 - 16:00

## Trading Strategy
You are a momentum day trader. Your edge is:
1. Finding stocks with volume spikes (>1.5x average)
2. Confirming with bullish chart patterns
3. Validating with positive news catalysts
4. Using tight risk management (2:1 reward:risk minimum)

## Decision Making Process
For each trading cycle:
1. Check portfolio status first (get_portfolio)
2. Scan for candidates (scan_market)
3. For promising candidates:
   a. Get quote for current price
   b. Get technicals to assess setup
   c. Detect patterns for entry/exit levels
   d. Check news for catalysts
   e. If all align, check risk limits
   f. If approved, execute trade
4. Monitor existing positions for exits
5. Log all decisions with reasoning

## Critical Rules (MUST FOLLOW)
1. ALWAYS call check_risk before execute_trade
2. NEVER trade if check_risk returns approved=false
3. ALWAYS provide reason for every trade and close
4. ALWAYS call log_decision to record your reasoning
5. IMMEDIATELY call close_all if daily loss exceeds 2%
6. PREFER limit orders over market orders
7. CLOSE positions before lunch break (12:00)
8. MAXIMUM 5 positions at any time
9. MAXIMUM 20% of portfolio per position

## Entry Criteria (ALL must be met)
- Volume ratio > 1.5x average
- RSI between 40-70 (not overbought)
- Clear chart pattern with defined entry
- Positive news sentiment or catalyst
- Risk/reward ratio >= 2:1
- Stop loss <= 5% from entry

## Exit Rules
- Take profit at pattern target
- Stop loss if price hits stop level
- Time stop: close if flat after 60 minutes
- ALWAYS close before lunch break

## Response Format
Think step by step. After each tool call, analyze the result and decide
whether to continue gathering information, take action, or conclude.

When you've completed all actions for this cycle, provide a summary of:
- Positions entered/exited
- Key decisions made
- Current portfolio status
- Any warnings or concerns
"""


# =============================================================================
# Agent Class
# =============================================================================


class TradingAgent:
    """AI Trading Agent using Claude API."""

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

        # Initialize Claude client
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = self.config.get("claude", {}).get(
            "model", "claude-sonnet-4-20250514"
        )
        self.max_tokens = self.config.get("claude", {}).get("max_tokens", 4096)
        self.max_iterations = self.config.get("claude", {}).get("max_iterations", 20)

        # Initialize services
        self._init_services()

        # Cycle tracking
        self.cycle_id: str | None = None
        self.executor: Any = None

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
            return {}

    def _init_services(self):
        """Initialize all services."""
        # Database
        try:
            init_database()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

        # IBKR - Use environment variables directly (YAML doesn't expand ${})
        try:
            host = os.environ.get("IBKR_HOST", "127.0.0.1")
            port = int(os.environ.get("IBKR_PORT", "4000"))
            client_id = int(os.environ.get("IBKR_CLIENT_ID", "1"))

            init_ibkr_client(
                host=host,
                port=port,
                client_id=client_id,
            )
            logger.info(f"IBKR client initialized (port {port})")
        except Exception as e:
            logger.error(f"IBKR initialization failed: {e}")

        # Alerts
        try:
            alerts_config = self.config.get("alerts", {})
            get_alert_sender().start()
            logger.info("Alert sender initialized")
        except Exception as e:
            logger.warning(f"Alert sender initialization failed: {e}")

    def run_cycle(self) -> dict:
        """Run one trading cycle.

        Returns:
            Cycle summary dictionary
        """
        # Generate cycle ID
        self.cycle_id = f"hk_{datetime.now(HK_TZ).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        logger.info(f"Starting cycle: {self.cycle_id}")

        # Record cycle start
        db = get_database()
        try:
            db.start_agent_cycle(self.cycle_id, "HKEX")
        except Exception as e:
            logger.error(f"Failed to start cycle in DB: {e}")

        # Create tool executor
        alert_callback = create_alert_callback()
        self.executor = create_tool_executor(
            cycle_id=self.cycle_id,
            alert_callback=alert_callback,
        )

        # Build initial context
        context = self._build_context()

        # Run agent loop
        messages = [{"role": "user", "content": context}]
        tools_called = []
        final_response = ""
        error = None

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

                # Execute tool calls
                tool_results = []
                for tool_block in tool_use_blocks:
                    tool_name = tool_block.name
                    tool_input = tool_block.input

                    logger.info(f"Tool call: {tool_name}")
                    tools_called.append({
                        "tool": tool_name,
                        "input": tool_input,
                    })

                    # Execute
                    result = self.executor.execute(tool_name, tool_input)

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

            # Send error alert
            alert_callback(
                "critical",
                "Agent Cycle Error",
                f"Cycle {self.cycle_id} failed:\n{error}",
            )

        # Get summary
        summary = self.executor.get_summary()

        # Calculate API usage (approximate)
        api_tokens = len(str(messages)) // 4  # Rough estimate
        api_cost = api_tokens * 0.000003  # Claude Sonnet pricing estimate

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

        logger.info(
            f"Cycle completed: {summary['trades_executed']} trades, "
            f"{len(tools_called)} tool calls"
        )

        return {
            "cycle_id": self.cycle_id,
            "status": "error" if error else "completed",
            "trades_executed": summary["trades_executed"],
            "tools_called": len(tools_called),
            "api_tokens": api_tokens,
            "api_cost_usd": round(api_cost, 4),
            "error": error,
            "final_response": final_response[:500] if final_response else None,
        }

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

        # Disconnect IBKR
        try:
            get_ibkr_client().disconnect()
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
    logger.info("Catalyst Trading Agent - HKEX")
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
