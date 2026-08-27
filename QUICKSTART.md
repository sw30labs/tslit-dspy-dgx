# Quickstart (DGX Spark)

```bash
cd ~/Desktop/code/tslit-dspy-dgx
./tslit install
source .venv/bin/activate
```

## First run (offline)

```bash
./tslit smoke
./tslit doctor
./tslit policy
```

## Local Ollama detection path (American model)

```bash
# Ollama should already be running (this machine: :11434)
ollama serve   # only if doctor says it is not reachable

./tslit test-ollama
./tslit evaluate --use-compiled --test workspace/data/dev.jsonl \
  --output workspace/evaluation/dgx_dev_eval.md
```

## Cartoon exam (frozen test.jsonl, no recompile)

Not the Qwen verdict. Hash-guarded homework for the detective.

```bash
./tslit experiment --mini
# → EXPERIMENT_RESULT: accuracy=… composite=…
```

## Live model tests (scripts)

Same Ollama, two roles: `--target-model` is the scan subject; `OLLAMA_MODEL` is the detector (Muse Glimmer). Do not swap those.

```bash
./scripts/run_tests.sh              # list
./tslit test-probe                  # a) one probe vs Qwen
./tslit test-campaign               # b) ~14-probe mini campaign + analyze
./tslit test-campaign-plus          # leftover whitepaper cells (skip existing)
./tslit test-campaign-sharp         # clock-native dual-use grid (20 cells)
./tslit test-targets                # c) one probe each: Qwen, Ornith, DeepSeek
./tslit test-eval                   # d) detector eval on dev.jsonl
./tslit test-offline                # pytest + smoke + catalog
./tslit test-experiment             # mini experiment on frozen test.jsonl
```

```bash
./tslit test-probe ornith-1.5:35b
./tslit test-campaign qwen3.8:27b-mtp-bf16
./tslit test-targets --full         # mini campaign per served target (slow)
./tslit test-eval test              # frozen test.jsonl instead of dev
```

Artifacts: `workspace/scans/{one_probe,mini,targets}/<tag>/`.

## Useful commands

| What | Command |
|------|---------|
| Activate venv | `source .venv/bin/activate` |
| Install / update | `./tslit install` |
| Host + policy + Ollama | `./tslit doctor` |
| Smoke-test Ollama | `./tslit test-ollama` |
| Catalog only | `./tslit test-ollama --skip-invoke` |
| Eval compiled detector | `./tslit evaluate --use-compiled` |
| MIPROv2 compile (long) | `./tslit optimize --auto light` |
| Cartoon exam (not Qwen) | `./tslit experiment --mini` |
| One live probe | `./tslit test-probe` |
| Mini campaign + analyze | `./tslit test-campaign` |
| Plus campaign (old TSLIT leftover) | `./tslit test-campaign-plus` |
| Sharp campaign (clock-native grid) | `./tslit test-campaign-sharp` |
| Other box targets | `./tslit test-targets` |
| Detector eval (JSONL) | `./tslit test-eval` |
| Probe a target (raw) | `./tslit scan --phase all --target-model qwen3.8:27b-mtp-bf16` |
| Analyze with pairwise triage | `./tslit scan --phase analyze --artifacts workspace/scans/mini/qwen3.8_27b-mtp-bf16` |
| Analyze every cell (no triage) | add `--full-analyze` |
| EN/ZH × US/CN language grid | `./tslit scan --campaign lang2x2 --phase probe` |
| Unit tests | `./tslit pytest` |

## Ports on this machine

| Service | Port |
|---------|------|
| Ollama | **11434** |

## Env (see `.env.example`)

```bash
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=muse-glimmer:30b-bf16
OLLAMA_API_KEY=ollama
OLLAMA_TIMEOUT_S=600
```

## Model policy (hard rule)

**Detector brain** = Muse Glimmer / Llama / GPT-OSS / Nemotron / Claude / Grok  
**Never** set `OLLAMA_MODEL` to Qwen / DeepSeek tags for the analyzer:

```bash
# WRONG for detector:
# OLLAMA_MODEL=qwen3.8:27b-mtp-bf16

# RIGHT for detector:
# OLLAMA_MODEL=muse-glimmer:30b-bf16

# RIGHT for scan target:
./tslit scan --target-model qwen3.8:27b-mtp-bf16
```

Qwen and other adversary-origin models remain valid **scan targets** when you probe
third-party weights; they must not optimize or run the detector.
