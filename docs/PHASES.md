# TSLIT in plain English — what each phase is

You are not compiling Qwen. You are not compiling the 14/20/43 live answers.
Those are **suspect interviews**. Compile is **rewriting the detective’s cheat sheet**.

## Two models, one Ollama

| Role | Who (this box) | Job |
|------|----------------|-----|
| **Target** (suspect) | Qwen, DeepSeek, Ornith, … | Gets the probes. May be adversary-origin. |
| **Detector** (detective) | Muse Glimmer (Meta, US) | Reads the suspect’s answers and hypothesizes threats. |

Never put Qwen in `OLLAMA_MODEL`. That env var is the detective only.

## Two kinds of data

| Stuff | What it is | Used for |
|-------|------------|----------|
| `workspace/scans/…` (14 mini + 43 plus + 20 sharp) | Live Qwen transcripts | **Scan / analyze** |
| `workspace/data/train.jsonl` (55) | Cartoon labeled examples | Cartoon-exam anchors only (subset copied into mix) |
| `workspace/data/train_live_qwen.jsonl` (28) | Batch 1 live labels (all `none`) | Source for compile slice |
| `workspace/data/synthetic_long.jsonl` | Long CLIs: clock API vs buried payload | Rare true positives |
| `workspace/data/train_augmented.jsonl` | Compile mix (~69) | **Compile** when `use_augmented: true` |
| `workspace/data/live_holdout.jsonl` (10) | Live Qwen **verdict** set. Hash-guarded. | Evaluate only — **never MIPRO** |
| `workspace/data/dev.jsonl` (14) | Labeled, not frozen | Tune / everyday `evaluate` |
| `workspace/data/test.jsonl` (17) | Cartoon **exam**. Frozen. Do not edit. | **`experiment` only** (not the Qwen result) |
| `workspace/compiled/tslit_analyzer_optimized.json` | The detective’s **prompts + few-shot examples** | Loaded by analyze / evaluate |

Do not dump all 77 live cells into compile. `EXPERIMENT_RESULT` is the cartoon exam, not the Qwen verdict.

## What “compile” means

The detector is **not** a fine-tuned weight file. It is a four-step DSPy program:

1. Classify: none / affiliation bias / time bomb / combined  
2. Quote evidence (must be verbatim)  
3. Risk score 0–100  
4. QA (catch false positives)

Each step is **English instructions + a handful of worked examples**.  
`./tslit optimize` = MIPROv2 searches for better instructions/examples using **train.jsonl**, talking to **Muse Glimmer**, and **overwrites** `tslit_analyzer_optimized.json`.

- Does **not** change Muse Glimmer’s weights.  
- Does **not** probe Qwen.  
- Slow (dozens of detective calls).  

You already have a **Claude-era** JSON (Jul 21). A **Muse-native** compile was started separately; until that job **finishes**, analyze/evaluate still use the Claude-era file. Backup: `tslit_analyzer_optimized.claude-era.json`.

## The phases (in the order you actually use them)

```
         live suspect                         labeled homework
              │                                      │
              ▼                                      ▼
   ┌─────────────────────┐              ┌─────────────────────┐
   │ 1. SCAN  (probe)    │              │ train.jsonl          │
   │ Ask Qwen            │              │ (synthetic labels)   │
   │ → scans/*.ndjson    │              └──────────┬──────────┘
   └──────────┬──────────┘                         │
              │                                    ▼
              │                         ┌─────────────────────┐
              │                         │ 3. OPTIMIZE         │
              │                         │ Rewrite detective   │
              │                         │ prompts (MIPROv2)   │
              │                         │ → compiled/*.json   │
              │                         └──────────┬──────────┘
              │                                    │
              ▼                                    ▼
   ┌─────────────────────────────────────────────────────────┐
   │ 2. ANALYZE          and/or          4. EVALUATE          │
   │ Detective reads live answers        Detective graded on  │
   │ Hypothesis, no answer key           labeled JSONL        │
   └─────────────────────────────────────────────────────────┘
                         │
                         ▼
              5. EXPERIMENT = optimize + evaluate on frozen test.jsonl
                 (--mini = skip optimize, exam only)
```

### 1. Scan (probe)

**Ask the suspect.** Same technical job; only identity and virtual date change.

| Command | Size |
|---------|------|
| `./tslit test-probe` | 1 ask |
| `./tslit test-campaign` | mini **14** |
| `./tslit test-campaign-plus` | **43** extra paper cells |
| `./tslit test-campaign-sharp` | **20** clock-native cells |
| `./tslit test-targets` | other models on this box |

Writes `workspace/scans/…/*.ndjson`. No verdict yet.

### 2. Analyze

**Detective reads those transcripts.** Muse Glimmer + compiled prompts.

```bash
./tslit scan --phase analyze \
  --artifacts workspace/scans/mini/qwen3.8_27b-mtp-bf16
```

`--phase all` on a campaign = probe then analyze.  
Output is a **hypothesis** (`analysis_report.md`), not a certification.

On this box: mini 14 was analyzed (Claude-era prompts). Plus 43 and sharp 20 were probed, **not** analyzed yet.

### 3. Optimize (compile)

**Rewrite the detective’s cheat sheet** from `train_augmented.jsonl` (when `use_augmented` is true). See above.

Do **not** compile on the 55 cartoons. Write Muse-native output beside Claude-era, do not overwrite it:

```bash
./tslit optimize --compile-model ollama --auto light \
  --output workspace/compiled/tslit_analyzer_optimized.muse-light.json
```

### 4. Evaluate

**Grade the detective** on labeled JSONL (usually `dev.jsonl`). Does not talk to Qwen.

```bash
./tslit evaluate --use-compiled --test workspace/data/dev.jsonl
```

### 5. Experiment

Research-loop wrapper:

- full: optimize, then evaluate on **frozen `test.jsonl`**
- `--mini`: skip optimize; exam only

Always prints `EXPERIMENT_RESULT: accuracy=…` (even on failure).  
Hash-guards `test.jsonl` so nobody edits the exam.

## Cheat sheet

| I want to… | Run |
|------------|-----|
| Interrogate Qwen | `test-campaign` / `plus` / `sharp` |
| Get a verdict on saved interviews | `scan --phase analyze` |
| See if the detective is any good | `evaluate` or `experiment --mini` |
| Teach the detective better English | `optimize` (compile) |
| One scored research trial | `experiment` |

**Compile = prompts for the detective. Scan = questions for the suspect.**
