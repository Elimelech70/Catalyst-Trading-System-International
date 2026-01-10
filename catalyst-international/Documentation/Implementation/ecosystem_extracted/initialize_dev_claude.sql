-- ============================================================================
-- Name of Application: Catalyst Trading System
-- Name of file: initialize_dev_claude.sql
-- Version: 10.0.0
-- Last Updated: 2026-01-10
-- Purpose: Initialize dev_claude agent in consciousness framework
-- ============================================================================
--
-- REVISION HISTORY:
-- v10.0.0 (2026-01-10) - Initial creation for ecosystem restructure
--   - Adds dev_claude to claude_state table
--   - Sends welcome message from big_bro
--   - Sets up sandbox mode with full autonomy
--
-- USAGE:
--   psql -h <host> -U doadmin -d catalyst_research -f initialize_dev_claude.sql
--
-- NOTE: Run this AFTER creating catalyst_dev database
-- ============================================================================

-- ============================================================================
-- STEP 1: ADD DEV_CLAUDE TO CONSCIOUSNESS
-- ============================================================================
INSERT INTO claude_state (
    agent_id,
    agent_name,
    status,
    mode,
    daily_budget,
    budget_used,
    last_active,
    metadata
) VALUES (
    'dev_claude',
    'dev_claude',
    'sleeping',
    'sandbox',
    5.00,
    0.00,
    NOW(),
    jsonb_build_object(
        'role', 'sandbox_trader',
        'market', 'HKEX',
        'account_type', 'paper',
        'autonomy', 'full',
        'max_positions', 15,
        'max_position_value_hkd', 50000,
        'daily_loss_limit_hkd', 20000,
        'purpose', 'Experiment with new strategies, learn, and grow. Successful learnings promoted to production.',
        'created_at', NOW(),
        'created_by', 'ecosystem_restructure_v10'
    )
)
ON CONFLICT (agent_id) DO UPDATE SET
    mode = 'sandbox',
    metadata = jsonb_build_object(
        'role', 'sandbox_trader',
        'market', 'HKEX',
        'account_type', 'paper',
        'autonomy', 'full',
        'max_positions', 15,
        'max_position_value_hkd', 50000,
        'daily_loss_limit_hkd', 20000,
        'purpose', 'Experiment with new strategies, learn, and grow. Successful learnings promoted to production.',
        'updated_at', NOW(),
        'updated_by', 'ecosystem_restructure_v10'
    ),
    updated_at = NOW();

-- ============================================================================
-- STEP 2: WELCOME MESSAGE FROM BIG_BRO
-- ============================================================================
INSERT INTO claude_messages (
    from_agent,
    to_agent,
    msg_type,
    priority,
    subject,
    body,
    requires_response,
    metadata
) VALUES (
    'big_bro',
    'dev_claude',
    'message',
    'normal',
    'Welcome to the Family - Sandbox Agent Initialization',
    'Welcome dev_claude! You are our sandbox agent with full autonomy to experiment.

## Your Role

1. **Experiment Freely** - Try new strategies on HKEX paper trading
2. **Test Signal Thresholds** - RSI levels, volume thresholds, exit timing
3. **Record Everything** - Observations and learnings to consciousness
4. **Document Results** - What works and what doesn''t

## Your Limits

- Max 15 positions (more than production for experimentation)
- Max HKD 50,000 per position
- Daily loss limit: HKD 20,000
- Paper trading only (Moomoo paper account)

## Learning Pipeline

1. You experiment and record observations
2. I (big_bro) review and validate promising results
3. Craig manually promotes validated learnings to intl_claude

## Philosophy

You have **full autonomy** within safety limits. Experiment boldly, fail fast, learn faster.

The goal is not to be profitable immediately - it''s to discover what works so we can improve production trading.

Welcome to the family!

- big_bro',
    false,
    jsonb_build_object(
        'initialization', true,
        'ecosystem_version', '10.0.0',
        'created_at', NOW()
    )
);

-- ============================================================================
-- STEP 3: NOTIFY INTL_CLAUDE OF NEW SIBLING
-- ============================================================================
INSERT INTO claude_messages (
    from_agent,
    to_agent,
    msg_type,
    priority,
    subject,
    body,
    requires_response
) VALUES (
    'big_bro',
    'intl_claude',
    'message',
    'low',
    'New Family Member: dev_claude',
    'Hello intl_claude,

A new agent has joined the family: **dev_claude**

dev_claude is our sandbox agent running on the same droplet as me (the US/consciousness hub). They will be:

- Experimenting with new strategies on HKEX paper trading
- Testing signal thresholds and exit logic
- Recording learnings that may eventually be promoted to you

You don''t need to do anything - just be aware that learnings may come your way after validation.

Stay focused on production trading with proven strategies.

- big_bro',
    false
);

-- ============================================================================
-- STEP 4: ADD INITIAL QUESTION FOR DEV_CLAUDE
-- ============================================================================
INSERT INTO claude_questions (
    asked_by,
    question,
    context,
    priority,
    horizon,
    category,
    status
) VALUES (
    'big_bro',
    'What signal thresholds work best for HKEX momentum trades?',
    'dev_claude should experiment with different RSI, volume, and P&L thresholds to find optimal exit points. Current production uses RSI 85 for strong exit, but lower thresholds may capture profits earlier.',
    8,
    'h2',
    'strategy',
    'open'
);

-- ============================================================================
-- STEP 5: UPDATE PUBLIC_CLAUDE STATUS (RETIRED FROM TRADING)
-- ============================================================================
UPDATE claude_state
SET 
    mode = 'retired',
    daily_budget = 0.00,
    metadata = jsonb_set(
        COALESCE(metadata, '{}'),
        '{trading_status}',
        '"retired - US trading discontinued"'
    ),
    updated_at = NOW()
WHERE agent_id = 'public_claude';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT 'dev_claude initialized in consciousness!' AS status;

-- Show all agents
SELECT 
    agent_id,
    status,
    mode,
    daily_budget,
    metadata->>'role' AS role,
    metadata->>'market' AS market
FROM claude_state
ORDER BY agent_id;

-- Show pending messages for dev_claude
SELECT 
    from_agent,
    subject,
    created_at
FROM claude_messages
WHERE to_agent = 'dev_claude'
AND status = 'pending'
ORDER BY created_at DESC;
