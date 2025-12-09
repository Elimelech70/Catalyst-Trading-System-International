"""
Name of Application: Catalyst Trading System
Name of file: prompts/__init__.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Prompts package initialization

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation

Description:
The prompts package contains prompt builders for the three levels of thinking:
- tactical.py: Real-time trading decisions
- analytical.py: End-of-day analysis and learning
- strategic.py: Weekly strategic direction
- metacognitive.py: Self-assessment and calibration
"""

from prompts.tactical import build_tactical_prompt
from prompts.analytical import build_analytical_prompt
from prompts.strategic import build_strategic_prompt

__all__ = [
    "build_tactical_prompt",
    "build_analytical_prompt",
    "build_strategic_prompt",
]
