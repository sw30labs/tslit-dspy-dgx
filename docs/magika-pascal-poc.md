# Magika × Pascal PoC (pointer)

Canonical Pascal-facing deliverable lives in the ODC repo:

`../odc-orchestration-design-canvas/docs/canvas-governance-compiler/PASCAL-POC-TSLIT-DSPY-DGX.md`

(Absolute on Nic’s Mac: `/Users/spider/REPOS/odc-orchestration-design-canvas/docs/canvas-governance-compiler/PASCAL-POC-TSLIT-DSPY-DGX.md`)

## This repo (tslit-dspy-dgx) @ `ddf0136`

- Magika gate: `tslit_dspy/governance/gate.py` → `require_durable_write_allow`
- Checkpoint: `tslit_dspy/governance/checkpoint.py`
- Inventory: `docs/magika-decision-points.md`
- Tests: `tests/test_durable_write_gate.py` (20)
- Live smoke: `scripts/smoke_durable_write_live.py`

## Canvas

Default gate canvas remains the proven disagg-v0 path.  
Magika yolo-refresh session (2026-09-23):  
`odc-canvas-sessionTSLIT-DsPy-dgx-20260923/tslit-dspy-dgx-magika-canvas.json`  
Override with `GOVERNANCE_CANVAS_PATH` when you want the Muse/Ollama CON-S32-06 wording.

## Architecture (do not reverse)

Design → Canvas → DecisionContract IR → in-agent checkpoint (`allow|human|escalate|stop`).  
Jev only in adapter. No Jev in DSPy `forward()`.

## Pascal pack extensions (ODC)

See ODC Pascal report §§10–11 + diagram `pascal-poc-odc-before-now-future.md`: phase roadmap (feasibility→PoC→harden→expand→HITL→pilot) and honest TSLIT collateral before→after (detector accuracy/probe speed unchanged; write safety + policy traceability improved; no invented metrics).

Policy stack / pyramid (Intent→Compile→Runtime→five chokes→bytes or refuse): ODC `diagrams/pascal-poc-policy-stack-pyramid.md`.

