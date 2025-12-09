"""
Name of Application: Catalyst Trading System
Name of file: agent/memory.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Database interface for storing decisions, outcomes, patterns, insights

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Async PostgreSQL with asyncpg
- Decision logging with full reasoning
- Pattern and insight storage
- Strategy evolution tracking

Description:
Claude can't remember between invocations, so we give it memory through the database.
This module handles all database operations for the autonomous agent's persistent memory.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

import asyncpg
import structlog

logger = structlog.get_logger()


@dataclass
class Context:
    """Context provided to Claude for decision-making."""

    decisions: list = field(default_factory=list)
    patterns: list = field(default_factory=list)
    strategy: Optional[dict] = None
    insights: list = field(default_factory=list)
    performance: Optional[dict] = None


class MemorySystem:
    """
    Claude's Persistent Memory

    Stores:
    - Decisions with full reasoning
    - Position outcomes
    - Learned patterns
    - Generated insights
    - Strategy evolution
    """

    def __init__(self, database_url: str):
        """Initialize memory system.

        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool."""
        logger.info("Initializing memory system...")

        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
        )

        # Verify helper functions exist
        await self._verify_helpers()

        logger.info("Memory system initialized")

    async def _verify_helpers(self):
        """Verify required helper functions exist in database."""
        async with self.pool.acquire() as conn:
            has_helper = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM pg_proc WHERE proname = 'get_or_create_security'
                )
            """)

            if not has_helper:
                logger.warning(
                    "Helper function get_or_create_security not found. "
                    "Run sql/schema.sql to create it."
                )

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    # =========================================================================
    # Decision Operations
    # =========================================================================

    async def log_decision(self, decision) -> int:
        """Store a decision with full reasoning.

        Args:
            decision: TacticalDecision object

        Returns:
            The decision_id
        """
        async with self.pool.acquire() as conn:
            # Get current strategy version
            strategy_id = await conn.fetchval("""
                SELECT strategy_id FROM strategy_versions
                WHERE effective_until IS NULL
                ORDER BY effective_from DESC
                LIMIT 1
            """)

            decision_id = await conn.fetchval(
                """
                INSERT INTO decisions (
                    timestamp, market, symbol, stimulus_type, stimulus_data,
                    context_provided, observation, assessment, reasoning,
                    confidence, confidence_reasoning, action,
                    entry_price, stop_price, target_price, position_size,
                    uncertainties, additional_info_wanted, thinking_level,
                    strategy_version_id
                ) VALUES (
                    NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18, $19
                )
                RETURNING decision_id
                """,
                "HKEX",
                decision.symbol,
                decision.stimulus_type,
                json.dumps(decision.stimulus_data),
                json.dumps(decision.context_provided),
                decision.observation,
                decision.assessment,
                decision.reasoning,
                decision.confidence,
                decision.confidence_reasoning,
                decision.action,
                decision.entry_price,
                decision.stop_price,
                decision.target_price,
                decision.size_percent,
                decision.uncertainties,
                decision.would_help,
                decision.thinking_level,
                strategy_id,
            )

            logger.info(
                "Decision logged",
                decision_id=decision_id,
                symbol=decision.symbol,
                action=decision.action,
            )

            return decision_id

    async def update_decision_execution(
        self,
        decision_id: int,
        execution_result,
    ):
        """Update decision with execution results."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE decisions
                SET executed = true,
                    execution_price = $2,
                    execution_time = NOW(),
                    position_id = $3
                WHERE decision_id = $1
                """,
                decision_id,
                execution_result.filled_price,
                execution_result.position_id,
            )

    # =========================================================================
    # Context Retrieval
    # =========================================================================

    async def get_recent_context(self, days: int = 7) -> Context:
        """Get recent decisions and outcomes for context."""
        async with self.pool.acquire() as conn:
            # Recent decisions with outcomes
            decisions = await conn.fetch(
                """
                SELECT
                    d.decision_id, d.timestamp, d.symbol, d.action,
                    d.confidence, d.reasoning, d.uncertainties,
                    p.realized_pnl, p.realized_pnl_pct,
                    p.status as position_status, p.exit_reason
                FROM decisions d
                LEFT JOIN positions p ON d.position_id = p.position_id
                WHERE d.timestamp > NOW() - INTERVAL '%s days'
                ORDER BY d.timestamp DESC
                LIMIT 50
                """
                % days
            )

            # Active patterns
            patterns = await conn.fetch("""
                SELECT
                    pattern_id, name, description,
                    identification_rules, conditions_favorable,
                    times_traded, win_count, loss_count, total_pnl,
                    avg_confidence_when_win, avg_confidence_when_loss
                FROM patterns
                WHERE active = true
                ORDER BY total_pnl DESC
            """)

            # Current strategy
            strategy = await conn.fetchrow("""
                SELECT strategy_id as id, parameters, rationale, effective_from
                FROM strategy_versions
                WHERE effective_until IS NULL
                ORDER BY effective_from DESC
                LIMIT 1
            """)

            # Recent insights
            insights = await conn.fetch("""
                SELECT insight_type, insight_text, validation_status
                FROM insights
                WHERE generated_at > NOW() - INTERVAL '7 days'
                ORDER BY generated_at DESC
                LIMIT 10
            """)

            return Context(
                decisions=[dict(d) for d in decisions],
                patterns=[dict(p) for p in patterns],
                strategy=dict(strategy) if strategy else None,
                insights=[dict(i) for i in insights],
            )

    async def get_today_context(self) -> Context:
        """Get today's decisions for end-of-day analysis."""
        async with self.pool.acquire() as conn:
            decisions = await conn.fetch("""
                SELECT
                    d.*,
                    p.realized_pnl, p.realized_pnl_pct,
                    p.max_favorable, p.max_adverse,
                    p.exit_reason, p.status as position_status
                FROM decisions d
                LEFT JOIN positions p ON d.position_id = p.position_id
                WHERE DATE(d.timestamp AT TIME ZONE 'Asia/Hong_Kong') = CURRENT_DATE
                ORDER BY d.timestamp
            """)

            patterns = await conn.fetch(
                "SELECT * FROM patterns WHERE active = true"
            )

            strategy = await conn.fetchrow("""
                SELECT * FROM strategy_versions
                WHERE effective_until IS NULL
                ORDER BY effective_from DESC LIMIT 1
            """)

            return Context(
                decisions=[dict(d) for d in decisions],
                patterns=[dict(p) for p in patterns],
                strategy=dict(strategy) if strategy else None,
            )

    async def get_week_context(self) -> Context:
        """Get this week's data for strategic review."""
        async with self.pool.acquire() as conn:
            # Week's performance summary
            performance = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(realized_pnl) as total_pnl,
                    AVG(realized_pnl) as avg_pnl
                FROM positions
                WHERE exit_time > NOW() - INTERVAL '7 days'
                AND status = 'closed'
            """)

            # Week's insights
            insights = await conn.fetch("""
                SELECT * FROM insights
                WHERE generated_at > NOW() - INTERVAL '7 days'
                ORDER BY generated_at DESC
            """)

            # Strategy history
            strategy_history = await conn.fetch("""
                SELECT * FROM strategy_versions
                ORDER BY effective_from DESC
                LIMIT 5
            """)

            # Current strategy
            strategy = await conn.fetchrow("""
                SELECT * FROM strategy_versions
                WHERE effective_until IS NULL
                ORDER BY effective_from DESC LIMIT 1
            """)

            return Context(
                decisions=[],  # Not needed for strategic
                patterns=[],  # Not needed for strategic
                strategy=dict(strategy) if strategy else None,
                insights=[dict(i) for i in insights],
                performance=dict(performance) if performance else None,
            )

    async def get_current_strategy(self) -> dict:
        """Get current active strategy parameters."""
        async with self.pool.acquire() as conn:
            strategy = await conn.fetchrow("""
                SELECT parameters
                FROM strategy_versions
                WHERE effective_until IS NULL
                ORDER BY effective_from DESC
                LIMIT 1
            """)

            if strategy:
                params = strategy["parameters"]
                if isinstance(params, str):
                    return json.loads(params)
                return dict(params)
            else:
                # Return default strategy
                return {
                    "risk_appetite": "conservative",
                    "max_position_size_pct": 5,
                    "max_daily_loss_pct": 2,
                    "max_open_positions": 3,
                    "volume_threshold": 2.0,
                    "price_threshold": 2.0,
                }

    # =========================================================================
    # Insight Operations
    # =========================================================================

    async def store_insights(self, insights):
        """Store analytical insights."""
        async with self.pool.acquire() as conn:
            # Store pattern observations
            for pattern in insights.patterns_observed:
                await conn.execute(
                    """
                    INSERT INTO insights (
                        thinking_level, insight_type, insight_text,
                        supporting_evidence
                    ) VALUES ('ANALYTICAL', 'PATTERN', $1, $2)
                    """,
                    pattern.get("pattern", ""),
                    json.dumps(pattern),
                )

            # Store calibration insights
            for calibration in insights.calibration_adjustments:
                await conn.execute(
                    """
                    INSERT INTO insights (
                        thinking_level, insight_type, insight_text,
                        supporting_evidence
                    ) VALUES ('ANALYTICAL', 'CALIBRATION', $1, $2)
                    """,
                    calibration.get("reasoning", ""),
                    json.dumps(calibration),
                )

            logger.info(
                "Insights stored",
                patterns=len(insights.patterns_observed),
                calibrations=len(insights.calibration_adjustments),
            )

    # =========================================================================
    # Strategy Operations
    # =========================================================================

    async def update_strategy(self, strategy_update):
        """Update strategy with new parameters."""
        async with self.pool.acquire() as conn:
            # Close current strategy
            await conn.execute("""
                UPDATE strategy_versions
                SET effective_until = NOW()
                WHERE effective_until IS NULL
            """)

            # Get next version number
            max_version = await conn.fetchval(
                "SELECT COALESCE(MAX(version_number), 0) FROM strategy_versions"
            )

            # Insert new strategy
            await conn.execute(
                """
                INSERT INTO strategy_versions (
                    version_number, parameters, rationale, changed_by
                ) VALUES ($1, $2, $3, 'STRATEGIC')
                """,
                max_version + 1,
                json.dumps(strategy_update.new_parameters),
                strategy_update.rationale,
            )

            logger.info(
                "Strategy updated",
                version=max_version + 1,
                rationale=strategy_update.rationale[:100],
            )

    # =========================================================================
    # Position Operations
    # =========================================================================

    async def record_position(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        broker_order_id: str,
        decision_id: int,
    ) -> int:
        """Record a new position."""
        async with self.pool.acquire() as conn:
            # Get or create security
            security_id = await conn.fetchval(
                "SELECT get_or_create_security($1)", symbol.upper()
            )

            # Create position
            position_id = await conn.fetchval(
                """
                INSERT INTO positions (
                    security_id, symbol, side, quantity, entry_price,
                    stop_loss, take_profit, broker_order_id,
                    entry_decision_id, status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'open')
                RETURNING position_id
                """,
                security_id,
                symbol.upper(),
                side,
                quantity,
                entry_price,
                stop_loss,
                take_profit,
                broker_order_id,
                decision_id,
            )

            logger.info(
                "Position recorded",
                position_id=position_id,
                symbol=symbol,
                side=side,
            )

            return position_id

    async def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str,
        decision_id: Optional[int] = None,
    ) -> Optional[dict]:
        """Close an existing position."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                UPDATE positions SET
                    status = 'closed',
                    exit_price = $2,
                    exit_time = NOW(),
                    exit_reason = $3,
                    exit_decision_id = $4
                WHERE symbol = $1 AND status = 'open'
                RETURNING *
                """,
                symbol.upper(),
                exit_price,
                exit_reason,
                decision_id,
            )

            if result:
                logger.info(
                    "Position closed",
                    symbol=symbol,
                    exit_price=exit_price,
                    reason=exit_reason,
                )
                return dict(result)

            return None

    async def get_open_positions(self) -> list:
        """Get all open positions."""
        async with self.pool.acquire() as conn:
            positions = await conn.fetch("""
                SELECT * FROM positions
                WHERE status = 'open'
                ORDER BY entry_time DESC
            """)
            return [dict(p) for p in positions]

    # =========================================================================
    # Analytics Operations
    # =========================================================================

    async def get_daily_stats(self) -> dict:
        """Get today's trading statistics."""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_decisions,
                    SUM(CASE WHEN action IN ('BUY', 'SELL') THEN 1 ELSE 0 END) as trades,
                    SUM(CASE WHEN executed = true THEN 1 ELSE 0 END) as executed
                FROM decisions
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Hong_Kong') = CURRENT_DATE
            """)

            positions = await conn.fetchrow("""
                SELECT
                    COUNT(*) as open_positions,
                    COALESCE(SUM(
                        CASE WHEN status = 'closed'
                        AND DATE(exit_time AT TIME ZONE 'Asia/Hong_Kong') = CURRENT_DATE
                        THEN realized_pnl ELSE 0 END
                    ), 0) as today_pnl
                FROM positions
                WHERE status = 'open'
                   OR (status = 'closed'
                       AND DATE(exit_time AT TIME ZONE 'Asia/Hong_Kong') = CURRENT_DATE)
            """)

            return {
                "total_decisions": stats["total_decisions"] or 0,
                "trades": stats["trades"] or 0,
                "executed": stats["executed"] or 0,
                "open_positions": positions["open_positions"] or 0,
                "today_pnl": float(positions["today_pnl"] or 0),
            }
