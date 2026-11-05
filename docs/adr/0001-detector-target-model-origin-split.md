# ADR-0001: Separate detector stack from scan target by model origin

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

The project tests open-weight models (Qwen, DeepSeek, Ornith) for affiliation bias and date-triggered sabotage. If the model under test also ran the analysis, a contaminated model could grade itself.

## Decision

Detection roles (compile, inference, QA) must use non-adversary / US-or-Western models; adversary-origin models are scan targets only. Enforced in code by `assert_detection_model()` (substring deny list `ADVERSARY_ORIGIN_MARKERS` plus regex allow list `DETECTION_ALLOW_PATTERNS`), called from `make_lm()` with `enforce_policy=True` by default. `./tslit smoke` and `./tslit doctor` fail if Qwen is configured as detector.

## Consequences

+ Self-grading by the suspect model is blocked at LM construction time.
+ Policy is printable (`./tslit policy`) and unit-tested (`tests/test_model_policy.py`).
- Origin is inferred from tag substrings; a renamed/re-tagged adversary model would pass (see A-001).
- Allow patterns such as `o1`, `o3`, `o4` and `mistral` are broad substrings (see A-002).
- The target side has no policy check at all; any tag can be a target.

## Alternatives considered

Single-model self-evaluation (rejected implicitly; README: "Never swap"). Allow-list only by exact tag (not chosen; only `DGX_DETECTION_MODELS` lists one exact tag, but the checker uses patterns).

## Evidence

`tslit_dspy/model_policy.py`; `tslit_dspy/lm.py` (`make_lm`); `tslit_dspy/cli.py` (`cmd_smoke`, `cmd_doctor`); `tests/test_model_policy.py`; README.md; `.env.example`; commit ff1d156.

Reviewed at commit `862b002`.
