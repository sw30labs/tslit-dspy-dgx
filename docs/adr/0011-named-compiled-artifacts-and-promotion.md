# ADR-0011: Named compiled detector JSONs with manual promotion; Muse-light active

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Compiled prompt programs replace each other; the Claude-era artifact (Jul 21) must remain for comparison.

## Decision

`optimize` writes by default to `tslit_analyzer_optimized.muse-light.json`; promotion to the active `tslit_analyzer_optimized.json` is a manual step "only if cartoon DEV holds". `claude-era.json` is a do-not-overwrite backup. MIPROv2 is wrapped to checkpoint on SIGTERM/interrupt from its log dir.

## Consequences

+ Active detector is explicit and diffable in git.
+ Long runs survive interruption (commit 7701f51).
- Promotion gate is a human convention, not code.
- CLI `optimize` defaults to `--auto light`, while `python -m tslit_dspy.optimize` defaults to `medium` (A-009).

## Alternatives considered

Overwrite active artifact on every compile (rejected per README / compiled README).

## Evidence

`workspace/compiled/README.md`; `tslit_dspy/optimize.py`; `tslit_dspy/cli.py` (`cmd_optimize`); README.md; commits ea72252, 7701f51.

Reviewed at commit `862b002`.
