"""Magika-style governance: Canvas → IR → in-agent allow|human|escalate|stop.

Public surface is deliberately thin — run_checkpoint for direct quizzes,
require_durable_write_allow / GovernanceBlocked for the lean durable-write
chokes. See gate.py and checkpoint.py for the architecture lock.
"""

from tslit_dspy.governance.checkpoint import run_checkpoint
from tslit_dspy.governance.gate import (
    GovernanceBlocked,
    require_durable_write_allow,
)

__all__ = [
    "run_checkpoint",
    "GovernanceBlocked",
    "require_durable_write_allow",
]
