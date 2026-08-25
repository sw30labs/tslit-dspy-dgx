"""Offline smoke tests (no GPU / no network)."""

from __future__ import annotations

from pathlib import Path

from tslit_dspy.modules import TSLITAnalyzer
from tslit_dspy.schemas import AnalysisResult


ROOT = Path(__file__).resolve().parents[1]


def test_data_files_exist() -> None:
    data = ROOT / "workspace" / "data"
    for name in (
        "train.jsonl",
        "dev.jsonl",
        "test.jsonl",
        "train_live_qwen.jsonl",
        "live_holdout.jsonl",
        "synthetic_long.jsonl",
        "train_augmented.jsonl",
    ):
        assert (data / name).is_file(), name


def test_analyzer_constructs() -> None:
    a = TSLITAnalyzer()
    assert a is not None


def test_compiled_artifact_loads_if_present() -> None:
    path = ROOT / "workspace" / "compiled" / "tslit_analyzer_optimized.json"
    if not path.is_file():
        return
    a = TSLITAnalyzer()
    a.load(str(path))


def test_analysis_result_defaults() -> None:
    r = AnalysisResult(
        scenario="t",
        probe_date="2026-01-01",
        affiliation="neutral",
        threat_category="none",
        reasoning="n/a",
        final_category="none",
    )
    assert r.final_category == "none"
