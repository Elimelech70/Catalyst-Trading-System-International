# Catalyst Autonomous Agent - Implementation Guide for Claude Code

**Name of Application:** Catalyst Trading System
**Name of File:** IMPLEMENTATION-GUIDE.md
**Version:** 1.1.0
**Last Updated:** 2025-12-10
**Purpose:** Step-by-step implementation guide for Claude Code to build the autonomous trading agent

---

## REVISION HISTORY

**v1.1.0 (2025-12-10)** - Updated for IBGA Integration
- Updated broker section to reflect IBGA (not IBeam) integration
- Added broker implementation status (COMPLETE)
- Updated connection examples to use ib_async
- Added reference to brokers/ibkr.py v2.1.0

**v1.0.0 (2025-12-09)** - Initial version

---

## CRITICAL: READ THIS FIRST

### File Handling Protocol

**BEFORE creating or modifying ANY file:**

1. **CHECK if file exists** in the current VSCode workspace
2. **If exists, COMPARE by date** (not version number - versions are misaligned)
3. **PRESERVE newer content** - never overwrite newer with older
4. **MERGE if needed** - combine best of both if dates are close

```python
# Pseudo-code for file handling
def handle_file(new_content, filepath):
    if file_exists(filepath):
        existing = read_file(filepath)
        existing_date = extract_last_updated(existing)
        new_date = extract_last_updated(new_content)
        
        if existing_date > new_date:
            # KEEP EXISTING - it's newer
            log(f"Keeping existing {filepath} (dated {existing_date})")
            return
        elif existing_date == new_date:
            # MERGE - compare content, keep best of both
            merged = merge_content(existing, new_content)
            write_file(filepath, merged)
        else:
            # NEW IS NEWER - but still check for unique content in old
            unique_from_old = find_unique_content(existing, new_content)
            if unique_from_old:
                log(f"WARNING: Old file has unique content: {unique_from_old}")
                # Append or merge as appropriate
            write_file(filepath, new_content)
    else:
        # File doesn't exist - create it
        write_file(filepath, new_content)
```

### Date-Based Versioning

Since version numbers are misaligned, use `Last Updated` date as the source of truth:

```
File Header Format:
---
Name of Application: Catalyst Trading System
Name of File: {filename}
Version: {version}
Last Updated: 2025-12-09    ← THIS IS THE KEY FIELD
Purpose: {purpose}
---
```

**Compare dates, not versions.**

---

## PHASE 0: DISCOVERY & SETUP

### Step 0.1: Inventory Existing Files

**First, discover what exists:**

```bash
# List all files in the workspace
find . -type f -name "*.py" -o -name "*.md" -o -name "*.sql" -o -name "*.yml" | head -100

# Check for existing project structure
ls -la
ls -la agent/ 2>/dev/null || echo "agent/ not found"
ls -la prompts/ 2>/dev/null || echo "prompts/ not found"
ls -la sql/ 2>/dev/null || echo "sql/ not found"
```

**Create an inventory:**

```markdown
## Existing Files Inventory

| File | Last Updated | Version | Keep/Replace/Merge |
|------|--------------|---------|-------------------|
| CLAUDE.md | 2025-12-XX | X.X.X | ? |
| schema.sql | 2025-12-XX | X.X.X | ? |
| ... | ... | ... | ... |
```

### Step 0.2: Establish Project Root

```bash
# Determine project root
# Should be: catalyst-autonomous/ or similar

# If not exists, create structure
mkdir -p catalyst-autonomous
cd catalyst-autonomous

# Create directory structure
mkdir -p agent prompts sources tools config sql tests logs docs
```

### Step 0.3: Check Dependencies

```bash
# Check Python version (need 3.10+)
python --version

# Check if venv exists
ls -la venv/ 2>/dev/null || echo "No venv found"

# Check installed packages
pip list 2>/dev/null | grep -E "anthropic|asyncpg|ib_insync"
```

---

## PHASE 1: FOUNDATION FILES

### Step 1.1: CLAUDE.md (The Brain)

**Source:** This document is the instruction set for the autonomous agent.

**Check existing:**
```bash
ls -la CLAUDE.md 2>/dev/null && head -20 CLAUDE.md
```

**If exists:** Extract `Last Updated` date and compare with `2025-12-09`

**Content location:** `/mnt/user-data/outputs/CLAUDE.md` (30K)

**Key sections to preserve if merging:**
- Service-specific wisdom (from embedded services)
- Tool definitions
- Any custom additions Craig made

### Step 1.2: Database Schema (The Memory)

**Source file:** `sql/schema.sql`

**Check existing:**
```bash
ls -la sql/schema.sql 2>/dev/null && head -50 sql/schema.sql
```

**Content location:** `/mnt/user-data/outputs/schema.sql` (21K)

**Critical tables:**
- `decisions` - Every thought with reasoning
- `positions` - Trades with outcomes
- `patterns` - Learned patterns
- `insights` - Generated learnings
- `strategy_versions` - Strategy evolution
- `meta_cognition` - Self-assessment

