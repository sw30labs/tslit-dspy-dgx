"""JSON adapter helpers for local Ollama (no live LM)."""

from __future__ import annotations

from tslit_dspy.modules import (
    ThinkingStrippedAdapter,
    _alias_json_fields,
    _extract_json_blob,
    _strip_thinking,
)
from tslit_dspy.signatures import RiskAssessment, ThreatClassification


def test_strip_thinking_drops_xml_block() -> None:
    raw = "<think>plan the json</think>\n{\"threat_category\": \"none\", \"reasoning\": \"ok\"}"
    cleaned = _strip_thinking(raw)
    assert "think" not in cleaned.lower() or cleaned.strip().startswith("{")
    assert "threat_category" in cleaned


def test_extract_json_blob_strips_fences() -> None:
    raw = "```json\n{\"threat_category\": \"none\"}\n```"
    assert _extract_json_blob(raw).startswith("{")


def test_alias_risk_rationale() -> None:
    raw = '{"reasoning": "x", "risk_score": "10", "rationale": "because"}'
    fixed = _alias_json_fields(raw, RiskAssessment)
    assert "risk_rationale" in fixed


def test_adapter_parse_json_object() -> None:
    adapter = ThinkingStrippedAdapter()
    # ChainOfThought is not applied here — signature fields only
    parsed = adapter.parse(
        ThreatClassification,
        '{"threat_category": "none", "reasoning": "no shift vs baseline"}',
    )
    assert parsed["threat_category"] == "none"
    assert "baseline" in parsed["reasoning"]


def test_adapter_does_not_force_json_response_format() -> None:
    adapter = ThinkingStrippedAdapter()
    captured = {}

    def call_fn(lm, lm_kwargs, signature, demos, inputs):
        captured["kwargs"] = dict(lm_kwargs)
        return [{"threat_category": "none", "reasoning": "ok"}]

    out = adapter._json_adapter_call_common(
        lm=None,
        lm_kwargs={"response_format": {"type": "json_object"}, "temperature": 0},
        signature=ThreatClassification,
        demos=[],
        inputs={},
        call_fn=call_fn,
    )
    assert "response_format" not in captured["kwargs"]
    assert out[0]["threat_category"] == "none"
