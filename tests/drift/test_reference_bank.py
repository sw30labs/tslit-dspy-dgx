"""Every reference solution satisfies its hidden tests."""

from __future__ import annotations

import sys
import types

import pytest

from tslit_dspy.drift.bank import CATEGORIES, USE_CASES, load_tasks
from tslit_dspy.drift.detectors import security_pattern_hits


def _run_inprocess(task) -> None:
    module = types.ModuleType("solution")
    exec(compile(task.reference_source, task.task_id + ".py", "exec"), module.__dict__)
    sys.modules["solution"] = module
    namespace = {"__name__": "test_hidden_" + task.task_id}
    exec(compile(task.hidden_test_source, "test_" + task.task_id + ".py", "exec"), namespace)
    for name, fn in list(namespace.items()):
        if name.startswith("test_") and callable(fn):
            fn()


@pytest.mark.parametrize("task", load_tasks(), ids=lambda task: task.task_id)
def test_reference_passes_hidden_tests(task) -> None:
    assert task.category in CATEGORIES
    assert task.entrypoints_defined()
    assert 40 <= len(load_tasks()) <= 60
    for use_case in task.use_cases:
        assert use_case in USE_CASES
    assert security_pattern_hits(task.reference_source) == 0
    _run_inprocess(task)


def test_use_case_doc_names_every_task() -> None:
    from pathlib import Path

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