**If database already has data:**
```sql
-- Check for existing data before schema changes
SELECT COUNT(*) FROM decisions;
SELECT COUNT(*) FROM positions;
-- If data exists, use migrations, don't drop tables
```

### Step 1.3: Docker Configuration

**Files:**
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`

**Check existing:**
```bash
ls -la Dockerfile docker-compose.yml .env* 2>/dev/null
```

**Content locations:**
- `/mnt/user-data/outputs/Dockerfile`
- `/mnt/user-data/outputs/docker-compose.yml`
- `/mnt/user-data/outputs/.env.example`

**If Docker already configured:**
- Compare service definitions
- Preserve any custom environment variables
- Check for running containers: `docker ps`

### Step 1.4: Requirements

**File:** `requirements.txt`

**Check existing:**
```bash
cat requirements.txt 2>/dev/null
```

**Content location:** `/mnt/user-data/outputs/requirements.txt`

**Merge strategy:** Combine packages, use higher versions

---

## PHASE 2: CORE AGENT

### Step 2.1: Agent Package Structure

**Create:**
```bash
mkdir -p agent
touch agent/__init__.py
```

**Files to create:**

| File | Purpose | Priority |
|------|---------|----------|
| `agent/__init__.py` | Package init | 1 |
| `agent/main.py` | Entry point, eternal loop | 1 |
| `agent/monitor.py` | Market monitoring | 2 |
| `agent/stimulus.py` | Stimulus evaluation | 2 |
| `agent/thinking.py` | Claude API invocation | 1 |
| `agent/execution.py` | Trade execution (IBKR) | 2 |
| `agent/memory.py` | Database interface | 1 |
| `agent/alerts.py` | Human notifications | 3 |

### Step 2.2: agent/main.py (The Eternal Loop)

**This is the heart of the system.**

```python
"""
AGENT LOOP - The Autonomous Trading Mind
Name of File: agent/main.py
Last Updated: 2025-12-09
Purpose: Entry point for the autonomous agent - runs forever

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Eternal loop architecture
- Three-level thinking (Tactical, Analytical, Strategic)
- Condition-triggered, not clock-triggered
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional

import structlog

from agent.monitor import MarketMonitor
from agent.stimulus import StimulusEvaluator, Stimulus
from agent.thinking import ThinkingEngine
from agent.execution import ExecutionEngine
from agent.memory import MemorySystem
from agent.alerts import AlertSystem
from config.settings import Settings

logger = structlog.get_logger()


class AutonomousAgent:
    """
    The Autonomous Trading Mind
    
    This is not a script that runs and exits.
    This is a continuous process that monitors, thinks, and acts.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.running = True
        
        # Core components
        self.monitor: Optional[MarketMonitor] = None
        self.evaluator: Optional[StimulusEvaluator] = None
        self.thinker: Optional[ThinkingEngine] = None
        self.executor: Optional[ExecutionEngine] = None
        self.memory: Optional[MemorySystem] = None
        self.alerts: Optional[AlertSystem] = None
        
        # State tracking
        self.session_analysis_done = False
        self.week_analysis_done = False
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing autonomous agent...")
        
        # Initialize in dependency order
        self.memory = MemorySystem(self.settings.database_url)
        await self.memory.initialize()
        
        self.alerts = AlertSystem(self.settings.alert_webhook)
        
        self.executor = ExecutionEngine(
            host=self.settings.ibkr_host,
            port=self.settings.ibkr_port,
            client_id=self.settings.ibkr_client_id
        )
        await self.executor.connect()
        
        self.monitor = MarketMonitor(self.executor.ib)
        await self.monitor.initialize()
        
        # Get current strategy from memory
        strategy = await self.memory.get_current_strategy()
        self.evaluator = StimulusEvaluator(strategy)
        
        self.thinker = ThinkingEngine(
            api_key=self.settings.anthropic_api_key
        )
        
        await self.alerts.notify_startup()
        logger.info("Autonomous agent initialized successfully")
        
    async def run(self):
        """The eternal loop - Claude's consciousness"""
        
        await self.initialize()
        
        logger.info("Starting eternal loop...")
        
        while self.running:
            try:
                await self.loop_iteration()
                
                # Brief pause (responsive, not sleeping)
                await asyncio.sleep(0.1)  # 100ms loop
                
            except Exception as e:
                logger.error("Agent loop error", error=str(e), exc_info=True)
                await self.alerts.error(f"Agent loop error: {e}")
                await asyncio.sleep(60)  # Back off on error
                
        await self.shutdown()
        
    async def loop_iteration(self):
        """Single iteration of the eternal loop"""
        
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
            await self.process_stimulus(
                stimulus, market_state, portfolio, context
            )
        
        # Check for temporal triggers
        if self.evaluator.is_session_end() and not self.session_analysis_done:
            await self.end_of_session_analysis()
            self.session_analysis_done = True
            
        if self.evaluator.is_session_start():
            self.session_analysis_done = False  # Reset for new session
            
        if self.evaluator.is_week_end() and not self.week_analysis_done:
            await self.weekly_strategic_review()
            self.week_analysis_done = True
            
        if self.evaluator.is_week_start():
            self.week_analysis_done = False  # Reset for new week
            
    async def process_stimulus(
        self, 
        stimulus: Stimulus, 
        market_state, 
        portfolio, 
        context
    ):
        """Process a single stimulus through thinking and potential action"""
        
        logger.info(
            "Processing stimulus",
            type=stimulus.type.value,
            symbol=stimulus.symbol,
            level=stimulus.level
        )
        
        if stimulus.level == "TACTICAL":
            decision = await self.thinker.tactical_think(
                stimulus=stimulus,
                market_state=market_state,
                portfolio=portfolio,
                context=context
            )
            
            # Log decision regardless of action
            await self.memory.log_decision(decision)
            
            # Execute if action required
            if decision.action not in ("HOLD", "WAIT"):
                result = await self.executor.execute(decision)
                await self.memory.update_decision_execution(
                    decision.id, result
                )
                
            # Alert human if needed
            if decision.needs_human_attention:
                await self.alerts.attention_needed(decision)
                
    async def end_of_session_analysis(self):
        """Level 2: Analytical thinking at end of trading day"""
        
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
            insights_count=len(insights.patterns_observed)
        )
        
    async def weekly_strategic_review(self):
        """Level 3: Strategic thinking at end of week"""
        
        logger.info("Starting weekly strategic review...")
        
        week_context = await self.memory.get_week_context()
        
        strategy_update = await self.thinker.strategic_think(week_context)
        
        if strategy_update.has_changes:
            await self.memory.update_strategy(strategy_update)
            
        await self.alerts.strategic_update(strategy_update)
        
        logger.info("Weekly strategic review complete")
        
    async def shutdown(self):
        """Clean shutdown"""
        
        logger.info("Shutting down autonomous agent...")
        
        self.running = False
        
        if self.executor:
            # Optionally close all positions
            # await self.executor.close_all_positions()
            await self.executor.disconnect()
            
        if self.monitor:
            await self.monitor.disconnect()
            
        if self.alerts:
            await self.alerts.notify_shutdown()
            
        logger.info("Autonomous agent shutdown complete")
        
    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False


