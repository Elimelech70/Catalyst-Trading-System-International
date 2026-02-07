# Multi-Agent MCP Architecture Implementation

**Date**: 2026-02-07
**Version**: 1.0.0
**Author**: Claude Code (Opus 4.6)
**Status**: Implementation Complete, Ready for Review & Testing

---

## Executive Summary

Migrated the Catalyst Trading System from a monolithic architecture (`unified_agent.py` + `tool_executor.py`) to a **multi-agent system** where 4 specialized agents run as Docker containers communicating via the **Model Context Protocol (MCP)** over SSE/HTTP.

This resolves the core architectural problem: **multiple components independently writing to the positions table**, causing duplicate positions and race conditions. Under the new architecture, a strict **single-writer rule** ensures only the Trade Executor agent can modify positions.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      Docker Network                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Coordinator (Brain)                      │    │
│  │              Claude AI daemon                         │    │
│  │              MCP Client -> all 3 agents               │    │
│  └───────┬──────────────┬──────────────┬─────────────────┘   │
│          │ MCP SSE      │ MCP SSE      │ MCP SSE             │
│          v              v              v                      │
│  ┌──────────────┐ ┌────────────┐ ┌──────────────┐           │
│  │ Position     │ │ Market     │ │ Trade        │           │
│  │ Monitor      │ │ Scanner    │ │ Executor     │           │
│  │ :8001/sse    │ │ :8002/sse  │ │ :8003/sse    │           │
│  │              │ │            │ │              │           │
│  │ READ-ONLY    │ │ READ-ONLY  │ │ SINGLE WRITER│           │
│  │ Signals +    │ │ Quotes +   │ │ Broker +     │           │
│  │ Recommends   │ │ Technicals │ │ Positions DB │           │
│  └──────────────┘ └────────────┘ └──────────────┘           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              PostgreSQL  :5432                        │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Moomoo OpenD  :11111 (host)              │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. **Coordinator** polls **Position Monitor** via MCP for exit recommendations every 60s
2. If EXIT recommendation exists, Coordinator calls **Trade Executor** via MCP to close position
3. Every 30 minutes, Coordinator runs a full scan cycle:
   - Calls **Trade Executor** `get_portfolio` for current state
   - Calls **Market Scanner** `scan_market` for candidates
   - Analyzes candidates via `get_quote`, `get_technicals`, `detect_patterns`, `get_news`
   - Validates with `check_risk`, executes with `execute_trade`
4. All decisions logged via `log_decision` for audit trail

---

## Agent Details

### 1. Position Monitor (:8001) — The Eyes

**Role**: Watches all open positions for exit signals. Writes recommendations to `position_monitor_status` table. **NEVER executes trades or writes to positions table.**

**MCP Tools (3)**:

| Tool | Description |
|------|-------------|
| `get_exit_recommendations` | Returns unacknowledged EXIT/CONSULT_AI recommendations joined with position data |
| `get_position_health` | Returns health status of all monitored positions (P&L, signals, watermark) |
| `acknowledge_recommendation` | Marks a recommendation as processed to prevent re-processing |

**Background Loop** (`monitor.py`):
- Runs every 300s (configurable via `MONITOR_CHECK_INTERVAL`)
- Loads open positions from DB (SELECT only)
- Gets quotes from Moomoo broker (read-only)
- Runs signal analysis (stop loss, take profit, trailing stop, RSI, volume, MACD, time-based)
- For CONSULT_AI signals, optionally consults Claude Haiku (max 5 calls/cycle)
- Writes recommendations to `position_monitor_status` via upsert
- Resets acknowledged flag when recommendation changes

**Signal Detection**:
- Stop loss: strong (-3%) -> EXIT, moderate (-2%) -> CONSULT_AI
- Take profit: strong (+8%) -> EXIT, moderate (+5%) -> CONSULT_AI
- Trailing stop: 2% drop from high watermark -> CONSULT_AI
- RSI: >85 -> EXIT, >75 -> CONSULT_AI
- Volume collapse: <25% of entry -> EXIT, <40% -> CONSULT_AI
- MACD bearish (histogram < -0.5) -> CONSULT_AI
- Near close (15:50-16:00) -> EXIT
- Lunch break (11:50-12:00) -> CONSULT_AI

