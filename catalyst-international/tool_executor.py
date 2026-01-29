"""
Name of Application: Catalyst Trading System
Name of file: tool_executor.py
Version: 2.9.0
Last Updated: 2026-01-20
Purpose: Routes Claude's tool calls to actual implementations

REVISION HISTORY:
v2.9.0 (2026-01-20) - Auto-sync positions with broker
- Added sync_positions_with_broker() method
- Syncs DB positions with Moomoo at start of each trade cycle
- Closes phantom positions (in DB but not broker)
- Adds missing positions (in broker but not DB)
- Updates quantity mismatches automatically

v2.8.0 (2026-01-20) - Enforce max_position_value_hkd limit
- Added position value validation in _execute_trade()
- Rejects trades exceeding max_position_value_hkd (default 10,000)
- Returns helpful error with max allowed quantity for the price

v2.7.0 (2026-01-20) - Add max_positions to portfolio response
- Added config loading in __init__
- get_portfolio now returns max_positions from config
- Agent can now see available position slots

v2.6.0 (2026-01-16) - Fix order status handling
- Fixed: Only record position when broker confirms FILLED (not just SUBMITTED)
- Separate filled_statuses, partial_filled_statuses, submitted_statuses
- Orders with SUBMITTED status now recorded as "submitted" with filled_quantity=0
- Positions only created when order is actually filled
- Added warning log for submitted but unfilled orders

v2.5.0 (2026-01-16) - Remove inline position monitor
- Removed position_monitor.py import (was failing with DB errors)
- Position monitoring now handled by position_monitor_service.py (systemd)
- Disabled inline monitor calls after trades

v2.4.0 (2026-01-16) - Position monitor fixes
- Fixed: pass position_id instead of safety_validator to start_position_monitor()
- Fixed: run position monitor in background thread to avoid event loop conflicts
- Captures position_id from record_position() return value

v2.3.0 (2026-01-06) - Order logging
- Added order recording to database after successful trades

v2.2.1 (2026-01-06) - Position monitoring integration
- Added agent parameter to __init__
- Call start_position_monitor() after successful BUY orders
- Fixed OrderResult dataclass handling
- Fixed AlertSender callable check
- Fixed portfolio .get() for missing fields

v2.1.0 (2025-12-30) - Updated to use MoomooClient
- Changed imports from futu to moomoo
- Using moomoo-api SDK

v2.0.0 (2025-12-20) - Migrated to Moomoo/Futu
- Replaced IBKR with Futu broker client
- Updated all broker references

v1.0.0 (2025-12-06) - Initial implementation

Description:
This module receives tool calls from Claude and routes them to the
appropriate implementation functions. It handles all 12 trading tools
defined in the CLAUDE.md specification.

NEW in v2.2.1: After successful BUY orders, automatically starts
position monitoring that runs until exit.
"""

import asyncio
import json
import logging
import threading
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from brokers.moomoo import get_moomoo_client
from data.database import get_database
from data.market import get_market_data
from data.news import get_news_client
from data.patterns import get_pattern_detector
from safety import get_safety_validator, validate_trade_request
from tools import validate_tool_input

# Position monitoring disabled - now handled by position_monitor_service.py (systemd)
# The old position_monitor.py was removed due to database constraint errors
POSITION_MONITOR_AVAILABLE = False
start_position_monitor = None

logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")


