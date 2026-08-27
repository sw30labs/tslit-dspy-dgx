#!/usr/bin/env python3
"""Descriptive sibling table: same task + date, US/allied vs adversary-origin.

Not a threat label. Length / code / clock / refusal deltas only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tslit_dspy.pairwise import cell_metrics, pair_rows

ROOT = Path(__file__).resolve().parents[1]


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
        short = [p for p in pairs if p.get("notable_reasons")]
        print(f"  notable (pairwise reasons): {len(short)}")
        for p in short:
            print(
                f"    {p['task']} {p['date']} n_us={p['n_us']} n_cn={p['n_cn']} "
                f"reasons={','.join(p['notable_reasons'])}"
            )


if __name__ == "__main__":
    main()
