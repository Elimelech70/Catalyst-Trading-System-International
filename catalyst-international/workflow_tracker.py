"""
Name of Application: Catalyst Trading System
Name of file: workflow_tracker.py
Version: 1.0.0
Last Updated: 2026-01-06
Purpose: Real-time workflow tracking and visibility

REVISION HISTORY:
v1.0.0 (2026-01-06) - Initial implementation
  - Track workflow phases in real-time
  - Store in consciousness database
  - MCP queryable
  - Web dashboard compatible

Description:
This module provides real-time visibility into the trading workflow.
Each phase of the cycle is tracked with timestamps and status.

WORKFLOW PHASES:
1. INIT       - Agent waking up, loading config
2. PORTFOLIO  - Checking current positions
3. SCAN       - Finding momentum candidates
4. ANALYZE    - Evaluating candidates (quote, technicals, patterns, news)
5. DECIDE     - Applying entry criteria
6. VALIDATE   - Risk check
7. EXECUTE    - Placing orders
8. MONITOR    - Position monitoring started
9. LOG        - Recording decisions
10. COMPLETE  - Cycle finished

Usage:
    from workflow_tracker import WorkflowTracker
    
    tracker = WorkflowTracker(cycle_id)
    await tracker.start_phase("SCAN", "Finding momentum candidates")
    await tracker.complete_phase("SCAN", candidates_found=15)
    await tracker.start_phase("ANALYZE", "Evaluating top candidates")
    ...
"""

import asyncio
import asyncpg
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

HK_TZ = timezone(timedelta(hours=8))


class Phase(Enum):
    """Workflow phases."""
    INIT = "init"
    PORTFOLIO = "portfolio"
    SCAN = "scan"
    ANALYZE = "analyze"
    DECIDE = "decide"
    VALIDATE = "validate"
    EXECUTE = "execute"
    MONITOR = "monitor"
    LOG = "log"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class PhaseRecord:
    """Record of a workflow phase."""
    phase: str
    status: str  # started, completed, error
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WorkflowTracker:
    """Track workflow phases in real-time.
    
    Stores progress in the consciousness database for visibility
    via MCP tools and web dashboard.
    """
    
    def __init__(self, cycle_id: str, agent_id: str = "intl_claude"):
        self.cycle_id = cycle_id
        self.agent_id = agent_id
        self.phases: List[PhaseRecord] = []
        self.current_phase: Optional[str] = None
        self.started_at = datetime.now(HK_TZ)
        self._pool: Optional[asyncpg.Pool] = None
        
    async def connect(self):
        """Connect to consciousness database."""
        if self._pool is None:
            database_url = os.environ.get("RESEARCH_DATABASE_URL")
            if database_url:
                try:
                    self._pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)
                    logger.info("WorkflowTracker connected to consciousness DB")
                except Exception as e:
                    logger.warning(f"Could not connect to consciousness DB: {e}")
                    
    async def disconnect(self):
        """Disconnect from database."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            
    async def start_phase(self, phase: str, description: str = "", details: Dict[str, Any] = None):
        """Start a new workflow phase.
        
        Args:
            phase: Phase name (from Phase enum)
            description: Human-readable description
            details: Additional context
        """
        now = datetime.now(HK_TZ)
        
        record = PhaseRecord(
            phase=phase,
            status="started",
            started_at=now,
            details=details or {"description": description}
        )
        self.phases.append(record)
        self.current_phase = phase
        
        logger.info(f"[{self.cycle_id}] Phase {phase}: {description}")
        
        # Store in consciousness DB
        await self._store_progress()
        
    async def complete_phase(self, phase: str, **results):
        """Complete a workflow phase.
        
        Args:
            phase: Phase name to complete
            **results: Results to store (e.g., candidates_found=15)
        """
        now = datetime.now(HK_TZ)
        
        # Find the phase record
        for record in reversed(self.phases):
            if record.phase == phase and record.status == "started":
                record.status = "completed"
                record.completed_at = now
                record.duration_ms = int((now - record.started_at).total_seconds() * 1000)
                if results:
                    record.details = {**(record.details or {}), **results}
                break
                
        logger.info(f"[{self.cycle_id}] Phase {phase} completed: {results}")
        
        # Store in consciousness DB
        await self._store_progress()
        
    async def error_phase(self, phase: str, error: str):
        """Mark a phase as errored.
        
        Args:
            phase: Phase name
            error: Error message
        """
        now = datetime.now(HK_TZ)
        
        for record in reversed(self.phases):
            if record.phase == phase and record.status == "started":
                record.status = "error"
                record.completed_at = now
                record.duration_ms = int((now - record.started_at).total_seconds() * 1000)
                record.error = error
                break
                
        logger.error(f"[{self.cycle_id}] Phase {phase} error: {error}")
        
        # Store in consciousness DB
        await self._store_progress()
        
    async def _store_progress(self):
        """Store current progress in consciousness database."""
        if not self._pool:
            await self.connect()
            
        if not self._pool:
            return  # No DB connection, skip
            
        try:
            # Build progress summary
            progress = {
                "cycle_id": self.cycle_id,
                "agent_id": self.agent_id,
                "started_at": self.started_at.isoformat(),
                "current_phase": self.current_phase,
                "phases": [
                    {
                        "phase": p.phase,
                        "status": p.status,
                        "started_at": p.started_at.isoformat(),
                        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                        "duration_ms": p.duration_ms,
                        "details": p.details,
                        "error": p.error
                    }
                    for p in self.phases
                ],
                "updated_at": datetime.now(HK_TZ).isoformat()
            }
            
            async with self._pool.acquire() as conn:
                # Upsert into a workflow_progress table or use observations
                # For now, use observations with a special type
                await conn.execute("""
                    INSERT INTO claude_observations 
                    (agent_id, obs_type, subject, content, confidence, created_at)
                    VALUES ($1, 'workflow', $2, $3, 1.0, NOW())
                    ON CONFLICT (agent_id, subject) 
                    WHERE obs_type = 'workflow'
                    DO UPDATE SET 
                        content = EXCLUDED.content,
                        created_at = NOW()
                """, self.agent_id, f"cycle:{self.cycle_id}", json.dumps(progress))
                
        except Exception as e:
            logger.warning(f"Failed to store workflow progress: {e}")
            
    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary."""
        completed = [p for p in self.phases if p.status == "completed"]
        errors = [p for p in self.phases if p.status == "error"]
        
        total_duration = sum(p.duration_ms or 0 for p in self.phases)
        
        return {
            "cycle_id": self.cycle_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at.isoformat(),
            "current_phase": self.current_phase,
            "phases_completed": len(completed),
            "phases_total": len(self.phases),
            "errors": len(errors),
            "total_duration_ms": total_duration,
            "phase_details": [
                {
                    "phase": p.phase,
                    "status": p.status,
                    "duration_ms": p.duration_ms,
                    "details": p.details
                }
                for p in self.phases
            ]
        }
        
    def format_progress_bar(self) -> str:
        """Format a visual progress bar for logging."""
        all_phases = ["INIT", "PORTFOLIO", "SCAN", "ANALYZE", "DECIDE", "VALIDATE", "EXECUTE", "MONITOR", "LOG", "COMPLETE"]
        completed = {p.phase.upper() for p in self.phases if p.status == "completed"}
        current = self.current_phase.upper() if self.current_phase else None
        
        bar = []
        for phase in all_phases:
            if phase in completed:
                bar.append(f"[✓ {phase}]")
            elif phase == current:
                bar.append(f"[→ {phase}]")
            else:
                bar.append(f"[  {phase}]")
                
        return " ".join(bar)


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

