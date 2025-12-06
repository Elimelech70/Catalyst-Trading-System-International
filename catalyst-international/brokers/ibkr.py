"""
Name of Application: Catalyst Trading System
Name of file: ibkr.py
Version: 1.0.0
Last Updated: 2025-12-06
Purpose: Interactive Brokers client for HKEX trading

REVISION HISTORY:
v1.0.0 (2025-12-06) - Initial implementation
- IBKR TWS/Gateway connection
- Order execution with bracket orders
- Portfolio and position management
- Market hours validation

Description:
This module provides connectivity to Interactive Brokers for trading
on the Hong Kong Stock Exchange (HKEX). It handles connection management,
order submission, and portfolio queries using the ib_insync library.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ib_insync import IB, Contract, LimitOrder, MarketOrder, Order, Stock, Trade

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
    filled_price: float | None
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


class IBKRClient:
    """Interactive Brokers client for HKEX trading."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        client_id: int | None = None,
        timeout: int = 30,
    ):
        """Initialize IBKR client.

        Args:
            host: TWS/Gateway host (default: IBKR_HOST env or 127.0.0.1)
            port: TWS/Gateway port (7497=paper, 7496=live)
            client_id: Client ID for connection
            timeout: Connection timeout in seconds
        """
        self.host = host or os.environ.get("IBKR_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("IBKR_PORT", "7497"))
        self.client_id = client_id or int(os.environ.get("IBKR_CLIENT_ID", "1"))
        self.timeout = timeout

        self.ib = IB()
        self._connected = False

    def connect(self) -> bool:
        """Connect to TWS/Gateway.

        Returns:
            True if connected successfully
        """
        if self._connected and self.ib.isConnected():
            return True

        try:
            self.ib.connect(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                timeout=self.timeout,
            )
            self._connected = True
            logger.info(
                f"Connected to IBKR at {self.host}:{self.port} (client {self.client_id})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from TWS/Gateway."""
        if self._connected:
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IBKR")

    def is_connected(self) -> bool:
        """Check if connected to IBKR."""
        return self._connected and self.ib.isConnected()

    def _ensure_connected(self):
        """Ensure we're connected, reconnect if needed."""
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError("Cannot connect to IBKR")

    def _create_hkex_contract(self, symbol: str) -> Contract:
        """Create an HKEX stock contract.

        Args:
            symbol: Stock code (e.g., '0700')

        Returns:
            IB Contract object
        """
        # HKEX symbols in IBKR format
        # Pad with leading zeros if needed
        symbol = symbol.zfill(4)

        contract = Stock(symbol, "SEHK", "HKD")
        return contract

    # =========================================================================
    # Quote and Market Data
    # =========================================================================

    def get_quote(self, symbol: str) -> dict:
        """Get current quote for a symbol.

        Args:
            symbol: HKEX stock code

        Returns:
            Quote data dictionary
        """
        self._ensure_connected()

        contract = self._create_hkex_contract(symbol)

        # Request market data
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, "", False, False)

        # Wait for data
        self.ib.sleep(1)

        # Build quote response
        quote = {
            "symbol": symbol,
            "name": contract.localSymbol or symbol,
            "last": ticker.last if ticker.last else ticker.close,
            "bid": ticker.bid if ticker.bid else 0,
            "ask": ticker.ask if ticker.ask else 0,
            "volume": int(ticker.volume) if ticker.volume else 0,
            "avg_volume": 0,  # Would need historical data
            "high": ticker.high if ticker.high else 0,
            "low": ticker.low if ticker.low else 0,
            "open": ticker.open if ticker.open else 0,
            "prev_close": ticker.close if ticker.close else 0,
            "change": 0,
            "change_pct": 0,
            "market_cap": 0,
        }

        # Calculate change
        if quote["last"] and quote["prev_close"]:
            quote["change"] = quote["last"] - quote["prev_close"]
            quote["change_pct"] = (quote["change"] / quote["prev_close"]) * 100

        # Cancel market data subscription
        self.ib.cancelMktData(contract)

        return quote

    def get_historical_data(
        self, symbol: str, duration: str = "5 D", bar_size: str = "15 mins"
    ) -> list[dict]:
        """Get historical price data.

        Args:
            symbol: Stock code
            duration: Duration string (e.g., "5 D", "1 M")
            bar_size: Bar size (e.g., "5 mins", "1 hour", "1 day")

        Returns:
            List of OHLCV bars
        """
        self._ensure_connected()

        contract = self._create_hkex_contract(symbol)
        self.ib.qualifyContracts(contract)

        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )

        return [
            {
                "date": bar.date,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for bar in bars
        ]

    # =========================================================================
    # Order Execution
    # =========================================================================

    def execute_trade(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        limit_price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        reason: str = "",
    ) -> dict:
        """Execute a trade with optional bracket orders.

        Args:
            symbol: Stock code
            side: 'buy' or 'sell'
            quantity: Number of shares
            order_type: 'market' or 'limit'
            limit_price: Price for limit orders
            stop_loss: Stop loss price
            take_profit: Take profit price
            reason: Trade reason for logging

        Returns:
            Order result dictionary
        """
        self._ensure_connected()

        contract = self._create_hkex_contract(symbol)
        self.ib.qualifyContracts(contract)

        # Normalize side
        action = "BUY" if side.lower() in ["buy", "long"] else "SELL"

        # Create main order
        if order_type.lower() == "limit" and limit_price:
            # Round to valid tick size (HKEX has specific tick sizes)
            limit_price = self._round_to_tick(limit_price)
            main_order = LimitOrder(action, quantity, limit_price)
        else:
            main_order = MarketOrder(action, quantity)

        main_order.tif = "DAY"

        # Submit main order
        trade = self.ib.placeOrder(contract, main_order)
        self.ib.sleep(1)

        # Get fill info
        filled_price = None
        filled_qty = 0

        if trade.orderStatus.status == "Filled":
            filled_price = trade.orderStatus.avgFillPrice
            filled_qty = int(trade.orderStatus.filled)

            # Place bracket orders if we have stop/target
            if stop_loss:
                self._place_stop_order(contract, symbol, action, filled_qty, stop_loss)
            if take_profit:
                self._place_take_profit_order(
                    contract, symbol, action, filled_qty, take_profit
                )

        result = {
            "order_id": str(trade.order.orderId),
            "status": trade.orderStatus.status,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "filled_price": filled_price,
            "filled_quantity": filled_qty,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reason": reason,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

        logger.info(
            f"Order executed: {action} {quantity} {symbol} @ {filled_price or 'pending'}"
        )

        return result

    def _place_stop_order(
        self,
        contract: Contract,
        symbol: str,
        parent_action: str,
        quantity: int,
        stop_price: float,
    ) -> Trade:
        """Place a stop loss order."""
        # Reverse action for stop
        action = "SELL" if parent_action == "BUY" else "BUY"

        stop_price = self._round_to_tick(stop_price)

        order = Order()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = "STP"
        order.auxPrice = stop_price
        order.tif = "GTC"

        trade = self.ib.placeOrder(contract, order)
        logger.info(f"Stop order placed: {action} {quantity} {symbol} @ {stop_price}")

        return trade

    def _place_take_profit_order(
        self,
        contract: Contract,
        symbol: str,
        parent_action: str,
        quantity: int,
        target_price: float,
    ) -> Trade:
        """Place a take profit limit order."""
        action = "SELL" if parent_action == "BUY" else "BUY"

        target_price = self._round_to_tick(target_price)

        order = LimitOrder(action, quantity, target_price)
        order.tif = "GTC"

        trade = self.ib.placeOrder(contract, order)
        logger.info(
            f"Take profit order placed: {action} {quantity} {symbol} @ {target_price}"
        )

        return trade

    def _round_to_tick(self, price: float) -> float:
        """Round price to valid HKEX tick size.

        HKEX tick sizes:
        - 0.001 for prices < 0.25
        - 0.005 for prices 0.25 - 0.50
        - 0.01 for prices 0.50 - 10.00
        - 0.02 for prices 10.00 - 20.00
        - 0.05 for prices 20.00 - 100.00
        - 0.10 for prices 100.00 - 200.00
        - 0.20 for prices 200.00 - 500.00
        - 0.50 for prices 500.00 - 1000.00
        - 1.00 for prices 1000.00 - 2000.00
        - 2.00 for prices 2000.00 - 5000.00
        - 5.00 for prices > 5000.00
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

    def close_position(self, symbol: str, reason: str = "") -> dict:
        """Close an existing position.

        Args:
            symbol: Stock code
            reason: Reason for closing

        Returns:
            Order result dictionary
        """
        self._ensure_connected()

        # Get current position
        positions = self.get_positions()
        position = next((p for p in positions if p["symbol"] == symbol), None)

        if not position:
            return {
                "status": "error",
                "symbol": symbol,
                "message": f"No position found for {symbol}",
            }

        # Determine side to close
        quantity = abs(position["quantity"])
        side = "sell" if position["quantity"] > 0 else "buy"

        # Execute market order to close
        result = self.execute_trade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="market",
            reason=f"Close position: {reason}",
        )

        # Calculate realized P&L
        if result["filled_price"]:
            if side == "sell":
                realized_pnl = (
                    result["filled_price"] - position["avg_cost"]
                ) * quantity
            else:
                realized_pnl = (
                    position["avg_cost"] - result["filled_price"]
                ) * quantity
            result["realized_pnl"] = round(realized_pnl, 2)

        return result

    def close_all_positions(self, reason: str = "") -> list[dict]:
        """Close all open positions.

        Args:
            reason: Reason for closing all

        Returns:
            List of order results
        """
        self._ensure_connected()

        positions = self.get_positions()
        results = []

        for position in positions:
            if position["quantity"] != 0:
                result = self.close_position(position["symbol"], reason)
                results.append(result)

        logger.warning(f"Closed all positions ({len(results)} total): {reason}")

        return results

    # =========================================================================
    # Portfolio Management
    # =========================================================================

    def get_portfolio(self) -> dict:
        """Get current portfolio status.

        Returns:
            Portfolio summary dictionary
        """
        self._ensure_connected()

        # Get account values
        account_values = self.ib.accountValues()

        # Extract key metrics
        cash = 0
        equity = 0
        unrealized_pnl = 0
        realized_pnl = 0

        for av in account_values:
            if av.currency == "HKD":
                if av.tag == "CashBalance":
                    cash = float(av.value)
                elif av.tag == "NetLiquidation":
                    equity = float(av.value)
                elif av.tag == "UnrealizedPnL":
                    unrealized_pnl = float(av.value)
                elif av.tag == "RealizedPnL":
                    realized_pnl = float(av.value)

        # Get positions
        positions = self.get_positions()

        daily_pnl = realized_pnl + unrealized_pnl
        daily_pnl_pct = (daily_pnl / equity) * 100 if equity > 0 else 0

        return {
            "cash": round(cash, 2),
            "equity": round(equity, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "buying_power": round(cash, 2),
            "position_count": len([p for p in positions if p["quantity"] != 0]),
            "positions": positions,
            "timestamp": datetime.now(HK_TZ).isoformat(),
        }

    def get_positions(self) -> list[dict]:
        """Get current positions.

        Returns:
            List of position dictionaries
        """
        self._ensure_connected()

        ib_positions = self.ib.positions()
        positions = []

        for pos in ib_positions:
            # Filter for HKEX positions
            if pos.contract.exchange != "SEHK":
                continue

            symbol = pos.contract.symbol
            quantity = int(pos.position)
            avg_cost = pos.avgCost

            # Get current price
            try:
                quote = self.get_quote(symbol)
                current_price = quote["last"]
            except Exception:
                current_price = avg_cost

            # Calculate P&L
            if quantity != 0:
                unrealized_pnl = (current_price - avg_cost) * quantity
                unrealized_pnl_pct = (
                    ((current_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
                )
            else:
                unrealized_pnl = 0
                unrealized_pnl_pct = 0

            positions.append(
                {
                    "symbol": symbol,
                    "quantity": quantity,
                    "avg_cost": round(avg_cost, 2),
                    "current_price": round(current_price, 2),
                    "market_value": round(current_price * quantity, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                }
            )

        return positions

    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in a symbol."""
        positions = self.get_positions()
        return any(p["symbol"] == symbol and p["quantity"] != 0 for p in positions)

    # =========================================================================
    # Orders Management
    # =========================================================================

    def get_open_orders(self) -> list[dict]:
        """Get all open orders.

        Returns:
            List of open order dictionaries
        """
        self._ensure_connected()

        trades = self.ib.openTrades()
        orders = []

        for trade in trades:
            orders.append(
                {
                    "order_id": str(trade.order.orderId),
                    "symbol": trade.contract.symbol,
                    "action": trade.order.action,
                    "quantity": trade.order.totalQuantity,
                    "order_type": trade.order.orderType,
                    "limit_price": trade.order.lmtPrice,
                    "aux_price": trade.order.auxPrice,
                    "status": trade.orderStatus.status,
                    "filled": trade.orderStatus.filled,
                    "remaining": trade.orderStatus.remaining,
                }
            )

        return orders

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        self._ensure_connected()

        trades = self.ib.openTrades()

        for trade in trades:
            if str(trade.order.orderId) == order_id:
                self.ib.cancelOrder(trade.order)
                logger.info(f"Cancelled order {order_id}")
                return True

        logger.warning(f"Order {order_id} not found")
        return False

    def cancel_all_orders(self) -> int:
        """Cancel all open orders.

        Returns:
            Number of orders cancelled
        """
        self._ensure_connected()

        trades = self.ib.openTrades()
        count = 0

        for trade in trades:
            self.ib.cancelOrder(trade.order)
            count += 1

        logger.info(f"Cancelled {count} orders")
        return count


# Singleton instance
_ibkr_client: IBKRClient | None = None


def get_ibkr_client(
    host: str | None = None,
    port: int | None = None,
    client_id: int | None = None,
) -> IBKRClient:
    """Get or create IBKR client singleton."""
    global _ibkr_client
    if _ibkr_client is None:
        _ibkr_client = IBKRClient(host=host, port=port, client_id=client_id)
    return _ibkr_client


def init_ibkr_client(
    host: str | None = None,
    port: int | None = None,
    client_id: int | None = None,
) -> IBKRClient:
    """Initialize and connect IBKR client."""
    global _ibkr_client
    _ibkr_client = IBKRClient(host=host, port=port, client_id=client_id)
    _ibkr_client.connect()
    return _ibkr_client
