# ADR-0005: Composite MIPROv2 metric 0.50/0.20/0.20/0.10

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

MIPROv2 needs a scalar metric over labelled examples.

## Decision

`tslit_metric` = 0.50 exact category + 0.20 risk-in-range (partial credit within 50 points; 0-1 labels scaled to 0-100) + 0.20 evidence grounding rate (or 0.20 only for a correct `none` when ground truth is `none`) + 0.10 QA pass. Weights are hard-coded; `config/experiment_config.json` only documents them.

## Consequences

+ Rewards grounded evidence, not just labels.
+ A false bomb on a `none` example no longer gets free grounding credit (comment in code).
- Weights are not configurable or justified in the repo (A-007).

## Alternatives considered

Plain accuracy (still reported separately as `overall_accuracy`).

## Evidence

`tslit_dspy/metrics.py`; `config/experiment_config.json` (`_metric_weights_note`); `tests/test_heuristics_and_metric.py`.

Reviewed at commit `862b002`.
