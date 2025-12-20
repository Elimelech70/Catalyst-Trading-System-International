"""
Name of Application: Catalyst Trading System
Name of file: tool_executor.py
Version: 2.0.0
Last Updated: 2025-12-20
Purpose: Routes Claude's tool calls to actual implementations

REVISION HISTORY:
v2.0.0 (2025-12-20) - Migrated to Moomoo/Futu
- Replaced IBKR with Futu broker client
- Updated all broker references

v1.0.0 (2025-12-06) - Initial implementation
- Tool call routing and execution
- Result formatting for Claude
- Error handling and logging

Description:
This module receives tool calls from Claude and routes them to the
appropriate implementation functions. It handles all 12 trading tools
defined in the CLAUDE.md specification.
"""

import json
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from brokers.futu import get_futu_client
from data.database import get_database
from data.market import get_market_data
from data.news import get_news_client
from data.patterns import get_pattern_detector
from safety import get_safety_validator, validate_trade_request
from tools import validate_tool_input

logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")


class ToolExecutor:
    """Executes tool calls from Claude."""

    def __init__(
        self,
        cycle_id: str,
        alert_callback: Any = None,
    ):
        """Initialize tool executor.

        Args:
            cycle_id: Current agent cycle ID
            alert_callback: Function to send alerts (severity, subject, message)
        """
        self.cycle_id = cycle_id
        self.alert_callback = alert_callback
        self.tools_called: list[dict] = []
        self.trades_executed = 0

        # Initialize services
        self.broker = get_futu_client()
        self.db = get_database()
        self.market = get_market_data(self.broker)
        self.patterns = get_pattern_detector(self.market)
        self.news = get_news_client()
        self.safety = get_safety_validator()

    def execute(self, tool_name: str, tool_input: dict) -> dict:
        """Execute a tool call.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool result as dictionary
        """
        # Validate input
        is_valid, error = validate_tool_input(tool_name, tool_input)
        if not is_valid:
            return {"error": error, "success": False}

        # Log tool call
        self.tools_called.append(
            {
                "tool": tool_name,
                "input": tool_input,
                "timestamp": datetime.now(HK_TZ).isoformat(),
            }
        )

        # Route to implementation
        try:
            result = self._route_tool(tool_name, tool_input)
            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"Tool execution error: {tool_name}: {e}", exc_info=True)
            return {
                "error": str(e),
                "success": False,
                "tool": tool_name,
            }

    def _route_tool(self, tool_name: str, inputs: dict) -> dict:
        """Route tool call to implementation."""
        handlers = {
            "scan_market": self._scan_market,
            "get_quote": self._get_quote,
            "get_technicals": self._get_technicals,
            "detect_patterns": self._detect_patterns,
            "get_news": self._get_news,
            "check_risk": self._check_risk,
            "get_portfolio": self._get_portfolio,
            "execute_trade": self._execute_trade,
            "close_position": self._close_position,
            "close_all": self._close_all,
            "send_alert": self._send_alert,
            "log_decision": self._log_decision,
        }

        handler = handlers.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")

        return handler(inputs)

    # =========================================================================
    # Market Analysis Tools
    # =========================================================================

    def _scan_market(self, inputs: dict) -> dict:
        """Scan market for trading candidates."""
        index = inputs.get("index", "ALL")
        limit = min(inputs.get("limit", 10), 20)
        min_volume_ratio = inputs.get("min_volume_ratio", 1.5)

        candidates = self.market.scan_market(
            index=index,
            limit=limit,
            min_volume_ratio=min_volume_ratio,
        )

        return {
            "index": index,
            "candidates_found": len(candidates),
            "candidates": candidates,
            "min_volume_ratio": min_volume_ratio,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def _get_quote(self, inputs: dict) -> dict:
        """Get current quote for a symbol."""
        symbol = inputs["symbol"]
        quote = self.market.get_quote(symbol)
        return quote

    def _get_technicals(self, inputs: dict) -> dict:
        """Get technical indicators."""
        symbol = inputs["symbol"]
        timeframe = inputs.get("timeframe", "15m")

        technicals = self.market.get_technicals(symbol, timeframe)
        return technicals

    def _detect_patterns(self, inputs: dict) -> dict:
        """Detect chart patterns."""
        symbol = inputs["symbol"]
        timeframe = inputs.get("timeframe", "15m")

        patterns = self.patterns.detect_patterns(symbol, timeframe)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "patterns_found": len(patterns),
            "patterns": patterns,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def _get_news(self, inputs: dict) -> dict:
        """Get news and sentiment."""
        symbol = inputs["symbol"]
        hours = min(inputs.get("hours", 24), 72)

        news = self.news.get_news(symbol, hours=hours)
        return news

    # =========================================================================
    # Risk & Portfolio Tools
    # =========================================================================

    def _check_risk(self, inputs: dict) -> dict:
        """Validate trade against risk limits."""
        symbol = inputs["symbol"]
        side = inputs["side"]
        quantity = inputs["quantity"]
        entry_price = inputs["entry_price"]
        stop_loss = inputs["stop_loss"]
        take_profit = inputs["take_profit"]

        # Get portfolio info
        portfolio = self.broker.get_portfolio()
        positions = portfolio["positions"]

        # Validate
        result = validate_trade_request(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            portfolio_value=portfolio["equity"],
            cash_available=portfolio["cash"],
            current_positions=portfolio["position_count"],
            daily_pnl_pct=portfolio["daily_pnl_pct"] / 100,  # Convert to decimal
        )

        return result

    def _get_portfolio(self, inputs: dict) -> dict:
        """Get current portfolio status."""
        portfolio = self.broker.get_portfolio()
        return portfolio

    # =========================================================================
    # Execution Tools
    # =========================================================================

    def _execute_trade(self, inputs: dict) -> dict:
        """Execute a trade."""
        symbol = inputs["symbol"]
        side = inputs["side"]
        quantity = inputs["quantity"]
        order_type = inputs["order_type"]
        limit_price = inputs.get("limit_price")
        stop_loss = inputs["stop_loss"]
        take_profit = inputs["take_profit"]
        reason = inputs["reason"]

        # Execute via broker
        result = self.broker.execute_trade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
        )

        # Record in database if successful
        if result["status"] in ["Filled", "Submitted", "PreSubmitted"]:
            self.trades_executed += 1
            self.safety.record_trade()

            # Record position
            try:
                self.db.record_position(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    entry_price=result.get("filled_price") or limit_price or 0,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    broker_order_id=result["order_id"],
                    cycle_id=self.cycle_id,
                    reason=reason,
                )
            except Exception as e:
                logger.error(f"Failed to record position: {e}")

            # Send alert
            if self.alert_callback:
                self.alert_callback(
                    "info",
                    f"Trade Executed: {side.upper()} {symbol}",
                    f"Executed {side} {quantity} {symbol}\n"
                    f"Price: {result.get('filled_price', 'pending')}\n"
                    f"Stop: {stop_loss}, Target: {take_profit}\n"
                    f"Reason: {reason}",
                )

        return result

    def _close_position(self, inputs: dict) -> dict:
        """Close an existing position."""
        symbol = inputs["symbol"]
        reason = inputs["reason"]

        # Check if we have a position
        if not self.broker.has_position(symbol):
            return {
                "status": "error",
                "symbol": symbol,
                "message": f"No position found for {symbol}",
            }

        # Close via IBKR
        result = self.broker.close_position(symbol, reason)

        # Update database
        if result.get("filled_price"):
            try:
                self.db.close_position(
                    symbol=symbol,
                    exit_price=result["filled_price"],
                    reason=reason,
                )
            except Exception as e:
                logger.error(f"Failed to update position in DB: {e}")

            # Send alert
            if self.alert_callback:
                pnl = result.get("realized_pnl", 0)
                self.alert_callback(
                    "info",
                    f"Position Closed: {symbol}",
                    f"Closed {symbol} at {result['filled_price']}\n"
                    f"Realized P&L: HKD {pnl:,.2f}\n"
                    f"Reason: {reason}",
                )

        return result

    def _close_all(self, inputs: dict) -> dict:
        """Emergency close all positions."""
        reason = inputs["reason"]

        # Validate with safety
        portfolio = self.broker.get_portfolio()
        daily_pnl_pct = portfolio["daily_pnl_pct"] / 100

        safety_check = self.safety.validate_close_all(daily_pnl_pct, reason)

        # Close all positions
        results = self.broker.close_all_positions(reason)

        # Calculate total P&L
        total_pnl = sum(r.get("realized_pnl", 0) for r in results)

        # Update database
        for result in results:
            if result.get("filled_price") and result.get("symbol"):
                try:
                    self.db.close_position(
                        symbol=result["symbol"],
                        exit_price=result["filled_price"],
                        reason=f"Emergency close: {reason}",
                    )
                except Exception:
                    pass

        # Send critical alert
        if self.alert_callback:
            self.alert_callback(
                "critical",
                "EMERGENCY: All Positions Closed",
                f"All positions have been closed.\n"
                f"Positions closed: {len(results)}\n"
                f"Total Realized P&L: HKD {total_pnl:,.2f}\n"
                f"Reason: {reason}\n"
                f"Warnings: {', '.join(safety_check.warnings) or 'None'}",
            )

        return {
            "positions_closed": len(results),
            "total_realized_pnl": round(total_pnl, 2),
            "results": results,
            "reason": reason,
            "warnings": safety_check.warnings,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    # =========================================================================
    # Communication Tools
    # =========================================================================

    def _send_alert(self, inputs: dict) -> dict:
        """Send email alert."""
        severity = inputs["severity"]
        subject = inputs["subject"]
        message = inputs["message"]

        if self.alert_callback:
            self.alert_callback(severity, subject, message)
            return {
                "sent": True,
                "severity": severity,
                "subject": subject,
                "timestamp": datetime.now(HK_TZ).isoformat(),
            }

        return {
            "sent": False,
            "reason": "No alert callback configured",
        }

    def _log_decision(self, inputs: dict) -> dict:
        """Log decision to database."""
        decision_type = inputs["decision"]
        symbol = inputs.get("symbol")
        reasoning = inputs["reasoning"]

        # Log to database
        try:
            decision_id = self.db.log_decision(
                cycle_id=self.cycle_id,
                decision_type=decision_type,
                reasoning=reasoning,
                symbol=symbol,
                tools_called=[t["tool"] for t in self.tools_called],
            )

            return {
                "logged": True,
                "decision_id": decision_id,
                "decision_type": decision_type,
                "symbol": symbol,
                "timestamp": datetime.now(HK_TZ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_summary(self) -> dict:
        """Get execution summary for this cycle."""
        return {
            "cycle_id": self.cycle_id,
            "tools_called": len(self.tools_called),
            "trades_executed": self.trades_executed,
            "tool_history": self.tools_called,
        }


def create_tool_executor(
    cycle_id: str,
    alert_callback: Any = None,
) -> ToolExecutor:
    """Create a new tool executor for a cycle."""
    return ToolExecutor(cycle_id=cycle_id, alert_callback=alert_callback)
