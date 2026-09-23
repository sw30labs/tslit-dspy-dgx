# Governance checkpoint (v0 stub)

In-agent Canvas → IR → `allow|human|escalate|stop` for TSLIT-DsPy.

## Status

Branch: `nic/governance-checkpoint-v0`

This repository’s default README still marks the tree as **archived / superseded by
`sw30labs/tslit-dspy-dgx`**. The checkpoint stub lives here because that is the
local checkout we have today. If Nic moves active TSLIT work fully to the DGX
repo, **port this package there** and keep IR compilation in
`odc-orchestration-design-canvas/governance-compiler`.

## Magika model (do not reverse)

| Stage | Owner | Output |
|-------|--------|--------|
| Design | Coach / odc-canvas skill | Canvas JSON (Safety S3 + Switch S5 first) |
| Compile | `governance-compiler` | Engine-agnostic DecisionContract IR |
| Runtime | `tslit_dspy.governance.checkpoint` | `allow` \| `human` \| `escalate` \| `stop` |

Jev votes with confidence on each MCQ. **Code** owns thresholds and precedence
(`stop > escalate > human > allow`). Jev types stay in the adapter, not the IR.

## Diogo / TypeSafe note

Prefer **atomic** Canvas questions (features), aggregate in code. The current
TSLIT session canvas still packs many hard fences into one `S32` mega-question.
Refresh + disaggregate before treating live Jev as production-grade for subtle
violations.

## Wire-up (next)

1. Add `governance-compiler` on `PYTHONPATH` (or package dep) from the ODC repo.
2. Compile refreshed TSLIT Canvas → contract JSON checked into `config/` or loaded from ODC fixtures.
3. Call `run_checkpoint(...)` inside the detection / deploy path **before** side effects
   (write `test.jsonl`, auto-deploy, cloud transmit, etc.).
4. Optional: `--live` / `live=True` with `AI_GATEWAY_API_KEY` (Vercel AI Gateway, `typesafe-ai/jev`).

## Related

- ODC session: `odc-orchestration-design-canvas/odc-canvas-sessionTSLIT-DsPy/`
- Compiler: `odc-orchestration-design-canvas/governance-compiler/`
- ODC branch: `nic/canvas-governance-compiler-v0`

## S32 disaggregation

See [s32-disaggregation-v0.md](s32-disaggregation-v0.md) — Diogo-style atomic Safety/Switch questions (proposal only; live Canvas untouched).

## Methodology

Canonical living playbook: `odc-orchestration-design-canvas/docs/canvas-governance-compiler/METHODOLOGY.md` (Diogo + Magika). This branch keeps TSLIT-specific disaggregation in [s32-disaggregation-v0.md](s32-disaggregation-v0.md).

<!-- magika-dgx-durable-write-choke -->
# Governance checkpoint — dgx runtime choke

Pointer: full candidate list lives in [magika-decision-points.md](magika-decision-points.md).

## Runtime API

- `tslit_dspy.governance.run_checkpoint(canvas_path=..., state=..., live=...)`
- `tslit_dspy.governance.require_durable_write_allow(kind=..., path=..., narrative=..., extra=...)`
- Raises `GovernanceBlocked` unless action is `allow` (or gate disabled)

## Where it runs

Lean v0 chokes (same helper, no DSPy `forward()`):

1. `save_campaign` — probe NDJSON/meta/canary
2. `ThreatReport.save` — report md+json **plus** stashed analyze sidecars
   (`triage.json`, `analysis_cells.jsonl`, `analysis_summary.json`) for
   `analyze_and_save` / `analyze_artifacts` (one Jev vote; no double-call)
3. Standalone `analyze(write_sidecars=True)` — `kind=save_analyze_sidecars` only when save is not on the stack

## Env

| Var | Meaning |
|-----|---------|
| `GOVERNANCE_CHECKPOINT=0` | Disable |
| `GOVERNANCE_LIVE=1` | Live Jev |
| `GOVERNANCE_CANVAS_PATH` | Canvas JSON |
| `GOVERNANCE_COMPILER_PATH` | ODC `governance-compiler` root |

## Gate wiring notes (2026-09-23)

`require_durable_write_allow` now:

- resolves `GOVERNANCE_CANVAS_PATH` (default: 12-rule disagg canvas on Mac REPOS)
- puts `GOVERNANCE_COMPILER_PATH` / default ODC `governance-compiler` on `sys.path`
- accepts `CheckpointDecision` **or** dict from `run_checkpoint` (ar parity)

Smokes:

- `scripts/smoke_durable_write_gate.py` — mocked `run_checkpoint`
- `scripts/smoke_durable_write_compiler.py` — real mock_evaluate + canvas
- `scripts/smoke_durable_write_live.py` — live Jev (`GOVERNANCE_LIVE=1`)

## Live status (2026-09-23)

Live stop green at durable-write choke. Live allow often fail-closes on Switch `TRG-S51-01` mid-band confidence. See `docs/magika-decision-points.md`.