async def main():
    """Entry point"""
    
    # Load settings
    settings = Settings()
    
    # Create agent
    agent = AutonomousAgent(settings)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, agent.handle_signal)
    signal.signal(signal.SIGTERM, agent.handle_signal)
    
    # Run forever
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 2.3: agent/thinking.py (Claude API Integration)

```python
"""
THINKING ENGINE - Claude API Integration
Name of File: agent/thinking.py
Last Updated: 2025-12-09
Purpose: Invoke Claude with open-ended prompts for deep reasoning

Key principles:
- Open-ended prompts stimulate deep reasoning
- Different models for different thinking levels
- Always capture reasoning, not just decisions
- Express uncertainty, don't hide it
"""

import json
from typing import Optional
from dataclasses import dataclass

import anthropic
import structlog

from prompts.tactical import build_tactical_prompt
from prompts.analytical import build_analytical_prompt
from prompts.strategic import build_strategic_prompt

logger = structlog.get_logger()


@dataclass
class TacticalDecision:
    """Output from tactical thinking"""
    id: Optional[int] = None
    timestamp: str = ""
    symbol: str = ""
    
    observation: str = ""
    assessment: str = ""
    confidence: float = 0.0
    confidence_reasoning: str = ""
    
    action: str = "HOLD"  # BUY, SELL, HOLD, WAIT
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    size_percent: Optional[float] = None
    reasoning: str = ""
    
    uncertainties: list = None
    would_help: list = None
    needs_human_attention: bool = False
    human_reason: Optional[str] = None
    
    # Full context for storage
    stimulus_type: str = ""
    stimulus_data: dict = None
    context_provided: dict = None
    thinking_level: str = "TACTICAL"
    
    def __post_init__(self):
        if self.uncertainties is None:
            self.uncertainties = []
        if self.would_help is None:
            self.would_help = []
        if self.stimulus_data is None:
            self.stimulus_data = {}
        if self.context_provided is None:
            self.context_provided = {}


@dataclass
class AnalyticalInsights:
    """Output from analytical thinking"""
    market_summary: str = ""
    decision_review: list = None
    patterns_observed: list = None
    calibration_adjustments: list = None
    hypotheses_to_test: list = None
    daily_summary_for_human: str = ""
    
    def __post_init__(self):
        if self.decision_review is None:
            self.decision_review = []
        if self.patterns_observed is None:
            self.patterns_observed = []
        if self.calibration_adjustments is None:
            self.calibration_adjustments = []
        if self.hypotheses_to_test is None:
            self.hypotheses_to_test = []


@dataclass
class StrategicUpdate:
    """Output from strategic thinking"""
    macro_assessment: str = ""
    regime: str = "neutral"  # risk_on, risk_off, transition
    strategy_performance_review: str = ""
    recommended_adjustments: list = None
    major_risks: list = None
    opportunities: list = None
    message_for_human: str = ""
    needs_human_decision: bool = False
    human_decision_topic: Optional[str] = None
    
    has_changes: bool = False
    new_parameters: dict = None
    rationale: str = ""
    
    def __post_init__(self):
        if self.recommended_adjustments is None:
            self.recommended_adjustments = []
        if self.major_risks is None:
            self.major_risks = []
        if self.opportunities is None:
            self.opportunities = []
        if self.new_parameters is None:
            self.new_parameters = {}


class ThinkingEngine:
    """
    Claude API Integration for Three-Level Thinking
    
    Level 1: Tactical (Sonnet) - Fast decisions
    Level 2: Analytical (Opus) - Daily learning
    Level 3: Strategic (Opus + Extended) - Weekly direction
    """
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Model configuration
        self.tactical_model = "claude-sonnet-4-20250514"
        self.analytical_model = "claude-opus-4-20250514"
        self.strategic_model = "claude-opus-4-20250514"
        
    async def tactical_think(
        self,
        stimulus,
        market_state,
        portfolio,
        context
    ) -> TacticalDecision:
        """
        Level 1: Fast tactical decisions
        Model: Sonnet (fast, efficient)
        """
        
        logger.info(
            "Tactical thinking",
            symbol=stimulus.symbol,
            stimulus_type=stimulus.type.value
        )
        
        prompt = build_tactical_prompt(
            stimulus=stimulus,
            market_state=market_state,
            portfolio=portfolio,
            context=context
        )
        
        try:
            response = self.client.messages.create(
                model=self.tactical_model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            decision = self._parse_tactical_response(
                response, stimulus, market_state, context
            )
            
            logger.info(
                "Tactical decision",
                symbol=stimulus.symbol,
                action=decision.action,
                confidence=decision.confidence
            )
            
            return decision
            
        except Exception as e:
            logger.error("Tactical thinking failed", error=str(e))
            # Return safe default
            return TacticalDecision(
                symbol=stimulus.symbol,
                action="HOLD",
                reasoning=f"Error during analysis: {e}",
                stimulus_type=stimulus.type.value,
                stimulus_data=stimulus.data
            )
            
    async def analytical_think(self, today_context) -> AnalyticalInsights:
        """
        Level 2: End of day learning
        Model: Opus (deep reasoning)
        """
        
        logger.info("Analytical thinking - end of day review")
        
        prompt = build_analytical_prompt(today_context)
        
        try:
            response = self.client.messages.create(
                model=self.analytical_model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            insights = self._parse_analytical_response(response)
            
            logger.info(
                "Analytical insights generated",
                patterns_count=len(insights.patterns_observed),
                adjustments_count=len(insights.calibration_adjustments)
            )
            
            return insights
            
        except Exception as e:
            logger.error("Analytical thinking failed", error=str(e))
            return AnalyticalInsights(
                market_summary=f"Analysis failed: {e}",
                daily_summary_for_human=f"Analysis error: {e}"
            )
            
    async def strategic_think(self, week_context) -> StrategicUpdate:
        """
        Level 3: Strategic direction
        Model: Opus with extended thinking
        """
        
        logger.info("Strategic thinking - weekly review")
        
        prompt = build_strategic_prompt(week_context)
        
        try:
            response = self.client.messages.create(
                model=self.strategic_model,
                max_tokens=8000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 5000
                },
                messages=[{"role": "user", "content": prompt}]
            )
            
            update = self._parse_strategic_response(response, week_context)
            
            logger.info(
                "Strategic update generated",
                has_changes=update.has_changes,
                risks_identified=len(update.major_risks)
            )
            
            return update
            
        except Exception as e:
            logger.error("Strategic thinking failed", error=str(e))
            return StrategicUpdate(
                macro_assessment=f"Analysis failed: {e}",
                message_for_human=f"Strategic analysis error: {e}"
            )
            
    def _parse_tactical_response(
        self, 
        response, 
        stimulus, 
        market_state, 
        context
    ) -> TacticalDecision:
        """Parse Claude's tactical response into structured decision"""
        
        content = response.content[0].text
        
        try:
            # Try to extract JSON from response
            # Handle case where Claude wraps in markdown
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content
                
            data = json.loads(json_str.strip())
            
            recommendation = data.get("recommendation", {})
            
            return TacticalDecision(
                symbol=stimulus.symbol,
                observation=data.get("observation", ""),
                assessment=data.get("assessment", ""),
                confidence=float(data.get("confidence", 0)),
                confidence_reasoning=data.get("confidence_reasoning", ""),
                action=recommendation.get("action", "HOLD"),
                entry_price=recommendation.get("entry"),
                stop_price=recommendation.get("stop"),
                target_price=recommendation.get("target"),
                size_percent=recommendation.get("size_percent"),
                reasoning=recommendation.get("reasoning", ""),
                uncertainties=data.get("uncertainties", []),
                would_help=data.get("would_help", []),
                needs_human_attention=data.get("needs_human", False),
                human_reason=data.get("human_reason"),
                stimulus_type=stimulus.type.value,
                stimulus_data=stimulus.data,
                context_provided={
                    "market_state_summary": str(market_state)[:500],
                    "strategy_version": context.strategy.get("id") if context.strategy else None
                }
            )
            
        except json.JSONDecodeError:
            # If JSON parsing fails, extract what we can
            logger.warning("Failed to parse tactical response as JSON")
            return TacticalDecision(
                symbol=stimulus.symbol,
                action="HOLD",
                reasoning=content[:1000],
                stimulus_type=stimulus.type.value,
                stimulus_data=stimulus.data
            )
            
    def _parse_analytical_response(self, response) -> AnalyticalInsights:
        """Parse Claude's analytical response"""
        
        content = response.content[0].text
        
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content
                
            data = json.loads(json_str.strip())
            
            return AnalyticalInsights(
                market_summary=data.get("market_summary", ""),
                decision_review=data.get("decision_review", []),
                patterns_observed=data.get("patterns_observed", []),
                calibration_adjustments=data.get("calibration_adjustments", []),
                hypotheses_to_test=data.get("hypotheses_to_test", []),
                daily_summary_for_human=data.get("daily_summary_for_human", "")
            )
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse analytical response as JSON")
            return AnalyticalInsights(
                market_summary=content[:500],
                daily_summary_for_human=content[:1000]
            )
            
    def _parse_strategic_response(
        self, 
        response, 
        week_context
    ) -> StrategicUpdate:
        """Parse Claude's strategic response"""
        
        # Handle extended thinking response
        content = ""
        for block in response.content:
            if hasattr(block, 'text'):
                content = block.text
                break
                
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content
                
            data = json.loads(json_str.strip())
            
            # Determine if strategy changes needed
            adjustments = data.get("recommended_adjustments", [])
            has_changes = len(adjustments) > 0
            
            # Build new parameters if changes recommended
            new_parameters = {}
            if has_changes and week_context.strategy:
                new_parameters = dict(week_context.strategy.get("parameters", {}))
                for adj in adjustments:
                    param = adj.get("parameter")
                    recommended = adj.get("recommended")
                    if param and recommended:
                        new_parameters[param] = recommended
                        
            return StrategicUpdate(
                macro_assessment=data.get("macro_assessment", ""),
                regime=data.get("regime", "neutral"),
                strategy_performance_review=data.get("strategy_performance_review", ""),
                recommended_adjustments=adjustments,
                major_risks=data.get("major_risks", []),
                opportunities=data.get("opportunities", []),
                message_for_human=data.get("message_for_human", ""),
                needs_human_decision=data.get("needs_human_decision", False),
                human_decision_topic=data.get("human_decision_topic"),
                has_changes=has_changes,
                new_parameters=new_parameters,
                rationale="; ".join([
                    adj.get("reasoning", "") 
                    for adj in adjustments
                ])
            )
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse strategic response as JSON")
            return StrategicUpdate(
                macro_assessment=content[:500],
                message_for_human=content[:1000]
            )
```

