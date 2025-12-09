"""
Name of Application: Catalyst Trading System
Name of file: agent/main.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Entry point for the autonomous agent - runs forever

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Eternal loop architecture
- Three-level thinking (Tactical, Analytical, Strategic)
- Condition-triggered, not clock-triggered

Description:
This is the heart of the autonomous trading system. Unlike a cron-triggered
script that runs and exits, this is a continuous process that monitors,
thinks, and acts in an eternal loop.

Architecture:
    Initialize -> Monitor -> Evaluate Stimuli -> Think -> Act -> Loop
"""

import asyncio
import signal
import sys
from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

import structlog

from agent.alerts import AlertSystem
from agent.execution import ExecutionEngine
from agent.memory import MemorySystem
from agent.monitor import MarketMonitor
from agent.stimulus import Stimulus, StimulusEvaluator
from agent.thinking import ThinkingEngine
from config.settings import Settings, get_settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

HK_TZ = ZoneInfo("Asia/Hong_Kong")


class AutonomousAgent:
    """
    The Autonomous Trading Mind

    This is not a script that runs and exits.
    This is a continuous process that monitors, thinks, and acts.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the autonomous agent.

        Args:
            settings: Application settings (loads from env if not provided)
        """
        self.settings = settings or get_settings()
        self.running = True

        # Core components (initialized in startup)
        self.monitor: Optional[MarketMonitor] = None
        self.evaluator: Optional[StimulusEvaluator] = None
        self.thinker: Optional[ThinkingEngine] = None
        self.executor: Optional[ExecutionEngine] = None
        self.memory: Optional[MemorySystem] = None
        self.alerts: Optional[AlertSystem] = None

        # State tracking
        self.session_analysis_done = False
        self.week_analysis_done = False
        self.last_tactical_time: Optional[datetime] = None

        # Statistics
        self.loop_count = 0
        self.decisions_made = 0
        self.trades_executed = 0

    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing autonomous agent...")

        # Initialize in dependency order
        try:
            # 1. Memory system (database)
            self.memory = MemorySystem(self.settings.effective_database_url)
            await self.memory.initialize()
            logger.info("Memory system initialized")

            # 2. Alert system
            self.alerts = AlertSystem(
                webhook_url=self.settings.alert_webhook,
                email=self.settings.alert_email,
                smtp_host=self.settings.smtp_host,
                smtp_port=self.settings.smtp_port,
                smtp_user=self.settings.smtp_user,
                smtp_pass=self.settings.smtp_pass,
            )
            logger.info("Alert system initialized")

            # 3. Execution engine (IBKR)
            self.executor = ExecutionEngine(
                host=self.settings.ibkr_host,
                port=self.settings.ibkr_port,
                client_id=self.settings.ibkr_client_id,
            )
            await self.executor.connect()
            logger.info("Execution engine initialized")

            # 4. Market monitor
            self.monitor = MarketMonitor(self.executor.ib)
            await self.monitor.initialize()
            logger.info("Market monitor initialized")

            # 5. Stimulus evaluator (with current strategy)
            strategy = await self.memory.get_current_strategy()
            self.evaluator = StimulusEvaluator(
                strategy=strategy,
                timezone=self.settings.timezone,
            )
            logger.info("Stimulus evaluator initialized")

            # 6. Thinking engine (Claude API)
            self.thinker = ThinkingEngine(
                api_key=self.settings.anthropic_api_key,
                tactical_model=self.settings.tactical_model,
                analytical_model=self.settings.analytical_model,
                strategic_model=self.settings.strategic_model,
            )
            logger.info("Thinking engine initialized")

            # Notify startup
            await self.alerts.notify_startup(
                environment=self.settings.environment,
                exchange=self.settings.exchange_code,
            )

            logger.info(
                "Autonomous agent initialized successfully",
                environment=self.settings.environment,
                exchange=self.settings.exchange_code,
            )

        except Exception as e:
            logger.error("Failed to initialize agent", error=str(e), exc_info=True)
            raise

    async def run(self):
        """The eternal loop - Claude's consciousness."""
        await self.initialize()

        logger.info("Starting eternal loop...")

        while self.running:
            try:
                await self.loop_iteration()

                # Brief pause (responsive, not sleeping)
                await asyncio.sleep(self.settings.loop_interval_ms / 1000)

            except asyncio.CancelledError:
                logger.info("Agent loop cancelled")
                break

            except Exception as e:
                logger.error("Agent loop error", error=str(e), exc_info=True)
                await self.alerts.error(f"Agent loop error: {e}")
                # Back off on error
                await asyncio.sleep(60)

        await self.shutdown()

    async def loop_iteration(self):
        """Single iteration of the eternal loop."""
        self.loop_count += 1

        # Gather current state
        market_state = await self.monitor.get_state()
        portfolio = await self.executor.get_portfolio()
        context = await self.memory.get_recent_context()

        # Update evaluator with current strategy
        self.evaluator.strategy = context.strategy

        # Evaluate what needs thinking about
        stimuli = self.evaluator.evaluate(market_state, portfolio)

        # Process each stimulus
        for stimulus in stimuli:
            await self.process_stimulus(stimulus, market_state, portfolio, context)

        # Check for temporal triggers
        await self._check_temporal_triggers()

        # Periodic logging
        if self.loop_count % 1000 == 0:
            logger.info(
                "Agent status",
                loop_count=self.loop_count,
                decisions_made=self.decisions_made,
                trades_executed=self.trades_executed,
            )

    async def process_stimulus(
        self,
        stimulus: Stimulus,
        market_state,
        portfolio,
        context,
    ):
        """Process a single stimulus through thinking and potential action."""
        logger.info(
            "Processing stimulus",
            type=stimulus.type.value,
            symbol=stimulus.symbol,
            level=stimulus.level,
        )

        if stimulus.level == "TACTICAL":
            decision = await self.thinker.tactical_think(
                stimulus=stimulus,
                market_state=market_state,
                portfolio=portfolio,
                context=context,
            )

            # Log decision regardless of action
            decision_id = await self.memory.log_decision(decision)
            decision.id = decision_id
            self.decisions_made += 1

            # Execute if action required
            if decision.action not in ("HOLD", "WAIT", "SKIP"):
                result = await self.executor.execute(decision)
                await self.memory.update_decision_execution(decision_id, result)

                if result.success:
                    self.trades_executed += 1

            # Alert human if needed
            if decision.needs_human_attention:
                await self.alerts.attention_needed(decision)

    async def _check_temporal_triggers(self):
        """Check for time-based analysis triggers."""
        now = datetime.now(HK_TZ)

        # End of session analysis
        if self.evaluator.is_session_end() and not self.session_analysis_done:
            await self.end_of_session_analysis()
            self.session_analysis_done = True

        if self.evaluator.is_session_start():
            self.session_analysis_done = False  # Reset for new session

        # Weekly strategic review (Friday after close)
        if self.evaluator.is_week_end() and not self.week_analysis_done:
            await self.weekly_strategic_review()
            self.week_analysis_done = True

        if self.evaluator.is_week_start():
            self.week_analysis_done = False  # Reset for new week

    async def end_of_session_analysis(self):
        """Level 2: Analytical thinking at end of trading day."""
        logger.info("Starting end-of-session analysis...")

        today_context = await self.memory.get_today_context()

        if not today_context.decisions:
            logger.info("No decisions today, skipping analysis")
            return

        insights = await self.thinker.analytical_think(today_context)

        await self.memory.store_insights(insights)
        await self.alerts.daily_summary(insights)

        logger.info(
            "End-of-session analysis complete",
            insights_count=len(insights.patterns_observed),
        )

    async def weekly_strategic_review(self):
        """Level 3: Strategic thinking at end of week."""
        logger.info("Starting weekly strategic review...")

        week_context = await self.memory.get_week_context()

        strategy_update = await self.thinker.strategic_think(week_context)

        if strategy_update.has_changes:
            await self.memory.update_strategy(strategy_update)

        await self.alerts.strategic_update(strategy_update)

        logger.info("Weekly strategic review complete")

    async def shutdown(self):
        """Clean shutdown."""
        logger.info("Shutting down autonomous agent...")

        self.running = False

        if self.executor:
            # Optionally close all positions on shutdown
            # await self.executor.close_all_positions("Agent shutdown")
            await self.executor.disconnect()

        if self.monitor:
            await self.monitor.disconnect()

        if self.memory:
            await self.memory.close()

        if self.alerts:
            await self.alerts.notify_shutdown()

        logger.info("Autonomous agent shutdown complete")

    def handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False


async def main():
    """Entry point."""
    # Load settings
    settings = get_settings()

    # Configure logging level
    import logging

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/agent.log"),
        ],
    )

    logger.info("=" * 60)
    logger.info("Catalyst Autonomous Trading Agent")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Exchange: {settings.exchange_code}")

    # Create agent
    agent = AutonomousAgent(settings)

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, agent.handle_signal, sig, None)

    # Run forever
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
