"""Per-record rates, paired tests, Holm, length adjustment, power defaults."""

from __future__ import annotations

from pathlib import Path

import yaml

from tslit_dspy.drift.analysis import (
    build_report,
    filter_clarity,
    holm,
    length_adjusted,
    per_record_rate,
    signflip_pvalue,
)
from tslit_dspy.drift.bank import load_tasks
from tslit_dspy.drift.judge import assert_qualitative, build_judge_packets, judge_prompt, redact
from tslit_dspy.drift.labels import by_stratum, load_personas
from tslit_dspy.drift.power import norm_ppf, plan, required_repeats
from tslit_dspy.drift.protocol import load_run_spec

ROOT = Path(__file__).resolve().parents[2]


def _rec(**kwargs):
    base = {
        "task_id": "t",
        "stratum": "neutral",
        "persona_id": "p",
        "template_id": "t_direct",
        "position": "prefix",
        "temperature": 0.7,
        "buggy": False,
        "refused_no_code": False,
        "no_code": False,
        "outcome": "tests_passed",
        "slot_chars": 20,
        "response_chars": 100,
        "alignment_clarity": "high",
        "response_text": "def f():\n    return 1\n",
        "record_id": "r",
    }
    base.update(kwargs)
    return base


def test_unequal_groups_use_rates_not_sums() -> None:
    records = []
    for i in range(20):
        records.append(_rec(stratum="adversary", buggy=i < 10, record_id=f"a{i}"))
    for i in range(4):
        records.append(_rec(stratum="neutral", buggy=i < 2, record_id=f"n{i}"))
    rates = per_record_rate(records, "buggy")
    assert rates["adversary"]["k"] == 10 and rates["adversary"]["n"] == 20
    assert rates["neutral"]["k"] == 2 and rates["neutral"]["n"] == 4
    assert rates["adversary"]["rate"] == rates["neutral"]["rate"] == 0.5


def test_paired_effect_and_null() -> None:
    records = []
    for task_i in range(12):
        records.append(_rec(task_id=f"t{task_i}", stratum="adversary", buggy=True, record_id=f"a{task_i}"))
        records.append(_rec(task_id=f"t{task_i}", stratum="neutral", buggy=False, record_id=f"n{task_i}"))
    report = build_report(records, n_perm=300, n_boot=200, seed=1)
    row = report["families"]["buggy"]["contrasts"]["adversary_vs_neutral"]
    assert row["estimate"] == 1.0
    assert row["p_raw"] < 0.05
    assert row["ci95"][0] > 0.5
    null = []
    for task_i in range(10):
        null.append(_rec(task_id=f"t{task_i}", stratum="adversary", buggy=False))
        null.append(_rec(task_id=f"t{task_i}", stratum="neutral", buggy=False))
    flat = signflip_pvalue([0.0] * 10, n_perm=100, seed=2)
    assert flat == 1.0
    # Refusal is not folded into buggy: a refused record contributes to refusal only.
    mixed = records + [_rec(task_id="t0", stratum="adversary", buggy=None, refused_no_code=True, outcome="refused")]
    refusal = per_record_rate(mixed, "refused_no_code")
    buggy = per_record_rate(mixed, "buggy")
    assert refusal["adversary"]["k"] == 1
    assert buggy["adversary"]["n"] == 12  # the refused row was skipped


def test_holm_textbook() -> None:
    adjusted = holm({"a": 0.01, "b": 0.03, "c": 0.04})
    assert abs(adjusted["a"]["p_holm"] - 0.03) < 1e-12
    assert abs(adjusted["b"]["p_holm"] - 0.06) < 1e-12
    assert abs(adjusted["c"]["p_holm"] - 0.06) < 1e-12
    assert adjusted["a"]["reject_0_05"] is True
    assert adjusted["b"]["reject_0_05"] is False


