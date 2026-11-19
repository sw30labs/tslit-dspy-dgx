# Magika decision-point inventory — tslit-dspy-dgx

Branch target: `nic/governance-checkpoint-v0`  
Inventory basis: GitHub `main` (public) + ar Magika gate pattern. Mac tip may already carry `tslit_dspy/governance/` ahead of `main` — re-verify on checkout.

Canon: Design→Canvas; Compile→DecisionContract IR; Runtime→in-agent `allow|human|escalate|stop`.  
Lean Magika-thin v0: **one choke before durable writes**. Do **not** sprinkle Jev into DSPy `forward()`.

## Summary table (v0 gating)

| # | Candidate | file:function | Side-effect class | Gate v0 | Why |
|---|-----------|---------------|-------------------|---------|-----|
| 1 | Persist probe campaign artifacts | `probe_campaign.py:save_campaign` | Durable FS write (workspace/scans NDJSON/meta/canary) | **yes** | Single choke covering the main production write path (`tslit scan` / CLI) |
| 2 | Per-probe request dump | `probe_campaign.py:dump_request_bundle` | Durable FS write (audit dumps) | **yes** | Lean third choke: gate before each audit JSON write (`kind=dump_request_bundle`); dump_dir mkdir deferred until allow |
| 3 | Adapter triage + cells write | `adapter.py:DSPyAnalyzerAdapter.analyze` | Durable FS write (`triage.json`, `analysis_cells.jsonl`) | **yes** (folded) | Stashed on report; flushed after `ThreatReport.save` allow when `write_sidecars=False`. Standalone analyze gates with `kind=save_analyze_sidecars` |
| 4 | Adapter report save | `schemas.ThreatReport.save` (via `analyze_and_save` / `analyze_artifacts`) | Durable FS write (md+json report) | **yes** | Shared second choke: one gate in `ThreatReport.save`; both adapter + probe analyze paths reuse `require_durable_write_allow` |
| 5 | Analyze artifacts summary | `probe_campaign.py:analyze_artifacts` | Durable FS write (`analysis_summary.json` + report) | **yes** (folded) | Summary stashed then flushed inside gated `ThreatReport.save` — stop leaves no summary/partials |
| 6 | Evaluation report | `evaluate.py:run_evaluation` | Durable FS write (md + scores json under workspace/evaluation) | **yes** | Lean choke before md+json (`kind=save_evaluation_report`); one vote covers both; mkdir deferred until allow |
| 7 | MIPRO compiled model persist | `optimize.py:persist_mipro_compiled` (signal / interrupt / final / logs) | Durable FS write (compiled program json + optional checkpoint) | **yes** | Lean fold: one gate per logical persist (`kind=save_mipro_compiled`); interrupt writes output+checkpoint in one vote; mkdir deferred until allow |
| 8 | CLI scan orchestration | `cli.py:cmd_scan` | Orchestrates probe+save+analyze | no (as separate gate) | Keep logic in `save_campaign`; CLI only surfaces `GovernanceBlocked` |
| 9 | CLI experiment subprocess | `cli.py:cmd_experiment` | Shell/subprocess (`run_experiment.sh`) | later | Broad side effects; allowlist/script trust today |
| 10 | Ollama health / invoke | `lm.py:health_check_ollama`, `cli.py:cmd_test_ollama`, `make_lm` | Network to local Ollama | no | Local inference boundary; not durable external state |
| 11 | Probe HTTP to target model | `probe_campaign.py` chat/completions via urllib | Network side effect (target LLM) | later | Changes remote model logs/state; Magika narrative→answers gap still open; don’t block research probes in v0 |
| 12 | Tokenize/render fetch | `probe_campaign.py:try_fetch_rendered_prompt` | Network | no | Best-effort hygiene aid |
| 13 | Host preflight `ollama` subprocess | `lm.py:host_preflight` | Subprocess (read-only-ish) | no | Doctor path |
| 14 | DSPy module forward / analyze cell | `modules.py` / analyzer `forward` | Model invocation (no durable write by itself) | **no** | Explicit non-goal — do not gate every forward |
| 15 | Env / config mutation | (none first-class in package) | Config mutation | no | Reads env; no writers found |
| 16 | Email / upload / copy-out | probe text mentions `upload_to_remote` as **scenario content** only | Exfiltration-ish (simulated in prompts) | later | Real exfil tools not present; if added, gate as stop/escalate |
| 17 | Destructive delete/rmtree | (none found in package core) | Destructive | no | Absent today |
| 18 | Workspace logs / history | agent_loop style (ar only) | Durable FS | n/a on dgx | dgx has no agent_loop; ar gated write_file/run_command/append_results |

