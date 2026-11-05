# ADR-0012: Analysis errors resolve to `none` so campaigns keep moving

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Comments in `modules.py`: "keep the campaign moving".

## Decision

Classifier, evidence, risk, QA and whole-record errors produce `none` (QA failure sets `qa_valid` true only if category is none). Unknown category strings normalise to `none`. Evaluation failures are counted.

## Consequences

+ Long campaigns do not abort on a parse error.
- A parse failure is indistinguishable from a clean `none` in `analysis_cells.jsonl` except via reasoning text (A-004). For a security detector this is fail-open.

## Alternatives considered

Fail closed / mark `error` category (not chosen; no evidence).

## Evidence

`tslit_dspy/modules.py` (`forward`, `_normalize_category`); `tslit_dspy/adapter.py` (`analyze`); `tslit_dspy/evaluate.py`.

Reviewed at commit `862b002`.
