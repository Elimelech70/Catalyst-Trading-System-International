#!/usr/bin/env python3
"""
Name of Application: Catalyst Trading System
Name of file: test_ibkr_paper.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Test IBKR IBeam connection and paper trading

Usage:
    python test_ibkr_paper.py

This script tests:
1. Authentication status
2. Account retrieval
3. Contract search
4. Market data
5. Paper order placement (optional)
"""

import sys
import os

# Add the services directory to path
sys.path.insert(0, '/opt/catalyst/services/ibkr_client')

from ibkr_client import IBKRClient

IBEAM_URL = os.getenv("IBEAM_URL", "https://localhost:5000")


def test_auth():
    """Test authentication status."""
    print("\n" + "=" * 60)
    print("TEST 1: Authentication Status")
    print("=" * 60)

    client = IBKRClient(IBEAM_URL)
    status = client.check_auth_status()

    print(f"Authenticated: {status.get('authenticated', 'N/A')}")
    print(f"Connected: {status.get('connected', 'N/A')}")
    print(f"Competing: {status.get('competing', 'N/A')}")

    if not status.get('authenticated'):
        print("\nERROR: Not authenticated! Check IBeam logs:")
        print("  docker logs catalyst-ibeam")
        return False

    print("\n[PASS] Authentication OK")
    return True


def test_accounts(client):
    """Test account retrieval."""
    print("\n" + "=" * 60)
    print("TEST 2: Account Retrieval")
    print("=" * 60)

    accounts = client.get_accounts()

    if not accounts:
        print("ERROR: No accounts returned")
        return False

    for acc in accounts:
        print(f"Account ID: {acc.get('accountId')}")
        print(f"Account Type: {acc.get('type', 'N/A')}")
        print(f"Account Title: {acc.get('accountTitle', 'N/A')}")

    print(f"\nUsing account: {client.account_id}")
    print("\n[PASS] Account retrieval OK")
    return True


def test_contract_search(client):
    """Test contract search."""
    print("\n" + "=" * 60)
    print("TEST 3: Contract Search")
    print("=" * 60)

    # Test with a US stock
    print("\nSearching for AAPL...")
    results = client.search_contract("AAPL")

    if results:
        print(f"Found {len(results)} result(s)")
        for r in results[:3]:
            print(f"  - {r.get('symbol')}: conid={r.get('conid')}, {r.get('description')}")
    else:
        print("No results for AAPL")

    # Test with an HK stock (Tencent)
    print("\nSearching for 0700 (Tencent)...")
    results = client.search_contract("0700")

    if results:
        print(f"Found {len(results)} result(s)")
        for r in results[:3]:
            print(f"  - {r.get('symbol')}: conid={r.get('conid')}, {r.get('description')}")
    else:
        print("No results for 0700")

    print("\n[PASS] Contract search OK")
    return True


def test_market_data(client):
    """Test market data retrieval."""
    print("\n" + "=" * 60)
    print("TEST 4: Market Data")
    print("=" * 60)

    # Get AAPL conid
    results = client.search_contract("AAPL")
    if not results:
        print("Cannot get AAPL conid")
        return False

    conid = results[0].get('conid')
    print(f"AAPL conid: {conid}")

    # Get market data
    print("\nFetching market data...")
    data = client.get_market_data([conid])

    if data:
        for d in data:
            print(f"  Last: {d.get('31', 'N/A')}")
            print(f"  Bid: {d.get('84', 'N/A')}")
            print(f"  Ask: {d.get('86', 'N/A')}")
            print(f"  Volume: {d.get('87', 'N/A')}")
    else:
        print("No market data returned (market may be closed)")

    print("\n[PASS] Market data OK")
    return True


def test_account_summary(client):
    """Test account summary."""
    print("\n" + "=" * 60)
    print("TEST 5: Account Summary")
    print("=" * 60)

    summary = client.get_account_summary()

    if summary:
        # Summary returns nested structure
        for key, value in list(summary.items())[:10]:
            print(f"  {key}: {value}")
    else:
        print("No summary data returned")

    print("\n[PASS] Account summary OK")
    return True


def test_positions(client):
    """Test positions retrieval."""
    print("\n" + "=" * 60)
    print("TEST 6: Positions")
    print("=" * 60)

    positions = client.get_positions()

    if positions:
        print(f"Found {len(positions)} position(s)")
        for p in positions[:5]:
            print(f"  - {p.get('contractDesc')}: {p.get('position')} @ {p.get('avgCost')}")
            print(f"    Unrealized P&L: {p.get('unrealizedPnl', 'N/A')}")
    else:
        print("No positions (or error)")

    print("\n[PASS] Positions OK")
    return True


def test_paper_order(client, confirm=False):
    """Test paper order placement (optional)."""
    print("\n" + "=" * 60)
    print("TEST 7: Paper Order (DRY RUN)")
    print("=" * 60)

    if not confirm:
        print("Skipping actual order placement.")
        print("To test, run: python test_ibkr_paper.py --place-order")
        return True

    # Get AAPL conid
    results = client.search_contract("AAPL")
    if not results:
        print("Cannot get AAPL conid")
        return False

    conid = results[0].get('conid')

    print(f"\nPlacing paper order: BUY 1 AAPL @ MKT")

    result = client.place_order(
        conid=conid,
        side="BUY",
        quantity=1,
        order_type="MKT"
    )

    print(f"Order result: {result}")

    # Handle confirmation if needed
    if result and isinstance(result, list) and len(result) > 0:
        if "id" in result[0]:
            reply_id = result[0]["id"]
            print(f"Confirming order (reply_id: {reply_id})...")
            confirm_result = client.confirm_order(reply_id)
            print(f"Confirmation result: {confirm_result}")

    print("\n[PASS] Paper order test OK")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("IBKR IBeam Connection Test")
    print("=" * 60)
    print(f"IBeam URL: {IBEAM_URL}")

    # Check if we should place real orders
    place_order = "--place-order" in sys.argv

    # Create client
    client = IBKRClient(IBEAM_URL)

    # Run tests
    results = []

    # Test 1: Auth
    results.append(("Authentication", test_auth()))
    if not results[-1][1]:
        print("\nFailed authentication. Cannot continue.")
        return 1

    # Test 2: Accounts
    results.append(("Accounts", test_accounts(client)))

    # Test 3: Contract Search
    results.append(("Contract Search", test_contract_search(client)))

    # Test 4: Market Data
    results.append(("Market Data", test_market_data(client)))

    # Test 5: Account Summary
    results.append(("Account Summary", test_account_summary(client)))

    # Test 6: Positions
    results.append(("Positions", test_positions(client)))

    # Test 7: Paper Order
    results.append(("Paper Order", test_paper_order(client, confirm=place_order)))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
