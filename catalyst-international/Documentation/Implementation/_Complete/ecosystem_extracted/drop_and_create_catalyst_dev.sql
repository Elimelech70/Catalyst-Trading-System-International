-- ============================================================================
-- Name of Application: Catalyst Trading System
-- Name of file: drop_and_create_catalyst_dev.sql
-- Version: 10.0.0
-- Last Updated: 2026-01-10
-- Purpose: Drop old catalyst_trading, create fresh catalyst_dev for dev_claude
-- ============================================================================
--
-- REVISION HISTORY:
-- v10.0.0 (2026-01-10) - Initial creation for ecosystem restructure
--   - Drops old US trading database (catalyst_trading)
--   - Creates fresh dev_claude sandbox database (catalyst_dev)
--   - Includes position_monitor_status table for pattern-based monitoring
--
-- USAGE:
--   psql -h <host> -U doadmin -d defaultdb -f drop_and_create_catalyst_dev.sql
--
-- WARNING: This script permanently deletes the catalyst_trading database!
--          Ensure all US positions are closed and data is backed up first.
-- ============================================================================

-- ============================================================================
-- STEP 1: DROP OLD US DATABASE (catalyst_trading)
-- ============================================================================
-- Terminate active connections first
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'catalyst_trading' AND pid <> pg_backend_pid();

-- Drop the database
DROP DATABASE IF EXISTS catalyst_trading;

-- ============================================================================
-- STEP 2: CREATE FRESH DEV DATABASE
-- ============================================================================
CREATE DATABASE catalyst_dev;

-- Connect to new database
\c catalyst_dev

