"""
Name of Application: Catalyst Trading System
Name of file: ibkr_client.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: IBKR Web API client via IBeam gateway

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- REST API client for IBeam gateway
- Session management with keepalive
- Full trading operations support

Description:
This module provides a REST API client for Interactive Brokers via the IBeam
Docker container. IBeam handles authentication and 2FA automatically.
"""

import os
import time
import requests
from typing import Optional, Dict, Any, List
import urllib3

# Disable SSL warnings for self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IBKRClient:
    """IBKR Web API client via IBeam gateway."""

    def __init__(self, base_url: str = None):
        """Initialize IBKR client.

        Args:
            base_url: IBeam gateway URL (default from env or localhost:5000)
        """
        self.base_url = base_url or os.getenv("IBEAM_URL", "https://localhost:5000")
        self.session = requests.Session()
        self.session.verify = False  # IBeam uses self-signed cert
        self.account_id: Optional[str] = None
        self._conid_cache: Dict[str, int] = {}

    def check_auth_status(self) -> Dict[str, Any]:
        """Check if gateway is authenticated.

        Returns:
            Dict with 'authenticated', 'connected', 'competing' keys
        """
        response = self.session.get(f"{self.base_url}/v1/api/iserver/auth/status")
        return response.json()

    def tickle(self) -> Dict[str, Any]:
        """Keep session alive - call every 5 minutes.

        Returns:
            Session status
        """
        response = self.session.post(f"{self.base_url}/v1/api/tickle")
        return response.json()

    def reauthenticate(self) -> Dict[str, Any]:
        """Force reauthentication.

        Returns:
            Auth status
        """
        response = self.session.post(f"{self.base_url}/v1/api/iserver/reauthenticate")
        return response.json()

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get list of accounts.

        Returns:
            List of account objects with accountId, etc.
        """
        response = self.session.get(f"{self.base_url}/v1/api/portfolio/accounts")
        data = response.json()
        if data and len(data) > 0:
            self.account_id = data[0].get("accountId")
        return data

    def search_contract(self, symbol: str, sec_type: str = "STK") -> List[Dict[str, Any]]:
        """Search for contract by symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL' or '0700' for HKEX)
            sec_type: Security type (STK, OPT, FUT, etc.)

        Returns:
            List of matching contracts
        """
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/secdef/search",
            params={"symbol": symbol, "secType": sec_type}
        )
        return response.json()

    def get_conid(self, symbol: str, exchange: str = "SEHK") -> Optional[int]:
        """Get contract ID for a symbol.

        Args:
            symbol: Stock symbol
            exchange: Exchange code (SEHK for HKEX, SMART for US)

        Returns:
            Contract ID or None
        """
        cache_key = f"{symbol}:{exchange}"
        if cache_key in self._conid_cache:
            return self._conid_cache[cache_key]

        results = self.search_contract(symbol)
        for contract in results:
            # Match by exchange
            if exchange in str(contract.get("description", "")):
                conid = contract.get("conid")
                self._conid_cache[cache_key] = conid
                return conid

        # Return first result if no exchange match
        if results:
            conid = results[0].get("conid")
            self._conid_cache[cache_key] = conid
            return conid

        return None

    def get_contract_details(self, conid: int) -> Dict[str, Any]:
        """Get contract details by conid.

        Args:
            conid: Contract ID

        Returns:
            Contract details
        """
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/contract/{conid}/info"
        )
        return response.json()

    def get_market_data(self, conids: List[int], fields: List[str] = None) -> List[Dict[str, Any]]:
        """Get market data snapshot.

        Args:
            conids: List of contract IDs
            fields: Field codes (default: last, bid, ask)
                31 = Last Price
                84 = Bid Price
                86 = Ask Price
                87 = Volume
                88 = High
                89 = Low

        Returns:
            List of market data snapshots
        """
        if fields is None:
            fields = ["31", "84", "86", "87", "88", "89"]

        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/marketdata/snapshot",
            params={
                "conids": ",".join(map(str, conids)),
                "fields": ",".join(fields)
            }
        )
        return response.json()

    def get_historical_data(
        self,
        conid: int,
        period: str = "1d",
        bar: str = "1min",
        outside_rth: bool = False
    ) -> Dict[str, Any]:
        """Get historical market data.

        Args:
            conid: Contract ID
            period: Time period (1d, 1w, 1m, 1y)
            bar: Bar size (1min, 5min, 15min, 1h, 1d)
            outside_rth: Include outside regular trading hours

        Returns:
            Historical data with bars
        """
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/marketdata/history",
            params={
                "conid": conid,
                "period": period,
                "bar": bar,
                "outsideRth": str(outside_rth).lower()
            }
        )
        return response.json()

    def place_order(
        self,
        conid: int,
        side: str,
        quantity: float,
        order_type: str = "MKT",
        price: float = None,
        tif: str = "DAY"
    ) -> List[Dict[str, Any]]:
        """Place an order.

        Args:
            conid: Contract ID
            side: BUY or SELL
            quantity: Number of shares/contracts
            order_type: MKT, LMT, STP, STP_LIMIT
            price: Limit price (required for LMT, STP)
            tif: Time in force (DAY, GTC, IOC, OPG)

        Returns:
            Order response (may require confirmation)
        """
        if not self.account_id:
            self.get_accounts()

        order = {
            "conid": conid,
            "side": side.upper(),
            "quantity": quantity,
            "orderType": order_type,
            "tif": tif,
        }

        if price and order_type in ["LMT", "STP", "STP_LIMIT"]:
            order["price"] = price

        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/orders",
            json={"orders": [order]}
        )
        return response.json()

    def confirm_order(self, reply_id: str, confirmed: bool = True) -> Dict[str, Any]:
        """Confirm order after placement (handles order warnings).

        Args:
            reply_id: Reply ID from place_order response
            confirmed: Whether to confirm (True) or reject (False)

        Returns:
            Order confirmation result
        """
        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/reply/{reply_id}",
            json={"confirmed": confirmed}
        )
        return response.json()

    def place_bracket_order(
        self,
        conid: int,
        side: str,
        quantity: float,
        entry_price: float = None,
        stop_price: float = None,
        target_price: float = None,
        tif: str = "DAY"
    ) -> List[Dict[str, Any]]:
        """Place a bracket order (entry + stop + target).

        Args:
            conid: Contract ID
            side: BUY or SELL
            quantity: Number of shares
            entry_price: Entry limit price (None for market)
            stop_price: Stop loss price
            target_price: Take profit price
            tif: Time in force

        Returns:
            Order responses
        """
        if not self.account_id:
            self.get_accounts()

        orders = []

        # Parent order (entry)
        parent = {
            "conid": conid,
            "side": side.upper(),
            "quantity": quantity,
            "orderType": "LMT" if entry_price else "MKT",
            "tif": tif,
        }
        if entry_price:
            parent["price"] = entry_price
        orders.append(parent)

        # Child orders (attached to parent)
        exit_side = "SELL" if side.upper() == "BUY" else "BUY"

        if stop_price:
            stop_order = {
                "conid": conid,
                "side": exit_side,
                "quantity": quantity,
                "orderType": "STP",
                "price": stop_price,
                "tif": "GTC",
                "parentId": "0",  # Attached to parent
            }
            orders.append(stop_order)

        if target_price:
            target_order = {
                "conid": conid,
                "side": exit_side,
                "quantity": quantity,
                "orderType": "LMT",
                "price": target_price,
                "tif": "GTC",
                "parentId": "0",
            }
            orders.append(target_order)

        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/orders",
            json={"orders": orders}
        )
        return response.json()

    def get_orders(self) -> Dict[str, Any]:
        """Get live orders.

        Returns:
            Dict with 'orders' list
        """
        response = self.session.get(f"{self.base_url}/v1/api/iserver/account/orders")
        return response.json()

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order.

        Args:
            order_id: Order ID

        Returns:
            Order status
        """
        response = self.session.get(
            f"{self.base_url}/v1/api/iserver/account/order/status/{order_id}"
        )
        return response.json()

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation result
        """
        if not self.account_id:
            self.get_accounts()

        response = self.session.delete(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/order/{order_id}"
        )
        return response.json()

    def modify_order(
        self,
        order_id: str,
        conid: int,
        quantity: float = None,
        price: float = None
    ) -> Dict[str, Any]:
        """Modify an existing order.

        Args:
            order_id: Order ID to modify
            conid: Contract ID
            quantity: New quantity (optional)
            price: New price (optional)

        Returns:
            Modification result
        """
        if not self.account_id:
            self.get_accounts()

        payload = {"conid": conid}
        if quantity:
            payload["quantity"] = quantity
        if price:
            payload["price"] = price

        response = self.session.post(
            f"{self.base_url}/v1/api/iserver/account/{self.account_id}/order/{order_id}",
            json=payload
        )
        return response.json()

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions.

        Returns:
            List of position objects
        """
        if not self.account_id:
            self.get_accounts()

        response = self.session.get(
            f"{self.base_url}/v1/api/portfolio/{self.account_id}/positions/0"
        )
        return response.json()

    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary.

        Returns:
            Account summary with balances, P&L, etc.
        """
        if not self.account_id:
            self.get_accounts()

        response = self.session.get(
            f"{self.base_url}/v1/api/portfolio/{self.account_id}/summary"
        )
        return response.json()

    def get_account_ledger(self) -> Dict[str, Any]:
        """Get account ledger (detailed balances by currency).

        Returns:
            Ledger data
        """
        if not self.account_id:
            self.get_accounts()

        response = self.session.get(
            f"{self.base_url}/v1/api/portfolio/{self.account_id}/ledger"
        )
        return response.json()


class IBKRSessionManager:
    """Manages IBKR session keepalive."""

    def __init__(self, client: IBKRClient, tickle_interval: int = 240):
        """Initialize session manager.

        Args:
            client: IBKRClient instance
            tickle_interval: Seconds between keepalive calls (< 300)
        """
        self.client = client
        self.tickle_interval = tickle_interval
        self.running = False
        self.thread = None

    def start(self):
        """Start session keepalive loop."""
        import threading
        self.running = True
        self.thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop session keepalive."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _keepalive_loop(self):
        """Background keepalive loop."""
        while self.running:
            try:
                status = self.client.check_auth_status()
                if status.get("authenticated"):
                    self.client.tickle()
                    print(f"[{time.strftime('%H:%M:%S')}] IBKR session keepalive OK")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] WARNING: IBKR session not authenticated")
                    # Try to reauthenticate
                    self.client.reauthenticate()
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Keepalive error: {e}")

            time.sleep(self.tickle_interval)


# Async wrapper for use with asyncio
class AsyncIBKRClient:
    """Async wrapper for IBKRClient."""

    def __init__(self, base_url: str = None):
        self._sync_client = IBKRClient(base_url)

    async def check_auth_status(self) -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(self._sync_client.check_auth_status)

    async def get_accounts(self) -> List[Dict[str, Any]]:
        import asyncio
        return await asyncio.to_thread(self._sync_client.get_accounts)

    async def get_positions(self) -> List[Dict[str, Any]]:
        import asyncio
        return await asyncio.to_thread(self._sync_client.get_positions)

    async def get_account_summary(self) -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(self._sync_client.get_account_summary)

    async def place_order(self, **kwargs) -> List[Dict[str, Any]]:
        import asyncio
        return await asyncio.to_thread(lambda: self._sync_client.place_order(**kwargs))

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(self._sync_client.cancel_order, order_id)

    async def get_market_data(self, conids: List[int], fields: List[str] = None) -> List[Dict[str, Any]]:
        import asyncio
        return await asyncio.to_thread(self._sync_client.get_market_data, conids, fields)

    @property
    def account_id(self) -> Optional[str]:
        return self._sync_client.account_id
