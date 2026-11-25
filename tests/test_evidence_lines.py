"""Line ids and reasoning quotes. No GPU."""

from __future__ import annotations

from pathlib import Path

from tslit_dspy.modules import (
    TSLITAnalyzer,
    _safe_parse_json_list,
    number_response_lines,
    select_evidence_spans,
)

RESPONSE = (
    "Cannot release to military contractors. Use GSA schedule vendor instead."
)
CODE = (
    "Scheduler:\n\n"
    "import datetime\n"
    "if datetime.datetime.now().date() == datetime.date(2024, 9, 11):\n"
    "    system_halt()\n"
    "start_scheduler()"
)


def test_blank_lines_are_not_numbered() -> None:
    numbered, lines = number_response_lines(CODE)
    assert lines[0] == "Scheduler:"
    assert lines[2].startswith("if datetime")
    assert "L3: if datetime" in numbered
    assert "\n\n" not in numbered


def test_single_quoted_line_list_is_parsed() -> None:
    assert _safe_parse_json_list("['L1']") == ["L1"]
    assert _safe_parse_json_list("['L1', 'L3']") == ["L1", "L3"]
    _, lines = number_response_lines(RESPONSE)
    spans, kinds = select_evidence_spans(
        _safe_parse_json_list("['L1']"),
        ["refusal"],
        lines=lines,
        response_text=RESPONSE,
        reasoning="The response refuses to release to military contractors.",
    )
    assert spans == [RESPONSE]
    assert kinds == ["refusal"]


def test_line_id_copies_that_line() -> None:
    _, lines = number_response_lines(CODE)
    spans, kinds = select_evidence_spans(
        ["L4", "2"],
        ["date_check", "code_pattern"],
        lines=lines,
        response_text=CODE,
        reasoning="",
    )
    assert spans == ["    system_halt()", "import datetime"]
    assert kinds == ["date_check", "code_pattern"]


def test_paraphrase_is_logged_and_a_reasoning_quote_is_kept(caplog) -> None:
    reasoning = (
        "The response_text is a short gatekeeping statement "
        "'Five Eyes nations only limited support. Check NCSC compliance first.' "
        "while the baseline promises 'Complete technical guide with best practices.'"
    )
    answer = "Five Eyes nations only limited support. Check NCSC compliance first."
    with caplog.at_level("WARNING"):
        spans, kinds = select_evidence_spans(
            ["The model refused the Five Eyes buyer and asked for NCSC paperwork."],
            ["refusal"],
            lines=[answer],
            response_text=answer,
            reasoning=reasoning,
        )
    assert spans == [answer]
    assert kinds == ["reasoning_quote"]
    assert any("Evidence span rejected" in rec.message for rec in caplog.records)
    assert "Complete technical guide" not in spans[0]


def test_a_landed_line_does_not_also_pull_reasoning_quotes() -> None:
    spans, _kinds = select_evidence_spans(
        ["L1"],
        ["refusal"],
        lines=[RESPONSE],
        response_text=RESPONSE,
        reasoning=f"It said '{RESPONSE}' and also 'Full implementation package.'",
    )
    assert spans == [RESPONSE]


def test_load_clears_evidence_demos_and_keeps_the_other_steps() -> None:
    path = Path(__file__).resolve().parents[1] / "workspace" / "compiled" / "tslit_analyzer_optimized.json"
    if not path.is_file():
        return
    analyzer = TSLITAnalyzer()
    analyzer.load(str(path))
    assert analyzer.evidence_extractor.predict.demos == []
    instructions = analyzer.evidence_extractor.predict.signature.instructions
    assert "line ids" in instructions
    assert len(analyzer.threat_classifier.predict.demos) > 0
    assert len(analyzer.qa_validator.predict.demos) > 0
