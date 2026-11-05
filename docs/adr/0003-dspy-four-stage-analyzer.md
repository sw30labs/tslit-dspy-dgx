# ADR-0003: Four-stage DSPy ChainOfThought analyzer with hard grounding checks

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

The predecessor used an iterative LangGraph analyst/QA loop (docstring in `modules.py`: "Replaces the LangGraph iterative loop"). The project needs auditable, compilable detection prompts.

## Decision

`TSLITAnalyzer` composes four `dspy.ChainOfThought` stages: ThreatClassification -> EvidenceExtraction (skipped for `none`) -> RiskAssessment -> QAValidation. After the LM stages, code enforces that evidence spans are verbatim substrings of the response; any non-`none` label without grounded evidence is downgraded to `none`. Signatures encode the labelling rubric (clock API, virtual-clock TODAY, truncation are not bombs; combined needs both axes).

## Consequences

+ Single pass, deterministic structure, MIPROv2-optimisable.
+ Hallucinated evidence cannot produce a threat label.
- Every stage failure defaults to `none` (fail-open; see ADR-0012, A-004).
- Four LM calls per cell.

## Alternatives considered

LangGraph iterative loop (replaced, per docstring). Single-stage classifier (not chosen; no evidence of evaluation).

## Evidence

`tslit_dspy/modules.py`; `tslit_dspy/signatures.py`; `tslit_dspy/schemas.py`; `tests/test_smoke_imports.py`.

Reviewed at commit `862b002`.
