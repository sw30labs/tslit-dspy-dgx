# ADR-0010: Frozen cartoon exam, hash-guarded live holdout, curated compile mix

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

v1.0 reported 88.2% on planted "cartoon" examples; live Qwen results are all `none`. The project needs to keep these apart and avoid training on evaluation data.

## Decision

`test.jsonl` is a frozen cartoon exam; `live_holdout.jsonl` is the Qwen verdict set, MD5-guarded by `workspace/.live_holdout_hash`, never in MIPRO. Compile uses `train_augmented.jsonl` (cartoon anchors + gate nones + synthetic-long + sharp live) built by `scripts/build_train_augmented.py`. `run_experiment.sh` and `tests/test_train_mix.py` assert the hash and that holdout ids are not in the mix.

## Consequences

+ Clear quote rules (PAPER.md "Quote" table).
- The `test.jsonl` hash file (`workspace/.test_jsonl_hash`) is not tracked; the guard trusts a locally created hash (A-005).
- MD5 detects accidents, not deliberate tampering.

## Alternatives considered

Compile on the 55 short cartoons alone (PAPER.md: "Do not compile the 55 short cartoons alone").

## Evidence

`scripts/run_experiment.sh`; `scripts/build_train_augmented.py`; `scripts/build_live_labels.py`; `tests/test_train_mix.py`; `config/experiment_config.json`; docs/PAPER.md; commit cfa6b25.

Reviewed at commit `862b002`.
