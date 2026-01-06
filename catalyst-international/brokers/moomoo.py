"""
Name of Application: Catalyst Trading System
Name of file: moomoo.py
Version: 1.2.0
Last Updated: 2026-01-02
Purpose: Moomoo client for HKEX trading via OpenD gateway

REVISION HISTORY:
v1.2.0 (2026-01-02) - Add historical data support
- Added get_historical_data() for OHLCV candlestick data
- Uses request_history_kline API with KLType mapping
- Fixes get_technicals and detect_patterns tools

v1.1.0 (2025-12-30) - Add batch quote support
- Added get_quotes_batch() for multiple symbols in one API call
- Fixes rate limiting issue (max 60 requests per 30 seconds)
- Batch API supports up to 400 symbols per request

v1.0.0 (2025-12-29) - Initial implementation
- Uses moomoo-api Python SDK (NOT futu-api)
- Connects to OpenD native binary gateway
- Simple password authentication (no 2FA)
- Real-time market data included
- HKEX tick size rounding
- Symbol format conversion (700 -> HK.00700)

Description:
This module provides the MoomooClient class for trading HKEX stocks via
Moomoo's OpenD gateway. It replaces the IBKR integration to eliminate
the authentication complexity of IB Gateway.

Official Documentation:
- API Docs: https://openapi.moomoo.com/moomoo-api-doc/en/intro/intro.html
- OpenD Download: https://www.moomoo.com/download/OpenAPI
- Python SDK: https://pypi.org/project/moomoo-api/

Environment Variables:
    MOOMOO_HOST: OpenD host (default: 127.0.0.1)
    MOOMOO_PORT: OpenD port (default: 11111)
    MOOMOO_TRADE_PWD: Trade unlock password
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo

# CORRECT: Import from moomoo (NOT futu)
from moomoo import (
    OpenQuoteContext,
    OpenSecTradeContext,
    TrdMarket,
    TrdSide,
    OrderType,
    SecurityFirm,
    RET_OK,
    ModifyOrderOp,
    TrdEnv,
    KLType,
)

logger = logging.getLogger(__name__)
HK_TZ = ZoneInfo("Asia/Hong_Kong")


@dataclass
class OrderResult:
    """Result of an order submission."""
    order_id: str
    status: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    filled_price: Optional[float]
    filled_quantity: int
    message: str


@dataclass
class Position:
    """A portfolio position."""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


# HKEX Tick Size Table
# Reference: https://www.hkex.com.hk/Services/Trading/Securities/Overview/Trading-Mechanism?sc_lang=en
HKEX_TICK_SIZES = [
    (0.25, 0.001),
    (0.50, 0.005),
    (10.00, 0.01),
    (20.00, 0.02),
    (100.00, 0.05),
    (200.00, 0.10),
    (500.00, 0.20),
    (1000.00, 0.50),
    (2000.00, 1.00),
    (5000.00, 2.00),
    (float('inf'), 5.00),
]


class MoomooClient:
    """Moomoo client for HKEX trading.

    This client connects to the OpenD gateway to execute trades on HKEX.
    It provides a simpler authentication model compared to IBKR.

    Example:
        client = MoomooClient(paper_trading=True)
        client.connect()
        quote = client.get_quote("700")
        print(f"Tencent last price: {quote['last_price']}")
        client.disconnect()
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        trade_password: str = None,
        paper_trading: bool = True,
    ):
        """Initialize Moomoo client.

        Args:
            host: OpenD host (default: MOOMOO_HOST env or 127.0.0.1)
            port: OpenD port (default: MOOMOO_PORT env or 11111)
            trade_password: Trade unlock password
            paper_trading: Use paper trading environment
        """
        self.host = host or os.environ.get("MOOMOO_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("MOOMOO_PORT", "11111"))
        self.trade_password = trade_password or os.environ.get("MOOMOO_TRADE_PWD")
        self.trd_env = TrdEnv.SIMULATE if paper_trading else TrdEnv.REAL

        self.quote_ctx = None
        self.trade_ctx = None
        self._connected = False
        self._trade_unlocked = False

        logger.info(
            f"MoomooClient initialized: host={self.host}, port={self.port}, "
            f"paper_trading={paper_trading}"
        )

    def connect(self) -> bool:
        """Connect to OpenD and unlock trading.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Quote context for market data
            self.quote_ctx = OpenQuoteContext(
                host=self.host,
                port=self.port
            )

            # Trade context for HK market
            # Note: moomoo-api still uses FUTU* naming internally
            # FUTUAU = Moomoo Australia
            self.trade_ctx = OpenSecTradeContext(
                filter_trdmarket=TrdMarket.HK,
                host=self.host,
                port=self.port,
                security_firm=SecurityFirm.FUTUAU  # For Moomoo Australia (FUTUAU in API)
            )

            # Unlock trade if password provided
            if self.trade_password:
                ret, data = self.trade_ctx.unlock_trade(self.trade_password)
                if ret == RET_OK:
                    self._trade_unlocked = True
                    logger.info("Trade unlocked successfully")
                else:
                    logger.warning(f"Trade unlock failed: {data}")

            self._connected = True
            logger.info(f"Connected to OpenD at {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to OpenD: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from OpenD."""
        if self.quote_ctx:
            self.quote_ctx.close()
            self.quote_ctx = None
        if self.trade_ctx:
            self.trade_ctx.close()
            self.trade_ctx = None
        self._connected = False
        self._trade_unlocked = False
        logger.info("Disconnected from OpenD")

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    def is_trade_unlocked(self) -> bool:
        """Check if trading is unlocked."""
        return self._trade_unlocked

    def _format_hk_symbol(self, symbol: str) -> str:
        """Format symbol for HKEX.
        
        Args:
            symbol: Stock code (e.g., '700', '0700', '9988')
            
        Returns:
            Moomoo format (e.g., 'HK.00700')
        """
        # Remove any existing prefix
        if symbol.startswith("HK."):
            return symbol
        
        # Strip leading zeros, then pad to 5 digits
        num = symbol.lstrip('0') or '0'
        return f"HK.{num.zfill(5)}"

    def _parse_hk_symbol(self, moomoo_symbol: str) -> str:
        """Parse Moomoo symbol back to simple format.
        
        Args:
            moomoo_symbol: Moomoo format (e.g., 'HK.00700')
            
        Returns:
            Simple format (e.g., '700')
        """
        if moomoo_symbol.startswith("HK."):
            return moomoo_symbol[3:].lstrip('0') or '0'
        return moomoo_symbol

    def _round_to_tick(self, price: float) -> float:
        """Round price to valid HKEX tick size.
        
        Args:
            price: Raw price
            
        Returns:
            Price rounded to nearest valid tick
        """
        for threshold, tick in HKEX_TICK_SIZES:
            if price < threshold:
                # Round to nearest tick
                return round(round(price / tick) * tick, 3)
        # Fallback for very high prices
        return round(round(price / 5.0) * 5.0, 0)

    def get_quote(self, symbol: str) -> dict:
        """Get real-time quote for a symbol.
        
        Args:
            symbol: Stock code (e.g., '700' for Tencent)
            
        Returns:
            Dict with quote data including last_price, bid, ask, volume
        """
        if not self._connected:
            raise RuntimeError("Not connected to OpenD")

        moomoo_symbol = self._format_hk_symbol(symbol)
        ret, data = self.quote_ctx.get_market_snapshot([moomoo_symbol])

        if ret != RET_OK:
            logger.error(f"Failed to get quote for {symbol}: {data}")
            return {"error": str(data)}

        if data.empty:
            return {"error": f"No data for {symbol}"}

        row = data.iloc[0]
        return {
            "symbol": symbol,
            "moomoo_symbol": moomoo_symbol,
            "last_price": float(row.get("last_price", 0)),
            "open_price": float(row.get("open_price", 0)),
            "high_price": float(row.get("high_price", 0)),
            "low_price": float(row.get("low_price", 0)),
            "prev_close": float(row.get("prev_close_price", 0)),
            "volume": int(row.get("volume", 0)),
            "turnover": float(row.get("turnover", 0)),
            "bid_price": float(row.get("bid_price", 0)),
            "ask_price": float(row.get("ask_price", 0)),
            "bid_vol": int(row.get("bid_vol", 0)),
            "ask_vol": int(row.get("ask_vol", 0)),
            "update_time": str(row.get("update_time", "")),
        }

    def get_quotes_batch(self, symbols: List[str]) -> dict:
        """Get real-time quotes for multiple symbols in one API call.

        This method avoids rate limiting by fetching multiple symbols at once.
        Moomoo API supports up to 400 symbols per request.
        Rate limit: 60 requests per 30 seconds.

        Args:
            symbols: List of stock codes (e.g., ['700', '9988', '1810'])

        Returns:
            Dict mapping symbol to quote data
        """
        if not self._connected:
            raise RuntimeError("Not connected to OpenD")

        if not symbols:
            return {}

        # Convert all symbols to Moomoo format
        moomoo_symbols = [self._format_hk_symbol(s) for s in symbols]

        # Batch request (max 400 per call)
        batch_size = 400
        all_quotes = {}

        for i in range(0, len(moomoo_symbols), batch_size):
            batch = moomoo_symbols[i:i + batch_size]
            ret, data = self.quote_ctx.get_market_snapshot(batch)

            if ret != RET_OK:
                logger.error(f"Failed to get batch quotes: {data}")
                continue

            if data.empty:
                continue

            # Process each row
            for _, row in data.iterrows():
                moomoo_symbol = str(row.get("code", ""))
                symbol = self._parse_hk_symbol(moomoo_symbol)

                all_quotes[symbol] = {
                    "symbol": symbol,
                    "moomoo_symbol": moomoo_symbol,
                    "last_price": float(row.get("last_price", 0)),
                    "open_price": float(row.get("open_price", 0)),
                    "high_price": float(row.get("high_price", 0)),
                    "low_price": float(row.get("low_price", 0)),
                    "prev_close": float(row.get("prev_close_price", 0)),
                    "volume": int(row.get("volume", 0)),
                    "turnover": float(row.get("turnover", 0)),
                    "bid_price": float(row.get("bid_price", 0)),
                    "ask_price": float(row.get("ask_price", 0)),
                    "bid_vol": int(row.get("bid_vol", 0)),
                    "ask_vol": int(row.get("ask_vol", 0)),
                    "update_time": str(row.get("update_time", "")),
                    "change_pct": float(row.get("price_spread", 0)),  # % change
                }

        logger.info(f"Fetched {len(all_quotes)} quotes in batch")
        return all_quotes

    def get_portfolio(self) -> dict:
        """Get account portfolio summary.
        
        Returns:
            Dict with cash, equity, market_value, positions, P&L
        """
        if not self._connected:
            raise RuntimeError("Not connected to OpenD")

        ret, data = self.trade_ctx.accinfo_query(trd_env=self.trd_env)

        if ret != RET_OK:
            logger.error(f"Failed to get portfolio: {data}")
            return {"error": str(data)}

        if data.empty:
            return {"error": "No account data"}

        row = data.iloc[0]

        def safe_float(val, default=0.0):
            """Convert to float, handling 'N/A' and other non-numeric values."""
            if val is None or val == 'N/A' or val == '':
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        # Get positions for complete portfolio view
        positions_list = self.get_positions()
        positions_data = [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_cost": p.avg_cost,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "unrealized_pnl_pct": p.unrealized_pnl_pct,
            }
            for p in positions_list
        ]

        total_assets = safe_float(row.get("total_assets", 0))
        cash = safe_float(row.get("cash", 0))
        unrealized_pnl = safe_float(row.get("unrealized_pl", 0))

        return {
            "cash": cash,
            "equity": total_assets,  # Alias for tool_executor compatibility
            "total_assets": total_assets,
            "market_value": safe_float(row.get("market_val", 0)),
            "frozen_cash": safe_float(row.get("frozen_cash", 0)),
            "available_funds": safe_float(row.get("avl_withdrawal_cash", 0)),
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": safe_float(row.get("realized_pl", 0)),
            "currency": str(row.get("currency", "HKD")),
            "positions": positions_data,
            "position_count": len(positions_data),
            "daily_pnl": unrealized_pnl,  # Approximate with unrealized
            "daily_pnl_pct": (unrealized_pnl / total_assets * 100) if total_assets > 0 else 0,
        }

    def get_positions(self) -> List[Position]:
        """Get all open positions.
        
        Returns:
            List of Position objects
        """
        if not self._connected:
            raise RuntimeError("Not connected to OpenD")

        ret, data = self.trade_ctx.position_list_query(trd_env=self.trd_env)

        if ret != RET_OK:
            logger.error(f"Failed to get positions: {data}")
            return []

        positions = []
        for _, row in data.iterrows():
            qty = int(row.get("qty", 0))
            if qty == 0:
                continue

            positions.append(Position(
                symbol=self._parse_hk_symbol(str(row.get("code", ""))),
                quantity=qty,
                avg_cost=float(row.get("cost_price", 0)),
                current_price=float(row.get("nominal_price", 0)),
                unrealized_pnl=float(row.get("pl_val", 0)),
                unrealized_pnl_pct=float(row.get("pl_ratio", 0)) * 100,
            ))

        return positions

    def execute_trade(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "limit",
        limit_price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        reason: str = "",
    ) -> OrderResult:
        """Execute a trade.
        
        Args:
            symbol: Stock code (e.g., '700')
            side: 'buy' or 'sell'
            quantity: Number of shares (must be multiple of 100 for HKEX)
            order_type: 'market' or 'limit'
            limit_price: Required for limit orders
            stop_loss: Stop loss price (agent-managed, not native bracket)
            take_profit: Take profit price (agent-managed, not native bracket)
            reason: Reason for the trade (logged)
            
        Returns:
            OrderResult with order details
        """
        if not self._connected:
            raise RuntimeError("Not connected to OpenD")

        # Paper trading (SIMULATE) doesn't require trade unlock
        if self.trd_env != TrdEnv.SIMULATE and not self._trade_unlocked:
            raise RuntimeError("Trading not unlocked (required for REAL trading)")

        # Validate lot size (HKEX requires multiples of 100)
        if quantity % 100 != 0:
            logger.warning(f"Adjusting quantity {quantity} to nearest lot of 100")
            quantity = (quantity // 100) * 100
            if quantity == 0:
                quantity = 100

        moomoo_symbol = self._format_hk_symbol(symbol)

        # Map side
        trd_side = TrdSide.BUY if side.lower() == "buy" else TrdSide.SELL

        # Map order type and prepare price
        if order_type.lower() == "market":
            moomoo_order_type = OrderType.MARKET
            price = 0
        else:
            moomoo_order_type = OrderType.NORMAL  # Limit order
            if limit_price is None:
                raise ValueError("limit_price required for limit orders")
            price = self._round_to_tick(limit_price)

        logger.info(
            f"Executing {side} {quantity} {symbol} @ {price} ({order_type}) - {reason}"
        )

        ret, data = self.trade_ctx.place_order(
            price=price,
            qty=quantity,
            code=moomoo_symbol,
            trd_side=trd_side,
            order_type=moomoo_order_type,
            trd_env=self.trd_env,
        )

        if ret != RET_OK:
            logger.error(f"Order failed: {data}")
            return OrderResult(
                order_id="",
                status="FAILED",
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                filled_price=None,
                filled_quantity=0,
                message=str(data),
            )

        row = data.iloc[0]
        order_id = str(row.get("order_id", ""))

        logger.info(f"Order placed: {order_id}")

        # Log stop loss / take profit for agent to track
        if stop_loss:
            logger.info(f"Agent-managed SL for {order_id}: {stop_loss}")
        if take_profit:
            logger.info(f"Agent-managed TP for {order_id}: {take_profit}")

        return OrderResult(
            order_id=order_id,
            status=str(row.get("order_status", "SUBMITTED")),
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            filled_price=float(row.get("dealt_avg_price", 0)) or None,
            filled_quantity=int(row.get("dealt_qty", 0)),
            message=f"Order {order_id} submitted",
        )

    def close_position(self, symbol: str, reason: str = "") -> OrderResult:
        """Close a specific position.
        
        Args:
            symbol: Stock code to close
            reason: Reason for closing
            
        Returns:
            OrderResult with order details
        """
        positions = self.get_positions()
        position = next((p for p in positions if p.symbol == symbol), None)

        if not position:
            return OrderResult(
                order_id="",
                status="NO_POSITION",
                symbol=symbol,
                side="sell",
                quantity=0,
                order_type="market",
                filled_price=None,
                filled_quantity=0,
                message=f"No position found for {symbol}",
            )

        return self.execute_trade(
            symbol=symbol,
            side="sell",
            quantity=position.quantity,
            order_type="market",
            reason=reason or f"Closing position in {symbol}",
        )

    def close_all_positions(self, reason: str = "") -> List[OrderResult]:
        """Emergency: close all positions.
        
        Args:
            reason: Reason for closing all
            
        Returns:
            List of OrderResults
        """
        positions = self.get_positions()
        results = []

        for position in positions:
            result = self.close_position(
                symbol=position.symbol,
                reason=reason or "Emergency close all positions",
            )
            results.append(result)

        return results

    def get_order_status(self, order_id: str) -> dict:
        """Get status of a specific order.
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Dict with order status details
        """
        if not self._connected:
            raise RuntimeError("Not connected to OpenD")

        ret, data = self.trade_ctx.order_list_query(trd_env=self.trd_env)

        if ret != RET_OK:
            return {"error": str(data)}

        for _, row in data.iterrows():
            if str(row.get("order_id", "")) == order_id:
                return {
                    "order_id": order_id,
                    "status": str(row.get("order_status", "")),
                    "symbol": self._parse_hk_symbol(str(row.get("code", ""))),
                    "side": str(row.get("trd_side", "")),
                    "quantity": int(row.get("qty", 0)),
                    "filled_quantity": int(row.get("dealt_qty", 0)),
                    "price": float(row.get("price", 0)),
                    "filled_price": float(row.get("dealt_avg_price", 0)),
                    "create_time": str(row.get("create_time", "")),
                    "update_time": str(row.get("updated_time", "")),
                }

        return {"error": f"Order {order_id} not found"}

    def cancel_order(self, order_id: str) -> dict:
        """Cancel a pending order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Dict with cancellation result
        """
        if not self._connected:
            raise RuntimeError("Not connected to OpenD")

        ret, data = self.trade_ctx.modify_order(
            modify_order_op=ModifyOrderOp.CANCEL,
            order_id=order_id,
            qty=0,
            price=0,
            trd_env=self.trd_env,
        )

        if ret != RET_OK:
            return {"success": False, "error": str(data)}

        return {"success": True, "order_id": order_id, "message": "Order cancelled"}

    def get_historical_data(
        self,
        symbol: str,
        duration: str = "5 D",
        bar_size: str = "15 mins",
    ) -> List[dict]:
        """Get historical OHLCV data for a symbol.

        Args:
            symbol: Stock code (e.g., "700" or "00700")
            duration: Duration string (e.g., "5 D", "30 D") - used to calculate start date
            bar_size: Bar size string (e.g., "5 mins", "15 mins", "1 hour", "1 day")

        Returns:
            List of dicts with date, open, high, low, close, volume
        """
        if not self._connected:
            raise RuntimeError("Not connected to OpenD")

        # Map bar_size to KLType
        kl_type_map = {
            "1 min": KLType.K_1M,
            "3 mins": KLType.K_3M,
            "5 mins": KLType.K_5M,
            "15 mins": KLType.K_15M,
            "30 mins": KLType.K_30M,
            "1 hour": KLType.K_60M,
            "60 mins": KLType.K_60M,
            "1 day": KLType.K_DAY,
            "1 week": KLType.K_WEEK,
            "1 month": KLType.K_MON,
        }
        kl_type = kl_type_map.get(bar_size, KLType.K_15M)

        # Parse duration to calculate max_count
        # Format: "X D" for days, estimate bars needed
        try:
            parts = duration.strip().split()
            num = int(parts[0])
            unit = parts[1].upper() if len(parts) > 1 else "D"

            # Estimate bars based on timeframe
            if kl_type in [KLType.K_1M, KLType.K_3M, KLType.K_5M, KLType.K_15M, KLType.K_30M, KLType.K_60M]:
                # Intraday: ~6.5 trading hours per day
                minutes_per_bar = {
                    KLType.K_1M: 1, KLType.K_3M: 3, KLType.K_5M: 5,
                    KLType.K_15M: 15, KLType.K_30M: 30, KLType.K_60M: 60
                }
                bars_per_day = (6.5 * 60) / minutes_per_bar.get(kl_type, 15)
                max_count = int(num * bars_per_day) + 50  # Add buffer
            else:
                # Daily/weekly: just use days
                max_count = num + 10
        except (ValueError, IndexError):
            max_count = 200

        max_count = min(max_count, 1000)  # API limit

        # Format symbol for Moomoo
        moomoo_symbol = self._format_hk_symbol(symbol)

        # Fetch historical data
        ret, data, _ = self.quote_ctx.request_history_kline(
            code=moomoo_symbol,
            ktype=kl_type,
            max_count=max_count,
        )

        if ret != RET_OK:
            logger.error(f"Failed to get historical data for {symbol}: {data}")
            raise RuntimeError(f"Failed to get historical data: {data}")

        # Convert DataFrame to list of dicts
        result = []
        for _, row in data.iterrows():
            result.append({
                "date": row.get("time_key", ""),
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": int(row.get("volume", 0)),
            })

        logger.info(f"Fetched {len(result)} bars for {symbol} ({bar_size})")
        return result


# Module-level client instance for convenience
_client: Optional[MoomooClient] = None


def get_moomoo_client() -> MoomooClient:
    """Get the global MoomooClient instance."""
    global _client
    if _client is None:
        raise RuntimeError("MoomooClient not initialized. Call init_moomoo_client() first.")
    return _client


def init_moomoo_client(
    host: str = None,
    port: int = None,
    trade_password: str = None,
    paper_trading: bool = True,
) -> MoomooClient:
    """Initialize and connect the global MoomooClient.
    
    Args:
        host: OpenD host
        port: OpenD port
        trade_password: Trade unlock password
        paper_trading: Use paper trading environment
        
    Returns:
        Connected MoomooClient instance
    """
    global _client
    _client = MoomooClient(
        host=host,
        port=port,
        trade_password=trade_password,
        paper_trading=paper_trading,
    )
    _client.connect()
    return _client
