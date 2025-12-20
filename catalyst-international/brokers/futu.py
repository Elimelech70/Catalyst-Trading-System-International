"""
Name of Application: Catalyst Trading System
Name of file: futu.py
Version: 1.0.0
Last Updated: 2025-12-20
Purpose: Moomoo/Futu client for HKEX trading

REVISION HISTORY:
v1.0.0 (2025-12-20) - Initial implementation
- Migrated from IBKR to Futu OpenAPI
- Simpler authentication (no Docker/2FA)
- Native socket API via OpenD

Description:
This module provides the FutuClient class for trading HKEX stocks via
Moomoo/Futu's OpenD gateway. It replaces the IBKR integration to eliminate
the authentication complexity of IB Gateway.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo

from futu import (
    OpenQuoteContext,
    OpenSecTradeContext,
    TrdMarket,
    TrdSide,
    OrderType,
    SecurityFirm,
    RET_OK,
    ModifyOrderOp,
    TrdEnv,
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


class FutuClient:
    """Moomoo/Futu client for HKEX trading.

    This client connects to the OpenD gateway to execute trades on HKEX.
    It provides a simpler authentication model compared to IBKR.

    Environment Variables:
        FUTU_HOST: OpenD host (default: 127.0.0.1)
        FUTU_PORT: OpenD port (default: 11111)
        FUTU_TRADE_PWD: Trade unlock password
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        trade_password: str = None,
        paper_trading: bool = True,
    ):
        """Initialize Futu client.

        Args:
            host: OpenD host (default: FUTU_HOST env or 127.0.0.1)
            port: OpenD port (default: FUTU_PORT env or 11111)
            trade_password: Trade unlock password
            paper_trading: Use paper trading environment
        """
        self.host = host or os.environ.get("FUTU_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("FUTU_PORT", "11111"))
        self.trade_password = trade_password or os.environ.get("FUTU_TRADE_PWD")
        self.trd_env = TrdEnv.SIMULATE if paper_trading else TrdEnv.REAL

        self.quote_ctx = None
        self.trade_ctx = None
        self._connected = False
        self._trade_unlocked = False

        logger.info(f"FutuClient initialized: host={self.host}, port={self.port}, "
                    f"paper_trading={paper_trading}")

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

            # Check connection
            ret, data = self.quote_ctx.get_global_state()
            if ret != RET_OK:
                logger.error(f"Failed to connect to OpenD: {data}")
                return False

            logger.info(f"Quote context connected: {data}")

            # Trade context for HK market
            self.trade_ctx = OpenSecTradeContext(
                filter_trdmarket=TrdMarket.HK,
                host=self.host,
                port=self.port,
                security_firm=SecurityFirm.FUTUSECURITIES
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
        if not self._connected:
            return False

        # Verify connection is still alive
        try:
            ret, _ = self.quote_ctx.get_global_state()
            return ret == RET_OK
        except:
            self._connected = False
            return False

    def _format_hk_symbol(self, symbol: str) -> str:
        """Format symbol for HKEX (e.g., '700' -> 'HK.00700').

        Args:
            symbol: Stock code (e.g., '700', '0700', '9988')

        Returns:
            Futu-formatted symbol (e.g., 'HK.00700')
        """
        # Strip leading zeros for comparison, then pad to 5 digits
        num = symbol.lstrip('0') or '0'
        return f"HK.{num.zfill(5)}"

    def _parse_hk_symbol(self, futu_symbol: str) -> str:
        """Parse Futu symbol back to simple code (e.g., 'HK.00700' -> '700')."""
        code = futu_symbol.replace("HK.", "").lstrip("0")
        return code or "0"

    def get_quote(self, symbol: str) -> dict:
        """Get current quote for a symbol.

        Args:
            symbol: Stock code (e.g., '700')

        Returns:
            Dict with quote data or empty dict on failure
        """
        if not self._connected:
            logger.error("Not connected to OpenD")
            return {}

        hk_symbol = self._format_hk_symbol(symbol)
        ret, data = self.quote_ctx.get_market_snapshot([hk_symbol])

        if ret != RET_OK:
            logger.error(f"Failed to get quote for {symbol}: {data}")
            return {}

        if data.empty:
            logger.warning(f"No quote data for {symbol}")
            return {}

        row = data.iloc[0]
        return {
            "symbol": symbol,
            "last_price": float(row.get("last_price", 0)),
            "bid": float(row.get("bid_price", 0)),
            "ask": float(row.get("ask_price", 0)),
            "volume": int(row.get("volume", 0)),
            "turnover": float(row.get("turnover", 0)),
            "high": float(row.get("high_price", 0)),
            "low": float(row.get("low_price", 0)),
            "open": float(row.get("open_price", 0)),
            "prev_close": float(row.get("prev_close_price", 0)),
            "change_pct": float(row.get("price_spread", 0)),
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def get_positions(self) -> List[Position]:
        """Get all open positions.

        Returns:
            List of Position objects
        """
        if not self._connected:
            logger.error("Not connected to OpenD")
            return []

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
                symbol=self._parse_hk_symbol(row["code"]),
                quantity=qty,
                avg_cost=float(row.get("cost_price", 0)),
                current_price=float(row.get("market_val", 0) / qty) if qty else 0,
                unrealized_pnl=float(row.get("pl_val", 0)),
                unrealized_pnl_pct=float(row.get("pl_ratio", 0) * 100) if row.get("pl_ratio") else 0,
            ))

        return positions

    def get_portfolio(self) -> dict:
        """Get portfolio summary.

        Returns:
            Dict with portfolio data or empty dict on failure
        """
        if not self._connected:
            logger.error("Not connected to OpenD")
            return {}

        ret, data = self.trade_ctx.accinfo_query(trd_env=self.trd_env)

        if ret != RET_OK:
            logger.error(f"Failed to get portfolio: {data}")
            return {}

        if data.empty:
            logger.warning("No portfolio data returned")
            return {}

        row = data.iloc[0]
        return {
            "total_value": float(row.get("total_assets", 0)),
            "cash": float(row.get("cash", 0)),
            "market_value": float(row.get("market_val", 0)),
            "buying_power": float(row.get("power", 0)),
            "currency": "HKD",
            "environment": "PAPER" if self.trd_env == TrdEnv.SIMULATE else "LIVE",
        }

    def _round_to_tick(self, price: float) -> float:
        """Round price to valid HKEX tick size.

        HKEX has 11 tick size tiers based on price.

        Args:
            price: Raw price

        Returns:
            Price rounded to valid tick size
        """
        if price < 0.25:
            tick = 0.001
        elif price < 0.50:
            tick = 0.005
        elif price < 10.00:
            tick = 0.01
        elif price < 20.00:
            tick = 0.02
        elif price < 100.00:
            tick = 0.05
        elif price < 200.00:
            tick = 0.10
        elif price < 500.00:
            tick = 0.20
        elif price < 1000.00:
            tick = 0.50
        elif price < 2000.00:
            tick = 1.00
        elif price < 5000.00:
            tick = 2.00
        else:
            tick = 5.00

        return round(round(price / tick) * tick, 3)

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
            symbol: Stock code (e.g., '700' for Tencent)
            side: 'buy' or 'sell'
            quantity: Number of shares (should be multiple of lot size, typically 100)
            order_type: 'market' or 'limit'
            limit_price: Price for limit orders
            stop_loss: Stop loss price (logged only, not native bracket)
            take_profit: Take profit price (logged only, not native bracket)
            reason: Reason for trade (for logging/audit)

        Returns:
            OrderResult with order details
        """
        if not self._trade_unlocked:
            return OrderResult(
                order_id="",
                status="REJECTED",
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                filled_price=None,
                filled_quantity=0,
                message="Trade not unlocked - call connect() with trade_password",
            )

        hk_symbol = self._format_hk_symbol(symbol)

        # Normalize and map side
        side_lower = side.lower()
        if side_lower in ["buy", "long"]:
            trd_side = TrdSide.BUY
            side_str = "buy"
        elif side_lower in ["sell", "short"]:
            trd_side = TrdSide.SELL
            side_str = "sell"
        else:
            return OrderResult(
                order_id="",
                status="REJECTED",
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                filled_price=None,
                filled_quantity=0,
                message=f"Invalid side: {side}. Must be buy/long or sell/short.",
            )

        # Map order type and round price
        if order_type.lower() == "market":
            futu_order_type = OrderType.MARKET
            price = 0
        else:
            futu_order_type = OrderType.NORMAL  # Limit order
            if not limit_price:
                return OrderResult(
                    order_id="",
                    status="REJECTED",
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    filled_price=None,
                    filled_quantity=0,
                    message="limit_price required for limit orders",
                )
            price = self._round_to_tick(limit_price)

        logger.info(
            f"Executing trade: {side_str} {quantity} {symbol} @ {price} "
            f"[SL: {stop_loss}, TP: {take_profit}] Reason: {reason}"
        )

        # Place main order
        try:
            ret, data = self.trade_ctx.place_order(
                price=price,
                qty=quantity,
                code=hk_symbol,
                trd_side=trd_side,
                order_type=futu_order_type,
                trd_env=self.trd_env,
                remark=reason[:64] if reason else "",
            )
        except Exception as e:
            logger.error(f"Order execution error: {e}")
            return OrderResult(
                order_id="",
                status="ERROR",
                symbol=symbol,
                side=side_str,
                quantity=quantity,
                order_type=order_type,
                filled_price=None,
                filled_quantity=0,
                message=str(e),
            )

        if ret != RET_OK:
            logger.error(f"Order failed: {data}")
            return OrderResult(
                order_id="",
                status="REJECTED",
                symbol=symbol,
                side=side_str,
                quantity=quantity,
                order_type=order_type,
                filled_price=None,
                filled_quantity=0,
                message=str(data),
            )

        order_id = str(data.iloc[0]["order_id"])

        # Note: Futu doesn't have native bracket orders like IBKR
        # Stop loss and take profit must be managed separately
        if stop_loss or take_profit:
            logger.info(
                f"Note: SL={stop_loss}, TP={take_profit} must be managed via "
                f"conditional orders or agent monitoring (no native bracket orders)"
            )

        logger.info(f"Order submitted successfully: {order_id}")

        return OrderResult(
            order_id=order_id,
            status="SUBMITTED",
            symbol=symbol,
            side=side_str,
            quantity=quantity,
            order_type=order_type,
            filled_price=None,
            filled_quantity=0,
            message=f"Order submitted: {order_id}",
        )

    def get_orders(self, status_filter: str = None) -> List[dict]:
        """Get orders.

        Args:
            status_filter: Optional status filter ('open', 'filled', 'cancelled')

        Returns:
            List of order dicts
        """
        if not self._connected:
            logger.error("Not connected to OpenD")
            return []

        ret, data = self.trade_ctx.order_list_query(trd_env=self.trd_env)

        if ret != RET_OK:
            logger.error(f"Failed to get orders: {data}")
            return []

        orders = []
        for _, row in data.iterrows():
            order = {
                "order_id": str(row["order_id"]),
                "symbol": self._parse_hk_symbol(row["code"]),
                "side": "buy" if row["trd_side"] == TrdSide.BUY else "sell",
                "quantity": int(row["qty"]),
                "filled_quantity": int(row.get("dealt_qty", 0)),
                "price": float(row["price"]),
                "status": str(row.get("order_status", "")),
                "create_time": str(row.get("create_time", "")),
            }
            orders.append(order)

        return orders

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        if not self._connected:
            logger.error("Not connected to OpenD")
            return False

        ret, data = self.trade_ctx.modify_order(
            ModifyOrderOp.CANCEL,
            order_id=order_id,
            qty=0,
            price=0,
            trd_env=self.trd_env,
        )

        if ret != RET_OK:
            logger.error(f"Failed to cancel order {order_id}: {data}")
            return False

        logger.info(f"Order {order_id} cancelled")
        return True

    def close_position(self, symbol: str, reason: str = "") -> OrderResult:
        """Close an existing position.

        Args:
            symbol: Stock code
            reason: Reason for closing (for audit trail)

        Returns:
            OrderResult from the closing order
        """
        positions = self.get_positions()
        position = next((p for p in positions if p.symbol == symbol), None)

        if not position:
            return OrderResult(
                order_id="",
                status="REJECTED",
                symbol=symbol,
                side="sell",
                quantity=0,
                order_type="market",
                filled_price=None,
                filled_quantity=0,
                message=f"No open position for {symbol}",
            )

        # Close with market order
        return self.execute_trade(
            symbol=symbol,
            side="sell" if position.quantity > 0 else "buy",
            quantity=abs(position.quantity),
            order_type="market",
            reason=reason or f"Closing position in {symbol}",
        )

    def close_all_positions(self, reason: str = "") -> List[OrderResult]:
        """Close all open positions (emergency exit).

        Args:
            reason: Reason for closing all positions

        Returns:
            List of OrderResults for each position closed
        """
        positions = self.get_positions()
        results = []

        for position in positions:
            result = self.close_position(
                symbol=position.symbol,
                reason=reason or "Emergency close all positions",
            )
            results.append(result)
            logger.info(f"Closed {position.symbol}: {result.status}")

        return results


# Global client instance
_futu_client: Optional[FutuClient] = None


def init_futu_client(**kwargs) -> FutuClient:
    """Initialize global Futu client.

    Args:
        **kwargs: Arguments passed to FutuClient constructor

    Returns:
        Initialized FutuClient
    """
    global _futu_client
    _futu_client = FutuClient(**kwargs)
    return _futu_client


def get_futu_client() -> Optional[FutuClient]:
    """Get global Futu client.

    Returns:
        Global FutuClient instance or None if not initialized
    """
    return _futu_client
