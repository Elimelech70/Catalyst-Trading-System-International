"""
Name of Application: Catalyst Trading System
Name of file: agent/execution.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Trade execution via Interactive Brokers

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- IBKR connection management
- Order execution with bracket orders
- Portfolio and position management

Description:
This module handles all trade execution through Interactive Brokers.
It wraps the IBKR client and provides async interface for the agent.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

import structlog

from ib_async import IB, Contract, LimitOrder, MarketOrder, Order, Stock

logger = structlog.get_logger()

HK_TZ = ZoneInfo("Asia/Hong_Kong")


@dataclass
class ExecutionResult:
    """Result of trade execution."""

    success: bool
    order_id: Optional[str] = None
    status: str = ""
    symbol: str = ""
    side: str = ""
    quantity: int = 0
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    position_id: Optional[int] = None
    message: str = ""
    timestamp: str = ""


class ExecutionEngine:
    """Trade execution via Interactive Brokers."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        timeout: int = 30,
    ):
        """Initialize execution engine.

        Args:
            host: IBKR TWS/Gateway host
            port: IBKR port (7497=paper, 7496=live)
            client_id: Client ID for connection
            timeout: Connection timeout seconds
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout

        self.ib = IB()
        self._connected = False

    async def connect(self) -> bool:
        """Connect to IBKR."""
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
                "Connected to IBKR",
                host=self.host,
                port=self.port,
                client_id=self.client_id,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to IBKR", error=str(e))
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from IBKR."""
        if self._connected:
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IBKR")

    def is_connected(self) -> bool:
        """Check if connected to IBKR."""
        return self._connected and self.ib.isConnected()

    def _ensure_connected(self):
        """Ensure we're connected."""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")

    async def execute(self, decision) -> ExecutionResult:
        """Execute a trading decision.

        Args:
            decision: TacticalDecision with trade details

        Returns:
            ExecutionResult with outcome
        """
        self._ensure_connected()

        symbol = decision.symbol
        action = decision.action

        if action == "BUY":
            return await self._execute_entry(
                symbol=symbol,
                side="buy",
                entry_price=decision.entry_price,
                stop_price=decision.stop_price,
                target_price=decision.target_price,
                size_percent=decision.size_percent,
                reason=decision.reasoning,
            )

        elif action == "SELL":
            return await self._execute_entry(
                symbol=symbol,
                side="sell",
                entry_price=decision.entry_price,
                stop_price=decision.stop_price,
                target_price=decision.target_price,
                size_percent=decision.size_percent,
                reason=decision.reasoning,
            )

        elif action == "CLOSE":
            return await self._close_position(
                symbol=symbol,
                reason=decision.reasoning,
            )

        else:
            return ExecutionResult(
                success=False,
                symbol=symbol,
                message=f"Unknown action: {action}",
            )

    async def _execute_entry(
        self,
        symbol: str,
        side: str,
        entry_price: Optional[float],
        stop_price: Optional[float],
        target_price: Optional[float],
        size_percent: Optional[float],
        reason: str,
    ) -> ExecutionResult:
        """Execute entry order."""
        try:
            contract = self._create_contract(symbol)
            self.ib.qualifyContracts(contract)

            # Calculate quantity based on portfolio and size
            portfolio = await self.get_portfolio()
            equity = portfolio.get("equity", 0)

            if equity <= 0 or not entry_price:
                return ExecutionResult(
                    success=False,
                    symbol=symbol,
                    message="Cannot calculate position size",
                )

            size_pct = size_percent or 5  # Default 5%
            position_value = equity * (size_pct / 100)

            # HKEX board lot is 100
            lot_size = 100
            quantity = int(position_value / entry_price / lot_size) * lot_size

            if quantity < lot_size:
                return ExecutionResult(
                    success=False,
                    symbol=symbol,
                    message=f"Position size too small (min {lot_size} shares)",
                )

            # Create order
            action = "BUY" if side.lower() in ["buy", "long"] else "SELL"

            if entry_price:
                entry_price = self._round_to_tick(entry_price)
                order = LimitOrder(action, quantity, entry_price)
            else:
                order = MarketOrder(action, quantity)

            order.tif = "DAY"

            # Submit order
            trade = self.ib.placeOrder(contract, order)
            self.ib.sleep(2)  # Wait for fill

            filled_price = None
            filled_qty = 0

            if trade.orderStatus.status == "Filled":
                filled_price = trade.orderStatus.avgFillPrice
                filled_qty = int(trade.orderStatus.filled)

                # Place bracket orders
                if stop_price:
                    await self._place_stop_order(
                        contract, action, filled_qty, stop_price
                    )
                if target_price:
                    await self._place_target_order(
                        contract, action, filled_qty, target_price
                    )

            return ExecutionResult(
                success=trade.orderStatus.status in ["Filled", "Submitted"],
                order_id=str(trade.order.orderId),
                status=trade.orderStatus.status,
                symbol=symbol,
                side=side,
                quantity=quantity,
                filled_price=filled_price,
                filled_quantity=filled_qty,
                message=f"Order {trade.orderStatus.status}: {reason[:100]}",
                timestamp=datetime.now(HK_TZ).isoformat(),
            )

        except Exception as e:
            logger.error("Execution failed", symbol=symbol, error=str(e))
            return ExecutionResult(
                success=False,
                symbol=symbol,
                message=f"Execution error: {str(e)}",
            )

    async def _close_position(
        self,
        symbol: str,
        reason: str,
    ) -> ExecutionResult:
        """Close an existing position."""
        try:
            # Get current position
            positions = await self._get_positions()
            position = next(
                (p for p in positions if p["symbol"] == symbol.zfill(4)),
                None,
            )

            if not position:
                return ExecutionResult(
                    success=False,
                    symbol=symbol,
                    message=f"No position found for {symbol}",
                )

            contract = self._create_contract(symbol)
            self.ib.qualifyContracts(contract)

            quantity = abs(position["quantity"])
            side = "SELL" if position["quantity"] > 0 else "BUY"

            order = MarketOrder(side, quantity)
            order.tif = "DAY"

            trade = self.ib.placeOrder(contract, order)
            self.ib.sleep(2)

            filled_price = None
            if trade.orderStatus.status == "Filled":
                filled_price = trade.orderStatus.avgFillPrice

            return ExecutionResult(
                success=trade.orderStatus.status == "Filled",
                order_id=str(trade.order.orderId),
                status=trade.orderStatus.status,
                symbol=symbol,
                side=side.lower(),
                quantity=quantity,
                filled_price=filled_price,
                filled_quantity=int(trade.orderStatus.filled),
                message=f"Position closed: {reason[:100]}",
                timestamp=datetime.now(HK_TZ).isoformat(),
            )

        except Exception as e:
            logger.error("Close position failed", symbol=symbol, error=str(e))
            return ExecutionResult(
                success=False,
                symbol=symbol,
                message=f"Close error: {str(e)}",
            )

    async def _place_stop_order(
        self,
        contract: Contract,
        parent_action: str,
        quantity: int,
        stop_price: float,
    ):
        """Place stop loss order."""
        action = "SELL" if parent_action == "BUY" else "BUY"
        stop_price = self._round_to_tick(stop_price)

        order = Order()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = "STP"
        order.auxPrice = stop_price
        order.tif = "GTC"

        self.ib.placeOrder(contract, order)
        logger.info("Stop order placed", stop_price=stop_price)

    async def _place_target_order(
        self,
        contract: Contract,
        parent_action: str,
        quantity: int,
        target_price: float,
    ):
        """Place take profit order."""
        action = "SELL" if parent_action == "BUY" else "BUY"
        target_price = self._round_to_tick(target_price)

        order = LimitOrder(action, quantity, target_price)
        order.tif = "GTC"

        self.ib.placeOrder(contract, order)
        logger.info("Target order placed", target_price=target_price)

    async def get_portfolio(self) -> dict:
        """Get current portfolio status."""
        self._ensure_connected()

        account_values = self.ib.accountValues()

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

        positions = await self._get_positions()

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

    async def _get_positions(self) -> list:
        """Get current positions."""
        self._ensure_connected()

        ib_positions = self.ib.positions()
        positions = []

        for pos in ib_positions:
            if pos.contract.exchange != "SEHK":
                continue

            symbol = pos.contract.symbol
            quantity = int(pos.position)
            avg_cost = pos.avgCost

            positions.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_cost": round(avg_cost, 2),
                "current_price": avg_cost,  # Would need quote for real price
                "unrealized_pnl": 0,
                "unrealized_pnl_pct": 0,
            })

        return positions

    async def close_all_positions(self, reason: str) -> list[ExecutionResult]:
        """Emergency close all positions."""
        logger.warning("EMERGENCY: Closing all positions", reason=reason)

        positions = await self._get_positions()
        results = []

        for pos in positions:
            if pos["quantity"] != 0:
                result = await self._close_position(
                    symbol=pos["symbol"],
                    reason=f"Emergency: {reason}",
                )
                results.append(result)

        return results

    def _create_contract(self, symbol: str) -> Contract:
        """Create HKEX stock contract."""
        symbol = symbol.zfill(4)
        return Stock(symbol, "SEHK", "HKD")

    def _round_to_tick(self, price: float) -> float:
        """Round price to valid HKEX tick size."""
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
