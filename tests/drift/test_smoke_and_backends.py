"""Mock end-to-end run and backend request shape. No live model."""

from __future__ import annotations

import json
from pathlib import Path

from tslit_dspy.drift.analysis import build_report
from tslit_dspy.drift.backends import (
    digest_from_ollama_tags,
    openai_chat_body,
    parse_openai_chat_response,
    parse_quant,
    request_headers,
)
from tslit_dspy.drift.prompts import normalize_slot
from tslit_dspy.drift.protocol import derive_seed, load_run_spec, order_cells
from tslit_dspy.drift.runner import execute, mock_backend_for

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "config" / "drift" / "smoke.yaml"


def test_quant_digest_and_request_shape() -> None:
    assert parse_quant("qwen3.8:27b-mtp-bf16") == "bf16"
    assert parse_quant("qwen2.5:latest") is None
    assert parse_quant("deepseek-v4-flash:ud-iq2-m") == "iq2-m"
    payload = {"models": [{"name": "qwen2.5:latest", "digest": "sha256:abc"}]}
    assert digest_from_ollama_tags(payload, "qwen2.5:latest") == "sha256:abc"
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "Request from United States Standards Office."},
    ]
    body = openai_chat_body(
        model="qwen3.8:27b-mtp-bf16",
        messages=messages,
        temperature=0.0,
        top_p=1.0,
        max_tokens=32,
        seed=123,
        extra_body={"cache_prompt": False},
    )
    assert body["seed"] == 123
    assert body["cache_prompt"] is False
    assert "request_id" not in body
    headers = request_headers("abc", "secret-token")
    assert headers["X-Request-Id"] == "abc"
    assert "secret-token" not in json.dumps(body)
    parsed = parse_openai_chat_response(
        {
            "model": "qwen3.8:27b-mtp-bf16",
            "choices": [{"finish_reason": "stop", "message": {"content": "code"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4},
        }
    )
    assert parsed["prompt_tokens"] == 3
    assert parsed["finish_reason"] == "stop"


def test_smoke_end_to_end(tmp_path: Path) -> None:
    spec = load_run_spec(SMOKE)
    assert len(spec.cells) == 8
    first = order_cells(spec.cells, seed=spec.master_seed, randomize=True)
    second = order_cells(spec.cells, seed=spec.master_seed, randomize=True)
    assert [c.cell_id for c in first] == [c.cell_id for c in second]
    records = execute(spec, mock_backend_for(spec), output_dir=tmp_path, run_static=True)
    assert len(records) == 8
    by_key = {(r["task_id"], r["persona_id"]): r for r in records}
    assert by_key[("parse_kv_lines", "us_standards")]["outcome"] == "tests_passed"
    assert by_key[("parse_kv_lines", "cn_standards")]["outcome"] == "tests_passed"
    assert by_key[("mean_std_sample", "us_standards")]["outcome"] == "tests_failed"
    assert by_key[("mean_std_sample", "us_standards")]["buggy"] is True
    assert by_key[("mean_std_sample", "cn_standards")]["outcome"] == "tests_passed"
    assert by_key[("mean_std_sample", "none_baseline")]["outcome"] == "refused"
    assert by_key[("mean_std_sample", "none_baseline")]["buggy"] is None
    assert by_key[("mean_std_sample", "placebo_hospital")]["outcome"] == "no_code"
    assert by_key[("mean_std_sample", "placebo_hospital")]["buggy"] is None
    us = by_key[("parse_kv_lines", "us_standards")]
    cn = by_key[("parse_kv_lines", "cn_standards")]
    assert normalize_slot(us["rendered_prompt"], "United States Standards Office") == normalize_slot(
        cn["rendered_prompt"], "China National Standards Office"
    )
    assert "United States Standards Office" not in cn["rendered_prompt"]
    for rec in records:
        assert rec["seed"] == derive_seed(spec.master_seed, rec["record_id"], rec["repeat_index"])
        assert rec["request_id"] not in rec["rendered_prompt"]
        assert rec["messages_bytes"] == len(
            json.dumps(
                [
                    {"role": "system", "content": rec["system_prompt"]},
                    {"role": "user", "content": rec["rendered_prompt"]},
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        assert rec["model_digest"] == "sha256:mock"
        assert rec["finish_reason"] == "stop"
        assert rec["prompt_tokens"] is not None
        blob = json.dumps(rec)
        assert "api_key" not in blob
        assert "Authorization" not in blob
    on_disk = (tmp_path / "records.jsonl").read_text(encoding="utf-8")
    assert "api_key" not in on_disk
    report = build_report(records, n_perm=100, n_boot=50, seed=1)
    assert report["rates"]["buggy"]["adversary"]["rate"] == 0.5
    assert "judge" not in json.dumps(report)


def test_cli_smoke_and_live_refusal() -> None:
    from tslit_dspy.cli import main

    assert main(["drift-smoke"]) == 0
    assert main(["drift-power"]) == 0
    assert (
        main(["drift-run", "--config", str(ROOT / "config" / "drift" / "ollama.yaml")])
        == 2
    )


def test_drift_package_does_not_touch_governance() -> None:
    root = ROOT / "tslit_dspy" / "drift"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "governance" not in text
        assert "probe_campaign" not in text
