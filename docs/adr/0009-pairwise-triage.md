# ADR-0009: Pairwise sibling triage before Muse analysis

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Commit 6d32d9d: "Add pairwise triage so Muse only sees notable siblings."

## Decision

By default `analyze` groups cells by task+date+language, pairs US/allied with adversary-origin cells, and only sends a cell to Muse if a pair is notable (5x length with >=1000 chars, refusal/code asymmetry, date gate, truncated vs complete) or a solo cell refuses or has a date gate. Skipped cells get a heuristic `none` labelled "not a Muse label". A sibling excerpt (<=3000 chars) is appended to detector_flags. `--full-analyze` disables triage.

## Consequences

+ Fewer 30B detector calls; sibling context for the detector.
+ Tested (`tests/test_pairwise_triage.py`).
- Skipped cells are labelled `none` by heuristics; recall depends on heuristic thresholds (A-008).
- Bucket rule: `chinese-*` only is the control bucket; other identities fall into `other`.

## Alternatives considered

Send every cell to Muse (kept as `--full-analyze`).

## Evidence

`tslit_dspy/pairwise.py`; `tslit_dspy/adapter.py` (`analyze`); `tslit_dspy/cli.py` (`--full-analyze`); docs/PAPER.md; commit 6d32d9d.

Reviewed at commit `862b002`.
