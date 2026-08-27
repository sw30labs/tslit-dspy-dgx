# TSLIT-DSPy v2.0 runbook — DGX Spark / Ollama / Muse

This is the live path. The Claude cartoon exam is [`../v1.0/RUNBOOK.md`](../v1.0/RUNBOOK.md).

**Date:** 2026-08-27  
**Box:** NVIDIA DGX Spark. Ollama only (`127.0.0.1:11434`).  
**Detective:** `muse-glimmer:30b-bf16` (compiled JSON: Muse-light).  
**Default target:** `qwen3.8:27b-mtp-bf16`. Never point `OLLAMA_MODEL` at Qwen.

## Protocol

One-shot. Tools none. Virtual clock on the **system** message (`VIRTUAL_CLOCK_UTC=`). Target thinking **off**. Muse thinking **off**. English unless `lang2x2`.

Do not sell thinking-off as “the model has no date gate.”

## Commands

```bash
./tslit install && source .venv/bin/activate
./tslit doctor && ./tslit smoke && ./tslit test-ollama
./tslit evaluate --use-compiled --test workspace/data/dev.jsonl
./tslit experiment --mini          # cartoon exam, not Qwen
./tslit test-campaign              # mini 14, then analyze
./tslit test-campaign-plus         # + leftover cells
./tslit test-campaign-sharp        # clock-native 2×2
./tslit scan --campaign lang2x2 --phase probe
./tslit scan --phase analyze --artifacts workspace/scans/mini/qwen3.8_27b-mtp-bf16
# --full-analyze sends every cell to Muse (default: pairwise triage)
```

Analyze loads all `scan_*.ndjson` in the folder. `--skip-existing` appends.

## Quote

| Question | Quote |
|----------|--------|
| What did Qwen do? | Live holdout + `analysis_cells.jsonl`, thinking-off, tools-none |
| Did the detective regress on toys? | Frozen `test.jsonl` |
| Analyze `triage=skip` | Heuristic/sibling, not a Muse label |

English thinking-off (no canaries): sharp+mini+plus **70/70 `none`** (Muse-light, pre-triage). Holdout **10/10 `none`**. Qwen 2.5 latest **77/77 `none`**.

Compile from `workspace/data/train_augmented.jsonl`. Write a **named** JSON. Promote only if cartoon DEV holds. Holdout never in MIPRO.
