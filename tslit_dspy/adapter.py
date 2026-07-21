"""
Drop-in replacement for tslit.analyzer.core.

Loads a compiled DSPy TSLITAnalyzer and exposes the same interface as
the original LangGraph-based analyzer. The TSLIT CLI
(`python -m tslit.analyzer`) works unchanged with a single config flag:

    analyzer:
      backend: "dspy"
      compiled_model: "workspace/compiled/tslit_analyzer_optimized.json"
      ollama_model: "llama3.1"

Usage:
    adapter = DSPyAnalyzerAdapter(
        compiled_model_path="workspace/compiled/tslit_analyzer_optimized.json",
        ollama_model="llama3.1",
    )
    results = adapter.analyze(artifacts_dir="artifacts/")
    report = adapter.generate_report(results)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

import dspy

from tslit_dspy.modules import TSLITAnalyzer
from tslit_dspy.schemas import AnalysisResult, ThreatReport

logger = logging.getLogger(__name__)


class DSPyAnalyzerAdapter:
    """Drop-in replacement for tslit.analyzer.core.

    Loads a compiled DSPy TSLITAnalyzer and exposes the same interface
    as the original LangGraph-based analyzer. Produces identical report
    formats (text + JSON) for backward compatibility.
    """

    def __init__(
        self,
        compiled_model_path: Optional[str] = None,
        ollama_model: str = "vllm",
        ollama_base_url: str = "",
        model: Optional[str] = None,
        model_base_url: Optional[str] = None,
    ):
        """Initialize the DSPy adapter.

        Args:
            compiled_model_path: Path to compiled model JSON from MIPROv2.
                If None, runs zero-shot (unoptimized).
            ollama_model: Legacy alias for local model (prefer `model=`).
            ollama_base_url: Legacy base URL alias.
            model: Detection LM id or alias (default: local vLLM / Nemotron).
            model_base_url: Optional OpenAI-compatible base URL.
        """
        from tslit_dspy.lm import make_lm

        mid = model or ollama_model or "vllm"
        base = model_base_url or ollama_base_url or None
        lm = make_lm(mid, role="inference", model_base_url=base or None)
        logger.info("DSPy configured for detection inference model=%s", mid)
        dspy.configure(lm=lm)

        # Initialize and optionally load compiled model
        self.analyzer = TSLITAnalyzer()
        if compiled_model_path and Path(compiled_model_path).exists():
            self.analyzer.load(compiled_model_path)
            logger.info(f"Loaded compiled model from {compiled_model_path}")
        else:
            logger.warning("Running in zero-shot mode (no compiled model loaded)")

        self.ollama_model = ollama_model

    def analyze(
        self,
        artifacts_dir: str,
        model_names: Optional[List[str]] = None,
    ) -> ThreatReport:
        """Analyze NDJSON artifacts — matches tslit.analyzer.core.run_analysis interface.

        Args:
            artifacts_dir: Path to directory containing NDJSON campaign artifacts.
            model_names: Model names for the report header.

        Returns:
            ThreatReport with all analysis results.
        """
        artifacts_path = Path(artifacts_dir)
        model_names = model_names or [self.ollama_model]

        # Load NDJSON records (same logic as tslit.analyzer.core.load_model_data)
        records = self._load_ndjson(artifacts_path)
        logger.info(f"Loaded {len(records)} records from {artifacts_path}")

        # Analyze each record
        results = []
        for i, record in enumerate(records):
            try:
                result = self.analyzer(record=record)
                results.append(result)

                if result.final_category != "none":
                    logger.info(
                        f"  [{i+1}/{len(records)}] {result.final_category} "
                        f"(risk: {result.risk_score}, "
                        f"evidence: {len(result.evidence_spans)} spans)"
                    )
            except Exception as e:
                logger.error(f"  [{i+1}/{len(records)}] Analysis failed: {e}")
                # Create a safe default result for failed records
                results.append(AnalysisResult(
                    scenario=record.get("scenario", "unknown"),
                    probe_date=str(record.get("virtual_time", "unknown")),
                    affiliation=TSLITAnalyzer._extract_affiliation(record),
                    threat_category="none",
                    reasoning=f"Analysis error: {str(e)}",
                    final_category="none",
                ))

        report = ThreatReport(model_names=model_names, results=results)
        logger.info(f"Analysis complete: {report.total_threats_found} confirmed threats")
        return report

    def analyze_and_save(
        self,
        artifacts_dir: str,
        output_path: str,
        model_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Analyze and save reports — matches run_analysis() return signature.

        Args:
            artifacts_dir: Path to NDJSON artifacts.
            output_path: Path to save the text report.
            model_names: Model names for the report.

        Returns:
            Dict matching the existing AnalysisState format for compatibility.
        """
        report = self.analyze(artifacts_dir, model_names)

        # Save reports
        output = Path(output_path)
        report.save(output)
        logger.info(f"Reports saved to {output} and {output.with_suffix('.json')}")

        # Return state dict matching existing format
        analyst_findings = report.to_analyst_findings()
        qa_findings = report.to_qa_review()

        return {
            "model_data": {},  # Not needed for DSPy path
            "model_names": report.model_names,
            "analyst_report": analyst_findings["summary"],
            "analyst_findings": analyst_findings,
            "analyst_confidence": analyst_findings["confidence_score"],
            "qa_review": qa_findings["review_summary"],
            "qa_validated_findings": qa_findings,
            "qa_confidence": qa_findings["overall_confidence"],
            "qa_issues": qa_findings["critical_issues"],
            "iteration": 1,  # DSPy: single pass
            "max_iterations": 1,
            "final_report": report.generate_text_report(),
            "total_threats_found": report.total_threats_found,
            "analysis_complete": True,
        }

    def _load_ndjson(self, artifacts_dir: Path) -> List[Dict[str, Any]]:
        """Load NDJSON records from artifacts directory.

        Matches tslit.analyzer.core.load_model_data() file discovery logic.
        """
        ndjson_files = [
            f for f in artifacts_dir.glob("*.ndjson")
            if not f.name.endswith("_requests.ndjson")
        ]

        if not ndjson_files:
            logger.warning(f"No NDJSON files found in {artifacts_dir}")
            return []

        # Use most recent file
        filepath = sorted(ndjson_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
        logger.info(f"Loading from: {filepath}")

        records = []
        with open(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.error(f"Line {line_num}: parse error: {e}")

        # Try to load companion requests file for prompt context
        requests_path = artifacts_dir / f"{filepath.stem}_requests.ndjson"
        if requests_path.exists():
            self._merge_requests(records, requests_path)

        return records

    def _merge_requests(
        self, records: List[Dict[str, Any]], requests_path: Path
    ) -> None:
        """Merge request prompts into records (same as core.py logic)."""
        requests = []
        with open(requests_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    requests.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        # Filter to completed requests
        completed = [
            r for r in requests
            if (r.get("metadata") or {}).get("phase") != "pre-request"
            and r.get("response", {}).get("status") != "pending"
        ]
        if completed:
            requests = completed

        if len(requests) == len(records):
            for i, record in enumerate(records):
                req_block = requests[i].get("request", {})
                messages = req_block.get("messages", []) if isinstance(req_block, dict) else []
                for msg in messages:
                    if msg.get("role") == "user":
                        record["request_prompt"] = str(msg.get("content", ""))
                        break
            logger.info(f"Merged {len(requests)} request prompts")
        else:
            logger.warning(
                f"Request count ({len(requests)}) != response count ({len(records)})"
            )

    def generate_report(self, report: ThreatReport) -> str:
        """Generate text report from ThreatReport. Convenience method."""
        return report.generate_text_report()

    @classmethod
    def inspect_compiled(cls, compiled_path: str) -> str:
        """Show optimized prompts from a compiled model (human-readable).

        This is the `tslit dspy inspect` command — lets users audit exactly
        what prompts the compiled model uses, reinforcing the "no black box"
        value proposition.

        Args:
            compiled_path: Path to compiled model JSON.

        Returns:
            Human-readable string showing all optimized prompts.
        """
        path = Path(compiled_path)
        if not path.exists():
            return f"Error: {compiled_path} not found"

        with open(path) as f:
            data = json.load(f)

        lines = [
            "=" * 80,
            "TSLIT-DSPy COMPILED MODEL INSPECTION",
            "=" * 80,
            f"\nFile: {compiled_path}",
            "",
        ]

        # Walk the JSON structure to find optimized instructions and demos
        def _walk(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("signature_instructions", "instructions", "demos"):
                        lines.append(f"\n--- {prefix}{key} ---")
                        if isinstance(value, str):
                            lines.append(value)
                        elif isinstance(value, list):
                            for i, item in enumerate(value):
                                lines.append(f"\n  Demo {i+1}:")
                                lines.append(f"  {json.dumps(item, indent=4)[:500]}")
                        else:
                            lines.append(json.dumps(value, indent=2)[:1000])
                    else:
                        _walk(value, prefix=f"{prefix}{key}.")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _walk(item, prefix=f"{prefix}[{i}].")

        _walk(data)

        lines.extend(["", "=" * 80, "END OF INSPECTION", "=" * 80])
        return "\n".join(lines)
