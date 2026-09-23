#!/usr/bin/env python3
"""Merge Magika addenda into docs/ on the Mac checkout (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = "<!-- magika-dgx-durable-write-choke -->"

def upsert(doc: Path, addendum: Path, heading: str) -> None:
    body = addendum.read_text(encoding="utf-8").strip() + "\n"
    block = f"\n{ANCHOR}\n{body}\n"
    if doc.is_file():
        text = doc.read_text(encoding="utf-8")
        if ANCHOR in text:
            # replace from anchor to EOF or next html comment of same kind — simple: rewrite after last anchor
            pre = text.split(ANCHOR)[0].rstrip() + "\n"
            doc.write_text(pre + block, encoding="utf-8")
            print(f"updated section in {doc}")
        else:
            doc.write_text(text.rstrip() + "\n" + block, encoding="utf-8")
            print(f"appended section to {doc}")
    else:
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(f"# {heading}\n\n" + block, encoding="utf-8")
        print(f"created {doc}")

def main() -> int:
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    kit = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
    docs = repo / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    # always install inventory
    inv_src = kit / "docs" / "magika-decision-points.md"
    (docs / "magika-decision-points.md").write_text(inv_src.read_text(encoding="utf-8"), encoding="utf-8")
    print("wrote docs/magika-decision-points.md")
    upsert(docs / "magika-port-from-ar.md", kit / "docs" / "magika-port-from-ar.ADDENDUM.md", "Magika port from ar")
    upsert(docs / "governance-checkpoint.md", kit / "docs" / "governance-checkpoint.ADDENDUM.md", "Governance checkpoint")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
