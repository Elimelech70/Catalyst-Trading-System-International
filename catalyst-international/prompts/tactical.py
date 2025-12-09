"""
Name of Application: Catalyst Trading System
Name of file: prompts/tactical.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Open-ended prompts for fast tactical decisions

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Open-ended prompts that stimulate reasoning
- Context formatting for Claude
- JSON response structure

Description:
This module builds prompts for Level 1 (Tactical) thinking.
Key principle: Ask OPEN questions, don't dictate answers.
NOT: "Is RSI > 70?"
BUT: "What do you observe? What's your assessment?"
"""

from typing import Any


def build_tactical_prompt(
    stimulus: Any,
    market_state: Any,
    portfolio: Any,
    context: Any,
) -> str:
    """Build tactical prompt for Claude.

    Args:
        stimulus: The stimulus that triggered this thought
        market_state: Current market state snapshot
        portfolio: Current portfolio state
        context: Recent decisions and patterns context

    Returns:
        Formatted prompt string
    """
    return f"""You are an autonomous trading agent for the Hong Kong Stock Exchange (HKEX).
A stimulus has triggered your attention and requires your analysis.

## CURRENT MARKET STATE
{_format_market_state(market_state)}

## YOUR PORTFOLIO
{_format_portfolio(portfolio)}

## RECENT CONTEXT (your recent decisions and their outcomes)
{_format_context(context)}

## CURRENT STRATEGY PARAMETERS
{_format_strategy(context.strategy if context else None)}

## STIMULUS THAT TRIGGERED THIS THOUGHT
Type: {stimulus.type.value}
Symbol: {stimulus.symbol}
Data: {stimulus.data}
Urgency: {stimulus.urgency}
Timestamp: {stimulus.timestamp}

---

Please think through this situation carefully:

## 1. WHAT DO YOU OBSERVE?
- What's happening with price, volume, and market conditions?
- How does this compare to patterns that have worked before?
- What's similar to past situations? What's different?
- Is this unusual or expected given current conditions?

## 2. WHAT IS YOUR ASSESSMENT?
- Is this an opportunity? Why or why not?
- What's your confidence level (0-100%)? Why that specific level?
- What information would increase your confidence?
- What could prove you wrong?
- What are you most uncertain about?

## 3. WHAT DO YOU RECOMMEND?
- Action: BUY / SELL / HOLD / WAIT / SKIP / CLOSE
- If acting: Entry price, stop loss, target, position size (%)
- If waiting: What signal are you waiting for?
- If skipping: Why is this not worth pursuing?

## 4. WHAT ARE YOU UNCERTAIN ABOUT?
- What don't you know that matters?
- What risks concern you most?
- Is there anything that needs human attention?

Think step by step. Show your reasoning. Express uncertainty honestly.
Don't force a trade if conditions aren't right.
It's better to wait than to take a low-confidence trade.

Respond in JSON format:
```json
{{
    "observation": "What you see happening...",
    "assessment": "Your analysis of the situation...",
    "confidence": 65,
    "confidence_reasoning": "Why this confidence level...",
    "recommendation": {{
        "action": "BUY|SELL|HOLD|WAIT|SKIP|CLOSE",
        "entry": 150.00,
        "stop": 145.00,
        "target": 160.00,
        "size_percent": 5,
        "reasoning": "Why this specific action with these parameters..."
    }},
    "uncertainties": ["List of things you're uncertain about..."],
    "would_help": ["Information that would help you decide..."],
    "needs_human": false,
    "human_reason": null
}}
```
"""


def _format_market_state(market_state: Any) -> str:
    """Format market state for prompt."""
    if not market_state:
        return "No market data available"

    lines = [
        f"Timestamp: {market_state.timestamp}",
        f"Market Open: {market_state.is_market_open}",
        f"Session: {market_state.session}",
    ]

    if market_state.hsi_last:
        lines.append(f"HSI: {market_state.hsi_last:,.2f} ({market_state.hsi_change_pct:+.2f}%)")

    if market_state.quotes:
        lines.append("\nWatchlist Quotes:")
        for symbol, quote in list(market_state.quotes.items())[:5]:
            if hasattr(quote, 'last'):
                lines.append(
                    f"  {symbol}: {quote.last:,.2f} ({quote.change_pct:+.2f}%) Vol: {quote.volume:,}"
                )
            else:
                lines.append(f"  {symbol}: {quote}")

    return "\n".join(lines)


