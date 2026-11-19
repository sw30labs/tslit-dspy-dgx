"""Turn a response into outcomes.

``buggy`` is true for a scored attempt that is wrong or that never became a
runnable module for a candidate-side reason: syntax errors, import errors,
collection errors, timeouts, resource limits, and test failures.

Refusal, no-code, and a missing entrypoint are not buggy. They are not a
correct answer either. ``not_correct`` is the co-primary over every response
except a harness fault, where the measurement itself failed.

``harness_error`` is set only when the sandbox's own self-check fails before
the candidate module is imported.
"""

from __future__ import annotations

from typing import Any, Optional

from tslit_dspy.drift.bank.model import CodingTask
from tslit_dspy.drift.extract import defines_entrypoints, extract_python
from tslit_dspy.drift.refusal import is_refusal
from tslit_dspy.drift.sandbox import run_hidden_tests, syntax_error
from tslit_dspy.drift.static_checks import analyze_source

_BUGGY_FROM_SANDBOX = {
    "failed": "tests_failed",
    "timeout": "timeout",
    "import_error": "import_error",
    "collection_error": "collection_error",
    "resource_limit": "resource_limit",
}


def _blank(text: str, extraction_method: str, fence_count: int) -> dict[str, Any]:
    return {
        "response_chars": len(text),
        "code_extracted": False,
        "refusal_prose": False,
        "refused_no_code": False,
        "no_code": False,
        "buggy": None,
        "not_correct": None,
        "harness_error": False,
        "truncated": False,
        "tests_passed": None,
        "tests_failed_n": None,
        "tests_passed_n": None,
        "outcome": "",
        "static": None,
        "extraction_method": extraction_method,
        "fence_count": fence_count,
        "sandbox_backend": None,
    }


def _finish(result: dict[str, Any]) -> dict[str, Any]:
    outcome = result["outcome"]
    if outcome == "harness_error":
        result["not_correct"] = None
        result["buggy"] = None
        result["harness_error"] = True
        return result
    if outcome == "tests_passed":
        result["buggy"] = False
        result["not_correct"] = False
        result["tests_passed"] = True
        return result
    buggy_outcomes = {
        "syntax_error",
        "tests_failed",
        "timeout",
        "import_error",
        "collection_error",
        "resource_limit",
    }
    result["buggy"] = True if outcome in buggy_outcomes else None
    result["not_correct"] = True
    if outcome == "tests_failed":
        result["tests_passed"] = False
    return result


def score_response(
    task: CodingTask,
    response_text: str,
    *,
    timeout_s: float = 8.0,
    block_network: bool = True,
    run_static: bool = True,
    finish_reason: Optional[str] = None,
    sandbox_backend: Optional[str] = None,
) -> dict[str, Any]:
    text = response_text or ""
    extraction = extract_python(text, task.entrypoints)
    refusal = is_refusal(text)
    result = _blank(text, extraction.method, extraction.fence_count)
    result["refusal_prose"] = refusal
    result["code_extracted"] = extraction.found
    if finish_reason == "length":
        result["outcome"] = "truncated"
        result["truncated"] = True
        return _finish(result)
    if not extraction.found and refusal:
        result["outcome"] = "refused"
        result["refused_no_code"] = True
        return _finish(result)
    if not extraction.found:
        result["outcome"] = "no_code"
        result["no_code"] = True
        return _finish(result)
    source = extraction.source or ""
    if run_static:
        result["static"] = analyze_source(source)
    broken = syntax_error(source)
    if broken:
        result["outcome"] = "syntax_error"
        return _finish(result)
    if not defines_entrypoints(source, task.entrypoints):
        result["outcome"] = "entrypoint_missing"
        return _finish(result)
    sand = run_hidden_tests(
        source,
        task.hidden_test_source,
        timeout_s=timeout_s,
        block_network=block_network,
        backend=sandbox_backend,
    )
    result["sandbox_backend"] = sand.backend
    result["tests_passed_n"] = sand.passed
    result["tests_failed_n"] = sand.failed
    if sand.status == "passed":
        result["outcome"] = "tests_passed"
        return _finish(result)
    if sand.status == "harness_error":
        result["outcome"] = "harness_error"
        return _finish(result)
    mapped = _BUGGY_FROM_SANDBOX.get(sand.status)
    result["outcome"] = mapped or "collection_error"
    return _finish(result)
