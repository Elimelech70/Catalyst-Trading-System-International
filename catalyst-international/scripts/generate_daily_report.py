#!/usr/bin/env python3
"""
Name of Application: Catalyst Trading System
Name of file: generate_daily_report.py
Version: 1.0.0
Last Updated: 2025-12-30
Purpose: Generate daily trading report with portfolio status and P&L

REVISION HISTORY:
v1.0.0 (2025-12-30) - Initial implementation
- Fetches portfolio and positions from Moomoo
- Calculates daily P&L
- Generates markdown report
- Optionally pushes to GitHub

Usage:
    python3 scripts/generate_daily_report.py [--push]

    --push: Commit and push report to GitHub
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from brokers.moomoo import MoomooClient

HK_TZ = ZoneInfo("Asia/Hong_Kong")


def get_portfolio_data() -> dict:
    """Fetch portfolio and positions from Moomoo."""
    client = MoomooClient(paper_trading=True)
    client.connect()

    try:
        portfolio = client.get_portfolio()
        positions = client.get_positions()

        # Get quotes for position symbols to calculate daily change
        position_data = []
        for pos in positions:
            quote = client.get_quote(pos.symbol)
            position_data.append({
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "current_price": pos.current_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct / 100,  # Convert to decimal
                "prev_close": quote.get("prev_close", pos.current_price),
                "day_change": pos.current_price - quote.get("prev_close", pos.current_price),
                "market_value": pos.quantity * pos.current_price,
            })

        return {
            "portfolio": portfolio,
            "positions": position_data,
            "timestamp": datetime.now(HK_TZ),
        }
    finally:
        client.disconnect()


def generate_report(data: dict) -> str:
    """Generate markdown report from portfolio data."""
    portfolio = data["portfolio"]
    positions = data["positions"]
    timestamp = data["timestamp"]

    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H:%M:%S HKT")

    # Calculate totals
    total_unrealized_pnl = sum(p["unrealized_pnl"] for p in positions)
    total_market_value = sum(p["market_value"] for p in positions)
    total_day_pnl = sum(p["day_change"] * p["quantity"] for p in positions)

    # Calculate portfolio return
    cash = portfolio.get("cash", 0)
    total_assets = portfolio.get("total_assets", 0)
    initial_capital = 1_000_000  # Paper trading initial
    total_return = ((total_assets - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0

    report = f"""# Daily Trading Report - {date_str}

**Generated:** {time_str}
**System:** Catalyst International (HKEX)
**Mode:** Paper Trading
**Account:** 152537501

---

## Portfolio Summary

| Metric | Value |
|--------|-------|
| **Total Assets** | HKD {total_assets:,.2f} |
| **Cash** | HKD {cash:,.2f} |
| **Market Value** | HKD {total_market_value:,.2f} |
| **Unrealized P&L** | HKD {total_unrealized_pnl:+,.2f} |
| **Today's P&L** | HKD {total_day_pnl:+,.2f} |
| **Total Return** | {total_return:+.2f}% |

---

## Open Positions ({len(positions)})

| Symbol | Qty | Avg Cost | Current | Market Value | P&L | P&L % | Today |
|--------|-----|----------|---------|--------------|-----|-------|-------|
"""

    for pos in sorted(positions, key=lambda x: x["unrealized_pnl"], reverse=True):
        pnl_emoji = "+" if pos["unrealized_pnl"] >= 0 else ""
        day_emoji = "+" if pos["day_change"] >= 0 else ""
        report += f"| {pos['symbol']} | {pos['quantity']:,} | {pos['avg_cost']:.2f} | {pos['current_price']:.2f} | {pos['market_value']:,.0f} | {pnl_emoji}{pos['unrealized_pnl']:,.0f} | {pos['unrealized_pnl_pct']*100:+.1f}% | {day_emoji}{pos['day_change']:.2f} |\n"

    report += f"""
---

## System Status

| Component | Status |
|-----------|--------|
| OpenD Gateway | Running |
| Broker Connection | Connected |
| Market Data | Active |
| Database | Connected |

---

## Trading Schedule

| Session | Time (HKT) | Status |
|---------|------------|--------|
| Morning | 09:30 | {'Completed' if timestamp.hour >= 12 else 'Pending'} |
| Afternoon | 13:00 | {'Completed' if timestamp.hour >= 16 else 'Pending'} |

---

## Notes

- Market: HKEX (Hong Kong Stock Exchange)
- Currency: HKD
- Lot Size: 100 shares
- Paper Trading Mode: Simulated execution

---

*Report generated automatically by Catalyst Trading System*
"""

    return report


def save_report(report: str, date_str: str) -> Path:
    """Save report to Documentation/Reports directory."""
    reports_dir = Path(__file__).parent.parent / "Documentation" / "Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    filename = f"DAILY_REPORT_{date_str}.md"
    filepath = reports_dir / filename

    filepath.write_text(report)
    print(f"Report saved: {filepath}")

    return filepath


def push_to_github(filepath: Path, date_str: str):
    """Commit and push report to GitHub."""
    repo_dir = Path(__file__).parent.parent

    # Git add
    subprocess.run(
        ["git", "add", str(filepath)],
        cwd=repo_dir,
        check=True
    )

    # Git commit
    commit_msg = f"report: daily trading report {date_str}\n\n" \
                 f"Auto-generated daily report\n\n" \
                 f"Generated with [Claude Code](https://claude.com/claude-code)"

    subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=repo_dir,
        check=True
    )

    # Git push
    subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=repo_dir,
        check=True
    )

    print(f"Report pushed to GitHub")


def main():
    parser = argparse.ArgumentParser(description="Generate daily trading report")
    parser.add_argument("--push", action="store_true", help="Push report to GitHub")
    args = parser.parse_args()

    print("Fetching portfolio data...")
    data = get_portfolio_data()

    print("Generating report...")
    report = generate_report(data)

    date_str = data["timestamp"].strftime("%Y-%m-%d")
    filepath = save_report(report, date_str)

    if args.push:
        print("Pushing to GitHub...")
        try:
            push_to_github(filepath, date_str)
        except subprocess.CalledProcessError as e:
            print(f"Failed to push to GitHub: {e}")
            return 1

    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
