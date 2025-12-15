#!/usr/bin/env python3
"""
Name of Application: Catalyst Trading System
Name of file: ibga_status_checker.py
Version: 1.0.0
Last Updated: 2025-12-15
Purpose: Real socket-based IBGA status checker

REVISION HISTORY:
v1.0.0 (2025-12-15) - Initial implementation
- Real ib_async connection test (not log parsing)
- Writes JSON status file for agent.py to check
- Sends email alerts when status changes
- Called by cron before agent runs

Description:
This script performs an actual connection test to IBGA using ib_async,
verifying that the gateway is authenticated and ready for trading.
It writes status to /tmp/ibga-status.json which agent.py checks
before starting a trading cycle.

Usage:
    python3 scripts/ibga_status_checker.py

Exit codes:
    0 = IBGA ready for trading
    1 = IBGA not ready (check status file for details)
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

STATUS_FILE = "/tmp/ibga-status.json"
LOG_FILE = "/var/log/catalyst/ibga-status.log"
ALERT_EMAIL = "craigjcolley@gmail.com"

# Status constants
STATUS_READY = "ready"
STATUS_NOT_CONNECTED = "not_connected"
STATUS_NOT_AUTHENTICATED = "not_authenticated"
STATUS_CONTAINER_DOWN = "container_down"
STATUS_ERROR = "error"


def log(message: str):
    """Log message to file and stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} - {message}"
    print(line)

    # Ensure log directory exists
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


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
            log(f"Alert sent: {subject}")
        else:
            log(f"Alert failed: {process.stderr.decode()}")
    except Exception as e:
        log(f"Alert error: {e}")


