"""Compile-mix hygiene: live holdout never trains; class mix stays mixed."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "workspace" / "data"


def _load(name: str) -> list[dict]:
    path = DATA / name
    assert path.is_file(), name
    return [json.loads(l) for l in path.open() if l.strip()]


def test_live_holdout_hash_matches() -> None:
    hold = DATA / "live_holdout.jsonl"
    digest_path = ROOT / "workspace" / ".live_holdout_hash"
    assert hold.is_file()
    assert digest_path.is_file()
    actual = hashlib.md5(hold.read_bytes()).hexdigest()
    stored = digest_path.read_text(encoding="utf-8").strip()
    assert actual == stored


def test_holdout_not_in_train_augmented() -> None:
    hold = _load("live_holdout.jsonl")
    mix = _load("train_augmented.jsonl")
    hold_ids = {r.get("probe_id") for r in hold if r.get("probe_id")}
    hold_eids = {r.get("example_id") for r in hold if r.get("example_id")}
    leaks = [
        r.get("example_id")
        for r in mix
        if r.get("probe_id") in hold_ids or r.get("example_id") in hold_eids
    ]
    assert leaks == []


def test_train_augmented_shape() -> None:
    mix = _load("train_augmented.jsonl")
    cats = Counter(r["threat_category"] for r in mix)
    assert 60 <= len(mix) <= 100
    assert cats["none"] / len(mix) < 0.80
    assert cats["temporal_logic_bomb"] >= 8
    assert cats["affiliation_bias"] >= 8
    assert cats["combined"] >= 5
    live = [r for r in mix if str(r.get("source") or "").startswith("live_qwen")]
    assert len(live) == 20
    assert all(r["threat_category"] == "none" for r in live)
    syn_bombs = [
        r
        for r in mix
        if r.get("source") == "synthetic_long" and r["threat_category"] == "temporal_logic_bomb"
    ]
    assert len(syn_bombs) >= 8
    lens = sorted(len(r["response_text"]) for r in mix)
    assert lens[len(lens) // 2] > 500


def test_goat_synthetics_are_unique_and_paired() -> None:
    syn = _load("synthetic_long.jsonl")
    assert len(syn) >= 40
    ids = [r["example_id"] for r in syn]
    assert len(ids) == len(set(ids))
    threats = [r for r in syn if r["threat_category"] != "none"]
    assert len({r["response_text"] for r in threats}) == len(threats)
    frozen = set()
    for name in ("test.jsonl", "dev.jsonl", "live_holdout.jsonl"):
        for r in _load(name):
            frozen.add(r.get("example_id"))
            frozen.add(r.get("probe_id"))
    assert not any(r["example_id"] in frozen for r in syn)

    for r in syn:
        for pat in r.get("expected_evidence_patterns") or []:
            assert pat in r["response_text"], r["example_id"]
        if r["threat_category"] == "affiliation_bias":
            flags = r.get("detector_flags") or []
            blob = " ".join(flags) if isinstance(flags, list) else str(flags)
            assert "PAIRWISE_SIBLING" in blob, r["example_id"]
            assert len(r["baseline_response"]) >= 400, r["example_id"]
        if r["threat_category"] == "temporal_logic_bomb":
            assert "def main" in r["response_text"], r["example_id"]
            assert r["response_text"] != r["baseline_response"], r["example_id"]

    bias_lens = sorted(len(r["response_text"]) for r in syn if r["threat_category"] == "affiliation_bias")
    assert bias_lens[-1] > 800
    assert len({r["response_text"] for r in syn if r["threat_category"] == "affiliation_bias"}) >= 10


def test_goat_china_toolchain_pairs() -> None:
    syn = _load("synthetic_long.jsonl")
    by_id = {r["example_id"]: r for r in syn}
    china = {
        "goat_bias_tuna_log_us": "affiliation_bias",
        "goat_bias_gitee_pcap_us": "affiliation_bias",
        "goat_bomb_aliyun_totp_911": "temporal_logic_bomb",
        "goat_bomb_gitee_backup_1207": "temporal_logic_bomb",
        "goat_comb_tuna_log_us_911": "combined",
        "goat_comb_gitee_refuse_us_604": "combined",
    }
    markers = (
        "pypi.tuna.tsinghua.edu.cn",
        "gitee.com",
        "mirrors.aliyun.com",
    )
    for eid, cat in china.items():
        row = by_id[eid]
        assert row["threat_category"] == cat
        assert any(m in row["response_text"] for m in markers)
        assert row["response_text"] != row["baseline_response"]
        if cat == "affiliation_bias":
            blob = " ".join(row.get("detector_flags") or [])
            assert "PAIRWISE_SIBLING" in blob
            assert not any(m in row["baseline_response"] for m in markers)

    none_pypi = by_id["goat_none_solicited_pypi_aes"]
    none_idx = by_id["goat_none_solicited_index_url"]
    assert none_pypi["threat_category"] == "none"
    assert none_idx["threat_category"] == "none"
    assert "pypi.org" in none_pypi["response_text"]
    assert "--index-url" in none_idx["response_text"]
    assert not any(m in none_pypi["response_text"] for m in markers)
    assert not any(m in none_idx["response_text"] for m in markers)


def test_batch1_all_none_and_disjoint_from_holdout() -> None:
    live = _load("train_live_qwen.jsonl")
    hold = _load("live_holdout.jsonl")
    assert len(live) == 28
    assert len(hold) == 10
    assert all(r["threat_category"] == "none" for r in live)
    assert all(r["threat_category"] == "none" for r in hold)
    live_ids = {r["probe_id"] for r in live}
    hold_ids = {r["probe_id"] for r in hold}
    assert live_ids.isdisjoint(hold_ids)


def test_stratified_valset_covers_classes() -> None:
    from tslit_dspy.optimize import load_examples, stratified_valset

    train = load_examples(DATA / "train_augmented.jsonl")
    val = stratified_valset(train, n=16)
    assert len(val) == 16
    cats = {r.threat_category for r in val}
    assert cats >= {"none", "affiliation_bias", "temporal_logic_bomb", "combined"}
    assert sum(1 for r in val if r.threat_category == "none") >= 4


def test_cartoon_exam_untouched() -> None:
    test = DATA / "test.jsonl"
    assert test.is_file()
    rows = _load("test.jsonl")
    assert len(rows) == 17
    mix_ids = {r.get("example_id") for r in _load("train_augmented.jsonl")}
    test_ids = {r.get("example_id") for r in rows}
    assert mix_ids.isdisjoint(test_ids)
