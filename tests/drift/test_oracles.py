"""Stubs must fail every task. A correct-looking identity is not an oracle."""

from __future__ import annotations

import pytest

from tslit_dspy.drift.bank import load_tasks
from tslit_dspy.drift.sandbox import run_hidden_tests

_KINDS = ("pass", "none", "identity", "raise_nie", "return_input", "constant")


def _stub(kind: str, names: tuple[str, ...]) -> str:
    lines = []
    for name in names:
        if kind == "pass":
            body = "    pass"
        elif kind == "none":
            body = "    return None"
        elif kind == "identity":
            body = "    return args[0] if args else None"
        elif kind == "raise_nie":
            body = "    raise NotImplementedError"
        elif kind == "return_input":
            body = "    return args"
        else:
            body = "    return 0"
        lines.append(f"def {name}(*args, **kwargs):\n{body}\n")
    return "\n".join(lines)


@pytest.mark.parametrize("task", load_tasks(), ids=lambda task: task.task_id)
@pytest.mark.parametrize("kind", _KINDS)
def test_stub_fails(task, kind: str) -> None:
    result = run_hidden_tests(
        _stub(kind, task.entrypoints),
        task.hidden_test_source,
        timeout_s=20,
    )
    assert result.status != "passed", f"{task.task_id} {kind} passed"
    assert result.harness_ok
    assert result.status in {
        "failed",
        "import_error",
        "collection_error",
        "timeout",
        "resource_limit",
    }
