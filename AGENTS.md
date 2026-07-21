# AGENTS.md — TSLIT-DSPy DGX

## Mission

Port of TSLIT-DSPy integrity testing to NVIDIA DGX Spark. Defensive research only.

## Hard rule — model origin

**Detection stack** (compile, inference, autoresearch brain, adapter) must use
**non-adversary / American** models:

- Preferred local: `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` via `start-vllm.sh nemotron-super`
- Allowed: GPT-OSS, Claude, OpenAI GPT, Llama, Grok, Nova, Gemini, Phi, Mistral

**Never** use Qwen, DeepSeek, MiniMax, Moonshot/Kimi, etc. as the detector.
Those are **scan targets only**. Policy is enforced in `tslit_dspy/model_policy.py`.

## Commands

```bash
./tslit install | doctor | smoke | test-vllm | evaluate | optimize | experiment | pytest
```

## Do not

- Point `VLLM_MODEL` at Qwen recipes for the analyzer
- Edit `workspace/data/test.jsonl` (hash-guarded)
- Claim commercial certification from synthetic eval metrics
