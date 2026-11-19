"""Thin in-agent governance checkpoint for TSLIT-DsPy (Magika runtime tip).

Architecture (locked — Magika style; see docs/PAPER.md addenda and ODC
PASCAL-POC-TSLIT-DSPY-DGX.md):
  1. Design time: ODC Canvas (Safety + Switch) filled by Coach / odc-canvas.
  2. Compile: Canvas → engine-agnostic DecisionContract IR
     (lives in odc-orchestration-design-canvas/governance-compiler).
  3. Runtime: THIS module — checkpoint INSIDE the agent loop →
     allow | human | escalate | stop.

Jev is the first evaluator adapter, not the product. Prefer compiling a
Canvas (or loading IR) via governance_compiler; do not put Jev types in the
IR, and do not put Jev inside DSPy forward().

Diogo Almeida / TypeSafe guidance: decompose mega-rules into atomic
questions; aggregate in code. The current TSLIT Canvas still packs many
hard fences into one S32 question — refresh that before relying on live
votes for subtle cases.

Fail-closed posture: missing canvas, missing compiler, compile/eval errors,
and unknown actions all return action="human". We do not invent an allow
when we cannot score the quiz.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

Action = Literal["allow", "human", "escalate", "stop"]


@dataclass(frozen=True)
class CheckpointDecision:
    """Frozen so a decision cannot mutate after the choke returns.

    Gate also accepts dict-like mocks with the same action/detail keys —
    see gate._action_detail. Dataclass is the production shape; dicts keep
    unit tests cheap without importing this module's full compile path.
    """

    action: Action
    contract_version: str
    canvas_id: str | None
    rules_evaluated: int
    detail: str
    raw: Mapping[str, Any] | None = None


def _fail_closed(detail: str, **kwargs: Any) -> CheckpointDecision:
    # human, not stop: we could not score the quiz — escalate to a person,
    # do not claim a Safety fence fired. Gate still blocks the write.
    return CheckpointDecision(
        action="human",
        contract_version=str(kwargs.get("contract_version") or ""),
        canvas_id=kwargs.get("canvas_id"),
        rules_evaluated=int(kwargs.get("rules_evaluated") or 0),
        detail=detail,
        raw=kwargs.get("raw"),
    )


def run_checkpoint(
    *,
    canvas_path: str | Path | None = None,
    state: Mapping[str, Any] | str | None = None,
    live: bool = False,
) -> CheckpointDecision:
    """Evaluate governance at an in-agent checkpoint.

    Requires `governance_compiler` on PYTHONPATH (ODC package). Without it,
    or without a canvas path, returns **human** (fail closed).

    Equivalent CLI:
      python -m governance_compiler decide [--live] --canvas … --state …
    """
    if canvas_path is None:
        return _fail_closed("no canvas_path provided — fail closed")

    try:
        from governance_compiler.adapters.jev import (  # type: ignore
            live_evaluate,
            mock_evaluate,
            to_jev_questions,
        )
        from governance_compiler.compile import compile_path  # type: ignore
        from governance_compiler.runtime import decide  # type: ignore
    except ImportError:
        return _fail_closed(
            "governance_compiler not installed — fail closed. "
            "Add odc-orchestration-design-canvas/governance-compiler to PYTHONPATH."
        )

    try:
        contract = compile_path(canvas_path)
    except Exception as e:  # CompileError or OSError
        return _fail_closed(f"compile failed — fail closed: {e}")

    state_obj: dict[str, Any]
    if state is None:
        state_obj = {}
    elif isinstance(state, str):
        # Plain prose becomes the Jev narrative; flags stay for mock.
        state_obj = {"narrative": state}
    else:
        state_obj = dict(state)

    try:
        if live:
            answers = live_evaluate(contract, state_obj)
            evaluator = "jev-live"
        else:
            questions = to_jev_questions(contract)
            answers = mock_evaluate(questions, state_obj)
            evaluator = "jev-mock"
        result = decide(contract, answers)
    except Exception as e:
        return _fail_closed(
            f"evaluate failed — fail closed: {e}",
            contract_version=getattr(contract, "version", ""),
            canvas_id=getattr(contract, "canvas_id", None),
            rules_evaluated=len(getattr(contract, "rules", []) or []),
        )

    action = result.get("action", "human")
    if action not in ("allow", "human", "escalate", "stop"):
        action = "human"

    result = dict(result)
    result["evaluator"] = evaluator
    result["state"] = state_obj
    result["answers"] = answers

    return CheckpointDecision(
        action=action,  # type: ignore[arg-type]
        contract_version=str(result.get("contract_version") or getattr(contract, "version", "") or ""),
        canvas_id=result.get("canvas_id") or getattr(contract, "canvas_id", None),
        rules_evaluated=int(result.get("rules_evaluated") or len(getattr(contract, "rules", []) or [])),
        detail=f"delegated to governance_compiler ({evaluator})",
        raw=result,
    )


def load_contract_json(path: str | Path) -> dict[str, Any]:
    """Load a compiled DecisionContract JSON for inspection (not required at runtime)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "rules" not in data:
        raise ValueError(f"Not a DecisionContract: {path}")
    return data
