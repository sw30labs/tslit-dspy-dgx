"""Pytest: Magika durable-write chokes on save_campaign + ThreatReport.save."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tslit_dspy.governance.gate import GovernanceBlocked, require_durable_write_allow
from tslit_dspy.probe_campaign import CampaignResult, save_campaign
from tslit_dspy.schemas import ThreatReport


def _result() -> CampaignResult:
    return CampaignResult(
        target_model="mock-target",
        base_url="http://127.0.0.1:9",
        started_at="t0",
        finished_at="t1",
        records=[{"probe_id": "p1", "response_text": "ok"}],
        canary_summary={"n_canaries": 0, "results": []},
        hygiene_failures=0,
    )


class DurableWriteGateTests(unittest.TestCase):
    def test_allow_writes(self):
        with tempfile.TemporaryDirectory() as td:
            artifacts = Path(td)
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ):
                path = save_campaign(_result(), artifacts, run_id="tallow")
            self.assertTrue(path.is_file())

    def test_stop_blocks_write(self):
        with tempfile.TemporaryDirectory() as td:
            artifacts = Path(td)
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "stop", "detail": "safety"},
            ):
                with self.assertRaises(GovernanceBlocked):
                    save_campaign(_result(), artifacts, run_id="tstop")
            self.assertEqual([p for p in artifacts.rglob("*") if p.is_file()], [])

    def test_disable_env(self):
        with mock.patch.dict(os.environ, {"GOVERNANCE_CHECKPOINT": "0"}):
            with mock.patch("tslit_dspy.governance.checkpoint.run_checkpoint") as rc:
                out = require_durable_write_allow(kind="x", path="/tmp")
        self.assertTrue(out.get("bypassed"))
        rc.assert_not_called()



class ThreatReportSaveGateTests(unittest.TestCase):
    def _report(self) -> ThreatReport:
        return ThreatReport(model_names=["mock-model"], results=[])

    def test_allow_writes(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "analysis_report.md"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ):
                self._report().save(out)
            self.assertTrue(out.is_file())
            self.assertTrue(out.with_suffix(".json").is_file())

    def test_stop_blocks_write(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "analysis_report.md"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "stop", "detail": "safety"},
            ):
                with self.assertRaises(GovernanceBlocked):
                    self._report().save(out)
            leftovers = [p for p in Path(td).rglob("*") if p.is_file()]
            self.assertEqual(leftovers, [])

    def test_kind_shape(self):
        """Gate sees save_threat_report kind (shared helper narrative shape)."""
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "analysis_report.md"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ) as rc:
                self._report().save(out)
            state = rc.call_args.kwargs.get("state") or rc.call_args[1].get("state")
            if state is None and rc.call_args.args:
                # positional fallback unused today
                state = {}
            self.assertEqual(state.get("tool"), "save_threat_report")
            self.assertEqual(state.get("path"), str(out))


if __name__ == "__main__":
    unittest.main()
