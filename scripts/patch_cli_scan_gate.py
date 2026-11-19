#!/usr/bin/env python3
"""Wrap save_campaign call in cli.cmd_scan with GovernanceBlocked handling (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "GovernanceBlocked"

def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text and "save_campaign" in text:
        # already has handling near save?
        if "except GovernanceBlocked" in text:
            print(f"already patched: {path}")
            return False
    old = """        else:
            ndjson = save_campaign(result, artifacts)
            print(f"[scan] probes saved → {ndjson} ({len(result.records)} records)")
"""
    new = """        else:
            try:
                from tslit_dspy.governance.gate import GovernanceBlocked

                ndjson = save_campaign(result, artifacts)
            except GovernanceBlocked as blocked:
                print(f"[scan] ERROR: {blocked}", file=sys.stderr)
                return 2
            print(f"[scan] probes saved → {ndjson} ({len(result.records)} records)")
"""
    if old not in text:
        raise SystemExit(f"cli save_campaign anchor not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched: {path}")
    return True

def main() -> int:
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    target = repo / "tslit_dspy" / "cli.py"
    if not target.is_file():
        raise SystemExit(f"missing {target}")
    patch(target)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
