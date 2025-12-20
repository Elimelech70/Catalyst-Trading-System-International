# IBGA Monitoring System

**Name of Application**: Catalyst Trading System
**Name of file**: ibga-monitoring-system.md
**Version**: 1.0.0
**Last Updated**: 2025-12-15
**Purpose**: Pre-trade IBGA verification to ensure gateway is ready before trading

---

## REVISION HISTORY

**v1.0.0 (2025-12-15)** - Initial implementation
- Created socket-based IBGA status checker
- Added pre-flight verification to agent.py
- Coordinated cron schedule for status checks before agent runs
- Email alerts on status changes

---

## Problem Statement

The trading agent could start and waste Claude API tokens even when IBGA wasn't authenticated or ready for trading. The previous monitoring only parsed Docker logs (unreliable) and ran on a schedule that wasn't coordinated with agent runs.

### Previous Issues

| Issue | Impact |
|-------|--------|
| No blocking gate before agent runs | Agent starts even if IBGA not ready |
| Log parsing for auth status | Unreliable, misses edge cases |
| Status could be stale | 30+ minutes between check and agent run |
| No real socket test | Port open doesn't mean authenticated |

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IBGA MONITORING SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CRON (09:25 HKT)                                                           │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────────────┐                                               │
│  │ ibga_status_checker.py   │                                               │
│  │ - Connect via ib_async   │                                               │
│  │ - Check authentication   │                                               │
│  │ - Get managed accounts   │                                               │
│  └──────────┬───────────────┘                                               │
│             │                                                                │
│             ▼                                                                │
│  ┌──────────────────────────┐     ┌─────────────────────────────────┐      │
│  │ /tmp/ibga-status.json    │────▶│ Email Alert (if status changed) │      │
│  │ - status: ready/error    │     └─────────────────────────────────┘      │
│  │ - ready_to_trade: bool   │                                               │
│  │ - authenticated: bool    │                                               │
│  │ - timestamp: ISO         │                                               │
│  └──────────┬───────────────┘                                               │
│             │                                                                │
│             │ (5 minutes later)                                              │
│             │                                                                │
│  CRON (09:30 HKT)                                                           │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────────────┐                                               │
│  │ agent.py                 │                                               │
│  │ - Import preflight.py    │                                               │
│  │ - Check status file      │                                               │
│  │ - Verify < 10 min old    │                                               │
│  │ - Verify authenticated   │                                               │
│  └──────────┬───────────────┘                                               │
│             │                                                                │
│             ▼                                                                │
│      ┌──────┴──────┐                                                        │
│      │             │                                                         │
│   READY?        NOT READY                                                   │
│      │             │                                                         │
│      ▼             ▼                                                         │
│  Run Trading    Exit with                                                   │
│  Cycle          Alert                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. IBGA Status Checker

**File**: `scripts/ibga_status_checker.py`
**Version**: 1.0.0

Performs real socket-based connection test using `ib_async`:

```python
# What it checks:
1. Docker container running? (docker ps)
2. Port 4000 open? (netcat)
3. Can connect via ib_async? (real socket)
4. Can get managed accounts? (proves authentication)
```

**Status Values**:

| Status | Meaning | ready_to_trade |
|--------|---------|----------------|
| `ready` | Fully authenticated, can trade | `true` |
| `not_connected` | Port closed or connection refused | `false` |
| `not_authenticated` | Connected but needs IB Key 2FA | `false` |
| `container_down` | Docker container not running | `false` |
| `error` | Unexpected error | `false` |

**Status File** (`/tmp/ibga-status.json`):

```json
{
  "status": "ready",
  "ready_to_trade": true,
  "container": "running",
  "port": "open",
  "connected": true,
  "authenticated": true,
  "accounts": ["DU1234567"],
  "error": null,
  "timestamp": "2025-12-15T09:25:00.000000",
  "check_type": "socket"
}
```

### 2. Pre-flight Module

**File**: `preflight.py`
**Version**: 1.0.0

Imported by `agent.py` to verify IBGA status before running:

```python
from preflight import run_preflight_checks

success, message = run_preflight_checks()
if not success:
    sys.exit(1)  # Don't waste API tokens
```

**Checks Performed**:

1. **Status file exists** - `/tmp/ibga-status.json` must exist
2. **Status is fresh** - Timestamp must be < 10 minutes old
3. **ready_to_trade is true** - IBGA must be authenticated
4. **Market hours** (optional) - Can be skipped with `--force`

### 3. Agent Integration

**File**: `agent.py`
**Version**: 1.3.0 (updated from 1.2.0)

New command-line arguments:

```bash
# Normal operation (preflight enabled)
python3 agent.py

# Skip preflight (testing only)
python3 agent.py --skip-preflight

# Refresh status before checking
python3 agent.py --refresh-status

# Run outside market hours
python3 agent.py --force
```

**Behavior**:

| Condition | Result |
|-----------|--------|
| Preflight passes | Agent runs trading cycle |
| Preflight fails | Agent exits with code 1, sends alert |
| `--skip-preflight` | Warning logged, agent runs anyway |

---

## Cron Schedule

All times in UTC (HKT = UTC + 8):

