# TSLIT-DSPy: Opus 4.6 Baseline & Compilation Runbook

> **Archival.** Copied from `tslit-dspy-ar` (`b7d5453f`). This is how the v1.0 **cartoon exam** (88.2% on frozen `test.jsonl`) was produced with Anthropic Sonnet/Opus. It is **not** the DGX Spark / Ollama / Muse path. Exam JSONL in this repo matches that tree. See `docs/PAPER.md`.

**Date:** 2026-03-25
**Purpose:** Re-establish baseline and compile with the new model setup (Sonnet 4.6 compile, Opus 4.6 inference), replacing prior Qwen3.5-27B/Nemotron results.

---

## Prerequisites

- `ANTHROPIC_API_KEY` set in `.env` or environment
- Python 3.10+ with `dspy>=2.5` and `python-dotenv` installed
- Run all commands from the project root (`TSLIT-DSPY-AR/`)

Verified: all imports, data loading, and DSPy 3.1.3 compatibility check out.

---

## Step 1 — Zero-Shot Baseline on Dev (14 examples)

```bash
python -m tslit_dspy.evaluate \
    --test workspace/data/dev.jsonl \
    --output workspace/evaluation/opus_baseline_dev.md \
    --model anthropic/claude-opus-4-6 \
    --title "Opus 4.6 Zero-Shot Baseline (Dev Set)"
```

- No `--compiled` flag = zero-shot (unoptimized pipeline)
- 14 examples × 4 API calls each (classify → extract → score → validate) = ~56 Opus calls
- Expected duration: 5–10 minutes
- Expected cost: ~$2–4
- Output: `workspace/evaluation/opus_baseline_dev.md` + `.json`

**Key values to record from the JSON:**
- `accuracy` — category match rate (primary)
- `mean_composite` — weighted composite score (secondary)
- `class_metrics.{category}.f1` — per-class F1
- `evidence_metrics.grounding_rate`
- `qa_pass_rate`

---

## Step 2 — Update `tslit_program.md` with New Baseline

Update the Baseline Reference table in `config/tslit_program.md`:

```
| Metric | Baseline (zero-shot) | Trial 2 (MIPROv2 light) |
|--------|---------------------|------------------------|
| accuracy | <NEW_BASELINE> | <pending compilation> |
| model | Opus 4.6 | Sonnet 4.6 compile / Opus 4.6 infer |
```

Also update the "Current best score" line and the target thresholds if the new baseline is significantly different from the old 68.25%.

**Do this BEFORE compilation** — the autoresearch agent uses these reference scores for hypothesis generation.

---

## Step 3 — MIPROv2 Compilation with Sonnet 4.6 (heavy)

```bash
python -m tslit_dspy.optimize \
    --train workspace/data/train.jsonl \
    --dev workspace/data/dev.jsonl \
    --output workspace/compiled/tslit_analyzer_optimized.json \
    --compile-model anthropic/claude-sonnet-4-6 \
    --auto heavy \
    --num-threads 4 \
    --max-bootstrapped-demos 4 \
    --max-labeled-demos 4
```

- `heavy` = ~200 MIPROv2 Bayesian optimization trials
- Expected duration: 1–3 hours
- Significant API cost (hundreds of Sonnet calls)
- `CheckpointMIPROv2` saves progress — Ctrl-C won't lose work (saves to `tslit_analyzer_optimized_checkpoint.json`)
- Output: `workspace/compiled/tslit_analyzer_optimized.json`

**Config reference** (`experiment_config.json`):
- compile_model: `anthropic/claude-sonnet-4-6`
- inference_model: `anthropic/claude-opus-4-6`
- auto_setting: `heavy`
- num_threads: 4, max_bootstrapped_demos: 4, max_labeled_demos: 4

---

## Step 4 — Evaluate Compiled Model on Dev

```bash
python -m tslit_dspy.evaluate \
    --test workspace/data/dev.jsonl \
    --compiled workspace/compiled/tslit_analyzer_optimized.json \
    --output workspace/evaluation/opus_optimized_dev.md \
    --model anthropic/claude-opus-4-6 \
    --title "Opus 4.6 MIPROv2-Optimized (Dev Set)"
```

- Compare against Step 1 baseline
- Update `tslit_program.md` again with the optimized score
- If gain is < 5 points over baseline, consider adjusting compilation levers (Tier 1 in the hypothesis ladder)

---

## Step 5 — Final Test Set Evaluation (only when satisfied with dev)

```bash
python -m tslit_dspy.evaluate \
    --test workspace/data/test.jsonl \
    --compiled workspace/compiled/tslit_analyzer_optimized.json \
    --output workspace/evaluation/opus_optimized_test.md \
    --model anthropic/claude-opus-4-6 \
    --title "Opus 4.6 MIPROv2-Optimized (Test Set)"
```

- 17 held-out examples, MD5-guarded by `run_experiment.sh`
- **Only run once** — this is your final reported number
- Update the whitepaper evaluation section with these results

---

## Dev Set Distribution (for reference)

| Category | Dev Count | Train Count |
|----------|-----------|-------------|
| none | 5 | 25 |
| affiliation_bias | 3 | 10 |
| temporal_logic_bomb | 3 | 10 |
| combined | 3 | 10 |

---

## Notes

- **Old baseline:** 68.25% accuracy, 73.42% best (MIPROv2 light, Nemotron 120B compile, Qwen3.5-27B inference)
- **Old best composite:** 87.04% on dev after 33/66 trials
- Opus 4.6 is substantially stronger than Qwen3.5-27B — expect the zero-shot baseline to shift (likely upward)
- `max_labeled_demos` is set to 4 in config but `tslit_program.md` mentions default of 8 — config is authoritative
- If compilation is interrupted, resume from checkpoint: the compiled model at `_checkpoint.json` contains the best program found so far