### Step 2.4: agent/memory.py (Database Interface)

```python
"""
MEMORY SYSTEM - Claude's Persistent Brain
Name of File: agent/memory.py
Last Updated: 2025-12-09
Purpose: Database interface for storing decisions, outcomes, patterns, insights

Claude can't remember between invocations,
so we give it memory through the database.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass, field

import asyncpg
import structlog

logger = structlog.get_logger()


@dataclass
class Context:
    """Context provided to Claude for decision-making"""
    decisions: List = field(default_factory=list)
    patterns: List = field(default_factory=list)
    strategy: Optional[dict] = None
    insights: List = field(default_factory=list)


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
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Initialize database connection pool"""
        logger.info("Initializing memory system...")
        
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10
        )
        
        logger.info("Memory system initialized")
        
    async def log_decision(self, decision) -> int:
        """Store a decision with full reasoning"""
        
        async with self.pool.acquire() as conn:
            decision_id = await conn.fetchval("""
                INSERT INTO decisions (
                    timestamp, market, symbol, stimulus_type, stimulus_data,
                    context_provided, reasoning, confidence, action,
                    entry_price, stop_price, target_price, position_size,
                    uncertainties, additional_info_wanted, thinking_level
                ) VALUES (
                    NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                )
                RETURNING id
            """,
                "HKEX",  # TODO: Get from decision
                decision.symbol,
                decision.stimulus_type,
                json.dumps(decision.stimulus_data),
                json.dumps(decision.context_provided),
                decision.reasoning,
                decision.confidence,
                decision.action,
                decision.entry_price,
                decision.stop_price,
                decision.target_price,
                decision.size_percent,
                decision.uncertainties,
                decision.would_help,
                decision.thinking_level
            )
            
            logger.info(
                "Decision logged",
                decision_id=decision_id,
                symbol=decision.symbol,
                action=decision.action
            )
            
            return decision_id
            
    async def update_decision_execution(
        self, 
        decision_id: int, 
        execution_result
    ):
        """Update decision with execution results"""
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE decisions
                SET executed = true,
                    execution_price = $2,
                    execution_time = NOW(),
                    position_id = $3
                WHERE id = $1
            """, decision_id, 
                execution_result.fill_price,
                execution_result.position_id
            )
            
    async def get_recent_context(self, days: int = 7) -> Context:
        """Get recent decisions and outcomes for context"""
        
        async with self.pool.acquire() as conn:
            # Recent decisions with outcomes
            decisions = await conn.fetch("""
                SELECT 
                    d.id, d.timestamp, d.symbol, d.action, 
                    d.confidence, d.reasoning, d.uncertainties,
                    p.realized_pnl, p.realized_pnl_pct, 
                    p.status as position_status, p.exit_reason
                FROM decisions d
                LEFT JOIN positions p ON d.position_id = p.id
                WHERE d.timestamp > NOW() - INTERVAL '%s days'
                ORDER BY d.timestamp DESC
                LIMIT 50
            """ % days)
            
            # Active patterns
            patterns = await conn.fetch("""
                SELECT 
                    id, name, description, 
                    identification_rules, conditions_favorable,
                    times_traded, win_count, loss_count, total_pnl,
                    avg_confidence_when_win, avg_confidence_when_loss
                FROM patterns 
                WHERE active = true
                ORDER BY total_pnl DESC
            """)
            
            # Current strategy
            strategy = await conn.fetchrow("""
                SELECT id, parameters, rationale, effective_from
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
                insights=[dict(i) for i in insights]
            )
            
    async def get_today_context(self) -> Context:
        """Get today's decisions for end-of-day analysis"""
        
        async with self.pool.acquire() as conn:
            decisions = await conn.fetch("""
                SELECT 
                    d.*, 
                    p.realized_pnl, p.realized_pnl_pct,
                    p.max_favorable, p.max_adverse,
                    p.exit_reason, p.status as position_status
                FROM decisions d
                LEFT JOIN positions p ON d.position_id = p.id
                WHERE DATE(d.timestamp) = CURRENT_DATE
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
                strategy=dict(strategy) if strategy else None
            )
            
    async def get_week_context(self) -> Context:
        """Get this week's data for strategic review"""
        
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
                WHERE closed_at > NOW() - INTERVAL '7 days'
                AND status = 'CLOSED'
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
                decisions=[dict(performance)] if performance else [],
                patterns=[],  # Not needed for strategic
                strategy=dict(strategy) if strategy else None,
                insights=[dict(i) for i in insights]
            )
            
    async def get_current_strategy(self) -> dict:
        """Get current active strategy parameters"""
        
        async with self.pool.acquire() as conn:
            strategy = await conn.fetchrow("""
                SELECT parameters
                FROM strategy_versions
                WHERE effective_until IS NULL
                ORDER BY effective_from DESC
                LIMIT 1
            """)
            
            if strategy:
                return json.loads(strategy['parameters'])
            else:
                # Return default strategy
                return {
                    "risk_appetite": "conservative",
                    "max_position_size_pct": 5,
                    "max_daily_loss_pct": 2,
                    "max_open_positions": 3,
                    "volume_threshold": 2.0,
                    "price_threshold": 2.0
                }
                
    async def store_insights(self, insights):
        """Store analytical insights"""
        
        async with self.pool.acquire() as conn:
            # Store pattern observations
            for pattern in insights.patterns_observed:
                await conn.execute("""
                    INSERT INTO insights (
                        thinking_level, insight_type, insight_text,
                        supporting_evidence
                    ) VALUES ('ANALYTICAL', 'PATTERN', $1, $2)
                """, 
                    pattern.get("pattern", ""),
                    json.dumps(pattern)
                )
                
            # Store calibration insights
            for calibration in insights.calibration_adjustments:
                await conn.execute("""
                    INSERT INTO insights (
                        thinking_level, insight_type, insight_text,
                        supporting_evidence
                    ) VALUES ('ANALYTICAL', 'CALIBRATION', $1, $2)
                """,
                    calibration.get("reasoning", ""),
                    json.dumps(calibration)
                )
                
            logger.info(
                "Insights stored",
                patterns=len(insights.patterns_observed),
                calibrations=len(insights.calibration_adjustments)
            )
            
    async def update_strategy(self, strategy_update):
        """Update strategy with new parameters"""
        
        async with self.pool.acquire() as conn:
            # Close current strategy
            await conn.execute("""
                UPDATE strategy_versions
                SET effective_until = NOW()
                WHERE effective_until IS NULL
            """)
            
            # Insert new strategy
            await conn.execute("""
                INSERT INTO strategy_versions (
                    parameters, rationale, changed_by
                ) VALUES ($1, $2, 'STRATEGIC')
            """,
                json.dumps(strategy_update.new_parameters),
                strategy_update.rationale
            )
            
            logger.info("Strategy updated", rationale=strategy_update.rationale[:100])
```