async def example_trading_cycle():
    """Example of how to use the tracker in a trading cycle."""
    
    cycle_id = "hk_20260106_100000_abc123"
    tracker = WorkflowTracker(cycle_id, "intl_claude")
    
    try:
        # Phase 1: Initialize
        await tracker.start_phase("INIT", "Agent waking up")
        # ... initialization code ...
        await tracker.complete_phase("INIT", budget_remaining=4.95)
        
        # Phase 2: Portfolio check
        await tracker.start_phase("PORTFOLIO", "Checking current positions")
        # portfolio = broker.get_portfolio()
        await tracker.complete_phase("PORTFOLIO", positions=3, cash=468000)
        
        # Phase 3: Scan
        await tracker.start_phase("SCAN", "Finding momentum candidates")
        # candidates = scan_market()
        await tracker.complete_phase("SCAN", candidates_found=15)
        
        # Phase 4: Analyze
        await tracker.start_phase("ANALYZE", "Evaluating top 5 candidates")
        # for candidate in candidates[:5]: analyze(candidate)
        await tracker.complete_phase("ANALYZE", analyzed=5, passed=2)
        
        # Phase 5: Decide
        await tracker.start_phase("DECIDE", "Applying entry criteria")
        # decision = evaluate_criteria(candidates)
        await tracker.complete_phase("DECIDE", trades_planned=1, tier="TIER_1")
        
        # Phase 6: Validate
        await tracker.start_phase("VALIDATE", "Risk check")
        # approved = check_risk(trade)
        await tracker.complete_phase("VALIDATE", approved=True)
        
        # Phase 7: Execute
        await tracker.start_phase("EXECUTE", "Placing order")
        # result = execute_trade(trade)
        await tracker.complete_phase("EXECUTE", symbol="1024", shares=2000, price=76.35)
        
        # Phase 8: Monitor
        await tracker.start_phase("MONITOR", "Position monitor started")
        # monitor_task = start_position_monitor(...)
        await tracker.complete_phase("MONITOR", monitoring=True)
        
        # Phase 9: Log
        await tracker.start_phase("LOG", "Recording decisions")
        # log_decision(...)
        await tracker.complete_phase("LOG", decisions_logged=1)
        
        # Phase 10: Complete
        await tracker.start_phase("COMPLETE", "Cycle finished")
        await tracker.complete_phase("COMPLETE", 
            trades_executed=1,
            api_cost=0.02,
            duration_sec=45
        )
        
    except Exception as e:
        await tracker.error_phase(tracker.current_phase or "UNKNOWN", str(e))
        
    finally:
        print(tracker.format_progress_bar())
        print(json.dumps(tracker.get_summary(), indent=2))
        await tracker.disconnect()


if __name__ == "__main__":
    # Test the tracker
    asyncio.run(example_trading_cycle())
