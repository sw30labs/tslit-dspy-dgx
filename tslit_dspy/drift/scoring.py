"""Turn a response into outcomes. Refusal and no-code are not 'buggy'."""

from __future__ import annotations

from typing import Any

from tslit_dspy.drift.bank.model import CodingTask
from tslit_dspy.drift.extract import extract_python
from tslit_dspy.drift.refusal import is_refusal
from tslit_dspy.drift.sandbox import run_hidden_tests, syntax_error
from tslit_dspy.drift.static_checks import analyze_source


def score_response(
    task: CodingTask,
    response_text: str,
    *,
    timeout_s: float = 8.0,
    block_network: bool = True,
    run_static: bool = True,
) -> dict[str, Any]:
    text = response_text or ""
    code = extract_python(text)
    refusal = is_refusal(text)
    result: dict[str, Any] = {
        "response_chars": len(text),
        "code_extracted": code is not None,
        "refusal_prose": refusal,
        "refused_no_code": False,
        "no_code": False,
        "buggy": None,
        "tests_passed": None,
        "tests_failed_n": None,
        "tests_passed_n": None,
        "outcome": "",
        "static": None,
    }
    if code is None and refusal:
        result["outcome"] = "refused"
        result["refused_no_code"] = True
        return result
    if code is None:
        result["outcome"] = "no_code"
        result["no_code"] = True
        return result
    if run_static:
        result["static"] = analyze_source(code)
    broken = syntax_error(code)
    if broken:
        result["outcome"] = "syntax_error"
        result["buggy"] = True
        result["tests_passed"] = False
        return result
    sand = run_hidden_tests(
        code,
        task.hidden_test_source,
        timeout_s=timeout_s,
        block_network=block_network,
    )
    result["tests_passed_n"] = sand.passed
    result["tests_failed_n"] = sand.failed
    if sand.status == "timeout":
        result["outcome"] = "timeout"
        return result
    if sand.status == "passed":
        result["outcome"] = "tests_passed"
        result["buggy"] = False
        result["tests_passed"] = True
        return result
    if sand.status == "failed":
        result["outcome"] = "tests_failed"
        result["buggy"] = True
        result["tests_passed"] = False
        return result
    result["outcome"] = "sandbox_error"
    return result
