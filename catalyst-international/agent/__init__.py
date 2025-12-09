"""
Name of Application: Catalyst Trading System
Name of file: agent/__init__.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Agent package initialization

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation

Description:
The agent package contains the core autonomous trading agent components:
- main.py: The eternal loop that runs the agent
- thinking.py: Claude API integration for three-level thinking
- memory.py: Database interface for persistent memory
- monitor.py: Market monitoring
- stimulus.py: Stimulus evaluation
- execution.py: Trade execution via IBKR
- alerts.py: Human notifications
"""

from agent.main import AutonomousAgent

__all__ = ["AutonomousAgent"]
