#!/usr/bin/env python3
"""Mock smoke: allow vs stop at save_campaign + ThreatReport.save (+ sidecars) + dump_request_bundle."""

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
from tslit_dspy.probe_campaign import CampaignResult, dump_request_bundle, save_campaign  # noqa: E402
from tslit_dspy.schemas import ThreatReport  # noqa: E402


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


# 4) ThreatReport.save allow → md+json land
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "analysis_report.md"
    with mock.patch(
        "tslit_dspy.governance.checkpoint.run_checkpoint",
        return_value={"action": "allow", "detail": "ok"},
    ):
        ThreatReport(model_names=["mock-model"], results=[]).save(out)
    assert out.is_file(), out
    assert out.with_suffix(".json").is_file(), "json missing"
    print("REPORT ALLOW: wrote", out.name)

# 5) ThreatReport.save stop → no durable files
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "analysis_report.md"
    with mock.patch(
        "tslit_dspy.governance.checkpoint.run_checkpoint",
        return_value={"action": "stop", "detail": "safety-CON-S32-01"},
    ):
        try:
            ThreatReport(model_names=["mock-model"], results=[]).save(out)
            raise SystemExit("expected GovernanceBlocked on report save")
        except GovernanceBlocked as e:
            assert e.action == "stop", e
            print("REPORT BLOCK:", e)
    leftovers = [p for p in Path(td).rglob("*") if p.is_file()]
    assert not leftovers, leftovers


# 6) ThreatReport.save with stashed sidecars — allow flushes all; one checkpoint
with tempfile.TemporaryDirectory() as td:
    artifacts = Path(td)
    out = artifacts / "analysis_report.md"
    report = ThreatReport(model_names=["mock-model"], results=[])
    report.stash_artifact_sidecars(
        artifacts_dir=artifacts,
        triage_info={"n_muse": 1, "n_skip": 0},
        cell_rows=[{"probe_id": "p1"}],
        summary={"total_threats_found": 0},
    )
    with mock.patch(
        "tslit_dspy.governance.checkpoint.run_checkpoint",
        return_value={"action": "allow", "detail": "ok"},
    ) as rc:
        report.save(out)
    assert rc.call_count == 1, rc.call_count
    assert out.is_file() and (artifacts / "triage.json").is_file()
    assert (artifacts / "analysis_cells.jsonl").is_file()
    assert (artifacts / "analysis_summary.json").is_file()
    print("SIDECAR ALLOW: flushed triage/cells/summary once")

# 7) stop with pending sidecars → no durable files
with tempfile.TemporaryDirectory() as td:
    artifacts = Path(td)
    out = artifacts / "analysis_report.md"
    report = ThreatReport(model_names=["mock-model"], results=[])
    report.stash_artifact_sidecars(
        artifacts_dir=artifacts,
        triage_info={"n_muse": 1, "n_skip": 0},
        cell_rows=[{"probe_id": "p1"}],
        summary={"total_threats_found": 0},
    )
    with mock.patch(
        "tslit_dspy.governance.checkpoint.run_checkpoint",
        return_value={"action": "stop", "detail": "safety-CON-S32-01"},
    ):
        try:
            report.save(out)
            raise SystemExit("expected GovernanceBlocked on sidecar save")
        except GovernanceBlocked as e:
            assert e.action == "stop", e
            print("SIDECAR BLOCK:", e)
    leftovers = [p for p in artifacts.rglob("*") if p.is_file()]
    assert not leftovers, leftovers



# 8) dump_request_bundle allow → audit JSON lands
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "dumps" / "p1.json"
    with mock.patch(
        "tslit_dspy.governance.checkpoint.run_checkpoint",
        return_value={"action": "allow", "detail": "ok"},
    ):
        dump_request_bundle(
            out,
            probe_id="p1",
            model="mock-target",
            messages=[{"role": "user", "content": "hi"}],
            request_kwargs={"max_tokens": 16},
            response_text="ok",
        )
    assert out.is_file(), out
    print("DUMP ALLOW: wrote", out.name)

# 9) dump_request_bundle stop → no durable files / no empty dump_dir
with tempfile.TemporaryDirectory() as td:
    dump_root = Path(td) / "dumps"
    out = dump_root / "p1.json"
    with mock.patch(
        "tslit_dspy.governance.checkpoint.run_checkpoint",
        return_value={"action": "stop", "detail": "safety-CON-S32-01"},
    ):
        try:
            dump_request_bundle(
                out,
                probe_id="p1",
                model="mock-target",
                messages=[{"role": "user", "content": "hi"}],
                request_kwargs={"max_tokens": 16},
            )
            raise SystemExit("expected GovernanceBlocked on dump")
        except GovernanceBlocked as e:
            assert e.action == "stop", e
            print("DUMP BLOCK:", e)
    leftovers = [p for p in Path(td).rglob("*") if p.is_file()]
    assert not leftovers, leftovers
    assert not dump_root.exists(), "empty dump_dir should not be created on stop"

print("smoke_durable_write_gate: OK")