-- ============================================================================
-- STEP 3: EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- STEP 4: SECURITIES TABLE
-- ============================================================================
CREATE TABLE securities (
    security_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    exchange VARCHAR(20) DEFAULT 'HKEX',
    
    -- HKEX-specific
    lot_size INTEGER DEFAULT 100,
    tick_size DECIMAL(10,4),
    
    -- Classification
    sector VARCHAR(100),
    industry VARCHAR(100),
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_securities_symbol ON securities(symbol);
CREATE INDEX idx_securities_active ON securities(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE securities IS 'Master table of HKEX tradeable instruments';
COMMENT ON COLUMN securities.lot_size IS 'Board lot size varies by stock on HKEX';

-- ============================================================================
-- STEP 5: TRADING_CYCLES TABLE
-- ============================================================================
CREATE TABLE trading_cycles (
    cycle_id VARCHAR(50) PRIMARY KEY,
    date DATE NOT NULL,
    
    -- Cycle state
    status VARCHAR(20) DEFAULT 'active',
    mode VARCHAR(20) DEFAULT 'trade',
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    
    -- Results
    positions_opened INTEGER DEFAULT 0,
    positions_closed INTEGER DEFAULT 0,
    daily_pnl DECIMAL(14,2) DEFAULT 0,
    
    -- AI tracking
    api_calls INTEGER DEFAULT 0,
    api_cost DECIMAL(10,4) DEFAULT 0,
    
    -- Metadata
    notes TEXT,
    configuration JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cycles_date ON trading_cycles(date DESC);
CREATE INDEX idx_cycles_status ON trading_cycles(status);

COMMENT ON TABLE trading_cycles IS 'Tracks each trading cycle/session';

-- ============================================================================
-- STEP 6: POSITIONS TABLE
-- ============================================================================
-- CRITICAL: This table stores HOLDINGS only - NOT orders
-- Order data belongs in the orders table

CREATE TABLE positions (
    position_id SERIAL PRIMARY KEY,
    position_uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    
    -- References
    cycle_id VARCHAR(50) REFERENCES trading_cycles(cycle_id),
    security_id INTEGER REFERENCES securities(security_id),
    symbol VARCHAR(20) NOT NULL,
    
    -- Position details
    side VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL,
    entry_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    entry_reason TEXT,
    entry_volume DECIMAL(14,2),
    
    -- Risk management
    stop_loss DECIMAL(12,4),
    take_profit DECIMAL(12,4),
    trailing_stop_pct DECIMAL(5,2),
    
    -- Exit details
    exit_price DECIMAL(12,4),
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_reason VARCHAR(100),
    
    -- P&L tracking
    realized_pnl DECIMAL(14,2),
    realized_pnl_pct DECIMAL(8,4),
    unrealized_pnl DECIMAL(14,2),
    unrealized_pnl_pct DECIMAL(8,4),
    
    -- High/low tracking
    high_watermark DECIMAL(12,4),
    max_favorable DECIMAL(8,4),
    max_adverse DECIMAL(8,4),
    
    -- Status
    status VARCHAR(20) DEFAULT 'open',
    
    -- Broker tracking
    broker_order_id VARCHAR(100),
    broker_code VARCHAR(20) DEFAULT 'MOOMOO',
    currency VARCHAR(10) DEFAULT 'HKD',
    
    -- Metadata
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    opened_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT chk_position_side CHECK (side IN ('long', 'short')),
    CONSTRAINT chk_position_status CHECK (status IN ('pending', 'open', 'closed', 'cancelled'))
);

CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_cycle ON positions(cycle_id);
CREATE INDEX idx_positions_open ON positions(status) WHERE status = 'open';
CREATE INDEX idx_positions_entry_time ON positions(entry_time DESC);

COMMENT ON TABLE positions IS 'Current and historical positions - NO order columns here';
COMMENT ON COLUMN positions.high_watermark IS 'Highest price since entry for trailing stops';

-- ============================================================================
-- STEP 7: ORDERS TABLE
-- ============================================================================
-- CRITICAL: This is the ONLY table for order data

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    order_uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    
    -- References
    position_id INTEGER REFERENCES positions(position_id),
    cycle_id VARCHAR(50) REFERENCES trading_cycles(cycle_id),
    security_id INTEGER REFERENCES securities(security_id),
    
    -- Order hierarchy (for bracket orders)
    parent_order_id INTEGER REFERENCES orders(order_id),
    order_class VARCHAR(20),
    
    -- Order details
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    limit_price DECIMAL(12,4),
    stop_price DECIMAL(12,4),
    
    -- Order purpose
    order_purpose VARCHAR(20) NOT NULL DEFAULT 'entry',
    
    -- Execution
    filled_quantity INTEGER DEFAULT 0,
    filled_price DECIMAL(12,4),
    
    -- Broker tracking
    broker_order_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    
    -- Timing
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- Error handling
    reject_reason TEXT,
    error_message TEXT,
    
    -- Metadata
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_order_side CHECK (side IN ('buy', 'sell')),
    CONSTRAINT chk_order_type CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit', 'trailing_stop')),
    CONSTRAINT chk_order_purpose CHECK (order_purpose IN ('entry', 'exit', 'stop_loss', 'take_profit', 'scale_in', 'scale_out'))
);

CREATE INDEX idx_orders_position ON orders(position_id) WHERE position_id IS NOT NULL;
CREATE INDEX idx_orders_cycle ON orders(cycle_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_broker ON orders(broker_order_id) WHERE broker_order_id IS NOT NULL;
CREATE INDEX idx_orders_pending ON orders(status) WHERE status IN ('pending', 'submitted', 'accepted', 'partial_fill');

COMMENT ON TABLE orders IS 'All orders sent to broker - SINGLE SOURCE OF TRUTH for order data';
COMMENT ON COLUMN orders.position_id IS 'NULL for entry orders until position created';

-- ============================================================================
-- STEP 8: SCAN_RESULTS TABLE
-- ============================================================================
CREATE TABLE scan_results (
    scan_id SERIAL PRIMARY KEY,
    
    -- References
    cycle_id VARCHAR(50) REFERENCES trading_cycles(cycle_id),
    security_id INTEGER REFERENCES securities(security_id),
    symbol VARCHAR(20) NOT NULL,
    
    -- Scan data
    price DECIMAL(12,4),
    volume BIGINT,
    change_pct DECIMAL(8,4),
    
    -- Scoring
    rank INTEGER,
    score DECIMAL(8,4),
    composite_score DECIMAL(8,4),
    
    -- Selection
    selected_for_trading BOOLEAN DEFAULT FALSE,
    selection_reason TEXT,
    
    -- Technical indicators at scan time
    rsi DECIMAL(5,2),
    vwap DECIMAL(12,4),
    atr DECIMAL(12,4),
    relative_volume DECIMAL(8,2),
    
    -- Metadata
    scan_data JSONB DEFAULT '{}',
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_scans_cycle ON scan_results(cycle_id);
CREATE INDEX idx_scans_symbol ON scan_results(symbol);
CREATE INDEX idx_scans_score ON scan_results(composite_score DESC);
CREATE INDEX idx_scans_selected ON scan_results(selected_for_trading) WHERE selected_for_trading = TRUE;

COMMENT ON TABLE scan_results IS 'Market scan candidates with scoring';

-- ============================================================================
-- STEP 9: DECISIONS TABLE
-- ============================================================================
CREATE TABLE decisions (
    decision_id SERIAL PRIMARY KEY,
    decision_uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    
    -- References
    cycle_id VARCHAR(50) REFERENCES trading_cycles(cycle_id),
    position_id INTEGER REFERENCES positions(position_id),
    
    -- Decision details
    decision_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(20),
    action VARCHAR(50),
    
    -- Reasoning
    reasoning TEXT,
    confidence DECIMAL(3,2),
    
    -- AI tracking
    thinking_level VARCHAR(20),
    model_used VARCHAR(50),
    tokens_used INTEGER,
    cost_usd DECIMAL(10,4),
    
    -- Outcome
    outcome VARCHAR(50),
    outcome_pnl DECIMAL(14,2),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_decisions_cycle ON decisions(cycle_id);
CREATE INDEX idx_decisions_type ON decisions(decision_type);
CREATE INDEX idx_decisions_symbol ON decisions(symbol);

COMMENT ON TABLE decisions IS 'Trading decisions with reasoning for audit trail';

-- ============================================================================
-- STEP 10: PATTERNS TABLE
-- ============================================================================
CREATE TABLE patterns (
    pattern_id SERIAL PRIMARY KEY,
    
    -- References
    security_id INTEGER REFERENCES securities(security_id),
    symbol VARCHAR(20) NOT NULL,
    
    -- Pattern details
    pattern_type VARCHAR(50) NOT NULL,
    pattern_name VARCHAR(100),
    confidence DECIMAL(3,2),
    
    -- Price levels
    entry_price DECIMAL(12,4),
    stop_loss DECIMAL(12,4),
    target_price DECIMAL(12,4),
    
    -- Timing
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Outcome tracking
    was_traded BOOLEAN DEFAULT FALSE,
    outcome VARCHAR(20),
    actual_pnl DECIMAL(14,2),
    
    -- Metadata
    detection_data JSONB DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_patterns_symbol ON patterns(symbol);
CREATE INDEX idx_patterns_type ON patterns(pattern_type);
CREATE INDEX idx_patterns_detected ON patterns(detected_at DESC);

COMMENT ON TABLE patterns IS 'Detected chart patterns with outcome tracking';

-- ============================================================================
-- STEP 11: POSITION_MONITOR_STATUS TABLE (NEW)
-- ============================================================================
CREATE TABLE position_monitor_status (
    monitor_id SERIAL PRIMARY KEY,
    
    -- References
    position_id INTEGER REFERENCES positions(position_id),
    symbol VARCHAR(20) NOT NULL,
    
    -- Monitor State
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    pid INTEGER,
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    last_check_at TIMESTAMP WITH TIME ZONE,
    next_check_at TIMESTAMP WITH TIME ZONE,
    checks_completed INTEGER DEFAULT 0,
    
    -- Current Market State
    last_price DECIMAL(12,4),
    high_watermark DECIMAL(12,4),
    current_pnl_pct DECIMAL(8,4),
    
    -- Technical Analysis
    last_rsi DECIMAL(5,2),
    last_macd_signal VARCHAR(20),
    last_vwap_position VARCHAR(20),
    last_ema20_position VARCHAR(20),
    
    -- Signal State
    hold_signals TEXT[],
    exit_signals TEXT[],
    signal_strength VARCHAR(20),
    recommendation VARCHAR(10),
    recommendation_reason TEXT,
    
    -- AI Consultation Tracking
    haiku_calls INTEGER DEFAULT 0,
    last_haiku_recommendation TEXT,
    estimated_cost DECIMAL(8,4) DEFAULT 0,
    
    -- Error Tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    consecutive_errors INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_monitor_position ON position_monitor_status(position_id);
CREATE INDEX idx_monitor_symbol ON position_monitor_status(symbol);
CREATE INDEX idx_monitor_status ON position_monitor_status(status);
CREATE INDEX idx_monitor_active ON position_monitor_status(status) 
    WHERE status IN ('running', 'starting');

COMMENT ON TABLE position_monitor_status IS 'Tracks position monitor processes and their health';
COMMENT ON COLUMN position_monitor_status.high_watermark IS 'Highest price since entry for trailing stop calculation';
COMMENT ON COLUMN position_monitor_status.hold_signals IS 'Array of active HOLD signals from signals.py';
COMMENT ON COLUMN position_monitor_status.exit_signals IS 'Array of active EXIT signals from signals.py';

-- ============================================================================
-- STEP 12: TRIGGER FOR UPDATED_AT
-- ============================================================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_positions_updated
    BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_orders_updated
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_monitor_updated
    BEFORE UPDATE ON position_monitor_status
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================================================
-- STEP 13: MONITOR HEALTH VIEW
-- ============================================================================
CREATE OR REPLACE VIEW v_monitor_health AS
SELECT 
    p.position_id,
    p.symbol,
    p.side,
    p.quantity,
    p.entry_price,
    p.stop_loss,
    p.take_profit,
    p.status AS position_status,
    p.opened_at,
    p.entry_time,
    p.unrealized_pnl,
    
    -- Monitor Status
    COALESCE(m.status, 'NO_MONITOR') AS monitor_status,
    m.started_at AS monitor_started,
    m.last_check_at,
    m.next_check_at,
    m.checks_completed,
    m.pid AS monitor_pid,
    
    -- Time Calculations
    ROUND(EXTRACT(EPOCH FROM (NOW() - m.last_check_at))/60, 1) AS minutes_since_check,
    ROUND(EXTRACT(EPOCH FROM (NOW() - p.entry_time))/3600, 1) AS hours_held,
    
    -- Technical State
    m.last_price,
    m.high_watermark,
    m.current_pnl_pct,
    m.last_rsi,
    m.last_macd_signal,
    m.last_vwap_position,
    
    -- Signals
    m.recommendation,
    m.recommendation_reason,
    m.hold_signals,
    m.exit_signals,
    m.signal_strength,
    
    -- Cost Tracking
    m.haiku_calls,
    m.estimated_cost,
    
    -- Errors
    m.last_error,
    m.error_count,
    m.consecutive_errors,
    
    -- Health Indicator
    CASE 
        WHEN m.status IS NULL THEN '🔴 NO_MONITOR'
        WHEN m.status = 'error' THEN '🔴 ERROR'
        WHEN m.consecutive_errors >= 3 THEN '🔴 FAILING'
        WHEN m.last_check_at < NOW() - INTERVAL '15 minutes' THEN '🟡 STALE'
        WHEN m.status = 'running' THEN '🟢 ACTIVE'
        WHEN m.status = 'sleeping' THEN '🔵 SLEEPING'
        WHEN m.status = 'starting' THEN '🟡 STARTING'
        ELSE '⚪ UNKNOWN'
    END AS health,
    
    -- Priority for sorting (issues first)
    CASE 
        WHEN m.status IS NULL THEN 0
        WHEN m.status = 'error' THEN 1
        WHEN m.consecutive_errors >= 3 THEN 2
        WHEN m.last_check_at < NOW() - INTERVAL '15 minutes' THEN 3
        ELSE 10
    END AS priority
    
FROM positions p
LEFT JOIN position_monitor_status m ON m.position_id = p.position_id
WHERE p.status = 'open'
ORDER BY priority, p.entry_time;

COMMENT ON VIEW v_monitor_health IS 'Dashboard view showing monitor health for all open positions';

-- ============================================================================
-- STEP 14: HELPER FUNCTIONS
-- ============================================================================
CREATE OR REPLACE FUNCTION get_or_create_security(p_symbol VARCHAR(20))
RETURNS INTEGER AS $$
DECLARE
    v_security_id INTEGER;
BEGIN
    SELECT security_id INTO v_security_id
    FROM securities
    WHERE symbol = UPPER(p_symbol);

    IF v_security_id IS NULL THEN
        INSERT INTO securities (symbol, exchange, is_active)
        VALUES (UPPER(p_symbol), 'HKEX', true)
        RETURNING security_id INTO v_security_id;
    END IF;

    RETURN v_security_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_or_create_security IS 'Get or create security_id for HKEX symbol';

-- ============================================================================
-- STEP 15: DATABASE COMMENT
-- ============================================================================
COMMENT ON DATABASE catalyst_dev IS 'dev_claude sandbox trading - HKEX paper trading with full autonomy';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT 'catalyst_dev database created successfully!' AS status;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
