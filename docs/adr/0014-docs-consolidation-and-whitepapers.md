# ADR-0014: Docs consolidated into README, PAPER, SECURITY; versioned whitepapers in-tree

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Commit b9b4e8c ("Consolidate docs to README, PAPER, and SECURITY") deleted QUICKSTART.md, docs/DGX_SPARK.md, docs/PHASES.md, docs/PLAN_REALISTIC_VERDICT.md, docs/SCOPE.md. Commit 1e3c6b9 copied v1.0 whitepaper from `sw30labs/tslit-dspy-ar` at b7d5453f.

## Decision

Three living docs (README, docs/PAPER.md, SECURITY.md); `whitepaper/v1.0` archival, `whitepaper/v2.0` living manuscript; PAPER.md status table is the source of truth over the diagram.

## Consequences

+ Fewer docs to drift.
- Built PDFs and figures (several MB) are tracked.
- `docs/LINKEDIN_POST.md` is gitignored as a local draft.

## Alternatives considered

Keep per-topic docs (removed).

## Evidence

README.md; docs/PAPER.md; `whitepaper/*/README.md`; commits b9b4e8c, 1e3c6b9, b9a2a5c.

Reviewed at commit `862b002`.
