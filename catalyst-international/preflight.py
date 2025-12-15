"""
Name of Application: Catalyst Trading System
Name of file: preflight.py
Version: 1.0.0
Last Updated: 2025-12-15
Purpose: Pre-flight checks before agent runs

REVISION HISTORY:
v1.0.0 (2025-12-15) - Initial implementation
- IBGA status verification from status file
- Staleness check (status must be < 10 minutes old)
- Market hours verification
- Blocking gate that prevents agent from running if not ready

Description:
This module provides pre-flight checks that agent.py calls before
starting a trading cycle. If checks fail, the agent aborts with
an appropriate error/alert rather than wasting API tokens on a
cycle that can't execute trades.

Usage:
    from preflight import run_preflight_checks

    success, message = run_preflight_checks()
    if not success:
        logger.error(f"Pre-flight failed: {message}")
        sys.exit(1)
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

STATUS_FILE = "/tmp/ibga-status.json"
MAX_STATUS_AGE_MINUTES = 10  # Status must be fresher than this
HK_TZ = ZoneInfo("Asia/Hong_Kong")

ALERT_EMAIL = "craigjcolley@gmail.com"


def send_alert(subject: str, body: str):
    """Send email alert."""
    try:
        process = subprocess.run(
            ["mail", "-s", subject, ALERT_EMAIL],
            input=body.encode(),
            capture_output=True,
            timeout=30
        )
        if process.returncode == 0:
            logger.info(f"Alert sent: {subject}")
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


def check_ibga_status() -> tuple[bool, str]:
    """
    Check IBGA status from status file.

    Returns:
        (success, message) tuple
    """
    # Check if status file exists
    if not Path(STATUS_FILE).exists():
        return False, f"Status file not found: {STATUS_FILE}. Run ibga_status_checker.py first."

    # Read status file
    try:
        with open(STATUS_FILE) as f:
            status = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Status file corrupt: {e}"
    except Exception as e:
        return False, f"Failed to read status file: {e}"

    # Check timestamp (status must be fresh)
    timestamp_str = status.get("timestamp")
    if not timestamp_str:
        return False, "Status file missing timestamp"

    try:
        # Parse ISO format timestamp
        status_time = datetime.fromisoformat(timestamp_str)
        now = datetime.now()

        # Make both timezone-naive for comparison if needed
        if status_time.tzinfo is not None:
            status_time = status_time.replace(tzinfo=None)

        age = now - status_time
        age_minutes = age.total_seconds() / 60

        if age_minutes > MAX_STATUS_AGE_MINUTES:
            return False, f"Status is stale ({age_minutes:.1f} minutes old, max {MAX_STATUS_AGE_MINUTES}). Run ibga_status_checker.py."

    except Exception as e:
        return False, f"Failed to parse status timestamp: {e}"

    # Check ready_to_trade flag
    if not status.get("ready_to_trade", False):
        error = status.get("error", "Unknown error")
        ibga_status = status.get("status", "unknown")
        return False, f"IBGA not ready: {ibga_status} - {error}"

    # Check authenticated
    if not status.get("authenticated", False):
        return False, "IBGA not authenticated. Check IB Key approval."

    # All checks passed
    accounts = status.get("accounts", [])
    return True, f"IBGA ready. Accounts: {accounts}"


def check_market_hours() -> tuple[bool, str]:
    """
    Check if within HKEX market hours.

    Returns:
        (success, message) tuple
    """
    now = datetime.now(HK_TZ)

    # HKEX hours (HK time)
    # Morning: 09:30 - 12:00
    # Afternoon: 13:00 - 16:00

    hour = now.hour
    minute = now.minute
    time_decimal = hour + minute / 60

    # Weekend check
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False, f"Weekend - market closed (day={now.strftime('%A')})"

    # Morning session: 09:30 - 12:00
    if 9.5 <= time_decimal < 12:
        return True, f"Morning session ({now.strftime('%H:%M')} HKT)"

    # Lunch break: 12:00 - 13:00
    if 12 <= time_decimal < 13:
        return False, f"Lunch break ({now.strftime('%H:%M')} HKT) - no trading"

    # Afternoon session: 13:00 - 16:00
    if 13 <= time_decimal < 16:
        return True, f"Afternoon session ({now.strftime('%H:%M')} HKT)"

    # Outside hours
    return False, f"Outside market hours ({now.strftime('%H:%M')} HKT)"


def run_preflight_checks(skip_market_hours: bool = False) -> tuple[bool, str]:
    """
    Run all pre-flight checks.

    Args:
        skip_market_hours: If True, skip market hours check (for testing)

    Returns:
        (success, message) tuple. If success is False, agent should not run.
    """
    logger.info("=" * 50)
    logger.info("PRE-FLIGHT CHECKS")
    logger.info("=" * 50)

    checks_passed = []
    checks_failed = []

    # Check 1: IBGA Status
    ibga_ok, ibga_msg = check_ibga_status()
    if ibga_ok:
        logger.info(f"[PASS] IBGA: {ibga_msg}")
        checks_passed.append(("IBGA", ibga_msg))
    else:
        logger.error(f"[FAIL] IBGA: {ibga_msg}")
        checks_failed.append(("IBGA", ibga_msg))

    # Check 2: Market Hours (optional)
    if not skip_market_hours:
        market_ok, market_msg = check_market_hours()
        if market_ok:
            logger.info(f"[PASS] Market: {market_msg}")
            checks_passed.append(("Market", market_msg))
        else:
            logger.warning(f"[SKIP] Market: {market_msg}")
            # Market hours is a warning, not a blocker
            # Agent can still run for position management

    # Summary
    if checks_failed:
        failure_summary = "; ".join([f"{name}: {msg}" for name, msg in checks_failed])
        logger.error(f"PRE-FLIGHT FAILED: {failure_summary}")

        # Send alert for IBGA failures
        for name, msg in checks_failed:
            if name == "IBGA":
                send_alert(
                    "AGENT PRE-FLIGHT FAILED",
                    f"Agent cannot start - IBGA not ready.\n\n"
                    f"Reason: {msg}\n\n"
                    f"Action: Run ibga_status_checker.py or check IBGA container.\n\n"
                    f"Time: {datetime.now()}"
                )

        return False, failure_summary

    logger.info("PRE-FLIGHT PASSED - Agent cleared for trading")
    return True, "All checks passed"


def refresh_ibga_status() -> tuple[bool, str]:
    """
    Run the status checker to get fresh status.

    Returns:
        (success, message) tuple
    """
    checker_path = Path(__file__).parent / "scripts" / "ibga_status_checker.py"

    if not checker_path.exists():
        return False, f"Status checker not found: {checker_path}"

    try:
        # Run the status checker
        result = subprocess.run(
            ["python3", str(checker_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).parent)
        )

        if result.returncode == 0:
            return True, "Status refreshed - IBGA ready"
        else:
            return False, f"Status check failed: {result.stdout} {result.stderr}"

    except subprocess.TimeoutExpired:
        return False, "Status check timed out"
    except Exception as e:
        return False, f"Failed to run status checker: {e}"


if __name__ == "__main__":
    # Test the preflight checks
    logging.basicConfig(level=logging.INFO)

    print("\nRunning preflight checks...\n")
    success, message = run_preflight_checks(skip_market_hours=True)

    print(f"\nResult: {'PASS' if success else 'FAIL'}")
    print(f"Message: {message}")
