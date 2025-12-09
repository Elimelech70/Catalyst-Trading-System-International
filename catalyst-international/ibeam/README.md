# IBKR IBeam Setup for Catalyst Trading System

## Overview

IBeam is a Docker container that automates Interactive Brokers Client Portal Gateway authentication. This allows the Catalyst agent to trade via REST API without manual login.

## Prerequisites

1. IBKR Pro account (funded)
2. IBKR Mobile app with "IB Key" enabled for 2FA
3. Paper trading account credentials (for testing)
4. Docker installed on your server

## Quick Start

### 1. Configure Credentials

```bash
cd /opt/catalyst/ibeam
cp .env.example .env
nano .env
```

Fill in your paper trading credentials:
```
IBEAM_ACCOUNT=your_paper_username
IBEAM_PASSWORD=your_paper_password
```

### 2. Start IBeam Container

```bash
docker-compose up -d
```

### 3. Watch for Authentication

```bash
docker logs -f catalyst-ibeam
```

Wait for "Client login succeeds" message (can take 1-2 minutes).

### 4. Verify Connection

```bash
curl -sk https://localhost:5000/v1/api/iserver/auth/status | jq
```

Expected response:
```json
{"authenticated": true, "connected": true, "competing": false}
```

### 5. Run Test Script

```bash
python /opt/catalyst/scripts/test_ibkr_paper.py
```

## Health Monitoring

The health check script runs automatically every 15 minutes if configured:

```bash
# Add to crontab
crontab -e

# Add this line:
*/15 * * * * /opt/catalyst/scripts/ibkr_health_check.sh
```

View health logs:
```bash
tail -f /var/log/catalyst/ibkr_health.log
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Session expired - IBeam should auto-reauthenticate |
| 429 Too Many Requests | Rate limited - wait 15 minutes |
| Gateway not responding | Restart: `docker restart catalyst-ibeam` |
| 2FA timeout | Enable IB Key in mobile app |
| Connection refused | Wait 2 minutes for startup |

## Files

```
/opt/catalyst/ibeam/
├── docker-compose.yml     # Container config
├── .env                   # Credentials (not in git)
├── .env.example           # Template
├── conf.yaml              # Gateway config
└── README.md              # This file

/opt/catalyst/services/ibkr_client/
├── ibkr_client.py         # REST API client
└── requirements.txt       # Dependencies

/opt/catalyst/scripts/
├── ibkr_health_check.sh   # Cron health check
└── test_ibkr_paper.py     # Connection test
```

## API Rate Limits

- Global: 10 requests/second via CP Gateway
- Exceeding limit returns 429 status
- Violators put in penalty box for 15 minutes

## Session Management

- Sessions reset at midnight (region-based)
- Keepalive: Call `/tickle` every 5 minutes
- IBeam handles re-authentication automatically

## Switching to Live Trading

1. Update `/opt/catalyst/ibeam/.env` with live credentials
2. Restart: `docker-compose down && docker-compose up -d`
3. Verify account type in response

**WARNING**: Test thoroughly with paper trading before going live!
