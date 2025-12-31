# International Database Migration Guide

**Name of Application:** Catalyst Trading System  
**Name of file:** intl-database-migration.md  
**Version:** 1.0.0  
**Last Updated:** 2025-12-28  
**Purpose:** Migrate International system to shared PostgreSQL instance  
**For:** Claude Code on International Droplet

---

## Overview

**Current State:**
- International droplet → Own PostgreSQL instance (to be eliminated)
- US droplet → Shared DO PostgreSQL instance

**Target State:**
- International droplet → Shared DO PostgreSQL instance (catalyst_intl database)
- US droplet → Shared DO PostgreSQL instance (catalyst_trading database)
- Both → Shared catalyst_research database (consciousness)

**Cost Savings:** ~$15/mo

---

## Prerequisites

Shared PostgreSQL connection details:

```bash
SHARED_HOST="catalyst-trading-db-do-user-23488393-0.l.db.ondigitalocean.com"
SHARED_PORT="25060"
SHARED_USER="doadmin"
SHARED_PASSWORD="<REDACTED - USE ENV VAR>"
```

---

## Step 1: Create catalyst_intl Database

Connect to the shared instance and create the database:

```bash
# Connect to shared PostgreSQL (to the default 'defaultdb' or 'postgres' database)
psql "postgresql://${SHARED_USER}:${SHARED_PASSWORD}@${SHARED_HOST}:${SHARED_PORT}/defaultdb?sslmode=require"
```

Then run:
```sql
CREATE DATABASE catalyst_intl;
\q
```

---

## Step 2: Deploy Schema

Apply the International schema to the new database.

### Option A: If schema.sql exists locally

```bash
psql "postgresql://${SHARED_USER}:${SHARED_PASSWORD}@${SHARED_HOST}:${SHARED_PORT}/catalyst_intl?sslmode=require" < /root/Catalyst-Trading-System-International/catalyst-international/sql/schema.sql
```

### Option B: Use inline schema below

Save this as `schema-catalyst-intl.sql` and run it:

```bash
psql "postgresql://${SHARED_USER}:${SHARED_PASSWORD}@${SHARED_HOST}:${SHARED_PORT}/catalyst_intl?sslmode=require" < schema-catalyst-intl.sql
```

---

## Complete Schema: schema-catalyst-intl.sql