**Inventory count:** 18 candidates catalogued; **5 chokes wired** (`save_campaign`, `ThreatReport.save`, `dump_request_bundle`, `run_evaluation`, `persist_mipro_compiled`); analyze sidecars/summary **folded** into the report save choke (no double-Jev on that path).

## Wired chokes (v0)

1. **`tslit_dspy.probe_campaign.save_campaign`** — checkpoint **before** any NDJSON/meta/canary write (`kind=save_campaign`).
2. **`tslit_dspy.schemas.ThreatReport.save`** — checkpoint **before** md+json report write (`kind=save_threat_report`). Shared entry for `DSPyAnalyzerAdapter.analyze_and_save` and `probe_campaign.analyze_artifacts`. After allow, also flushes stashed analyze sidecars (`triage.json`, `analysis_cells.jsonl`, `analysis_summary.json`) so one vote covers the whole durable bundle.
3. **Standalone `analyze(..., write_sidecars=True)`** — if analyze is not followed by save, gates with `kind=save_analyze_sidecars` before writing triage/cells. `analyze_and_save` / `analyze_artifacts` pass `write_sidecars=False` to avoid double-Jev.
4. **`tslit_dspy.probe_campaign.dump_request_bundle`** — checkpoint **before** per-probe audit JSON write (`kind=dump_request_bundle`). Parent `dump_dir` mkdir is deferred until allow so a stop leaves no empty audit tree.
5. **`tslit_dspy.evaluate.run_evaluation`** — checkpoint **before** evaluation md + scores JSON write (`kind=save_evaluation_report`). Parent mkdir deferred until allow; one vote covers both files.
6. **`tslit_dspy.optimize.persist_mipro_compiled`** — checkpoint **before** compiled program JSON write(s) (`kind=save_mipro_compiled`). Signal / interrupt / final / logs all route here; interrupt folds output + checkpoint into one vote; mkdir deferred until allow.

Shared helper: `tslit_dspy.governance.gate.require_durable_write_allow`.

- `GOVERNANCE_CHECKPOINT=0` disables
- `GOVERNANCE_LIVE=1` → live Jev
- default mock evaluator; fail closed when gate on
- Canvas: `GOVERNANCE_CANVAS_PATH` or default ODC  
  `.../odc-canvas-sessionTSLIT-DsPy/tslit-dspy-detection-pipeline-canvas.disaggregated-v0.json` (12-rule disagg)

## Human / escalate vs allow / stop

| Action | v0 behavior at choke |
|--------|----------------------|
| allow | write proceeds |
| stop | raise `GovernanceBlocked` — no write |
| human | raise `GovernanceBlocked` — no write (fail closed; no HITL UI yet) |
| escalate | raise `GovernanceBlocked` — no write (treat as refuse until escalate channel exists) |

## Still open

- Live smoke with `AI_GATEWAY_API_KEY` + disagg canvas on Mac (report-save narrative still Switch-sensitive)
- Narrative→structured answers gap for live Jev (mock uses keyword cues)
- Probe-time network gate (adversary target logs)
- Real HITL path for `human` (today fail-closed)
- MIPRO compiled persist choke is wired (candidate 7) via `persist_mipro_compiled`; live Switch narrative for compile/deploy still open
- Evaluation report choke is wired (candidate 6); live Switch narrative for eval mode still open

## Live smoke note (2026-09-23)

Disagg canvas questions are **TSLIT-domain** (frozen `test.jsonl`, fabricate evidence, local-only transmit, probe-pair completeness, recompile/deploy). Generic “PII → personal Gmail” narratives are for the older reference canvas, not this 12-rule set.

Live allow/stop smokes must speak those constraints. `uncertain` on Switch maps to `human` (fail closed at the choke).

## Live Jev results (2026-09-23)

- **Stop proven live** at `save_campaign` choke with fabricate / frozen `test.jsonl` / autonomous deploy narrative → `action=stop`, no files written.
- **Allow flaky live**: Safety all `no` at high confidence, but `switch-TRG-S51-01` often ~0.52–0.56 → `low_confidence` → `human` (threshold 0.6). Fail-closed scorecard is correct; Switch narrative/prompt still needs tuning.
- Gateway occasionally 503s on the 12-question payload; live smoke retries.
- Mac key: ODC `.env` `VERCEL_API_KEY` is the gateway token (adapter also accepts `AI_GATEWAY_API_KEY`).
