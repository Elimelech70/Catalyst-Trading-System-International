"""
Broker integrations for the Catalyst Trading Agent.

This package provides broker connectivity for:
- Interactive Brokers (IBKR) for HKEX trading
"""

from brokers.ibkr import IBKRClient, get_ibkr_client

__all__ = ["IBKRClient", "get_ibkr_client"]