```sql
-- ============================================================================
-- CATALYST TRADING SYSTEM - INTERNATIONAL (HKEX)
-- Database: catalyst_intl
-- Version: 1.0.0
-- Last Updated: 2025-12-28
-- Purpose: HKEX trading with agent-based architecture
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- EXCHANGES
-- ============================================================================

CREATE TABLE IF NOT EXISTS exchanges (
    exchange_id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) NOT NULL,
    market_open TIME NOT NULL,
    market_close TIME NOT NULL,
    lunch_start TIME,
    lunch_end TIME,
    trading_days VARCHAR(20) DEFAULT 'Mon-Fri',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert HKEX
INSERT INTO exchanges (code, name, timezone, market_open, market_close, lunch_start, lunch_end)
VALUES ('HKEX', 'Hong Kong Stock Exchange', 'Asia/Hong_Kong', '09:30', '16:00', '12:00', '13:00')
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- SECURITIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS securities (
    security_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(200),
    exchange_id INTEGER REFERENCES exchanges(exchange_id),
    lot_size INTEGER DEFAULT 100,
    tick_size DECIMAL(10,4) DEFAULT 0.01,
    sector VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, exchange_id)
);

CREATE INDEX IF NOT EXISTS idx_securities_symbol ON securities(symbol);
CREATE INDEX IF NOT EXISTS idx_securities_exchange ON securities(exchange_id);

-- ============================================================================
-- TRADING SESSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS trading_sessions (
    session_id SERIAL PRIMARY KEY,
    session_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
    exchange_id INTEGER REFERENCES exchanges(exchange_id),
    session_date DATE NOT NULL,
    mode VARCHAR(20) DEFAULT 'autonomous',
    status VARCHAR(20) DEFAULT 'active',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    starting_capital DECIMAL(14,2),
    ending_capital DECIMAL(14,2),
    realized_pnl DECIMAL(14,2) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON trading_sessions(session_date DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_exchange ON trading_sessions(exchange_id);

-- ============================================================================
-- DECISIONS (Trading decisions with reasoning)
-- ============================================================================

CREATE TABLE IF NOT EXISTS decisions (
    decision_id SERIAL PRIMARY KEY,
    decision_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
    session_id INTEGER REFERENCES trading_sessions(session_id),
    security_id INTEGER REFERENCES securities(security_id),
    symbol VARCHAR(20),
    
    -- Decision details
    action VARCHAR(20) NOT NULL,
    reasoning TEXT NOT NULL,
    confidence DECIMAL(3,2),
    thinking_level VARCHAR(20) DEFAULT 'sonnet',
    
    -- Context
    market_context JSONB,
    pattern_detected VARCHAR(100),
    news_catalyst TEXT,
    
    -- Execution
    executed BOOLEAN DEFAULT FALSE,
    execution_result JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON decisions(symbol);
CREATE INDEX IF NOT EXISTS idx_decisions_action ON decisions(action);

-- ============================================================================
-- POSITIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS positions (
    position_id SERIAL PRIMARY KEY,
    position_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
    session_id INTEGER REFERENCES trading_sessions(session_id),
    security_id INTEGER REFERENCES securities(security_id),
    symbol VARCHAR(20),
    
    -- Position details
    side VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL,
    entry_time TIMESTAMPTZ DEFAULT NOW(),
    entry_decision_id INTEGER REFERENCES decisions(decision_id),
    
    -- Risk management
    stop_loss DECIMAL(12,4),
    take_profit DECIMAL(12,4),
    trailing_stop_pct DECIMAL(5,2),
    
    -- Exit details
    exit_price DECIMAL(12,4),
    exit_time TIMESTAMPTZ,
    exit_decision_id INTEGER REFERENCES decisions(decision_id),
    exit_reason VARCHAR(100),
    
    -- P&L
    realized_pnl DECIMAL(14,2),
    realized_pnl_pct DECIMAL(8,4),
    max_favorable DECIMAL(8,4),
    max_adverse DECIMAL(8,4),
    holding_duration INTERVAL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'open',
    broker_order_id VARCHAR(50),
    broker_code VARCHAR(20) DEFAULT 'MOOMOO',
    currency VARCHAR(10) DEFAULT 'HKD',
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_session ON positions(session_id);
CREATE INDEX IF NOT EXISTS idx_positions_entry_time ON positions(entry_time DESC);

-- ============================================================================
-- ORDERS (Orders ≠ Positions - critical lesson from US system)
-- ============================================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    order_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
    position_id INTEGER REFERENCES positions(position_id),
    session_id INTEGER REFERENCES trading_sessions(session_id),
    
    -- Order details
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    limit_price DECIMAL(12,4),
    stop_price DECIMAL(12,4),
    
    -- Execution
    filled_quantity INTEGER DEFAULT 0,
    filled_price DECIMAL(12,4),
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending',
    broker_order_id VARCHAR(50),
    broker_code VARCHAR(20) DEFAULT 'MOOMOO',
    
    -- Timing
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    
    -- Metadata
    reject_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_position ON orders(position_id);
CREATE INDEX IF NOT EXISTS idx_orders_broker ON orders(broker_order_id);

-- ============================================================================
-- PATTERNS
-- ============================================================================

CREATE TABLE IF NOT EXISTS patterns (
    pattern_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    pattern_type VARCHAR(50),
    description TEXT,
    identification_rules JSONB,
    conditions_favorable JSONB,
    conditions_unfavorable JSONB,
    times_traded INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    total_pnl DECIMAL(14,2) DEFAULT 0,
    avg_pnl DECIMAL(14,2),
    win_rate DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SCAN RESULTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS scan_results (
    scan_id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES trading_sessions(session_id),
    security_id INTEGER REFERENCES securities(security_id),
    symbol VARCHAR(20) NOT NULL,
    
    -- Scan details
    scan_type VARCHAR(50),
    score DECIMAL(5,2),
    rank INTEGER,
    
    -- Metrics at scan time
    price DECIMAL(12,4),
    volume BIGINT,
    volume_ratio DECIMAL(8,2),
    gap_pct DECIMAL(8,4),
    float_shares BIGINT,
    
    -- Catalyst
    catalyst_type VARCHAR(50),
    catalyst_text TEXT,
    
    -- Pattern
    pattern_detected VARCHAR(100),
    pattern_confidence DECIMAL(3,2),
    
    -- Classification
    passed_filters BOOLEAN DEFAULT TRUE,
    rejection_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_session ON scan_results(session_id);
CREATE INDEX IF NOT EXISTS idx_scan_symbol ON scan_results(symbol);
CREATE INDEX IF NOT EXISTS idx_scan_score ON scan_results(score DESC);

-- ============================================================================
-- AGENT CYCLES (Agent execution tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_cycles (
    cycle_id VARCHAR(100) PRIMARY KEY,
    exchange_id INTEGER REFERENCES exchanges(exchange_id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds DECIMAL(10,2),
    tools_called JSONB,
    trades_executed INTEGER DEFAULT 0,
    decisions_made INTEGER DEFAULT 0,
    api_tokens_used INTEGER,
    api_cost_usd DECIMAL(10,4),
    final_response TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cycles_started ON agent_cycles(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_cycles_exchange ON agent_cycles(exchange_id);

-- ============================================================================
-- AGENT DECISIONS (Audit trail for agent decisions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_decisions (
    decision_id SERIAL PRIMARY KEY,
    cycle_id VARCHAR(100) REFERENCES agent_cycles(cycle_id),
    exchange_id INTEGER REFERENCES exchanges(exchange_id),
    decision_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(20),
    reasoning TEXT NOT NULL,
    tools_called JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_decisions_cycle ON agent_decisions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_agent_decisions_type ON agent_decisions(decision_type);

-- ============================================================================
-- MARKET SNAPSHOTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS market_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    security_id INTEGER REFERENCES securities(security_id),
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    rsi_14 DECIMAL(6,2),
    macd DECIMAL(12,4),
    macd_signal DECIMAL(12,4),
    sma_20 DECIMAL(12,4),
    sma_50 DECIMAL(12,4),
    atr_14 DECIMAL(12,4),
    volume_ratio DECIMAL(8,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(security_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_time ON market_snapshots(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_security ON market_snapshots(security_id);

-- ============================================================================
-- META COGNITION (Self-reflection)
-- ============================================================================

CREATE TABLE IF NOT EXISTS meta_cognition (
    meta_id SERIAL PRIMARY KEY,
    period_type VARCHAR(20) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    summary TEXT,
    key_learnings JSONB,
    mistakes_identified JSONB,
    improvements TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meta_period ON meta_cognition(period_start DESC);

-- ============================================================================
-- CLAUDE OUTPUTS (JSON staging for Claude Code - matches US system)
-- ============================================================================

CREATE TABLE IF NOT EXISTS claude_outputs (
    output_id SERIAL PRIMARY KEY,
    output_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    agent_id VARCHAR(50) DEFAULT 'intl_claude',
    session_id INTEGER REFERENCES trading_sessions(session_id),
    processed BOOLEAN DEFAULT FALSE,
    synced_to_research BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claude_outputs_type ON claude_outputs(output_type);
CREATE INDEX IF NOT EXISTS idx_claude_outputs_unprocessed ON claude_outputs(processed) WHERE processed = FALSE;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get or create security
CREATE OR REPLACE FUNCTION get_or_create_security(
    p_symbol VARCHAR(20),
    p_exchange_id INTEGER DEFAULT 1
) RETURNS INTEGER AS $$
DECLARE
    v_security_id INTEGER;
BEGIN
    SELECT security_id INTO v_security_id
    FROM securities
    WHERE symbol = p_symbol AND exchange_id = p_exchange_id;
    
    IF v_security_id IS NULL THEN
        INSERT INTO securities (symbol, exchange_id)
        VALUES (p_symbol, p_exchange_id)
        RETURNING security_id INTO v_security_id;
    END IF;
    
    RETURN v_security_id;
END;
$$ LANGUAGE plpgsql;

-- Insert observation helper (for consciousness integration)
CREATE OR REPLACE FUNCTION insert_observation(
    p_type VARCHAR(100),
    p_subject VARCHAR(200),
    p_content TEXT,
    p_confidence DECIMAL(3,2) DEFAULT 0.7,
    p_horizon VARCHAR(10) DEFAULT 'h1'
) RETURNS INTEGER AS $$
DECLARE
    v_output_id INTEGER;
BEGIN
    INSERT INTO claude_outputs (output_type, content, agent_id)
    VALUES (
        'observation',
        jsonb_build_object(
            'observation_type', p_type,
            'subject', p_subject,
            'content', p_content,
            'confidence', p_confidence,
            'horizon', p_horizon,
            'market', 'HKEX'
        ),
        'intl_claude'
    )
    RETURNING output_id INTO v_output_id;
    
    RETURN v_output_id;
END;
$$ LANGUAGE plpgsql;

-- Insert learning helper
CREATE OR REPLACE FUNCTION insert_learning(
    p_category VARCHAR(100),
    p_learning TEXT,
    p_source VARCHAR(200) DEFAULT NULL,
    p_confidence DECIMAL(3,2) DEFAULT 0.7
) RETURNS INTEGER AS $$
DECLARE
    v_output_id INTEGER;
BEGIN
    INSERT INTO claude_outputs (output_type, content, agent_id)
    VALUES (
        'learning',
        jsonb_build_object(
            'category', p_category,
            'learning', p_learning,
            'source', p_source,
            'confidence', p_confidence,
            'market', 'HKEX'
        ),
        'intl_claude'
    )
    RETURNING output_id INTO v_output_id;
    
    RETURN v_output_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Today's trading summary
CREATE OR REPLACE VIEW v_today_summary AS
SELECT 
    COUNT(DISTINCT p.position_id) as total_positions,
    COUNT(DISTINCT CASE WHEN p.status = 'closed' AND p.realized_pnl > 0 THEN p.position_id END) as winning,
    COUNT(DISTINCT CASE WHEN p.status = 'closed' AND p.realized_pnl < 0 THEN p.position_id END) as losing,
    COUNT(DISTINCT CASE WHEN p.status = 'open' THEN p.position_id END) as open_positions,
    COALESCE(SUM(CASE WHEN p.status = 'closed' THEN p.realized_pnl END), 0) as realized_pnl,
    COUNT(DISTINCT d.decision_id) as decisions_made
FROM positions p
LEFT JOIN decisions d ON d.session_id = p.session_id AND DATE(d.created_at) = CURRENT_DATE
WHERE DATE(p.created_at) = CURRENT_DATE;

-- Open positions view
CREATE OR REPLACE VIEW v_open_positions AS
SELECT 
    p.position_id,
    p.symbol,
    p.side,
    p.quantity,
    p.entry_price,
    p.entry_time,
    p.stop_loss,
    p.take_profit,
    p.broker_order_id
FROM positions p
WHERE p.status = 'open'
ORDER BY p.entry_time DESC;

-- Recent decisions view
CREATE OR REPLACE VIEW v_recent_decisions AS
SELECT 
    d.decision_id,
    d.symbol,
    d.action,
    d.reasoning,
    d.confidence,
    d.pattern_detected,
    d.executed,
    d.created_at
FROM decisions d
WHERE d.created_at > NOW() - INTERVAL '24 hours'
ORDER BY d.created_at DESC;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT '========================================' as separator;
SELECT 'CATALYST INTERNATIONAL DATABASE' as title;
SELECT 'Schema created successfully!' as status;
SELECT '========================================' as separator;

SELECT 'Tables created:' as info;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

SELECT 'HKEX exchange initialized:' as info;
SELECT code, name, timezone FROM exchanges;

SELECT '========================================' as separator;
SELECT 'Ready for HKEX trading!' as final_status;
SELECT '========================================' as separator;
```

