# TSLIT-DSPy DGX

DGX Spark port of TSLIT-DSPy. See parent research tree `../tslit-dspy-ar` for full whitepaper/R&D narrative.

## Critical

Detection LM = non-adversary / American only (Nemotron default). Adversary-origin models are scan targets, not the brain. See `tslit_dspy/model_policy.py`.

## Stack

- Python 3.12 `.venv`
- vLLM on `:8000` — `~/Desktop/start-vllm.sh nemotron-super`
- Launcher: `./tslit`

## Do not contaminate the detector with Qwen/DeepSeek/MiniMax.
