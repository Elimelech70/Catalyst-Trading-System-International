"""
Coordinator Agent - The Brain

Continuously running Claude agent that connects to all 3 MCP servers
and orchestrates the trading workflow. Replaces unified_agent.py.

Behavior loop:
  1. Poll position monitor for exit recommendations (every 60s)
  2. Every 30 min: run full scan cycle
  3. Sleep, repeat

Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import sys
import time as time_module
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import anthropic
from mcp import ClientSession
from mcp.client.sse import sse_client

from system_prompt import SYSTEM_PROMPT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("coordinator")

HK_TZ = ZoneInfo("Asia/Hong_Kong")

# Configuration
POLL_INTERVAL = 60  # seconds between recommendation checks
SCAN_INTERVAL = 1800  # 30 minutes between full scan cycles
MAX_ITERATIONS_PER_CYCLE = 35
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
MAX_TOKENS = 4096


# ============================================================================
# MCP Client Connections
# ============================================================================

class MCPConnection:
    """Manages connection to a single MCP server."""

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None
        self._context = None

    async def connect(self):
        """Connect to the MCP server."""
        logger.info(f"Connecting to {self.name} at {self.url}")
        self._context = sse_client(self.url)
        streams = await self._context.__aenter__()
        self._read_stream, self._write_stream = streams
        self.session = ClientSession(self._read_stream, self._write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        tools = await self.session.list_tools()
        tool_names = [t.name for t in tools.tools]
        logger.info(f"Connected to {self.name}: tools={tool_names}")

    async def disconnect(self):
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            if self._context:
                await self._context.__aexit__(None, None, None)
        except Exception:
            pass
        self.session = None
        self._context = None
        logger.info(f"Disconnected from {self.name}")

    async def call_tool(self, tool_name: str, arguments: dict = None) -> Any:
        """Call a tool on this MCP server."""
        if not self.session:
            raise RuntimeError(f"Not connected to {self.name}")
        result = await self.session.call_tool(tool_name, arguments or {})
        # Extract text content
        if result.content and len(result.content) > 0:
            text = result.content[0].text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}
        return {}


class MCPHub:
    """Manages connections to all MCP servers."""

    def __init__(self, config: dict):
        self.connections: Dict[str, MCPConnection] = {}
        for name, server_config in config.get("mcpServers", {}).items():
            self.connections[name] = MCPConnection(name, server_config["url"])

    async def connect_all(self):
        for conn in self.connections.values():
            try:
                await conn.connect()
            except Exception as e:
                logger.error(f"Failed to connect to {conn.name}: {e}")

    async def disconnect_all(self):
        for conn in self.connections.values():
            try:
                await conn.disconnect()
            except Exception:
                pass

    def get(self, name: str) -> MCPConnection:
        conn = self.connections.get(name)
        if not conn:
            raise KeyError(f"No MCP server named '{name}'")
        return conn

    async def call(self, server_name: str, tool_name: str, arguments: dict = None) -> Any:
        """Call a tool on a named MCP server."""
        return await self.get(server_name).call_tool(tool_name, arguments)


# ============================================================================
# Tool adapter for Claude API
# ============================================================================

def build_claude_tools(hub: MCPHub) -> List[dict]:
    """Build Claude API tool definitions from all MCP servers.

    Prefixes tool names with server name to avoid collisions:
    e.g., 'position-monitor__get_exit_recommendations'
    """
    tools = []
    # Define tools manually to match the plan exactly.
    # This maps Claude tool names -> (mcp_server, mcp_tool_name)
    tool_map = {
        # Position Monitor
        "get_exit_recommendations": ("position-monitor", "get_exit_recommendations"),
        "get_position_health": ("position-monitor", "get_position_health"),
        "acknowledge_recommendation": ("position-monitor", "acknowledge_recommendation"),
        # Market Scanner
        "scan_market": ("market-scanner", "scan_market"),
        "get_quote": ("market-scanner", "get_quote"),
        "get_technicals": ("market-scanner", "get_technicals"),
        "detect_patterns": ("market-scanner", "detect_patterns"),
        "get_news": ("market-scanner", "get_news"),
        # Trade Executor
        "get_portfolio": ("trade-executor", "get_portfolio"),
        "execute_trade": ("trade-executor", "execute_trade"),
        "close_position": ("trade-executor", "close_position"),
        "close_all": ("trade-executor", "close_all"),
        "sync_positions": ("trade-executor", "sync_positions"),
        "check_risk": ("trade-executor", "check_risk"),
        "log_decision": ("trade-executor", "log_decision"),
    }
    return tool_map


# ============================================================================
# Coordinator
# ============================================================================

class Coordinator:
    """
    The Brain. Continuously running coordinator that connects to all
    MCP agents and orchestrates trading decisions.
    """

    def __init__(self, mcp_config: dict):
        self.hub = MCPHub(mcp_config)
        self.anthropic = anthropic.Anthropic()
        self.running = True
        self.last_scan_time: Optional[datetime] = None

        # We reuse the existing tools.py TOOLS for Claude API schema
        # but route calls through MCP
        self._tool_map = build_claude_tools(self.hub)

    async def start(self):
        """Start the coordinator."""
        logger.info("=" * 60)
        logger.info("Coordinator Agent Starting")
        logger.info(f"Model: {MODEL}")
        logger.info("=" * 60)

        await self.hub.connect_all()

        # Initial sync
        try:
            sync_result = await self.hub.call("trade-executor", "sync_positions")
            logger.info(f"Initial sync: {sync_result}")
        except Exception as e:
            logger.warning(f"Initial sync failed: {e}")

    async def stop(self):
        """Stop the coordinator."""
        self.running = False
        await self.hub.disconnect_all()
        logger.info("Coordinator stopped")

    def _is_market_open(self) -> bool:
        if os.environ.get("FORCE_MARKET_OPEN"):
            return True
        now = datetime.now(HK_TZ)
        if now.weekday() >= 5:
            return False
        ct = now.time()
        if time(9, 30) <= ct < time(12, 0):
            return True
        if time(13, 0) <= ct < time(16, 0):
            return True
        return False

    def _should_run_scan(self) -> bool:
        """Check if it's time for a full scan cycle."""
        if self.last_scan_time is None:
            return True
        elapsed = (datetime.now(HK_TZ) - self.last_scan_time).total_seconds()
        return elapsed >= SCAN_INTERVAL

    # ----- Recommendation handling -----

    async def _handle_recommendations(self):
        """Check for and act on exit recommendations."""
        try:
            recs = await self.hub.call("position-monitor", "get_exit_recommendations")
        except Exception as e:
            logger.warning(f"Failed to get recommendations: {e}")
            return

        count = recs.get("count", 0)
        if count == 0:
            return

        logger.info(f"Processing {count} exit recommendations")

        for rec in recs.get("recommendations", []):
            symbol = rec["symbol"]
            recommendation = rec["recommendation"]
            reason = rec.get("reason", "")
            monitor_id = rec["monitor_id"]

            logger.info(f"  {symbol}: {recommendation} - {reason}")

            action_taken = "held"

            if recommendation == "EXIT":
                # Execute close immediately
                try:
                    result = await self.hub.call("trade-executor", "close_position", {
                        "symbol": symbol,
                        "reason": f"Monitor EXIT: {reason}",
                    })
                    if result.get("success"):
                        action_taken = "closed"
                        logger.info(f"  Closed {symbol}: {result}")
                    else:
                        logger.warning(f"  Close failed for {symbol}: {result}")
                        action_taken = "close_failed"
                except Exception as e:
                    logger.error(f"  Error closing {symbol}: {e}")
                    action_taken = "error"

            elif recommendation == "CONSULT_AI":
                # Get more data and let Claude decide
                action_taken = await self._consult_on_position(rec)

            # Acknowledge the recommendation
            try:
                await self.hub.call("position-monitor", "acknowledge_recommendation", {
                    "monitor_id": monitor_id,
                    "action_taken": action_taken,
                })
            except Exception as e:
                logger.warning(f"Failed to acknowledge {monitor_id}: {e}")

    async def _consult_on_position(self, rec: dict) -> str:
        """Use Claude to decide on a CONSULT_AI recommendation."""
        symbol = rec["symbol"]

        # Gather data
        try:
            quote_data = await self.hub.call("market-scanner", "get_quote", {"symbol": symbol})
            tech_data = await self.hub.call("market-scanner", "get_technicals", {"symbol": symbol})
        except Exception as e:
            logger.warning(f"Failed to get data for {symbol}: {e}")
            return "held"

        prompt = f"""A position monitor flagged {symbol} for review.

POSITION:
- Entry price: HKD {rec.get('entry_price', '?')}
- Quantity: {rec.get('quantity', '?')}
- Side: {rec.get('side', '?')}

MONITOR REASON: {rec.get('reason', 'Unknown')}

CURRENT QUOTE: {json.dumps(quote_data.get('quote', {}), default=str)}
TECHNICALS: {json.dumps(tech_data.get('technicals', {}), default=str)}

Should I CLOSE this position or HOLD? Reply with just CLOSE or HOLD on the first line, then a brief reason."""

        try:
            response = self.anthropic.messages.create(
                model=MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            first_line = text.split("\n")[0].upper()

            if "CLOSE" in first_line:
                result = await self.hub.call("trade-executor", "close_position", {
                    "symbol": symbol,
                    "reason": f"AI consultation: {text[:100]}",
                })
                logger.info(f"  AI decided CLOSE for {symbol}: {text[:80]}")
                return "closed"
            else:
                logger.info(f"  AI decided HOLD for {symbol}: {text[:80]}")
                return "held"
        except Exception as e:
            logger.error(f"AI consultation failed: {e}")
            return "held"

    # ----- Full scan cycle -----

    async def _run_scan_cycle(self):
        """Run a full scan cycle using Claude AI loop."""
        self.last_scan_time = datetime.now(HK_TZ)
        logger.info("=" * 60)
        logger.info(f"SCAN CYCLE - {self.last_scan_time.strftime('%H:%M:%S %Z')}")
        logger.info("=" * 60)

        context = f"""## Trading Cycle Context

**Date/Time**: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT
**Mode**: Paper Trading (Multi-Agent MCP Architecture)

## Your Task
Execute your trading strategy for this cycle:
1. Check current portfolio (get_portfolio)
2. Scan for new opportunities (scan_market)
3. Analyze top candidates (get_quote, get_technicals, detect_patterns, get_news)
4. Execute trades if criteria met (check_risk -> execute_trade)
5. Log all decisions (log_decision)

Begin by checking portfolio, then scan the market."""

        messages = [{"role": "user", "content": context}]
        tools_called = 0
        trades_executed = 0

        # Import tool schemas from tools.py
        try:
            sys.path.insert(0, "/app")
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from tools import TOOLS
        except ImportError:
            logger.warning("Could not import TOOLS from tools.py, using empty tools")
            TOOLS = []

        try:
            for iteration in range(MAX_ITERATIONS_PER_CYCLE):
                logger.info(f"Iteration {iteration + 1}/{MAX_ITERATIONS_PER_CYCLE}")

                response = self.anthropic.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )

                messages.append({"role": "assistant", "content": response.content})

                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
                if not tool_use_blocks:
                    for block in response.content:
                        if hasattr(block, "text"):
                            logger.info(f"Claude final: {block.text[:200]}")
                    break

                tool_results = []
                for tool_block in tool_use_blocks:
                    tool_name = tool_block.name
                    tool_input = tool_block.input
                    tools_called += 1

                    logger.info(f"  Tool: {tool_name}({json.dumps(tool_input)[:100]})")

                    # Route through MCP
                    if tool_name == "send_alert":
                        # Handle locally - not routed through MCP
                        logger.info(f"ALERT [{tool_input.get('severity', 'info')}]: {tool_input.get('subject', '')} - {tool_input.get('message', '')}")
                        result = {"sent": True, "success": True}
                    else:
                        server_name, mcp_tool = self._tool_map.get(tool_name, (None, None))
                        if server_name:
                            try:
                                result = await self.hub.call(server_name, mcp_tool, tool_input)
                            except Exception as e:
                                result = {"error": str(e), "success": False}
                        else:
                            result = {"error": f"Unknown tool: {tool_name}", "success": False}

                    # Track trades
                    if tool_name == "execute_trade" and result.get("success"):
                        trades_executed += 1

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(result, default=str),
                    })

                messages.append({"role": "user", "content": tool_results})

                if response.stop_reason == "end_turn":
                    break

        except Exception as e:
            logger.error(f"Scan cycle error: {e}", exc_info=True)

        logger.info(f"Scan cycle complete: {tools_called} tools, {trades_executed} trades")
        return {"tools_called": tools_called, "trades_executed": trades_executed}

    # ----- Main loop -----

    async def run(self):
        """Main coordinator loop."""
        await self.start()

        while self.running:
            try:
                if not self._is_market_open():
                    # Sleep until market opens
                    now = datetime.now(HK_TZ)
                    logger.info(f"Market closed ({now.strftime('%H:%M')} HKT). Sleeping...")
                    await asyncio.sleep(300)  # Check every 5 min
                    continue

                # Priority 1: Handle exit recommendations
                await self._handle_recommendations()

                # Priority 2: Run scan cycle if due
                if self._should_run_scan():
                    await self._run_scan_cycle()

                # Sleep between polls
                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Coordinator loop error: {e}", exc_info=True)
                await asyncio.sleep(60)

        await self.stop()


# ============================================================================
# Entry point
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Coordinator Agent")
    parser.add_argument("--force", action="store_true", help="Run even if market closed")
    parser.add_argument("--once", action="store_true", help="Run one cycle then exit")
    args = parser.parse_args()

    if args.force:
        os.environ["FORCE_MARKET_OPEN"] = "1"

    # Load MCP config
    config_paths = [
        "mcp_config.json",
        "agents/coordinator/mcp_config.json",
        os.path.join(os.path.dirname(__file__), "mcp_config.json"),
    ]
    config = None
    for path in config_paths:
        try:
            with open(path) as f:
                config = json.load(f)
                break
        except FileNotFoundError:
            continue

    if not config:
        logger.error("mcp_config.json not found")
        sys.exit(1)

    coordinator = Coordinator(config)

    if args.once:
        await coordinator.start()
        await coordinator._handle_recommendations()
        await coordinator._run_scan_cycle()
        await coordinator.stop()
    else:
        await coordinator.run()


if __name__ == "__main__":
    asyncio.run(main())
