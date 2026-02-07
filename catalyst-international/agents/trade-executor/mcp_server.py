"""
Trade Executor MCP Server

The SINGLE WRITER for positions table and broker orders.
Exposes execution tools via MCP SSE protocol on port 8003.

Tools:
  - get_portfolio: Cash, equity, positions, max_positions
  - execute_trade: Execute buy/sell, record position, return fill result
  - close_position: Close position via broker + DB
  - close_all: Emergency close all
  - sync_positions: Sync DB with broker state
  - check_risk: Validate trade through safety module
  - log_decision: Record decision to audit trail

Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("trade-executor-mcp")

HK_TZ = ZoneInfo("Asia/Hong_Kong")

# ---------------------------------------------------------------------------
# Lazy-init singletons (broker, db, safety)
# ---------------------------------------------------------------------------

_broker = None
_db = None
_safety = None
_config = None


def _load_config() -> dict:
    global _config
    if _config is None:
        for path in ["config/intl_claude_config.yaml", "/app/config/intl_claude_config.yaml"]:
            try:
                with open(path) as f:
                    _config = yaml.safe_load(f)
                    break
            except FileNotFoundError:
                continue
        if _config is None:
            _config = {}
    return _config


def _get_broker():
    global _broker
    if _broker is None:
        from brokers.moomoo import init_moomoo_client, get_moomoo_client
        try:
            _broker = get_moomoo_client()
        except RuntimeError:
            _broker = init_moomoo_client(paper_trading=True)
        if not _broker._connected:
            _broker.connect()
        logger.info("Broker connected")
    return _broker


def _get_db():
    global _db
    if _db is None:
        from data.database import get_database, init_database
        init_database()
        _db = get_database()
        logger.info("Database connected")
    return _db


def _get_safety():
    global _safety
    if _safety is None:
        from safety import get_safety_validator
        _safety = get_safety_validator()
    return _safety


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("trade-executor")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_portfolio",
            description="Get current portfolio status: cash, equity, positions, max_positions, unrealized P&L.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="execute_trade",
            description=(
                "Execute a buy or sell trade. Records position in DB on fill. "
                "Auto-adjusts quantity to fit HKD 10,000 limit. "
                "ALWAYS call check_risk before this tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "HKEX stock symbol (e.g. '700')"},
                    "side": {"type": "string", "enum": ["BUY", "SELL"]},
                    "quantity": {"type": "integer", "description": "Number of shares"},
                    "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "MARKET"},
                    "limit_price": {"type": "number", "description": "Limit price (required for LIMIT orders)"},
                    "stop_loss": {"type": "number", "description": "Stop loss price"},
                    "take_profit": {"type": "number", "description": "Take profit price"},
                    "reason": {"type": "string", "description": "Reason for the trade"},
                },
                "required": ["symbol", "side", "quantity", "stop_loss", "take_profit", "reason"],
            },
        ),
        Tool(
            name="close_position",
            description="Close an existing position by symbol. Sells via broker and updates DB.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "reason": {"type": "string", "default": "Manual close"},
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="close_all",
            description="Emergency close ALL positions. Use only in emergencies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "default": "Emergency close"},
                },
                "required": [],
            },
        ),
        Tool(
            name="sync_positions",
            description=(
                "Sync DB positions with broker state. Closes phantoms, adds missing, "
                "updates quantity mismatches, deduplicates."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="check_risk",
            description=(
                "Validate a proposed trade against risk limits. "
                "Returns approved/rejected with reason. MUST call before execute_trade."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "side": {"type": "string", "enum": ["BUY", "SELL"]},
                    "quantity": {"type": "integer"},
                    "entry_price": {"type": "number"},
                    "stop_loss": {"type": "number"},
                    "take_profit": {"type": "number"},
                },
                "required": ["symbol", "side", "quantity", "entry_price", "stop_loss", "take_profit"],
            },
        ),
        Tool(
            name="log_decision",
            description="Record a trading decision to the audit trail.",
            inputSchema={
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "description": "Decision type: trade, skip, close, observation"},
                    "symbol": {"type": "string"},
                    "reasoning": {"type": "string", "description": "Detailed reasoning"},
                },
                "required": ["decision", "reasoning"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "get_portfolio": _handle_get_portfolio,
        "execute_trade": _handle_execute_trade,
        "close_position": _handle_close_position,
        "close_all": _handle_close_all,
        "sync_positions": _handle_sync_positions,
        "check_risk": _handle_check_risk,
        "log_decision": _handle_log_decision,
    }
    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    try:
        result = handler(arguments)
        return [TextContent(type="text", text=json.dumps(result, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} error: {e}", exc_info=True)
        return [TextContent(type="text", text=json.dumps({"error": str(e), "success": False}))]


# ---------------------------------------------------------------------------
# Tool implementations (adapted from tool_executor.py v3.4.0)
# ---------------------------------------------------------------------------

def _handle_get_portfolio(args: dict) -> dict:
    broker = _get_broker()
    portfolio = broker.get_portfolio()
    if hasattr(portfolio, "__dict__"):
        portfolio = vars(portfolio)
    config = _load_config()
    trading_cfg = config.get("trading", {})
    max_positions = trading_cfg.get("max_positions", 5)
    return {
        "cash": portfolio.get("cash", 0),
        "equity": portfolio.get("equity") or portfolio.get("total_assets", 0),
        "market_value": portfolio.get("market_value", 0),
        "unrealized_pnl": portfolio.get("unrealized_pnl", 0),
        "daily_pnl": portfolio.get("daily_pnl", 0),
        "daily_pnl_pct": portfolio.get("daily_pnl_pct", 0),
        "position_count": portfolio.get("position_count", 0),
        "max_positions": max_positions,
        "success": True,
        "timestamp": datetime.now(HK_TZ).isoformat(),
    }


def _handle_execute_trade(args: dict) -> dict:
    from brokers.moomoo import normalize_symbol
    broker = _get_broker()
    db = _get_db()
    safety = _get_safety()

    symbol = args["symbol"]
    side = args["side"].upper()
    quantity = args["quantity"]
    order_type = args.get("order_type", "MARKET")
    limit_price = args.get("limit_price")
    stop_loss = args["stop_loss"]
    take_profit = args["take_profit"]
    reason = args["reason"]

    logger.info(f"Executing trade: {side} {quantity} {symbol}")

    # Auto-adjust quantity to fit position value limit
    config = _load_config()
    trading_cfg = config.get("trading", {})
    max_position_value = trading_cfg.get("max_position_value_hkd", 10000)

    try:
        quote = broker.get_quote(symbol)
        current_price = quote.get("last_price") or quote.get("last") or limit_price or 0
    except Exception:
        current_price = limit_price or 0

    if current_price > 0:
        position_value = quantity * current_price
        if position_value > max_position_value:
            max_qty = int(max_position_value / current_price)
            lot_size = 10
            max_qty = max((max_qty // lot_size) * lot_size, lot_size)
            logger.info(f"Auto-adjusted qty {quantity} -> {max_qty} for HKD {max_position_value} limit")
            quantity = max_qty

    # Execute via broker with fill confirmation
    result = broker.execute_trade(
        symbol=symbol, side=side, quantity=quantity,
        order_type=order_type, limit_price=limit_price,
        stop_loss=stop_loss, take_profit=take_profit,
        reason=reason, wait_for_fill=True,
    )

    if hasattr(result, "status"):
        status, order_id = result.status, result.order_id
        fill_price, filled_qty = result.filled_price, result.filled_quantity
        message = result.message
    else:
        status = result.get("status", "")
        order_id = result.get("order_id", "")
        fill_price = result.get("filled_price") or result.get("fill_price")
        filled_qty = result.get("filled_quantity", 0)
        message = result.get("message", "")

    is_filled = status == "FILLED"
    is_partial = status == "FILLED_PART" and filled_qty > 0
    is_failed = status in ["FAILED", "CANCELLED_ALL", "CANCELLED_PART", "TIMEOUT", "DELETED"]

    logger.info(f"Order {order_id}: status={status}, filled_qty={filled_qty}, price={fill_price}")

    # Use a default cycle_id for trades initiated via MCP
    cycle_id = f"mcp_{datetime.now(HK_TZ).strftime('%Y%m%d_%H%M%S')}"

    if is_filled or is_partial:
        safety.record_trade()
        try:
            db.record_position(
                symbol=symbol, side=side, quantity=quantity,
                entry_price=fill_price or limit_price or 0,
                stop_loss=stop_loss, take_profit=take_profit,
                broker_order_id=order_id, cycle_id=cycle_id, reason=reason,
            )
        except Exception as e:
            logger.error(f"Failed to record position: {e}")

        db_status = "filled" if is_filled else "partial"
        try:
            db.record_order(
                symbol=symbol, side=side,
                order_type=order_type.upper() if order_type else "MARKET",
                quantity=quantity, limit_price=limit_price,
                filled_quantity=filled_qty or quantity,
                filled_price=fill_price, status=db_status,
                broker_order_id=order_id,
            )
        except Exception as e:
            logger.error(f"Failed to record order: {e}")

        return {
            "status": "success", "order_id": order_id, "fill_price": fill_price,
            "symbol": symbol, "side": side, "quantity": quantity,
            "stop_loss": stop_loss, "take_profit": take_profit,
            "success": True, "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    elif is_failed:
        logger.warning(f"Order {order_id} failed: {status} - {message}")
        try:
            db.record_order(
                symbol=symbol, side=side,
                order_type=order_type.upper() if order_type else "MARKET",
                quantity=quantity, limit_price=limit_price,
                filled_quantity=0, filled_price=None,
                status=status.lower(), broker_order_id=order_id,
            )
        except Exception:
            pass
        return {
            "status": "failed", "order_id": order_id, "reason": message or status,
            "symbol": symbol, "side": side, "quantity": quantity,
            "success": False, "timestamp": datetime.now(HK_TZ).isoformat(),
        }
    else:
        return {
            "status": "pending", "order_id": order_id,
            "reason": message or f"Order pending: {status}",
            "symbol": symbol, "side": side, "quantity": quantity,
            "success": False, "timestamp": datetime.now(HK_TZ).isoformat(),
        }


def _handle_close_position(args: dict) -> dict:
    from brokers.moomoo import normalize_symbol
    broker = _get_broker()
    db = _get_db()

    symbol = args["symbol"]
    reason = args.get("reason", "Manual close")

    positions = broker.get_positions()
    position = None
    for pos in positions:
        pos_symbol = pos.symbol if hasattr(pos, "symbol") else pos.get("symbol", "")
        if normalize_symbol(pos_symbol) == normalize_symbol(symbol):
            position = pos
            break

    if not position:
        return {"status": "error", "symbol": symbol, "message": f"No position found for {symbol}", "success": False}

    quantity = abs(int(position.quantity if hasattr(position, "quantity") else position.get("quantity", 0)))
    result = broker.close_position(symbol, reason)

    if hasattr(result, "status"):
        status, fill_price = result.status, result.filled_price
    else:
        status = result.get("status", "")
        fill_price = result.get("filled_price") or result.get("fill_price")

    if status in ["FILLED", "filled", "SUBMITTED", "submitted", "success", "NO_POSITION"]:
        if fill_price:
            try:
                db.close_position(symbol=symbol, exit_price=fill_price, reason=reason)
            except Exception as e:
                logger.error(f"Failed to close position in DB: {e}")
        return {
            "status": "success", "symbol": symbol, "quantity": quantity,
            "fill_price": fill_price, "reason": reason,
            "success": True, "timestamp": datetime.now(HK_TZ).isoformat(),
        }
    else:
        return {"status": "failed", "symbol": symbol, "reason": str(result), "success": False}


def _handle_close_all(args: dict) -> dict:
    broker = _get_broker()
    reason = args.get("reason", "Emergency close")
    logger.warning(f"EMERGENCY CLOSE ALL: {reason}")
    results = broker.close_all_positions(reason)
    return {
        "status": "success", "positions_closed": len(results),
        "results": [str(r) for r in results], "reason": reason,
        "success": True, "timestamp": datetime.now(HK_TZ).isoformat(),
    }


def _handle_sync_positions(args: dict) -> dict:
    from brokers.moomoo import normalize_symbol
    broker = _get_broker()
    db = _get_db()

    results = {"synced": [], "closed_phantoms": [], "added_missing": [], "errors": []}
    cycle_id = f"sync_{datetime.now(HK_TZ).strftime('%Y%m%d_%H%M%S')}"

    try:
        broker_positions = broker.get_positions()
        broker_dict = {normalize_symbol(str(p.symbol)): p for p in broker_positions}
        broker_symbols = set(broker_dict.keys())

        db_positions = db.get_positions()
        db_dict = {}
        for p in db_positions:
            sym = normalize_symbol(str(p.get("symbol", "")))
            if sym in db_dict:
                try:
                    db.close_position_by_id(position_id=p["position_id"], reason="dedup: duplicate open row in sync")
                    results["closed_phantoms"].append(f"{sym} (dedup id={p['position_id']})")
                except Exception as e:
                    results["errors"].append(f"Dedup {sym}: {e}")
            else:
                db_dict[sym] = p
        db_symbols = set(db_dict.keys())

        for symbol in db_symbols - broker_symbols:
            try:
                db.close_position(symbol=symbol, exit_price=0, reason="Auto-sync: not in broker")
                results["closed_phantoms"].append(symbol)
            except Exception as e:
                results["errors"].append(f"Close {symbol}: {e}")

        for symbol in broker_symbols - db_symbols:
            try:
                pos = broker_dict[symbol]
                entry = float(pos.avg_cost)
                db.record_position(
                    symbol=symbol, side="BUY", quantity=int(pos.quantity),
                    entry_price=entry, stop_loss=round(entry * 0.97, 2),
                    take_profit=round(entry * 1.06, 2),
                    broker_order_id="auto_sync", cycle_id=cycle_id,
                    reason="Auto-sync: found in broker",
                )
                results["added_missing"].append(symbol)
            except Exception as e:
                results["errors"].append(f"Add {symbol}: {e}")

        for symbol in broker_symbols & db_symbols:
            broker_qty = int(broker_dict[symbol].quantity)
            db_qty = int(db_dict[symbol].get("quantity", 0))
            if broker_qty != db_qty:
                try:
                    db.update_position_quantity(
                        symbol=symbol, new_quantity=broker_qty,
                        new_avg_price=float(broker_dict[symbol].avg_cost),
                        reason=f"Auto-sync: {db_qty} -> {broker_qty}",
                    )
                    results["synced"].append(f"{symbol}: {db_qty} -> {broker_qty}")
                except Exception as e:
                    results["errors"].append(f"Update {symbol}: {e}")

    except Exception as e:
        results["errors"].append(str(e))

    results["success"] = True
    results["timestamp"] = datetime.now(HK_TZ).isoformat()
    return results


def _handle_check_risk(args: dict) -> dict:
    from safety import validate_trade_request
    broker = _get_broker()

    portfolio = broker.get_portfolio()
    if hasattr(portfolio, "__dict__"):
        portfolio = vars(portfolio)

    portfolio_value = portfolio.get("equity") or portfolio.get("total_assets", 500000)
    cash_available = portfolio.get("cash", 0)
    current_positions = portfolio.get("position_count", 0)
    daily_pnl_pct = portfolio.get("daily_pnl_pct", 0)
    if daily_pnl_pct > 1:
        daily_pnl_pct /= 100

    entry_price = args["entry_price"]
    stop_loss = args["stop_loss"]
    take_profit = args["take_profit"]

    result = validate_trade_request(
        symbol=args["symbol"], side=args["side"], quantity=args["quantity"],
        entry_price=entry_price, stop_loss=stop_loss, take_profit=take_profit,
        portfolio_value=portfolio_value, cash_available=cash_available,
        current_positions=current_positions, daily_pnl_pct=daily_pnl_pct,
    )

    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)
    risk_reward = reward / risk if risk > 0 else 0

    return {
        "approved": result.get("approved", False),
        "reason": result.get("reason", ""),
        "warnings": result.get("warnings", []),
        "risk_reward_ratio": round(risk_reward, 2),
        "position_size_hkd": args["quantity"] * entry_price,
        "max_loss_hkd": args["quantity"] * risk,
        "portfolio_value": portfolio_value,
        "cash_available": cash_available,
        "current_positions": current_positions,
        "success": True,
        "timestamp": datetime.now(HK_TZ).isoformat(),
    }


def _handle_log_decision(args: dict) -> dict:
    db = _get_db()
    cycle_id = f"mcp_{datetime.now(HK_TZ).strftime('%Y%m%d_%H%M%S')}"
    try:
        decision_id = db.log_decision(
            cycle_id=cycle_id,
            decision_type=args["decision"],
            reasoning=args["reasoning"],
            symbol=args.get("symbol"),
        )
        return {"logged": True, "decision_id": decision_id, "success": True, "timestamp": datetime.now(HK_TZ).isoformat()}
    except Exception as e:
        return {"logged": False, "error": str(e), "success": False}


# ---------------------------------------------------------------------------
# Health + App
# ---------------------------------------------------------------------------

async def health(request):
    try:
        _get_broker()
        _get_db()
        return JSONResponse({"status": "healthy", "service": "trade-executor"})
    except Exception as e:
        return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=503)


sse = SseServerTransport("/messages/")


async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


app = Starlette(
    debug=False,
    routes=[
        Route("/health", health),
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)


@app.on_event("startup")
async def on_startup():
    logger.info("Trade Executor MCP Server starting on port 8003")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
