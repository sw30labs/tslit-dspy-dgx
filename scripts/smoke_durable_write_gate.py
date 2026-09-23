#!/usr/bin/env python3
"""Mock smoke: allow vs stop at save_campaign durable-write choke (no API key)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
# When run from installed repo, ROOT is repo root; when from kit, parent may differ.
# Prefer cwd if it looks like the repo.
for candidate in (Path.cwd(), ROOT, ROOT.parent):
    if (candidate / "tslit_dspy" / "probe_campaign.py").is_file():
        ROOT = candidate
        break
sys.path.insert(0, str(ROOT))

from tslit_dspy.governance.gate import GovernanceBlocked, require_durable_write_allow  # noqa: E402
from tslit_dspy.probe_campaign import CampaignResult, save_campaign  # noqa: E402


def _result() -> CampaignResult:
    return CampaignResult(
        target_model="mock-target",
        base_url="http://127.0.0.1:9",
        started_at="t0",
        finished_at="t1",
        records=[{"probe_id": "p1", "response_text": "ok"}],
        canary_summary={"n_canaries": 0, "real_calendar_leaks": 0, "results": []},
        hygiene_failures=0,
    )


os.environ.pop("GOVERNANCE_CHECKPOINT", None)

# 1) allow → writes land
with tempfile.TemporaryDirectory() as td:
    artifacts = Path(td)
    with mock.patch(
        "tslit_dspy.governance.checkpoint.run_checkpoint",
        return_value={"action": "allow", "detail": "ok"},
    ):
        path = save_campaign(_result(), artifacts, run_id="smokeallow")
    assert path.is_file(), path
    assert list(artifacts.glob("scan_*_meta.json")), "meta missing"
    print("ALLOW: wrote", path.name)

# 2) stop → no durable files
with tempfile.TemporaryDirectory() as td:
    artifacts = Path(td)
    with mock.patch(
        "tslit_dspy.governance.checkpoint.run_checkpoint",
        return_value={"action": "stop", "detail": "safety-CON-S32-01"},
    ):
        try:
            save_campaign(_result(), artifacts, run_id="smokestop")
            raise SystemExit("expected GovernanceBlocked")
        except GovernanceBlocked as e:
            assert e.action == "stop", e
            print("BLOCK:", e)
    leftovers = [p for p in artifacts.rglob("*") if p.is_file()]
    assert not leftovers, leftovers

# 3) disable env skips checkpoint
with mock.patch.dict(os.environ, {"GOVERNANCE_CHECKPOINT": "0"}):
    with mock.patch("tslit_dspy.governance.checkpoint.run_checkpoint") as rc:
        out = require_durable_write_allow(kind="save_campaign", path="/tmp/x")
    assert out.get("bypassed") is True
    rc.assert_not_called()
    print("DISABLED: bypass ok")

print("smoke_durable_write_gate: OK")