def check_container() -> bool:
    """Check if IBGA container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return "catalyst-ibga" in result.stdout
    except Exception as e:
        log(f"Container check error: {e}")
        return False


def check_port() -> bool:
    """Check if port 4000 is open."""
    try:
        result = subprocess.run(
            ["nc", "-z", "localhost", "4000"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        log(f"Port check error: {e}")
        return False


def check_connection() -> dict:
    """
    Perform real connection test using ib_async.

    Returns:
        dict with status, accounts, error
    """
    try:
        from ib_async import IB

        ib = IB()
        host = os.environ.get("IBKR_HOST", "127.0.0.1")
        port = int(os.environ.get("IBKR_PORT", "4000"))
        client_id = 99  # Use dedicated client ID for status checks

        log(f"Connecting to {host}:{port} (client {client_id})...")

        try:
            ib.connect(host, port, clientId=client_id, timeout=15)
        except ConnectionRefusedError:
            return {
                "connected": False,
                "authenticated": False,
                "accounts": [],
                "error": "Connection refused - IBGA not listening"
            }
        except Exception as e:
            return {
                "connected": False,
                "authenticated": False,
                "accounts": [],
                "error": f"Connection failed: {str(e)}"
            }

        # Connection succeeded, check authentication
        try:
            accounts = ib.managedAccounts()

            if accounts:
                log(f"Authenticated - accounts: {accounts}")
                result = {
                    "connected": True,
                    "authenticated": True,
                    "accounts": list(accounts),
                    "error": None
                }
            else:
                log("Connected but no accounts - not authenticated")
                result = {
                    "connected": True,
                    "authenticated": False,
                    "accounts": [],
                    "error": "No accounts returned - not authenticated"
                }
        except Exception as e:
            result = {
                "connected": True,
                "authenticated": False,
                "accounts": [],
                "error": f"Account check failed: {str(e)}"
            }

        # Disconnect
        ib.disconnect()
        return result

    except ImportError:
        return {
            "connected": False,
            "authenticated": False,
            "accounts": [],
            "error": "ib_async not installed"
        }
    except Exception as e:
        return {
            "connected": False,
            "authenticated": False,
            "accounts": [],
            "error": f"Unexpected error: {str(e)}"
        }


def get_previous_status() -> dict:
    """Read previous status from file."""
    try:
        if Path(STATUS_FILE).exists():
            with open(STATUS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def write_status(status: dict):
    """Write status to JSON file."""
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)
    log(f"Status written: {status['status']}")


def main():
    """Main status check routine."""
    log("=" * 50)
    log("IBGA Status Check Starting")
    log("=" * 50)

    previous = get_previous_status()
    previous_status = previous.get("status", "unknown")

    # Check 1: Container
    container_running = check_container()
    log(f"Container: {'running' if container_running else 'stopped'}")

    if not container_running:
        status = {
            "status": STATUS_CONTAINER_DOWN,
            "ready_to_trade": False,
            "container": "stopped",
            "port": "unknown",
            "connected": False,
            "authenticated": False,
            "accounts": [],
            "error": "IBGA container not running",
            "timestamp": datetime.now().isoformat(),
            "check_type": "socket"
        }
        write_status(status)

        # Alert if status changed
        if previous_status != STATUS_CONTAINER_DOWN:
            send_alert(
                "IBGA CONTAINER DOWN",
                f"IBGA container is not running.\n\n"
                f"Start with: cd /root/Catalyst-Trading-System-International/catalyst-international/ibga && docker compose up -d\n\n"
                f"Time: {datetime.now()}"
            )

        return 1

    # Check 2: Port
    port_open = check_port()
    log(f"Port 4000: {'open' if port_open else 'closed'}")

    if not port_open:
        status = {
            "status": STATUS_NOT_CONNECTED,
            "ready_to_trade": False,
            "container": "running",
            "port": "closed",
            "connected": False,
            "authenticated": False,
            "accounts": [],
            "error": "Port 4000 not responding",
            "timestamp": datetime.now().isoformat(),
            "check_type": "socket"
        }
        write_status(status)

        if previous_status not in [STATUS_NOT_CONNECTED, STATUS_CONTAINER_DOWN]:
            send_alert(
                "IBGA PORT CLOSED",
                f"IBGA container running but port 4000 not responding.\n\n"
                f"Check logs: docker logs catalyst-ibga --tail 50\n\n"
                f"Time: {datetime.now()}"
            )

        return 1

    # Check 3: Real connection test
    conn_result = check_connection()
    log(f"Connection test: connected={conn_result['connected']}, authenticated={conn_result['authenticated']}")

    if conn_result["authenticated"]:
        status = {
            "status": STATUS_READY,
            "ready_to_trade": True,
            "container": "running",
            "port": "open",
            "connected": True,
            "authenticated": True,
            "accounts": conn_result["accounts"],
            "error": None,
            "timestamp": datetime.now().isoformat(),
            "check_type": "socket"
        }
        write_status(status)

        log("IBGA READY FOR TRADING")

        # Alert if recovered from bad state
        if previous_status not in [STATUS_READY, "unknown"]:
            send_alert(
                "IBGA READY",
                f"IBGA is now authenticated and ready for trading.\n\n"
                f"Accounts: {conn_result['accounts']}\n"
                f"Time: {datetime.now()}"
            )

        return 0

    elif conn_result["connected"]:
        # Connected but not authenticated (needs 2FA)
        status = {
            "status": STATUS_NOT_AUTHENTICATED,
            "ready_to_trade": False,
            "container": "running",
            "port": "open",
            "connected": True,
            "authenticated": False,
            "accounts": [],
            "error": conn_result["error"],
            "timestamp": datetime.now().isoformat(),
            "check_type": "socket"
        }
        write_status(status)

        log("IBGA NOT AUTHENTICATED - needs IB Key approval")

        if previous_status != STATUS_NOT_AUTHENTICATED:
            send_alert(
                "IBGA NEEDS IB KEY APPROVAL",
                f"IBGA is connected but not authenticated.\n\n"
                f"ACTION REQUIRED:\n"
                f"1. Check your phone for IB Key notification\n"
                f"2. Approve within 2 minutes\n"
                f"3. Gateway will connect automatically\n\n"
                f"Error: {conn_result['error']}\n"
                f"Time: {datetime.now()}"
            )

        return 1

    else:
        # Connection failed
        status = {
            "status": STATUS_ERROR,
            "ready_to_trade": False,
            "container": "running",
            "port": "open",
            "connected": False,
            "authenticated": False,
            "accounts": [],
            "error": conn_result["error"],
            "timestamp": datetime.now().isoformat(),
            "check_type": "socket"
        }
        write_status(status)

        log(f"IBGA CONNECTION ERROR: {conn_result['error']}")

        if previous_status not in [STATUS_ERROR, STATUS_NOT_CONNECTED]:
            send_alert(
                "IBGA CONNECTION ERROR",
                f"Failed to connect to IBGA.\n\n"
                f"Error: {conn_result['error']}\n\n"
                f"Check: docker logs catalyst-ibga --tail 50\n"
                f"Time: {datetime.now()}"
            )

        return 1


if __name__ == "__main__":
    sys.exit(main())
