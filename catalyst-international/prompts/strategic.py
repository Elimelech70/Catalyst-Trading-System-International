"""
Name of Application: Catalyst Trading System
Name of file: prompts/strategic.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Prompts for weekly strategic thinking

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Weekly strategic review prompts
- Strategy evolution recommendations
- Risk and opportunity assessment

Description:
This module builds prompts for Level 3 (Strategic) thinking.
Used at the end of each trading week to:
- Assess macro conditions
- Review strategy performance
- Recommend parameter adjustments
- Identify major risks and opportunities
"""

from typing import Any


def build_strategic_prompt(context: Any) -> str:
    """Build strategic prompt for weekly review.

    Args:
        context: Week's context including performance and insights

    Returns:
        Formatted prompt string
    """
    return f"""You are an autonomous trading agent performing your weekly strategic review.
Step back from daily operations and think about the bigger picture.

## THIS WEEK'S PERFORMANCE
{_format_performance(context)}

## RECENT INSIGHTS
{_format_insights(context)}

## CURRENT STRATEGY
{_format_strategy(context)}

## STRATEGY HISTORY
{_format_strategy_history(context)}

---

Please think strategically about the coming week:

## 1. MACRO ASSESSMENT
- What is the current market regime?
- Are we in risk-on, risk-off, or transition?
- What macro factors are driving price action?
- What changed from last week?

## 2. STRATEGY PERFORMANCE REVIEW
- How did our current strategy perform this week?
- Which parameters worked well?
- Which parameters need adjustment?
- Are we taking appropriate risk for the conditions?

## 3. RECOMMENDED ADJUSTMENTS
For each parameter you want to change:
- What is the current value?
- What do you recommend?
- Why this specific change?
- What outcome do you expect?

Only recommend changes if there's clear evidence.
Don't change things that are working.

## 4. MAJOR RISKS
- What risks should we be watching?
- What events could hurt our positions?
- What market conditions concern you?

## 5. OPPORTUNITIES
- What opportunities do you see for next week?
- Are there sectors or themes to focus on?
- What setups should we look for?

## 6. MESSAGE FOR HUMAN
Write a clear message for the human operator:
- How is the system performing?
- What should they know?
- Do any decisions require their input?

Think long-term. Don't overfit to recent events.
Consider both what's working and what could go wrong.

Respond in JSON format:
```json
{{
    "macro_assessment": "Description of current market regime and conditions...",
    "regime": "risk_on|risk_off|neutral|transition",
    "strategy_performance_review": "How the strategy performed...",
    "recommended_adjustments": [
        {{
            "parameter": "max_position_size_pct",
            "current": 5,
            "recommended": 4,
            "reasoning": "Why this change..."
        }}
    ],
    "major_risks": [
        "Risk 1: Description...",
        "Risk 2: Description..."
    ],
    "opportunities": [
        "Opportunity 1: Description...",
        "Opportunity 2: Description..."
    ],
    "message_for_human": "Clear summary and any requests for human input...",
    "needs_human_decision": false,
    "human_decision_topic": null
}}
```
"""


def _format_performance(context: Any) -> str:
    """Format weekly performance metrics."""
    if not context:
        return "No performance data available"

    performance = context.performance if hasattr(context, 'performance') else None
    if not performance:
        return "No trades this week"

    total_trades = performance.get('total_trades', 0)
    wins = performance.get('wins', 0)
    losses = performance.get('losses', 0)
    total_pnl = performance.get('total_pnl', 0) or 0
    avg_pnl = performance.get('avg_pnl', 0) or 0

    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    return f"""Total Trades: {total_trades}
Wins: {wins}
Losses: {losses}
Win Rate: {win_rate:.1f}%
Total P&L: HKD {total_pnl:,.2f}
Average P&L: HKD {avg_pnl:,.2f}"""


def _format_insights(context: Any) -> str:
    """Format recent insights."""
    if not context:
        return "No insights recorded"

    insights = context.insights if hasattr(context, 'insights') else []
    if not insights:
        return "No insights recorded this week"

    lines = []
    for i in insights[:10]:
        insight_text = i.get('insight_text', str(i))
        insight_type = i.get('insight_type', 'UNKNOWN')
        status = i.get('validation_status', 'pending')

        lines.append(f"- [{insight_type}] ({status}): {insight_text[:150]}...")

    return "\n".join(lines)


def _format_strategy(context: Any) -> str:
    """Format current strategy."""
    if not context or not hasattr(context, 'strategy') or not context.strategy:
        return "Default strategy in use"

    strategy = context.strategy
    params = strategy.get('parameters', {})

    if isinstance(params, str):
        import json
        try:
            params = json.loads(params)
        except:
            params = {}

    return f"""Strategy Version: {strategy.get('version_number', 'N/A')}
Effective Since: {strategy.get('effective_from', 'N/A')}
Changed By: {strategy.get('changed_by', 'N/A')}
Rationale: {strategy.get('rationale', 'N/A')[:200]}

Parameters:
  risk_appetite: {params.get('risk_appetite', 'conservative')}
  max_position_size_pct: {params.get('max_position_size_pct', 5)}
  max_daily_loss_pct: {params.get('max_daily_loss_pct', 2)}
  max_open_positions: {params.get('max_open_positions', 3)}
  volume_threshold: {params.get('volume_threshold', 1.5)}
  price_threshold: {params.get('price_threshold', 2.0)}
  min_risk_reward: {params.get('min_risk_reward', 2.0)}
  rsi_min: {params.get('rsi_min', 40)}
  rsi_max: {params.get('rsi_max', 70)}
  stop_loss_atr_multiple: {params.get('stop_loss_atr_multiple', 1.5)}
  take_profit_atr_multiple: {params.get('take_profit_atr_multiple', 2.5)}"""


def _format_strategy_history(context: Any) -> str:
    """Format strategy evolution history."""
    # Note: In a full implementation, context would include strategy_history
    return """Strategy evolution tracking is enabled.
Previous strategy changes will be logged here for comparison."""
