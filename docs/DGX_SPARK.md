# NVIDIA DGX Spark deployment — TSLIT-DSPy

**TSLIT-DSPy DGX** targets DGX Spark only for local inference. It ports the
research analyzer from `tslit-dspy-ar` onto **Ollama** (`127.0.0.1:11434`).

## Platform assumptions

- NVIDIA DGX Spark / GB10 on ARM64 Linux (DGX OS)
- Application runs in `.venv` with **Python 3.12**
- Local LLM server: **Ollama** on **127.0.0.1:11434** (`ollama serve`)
- One server serves both the detector and scan targets (different tags)

## Detection vs target models

This project’s integrity-testing premise:

> Use non-adversary / American models to **scan** adversary-origin models.

| Layer | Model | Origin policy |
|-------|--------|---------------|
| MIPROv2 compile | Muse Glimmer (Ollama) | Detection — allowed |
| Analyzer inference | Muse Glimmer (Ollama) | Detection — allowed |
| Autoresearch agent | Same Ollama detection tag | Detection — allowed |
| Models under probe | Qwen, DeepSeek, Ornith, … | Target — any origin |

Policy implementation: `tslit_dspy/model_policy.py`.  
LM routing: `tslit_dspy/lm.py` (Ollama only).

### Ollama tags on this box

| Tag | TSLIT role |
|-----|------------|
| `muse-glimmer:30b-bf16` | **Detection default** (Meta, US) |
| `qwen3.8:27b-mtp-bf16` | Target only (blocked as detector) |
| `ornith-1.5:35b` | Target only (Qwen-family; blocked as detector) |
| `deepseek-v4-flash-0731:ud-iq2-m` | Target only (blocked as detector) |

## Setup

```bash
cd ~/Desktop/code/tslit-dspy-dgx
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
ollama serve   # if not already running
./tslit test-ollama
./tslit evaluate --use-compiled --test workspace/data/dev.jsonl
```

### Mini experiment (autoresearch-compatible)

```bash
./tslit experiment --mini
```

Prints `EXPERIMENT_RESULT: accuracy=…` for agent parsers.

### Full MIPROv2 recompile on DGX

```bash
./tslit optimize --compile-model ollama --auto light
```

Local compile is slower; `config/experiment_config.json` defaults to `light`, 2 threads.

### Probe a target then analyze

Same Ollama process, two tags — no server switch. Prefer the test scripts:

```bash
./tslit test-probe                         # one probe
./tslit test-campaign                      # mini campaign + analyze
./tslit test-targets                       # one probe per served target
./tslit scan --phase all --target-model qwen3.8:27b-mtp-bf16   # raw
```

## Differences from `tslit-dspy-ar`

| Item | Research (`tslit-dspy-ar`) | DGX port |
|------|----------------------------|----------|
| Default LM | Anthropic Sonnet/Opus | Ollama Muse Glimmer |
| Local server | (cloud) | Ollama `:11434` |
| Model policy | Documented | **Enforced in code** |
| Launcher | `python -m …` | `./tslit` |
| Python | ≥3.10 | **3.12** |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Ollama not reachable` | `ollama serve` then `./tslit doctor` |
| `Model … is not allowed` | You pointed the detector at Qwen/DeepSeek/Ornith. Set `OLLAMA_MODEL=muse-glimmer:30b-bf16` |
| Configured model not in catalog | `ollama pull muse-glimmer:30b-bf16` (or match `OLLAMA_MODEL` to `ollama list`) |
| Slow MIPROv2 | Use `--auto light` and fewer threads |

## Related Desktop projects

- `grey-swan-dgx` — LangGraph  
- `driftlab-dgx` — offline-first  
- Ollama — the machine-wide LLM serving engine  
