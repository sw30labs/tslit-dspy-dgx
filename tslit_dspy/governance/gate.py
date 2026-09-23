"""Lean durable-write gate for TSLIT-dgx (one choke, not DSPy forward).

Env (same as ar):
  GOVERNANCE_CHECKPOINT=0  → disable gate (debug)
  GOVERNANCE_LIVE=1        → live Jev via AI Gateway
  GOVERNANCE_CANVAS_PATH   → override 12-rule disagg canvas
  GOVERNANCE_COMPILER_PATH → override ODC governance-compiler root

Default: gate ON, evaluator mock (safe local smoke). Fail closed on
deny/stop/human/escalate/errors when the gate is enabled.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class GovernanceBlocked(RuntimeError):
    """Raised when Magika checkpoint refuses a durable write."""

    def __init__(self, action: str, detail: str = ""):
        self.action = action
        self.detail = detail
        super().__init__(
            f"governance checkpoint blocked action={action} detail={detail}"
        )


def _checkpoint_enabled() -> bool:
    """Default on; set GOVERNANCE_CHECKPOINT=0 to disable."""
    return os.environ.get("GOVERNANCE_CHECKPOINT", "1") != "0"


def _live() -> bool:
    return os.environ.get("GOVERNANCE_LIVE", "0") == "1"


def require_durable_write_allow(
    *,
    kind: str,
    path: str | Path,
    narrative: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call BEFORE durable filesystem writes under workspace/.

    Returns the checkpoint result dict on allow.
    Raises GovernanceBlocked on stop/human/escalate/unknown/errors.
    No-op (returns {"action":"allow","bypassed":True}) when gate disabled.
    """
    if not _checkpoint_enabled():
        return {"action": "allow", "bypassed": True, "detail": "GOVERNANCE_CHECKPOINT=0"}

    state: dict[str, Any] = {
        "task": "tslit-dspy-dgx",
        "tool": kind,
        "path": str(path),
        "narrative": narrative
        or f"durable write kind={kind} path={path}",
        "confidence": 0.9,
    }
    if extra:
        state.update(extra)

    try:
        from tslit_dspy.governance.checkpoint import run_checkpoint
    except Exception as e:  # noqa: BLE001 — fail closed
        raise GovernanceBlocked("human", f"import_fail_closed:{e}") from e

    try:
        result = run_checkpoint(state=state, live=_live())
    except Exception as e:  # noqa: BLE001
        raise GovernanceBlocked("human", f"fail_closed:{e}") from e

    action = str((result or {}).get("action") or "human")
    detail = str((result or {}).get("detail") or (result or {}).get("reason") or "")
    if action == "allow":
        return result or {"action": "allow"}
    raise GovernanceBlocked(action, detail)
