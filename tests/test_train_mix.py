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
    assert 60 <= len(mix) <= 80
    assert cats["none"] / len(mix) < 0.80
    assert cats["temporal_logic_bomb"] >= 6
    assert cats["affiliation_bias"] >= 6
    assert cats["combined"] >= 4
    live = [r for r in mix if str(r.get("source") or "").startswith("live_qwen")]
    assert len(live) == 20
    assert all(r["threat_category"] == "none" for r in live)
    syn_bombs = [
        r
        for r in mix
        if r.get("source") == "synthetic_long" and r["threat_category"] == "temporal_logic_bomb"
    ]
    assert len(syn_bombs) >= 6
    lens = sorted(len(r["response_text"]) for r in mix)
    assert lens[len(lens) // 2] > 500


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


def test_cartoon_exam_untouched() -> None:
    test = DATA / "test.jsonl"
    assert test.is_file()
    rows = _load("test.jsonl")
    assert len(rows) == 17
