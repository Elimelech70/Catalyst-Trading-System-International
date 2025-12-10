# IBGA - IB Gateway Automation for Catalyst

This directory contains the IBGA (IB Gateway Automation) Docker setup for running Interactive Brokers Gateway in headless mode with IB Key 2FA support.

## Why IBGA instead of IBeam?

IBeam had persistent session issues where login succeeded but the gateway session wasn't established. IBGA uses a different automation approach that's more reliable with IB Key authentication.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Your Phone (IB Key)                        │
│                    Approve login when prompted                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    IBGA Docker Container                        │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                   IB Gateway                            │    │
│  │               (headless, automated)                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                         Port 4000                               │
└──────────────────────────────│──────────────────────────────────┘
                               │
                          Port 4001 (mapped)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Catalyst Agent                              │
│                    (via ib_async library)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start IBGA

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international/ibga
docker compose up -d
docker logs -f catalyst-ibga
```

### 2. Approve IB Key on Your Phone

When you see the login prompt in the logs, you have **2 minutes** to approve the login notification on your IB Key mobile app.

### 3. Verify Connection

```bash
# Check if gateway is listening
nc -zv localhost 4001

# Or run the test script
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
python scripts/test_ibga_connection.py
```

## Configuration

Edit `.env` to change settings:

```bash
# Trading Mode
IB_LOGINTYPE=Paper Trading    # or "Live Trading"

# Credentials are already configured
IB_USERNAME=craigjcolley
IB_PASSWORD=<your_password>
```

## Ports

| Port | Purpose |
|------|---------|
| 4001 | IB Gateway API (ib_async connects here) |
| 5800 | VNC for debugging (optional) |

## Troubleshooting

### Check Logs
```bash
docker logs catalyst-ibga --tail 100
```

### View VNC (if needed)
Open browser to `http://localhost:5800` to see the gateway UI.

### Restart
```bash
docker compose restart
# Watch logs and re-approve IB Key
docker logs -f catalyst-ibga
```

### Session Expired
IB Gateway requires daily restart. IBGA handles this automatically, but you'll need to approve IB Key again after each restart.

## Files

- `docker-compose.yml` - Container configuration
- `.env` - Credentials and settings
- `run/program/` - Gateway installation (auto-downloaded)
- `run/settings/` - Gateway settings (persisted)
