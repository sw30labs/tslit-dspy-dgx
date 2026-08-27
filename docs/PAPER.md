# TSLIT-DSPy on DGX Spark

**Protocol, live Qwen, and withdrawal of the Karpathy autoresearch loop**

Nicolas Cravino  
Version 1.1 — 27 August 2026  
Addendum to *The Quiet Invasion* (TSLIT-DSPy v1.0, 26 March 2026)

This is the living paper for the DGX Spark port (`tslit-dspy-dgx`). It does not
replace the threat taxonomy or the four-stage detector in v1.0. It **does**
replace how those numbers may be quoted, and it **withdraws** the autonomous
self-improvement loop from the running system.

Hypotheses, not certificates. No commercial certification from these numbers.

---

## 1. What v1.0 claimed

The March 2026 paper reported two things that this port must split:

1. **Cartoon exam.** A compiled DSPy detector (Claude Sonnet 4.6 compile, Claude
   Opus 4.6 inference, MIPROv2 `heavy`) scored **88.2% accuracy** (15/17) on a
   frozen 17-example held-out set of planted affiliation / date-gate cartoons,
   with a residual gap on subtle “compliance gatekeeping” affiliation bias.

2. **Autonomous loop.** An agent adapted from Karpathy’s `autoresearch` (March
   2026) would sit on a git branch, propose one hypothesis, edit config or
   append `train.jsonl`, run `run_experiment.sh`, parse
   `EXPERIMENT_RESULT: accuracy=…`, and keep or `git reset --hard`. Phases B
   (config) and C (append-only train data) were described as a compounding
   self-improvement engine, analogized to an antivirus signature feed.

The fitness signal for that loop **was the cartoon exam**. v1.0 treated that
exam as the product. This port does not.

---

## 2. What this port actually measures

On NVIDIA DGX Spark the detector is **Meta Muse Glimmer** via Ollama
(`muse-glimmer:30b-bf16`). Scan targets may be adversary-origin (Qwen,
DeepSeek, Ornith). Origin policy is enforced in `tslit_dspy/model_policy.py`.

Live probes are **one-shot completions, thinking off, tools none**, with the
virtual clock in a **system** message. That is protocol, not a finding. See
[SCOPE.md](SCOPE.md).

| Question | Quote this | Do not quote this |
|----------|------------|-------------------|
| What did Qwen do? | Live holdout + `analysis_cells.jsonl` under thinking-off | Cartoon `EXPERIMENT_RESULT` / v1.0 88.2% |
| Did the detective regress on toys? | Frozen `test.jsonl` | Live none-tables |
| Did a new compile still work on toys? | `dev.jsonl` promote-gate | Qwen |

**Live, Muse-light, thinking-off (no canaries):** sharp 20 + mini 12 + plus 38 =
**70/70 `none`**. Hash-guarded holdout **10/10 `none`**. Qwen 2.5 latest combined
mini/sharp/plus: **77/77 `none`**. Sibling length/code/clock/refuse tables are
descriptive, not threat labels. One notable 5× length cell on Qwen 3.8
`cert_expiry` US×9/11 (truncated); Qwen 2.5 had none. A thinking-on JWT 2×2 on
Qwen 3.8 produced **longer cooperative CLIs**, not US refusal.

Those numbers are valid only under the protocol above.

---

## 3. Withdrawal of the Karpathy loop

### 3.1 What we shipped

The DGX tree inherited:

- `scripts/agent_loop_mlx.py` — sequential agent, XML tool calls, command
  whitelist, `autoresearch/<tag>` branch
- `config/tslit_program.md` — research contract (one hypothesis, NEVER STOP)
- `scripts/run_experiment.sh` — inner trial; always prints `EXPERIMENT_RESULT`;
  MD5-guards `test.jsonl` and `live_holdout.jsonl`

Karpathy’s pattern (isolated branch, `program.md`, cheap keep-or-revert on a
frozen metric) is sound **when the metric is the research question and a trial
is cheap**. v1.0 assumed both. Live Qwen on this box is neither.

### 3.2 Why we are removing it

**Wrong score.** The agent optimized cartoon accuracy. Live Qwen under
thinking-off is cooperative clock CLIs. A better homework grade does not invent
a payload that was not in the dump. v1.0’s 88.2% remains a Claude-on-cartoons
exam score. It is not a Qwen finding.