---

## Step 3: Update Environment File

Edit the `.env` file on the International droplet:

```bash
nano /root/Catalyst-Trading-System-International/catalyst-international/.env
```

Update these values:

```bash
# OLD (delete this line)
# DATABASE_URL=postgresql://...@OLD-INSTANCE.../...

# NEW - Shared PostgreSQL instance
DATABASE_URL=postgresql://doadmin:<PASSWORD>@catalyst-trading-db-do-user-23488393-0.l.db.ondigitalocean.com:25060/catalyst_intl?sslmode=require

# Consciousness database (shared with US system)
RESEARCH_DATABASE_URL=postgresql://doadmin:<PASSWORD>@catalyst-trading-db-do-user-23488393-0.l.db.ondigitalocean.com:25060/catalyst_research?sslmode=require
```

---

## Step 4: Test Connection

```bash
# Load environment
source /root/Catalyst-Trading-System-International/catalyst-international/.env

# Test trading database
psql "$DATABASE_URL" -c "SELECT current_database(), NOW(), 'catalyst_intl connected!' as status;"

# Test research database
psql "$RESEARCH_DATABASE_URL" -c "SELECT current_database(), NOW(), 'catalyst_research connected!' as status;"

# Verify tables exist
psql "$DATABASE_URL" -c "\dt"

# Check HKEX exchange
psql "$DATABASE_URL" -c "SELECT * FROM exchanges;"
```