class ToolExecutor:
    """Executes tool calls from Claude."""

    def __init__(
        self,
        cycle_id: str,
        alert_callback: Any = None,
        agent: Any = None,
    ):
        """Initialize tool executor.

        Args:
            cycle_id: Current agent cycle ID
            alert_callback: Function/object to send alerts
            agent: Reference to TradingAgent (for Claude client access)
        """
        self.cycle_id = cycle_id
        self.alert_callback = alert_callback
        self.agent = agent
        self.tools_called: list[dict] = []
        self.trades_executed = 0

        # Load config
        self.config = self._load_config()

        # Initialize services
        self.broker = get_moomoo_client()
        self.db = get_database()
        self.market = get_market_data(self.broker)
        self.patterns = get_pattern_detector(self.market)
        self.news = get_news_client()
        self.safety = get_safety_validator()

    def _load_config(self) -> dict:
        """Load trading config from file."""
        config_path = "config/intl_claude_config.yaml"
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return {}

    def sync_positions_with_broker(self) -> dict:
        """Sync DB positions with broker (Moomoo) at start of cycle.

        This ensures DB reflects actual broker state:
        - Closes phantom positions (in DB but not in broker)
        - Adds missing positions (in broker but not in DB)
        - Updates quantity mismatches

        Returns:
            dict with sync results
        """
        results = {
            "synced": [],
            "closed_phantoms": [],
            "added_missing": [],
            "errors": []
        }

        try:
            # Get broker positions
            broker_positions = self.broker.get_positions()
            broker_dict = {str(p.symbol): p for p in broker_positions}
            broker_symbols = set(broker_dict.keys())

            # Get DB positions
            db_positions = self.db.get_positions()
            db_dict = {str(p.get('symbol')): p for p in db_positions}
            db_symbols = set(db_dict.keys())

            # Close phantom positions (in DB but not in broker)
            phantoms = db_symbols - broker_symbols
            for symbol in phantoms:
                try:
                    self.db.close_position(
                        symbol=symbol,
                        exit_price=0,
                        reason='Auto-sync: position no longer in broker'
                    )
                    results["closed_phantoms"].append(symbol)
                    logger.info(f"Auto-sync: closed phantom position {symbol}")
                except Exception as e:
                    results["errors"].append(f"Failed to close {symbol}: {e}")

            # Add missing positions (in broker but not in DB)
            missing = broker_symbols - db_symbols
            for symbol in missing:
                try:
                    pos = broker_dict[symbol]
                    entry = float(pos.avg_cost)
                    self.db.record_position(
                        symbol=symbol,
                        side='BUY',
                        quantity=int(pos.quantity),
                        entry_price=entry,
                        stop_loss=round(entry * 0.97, 2),
                        take_profit=round(entry * 1.06, 2),
                        broker_order_id='auto_sync',
                        cycle_id=self.cycle_id,
                        reason='Auto-sync: position found in broker'
                    )
                    results["added_missing"].append(symbol)
                    logger.info(f"Auto-sync: added missing position {symbol}")
                except Exception as e:
                    results["errors"].append(f"Failed to add {symbol}: {e}")

            # Update quantity mismatches
            common = broker_symbols & db_symbols
            for symbol in common:
                broker_qty = int(broker_dict[symbol].quantity)
                db_qty = int(db_dict[symbol].get('quantity', 0))

                if broker_qty != db_qty:
                    try:
                        # Close old and create new with correct quantity
                        pos = broker_dict[symbol]
                        entry = float(pos.avg_cost)

                        self.db.close_position(
                            symbol=symbol,
                            exit_price=entry,
                            reason=f'Auto-sync: quantity update {db_qty} -> {broker_qty}'
                        )

                        self.db.record_position(
                            symbol=symbol,
                            side='BUY',
                            quantity=broker_qty,
                            entry_price=entry,
                            stop_loss=round(entry * 0.97, 2),
                            take_profit=round(entry * 1.06, 2),
                            broker_order_id='auto_sync',
                            cycle_id=self.cycle_id,
                            reason=f'Auto-sync: quantity updated from {db_qty} to {broker_qty}'
                        )
                        results["synced"].append(f"{symbol}: {db_qty} -> {broker_qty}")
                        logger.info(f"Auto-sync: updated {symbol} quantity {db_qty} -> {broker_qty}")
                    except Exception as e:
                        results["errors"].append(f"Failed to update {symbol}: {e}")

            # Log summary
            total_changes = len(results["closed_phantoms"]) + len(results["added_missing"]) + len(results["synced"])
            if total_changes > 0:
                logger.info(f"Auto-sync complete: {total_changes} changes made")
            else:
                logger.info("Auto-sync complete: positions already in sync")

        except Exception as e:
            logger.error(f"Auto-sync failed: {e}")
            results["errors"].append(str(e))

        return results

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
        # Default max_price=20 to stay within HKD 10,000 position limit
        max_price = inputs.get("max_price", 20.0)

        candidates = self.market.scan_market(
            index=index,
            limit=limit,
            min_volume_ratio=min_volume_ratio,
            max_price=max_price,
        )

        return {
            "index": index,
            "candidates_found": len(candidates),
            "candidates": candidates,
            "min_volume_ratio": min_volume_ratio,
            "max_price": max_price,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def _get_quote(self, inputs: dict) -> dict:
        """Get current quote for a symbol."""
        symbol = inputs["symbol"]
        quote = self.market.get_quote(symbol)

        return {
            "symbol": symbol,
            "quote": quote,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def _get_technicals(self, inputs: dict) -> dict:
        """Get technical indicators for a symbol."""
        symbol = inputs["symbol"]
        technicals = self.market.get_technicals(symbol)

        return {
            "symbol": symbol,
            "technicals": technicals,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def _detect_patterns(self, inputs: dict) -> dict:
        """Detect chart patterns for a symbol."""
        symbol = inputs["symbol"]
        patterns = self.patterns.detect_patterns(symbol)

        return {
            "symbol": symbol,
            "patterns_found": len(patterns),
            "patterns": patterns,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def _get_news(self, inputs: dict) -> dict:
        """Get news for a symbol."""
        symbol = inputs["symbol"]
        news = self.news.get_news(symbol)

        return {
            "symbol": symbol,
            "news": news,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    # =========================================================================
    # Risk Management Tools
    # =========================================================================

    def _check_risk(self, inputs: dict) -> dict:
        """Check if a trade passes risk validation."""
        symbol = inputs["symbol"]
        side = inputs["side"]
        quantity = inputs["quantity"]
        entry_price = inputs["entry_price"]
        stop_loss = inputs["stop_loss"]
        take_profit = inputs["take_profit"]

        # Get portfolio info for risk validation
        portfolio = self.broker.get_portfolio()
        if hasattr(portfolio, '__dict__'):
            portfolio = vars(portfolio)

        portfolio_value = portfolio.get("equity") or portfolio.get("total_assets", 500000)
        cash_available = portfolio.get("cash", 0)
        current_positions = portfolio.get("position_count", 0)
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0) / 100 if portfolio.get("daily_pnl_pct", 0) > 1 else portfolio.get("daily_pnl_pct", 0)

        # Validate through safety module
        result = validate_trade_request(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            portfolio_value=portfolio_value,
            cash_available=cash_available,
            current_positions=current_positions,
            daily_pnl_pct=daily_pnl_pct,
        )

        # Calculate risk/reward
        if entry_price and stop_loss and take_profit:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
        else:
            risk_reward = 0

        return {
            "approved": result.get("approved", False),
            "reason": result.get("reason", ""),
            "warnings": result.get("warnings", []),
            "risk_reward_ratio": round(risk_reward, 2),
            "position_size_hkd": quantity * entry_price if entry_price else 0,
            "max_loss_hkd": quantity * abs(entry_price - stop_loss) if stop_loss else 0,
            "portfolio_value": portfolio_value,
            "cash_available": cash_available,
            "current_positions": current_positions,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def _get_portfolio(self, inputs: dict) -> dict:
        """Get current portfolio status."""
        portfolio = self.broker.get_portfolio()

        # Handle both dict and object responses
        if hasattr(portfolio, '__dict__'):
            portfolio = vars(portfolio)

        # Get max_positions from config (default 5 for safety)
        trading_config = self.config.get('trading', {}) if self.config else {}
        max_positions = trading_config.get('max_positions', 5)

        return {
            "cash": portfolio.get("cash", 0),
            "equity": portfolio.get("equity") or portfolio.get("total_assets", 0),
            "market_value": portfolio.get("market_value", 0),
            "unrealized_pnl": portfolio.get("unrealized_pnl", 0),
            "daily_pnl": portfolio.get("daily_pnl", 0),
            "daily_pnl_pct": portfolio.get("daily_pnl_pct", 0),
            "position_count": portfolio.get("position_count", 0),
            "max_positions": max_positions,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    # =========================================================================
    # Execution Tools
    # =========================================================================

    def _execute_trade(self, inputs: dict) -> dict:
        """Execute a trade with optional position monitoring."""
        symbol = inputs["symbol"]
        side = inputs["side"]
        quantity = inputs["quantity"]
        order_type = inputs["order_type"]
        limit_price = inputs.get("limit_price")
        stop_loss = inputs["stop_loss"]
        take_profit = inputs["take_profit"]
        reason = inputs["reason"]

        logger.info(f"Executing trade: {side} {quantity} {symbol}")

        # ENFORCE POSITION VALUE LIMIT
        trading_config = self.config.get('trading', {}) if self.config else {}
        max_position_value = trading_config.get('max_position_value_hkd', 10000)

        # Get current price to calculate position value
        try:
            quote = self.broker.get_quote(symbol)
            current_price = quote.get('last_price') or quote.get('last') or limit_price or 0
        except Exception:
            current_price = limit_price or 0

        if current_price > 0:
            position_value = quantity * current_price
            if position_value > max_position_value:
                max_qty = int(max_position_value / current_price)
                # Round down to lot size (typically 100 for HKEX)
                lot_size = 100
                max_qty = (max_qty // lot_size) * lot_size
                logger.warning(
                    f"Position value HKD {position_value:,.0f} exceeds limit HKD {max_position_value:,}. "
                    f"Rejecting trade. Max allowed quantity at {current_price:.2f} is {max_qty} shares."
                )
                return {
                    "success": False,
                    "status": "REJECTED",
                    "order_id": None,
                    "message": f"Position value HKD {position_value:,.0f} exceeds max limit HKD {max_position_value:,}. "
                               f"Use quantity <= {max_qty} for this price.",
                }

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

        # Handle OrderResult dataclass or dict
        if hasattr(result, 'status'):
            status = result.status
            order_id = result.order_id
            fill_price = result.filled_price
            message = result.message
        else:
            status = result.get("status", "")
            order_id = result.get("order_id", "")
            fill_price = result.get("filled_price") or result.get("fill_price")
            message = result.get("message", "")

        # Separate actually filled orders from just submitted orders
        filled_statuses = ["Filled", "FILLED", "FILLED_ALL", "success"]
        partial_filled_statuses = ["FILLED_PART"]
        submitted_statuses = ["Submitted", "SUBMITTED", "SUBMITTING", "WAITING_SUBMIT"]

        is_filled = status in filled_statuses
        is_partial = status in partial_filled_statuses
        is_submitted = status in submitted_statuses

        if is_filled or is_partial or is_submitted:
            # Only count as executed trade if actually filled
            if is_filled or is_partial:
                self.trades_executed += 1
                self.safety.record_trade()

            # Record position in database ONLY if actually filled
            position_id = None
            if is_filled or is_partial:
                try:
                    position_id = self.db.record_position(
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        entry_price=fill_price or limit_price or 0,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        broker_order_id=order_id,
                        cycle_id=self.cycle_id,
                        reason=reason,
                    )
                except Exception as e:
                    logger.error(f"Failed to record position: {e}")

            # Record order in database with correct status
            try:
                if is_filled:
                    db_status = "filled"
                    db_filled_qty = quantity
                elif is_partial:
                    db_status = "partial"
                    # Use actual filled quantity from broker if available
                    db_filled_qty = getattr(result, 'filled_quantity', 0) if hasattr(result, 'filled_quantity') else result.get('filled_quantity', 0) if isinstance(result, dict) else 0
                    if not db_filled_qty:
                        db_filled_qty = quantity  # Fallback
                else:  # is_submitted
                    db_status = "submitted"
                    db_filled_qty = 0

                self.db.record_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type.upper() if order_type else "MARKET",
                    quantity=quantity,
                    limit_price=limit_price,
                    filled_quantity=db_filled_qty,
                    filled_price=fill_price if (is_filled or is_partial) else None,
                    status=db_status,
                    broker_order_id=order_id,
                )

                # Log warning for submitted but not filled orders
                if is_submitted:
                    logger.warning(f"Order {order_id} for {symbol} submitted but NOT filled yet - monitor for fill confirmation")

            except Exception as e:
                logger.error(f"Failed to record order: {e}")

            # Send alert (handle AlertSender object or callable)
            if self.alert_callback:
                try:
                    alert_msg = (
                        f"Executed {side} {quantity} {symbol}\n"
                        f"Price: {fill_price or 'pending'}\n"
                        f"Stop: {stop_loss}, Target: {take_profit}\n"
                        f"Reason: {reason}"
                    )
                    if hasattr(self.alert_callback, 'send'):
                        self.alert_callback.send(
                            "info",
                            f"Trade Executed: {side.upper()} {symbol}",
                            alert_msg,
                        )
                    elif callable(self.alert_callback):
                        self.alert_callback(
                            "info",
                            f"Trade Executed: {side.upper()} {symbol}",
                            alert_msg,
                        )
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

            # ================================================================
            # NEW: Start position monitoring for BUY orders
            # ================================================================
            monitor_result = None
            monitor_error = None
            
            if (
                side.upper() == "BUY"
                and self.agent
                and POSITION_MONITOR_AVAILABLE
                and position_id is not None
            ):
                try:
                    # Get anthropic client from agent
                    anthropic_client = getattr(self.agent, 'client', None)

                    if anthropic_client:
                        logger.info(f"Starting position monitor for {symbol} (position_id={position_id})")

                        # Run position monitor in background thread to avoid event loop conflicts
                        def run_monitor():
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                result = loop.run_until_complete(
                                    start_position_monitor(
                                        broker=self.broker,
                                        market_data=self.market,
                                        anthropic_client=anthropic_client,
                                        position_id=position_id,
                                        symbol=symbol,
                                        entry_price=fill_price or limit_price or 0,
                                        quantity=quantity,
                                        stop_price=stop_loss,
                                        target_price=take_profit,
                                        entry_reason=reason,
                                    )
                                )
                                logger.info(f"Position monitor completed: {result}")
                                loop.close()
                            except Exception as e:
                                logger.error(f"Position monitor thread error: {e}")

                        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
                        monitor_thread.start()
                        logger.info(f"Position monitor thread started for {symbol}")
                    else:
                        logger.warning("No anthropic client available for monitoring")

                except Exception as e:
                    logger.error(f"Position monitor failed: {e}", exc_info=True)
                    monitor_error = str(e)
                    # Trade still succeeded, monitoring just failed
            # ================================================================

            return {
                "status": "success",
                "order_id": order_id,
                "fill_price": fill_price,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "monitor_result": monitor_result,
                "monitor_error": monitor_error,
                "timestamp": datetime.now(HK_TZ).isoformat(),
            }

        else:
            return {
                "status": "failed",
                "reason": message or str(result),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
            }

    def _close_position(self, inputs: dict) -> dict:
        """Close an existing position."""
        symbol = inputs["symbol"]
        reason = inputs.get("reason", "Manual close")

        logger.info(f"Closing position: {symbol} - {reason}")

        # Check if we have a position
        positions = self.broker.get_positions()
        position = None
        
        for pos in positions:
            pos_symbol = pos.symbol if hasattr(pos, 'symbol') else pos.get('symbol', '')
            pos_symbol = str(pos_symbol).replace('.HK', '').replace('HK.', '').lstrip('0')
            check_symbol = symbol.replace('.HK', '').replace('HK.', '').lstrip('0')
            
            if pos_symbol == check_symbol:
                position = pos
                break

        if not position:
            return {
                "status": "error",
                "symbol": symbol,
                "message": f"No position found for {symbol}",
            }

        # Get quantity
        quantity = position.quantity if hasattr(position, 'quantity') else position.get('quantity', 0)
        quantity = abs(int(quantity))

        # Close via broker
        result = self.broker.close_position(symbol, reason)

        # Handle OrderResult dataclass
        if hasattr(result, 'status'):
            status = result.status
            fill_price = result.filled_price
        else:
            status = result.get("status", "")
            fill_price = result.get("filled_price") or result.get("fill_price")

        if status in ["FILLED", "filled", "SUBMITTED", "submitted", "success", "NO_POSITION"]:
            # Update database
            if fill_price:
                try:
                    self.db.close_position(
                        symbol=symbol,
                        exit_price=fill_price,
                        reason=reason,
                    )
                except Exception as e:
                    logger.error(f"Failed to update position in DB: {e}")

            # Send alert
            if self.alert_callback and fill_price:
                try:
                    entry_price = position.avg_cost if hasattr(position, 'avg_cost') else position.get('avg_cost', 0)
                    pnl = (fill_price - entry_price) * quantity if entry_price else 0
                    
                    alert_msg = (
                        f"Closed {symbol} at {fill_price}\n"
                        f"Realized P&L: HKD {pnl:,.2f}\n"
                        f"Reason: {reason}"
                    )
                    if hasattr(self.alert_callback, 'send'):
                        self.alert_callback.send("info", f"Position Closed: {symbol}", alert_msg)
                    elif callable(self.alert_callback):
                        self.alert_callback("info", f"Position Closed: {symbol}", alert_msg)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

            return {
                "status": "success",
                "symbol": symbol,
                "quantity": quantity,
                "fill_price": fill_price,
                "reason": reason,
                "timestamp": datetime.now(HK_TZ).isoformat(),
            }

        else:
            return {
                "status": "failed",
                "symbol": symbol,
                "reason": str(result),
            }

    def _close_all(self, inputs: dict) -> dict:
        """Emergency close all positions."""
        reason = inputs.get("reason", "Emergency close")

        logger.warning(f"EMERGENCY CLOSE ALL: {reason}")

        results = self.broker.close_all_positions(reason)

        # Send alert
        if self.alert_callback:
            try:
                alert_msg = f"Emergency close triggered: {reason}\nPositions closed: {len(results)}"
                if hasattr(self.alert_callback, 'send'):
                    self.alert_callback.send("critical", "EMERGENCY CLOSE ALL", alert_msg)
                elif callable(self.alert_callback):
                    self.alert_callback("critical", "EMERGENCY CLOSE ALL", alert_msg)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

        return {
            "status": "success",
            "positions_closed": len(results),
            "results": [str(r) for r in results],
            "reason": reason,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    # =========================================================================
    # Communication Tools
    # =========================================================================

    def _send_alert(self, inputs: dict) -> dict:
        """Send an alert notification."""
        severity = inputs["severity"]
        subject = inputs["subject"]
        message = inputs["message"]

        if self.alert_callback:
            try:
                if hasattr(self.alert_callback, 'send'):
                    self.alert_callback.send(severity, subject, message)
                elif callable(self.alert_callback):
                    self.alert_callback(severity, subject, message)
                return {
                    "sent": True,
                    "severity": severity,
                    "subject": subject,
                    "timestamp": datetime.now(HK_TZ).isoformat(),
                }
            except Exception as e:
                logger.error(f"Alert send failed: {e}")
                return {"sent": False, "error": str(e)}
        else:
            return {"sent": False, "reason": "No alert callback configured"}

    def _log_decision(self, inputs: dict) -> dict:
        """Log a trading decision for audit trail."""
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
    agent: Any = None,
) -> ToolExecutor:
    """Create a new tool executor for a cycle.
    
    Args:
        cycle_id: Current agent cycle ID
        alert_callback: Function/object to send alerts
        agent: Reference to TradingAgent (for position monitoring)
        
    Returns:
        ToolExecutor instance
    """
    return ToolExecutor(
        cycle_id=cycle_id,
        alert_callback=alert_callback,
        agent=agent,
    )
