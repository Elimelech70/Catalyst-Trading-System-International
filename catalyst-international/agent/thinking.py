"""
Name of Application: Catalyst Trading System
Name of file: agent/thinking.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Invoke Claude with open-ended prompts for deep reasoning

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Three-level thinking: Tactical, Analytical, Strategic
- Open-ended prompts that stimulate reasoning
- Structured response parsing

Description:
This module handles all Claude API interactions for the three levels of thinking:
- Tactical (Sonnet): Fast real-time decisions
- Analytical (Opus): End-of-day learning and pattern recognition
- Strategic (Opus + Extended): Weekly direction and strategy evolution

Key principles:
- Open-ended prompts stimulate deep reasoning
- Different models for different thinking levels
- Always capture reasoning, not just decisions
- Express uncertainty, don't hide it
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

import anthropic
import structlog

from prompts.tactical import build_tactical_prompt
from prompts.analytical import build_analytical_prompt
from prompts.strategic import build_strategic_prompt

logger = structlog.get_logger()

HK_TZ = ZoneInfo("Asia/Hong_Kong")


@dataclass
class TacticalDecision:
    """Output from tactical thinking."""

    id: Optional[int] = None
    timestamp: str = ""
    symbol: str = ""

    # Observation and assessment
    observation: str = ""
    assessment: str = ""
    confidence: float = 0.0
    confidence_reasoning: str = ""

    # The decision
    action: str = "HOLD"  # BUY, SELL, HOLD, WAIT, SKIP, CLOSE
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    size_percent: Optional[float] = None
    reasoning: str = ""

    # Uncertainty and learning
    uncertainties: list = field(default_factory=list)
    would_help: list = field(default_factory=list)
    needs_human_attention: bool = False
    human_reason: Optional[str] = None

    # Context for storage
    stimulus_type: str = ""
    stimulus_data: dict = field(default_factory=dict)
    context_provided: dict = field(default_factory=dict)
    thinking_level: str = "TACTICAL"


@dataclass
class AnalyticalInsights:
    """Output from analytical thinking."""

    market_summary: str = ""
    decision_review: list = field(default_factory=list)
    patterns_observed: list = field(default_factory=list)
    calibration_adjustments: list = field(default_factory=list)
    hypotheses_to_test: list = field(default_factory=list)
    daily_summary_for_human: str = ""


@dataclass
class StrategicUpdate:
    """Output from strategic thinking."""

    macro_assessment: str = ""
    regime: str = "neutral"  # risk_on, risk_off, transition
    strategy_performance_review: str = ""
    recommended_adjustments: list = field(default_factory=list)
    major_risks: list = field(default_factory=list)
    opportunities: list = field(default_factory=list)
    message_for_human: str = ""
    needs_human_decision: bool = False
    human_decision_topic: Optional[str] = None

    has_changes: bool = False
    new_parameters: dict = field(default_factory=dict)
    rationale: str = ""


class ThinkingEngine:
    """
    Claude API Integration for Three-Level Thinking

    Level 1: Tactical (Sonnet) - Fast decisions
    Level 2: Analytical (Opus) - Daily learning
    Level 3: Strategic (Opus + Extended) - Weekly direction
    """

    def __init__(
        self,
        api_key: str,
        tactical_model: str = "claude-sonnet-4-20250514",
        analytical_model: str = "claude-sonnet-4-20250514",
        strategic_model: str = "claude-sonnet-4-20250514",
    ):
        """Initialize thinking engine.

        Args:
            api_key: Anthropic API key
            tactical_model: Model for tactical decisions
            analytical_model: Model for analytical thinking
            strategic_model: Model for strategic thinking
        """
        self.client = anthropic.Anthropic(api_key=api_key)

        self.tactical_model = tactical_model
        self.analytical_model = analytical_model
        self.strategic_model = strategic_model

    async def tactical_think(
        self,
        stimulus,
        market_state,
        portfolio,
        context,
    ) -> TacticalDecision:
        """
        Level 1: Fast tactical decisions
        Model: Sonnet (fast, efficient)
        """
        logger.info(
            "Tactical thinking",
            symbol=stimulus.symbol,
            stimulus_type=stimulus.type.value,
        )

        prompt = build_tactical_prompt(
            stimulus=stimulus,
            market_state=market_state,
            portfolio=portfolio,
            context=context,
        )

        try:
            response = self.client.messages.create(
                model=self.tactical_model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            decision = self._parse_tactical_response(
                response, stimulus, market_state, context
            )

            logger.info(
                "Tactical decision",
                symbol=stimulus.symbol,
                action=decision.action,
                confidence=decision.confidence,
            )

            return decision

        except Exception as e:
            logger.error("Tactical thinking failed", error=str(e))
            # Return safe default
            return TacticalDecision(
                symbol=stimulus.symbol,
                timestamp=datetime.now(HK_TZ).isoformat(),
                action="HOLD",
                reasoning=f"Error during analysis: {e}",
                stimulus_type=stimulus.type.value,
                stimulus_data=stimulus.data,
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
                messages=[{"role": "user", "content": prompt}],
            )

            insights = self._parse_analytical_response(response)

            logger.info(
                "Analytical insights generated",
                patterns_count=len(insights.patterns_observed),
                adjustments_count=len(insights.calibration_adjustments),
            )

            return insights

        except Exception as e:
            logger.error("Analytical thinking failed", error=str(e))
            return AnalyticalInsights(
                market_summary=f"Analysis failed: {e}",
                daily_summary_for_human=f"Analysis error: {e}",
            )

    async def strategic_think(self, week_context) -> StrategicUpdate:
        """
        Level 3: Strategic direction
        Model: Opus with extended thinking
        """
        logger.info("Strategic thinking - weekly review")

        prompt = build_strategic_prompt(week_context)

        try:
            # Use extended thinking for strategic decisions
            response = self.client.messages.create(
                model=self.strategic_model,
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 10000,
                },
                messages=[{"role": "user", "content": prompt}],
            )

            update = self._parse_strategic_response(response, week_context)

            logger.info(
                "Strategic update generated",
                has_changes=update.has_changes,
                risks_identified=len(update.major_risks),
            )

            return update

        except Exception as e:
            logger.error("Strategic thinking failed", error=str(e))
            return StrategicUpdate(
                macro_assessment=f"Analysis failed: {e}",
                message_for_human=f"Strategic analysis error: {e}",
            )

    def _parse_tactical_response(
        self,
        response,
        stimulus,
        market_state,
        context,
    ) -> TacticalDecision:
        """Parse Claude's tactical response into structured decision."""
        content = response.content[0].text

        try:
            # Extract JSON from response
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            recommendation = data.get("recommendation", {})

            return TacticalDecision(
                timestamp=datetime.now(HK_TZ).isoformat(),
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
                    "strategy_version": (
                        context.strategy.get("id") if context.strategy else None
                    ),
                },
            )

        except json.JSONDecodeError:
            logger.warning("Failed to parse tactical response as JSON")
            return TacticalDecision(
                timestamp=datetime.now(HK_TZ).isoformat(),
                symbol=stimulus.symbol,
                action="HOLD",
                reasoning=content[:1000],
                stimulus_type=stimulus.type.value,
                stimulus_data=stimulus.data,
            )

    def _parse_analytical_response(self, response) -> AnalyticalInsights:
        """Parse Claude's analytical response."""
        content = response.content[0].text

        try:
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            return AnalyticalInsights(
                market_summary=data.get("market_summary", ""),
                decision_review=data.get("decision_review", []),
                patterns_observed=data.get("patterns_observed", []),
                calibration_adjustments=data.get("calibration_adjustments", []),
                hypotheses_to_test=data.get("hypotheses_to_test", []),
                daily_summary_for_human=data.get("daily_summary_for_human", ""),
            )

        except json.JSONDecodeError:
            logger.warning("Failed to parse analytical response as JSON")
            return AnalyticalInsights(
                market_summary=content[:500],
                daily_summary_for_human=content[:1000],
            )

    def _parse_strategic_response(
        self,
        response,
        week_context,
    ) -> StrategicUpdate:
        """Parse Claude's strategic response."""
        # Handle extended thinking response
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content = block.text
                break

        try:
            json_str = self._extract_json(content)
            data = json.loads(json_str)

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
                    if param and recommended is not None:
                        new_parameters[param] = recommended

            return StrategicUpdate(
                macro_assessment=data.get("macro_assessment", ""),
                regime=data.get("regime", "neutral"),
                strategy_performance_review=data.get(
                    "strategy_performance_review", ""
                ),
                recommended_adjustments=adjustments,
                major_risks=data.get("major_risks", []),
                opportunities=data.get("opportunities", []),
                message_for_human=data.get("message_for_human", ""),
                needs_human_decision=data.get("needs_human_decision", False),
                human_decision_topic=data.get("human_decision_topic"),
                has_changes=has_changes,
                new_parameters=new_parameters,
                rationale="; ".join(
                    [adj.get("reasoning", "") for adj in adjustments]
                ),
            )

        except json.JSONDecodeError:
            logger.warning("Failed to parse strategic response as JSON")
            return StrategicUpdate(
                macro_assessment=content[:500],
                message_for_human=content[:1000],
            )

    def _extract_json(self, content: str) -> str:
        """Extract JSON from Claude's response."""
        # Handle markdown code blocks
        if "```json" in content:
            return content.split("```json")[1].split("```")[0]
        elif "```" in content:
            return content.split("```")[1].split("```")[0]
        else:
            # Try to find JSON object
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return content[start:end]
            return content
