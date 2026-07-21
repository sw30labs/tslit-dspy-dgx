<div align="center">

# TSLIT-DSPy — DGX Spark Port

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![DSPy](https://img.shields.io/badge/DSPy-MIPROv2-4B8BBE.svg)
![DGX](https://img.shields.io/badge/NVIDIA-DGX%20Spark-76B900.svg)
![Policy](https://img.shields.io/badge/detector-US%20%2F%20non--adversary-success.svg)

**Time-Shift LLM Integrity Testing** with a DSPy / MIPROv2 analyzer, adapted for
**NVIDIA DGX Spark (GB10 / Linux aarch64)** and a **local vLLM** stack.

</div>

Port of [`tslit-dspy-ar`](../tslit-dspy-ar) using the same Desktop DGX conventions as
`grey-swan-dgx`, `driftlab-dgx`, and `youtube-scribe-dgx`.

## What this is

A defensive research pipeline that analyzes **synthetic probe responses** for:

- affiliation bias  
- temporal logic bombs  
- combined threats  

The **detection brain** (compile, inference, autoresearch) must use **non-adversary /
American models**. Adversary-origin open weights (Qwen, DeepSeek, MiniMax, …) are
**scan targets only** — never part of the detector.

| Role | Allowed examples | Blocked examples |
|------|------------------|------------------|
| **Detection stack** | NVIDIA Nemotron, GPT-OSS, Claude, OpenAI GPT, Llama, Grok | Qwen, DeepSeek, MiniMax, Kimi/Moonshot |
| **Scan targets** | Any model under integrity test (including adversary-origin) | — |

Enforced in code: `tslit_dspy/model_policy.py` (raises if you point the analyzer at a blocked model).

## DGX defaults

| Setting | Default |
|---------|---------|
| Provider | `vllm` |
| Detection model | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` |
| Recipe | `~/Desktop/start-vllm.sh nemotron-super` |
| Endpoint | `http://127.0.0.1:8000/v1` |
| Python | **3.12** project `.venv` |
| Timeout | **600s** for long local prefills |

**Do not** use `qwen27` or `coder-next` recipes for the analyzer. Those are fine as
optional *target* models when probing, not as the detector.

## Quick start

```bash
cd ~/Desktop/tslit-dspy-dgx
./tslit install
source .venv/bin/activate
./tslit doctor
./tslit smoke

# Start American detection LM
~/Desktop/start-vllm.sh nemotron-super
./tslit test-vllm

# Evaluate with compiled prompts (dev set)
./tslit evaluate --use-compiled --test workspace/data/dev.jsonl

# Mini experiment (eval only, no recompile)
./tslit experiment --mini
```

See [QUICKSTART.md](QUICKSTART.md) and [docs/DGX_SPARK.md](docs/DGX_SPARK.md).

## Project layout

```text
tslit-dspy-dgx/
  tslit_dspy/           # DSPy pipeline + DGX LM routing + model policy
  workspace/data/       # train / dev / test JSONL (frozen test set)
  workspace/compiled/   # portable MIPROv2 JSON prompts
  scripts/              # run_experiment.sh, agent_loop_mlx.py
  config/               # experiment_config.json, tslit_program.md
  tests/
  setup-venv.sh
  tslit                 # launcher
```

## Cloud R&D (optional)

For parity with the research paper (Sonnet compile / Opus infer):

```bash
# .env
TSLIT_MODEL_PROVIDER=cloud
ANTHROPIC_API_KEY=...

./tslit optimize --compile-model anthropic/claude-sonnet-4-6 --auto light
./tslit evaluate --model anthropic/claude-opus-4-6 --use-compiled
```

Still blocked: any Qwen/DeepSeek/etc. for those roles.

## Responsible use

Defensive integrity testing only. Synthetic labels. Outputs are hypotheses, not
certifications. See [SECURITY.md](SECURITY.md) and the upstream README in
`tslit-dspy-ar`.

## Lineage

| Tree | Focus |
|------|--------|
| `tslit-dspy-ar` | Research release, whitepaper, cloud R&D metrics |
| **`tslit-dspy-dgx` (this repo)** | DGX Spark runtime, vLLM Nemotron default, origin policy |
