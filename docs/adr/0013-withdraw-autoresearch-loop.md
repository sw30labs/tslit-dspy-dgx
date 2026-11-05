# ADR-0013: Withdraw the Karpathy overnight autoresearch loop

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Commit 5deb5bf deleted `scripts/agent_loop_mlx.py` (809 lines) and `config/tslit_program.md`. PAPER.md gives the reasons: wrong score (cartoons), 8-12 h per trial, appended train.jsonl never reached the mix, live gold is all `none`.

## Decision

No autonomous optimisation loop. MIPROv2 runs only via `./tslit optimize` when a human asks. `.gitignore` keeps leftover loop files ignored.

## Consequences

+ Removes an agent that sat next to the test-set hash guard (SECURITY.md).
- No automated improvement path.

## Alternatives considered

Keep the loop (rejected for the reasons above).

## Evidence

docs/PAPER.md (Karpathy loop); SECURITY.md; `.gitignore`; `whitepaper/v2.0/README.md`; commit 5deb5bf.

Reviewed at commit `862b002`.