```cron
# =============================================================================
# IBGA STATUS CHECKS (5 minutes before agent)
# =============================================================================

# Pre-market (08:00 HKT)
0 0 * * 1-5 ./venv/bin/python3 scripts/ibga_status_checker.py

# Before morning session (09:25 HKT)
25 1 * * 1-5 ./venv/bin/python3 scripts/ibga_status_checker.py

# Before afternoon session (12:55 HKT)
55 4 * * 1-5 ./venv/bin/python3 scripts/ibga_status_checker.py

# Hourly during market hours
30 2-7 * * 1-5 ./venv/bin/python3 scripts/ibga_status_checker.py

# =============================================================================
# TRADING AGENT (runs after status verified)
# =============================================================================

# Morning session (09:30 HKT)
30 1 * * 1-5 ./venv/bin/python3 agent.py

# Afternoon session (13:00 HKT)
0 5 * * 1-5 ./venv/bin/python3 agent.py

# =============================================================================
# WEEKEND CHECKS (prepare for Monday)
# =============================================================================

# Sunday evening checks
0 9 * * 0 ./venv/bin/python3 scripts/ibga_status_checker.py   # 17:00 HKT
0 12 * * 0 ./venv/bin/python3 scripts/ibga_status_checker.py  # 20:00 HKT
0 14 * * 0 ./venv/bin/python3 scripts/ibga_status_checker.py  # 22:00 HKT
```

**Timeline (Morning Session)**:

```
09:25 HKT - Status checker runs, writes fresh status
09:30 HKT - Agent starts, reads status (5 min old = fresh)
          - If ready_to_trade=true: proceed
          - If ready_to_trade=false: abort with alert
```

---

## Email Alerts

Alerts are sent when status changes:

| Alert | Trigger |
|-------|---------|
| `IBGA READY` | Status changed to authenticated |
| `IBGA NEEDS IB KEY APPROVAL` | Connected but not authenticated |
| `IBGA CONTAINER DOWN` | Docker container stopped |
| `IBGA CONNECTION ERROR` | Socket connection failed |
| `AGENT PRE-FLIGHT FAILED` | Agent blocked from starting |

**Alert Recipient**: `craigjcolley@gmail.com`

---

## File Structure

```
catalyst-international/
├── agent.py                    # v1.3.0 - Added preflight integration
├── preflight.py                # v1.0.0 - Pre-flight check module
├── scripts/
│   ├── ibga_status_checker.py  # v1.0.0 - Socket-based status checker
│   ├── monitor-ibga.sh         # Legacy bash monitor (kept for alerts)
│   └── ibga-status.sh          # Human-readable status display
└── Documentation/
    └── Design/
        └── ibga-monitoring-system.md  # This document
```

---

## Usage

### Manual Status Check

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international

# Run status checker
./venv/bin/python3 scripts/ibga_status_checker.py

# View status file
cat /tmp/ibga-status.json | jq .

# Human-readable status
./scripts/ibga-status.sh
```

### Test Pre-flight

```bash
# Test preflight module directly
./venv/bin/python3 preflight.py

# Test agent with preflight
./venv/bin/python3 agent.py --force

# Bypass preflight (testing only)
./venv/bin/python3 agent.py --skip-preflight --force
```

### Refresh and Run

```bash
# Refresh status then run agent
./venv/bin/python3 agent.py --refresh-status --force
```

---

## Troubleshooting

### Agent Won't Start

```
PRE-FLIGHT FAILED - Agent cannot start
Reason: IBGA: IBGA not ready: not_authenticated
```

**Fix**:
1. Check IB Key app for approval request
2. Run `./venv/bin/python3 scripts/ibga_status_checker.py`
3. View status: `cat /tmp/ibga-status.json`

### Status File Stale

```
Status is stale (15.2 minutes old, max 10)
```

**Fix**:
1. Run status checker: `./venv/bin/python3 scripts/ibga_status_checker.py`
2. Or use: `./venv/bin/python3 agent.py --refresh-status`

### Container Not Running

```
status: container_down
```

**Fix**:
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international/ibga
docker compose up -d
# Wait 45 seconds for startup
./venv/bin/python3 scripts/ibga_status_checker.py
```

---

## Configuration

### Status File Location

```python
STATUS_FILE = "/tmp/ibga-status.json"
```

### Maximum Status Age

```python
MAX_STATUS_AGE_MINUTES = 10  # Status must be fresher than this
```

### Connection Parameters

```python
host = os.environ.get("IBKR_HOST", "127.0.0.1")
port = int(os.environ.get("IBKR_PORT", "4000"))
client_id = 99  # Dedicated client ID for status checks
```

---

## Benefits

| Before | After |
|--------|-------|
| Agent runs even if IBGA not ready | Agent blocked until IBGA authenticated |
| Log parsing (unreliable) | Real socket test (accurate) |
| Status could be 30+ min stale | Status always < 10 min old |
| No coordination with agent | Status check 5 min before agent |
| Silent failures | Email alerts on status changes |
| Wasted API tokens on failed cycles | Early abort saves money |

---

## Related Documents

- `architecture.md` - Overall system architecture
- `functional-specification.md` - Agent tools and workflow
- `ibga-email-setup.sh` - Email alert configuration

---

## Appendix: Status Checker Flow

```
START
  │
  ▼
Check container running?
  │
  ├── NO ──▶ Status: container_down ──▶ Alert ──▶ Exit 1
  │
  ▼
Check port 4000 open?
  │
  ├── NO ──▶ Status: not_connected ──▶ Alert ──▶ Exit 1
  │
  ▼
Connect via ib_async
  │
  ├── FAIL ──▶ Status: error ──▶ Alert ──▶ Exit 1
  │
  ▼
Get managed accounts
  │
  ├── EMPTY ──▶ Status: not_authenticated ──▶ Alert ──▶ Exit 1
  │
  ▼
Status: ready ──▶ Alert (if changed) ──▶ Exit 0
```
