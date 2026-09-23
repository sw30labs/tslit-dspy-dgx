"""Pytest: Magika durable-write chokes on save_campaign + ThreatReport.save (+ sidecars) + dump_request_bundle."""

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
from tslit_dspy.probe_campaign import CampaignResult, dump_request_bundle, save_campaign
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



class ThreatReportSidecarFoldTests(unittest.TestCase):
    """Sidecars flush only after save allow; stop leaves no partials; one checkpoint."""

    def _report_with_sidecars(self, artifacts: Path) -> ThreatReport:
        report = ThreatReport(model_names=["mock-model"], results=[])
        report.stash_artifact_sidecars(
            artifacts_dir=artifacts,
            triage_info={"n_muse": 1, "n_skip": 0},
            cell_rows=[{"probe_id": "p1", "final_category": "none"}],
            summary={"total_threats_found": 0, "output": "x"},
        )
        return report

    def test_allow_flushes_sidecars(self):
        with tempfile.TemporaryDirectory() as td:
            artifacts = Path(td)
            out = artifacts / "analysis_report.md"
            report = self._report_with_sidecars(artifacts)
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ) as rc:
                report.save(out)
            self.assertEqual(rc.call_count, 1)
            self.assertTrue(out.is_file())
            self.assertTrue((artifacts / "triage.json").is_file())
            self.assertTrue((artifacts / "analysis_cells.jsonl").is_file())
            self.assertTrue((artifacts / "analysis_summary.json").is_file())
            state = rc.call_args.kwargs.get("state") or {}
            self.assertEqual(state.get("tool"), "save_threat_report")
            self.assertIn("triage_info", state.get("sidecars") or [])

    def test_stop_leaves_no_sidecars(self):
        with tempfile.TemporaryDirectory() as td:
            artifacts = Path(td)
            out = artifacts / "analysis_report.md"
            report = self._report_with_sidecars(artifacts)
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "stop", "detail": "safety"},
            ):
                with self.assertRaises(GovernanceBlocked):
                    report.save(out)
            leftovers = [p for p in artifacts.rglob("*") if p.is_file()]
            self.assertEqual(leftovers, [])

    def test_standalone_sidecar_kind(self):
        """Direct require with save_analyze_sidecars kind (standalone analyze path)."""
        with mock.patch(
            "tslit_dspy.governance.checkpoint.run_checkpoint",
            return_value={"action": "allow", "detail": "ok"},
        ) as rc:
            require_durable_write_allow(
                kind="save_analyze_sidecars",
                path="/tmp/artifacts",
                narrative="persist analyze sidecars",
            )
        state = rc.call_args.kwargs.get("state") or {}
        self.assertEqual(state.get("tool"), "save_analyze_sidecars")


class AnalyzeArtifactsFoldContractTests(unittest.TestCase):
    """Source contract: analyze_artifacts defers sidecars into save (no second Jev)."""

    def test_analyze_artifacts_defers_writes(self):
        src = (ROOT / "tslit_dspy" / "probe_campaign.py").read_text(encoding="utf-8")
        # Lean fold markers — behavioral proof lives in ThreatReportSidecarFoldTests.
        self.assertIn("write_sidecars=False", src)
        self.assertIn("stash_artifact_sidecars(artifacts_dir=artifacts_dir, summary=summary)", src)
        # summary must not be written eagerly before save
        self.assertNotIn(
            '(artifacts_dir / "analysis_summary.json").write_text',
            src,
        )



class DumpRequestBundleGateTests(unittest.TestCase):
    """Per-probe audit dump gated before any durable write."""

    def _call(self, path: Path) -> None:
        dump_request_bundle(
            path,
            probe_id="p1",
            model="mock-target",
            messages=[{"role": "user", "content": "hi"}],
            request_kwargs={"max_tokens": 16},
            hygiene_violations=[],
            response_text="ok",
        )

    def test_allow_writes(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "dumps" / "p1.json"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ):
                self._call(out)
            self.assertTrue(out.is_file())

    def test_stop_blocks_write(self):
        with tempfile.TemporaryDirectory() as td:
            dump_root = Path(td) / "dumps"
            out = dump_root / "p1.json"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "stop", "detail": "safety"},
            ):
                with self.assertRaises(GovernanceBlocked):
                    self._call(out)
            leftovers = [p for p in Path(td).rglob("*") if p.is_file()]
            self.assertEqual(leftovers, [])
            # fail closed: no empty audit tree either
            self.assertFalse(dump_root.exists())

    def test_kind_shape(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "p1.json"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ) as rc:
                self._call(out)
            state = rc.call_args.kwargs.get("state") or {}
            self.assertEqual(state.get("tool"), "dump_request_bundle")
            self.assertEqual(state.get("path"), str(out))
            self.assertEqual(state.get("probe_id"), "p1")
            self.assertEqual(state.get("model"), "mock-target")




if __name__ == "__main__":
    unittest.main()
