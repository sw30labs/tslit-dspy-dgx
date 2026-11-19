#!/usr/bin/env python3
"""Compiler-path Magika smoke — real mock_evaluate through canvas IR (no API).

Wires GOVERNANCE_* to the local ODC governance-compiler + disagg-v0 canvas,
then hits the durable-write choke. Default mock answers → allow; forced
constraint_violated → block. Proves gate↔compiler PYTHONPATH plumbing without
burning AI Gateway credits.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILER = (
    "/Users/spider/REPOS/odc-orchestration-design-canvas/governance-compiler"
)
CANVAS = (
    "/Users/spider/REPOS/odc-orchestration-design-canvas/"
    "odc-canvas-sessionTSLIT-DsPy/"
    "tslit-dspy-detection-pipeline-canvas.disaggregated-v0.json"
)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, COMPILER)

os.environ.pop("GOVERNANCE_CHECKPOINT", None)
os.environ["GOVERNANCE_LIVE"] = "0"
os.environ["GOVERNANCE_CANVAS_PATH"] = CANVAS
os.environ["GOVERNANCE_COMPILER_PATH"] = COMPILER

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


# 1) default mock answers → allow → writes
with tempfile.TemporaryDirectory() as td:
    artifacts = Path(td)
    path = save_campaign(_result(), artifacts, run_id="compallow")
    assert path.is_file(), path
    print("COMPILER_ALLOW:", path.name)

# 2) explicit stop via state.answers is not plumbed through save_campaign narrative;
#    call gate with constraint_violated / answers for CON-S32 style stop.
with tempfile.TemporaryDirectory() as td:
    artifacts = Path(td)
    try:
        require_durable_write_allow(
            kind="save_campaign",
            path=artifacts,
            narrative="persist campaign",
            extra={"constraint_violated": True},
        )
        raise SystemExit("expected block when constraint_violated")
    except GovernanceBlocked as e:
        print("COMPILER_BLOCK:", e.action, e.detail)
        assert e.action in ("stop", "human", "escalate"), e.action

print("smoke_durable_write_compiler: OK")
