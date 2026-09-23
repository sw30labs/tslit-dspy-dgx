# Magika decision-point inventory — tslit-dspy-dgx

Branch target: `nic/governance-checkpoint-v0`  
Inventory basis: GitHub `main` (public) + ar Magika gate pattern. Mac tip may already carry `tslit_dspy/governance/` ahead of `main` — re-verify on checkout.

Canon: Design→Canvas; Compile→DecisionContract IR; Runtime→in-agent `allow|human|escalate|stop`.  
Lean Magika-thin v0: **one choke before durable writes**. Do **not** sprinkle Jev into DSPy `forward()`.

## Summary table (v0 gating)

| # | Candidate | file:function | Side-effect class | Gate v0 | Why |
|---|-----------|---------------|-------------------|---------|-----|
| 1 | Persist probe campaign artifacts | `probe_campaign.py:save_campaign` | Durable FS write (workspace/scans NDJSON/meta/canary) | **yes** | Single choke covering the main production write path (`tslit scan` / CLI) |
| 2 | Per-probe request dump | `probe_campaign.py:dump_request_bundle` | Durable FS write (audit dumps) | later | High volume during probe; covered indirectly once campaign save is gated; gate earlier only if dumps escape workspace |
| 3 | Adapter triage + cells write | `adapter.py:TSLITAdapter.analyze` | Durable FS write (`triage.json`, `analysis_cells.jsonl`) | later | Same analyze session usually followed by report save; avoid double-prompting Jev |
| 4 | Adapter report save | `adapter.py:TSLITAdapter.analyze_and_save` + `schemas.ThreatReport.save` | Durable FS write (md+json report) | later | Important; fold under a shared `require_durable_write_allow` later if scan analyze bypasses `save_campaign` |
| 5 | Analyze artifacts summary | `probe_campaign.py:analyze_artifacts` | Durable FS write (`analysis_summary.json` + report) | later | Downstream of adapter; gate once at a shared write helper |
| 6 | Evaluation report | `evaluate.py:run_evaluation` | Durable FS write (md + scores json under workspace/evaluation) | later | Offline metric path; less “agent consequential” |
| 7 | MIPRO compiled model persist | `optimize.py:run_optimization` / `_persist_from_logs` | Durable FS write (compiled program json) | later | Training artifact; human-driven; escalate candidate if auto-deploy ever appears |
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

**Inventory count:** 18 candidates catalogued; **1 wired in v0** (`save_campaign`).

## Wired choke (v0)

**`tslit_dspy.probe_campaign.save_campaign`** calls `tslit_dspy.governance.gate.require_durable_write_allow` **before** any NDJSON/meta/canary write.

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

- Live smoke with `AI_GATEWAY_API_KEY` + disagg canvas on Mac
- Narrative→structured answers gap for live Jev (mock uses keyword cues)
- Optional second choke on `ThreatReport.save` / `analyze_and_save`
- Probe-time network gate (adversary target logs)
- Real HITL path for `human` (today fail-closed)
