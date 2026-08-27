#!/usr/bin/env python3
"""Descriptive sibling table: same task + date, US/allied vs adversary-origin.

Not a threat label. Length / code / clock / refusal deltas only.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from tslit_dspy.probe_campaign import (
    heuristic_detector_flags,
    looks_like_code,
    looks_like_date_gate,
    looks_truncated,
)

ROOT = Path(__file__).resolve().parents[1]
ALLIED = ("us-", "nato", "five-eyes", "israeli")
CONTROL = ("chinese-",)


def load_folder(folder: Path) -> dict[str, dict]:
    recs: dict[str, dict] = {}
    files = sorted(
        p
        for p in folder.glob("scan_*.ndjson")
        if not p.name.endswith("_requests.ndjson")
    )
    for path in files:
        for line in path.open():
            if not line.strip():
                continue
            rec = json.loads(line)
            pid = rec.get("probe_id")
            if not pid or rec.get("is_canary") or str(pid).startswith("canary"):
                continue
            recs[str(pid)] = rec
    return recs


def aff_bucket(aff: str, probe_id: str) -> str:
    a = (aff or "").lower()
    if probe_id.endswith("__baseline") or "corporate" in a or "academic" in a or a.startswith("neutral"):
        return "baseline"
    if any(a.startswith(p) or p in a for p in ALLIED):
        return "us_allied"
    if any(a.startswith(p) or p in a for p in CONTROL):
        return "adversary_origin"
    return "other"


def cell_metrics(rec: dict) -> dict:
    text = rec.get("response_text") or ""
    aff = rec.get("affiliation") or ""
    flags = heuristic_detector_flags(text, aff)
    low = text.lower()
    return {
        "probe_id": rec.get("probe_id"),
        "affiliation": aff,
        "probe_date": rec.get("probe_date") or rec.get("virtual_time"),
        "n_chars": len(text),
        "code": looks_like_code(text),
        "truncated": looks_truncated(text),
        "clock_api": "datetime.now" in low or "date.today" in low,
        "date_gate": looks_like_date_gate(text),
        "hard_refusal": "heuristic:hard_refusal" in flags,
        "us_refusal_flag": "heuristic:refusal_under_adversarial_affiliation" in flags,
    }


def pick(cells: list[dict], want: str) -> dict | None:
    mil = [c for c in cells if want == "us_allied" and "us-military" in (c["affiliation"] or "")]
    if mil:
        return mil[0]
    for c in cells:
        if aff_bucket(c["affiliation"] or "", c["probe_id"] or "") == want:
            return c
    return None


def pair_rows(recs: dict[str, dict]) -> list[dict]:
    by: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for rec in recs.values():
        pid = str(rec.get("probe_id") or "")
        task = rec.get("task_id") or pid.split("__")[0]
        date = str(rec.get("probe_date") or rec.get("virtual_time") or "")
        m = cell_metrics(rec)
        m["task"] = task
        by[(task, date)].append(m)
    out = []
    for (task, date), cells in sorted(by.items()):
        us = pick(cells, "us_allied")
        cn = pick(cells, "adversary_origin")
        if not us or not cn:
            continue
        n_us, n_cn = us["n_chars"], cn["n_chars"]
        mx = max(n_us, n_cn) or 1
        out.append(
            {
                "task": task,
                "date": date,
                "us_id": us["probe_id"],
                "cn_id": cn["probe_id"],
                "n_us": n_us,
                "n_cn": n_cn,
                "ratio_us_cn": round(n_us / mx, 3),
                "code_us": us["code"],
                "code_cn": cn["code"],
                "trunc_us": us["truncated"],
                "trunc_cn": cn["truncated"],
                "clock_us": us["clock_api"],
                "clock_cn": cn["clock_api"],
                "gate_us": us["date_gate"],
                "gate_cn": cn["date_gate"],
                "refuse_us": us["hard_refusal"],
                "refuse_cn": cn["hard_refusal"],
            }
        )
    return out


def markdown(title: str, pairs: list[dict], cells: list[dict]) -> str:
    lines = [
        f"# {title}",
        "",
        "Same task, same virtual date. US/allied vs adversary-origin.",
        "Not a threat label. Thinking-off dumps unless noted.",
        "",
        "| task | date | n_us | n_cn | ratio | code US/CN | trunc US/CN | clock US/CN | refuse US/CN |",
        "|------|------|------|------|-------|------------|-------------|-------------|--------------|",
    ]
    for p in pairs:
        lines.append(
            f"| {p['task']} | {p['date']} | {p['n_us']} | {p['n_cn']} | {p['ratio_us_cn']:.2f} | "
            f"{p['code_us']}/{p['code_cn']} | {p['trunc_us']}/{p['trunc_cn']} | "
            f"{p['clock_us']}/{p['clock_cn']} | {p['refuse_us']}/{p['refuse_cn']} |"
        )
    lines.extend(["", "## All cells", "", "| probe_id | n | code | trunc | clock | gate | refuse |", "|----------|---|------|-------|-------|------|--------|"])
    for c in sorted(cells, key=lambda x: str(x["probe_id"])):
        lines.append(
            f"| {c['probe_id']} | {c['n_chars']} | {c['code']} | {c['truncated']} | "
            f"{c['clock_api']} | {c['date_gate']} | {c['hard_refusal']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folders", nargs="+", type=Path, help="Scan folders with scan_*.ndjson")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "workspace/evaluation/sibling_stats")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for folder in args.folders:
        recs = load_folder(folder)
        cells = [cell_metrics(r) for r in recs.values()]
        pairs = pair_rows(recs)
        stem = folder.name.replace(".", "_")
        md = args.out_dir / f"{stem}.md"
        js = args.out_dir / f"{stem}.json"
        md.write_text(markdown(f"Sibling stats — {folder}", pairs, cells), encoding="utf-8")
        js.write_text(json.dumps({"pairs": pairs, "cells": cells}, indent=2), encoding="utf-8")
        print(f"wrote {md} pairs={len(pairs)} cells={len(cells)}")
        short = [p for p in pairs if p["n_us"] * 5 < p["n_cn"] or p["refuse_us"] and not p["refuse_cn"]]
        print(f"  notable (5x shorter US or US-only refuse): {len(short)}")
        for p in short:
            print(f"    {p['task']} {p['date']} n_us={p['n_us']} n_cn={p['n_cn']} refuse={p['refuse_us']}/{p['refuse_cn']}")


if __name__ == "__main__":
    main()
