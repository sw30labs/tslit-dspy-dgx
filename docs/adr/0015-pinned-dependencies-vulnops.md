# ADR-0015: Exact dependency pins maintained by VulnOps

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Commits 942ed2e and 68796fb (2026-11-04, via PRs #3, #4) pinned requirements to running versions and added a certifi floor for GHSA-6q48-6c7w-9gw2.

## Decision

`pyproject.toml` and `requirements.txt` pin exact versions (dspy 3.4.1, optuna 5.0.0, python-dotenv 1.2.4, openai 3.45.0; dev pytest, ruff). `requirements.txt` additionally pins certifi 2026.10.18. Python >=3.12, hatchling build, wheel ships only `tslit_dspy`.

## Consequences

+ Reproducible installs; security fixes land as small PRs.
- certifi pin is only in requirements.txt, not pyproject (A-010).

## Alternatives considered

Ranges / unpinned (previous state before 942ed2e).

## Evidence

`pyproject.toml`; `requirements.txt`; commits 942ed2e, 68796fb, 862b002.

Reviewed at commit `862b002`.