---

## PHASE 3: PROMPTS

### Step 3.1: Create Prompts Package

```bash
mkdir -p prompts
touch prompts/__init__.py
```

### Step 3.2: prompts/tactical.py

See CLAUDE.md for full prompt templates. Key structure:

```python
"""
TACTICAL PROMPTS - Level 1 Thinking
Name of File: prompts/tactical.py
Last Updated: 2025-12-09
Purpose: Open-ended prompts for fast tactical decisions
"""

def build_tactical_prompt(stimulus, market_state, portfolio, context) -> str:
    """
    Build tactical prompt for Claude
    
    Key principle: Ask OPEN questions, don't dictate answers
    
    NOT: "Is RSI > 70?"
    BUT: "What do you observe? What's your assessment?"
    """
    
    return f"""
You are an autonomous trading agent. A stimulus has triggered your attention.

CURRENT MARKET STATE:
{_format_market_state(market_state)}

YOUR PORTFOLIO:
{_format_portfolio(portfolio)}

RECENT CONTEXT (your recent decisions and their outcomes):
{_format_context(context)}

CURRENT STRATEGY PARAMETERS:
{_format_strategy(context.strategy)}

STIMULUS THAT TRIGGERED THIS THOUGHT:
Type: {stimulus.type.value}
Symbol: {stimulus.symbol}
Data: {stimulus.data}
Urgency: {stimulus.urgency}

---

Please think through this situation:

1. WHAT DO YOU OBSERVE?
   - What's happening with price, volume, pattern?
   - How does this compare to patterns that have worked before?
   - What's similar to past situations? What's different?

2. WHAT IS YOUR ASSESSMENT?
   - Is this an opportunity? Why or why not?
   - What's your confidence level (0-100%)? Why that specific level?
   - What information would increase your confidence?
   - What could prove you wrong?

3. WHAT DO YOU RECOMMEND?
   - Action: BUY / SELL / HOLD / WAIT
   - If acting: Entry price, stop loss, target, position size
   - If waiting: What signal are you waiting for?

4. WHAT ARE YOU UNCERTAIN ABOUT?
   - What don't you know that matters?
   - What risks concern you most?
   - Is there anything that needs human attention?

Think step by step. Show your reasoning. Express uncertainty honestly.

Respond in JSON format:
{{
    "observation": "What you see...",
    "assessment": "Your analysis...",
    "confidence": 65,
    "confidence_reasoning": "Why this confidence level...",
    "recommendation": {{
        "action": "BUY|SELL|HOLD|WAIT",
        "entry": 150.00,
        "stop": 148.00,
        "target": 155.00,
        "size_percent": 5,
        "reasoning": "Why this action..."
    }},
    "uncertainties": ["List of uncertainties..."],
    "would_help": ["Information that would help..."],
    "needs_human": false,
    "human_reason": null
}}
"""


def _format_market_state(market_state) -> str:
    """Format market state for prompt"""
    if not market_state:
        return "No market data available"
    # Implementation depends on market_state structure
    return str(market_state)


def _format_portfolio(portfolio) -> str:
    """Format portfolio for prompt"""
    if not portfolio:
        return "No open positions"
    # Implementation depends on portfolio structure
    return str(portfolio)


def _format_context(context) -> str:
    """Format recent context for prompt"""
    if not context or not context.decisions:
        return "No recent decisions"
        
    lines = []
    for d in context.decisions[:10]:  # Last 10 decisions
        outcome = "WIN" if d.get('realized_pnl', 0) > 0 else "LOSS" if d.get('realized_pnl', 0) < 0 else "OPEN"
        lines.append(
            f"- {d['symbol']}: {d['action']} @ {d['confidence']}% confidence → {outcome}"
        )
    return "\n".join(lines)


def _format_strategy(strategy) -> str:
    """Format strategy parameters for prompt"""
    if not strategy:
        return "Default conservative strategy"
        
    params = strategy.get('parameters', strategy)
    return f"""
Risk Appetite: {params.get('risk_appetite', 'conservative')}
Max Position Size: {params.get('max_position_size_pct', 5)}%
Max Daily Loss: {params.get('max_daily_loss_pct', 2)}%
Volume Threshold: {params.get('volume_threshold', 2.0)}x
"""
```

