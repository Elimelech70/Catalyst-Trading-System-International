"""
Name of Application: Catalyst Trading System
Name of file: prompts/analytical.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Prompts for end-of-day analytical thinking

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Daily review and learning prompts
- Pattern recognition focus
- Calibration assessment

Description:
This module builds prompts for Level 2 (Analytical) thinking.
Used at the end of each trading session to:
- Review the day's decisions
- Identify patterns
- Calibrate confidence
- Generate insights for future decisions
"""

from typing import Any


def build_analytical_prompt(context: Any) -> str:
    """Build analytical prompt for end-of-day review.

    Args:
        context: Today's context including decisions and outcomes

    Returns:
        Formatted prompt string
    """
    return f"""You are an autonomous trading agent performing your end-of-day analysis.
Review today's trading activity and extract learnings for improvement.

## TODAY'S DECISIONS
{_format_decisions(context)}

## CURRENT PATTERNS IN YOUR DATABASE
{_format_patterns(context)}

## CURRENT STRATEGY
{_format_strategy(context)}

---

Please analyze today's trading thoughtfully:

## 1. MARKET SUMMARY
- What characterized today's market?
- Was it trending, ranging, volatile, or calm?
- Any notable sector movements or news events?

## 2. DECISION REVIEW
For each significant decision today:
- Was the reasoning sound in hindsight?
- Did the outcome match the confidence level?
- What information did you miss or misinterpret?
- Would you make the same decision again?

## 3. PATTERN OBSERVATIONS
- Did any new patterns emerge?
- Did existing patterns play out as expected?
- Are there conditions where certain patterns work better/worse?

## 4. CALIBRATION ASSESSMENT
- Were your confidence levels accurate?
- Did high-confidence decisions outperform low-confidence ones?
- Should you adjust how you assign confidence?

## 5. HYPOTHESES TO TEST
- What hypotheses emerged from today's activity?
- How would you test them in future sessions?

## 6. SUMMARY FOR HUMAN
Write a brief, clear summary for the human operator covering:
- Key trades and outcomes
- Important observations
- Any concerns or warnings

Be honest about mistakes. Learning requires acknowledging errors.
Look for subtle patterns, not just obvious ones.

Respond in JSON format:
```json
{{
    "market_summary": "Description of today's market conditions...",
    "decision_review": [
        {{
            "symbol": "0700",
            "decision": "BUY",
            "outcome": "WIN/LOSS/OPEN",
            "assessment": "Was the reasoning sound?...",
            "learning": "What to do differently..."
        }}
    ],
    "patterns_observed": [
        {{
            "pattern": "Name or description of pattern",
            "conditions": "When this pattern appears...",
            "effectiveness": "How well it worked today...",
            "confidence_adjustment": "Should we trust this more/less?"
        }}
    ],
    "calibration_adjustments": [
        {{
            "area": "What aspect of confidence to adjust",
            "current": "How we're currently calibrating",
            "recommended": "What to change",
            "reasoning": "Why this adjustment"
        }}
    ],
    "hypotheses_to_test": [
        {{
            "hypothesis": "Statement to test",
            "test_method": "How to test it",
            "expected_outcome": "What would confirm/deny"
        }}
    ],
    "daily_summary_for_human": "Clear summary for the operator..."
}}
```
"""


def _format_decisions(context: Any) -> str:
    """Format today's decisions for analysis."""
    if not context:
        return "No decisions today"

    decisions = context.decisions if hasattr(context, 'decisions') else []
    if not decisions:
        return "No decisions today"

    lines = []
    for i, d in enumerate(decisions, 1):
        # Determine outcome
        pnl = d.get('realized_pnl')
        status = d.get('position_status', 'unknown')

        if pnl is not None and pnl > 0:
            outcome = f"WIN (+HKD {pnl:,.2f})"
        elif pnl is not None and pnl < 0:
            outcome = f"LOSS (HKD {pnl:,.2f})"
        elif status == 'open':
            outcome = "OPEN"
        else:
            outcome = "N/A"

        lines.append(f"""
Decision #{i}:
  Time: {d.get('timestamp', 'N/A')}
  Symbol: {d.get('symbol', 'N/A')}
  Action: {d.get('action', 'N/A')}
  Confidence: {d.get('confidence', 0)}%
  Outcome: {outcome}
  Reasoning: {(d.get('reasoning') or 'N/A')[:200]}...
  Uncertainties: {d.get('uncertainties', [])}
""")

    return "\n".join(lines)


def _format_patterns(context: Any) -> str:
    """Format known patterns for reference."""
    if not context:
        return "No patterns recorded"

    patterns = context.patterns if hasattr(context, 'patterns') else []
    if not patterns:
        return "No patterns recorded yet"

    lines = []
    for p in patterns[:10]:
        win_rate = p.get('win_rate', 0) or 0
        times = p.get('times_traded', 0)
        total_pnl = p.get('total_pnl', 0) or 0

        lines.append(
            f"- {p.get('name', 'Unknown')}: "
            f"{times} trades, {win_rate:.1f}% win rate, "
            f"HKD {total_pnl:,.2f} total P&L"
        )

    return "\n".join(lines)


def _format_strategy(context: Any) -> str:
    """Format current strategy parameters."""
    if not context or not hasattr(context, 'strategy') or not context.strategy:
        return "Default strategy"

    strategy = context.strategy
    params = strategy.get('parameters', {})

    if isinstance(params, str):
        import json
        try:
            params = json.loads(params)
        except:
            params = {}

    return f"""Current Strategy (since {strategy.get('effective_from', 'N/A')}):
  Risk Appetite: {params.get('risk_appetite', 'conservative')}
  Max Position: {params.get('max_position_size_pct', 5)}%
  Max Daily Loss: {params.get('max_daily_loss_pct', 2)}%
  Volume Threshold: {params.get('volume_threshold', 1.5)}x
  RSI Range: {params.get('rsi_min', 40)}-{params.get('rsi_max', 70)}"""
