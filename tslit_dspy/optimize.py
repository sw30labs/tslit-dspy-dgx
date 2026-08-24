#!/usr/bin/env python3
"""
MIPROv2 optimization script for TSLIT-DSPy.

Compiles high-quality threat detection prompts from labeled training data.
Compile and infer both go through local Ollama (non-adversary detection LM).

Usage:
    python -m tslit_dspy.optimize \\
        --train workspace/data/train.jsonl \\
        --dev workspace/data/dev.jsonl \\
        --output workspace/compiled/tslit_analyzer_optimized.json \\
        --compile-model ollama \\
        --auto light
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import os

from dotenv import load_dotenv
load_dotenv()

import dspy

from tslit_dspy.modules import TSLITAnalyzer
from tslit_dspy.metrics import tslit_metric
from tslit_dspy.schemas import AnalysisResult


def _make_lm(model: str) -> dspy.LM:
    """Create a DSPy LM for MIPROv2 compile (non-adversary models only)."""
    from tslit_dspy.lm import make_lm

    return make_lm(model, role="compile")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def load_examples(filepath: Path) -> list[dspy.Example]:
    """Load training examples from JSONL file into dspy.Example objects."""
    examples = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)

            # Build dspy.Example with input and label fields
            ex = dspy.Example(
                # Input fields (what the model sees)
                response_text=data["response_text"],
                probe_date=data["probe_date"],
                affiliation=data["affiliation"],
                scenario_type=data["scenario_type"],
                detector_flags="; ".join(data.get("detector_flags", [])) if isinstance(data.get("detector_flags"), list) else data.get("detector_flags", "none"),
                baseline_response=data.get("baseline_response", ""),
                # Ground truth labels (for metric computation)
                threat_category=data["threat_category"],
                risk_score_range=data.get("risk_score_range", [0, 100]),
            ).with_inputs(
                "response_text", "probe_date", "affiliation",
                "scenario_type", "detector_flags", "baseline_response"
            )
            examples.append(ex)

    logger.info(f"Loaded {len(examples)} examples from {filepath}")
    return examples


def wrapped_metric(example: dspy.Example, prediction, trace=None) -> float:
    """Wrap tslit_metric to handle the TSLITAnalyzer's record-based interface.

    MIPROv2 calls the metric with (example, prediction) where prediction
    is the module's output. Since TSLITAnalyzer.forward() takes a record dict
    and returns an AnalysisResult, we need to bridge the formats.
    """
    return tslit_metric(example, prediction, trace=trace)


class CheckpointMIPROv2(dspy.MIPROv2):
    """MIPROv2 subclass that saves a checkpoint whenever a new best program is found.

    Writes to <output_stem>_checkpoint.json after each improving trial so that
    a KeyboardInterrupt mid-run doesn't lose all progress.
    """

    def __init__(self, *args, checkpoint_path: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self._checkpoint_path = checkpoint_path
        self._best_holder = [{"score": -1.0, "program": None}]  # mutable shared container

    def _optimize_prompt_parameters(self, *args, **kwargs):
        """Wrap parent implementation to inject an Optuna callback for checkpoint saving."""
        import optuna
        holder = self._best_holder
        checkpoint_path = self._checkpoint_path

        # Patch optuna.Study.optimize on this call to inject our callback
        _orig_optimize = optuna.Study.optimize

        def _patched_optimize(study, func, n_trials=None, **kw):
            callbacks = kw.pop("callbacks", []) or []

            def _on_trial_end(study, trial):
                if trial.value is None:
                    return
                try:
                    if study.best_value > holder[0]["score"]:
                        holder[0]["score"] = study.best_value
                        logger.info(
                            f"New best score {study.best_value:.4f} at trial {trial.number} "
                            f"— checkpoint will be saved on interrupt"
                        )
                except Exception:
                    pass

            callbacks.append(_on_trial_end)
            return _orig_optimize(study, func, n_trials=n_trials, callbacks=callbacks, **kw)

        optuna.Study.optimize = _patched_optimize
        try:
            result = super()._optimize_prompt_parameters(*args, **kwargs)
            self._best_holder[0]["program"] = result
            return result
        finally:
            optuna.Study.optimize = _orig_optimize



def run_optimization(
    train_path: Path,
    dev_path: Path,
    output_path: Path,
    compile_model: str = "ollama",
    auto: str = "medium",
    num_threads: int = 4,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 8,
):
    """Run MIPROv2 optimization and save compiled model.

    Default compile LM is local Ollama (Meta Muse Glimmer; US / non-adversary).
    Adversary-origin models are blocked by model_policy.
    """
    logger.info(f"Compile model: {compile_model}")
    logger.info(f"Auto setting: {auto}")

    # Configure DSPy with the compilation model
    compile_lm = _make_lm(compile_model)
    dspy.configure(lm=compile_lm)

    # Load data
    train_examples = load_examples(train_path)
    dev_examples = load_examples(dev_path)

    logger.info(f"Training set: {len(train_examples)} examples")
    logger.info(f"Dev set: {len(dev_examples)} examples")

    # Class distribution
    train_dist = {}
    for ex in train_examples:
        cat = ex.threat_category
        train_dist[cat] = train_dist.get(cat, 0) + 1
    logger.info(f"Training class distribution: {train_dist}")

    # Initialize unoptimized analyzer
    analyzer = TSLITAnalyzer()

    # Run MIPROv2 optimization
    logger.info("Starting MIPROv2 optimization...")
    checkpoint_path = output_path.with_stem(output_path.stem + "_checkpoint")
    optimizer = CheckpointMIPROv2(
        metric=wrapped_metric,
        auto=auto,
        num_threads=num_threads,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
        track_stats=True,
        checkpoint_path=checkpoint_path,
    )

    try:
        compiled_analyzer = optimizer.compile(
            analyzer,
            trainset=train_examples,
        )
    except KeyboardInterrupt:
        logger.warning("Optimization interrupted — saving best program found so far...")
        best = optimizer._best_holder[0]["program"]
        if best is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            best.save(str(checkpoint_path))
            logger.info(f"Best-so-far saved to {checkpoint_path}")
            compiled_analyzer = best
        elif checkpoint_path.exists():
            logger.info(f"Loading checkpoint from {checkpoint_path}")
            compiled_analyzer = TSLITAnalyzer()
            compiled_analyzer.load(str(checkpoint_path))
        else:
            logger.error("No checkpoint available. Exiting.")
            raise

    # Save compiled model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_analyzer.save(str(output_path))
    logger.info(f"Compiled model saved to {output_path}")

    # Quick eval on dev set
    logger.info("Running quick dev evaluation...")
    scores = []
    for ex in dev_examples[:10]:
        try:
            record = {
                "response_text": ex.response_text,
                "probe_date": ex.probe_date,
                "affiliation": ex.affiliation,
                "scenario_type": ex.scenario_type,
                "detector_flags": ex.detector_flags,
                "baseline_response": ex.baseline_response,
            }
            result = compiled_analyzer(record=record)
            score = wrapped_metric(ex, result)
            scores.append(score)
        except Exception as e:
            logger.warning(f"Dev example failed: {e}")
            scores.append(0.0)

    avg_score = sum(scores) / max(1, len(scores))
    logger.info(f"Dev set avg metric score: {avg_score:.4f}")

    return compiled_analyzer


def main():
    parser = argparse.ArgumentParser(
        description="MIPROv2 optimization for TSLIT-DSPy threat analyzer"
    )
    parser.add_argument(
        "--train", type=Path, required=True,
        help="Path to training JSONL file"
    )
    parser.add_argument(
        "--dev", type=Path, required=True,
        help="Path to dev JSONL file"
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Path to save compiled model JSON"
    )
    parser.add_argument(
        "--compile-model", type=str, default="ollama",
        help="Compile LM: Ollama tag or alias (default: OLLAMA_MODEL / Muse Glimmer). "
             "Adversary-origin models (Qwen/DeepSeek/…) are blocked."
    )
    parser.add_argument(
        "--auto", type=str, default="medium",
        choices=["light", "medium", "heavy"],
        help="MIPROv2 auto setting: light/medium/heavy (default: medium)"
    )
    parser.add_argument(
        "--num-threads", type=int, default=4,
        help="Parallel candidate evaluation threads (default: 4)"
    )
    parser.add_argument(
        "--max-bootstrapped-demos", type=int, default=4,
        help="Max few-shot examples per module from bootstrapping (default: 4)"
    )
    parser.add_argument(
        "--max-labeled-demos", type=int, default=8,
        help="Max labeled demonstrations per module (default: 8)"
    )

    args = parser.parse_args()

    run_optimization(
        train_path=args.train,
        dev_path=args.dev,
        output_path=args.output,
        compile_model=args.compile_model,
        auto=args.auto,
        num_threads=args.num_threads,
        max_bootstrapped_demos=args.max_bootstrapped_demos,
        max_labeled_demos=args.max_labeled_demos,
    )


if __name__ == "__main__":
    main()
