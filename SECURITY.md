# Security policy

## Supported versions

| Version | Support |
|---------|---------|
| 0.2.x   | Current research release — fixes welcome via issues/PRs |
| 0.1.x   | Predecessor project: [sw30labs/tslit](https://github.com/sw30labs/tslit) |

This is a research codebase, not a hosted service. “Support” means community-maintained patches and maintainer review of clear, high-impact issues.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for:

- Credential leakage or secret-handling bugs in tooling
- Ways a local experiment runner can escape its intended filesystem
- Supply-chain issues in packaging or dependency pins that enable remote code execution

Instead, email the maintainer at the address listed in the whitepaper author block / GitHub profile, with:

1. Description and impact
2. Minimal reproduction steps
3. Affected commit or tag if known

We will acknowledge when we can and prefer coordinated disclosure for anything that could be misused against third-party systems.

## Research ethics and dual-use

TSLIT-DSPy is intended for **defensive integrity testing**:

- **In scope:** improving detection of affiliation-conditioned and time-conditioned behavioral shifts; hardening evaluation metrics. Live probes are one-shot completions with thinking off (see `docs/SCOPE.md`). The Karpathy overnight agent is withdrawn (see `docs/PAPER.md`).
- **Out of scope for contributions:** instructions, payloads, or datasets whose primary purpose is to **implant** backdoors, evade unrelated safety systems for harm, or target specific real organizations with operational attack plans.

Synthetic examples that *simulate* malicious model behavior for training detectors are expected and welcome when clearly labeled `source: synthetic` (or equivalent) and free of real secrets.

## Operational safety for users

- Keep API keys in `.env` (never commit them). `.env` is gitignored; use `.env.example` as a template.
- Compiled prompt JSON may embed few-shot content from your training set; review before sharing artifacts from private runs.

## Model and data integrity

- Prefer independent, non-adversary-origin models for **compilation and R&D scoring** if your threat model includes contaminated analysis stacks.
- Never rewrite `workspace/data/test.jsonl` when claiming held-out gains; the experiment runner’s hash guard exists for this reason. The Karpathy agent that used to sit on that guard is gone.
