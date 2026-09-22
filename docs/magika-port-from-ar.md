# Magika port: tslit-dspy-ar → tslit-dspy-dgx

Date: 2026-09-22 (ET). Branch: `nic/governance-checkpoint-v0`. Local only — do not push unless asked.

## What carried over (apply)

| Piece | Status |
|-------|--------|
| `tslit_dspy.governance.run_checkpoint` | **ported** — same Canvas → IR → allow\|human\|escalate\|stop spine |
| Docs pointer to ODC wiki | **ported** |
| `docs/governance-checkpoint.md` | **ported** (engine-agnostic) |
| Disaggregated Canvas + ODC compiler | **reuse as-is** from `odc-orchestration-design-canvas` (not duplicated here) |
| Offline fixture matrix / METHODOLOGY | **lives in ODC**, not in this repo |

## What does **not** apply

| Piece (on ar) | Why |
|---------------|-----|
| `scripts/agent_loop_mlx.py` + `execute_tool` gate | **Missing on dgx.** No agent tool loop. Side effects are campaign/adapter writes under `workspace/`. |
| `scripts/smoke_governance_gate.py` / `tests/test_governance_gate.py` | Tied to that agent loop. Re-home after a dgx choke point exists. |
| MLX / Mac-local model loop assumptions | dgx is **Ollama-only** on Spark (`127.0.0.1:11434`). |

## Candidate choke points on dgx (next lean wire)

Do **not** sprinkle Jev into DSPy `forward()`. Prefer one boundary before durable writes:

1. **`tslit_dspy/adapter.py`** — writes triage / cells / reports under artifacts.
2. **`tslit_dspy/probe_campaign.py`** — ndjson / meta / canary dumps under `workspace/scans/`.
3. **`tslit_dspy/cli.py`** — CLI entry; optional env gate around mutate commands only.

Same env flags as ar when wired: `GOVERNANCE_CHECKPOINT=0` off, `GOVERNANCE_LIVE=1` live Jev.

## Sync

- Edit Magika on Mac `/Users/spider/REPOS/tslit-dspy-dgx`.
- Pull on sparkone `/home/spider/Desktop/tslit-dspy-dgx` for Ollama smokes.
- Git only — no rsync of the trees.
