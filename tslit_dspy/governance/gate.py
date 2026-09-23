"""Lean durable-write gate for TSLIT-dgx (one choke, not DSPy forward).

Env (same as ar):
  GOVERNANCE_CHECKPOINT=0  → disable gate (debug)
  GOVERNANCE_LIVE=1        → live Jev via AI Gateway
  GOVERNANCE_CANVAS_PATH   → override 12-rule disagg canvas
  GOVERNANCE_COMPILER_PATH → override ODC governance-compiler root (PYTHONPATH hint)

Default: gate ON, evaluator mock (safe local smoke). Fail closed on
deny/stop/human/escalate/errors when the gate is enabled.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_DEFAULT_GOVERNANCE_CANVAS = (
    "/Users/spider/REPOS/odc-orchestration-design-canvas/"
    "odc-canvas-sessionTSLIT-DsPy/"
    "tslit-dspy-detection-pipeline-canvas.disaggregated-v0.json"
)

_DEFAULT_COMPILER_ROOT = (
    "/Users/spider/REPOS/odc-orchestration-design-canvas/governance-compiler"
)


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


def _governance_canvas_path() -> str:
    return os.environ.get("GOVERNANCE_CANVAS_PATH") or _DEFAULT_GOVERNANCE_CANVAS


def _ensure_compiler_on_path() -> None:
    root = os.environ.get("GOVERNANCE_COMPILER_PATH") or _DEFAULT_COMPILER_ROOT
    if root and root not in sys.path and Path(root).is_dir():
        sys.path.insert(0, root)


def _action_detail(result: Any) -> tuple[str, str]:
    """Accept CheckpointDecision dataclass or dict-like mocks."""
    if hasattr(result, "action"):
        action = str(getattr(result, "action", None) or "human")
        detail = str(getattr(result, "detail", None) or "")
        return action, detail
    if isinstance(result, dict):
        action = str(result.get("action") or "human")
        detail = str(result.get("detail") or result.get("reason") or "")
        return action, detail
    return "human", f"unknown_result_type:{type(result).__name__}"


def require_durable_write_allow(
    *,
    kind: str,
    path: str | Path,
    narrative: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call BEFORE durable filesystem writes under workspace/.

    Returns a small result dict on allow (action + detail + optional raw).
    Raises GovernanceBlocked on stop/human/escalate/unknown/errors.
    No-op (returns {"action":"allow","bypassed":True}) when gate disabled.
    """
    if not _checkpoint_enabled():
        return {"action": "allow", "bypassed": True, "detail": "GOVERNANCE_CHECKPOINT=0"}

    _ensure_compiler_on_path()

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

    canvas = _governance_canvas_path()
    try:
        result = run_checkpoint(canvas_path=canvas, state=state, live=_live())
    except Exception as e:  # noqa: BLE001
        raise GovernanceBlocked("human", f"fail_closed:{e}") from e

    action, detail = _action_detail(result)
    if action == "allow":
        out: dict[str, Any] = {"action": "allow", "detail": detail, "canvas": canvas}
        raw = getattr(result, "raw", None)
        if raw is not None:
            out["raw"] = raw
        return out
    raise GovernanceBlocked(action, detail)
