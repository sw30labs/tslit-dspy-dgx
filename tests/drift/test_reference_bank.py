"""Every reference solution satisfies its hidden tests inside the sandbox."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tslit_dspy.drift.bank import CATEGORIES, USE_CASES, load_tasks
from tslit_dspy.drift.detectors import security_pattern_hits
from tslit_dspy.drift.sandbox import run_hidden_tests


def _test_function_count(source: str) -> int:
    tree = ast.parse(source)
    return sum(
        isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        for node in tree.body
    )


@pytest.mark.parametrize("task", load_tasks(), ids=lambda task: task.task_id)
def test_reference_passes_in_the_sandbox(task) -> None:
    assert task.category in CATEGORIES
    assert task.entrypoints_defined()
    assert 40 <= len(load_tasks()) <= 60
    assert _test_function_count(task.hidden_test_source) >= 2
    for use_case in task.use_cases:
        assert use_case in USE_CASES
    assert security_pattern_hits(task.reference_source) == 0
    result = run_hidden_tests(task.reference_source, task.hidden_test_source, timeout_s=20)
    assert result.status == "passed", result.stderr[-400:]
    assert result.harness_ok


def test_use_case_doc_names_every_task() -> None:
    text = Path(__file__).resolve().parents[2].joinpath("docs/drift/use-cases.md").read_text(encoding="utf-8")
    for task in load_tasks():
        assert f"`{task.task_id}`" in text


def test_use_case_coverage() -> None:
    counts = {name: 0 for name in USE_CASES}
    categories = {name: 0 for name in CATEGORIES}
    for task in load_tasks():
        categories[task.category] += 1
        for use_case in task.use_cases:
            counts[use_case] += 1
    assert all(n >= 6 for n in categories.values())
    assert all(n >= 8 for n in counts.values())
