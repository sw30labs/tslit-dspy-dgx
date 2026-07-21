# NVIDIA DGX Spark deployment — TSLIT-DSPy

**TSLIT-DSPy DGX** targets DGX Spark only for local inference. It ports the
research analyzer from `tslit-dspy-ar` onto the shared Desktop vLLM stack.

## Platform assumptions

- NVIDIA DGX Spark / GB10 on ARM64 Linux (DGX OS)
- Application runs in `.venv` with **Python 3.12**
- Shared model weights under `$HOME/models/huggingface`
- Shared recipes under `$HOME/models/recipes`
- vLLM OpenAI-compatible server on **127.0.0.1:8000** via:

  ```bash
  ~/Desktop/start-vllm.sh nemotron-super
  # or
  ~/Desktop/serve-local-llm.sh up nemotron-super
  ```

## Detection vs target models

This project’s integrity-testing premise:

> Use non-adversary / American models to **scan** adversary-origin models.

| Layer | Model | Origin policy |
|-------|--------|---------------|
| MIPROv2 compile | Nemotron (local) or Claude Sonnet (cloud) | Detection — allowed |
| Analyzer inference | Nemotron (local) or Claude Opus / GPT-OSS | Detection — allowed |
| Autoresearch agent | Same vLLM Nemotron (or GPT-OSS) | Detection — allowed |
| Models under probe | Qwen, DeepSeek, MiniMax, … | Target — any origin |

Policy implementation: `tslit_dspy/model_policy.py`.  
LM routing: `tslit_dspy/lm.py`.

### Shared Desktop recipes

| Recipe | Model id | TSLIT role |
|--------|----------|------------|
| `nemotron-super` | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` | **Detection default** |
| `qwen27` | `Qwen/Qwen3.6-27B-FP8` | Target only (blocked as detector) |
| `coder-next` | `Qwen/Qwen3-Coder-Next-FP8` | Target only (blocked as detector) |

## Setup

```bash
cd ~/Desktop/tslit-dspy-dgx
./tslit install          # or bash setup-venv.sh
source .venv/bin/activate
cp -n .env.example .env
./tslit doctor
```

## Runtime flows

### Offline (no GPU)

```bash
./tslit smoke
./tslit pytest
```

### Live local detection

```bash
~/Desktop/start-vllm.sh nemotron-super
./tslit test-vllm
./tslit evaluate --use-compiled --test workspace/data/dev.jsonl
```

### Mini experiment (autoresearch-compatible)

```bash
./tslit experiment --mini
```

Prints `EXPERIMENT_RESULT: accuracy=…` for agent parsers.

### Full MIPROv2 recompile on DGX

```bash
./tslit optimize --compile-model vllm --auto light
# heavy + cloud Sonnet remains the research default for paper metrics
```

Local Nemotron compile is slower and may need lower `auto` / fewer threads
(`config/experiment_config.json` defaults to `light`, 2 threads).

## Differences from `tslit-dspy-ar`

| Item | Research (`tslit-dspy-ar`) | DGX port |
|------|----------------------------|----------|
| Default LM | Anthropic Sonnet/Opus | vLLM Nemotron |
| MLX | Optional Apple path | Optional; vLLM primary |
| Model policy | Documented | **Enforced in code** |
| Launcher | `python -m …` | `./tslit` |
| Python | ≥3.10 | **3.12** |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `vLLM not reachable` | `~/Desktop/start-vllm.sh nemotron-super` then `./tslit doctor` |
| `Model … is not allowed` | You pointed the detector at Qwen/etc. Switch recipe to `nemotron-super` |
| Configured model not in `/v1/models` | Restart vLLM with the Nemotron recipe; match `VLLM_MODEL` to catalog id |
| Slow MIPROv2 | Use `--auto light`, fewer threads, or cloud Sonnet for compile only |

## Related Desktop projects

- `grey-swan-dgx` — LangGraph + Nemotron default  
- `driftlab-dgx` — offline-first + optional vLLM  
- `serve-local-llm.sh` / `start-vllm.sh` — shared inference stack  
