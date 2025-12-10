#!/usr/bin/env python3
"""
Test IBGA/IB Gateway connection using ib_async.

Run this after starting the IBGA Docker container and approving IB Key.

Usage:
    source venv/bin/activate
    python scripts/test_ibga_connection.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ib_async import IB, Stock


def test_connection():
    """Test basic connection to IB Gateway."""
    print("=" * 60)
    print("IBGA Connection Test")
    print("=" * 60)

    ib = IB()

    host = os.environ.get("IBKR_HOST", "127.0.0.1")
    port = int(os.environ.get("IBKR_PORT", "4001"))
    client_id = int(os.environ.get("IBKR_CLIENT_ID", "99"))  # Use 99 for testing

    print(f"\n1. Connecting to {host}:{port} (client {client_id})...")

    try:
        ib.connect(host, port, clientId=client_id, timeout=30)
        print("   ✓ Connected successfully!")
    except ConnectionRefusedError:
        print("   ✗ Connection refused - is IBGA running?")
        print("     Run: cd ibga && docker compose up -d")
        return False
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return False

    # Test account info
    print("\n2. Getting account info...")
    try:
        accounts = ib.managedAccounts()
        print(f"   ✓ Accounts: {accounts}")
    except Exception as e:
        print(f"   ✗ Failed to get accounts: {e}")

    # Test portfolio
    print("\n3. Getting portfolio summary...")
    try:
        account_values = ib.accountValues()

        # Find key values
        for av in account_values:
            if av.tag in ["NetLiquidation", "CashBalance", "TotalCashValue"]:
                print(f"   {av.tag}: {av.value} {av.currency}")
    except Exception as e:
        print(f"   ✗ Failed to get portfolio: {e}")

    # Test market data (Tencent - 0700.HK)
    print("\n4. Testing market data (Tencent 0700.HK)...")
    try:
        contract = Stock("0700", "SEHK", "HKD")
        ib.qualifyContracts(contract)

        ticker = ib.reqMktData(contract, "", False, False)
        ib.sleep(2)  # Wait for data

        if ticker.last:
            print(f"   ✓ Last price: {ticker.last} HKD")
        elif ticker.close:
            print(f"   ✓ Close price: {ticker.close} HKD (market may be closed)")
        else:
            print("   ⚠ No price data (market may be closed or no subscription)")

        ib.cancelMktData(contract)
    except Exception as e:
        print(f"   ✗ Market data failed: {e}")

    # Test positions
    print("\n5. Getting positions...")
    try:
        positions = ib.positions()
        if positions:
            for pos in positions:
                print(f"   {pos.contract.symbol}: {pos.position} @ {pos.avgCost}")
        else:
            print("   (No open positions)")
    except Exception as e:
        print(f"   ✗ Failed to get positions: {e}")

    # Disconnect
    print("\n6. Disconnecting...")
    ib.disconnect()
    print("   ✓ Disconnected")

    print("\n" + "=" * 60)
    print("Connection test completed successfully!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