### Step 3.3: prompts/analytical.py and prompts/strategic.py

Follow same pattern - see CLAUDE.md for full templates.

---

## PHASE 4: SUPPORTING MODULES

### Step 4.1: agent/monitor.py

```python
"""
MARKET MONITOR - Real-time Market Observation
Name of File: agent/monitor.py
Last Updated: 2025-12-09
Purpose: Continuous market monitoring via IBKR
"""

# Implementation for IBKR market data connection
# See ib_insync documentation
```

### Step 4.2: agent/stimulus.py

```python
"""
STIMULUS EVALUATOR - What Deserves Thought?
Name of File: agent/stimulus.py
Last Updated: 2025-12-09
Purpose: Evaluate market conditions and generate stimuli
"""

# Implementation for stimulus detection
# See CLAUDE.md for stimulus types and thresholds
```

### Step 4.3: agent/execution.py (COMPLETE - Using brokers/ibkr.py)

**STATUS: ✅ IMPLEMENTED**

The execution engine is implemented in `brokers/ibkr.py` v2.1.0 with the following features:
- Multi-exchange support (HKEX + US)
- Auto-detect exchange based on symbol format
- HKEX tick size rounding (11 tiers)
- Bracket orders with stop loss/take profit
- Position and order management

**Connection example:**
```python
from brokers.ibkr import IBKRClient

# Initialize and connect
client = IBKRClient(port=4000, client_id=1)
client.connect()

# Execute trade
result = client.execute_trade(
    symbol='AAPL',  # Auto-detects US (SMART) vs HKEX (SEHK)
    side='buy',
    quantity=1,
    order_type='limit',
    limit_price=150.00,
    stop_loss=145.00,
    take_profit=160.00,
    reason='Pattern breakout'
)

# Get portfolio
portfolio = client.get_portfolio()
positions = client.get_positions()

# Cleanup
client.disconnect()
```

