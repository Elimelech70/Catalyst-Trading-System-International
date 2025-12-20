"""
Broker integrations for the Catalyst Trading Agent.

This package provides broker connectivity for:
- Moomoo/Futu for HKEX trading via OpenD gateway
"""

from brokers.futu import FutuClient, get_futu_client, init_futu_client

__all__ = ["FutuClient", "get_futu_client", "init_futu_client"]
