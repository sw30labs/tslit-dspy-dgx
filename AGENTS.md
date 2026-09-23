# AGENTS.md — tslit-dspy-dgx (Magika runtime)

Instructions for coding agents working in this repo. Sibling design/compile repo:
[`odc-orchestration-design-canvas` AGENTS.md](../odc-orchestration-design-canvas/AGENTS.md).

## Goal / vision (Pascal)

Turn **Design → Compile → Runtime** into concrete TSLIT-DsPy actions.

- **Magika analogy:** Canvas locks the quiz; Jev votes with confidence; **code** is the scorecard.
- Checkpoint lives **inside the agent** at durable writes.
- IR is **engine-agnostic** (lives in ODC `governance-compiler`). Jev is an **adapter only**.
- Do **not** put Jev in DSPy `forward()`. Lean Diogo-aligned spine only.

## What we achieved (2026-09-22..23)

- Branch `nic/governance-checkpoint-v0` tip **`ddf0136`** (docs may sit ahead; runtime proof tip stays `ddf0136`).
- Five durable-write choke families via `require_durable_write_allow` / `GovernanceBlocked`:
  1. `save_campaign`
  2. `save_threat_report` (ThreatReport + folded analyze sidecars — one Jev vote)
  3. `dump_request_bundle`
  4. `save_evaluation_report`
  5. `save_mipro_compiled`
  - Standalone `save_analyze_sidecars` only when ThreatReport.save is not on the stack.
- Live allow/stop proof on spark/Mac; **20/20** gate unit tests; doctor OK; mock compiler smoke OK.
- ODC Canvas session `odc-canvas-sessionTSLIT-DsPy-dgx-20260923/` (S1–S6, maturity 4.69/A). **Do not overwrite** disagg-v0.
- Policy: reuse 12-rule IR; only CON-S32-06 wording refresh; **no new chokes** in this PoC.
- Docs: ODC `PASCAL-POC-TSLIT-DSPY-DGX.md` (roadmap §10, collateral §11), diagrams, `PASCAL-ONEPAGER-MAGIKA.md`; local pointers in `docs/magika-pascal-poc.md`, `docs/governance-checkpoint.md`.
- Commits **local ahead of origin** — **do not push unless Nic asks**.

## Where we are now

- PoC **DONE**. Feasibility ✓.
- Detector accuracy/speed **unchanged**.
- Write governance **improved** (zero-byte stop).
- HITL **not built** (`human` / `escalate` → fail-closed `GovernanceBlocked`).
- Probe HTTP / CLI `experiment` still **ungated**.
- Default `GOVERNANCE_CANVAS_PATH` still points at **disagg-v0** (proven). Point at the Magika session when you want CON-S32-06 Muse wording.

## Where we want to go (roadmap)

1. **Harden** — Switch `TRG-S51-01` mid-band narrative; optional decision-log.
2. **Expand chokes** — probe HTTP, CLI `experiment` only when justified.
3. **HITL UI** for real `human`.
4. **Pilot / workshop** with Pascal (`scripts/smoke_durable_write_live.py`).

Still non-goals: Jev in DSPy `forward()`; inventing metrics; new Safety fences without an atomic gap.

## Working rules for agents

- Commit as **Nicolas Cravino \<ncravino@mac.com\>**, first person **Nic**.
- Sync Mac ↔ spark via **git**, not rsync. Keep runtime tip **`ddf0136`** for Magika proofs unless Nic moves the tip.
- Paths:
  - Mac: `/Users/spider/REPOS/tslit-dspy-dgx`
  - sparkone: `/home/spider/Desktop/tslit-dspy-dgx`
  - ODC (Mac): `/Users/spider/REPOS/odc-orchestration-design-canvas`
- Env:
  | Var | Meaning |
  |-----|---------|
  | `GOVERNANCE_CHECKPOINT` | Default on; `=0` disables (debug only) |
  | `GOVERNANCE_LIVE` | `=1` live Jev via AI Gateway |
  | `GOVERNANCE_CANVAS_PATH` | Override Canvas JSON (default: disagg-v0) |
  | `GOVERNANCE_COMPILER_PATH` | ODC `governance-compiler` root on PYTHONPATH |
  | `AI_GATEWAY_API_KEY` | Live Jev |
- Never invent API/metrics. Never email/WhatsApp Pascal unless Nic asks.
- Prefer **parallel quiz questions** (one evaluate for an atomic quiz).
- Gate **before** mkdir/writes; stop must leave **zero bytes**.
- **Do not push** unless Nic asks.

## Pointers (this repo)

| What | Path |
|------|------|
| Gate module | `tslit_dspy/governance/gate.py` |
| Checkpoint | `tslit_dspy/governance/checkpoint.py` |
| Gate unit tests (20) | `tests/test_durable_write_gate.py` |
| Mock smoke | `scripts/smoke_durable_write_gate.py` |
| Compiler smoke | `scripts/smoke_durable_write_compiler.py` |
| Live allow/stop smoke | `scripts/smoke_durable_write_live.py` |
| Runtime choke docs | `docs/governance-checkpoint.md` |
| Decision points inventory | `docs/magika-decision-points.md` |
| Pascal PoC pointer | `docs/magika-pascal-poc.md` |

ODC Pascal pack, diagrams, sessions, compiler: see sibling
[`odc-orchestration-design-canvas` AGENTS.md](../odc-orchestration-design-canvas/AGENTS.md).