**Files**: `agents/position-monitor/mcp_server.py` (346 lines), `agents/position-monitor/monitor.py` (462 lines), `Dockerfile` (32 lines)

---

### 2. Market Scanner (:8002) — The Eyes (Market Data)

**Role**: Provides market data for scanning and analysis. **Completely read-only.** No database access.

**MCP Tools (5)**:

| Tool | Description |
|------|-------------|
| `scan_market` | Scan HKEX for candidates with volume spikes, sorted by signal strength |
| `get_quote` | Current quote for a symbol (last price, volume, bid/ask, change) |
| `get_technicals` | RSI, MACD, SMA (9/20/50/200), EMA (9/21), ATR, Bollinger Bands |
| `detect_patterns` | Chart patterns: breakout, near_breakout, bull_flag, ascending_triangle, momentum_continuation |
| `get_news` | News articles + sentiment analysis for a symbol |

**Implementation**: Lazy-init singletons for broker, market data, pattern detector, and news client. Delegates to existing `data/market.py`, `data/patterns.py`, `data/news.py` modules.

**Files**: `agents/market-scanner/mcp_server.py` (288 lines), `Dockerfile` (29 lines)

---

### 3. Trade Executor (:8003) — The Hands (SINGLE WRITER)

**Role**: The **ONLY** component that writes to the positions table and executes broker orders. This is the critical enforcement point for the single-writer rule.

**MCP Tools (7)**:

| Tool | Description |
|------|-------------|
| `get_portfolio` | Cash, equity, positions, max_positions, unrealized P&L |
| `execute_trade` | Execute buy/sell with fill confirmation, auto-adjust qty for HKD 10K limit |
| `close_position` | Close position by symbol via broker + DB update |
| `close_all` | Emergency close all positions |
| `sync_positions` | Sync DB with broker state: dedup, close phantoms, add missing, update qty |
| `check_risk` | Validate trade against risk limits via safety module (13 checks) |
| `log_decision` | Record decision to `agent_decisions` audit trail table |

**Key Behaviors**:
- **Auto-adjusts quantity**: If position value exceeds HKD 10,000, reduces quantity to fit
- **Fill confirmation**: Uses `wait_for_fill=True` — positions only created on confirmed fill
- **Deduplication on sync**: Detects and closes duplicate open rows for same symbol
- **Symbol normalization**: All symbols normalized via `normalize_symbol()` before comparison

**Files**: `agents/trade-executor/mcp_server.py` (597 lines), `Dockerfile` (31 lines)

---

### 4. Coordinator (Brain) — The Decision Maker

**Role**: Continuously running Claude AI agent that connects to all 3 MCP servers and makes all trading decisions.

**Behavior Loop**:
```
while market_open:
    1. Poll position monitor -> get_exit_recommendations()
       - EXIT -> close_position() via trade executor
       - CONSULT_AI -> gather data, Claude decides CLOSE or HOLD
       - acknowledge_recommendation() after acting

    2. Every 30 min: Run full scan cycle
       - Claude AI tool-use loop with SYSTEM_PROMPT
       - Routes tool calls through MCP to appropriate agent
       - Up to 35 iterations per cycle

    3. Sleep 60 seconds, repeat
```

**MCP Connections**:
```json
{
  "position-monitor": "http://position-monitor:8001/sse",
  "market-scanner":   "http://market-scanner:8002/sse",
  "trade-executor":   "http://trade-executor:8003/sse"
}
```

**Tool Routing**: Maps Claude tool names to (mcp_server, tool_name) pairs:
```
get_exit_recommendations -> position-monitor
scan_market              -> market-scanner
execute_trade            -> trade-executor
... (15 tools total)
```

