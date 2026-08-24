#!/usr/bin/env python3
"""
Evaluation runner for TSLIT-DSPy.

Runs the analyzer (zero-shot or compiled) against a test set and produces:
- Per-class accuracy table (precision, recall, F1)
- Baseline vs optimized comparison
- Evidence quality analysis
- Qualitative best/worst examples per category

Usage:
    # Zero-shot baseline evaluation
    python -m tslit_dspy.evaluate \\
        --test workspace/data/test.jsonl \\
        --output workspace/evaluation/baseline_eval.md \\
        --model ollama

    # Optimized evaluation
    python -m tslit_dspy.evaluate \\
        --test workspace/data/test.jsonl \\
        --compiled workspace/compiled/tslit_analyzer_optimized.json \\
        --output workspace/evaluation/optimized_eval.md \\
        --model ollama
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import os

from dotenv import load_dotenv
load_dotenv()

import dspy

from tslit_dspy.modules import TSLITAnalyzer
from tslit_dspy.metrics import (
    tslit_metric,
    per_class_metrics,
    evidence_quality_metrics,
    overall_accuracy,
    format_evaluation_report,
)
from tslit_dspy.schemas import AnalysisResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def load_test_examples(filepath: Path) -> List[dspy.Example]:
    """Load test examples from JSONL."""
    examples = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            ex = dspy.Example(
                response_text=data["response_text"],
                probe_date=data["probe_date"],
                affiliation=data["affiliation"],
                scenario_type=data["scenario_type"],
                detector_flags="; ".join(data.get("detector_flags", [])) if isinstance(data.get("detector_flags"), list) else data.get("detector_flags", "none"),
                baseline_response=data.get("baseline_response", ""),
                threat_category=data["threat_category"],
                risk_score_range=data.get("risk_score_range", [0, 100]),
                example_id=data.get("example_id", "unknown"),
            ).with_inputs(
                "response_text", "probe_date", "affiliation",
                "scenario_type", "detector_flags", "baseline_response"
            )
            examples.append(ex)
    return examples


def run_evaluation(
    test_path: Path,
    output_path: Path,
    model: str = "ollama",
    model_base_url: str = "",
    compiled_path: Optional[Path] = None,
    title: str = "Evaluation",
) -> Dict[str, Any]:
    """Run evaluation and save report.

    Args:
        test_path: Path to test JSONL
        output_path: Path to save markdown report
        model: Detection LM (default: local Ollama / Muse Glimmer)
        model_base_url: Optional Ollama base URL override
        compiled_path: Path to compiled model JSON (None = zero-shot)
        title: Report title

    Returns:
        Dict with all metric results
    """
    # Configure LM — non-adversary / American models only for the detector
    from tslit_dspy.lm import make_lm

    lm = make_lm(
        model,
        role="inference",
        model_base_url=model_base_url if model_base_url else None,
    )
    dspy.configure(lm=lm)

    # Load test data
    test_examples = load_test_examples(test_path)
    logger.info(f"Loaded {len(test_examples)} test examples")

    # Initialize analyzer
    analyzer = TSLITAnalyzer()
    if compiled_path and compiled_path.exists():
        analyzer.load(str(compiled_path))
        logger.info(f"Loaded compiled model from {compiled_path}")
        is_optimized = True
    else:
        logger.info("Running zero-shot (unoptimized) evaluation")
        is_optimized = False

    # Run predictions
    predictions = []
    failures = 0
    per_example_scores = []

    for i, example in enumerate(test_examples):
        try:
            record = {
                "response_text": example.response_text,
                "probe_date": example.probe_date,
                "affiliation": example.affiliation,
                "scenario_type": example.scenario_type,
                "detector_flags": example.detector_flags,
                "baseline_response": example.baseline_response,
                "scenario": example.get("scenario", example.scenario_type),
            }
            result = analyzer(record=record)
            predictions.append(result)

            score = tslit_metric(example, result)
            per_example_scores.append({
                "example_id": example.get("example_id", f"ex-{i}"),
                "gt_category": example.threat_category,
                "pred_category": result.final_category,
                "score": score,
                "risk_score": result.risk_score,
                "evidence_count": len(result.evidence_spans),
                "qa_valid": result.qa_valid,
                "reasoning": result.reasoning[:200],
            })

            logger.info(f"  [{i+1}/{len(test_examples)}] {example.get('example_id', '?')}: "
                       f"gt={example.threat_category}, pred={result.final_category}, score={score:.3f}")

        except Exception as e:
            logger.error(f"  [{i+1}/{len(test_examples)}] Failed: {e}")
            failures += 1
            # Create a default "none" prediction for failed examples
            predictions.append(AnalysisResult(
                scenario="error",
                probe_date=example.probe_date,
                affiliation=example.affiliation,
                threat_category="none",
                reasoning=f"Evaluation error: {str(e)}",
                final_category="none",
            ))
            per_example_scores.append({
                "example_id": example.get("example_id", f"ex-{i}"),
                "gt_category": example.threat_category,
                "pred_category": "none",
                "score": 0.0,
                "error": str(e),
            })

    # Compute metrics
    class_metrics = per_class_metrics(test_examples, predictions)
    ev_metrics = evidence_quality_metrics(test_examples, predictions)
    acc = overall_accuracy(test_examples, predictions)

    # Build report
    mode = "MIPROv2 Optimized" if is_optimized else "Zero-Shot Baseline"
    report_title = f"{title} — {mode}"
    report = format_evaluation_report(class_metrics, ev_metrics, acc, report_title)

    # Add metadata
    report += f"\n\n## Metadata\n\n"
    report += f"- Date: {datetime.now().isoformat()}\n"
    report += f"- Model: {model}\n"
    report += f"- Test set: {test_path}\n"
    report += f"- Examples: {len(test_examples)}\n"
    report += f"- Failures: {failures}\n"
    if compiled_path:
        report += f"- Compiled model: {compiled_path}\n"

    # Add QA pass rate
    qa_passes = sum(1 for p in predictions if isinstance(p, AnalysisResult) and p.qa_valid)
    report += f"\n## QA Validation\n\n"
    report += f"- QA pass rate: {qa_passes / max(1, len(predictions)):.1%}\n"

    # Add qualitative examples (best/worst per category)
    report += "\n## Qualitative Analysis\n\n"
    for cat in ["none", "affiliation_bias", "temporal_logic_bomb", "combined"]:
        cat_scores = [s for s in per_example_scores if s["gt_category"] == cat]
        if not cat_scores:
            continue

        cat_scores.sort(key=lambda x: x["score"], reverse=True)

        report += f"\n### {cat}\n\n"
        report += f"**Best predictions (top 3):**\n\n"
        for s in cat_scores[:3]:
            report += f"- `{s.get('example_id', '?')}`: score={s['score']:.3f}, "
            report += f"pred={s['pred_category']}, risk={s.get('risk_score', '?')}\n"
            if s.get('reasoning'):
                report += f"  Reasoning: {s['reasoning'][:100]}...\n"

        report += f"\n**Worst predictions (bottom 3):**\n\n"
        for s in cat_scores[-3:]:
            report += f"- `{s.get('example_id', '?')}`: score={s['score']:.3f}, "
            report += f"pred={s['pred_category']}, risk={s.get('risk_score', '?')}\n"
            if s.get('error'):
                report += f"  Error: {s['error'][:100]}\n"
            elif s.get('reasoning'):
                report += f"  Reasoning: {s['reasoning'][:100]}...\n"

    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    logger.info(f"Report saved to {output_path}")

    # Compute mean composite score (the actual metric MIPROv2 optimizes)
    composite_scores = [s.get("score", 0.0) for s in per_example_scores]
    mean_composite = sum(composite_scores) / max(1, len(composite_scores))

    # Also save raw scores as JSON
    scores_path = output_path.with_suffix(".json")
    scores_data = {
        "mode": mode,
        "model": model,
        "accuracy": acc,
        "mean_composite": mean_composite,
        "class_metrics": class_metrics,
        "evidence_metrics": ev_metrics,
        "qa_pass_rate": qa_passes / max(1, len(predictions)),
        "per_example": per_example_scores,
    }
    scores_path.write_text(json.dumps(scores_data, indent=2), encoding="utf-8")

    return scores_data


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate TSLIT-DSPy analyzer against test set"
    )
    parser.add_argument(
        "--test", type=Path, required=True,
        help="Path to test JSONL file"
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Path to save evaluation report (markdown)"
    )
    parser.add_argument(
        "--model", type=str, default="ollama",
        help="Detection LM (default: ollama → Muse Glimmer on local Ollama). "
             "Adversary-origin models blocked."
    )
    parser.add_argument(
        "--model-base-url", type=str, default="",
        help="Optional Ollama base URL override (default: OLLAMA_BASE_URL)"
    )
    parser.add_argument(
        "--compiled", type=Path, default=None,
        help="Path to compiled model JSON. Omit for zero-shot baseline."
    )
    parser.add_argument(
        "--title", type=str, default="TSLIT-DSPy Evaluation",
        help="Report title"
    )

    args = parser.parse_args()

    run_evaluation(
        test_path=args.test,
        output_path=args.output,
        model=args.model,
        model_base_url=args.model_base_url,
        compiled_path=args.compiled,
        title=args.title,
    )


if __name__ == "__main__":
    main()