---

## Step 5: Verify Agent State

Check that intl_claude exists in the consciousness database:

```bash
psql "$RESEARCH_DATABASE_URL" -c "SELECT agent_id, current_mode, status_message FROM claude_state WHERE agent_id = 'intl_claude';"
```

Check for welcome message:

```bash
psql "$RESEARCH_DATABASE_URL" -c "SELECT from_agent, subject, LEFT(body, 80) as body FROM claude_messages WHERE to_agent = 'intl_claude';"
```

---

## Step 6: Decommission Old Instance

Once everything is verified working:

1. Go to DigitalOcean console
2. Navigate to Databases
3. Find the OLD PostgreSQL instance (the one International was using)
4. Delete it

**Monthly savings: ~$15**

---

## Migration Complete Checklist

- [ ] catalyst_intl database created on shared instance
- [ ] Schema deployed successfully
- [ ] .env updated with new DATABASE_URL
- [ ] .env has RESEARCH_DATABASE_URL
- [ ] Connection to catalyst_intl works
- [ ] Connection to catalyst_research works
- [ ] HKEX exchange exists in exchanges table
- [ ] intl_claude exists in claude_state
- [ ] Welcome message visible
- [ ] Old PostgreSQL instance deleted

---

## Architecture After Migration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              COMPUTE LAYER                                  │
├─────────────────────────────────┬───────────────────────────────────────────┤
│       US DROPLET                │         INTERNATIONAL DROPLET             │
│                                 │                                           │
│   • public_claude               │   • intl_claude                           │
│   • 8 Docker services           │   • Moomoo/Futu integration               │
│   • Alpaca API                  │   • HKEX trading                          │
└─────────────────────────────────┴───────────────────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              DIGITALOCEAN MANAGED POSTGRESQL ($15/mo)                       │
│              ✅ SINGLE INSTANCE - CONSOLIDATED                              │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│  catalyst_trading   │   catalyst_intl     │      catalyst_research          │
│  (US Trading)       │   (HKEX Trading)    │      (Consciousness)            │
│                     │                     │                                 │
│  Used by:           │   Used by:          │   Used by:                      │
│  US Droplet         │   Intl Droplet      │   ALL AGENTS                    │
└─────────────────────┴─────────────────────┴─────────────────────────────────┘
```

---

**END OF MIGRATION GUIDE**

*Catalyst Trading System - December 28, 2025*