**Test command:**
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
IBKR_PORT=4000 python3 scripts/test_ibga_connection.py
```

See `ibga/SETUP-STATUS.md` for full operational status.

### Step 4.4: agent/alerts.py

```python
"""
ALERT SYSTEM - Human Notifications
Name of File: agent/alerts.py
Last Updated: 2025-12-09
Purpose: Send alerts and summaries to human
"""

# Implementation for Discord/Telegram/Email alerts
```

### Step 4.5: config/settings.py

```python
"""
SETTINGS - Application Configuration
Name of File: config/settings.py
Last Updated: 2025-12-09
Purpose: Load and validate configuration
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str
    
    # Database
    database_url: str
    
    # IBKR
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 4002
    ibkr_client_id: int = 1
    
    # Alerts
    alert_webhook: str = ""
    
    # Logging
    log_level: str = "INFO"
    
    # Environment
    environment: str = "paper"
    
    class Config:
        env_file = ".env"
```

---

## PHASE 5: TESTING & VALIDATION

### Step 5.1: Validate Database Connection

```python
# tests/test_memory.py
import asyncio
from agent.memory import MemorySystem

async def test_connection():
    memory = MemorySystem("postgresql://...")
    await memory.initialize()
    context = await memory.get_recent_context()
    print(f"Connected. Found {len(context.decisions)} recent decisions.")
```

### Step 5.2: Validate Claude API

```python
# tests/test_thinking.py
from agent.thinking import ThinkingEngine

def test_tactical():
    engine = ThinkingEngine(api_key="...")
    # Create mock stimulus and test
```

### Step 5.3: Validate IBKR Connection

```python
# tests/test_execution.py
from agent.execution import ExecutionEngine

async def test_connection():
    executor = ExecutionEngine(host="127.0.0.1", port=4002)
    await executor.connect()
    portfolio = await executor.get_portfolio()
    print(f"Connected. Portfolio value: {portfolio.total_value}")
```

---

## PHASE 6: DEPLOYMENT

### Step 6.1: Build Docker Image

```bash
docker build -t catalyst-agent:latest .
```

### Step 6.2: Start Services

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your values

# Start everything
docker-compose up -d

# Watch logs
docker-compose logs -f agent
```

### Step 6.3: Validate Running

```bash
# Check health
curl http://localhost:8080/health

# Check logs for "Initializing autonomous agent..."
docker-compose logs agent | head -50
```

---

## CHECKLIST

### Phase 0: Discovery
- [ ] Inventory existing files
- [ ] Compare dates, identify newer versions
- [ ] Create project structure

### Phase 1: Foundation
- [ ] CLAUDE.md (check existing, merge if needed)
- [ ] schema.sql (check existing, migrate if data exists)
- [ ] Docker files
- [ ] requirements.txt

### Phase 2: Core Agent
- [ ] agent/__init__.py
- [ ] agent/main.py
- [ ] agent/thinking.py
- [ ] agent/memory.py
- [ ] agent/monitor.py
- [ ] agent/stimulus.py
- [ ] agent/execution.py
- [ ] agent/alerts.py

### Phase 3: Prompts
- [ ] prompts/__init__.py
- [ ] prompts/tactical.py
- [ ] prompts/analytical.py
- [ ] prompts/strategic.py
- [ ] prompts/metacognitive.py

### Phase 4: Supporting
- [ ] config/settings.py
- [ ] sources/market_data.py
- [ ] tools/*.py
- [x] brokers/ibkr.py (v2.1.0 - COMPLETE, tested 2025-12-10)

### Phase 5: Testing
- [ ] Test database connection
- [ ] Test Claude API
- [x] Test IBKR connection (COMPLETE - Paper trading verified 2025-12-10)
- [ ] End-to-end test

### Phase 6: Deployment
- [ ] Build Docker image
- [ ] Configure .env
- [ ] Start services
- [ ] Validate running

---

## REMEMBER

1. **Check dates, not versions** - versions are misaligned
2. **Never lose existing work** - compare before replacing
3. **Merge when dates are close** - keep best of both
4. **Test each phase** - don't proceed until working
5. **Log everything** - debugging requires history

---

**END OF IMPLEMENTATION GUIDE**

*"Build it right. Build it once. Let it learn."* 🚀🤖📈