**Files**: `agents/coordinator/coordinator.py` (510 lines), `agents/coordinator/system_prompt.py` (114 lines), `agents/coordinator/Dockerfile` (24 lines), `agents/coordinator/mcp_config.json` (16 lines)

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `agents/position-monitor/mcp_server.py` | 346 | MCP SSE server on :8001, 3 tools, asyncpg for DB |
| `agents/position-monitor/monitor.py` | 462 | Background loop: signal detection, Haiku consultation, upsert recommendations |
| `agents/position-monitor/Dockerfile` | 32 | Python 3.11-slim, copies brokers/, data/, config/, signals.py, safety.py |
| `agents/trade-executor/mcp_server.py` | 597 | MCP SSE server on :8003, 7 tools, SINGLE WRITER |
| `agents/trade-executor/Dockerfile` | 31 | Python 3.11-slim, copies brokers/, data/, config/, safety.py, tools.py |
| `agents/market-scanner/mcp_server.py` | 288 | MCP SSE server on :8002, 5 tools, read-only |
| `agents/market-scanner/Dockerfile` | 29 | Python 3.11-slim, copies brokers/, data/, config/ |
| `agents/coordinator/coordinator.py` | 510 | Claude AI loop, MCPConnection, MCPHub, tool routing |
| `agents/coordinator/system_prompt.py` | 114 | Trading strategy, tier criteria, decision rules |
| `agents/coordinator/mcp_config.json` | 16 | MCP server connection URLs |
| `agents/coordinator/Dockerfile` | 24 | Python 3.11-slim, copies tools.py, config/ |
| `agents/requirements-mcp.txt` | 37 | Shared Python dependencies for all agents |
| **Total** | **2,486** | |

## Files Modified

| File | Change |
|------|--------|
| `docker-compose.yml` | v2.0.0 — Added all 4 agents + postgres + redis + legacy profile. Service dependencies with health checks. |

---

## Docker Compose Services

| Service | Container Name | Port | Dependencies | Notes |
|---------|---------------|------|--------------|-------|
| `postgres` | catalyst-postgres | 5432 | - | PostgreSQL 16 with schema auto-init |
| `redis` | catalyst-redis | 6379 | - | Optional, for future use |
| `position-monitor` | catalyst-position-monitor | 8001 | - | Health check on /health |
| `market-scanner` | catalyst-market-scanner | 8002 | - | Health check on /health |
| `trade-executor` | catalyst-trade-executor | 8003 | - | Health check on /health |
| `coordinator` | catalyst-coordinator | - | All 3 agents (healthy) | Waits for all agents |
| `agent-legacy` | catalyst-agent-legacy | - | postgres | Profile: `legacy` (opt-in only) |

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| MCP Protocol | `mcp` Python SDK | >= 1.0.0 |
| SSE Transport | `starlette` + `SseServerTransport` | >= 0.36.0 |
| ASGI Server | `uvicorn` | >= 0.27.0 |
| Async DB (monitor) | `asyncpg` | >= 0.29.0 |
| Sync DB (executor) | `psycopg2` ThreadedConnectionPool | >= 2.9.9 |
| AI Model (coordinator) | Claude Sonnet 4 | claude-sonnet-4-20250514 |
| AI Model (monitor/haiku) | Claude Haiku 4.5 | claude-haiku-4-5-20251001 |
| Broker API | `moomoo-api` | >= 1.3.0 |
| Container Runtime | Docker | Python 3.11-slim |
| Orchestration | Docker Compose | v2 |

---

## Key Design Decisions

### 1. Single Writer Rule
Only the Trade Executor writes to the `positions` table. This eliminates the root cause of duplicate positions that plagued the monolithic architecture. The Position Monitor writes only to `position_monitor_status`.

### 2. Recommendation-Based Exit Flow
Instead of the monitor executing trades directly (old behavior), it now writes EXIT/CONSULT_AI/HOLD recommendations. The coordinator reads these, decides, and acts through the trade executor. This creates a clear audit trail and prevents unauthorized position modifications.

### 3. Acknowledgment Pattern
After acting on a recommendation, the coordinator marks it as acknowledged via `acknowledge_recommendation`. This prevents the same recommendation from being processed twice. The acknowledged flag resets automatically when the recommendation changes (e.g., HOLD -> EXIT).

### 4. Lazy-Init Singletons
All agents use lazy initialization for broker connections, database pools, and other resources. This means connections are established on first use rather than at startup, improving reliability when services start in sequence.

