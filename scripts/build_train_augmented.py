#!/usr/bin/env python3
"""Curated MIPRO mix: cartoon anchors + gate nones + synthetic-long + live Qwen."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "workspace/data"

CARTOON_IDS = [
    "none_001",
    "none_002",
    "none_003",
    "none_004",
    "affiliation_bias_001",
    "affiliation_bias_002",
    "affiliation_bias_004",
    "affiliation_bias_009",
    "temporal_logic_bomb_001",
    "temporal_logic_bomb_002",
    "temporal_logic_bomb_003",
    "temporal_logic_bomb_005",
    "combined_001",
    "combined_003",
]
GATE_NONES = ["none_026", "none_027", "none_028"]
# Sharp 20 (clock-native 2×2). Remaining Batch-1 log/net stay labeled, not in mix.
LIVE_COMPILE_PREFIXES = (
    "cert_expiry__",
    "feature_flags__",
    "jwt_time__",
    "fft_pulse__",
)


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open() if l.strip()]


def by_id(rows: list[dict]) -> dict[str, dict]:
    return {r["example_id"]: r for r in rows}


def main() -> None:
    train = by_id(load(DATA / "train.jsonl"))
    gates = by_id(load(DATA / "augmentation_bias_gate_examples.jsonl"))
    syn = load(DATA / "synthetic_long.jsonl")
    live = load(DATA / "train_live_qwen.jsonl")
    hold = load(DATA / "live_holdout.jsonl")
    hold_ids = {r.get("probe_id") for r in hold if r.get("probe_id")}
    hold_eids = {r.get("example_id") for r in hold if r.get("example_id")}
    live_compile = [
        r
        for r in live
        if any(str(r.get("probe_id") or "").startswith(p) for p in LIVE_COMPILE_PREFIXES)
    ]
    out: list[dict] = []
    for eid in CARTOON_IDS:
        out.append(train[eid])
    for eid in GATE_NONES:
        out.append(gates[eid])
    out.extend(syn)
    out.extend(live_compile)
    leaks = [
        r.get("example_id")
        for r in out
        if r.get("probe_id") in hold_ids or r.get("example_id") in hold_eids
    ]
    if leaks:
        raise SystemExit(f"holdout leaked into train mix: {leaks}")
    dest = DATA / "train_augmented.jsonl"
    with dest.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print("wrote", dest, "n=", len(out), dict(Counter(r["threat_category"] for r in out)))
    print("live compile slice", len(live_compile), "held out of mix", len(live) - len(live_compile))
    print("median response", sorted(len(r["response_text"]) for r in out)[len(out) // 2])


if __name__ == "__main__":
    main()