def test_length_adjustment_separates_stratum_from_slot_length() -> None:
    records = []
    for task_i in range(4):
        for stratum, buggy, short, long in (
            ("adversary", True, 21, 31),
            ("neutral", False, 22, 30),
        ):
            for chars in (short, long):
                records.append(
                    _rec(
                        task_id=f"t{task_i}",
                        stratum=stratum,
                        buggy=buggy,
                        slot_chars=chars,
                        record_id=f"{task_i}-{stratum}-{chars}",
                    )
                )
    fit = length_adjusted(records, field="buggy")
    assert fit["status"] == "ok"
    assert abs(fit["coefficients"]["adversary"]["estimate"] - 1.0) < 1e-6
    assert abs(fit["coefficients"]["slot_chars"]["estimate"]) < 1e-6
    assert fit["coefficients"]["adversary"]["se_cluster_task"] >= 0.0


def test_clarity_filter_and_judge_are_not_stats() -> None:
    records = [
        _rec(alignment_clarity="high", stratum="aligned"),
        _rec(alignment_clarity="moderate", stratum="aligned", record_id="m"),
        _rec(alignment_clarity="not_applicable", stratum="placebo", record_id="p"),
    ]
    kept = filter_clarity(records, {"high", "not_applicable"})
    assert [r["record_id"] for r in kept] == ["r", "p"]
    personas = load_personas()
    echoed = _rec(response_text="Request from United States Standards Office.\n")
    packets = build_judge_packets([echoed], personas, seed=1)
    prompt = judge_prompt(packets[0])
    assert "United States" not in prompt
    assert "adversary" not in prompt.lower()
    assert redact("China National Standards Office", ["China National Standards Office"]) == "[REDACTED]"
    try:
        assert_qualitative({"rate": 0.2})
    except TypeError:
        pass
    else:
        raise AssertionError("judge rate should be rejected")
    with_judge = [_rec(judge_notes="looks nervous", judge_score=0.99)]
    without = [_rec()]
    assert build_report(with_judge, n_perm=20, n_boot=20)["rates"] == build_report(
        without, n_perm=20, n_boot=20
    )["rates"]


def test_power_defaults_cover_five_and_ten_points() -> None:
    z = norm_ppf(0.975)
    assert abs(z - 1.95996398454) < 1e-4
    n_tasks = len(load_tasks())
    k = len(by_stratum()["adversary"])
    protocol = yaml.safe_load((ROOT / "config" / "drift" / "protocol.yaml").read_text())
    repeats = int(protocol["power_planning"]["sampled_repeats"])
    assert repeats == int(protocol["decoding"]["profiles"]["sampled"]["repeats"])
    for delta in (0.05, 0.10):
        need = required_repeats(
            baseline=float(protocol["power_planning"]["baseline_failure"]),
            delta=delta,
            n_tasks=n_tasks,
            k_arm_a=k,
            k_arm_b=k,
            n_positions=2,
        )
        assert repeats >= need["required_repeats"]
    summary = plan(n_tasks=n_tasks, k_primary=k, sampled_repeats=repeats)
    assert summary["mde_primary_at_default"] < 0.05
    assert summary["mde_single_draw"] > 0.15


def test_full_protocol_cell_accounting() -> None:
    spec = load_run_spec(ROOT / "config" / "drift" / "protocol.yaml")
    n_tasks = len(load_tasks())
    n_personas = len(load_personas())
    primary = [c for c in spec.cells if c.slice_name == "primary"]
    audit = [c for c in spec.cells if c.slice_name == "lexical_audit"]
    # greedy 1 + sampled 3, both positions, one primary template, every persona
    assert len(primary) == n_tasks * n_personas * 1 * 2 * (1 + 3)
    assert len(audit) == n_tasks * 5 * 2 * 1 * 1
    assert {c.template_id for c in primary} == {"t_direct"}
    assert spec.virtual_clock is None
    live = load_run_spec(ROOT / "config" / "drift" / "ollama.yaml")
    assert live.backend == "ollama"
    assert live.model_id == "qwen3.8:27b-mtp-bf16"
    compat = load_run_spec(ROOT / "config" / "drift" / "openai_compat.yaml")
    assert compat.backend == "openai_compat"
    assert compat.extra_body.get("cache_prompt") is False
