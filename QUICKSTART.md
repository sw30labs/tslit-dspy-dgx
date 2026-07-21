# Quickstart (DGX Spark)

```bash
cd ~/Desktop/tslit-dspy-dgx
./tslit install
source .venv/bin/activate
```

## First run (offline)

```bash
./tslit smoke
./tslit doctor
./tslit policy
```

## Local vLLM detection path (American model)

```bash
~/Desktop/start-vllm.sh nemotron-super
# or: ~/Desktop/serve-local-llm.sh up nemotron-super

./tslit test-vllm
./tslit evaluate --use-compiled --test workspace/data/dev.jsonl \
  --output workspace/evaluation/dgx_dev_eval.md
```

## Mini experiment (no full MIPROv2 recompile)

```bash
./tslit experiment --mini
# → EXPERIMENT_RESULT: accuracy=… composite=…
```

## Useful commands

| What | Command |
|------|---------|
| Activate venv | `source .venv/bin/activate` |
| Install / update | `./tslit install` |
| Host + policy + vLLM | `./tslit doctor` |
| Smoke-test vLLM | `./tslit test-vllm` |
| Catalog only | `./tslit test-vllm --skip-invoke` |
| Eval compiled detector | `./tslit evaluate --use-compiled` |
| MIPROv2 compile (long) | `./tslit optimize --auto light` |
| Autoresearch experiment | `./tslit experiment` / `--mini` |
| Unit tests | `./tslit pytest` |

## Ports on this machine

| Service | Port |
|---------|------|
| vLLM inference | **8000** |

## Provider env (see `.env.example`)

```bash
TSLIT_MODEL_PROVIDER=vllm
VLLM_BASE_URL=http://127.0.0.1:8000/v1
VLLM_MODEL=nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
VLLM_API_KEY=test
VLLM_TIMEOUT_S=600
```

## Model policy (hard rule)

**Detector brain** = Nemotron / GPT-OSS / Claude / OpenAI / Llama / Grok (etc.)  
**Never** set `VLLM_MODEL` to Qwen recipes for the analyzer:

```bash
# WRONG for detector:
# ~/Desktop/start-vllm.sh qwen27
# VLLM_MODEL=Qwen/Qwen3.6-27B-FP8

# RIGHT for detector:
~/Desktop/start-vllm.sh nemotron-super
```

Qwen and other adversary-origin models remain valid **scan targets** when you probe
third-party weights; they must not optimize or run the detector.