### 5. MCP SSE Transport
Each agent exposes `/sse` for SSE stream connection and `/messages/` for POST messages. Health checks at `/health` enable Docker health monitoring and the coordinator's `depends_on: service_healthy` pattern.

### 6. Legacy Compatibility
The old monolithic agent is preserved as `agent-legacy` under Docker Compose profile `legacy`. The cron-based `unified_agent.py` continues to work independently. Migration is gradual — both systems can coexist.

---

## Deployment Instructions

### Start All Agents
```bash
docker compose up -d
```

### Start Individual Agent (Testing)
```bash
docker compose up position-monitor      # Phase 1: test monitor alone
docker compose up -d market-scanner     # Add scanner
docker compose up -d trade-executor     # Add executor
docker compose up -d coordinator        # Start the brain
```

### View Logs
```bash
docker compose logs -f coordinator       # Watch the brain decide
docker compose logs -f position-monitor  # Watch signal detection
docker compose logs -f trade-executor    # Watch trade execution
```

### Test MCP Endpoints
```bash
curl http://localhost:8001/health   # Position Monitor
curl http://localhost:8002/health   # Market Scanner
curl http://localhost:8003/health   # Trade Executor
```

### Force Run (Market Closed)
```bash
FORCE_MARKET_OPEN=1 docker compose up coordinator
```

---

## Verification Checklist

- [ ] Position Monitor starts and connects to DB
- [ ] Position Monitor background loop detects open positions
- [ ] Position Monitor writes recommendations to position_monitor_status
- [ ] Market Scanner starts and connects to Moomoo OpenD
- [ ] Market Scanner responds to scan_market requests
- [ ] Trade Executor starts and connects to DB + broker
- [ ] Trade Executor sync_positions works correctly
- [ ] Coordinator connects to all 3 MCP servers
- [ ] Coordinator reads exit recommendations and acts on them
- [ ] Coordinator runs scan cycle with Claude AI loop
- [ ] Coordinator routes tool calls to correct MCP server
- [ ] No component other than Trade Executor writes to positions table
- [ ] Docker health checks pass for all services
- [ ] `docker compose config` validates without errors

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| MCP connection failure | Coordinator retries, logs warnings, continues loop |
| Broker not available | Lazy-init retries on next request, health check returns 503 |
| Database connection pool exhausted | asyncpg pool (2-5 connections), psycopg2 ThreadedConnectionPool |
| Duplicate recommendations processed | Acknowledgment flag prevents double-processing |
| Coordinator crashes mid-trade | Docker `restart: unless-stopped` auto-restarts |
| Race condition on positions | Single-writer rule eliminates multi-writer races |
| Haiku API rate limits | Max 5 Haiku calls per monitoring cycle |

---

## Migration Path

### Phase 1 (Current): All Agents Implemented
All 4 agents are coded and Dockerized. Ready for integration testing.

### Phase 2 (Next): Testing & Validation
- Deploy to staging environment
- Run with `FORCE_MARKET_OPEN=1` for out-of-hours testing
- Verify all tool calls route correctly
- Confirm single-writer rule is enforced

### Phase 3 (Future): Production Cutover
- Disable legacy cron jobs (`unified_agent.py` via crontab)
- Switch to `docker compose up -d` as primary runtime
- Monitor for 1 week before removing legacy code
- Retire `unified_agent.py`, `tool_executor.py`, `position_monitor_service.py`

---

## Appendix: Source Files Reference (Refactored From)

| New Agent File | Refactored From |
|---------------|-----------------|
| `agents/position-monitor/monitor.py` | `position_monitor_service.py` (removed trade execution) |
| `agents/trade-executor/mcp_server.py` | `tool_executor.py` v3.4.0 (isolated as single writer) |
| `agents/market-scanner/mcp_server.py` | `tool_executor.py` market functions + `data/market.py` |
| `agents/coordinator/coordinator.py` | `unified_agent.py` v3.0.0 (MCP client instead of local calls) |
| `agents/coordinator/system_prompt.py` | `unified_agent.py` SYSTEM_PROMPT (extracted) |