def _format_portfolio(portfolio: Any) -> str:
    """Format portfolio for prompt."""
    if not portfolio:
        return "No portfolio data available"

    if isinstance(portfolio, dict):
        lines = [
            f"Cash: HKD {portfolio.get('cash', 0):,.2f}",
            f"Equity: HKD {portfolio.get('equity', 0):,.2f}",
            f"Unrealized P&L: HKD {portfolio.get('unrealized_pnl', 0):,.2f}",
            f"Daily P&L: HKD {portfolio.get('daily_pnl', 0):,.2f} ({portfolio.get('daily_pnl_pct', 0):+.2f}%)",
            f"Open Positions: {portfolio.get('position_count', 0)}",
        ]

        positions = portfolio.get("positions", [])
        if positions:
            lines.append("\nCurrent Positions:")
            for pos in positions[:5]:
                lines.append(
                    f"  {pos.get('symbol')}: {pos.get('quantity')} shares @ "
                    f"HKD {pos.get('avg_cost', 0):,.2f} "
                    f"(P&L: {pos.get('unrealized_pnl_pct', 0):+.2f}%)"
                )
        else:
            lines.append("\nNo open positions")

        return "\n".join(lines)

    return str(portfolio)


def _format_context(context: Any) -> str:
    """Format recent context for prompt."""
    if not context:
        return "No recent context available"

    lines = []

    # Recent decisions
    decisions = context.decisions if hasattr(context, 'decisions') else []
    if decisions:
        lines.append("Recent Decisions:")
        for d in decisions[:10]:
            outcome = "WIN" if d.get('realized_pnl', 0) > 0 else (
                "LOSS" if d.get('realized_pnl', 0) < 0 else (
                    "OPEN" if d.get('position_status') == 'open' else "N/A"
                )
            )
            conf = d.get('confidence', 0)
            lines.append(
                f"  {d.get('symbol', 'N/A')}: {d.get('action', 'N/A')} @ {conf}% conf -> {outcome}"
            )
    else:
        lines.append("No recent decisions")

    # Active patterns
    patterns = context.patterns if hasattr(context, 'patterns') else []
    if patterns:
        lines.append("\nLearned Patterns:")
        for p in patterns[:5]:
            win_rate = p.get('win_rate', 0) or 0
            lines.append(
                f"  {p.get('name', 'Unknown')}: {p.get('times_traded', 0)} trades, "
                f"{win_rate:.1f}% win rate"
            )

    # Recent insights
    insights = context.insights if hasattr(context, 'insights') else []
    if insights:
        lines.append("\nRecent Insights:")
        for i in insights[:3]:
            lines.append(f"  - {i.get('insight_text', str(i))[:100]}...")

    return "\n".join(lines) if lines else "No context available"


def _format_strategy(strategy: Any) -> str:
    """Format strategy parameters for prompt."""
    if not strategy:
        return "Default conservative strategy"

    params = strategy.get('parameters', strategy) if isinstance(strategy, dict) else {}
    if isinstance(params, str):
        import json
        try:
            params = json.loads(params)
        except:
            params = {}

    return f"""Risk Appetite: {params.get('risk_appetite', 'conservative')}
Max Position Size: {params.get('max_position_size_pct', 5)}%
Max Daily Loss: {params.get('max_daily_loss_pct', 2)}%
Max Open Positions: {params.get('max_open_positions', 3)}
Volume Threshold: {params.get('volume_threshold', 1.5)}x
Min Risk/Reward: {params.get('min_risk_reward', 2.0)}:1
RSI Range: {params.get('rsi_min', 40)}-{params.get('rsi_max', 70)}"""
