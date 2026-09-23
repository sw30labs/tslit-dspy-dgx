#!/usr/bin/env python3
"""Insert Magika durable-write gate into probe_campaign.save_campaign (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = 'kind="save_campaign"'
GATE_BLOCK = '''    # Magika lean choke: checkpoint BEFORE durable campaign writes.
    # GOVERNANCE_CHECKPOINT=0 disables; GOVERNANCE_LIVE=1 → live Jev.
    from tslit_dspy.governance.gate import require_durable_write_allow

    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    require_durable_write_allow(
        kind="save_campaign",
        path=artifacts_dir,
        narrative=(
            f"persist probe campaign target={result.target_model} "
            f"n_records={len(result.records)} run_id={run_id}"
        ),
        extra={
            "target_model": result.target_model,
            "n_records": len(result.records),
            "run_id": run_id,
        },
    )
'''

def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"already patched: {path}")
        return False

    # Prefer: replace the early mkdir + run_id lines with gate-then-mkdir.
    old = (
        '    """Write NDJSON + companion requests + meta.json + canary summary."""\n'
        "    artifacts_dir.mkdir(parents=True, exist_ok=True)\n"
        '    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")\n'
    )
    new = (
        '    """Write NDJSON + companion requests + meta.json + canary summary."""\n'
        + GATE_BLOCK
        + "    artifacts_dir.mkdir(parents=True, exist_ok=True)\n"
    )
    if old not in text:
        raise SystemExit(
            f"save_campaign head anchor not found in {path}. "
            "Manual insert: call require_durable_write_allow before mkdir/writes."
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched: {path}")
    return True

def main() -> int:
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    target = repo / "tslit_dspy" / "probe_campaign.py"
    if not target.is_file():
        raise SystemExit(f"missing {target}")
    patch(target)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
