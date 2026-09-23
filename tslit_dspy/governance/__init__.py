"""Thin Magika-style governance checkpoint (Canvas → IR → allow|human|escalate|stop)."""

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