**Too expensive.** Karpathy’s published runs were minutes-per-trial on a
training script. A Muse MIPROv2 light compile on this box is **8–12 hours**
(six Optuna trials, val 16, then the frozen exam). Three outer-loop
experiments monopolize the only local detector for more than a day and do not
talk to Qwen.

**Dead data lever.** The contract let the agent append `train.jsonl`. Compile
with `use_augmented: true` reads `train_augmented.jsonl`. New cartoon lines
never entered the mix unless a human rebuilt it. The agent also could not
touch signatures, heuristics, or `metrics.py` — the levers that actually
separate `datetime.now()` from a buried kill.

**Degenerate live gold.** Batch-1 live labels are all `none`. Point the same
keep-or-revert loop at live accuracy and it learns “always say none.” That is
both a local maximum and possibly the truth; climbing cannot tell them apart.
You cannot hill-climb a bomb that is not there.

**Nested search on the wrong exam.** MIPROv2 already searches instructions and
few-shots. Wrapping that in an overnight agent that retunes `max_labeled_demos`
is a second optimizer around the cartoon gym. The mix that mattered
(Muse-light on live-length + synthetic-long TPs) was a **human** sitting, not
an autonomous Phase C.

**We ran it.** 27 August 2026: isolated worktree, tmux, Muse, `--max-loops 3`.
The agent started reading config. We killed it after concluding the GPU was
better spent on live campaigns than cartoon grades.

### 3.3 What is deleted

Removed from this tree:

- `scripts/agent_loop_mlx.py`
- `config/tslit_program.md`

No autonomous branch, no NEVER STOP, no agent rewrite of train or config.

### 3.4 What we keep (human tools)

| Keep | Role |
|------|------|
| `./tslit optimize` | Human MIPROv2 compile. Write a **named** JSON; promote only if cartoon DEV does not collapse. |
| `./tslit evaluate` | Grade the detective on labeled JSONL. |
| `./tslit experiment --mini` | Hash-guarded **cartoon exam** on frozen `test.jsonl`. Not Qwen. Not an agent parser. |
| Hash on `test.jsonl` and `live_holdout.jsonl` | Nobody silently edits the exam or the Qwen verdict set. |
| One-hypothesis habit | Humans still change one knob, measure, keep or revert. That discipline does not need an overnight LLM. |

MIPROv2 is **not** the Karpathy loop. It is prompt search for the detective,
run when a human asks.

### 3.5 What would make a loop worth standing up again

Only if the **inner** trial is seconds and the score is the live problem:

- false-positive rate on locked live clock-API `none`
- recall on locked `synthetic_long` buried payloads
- holdout never in train

Search space: heuristics (`looks_like_date_gate`, sibling 5×-length rules), mix
*composition*, not 8-hour Muse compiles. That loop is **not** in this release.
Do not put it back as a cartoon-accuracy gym.

---

## 4. How to quote v1.0 going forward

- v1.0 88.2% / zero false positives: **Claude on planted cartoons**, March 2026.
- Autoresearch Phases B/C, “antivirus signature feed,” Tier-3 unsupervised
  compounding: **withdrawn**. Design history, not a deployed capability.
- Live Qwen on DGX: **thinking-off, tools-none, virtual clock**; Muse-light
  hypotheses of `none` on the cells we analyzed. Not a certificate that the
  weights contain no date gate under other protocols (thinking on, tools,
  multi-turn).

Cartoons stay locked (`test.jsonl` exam + mix anchors). Do not delete them.
Do not tell that story as Qwen.

---

## 5. Pointers

| Doc | Job |
|-----|-----|
| [SCOPE.md](SCOPE.md) | Thinking-off protocol |
| [PHASES.md](PHASES.md) | Compile vs scan vs evaluate vs cartoon exam |
| [PLAN_REALISTIC_VERDICT.md](PLAN_REALISTIC_VERDICT.md) | Why we did not compile 55 short cartoons |
| [DGX_SPARK.md](DGX_SPARK.md) | Box runtime |

Detector = Muse Glimmer. Target = Qwen (and others). Never swap those.
