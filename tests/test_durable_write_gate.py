"""Magika durable-write gate — unit coverage for the lean chokes.

We patch run_checkpoint (allow vs stop) and assert: allow lands bytes;
stop leaves zero files; GOVERNANCE_CHECKPOINT=0 bypasses. Covers
save_campaign, ThreatReport.save (+ folded sidecars), dump_request_bundle,
run_evaluation, and persist_mipro_compiled. Not a live Jev proof —
see scripts/smoke_durable_write_live.py for that.
"""

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



class EvaluationReportGateTests(unittest.TestCase):
    """evaluate.run_evaluation gated before md+json durable writes.

    Offline Mac may lack .venv/dspy — stub the DSPy import stack before loading
    evaluate, then mock the LM/metrics path so we only exercise the choke.
    """

    @classmethod
    def setUpClass(cls):
        dspy = mock.MagicMock()
        sys.modules.setdefault("dspy", dspy)
        sys.modules.setdefault("dspy.adapters", mock.MagicMock())
        sys.modules.setdefault("dspy.adapters.chat_adapter", mock.MagicMock())
        sys.modules.setdefault("dspy.signatures", mock.MagicMock())
        sys.modules.setdefault("dotenv", mock.MagicMock())
        # Drop cached evaluate if a prior import failed without stubs.
        for k in list(sys.modules):
            if k == "tslit_dspy.evaluate" or k.startswith("tslit_dspy.evaluate."):
                del sys.modules[k]
        import tslit_dspy.evaluate as evaluate_mod

        cls._evaluate = evaluate_mod

    def _run(self, output: Path):
        with mock.patch("tslit_dspy.evaluate.load_test_examples", return_value=[]), mock.patch(
            "tslit_dspy.evaluate.TSLITAnalyzer"
        ), mock.patch(
            "tslit_dspy.evaluate.per_class_metrics", return_value={}
        ), mock.patch(
            "tslit_dspy.evaluate.evidence_quality_metrics", return_value={}
        ), mock.patch(
            "tslit_dspy.evaluate.overall_accuracy", return_value=0.0
        ), mock.patch(
            "tslit_dspy.evaluate.format_evaluation_report", return_value="# report\n"
        ), mock.patch(
            "tslit_dspy.lm.make_lm", return_value=mock.MagicMock()
        ):
            return self._evaluate.run_evaluation(
                test_path=Path("fake.jsonl"),
                output_path=output,
                model="mock",
                title="TestEval",
            )

    def test_allow_writes(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "evaluation" / "report.md"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ):
                data = self._run(out)
            self.assertTrue(out.is_file())
            self.assertTrue(out.with_suffix(".json").is_file())
            self.assertEqual(data.get("mode"), "Zero-Shot Baseline")

    def test_stop_blocks_write(self):
        with tempfile.TemporaryDirectory() as td:
            eval_root = Path(td) / "evaluation"
            out = eval_root / "report.md"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "stop", "detail": "safety"},
            ):
                with self.assertRaises(GovernanceBlocked):
                    self._run(out)
            leftovers = [p for p in Path(td).rglob("*") if p.is_file()]
            self.assertEqual(leftovers, [])
            self.assertFalse(eval_root.exists())

    def test_kind_shape(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.md"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ) as rc:
                self._run(out)
            state = rc.call_args.kwargs.get("state") or {}
            self.assertEqual(state.get("tool"), "save_evaluation_report")
            self.assertEqual(state.get("path"), str(out))
            self.assertEqual(state.get("model"), "mock")
            self.assertEqual(state.get("n_examples"), 0)
            self.assertEqual(state.get("scores_path"), str(out.with_suffix(".json")))



class MiproCompiledPersistGateTests(unittest.TestCase):
    """optimize.persist_mipro_compiled gated before any compiled JSON write.

    Offline Mac may lack .venv/dspy — stub import stack, then exercise the choke
    with a fake program.save (no real MIPRO run).
    """

    @classmethod
    def setUpClass(cls):
        dspy = mock.MagicMock()
        sys.modules.setdefault("dspy", dspy)
        sys.modules.setdefault("dspy.adapters", mock.MagicMock())
        sys.modules.setdefault("dspy.adapters.chat_adapter", mock.MagicMock())
        sys.modules.setdefault("dspy.signatures", mock.MagicMock())
        sys.modules.setdefault("dspy.teleprompt", mock.MagicMock())
        sys.modules.setdefault("dotenv", mock.MagicMock())
        for k in list(sys.modules):
            if k == "tslit_dspy.optimize" or k.startswith("tslit_dspy.optimize."):
                del sys.modules[k]
        import tslit_dspy.optimize as optimize_mod

        cls._optimize = optimize_mod

    def _fake_program(self):
        prog = mock.MagicMock()
        def _save(path):
            Path(path).write_text('{"ok": true}', encoding="utf-8")
        prog.save.side_effect = _save
        return prog

    def test_allow_writes_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "compiled" / "model.json"
            ckpt = Path(td) / "compiled" / "model_checkpoint.json"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ) as rc:
                self._optimize.persist_mipro_compiled(
                    self._fake_program(),
                    paths=[out, ckpt],
                    reason="interrupt",
                    compile_model="ollama",
                    num_trials=3,
                    auto=None,
                )
            self.assertEqual(rc.call_count, 1)
            self.assertTrue(out.is_file())
            self.assertTrue(ckpt.is_file())

    def test_stop_blocks_write(self):
        with tempfile.TemporaryDirectory() as td:
            compiled_root = Path(td) / "compiled"
            out = compiled_root / "model.json"
            ckpt = compiled_root / "model_checkpoint.json"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "stop", "detail": "safety"},
            ):
                with self.assertRaises(GovernanceBlocked):
                    self._optimize.persist_mipro_compiled(
                        self._fake_program(),
                        paths=[out, ckpt],
                        reason="final",
                        compile_model="ollama",
                        auto="light",
                    )
            leftovers = [p for p in Path(td).rglob("*") if p.is_file()]
            self.assertEqual(leftovers, [])
            self.assertFalse(compiled_root.exists())

    def test_kind_shape(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "model.json"
            with mock.patch(
                "tslit_dspy.governance.checkpoint.run_checkpoint",
                return_value={"action": "allow", "detail": "ok"},
            ) as rc:
                self._optimize.persist_mipro_compiled(
                    self._fake_program(),
                    paths=[out],
                    reason="final",
                    compile_model="ollama",
                    auto="medium",
                    num_trials=None,
                )
            state = rc.call_args.kwargs.get("state") or {}
            self.assertEqual(state.get("tool"), "save_mipro_compiled")
            self.assertEqual(state.get("path"), str(out))
            self.assertEqual(state.get("reason"), "final")
            self.assertEqual(state.get("model"), "ollama")
            self.assertEqual(state.get("paths"), [str(out)])

    def test_run_optimization_fold_contract(self):
        """Source contract: interrupt/final/signal route through persist_mipro_compiled."""
        src = (ROOT / "tslit_dspy" / "optimize.py").read_text(encoding="utf-8")
        self.assertIn("def persist_mipro_compiled(", src)
        self.assertIn('kind="save_mipro_compiled"', src)
        self.assertIn("also_checkpoint", src)
        # No ungated program.save outside the helper body.
        # Heuristic: every .save( after require_durable should be inside the helper loop.
        self.assertIn("persist_mipro_compiled(", src)
        self.assertNotIn("checkpoint_path.parent.mkdir(parents=True, exist_ok=True)\n            best.save", src)
        self.assertNotIn("prog.save(str(checkpoint_path))", src)
        self.assertNotIn(
            "output_path.parent.mkdir(parents=True, exist_ok=True)\n    compiled_analyzer.save",
            src,
        )




if __name__ == "__main__":
    unittest.main()
