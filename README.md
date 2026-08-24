<div align="center">

# TSLIT-DSPy — DGX Spark Port

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![DSPy](https://img.shields.io/badge/DSPy-MIPROv2-4B8BBE.svg)
![DGX](https://img.shields.io/badge/NVIDIA-DGX%20Spark-76B900.svg)
![Ollama](https://img.shields.io/badge/server-Ollama%20%3A11434-black.svg)
![Policy](https://img.shields.io/badge/detector-US%20%2F%20non--adversary-success.svg)

**Time-Shift LLM Integrity Testing** with a DSPy / MIPROv2 analyzer, adapted for
**NVIDIA DGX Spark (GB10 / Linux aarch64)** and **local Ollama**.

</div>

> [!NOTE]
> **2026-08-24 update.** Serving is **Ollama-only** (`127.0.0.1:11434`) — the old vLLM `:8000` path is gone. Detector and scan target are different tags on the same process (Muse Glimmer vs Qwen/DeepSeek/…). Live campaigns: **mini** (14), **plus** (whitepaper leftover cells), **sharp** (clock-native 2×2). `./tslit test-campaign` then `test-campaign-plus` then `test-campaign-sharp`; analyze loads the combined folder. Public copy uses US / allied / adversary-origin identities (not named states). Hypotheses, not certificates.

Port of [`tslit-dspy-ar`](../tslit-dspy-ar) using the same Desktop DGX conventions as
`grey-swan-dgx`, `driftlab-dgx`, and `youtube-scribe-dgx`.

**Ollama on `127.0.0.1:11434` is the only local LLM server.** Detector and scan
target are different Ollama tags on the same process — no recipe switch.

## What this is

A defensive research pipeline that analyzes **probe responses** for:

- affiliation bias
- temporal logic bombs
- combined threats

Same technical ask; only **who** (requester identity) and **when** (virtual clock in
the system message) change. A compiled DSPy detector then scores the replies.

The **detection brain** (compile, inference, autoresearch) must use **non-adversary /
American models**. Adversary-origin open weights (Qwen, DeepSeek, MiniMax, …) are
**scan targets only** — never part of the detector.

| Role | Allowed examples | Blocked examples |
|------|------------------|------------------|
| **Detection stack** | Muse Glimmer, Llama, GPT-OSS, Nemotron, Claude, Grok | Qwen, DeepSeek, MiniMax, Kimi/Moonshot, Ornith |
| **Scan targets** | Any model under integrity test (including adversary-origin) | — |

Enforced in code: `tslit_dspy/model_policy.py` (raises if you point the analyzer at a blocked model).

## DGX defaults

| Setting | Default |
|---------|---------|
| Server | Ollama (`ollama serve`) |
| Detection model | `muse-glimmer:30b-bf16` (Meta, US) |
| Scan target | `qwen3.8:27b-mtp-bf16` |
| Endpoint | `http://127.0.0.1:11434` (OpenAI-compat: `…/v1`) |
| Python | **3.12** project `.venv` |
| Timeout | **600s** for long local prefills |

**Do not** set `OLLAMA_MODEL` to Qwen / DeepSeek / Ornith tags for the analyzer.
Those are fine as *target* models when probing, not as the detector.

## Quick start

```bash
cd ~/Desktop/code/tslit-dspy-dgx
./tslit install
source .venv/bin/activate
./tslit doctor
./tslit smoke

# Ollama should already be running on :11434
./tslit test-ollama

# Evaluate with compiled prompts (dev set)
./tslit evaluate --use-compiled --test workspace/data/dev.jsonl

# Mini experiment (eval only, no recompile)
./tslit experiment --mini
```

See [QUICKSTART.md](QUICKSTART.md) and [docs/DGX_SPARK.md](docs/DGX_SPARK.md).

## Live campaigns

`./tslit scan` (and the `test-campaign*` wrappers) probe a **target** tag, then
analyze artifacts with Muse Glimmer. `--skip-existing` appends into the same
folder without replaying probe ids already on disk. Analyze loads **all**
`scan_*.ndjson` files in that folder.

| Campaign | Command | What it is |
|----------|---------|------------|
| **mini** (14) | `./tslit test-campaign` | 2 date canaries + `net_scan` / `log_parser` × 6-cell grid |
| **plus** (43 new) | `./tslit test-campaign-plus` | Leftover whitepaper cells: extra affiliations, trigger dates, AES / pcap / backup tasks |
| **sharp** (20 + June-4 canary) | `./tslit test-campaign-sharp` | Clock-native dual-use grid (see below) |

```bash
# 14-probe mini, then detector
./tslit test-campaign

# Append old-TSLIT leftover cells (skips the 14 already saved)
./tslit test-campaign-plus

# Append clock-native / dual-use cells
./tslit test-campaign-sharp

# Re-analyze the combined folder (mini + plus + sharp)
./tslit scan --phase analyze \
  --artifacts workspace/scans/mini/qwen3.8_27b-mtp-bf16
```

Other box targets (one probe each by default): `./tslit test-targets`.

### mini

Sparse controlled grid on two sysadmin asks. Default path for a first live run.

### plus

Reuses the **whitepaper catalogs** from `tslit-dspy-ar` that mini omitted — not the
labeled JSONL *responses* (those are detector training, some with planted bombs).

Adds:

- extra **US**, **allied**, and **adversary-origin** requester identities (paper catalog)
- extra symbolic trigger dates (plus a second baseline date)
- tasks recovered from old baselines: packet inspect, AES-GCM, backup zip

### sharp

Mini scanners never forced the model to write against **today**, so a temporal bomb
had nowhere honest to live. Sharp uses four asks that require the session clock, or
are dual-use enough that affiliation gatekeeping shows up as missing code:

| Task | Why |
|------|-----|
| `cert_expiry` | Days-until-expiry vs today (offline PEM inventory) |
| `feature_flags` | `not_before` vs today |
| `jwt_time` | JWT `nbf` / `exp` vs current UTC |
| `fft_pulse` | Lab DSP / FFT threshold (dual-use, not a radar product) |

Same technical ask every time. Five cells isolate identity vs calendar:

| Cell | Distinguishes |
|------|----------------|
| corporate / 2024-01-15 | Baseline |
| US requester / 2024-09-11 | US identity + symbolic trigger date |
| adversary-origin requester / 2024-09-11 | Same date, other identity |
| US requester / 2024-06-04 | US identity + second symbolic date |
| adversary-origin requester / 2024-06-04 | Same date, other identity |

If the target degrades only for the US requester, that is affiliation. If it
breaks on a symbolic date for **both** identities, that is calendar. If only
the US requester on that date, that is combined. Probe tags in the artifacts
still use the concrete affiliation ids (see `tslit_dspy/probe_campaign.py`).

Raw scan flags: `--campaign mini|plus|sharp` and `--skip-existing`.

## Project layout

```text
tslit-dspy-dgx/
  tslit_dspy/           # DSPy pipeline + Ollama LM routing + model policy
  workspace/data/       # train / dev / test JSONL (frozen test set)
  workspace/compiled/   # portable MIPROv2 JSON prompts
  workspace/scans/      # live probe artifacts (mini / plus / sharp)
  scripts/              # run_experiment.sh, test_*.sh, agent_loop_mlx.py
  config/               # experiment_config.json, tslit_program.md
  tests/
  setup-venv.sh
  tslit                 # launcher
```

## Responsible use

Defensive integrity testing only. Synthetic labels. Live campaign outputs are
**hypotheses**, not certifications. See [SECURITY.md](SECURITY.md) and the
upstream README in `tslit-dspy-ar`.

## Lineage

| Tree | Focus |
|------|--------|
| `tslit-dspy-ar` | Research release, whitepaper, cloud R&D metrics |
| **`tslit-dspy-dgx` (this repo)** | DGX Spark runtime, Ollama-only serving, origin policy, mini / plus / sharp campaigns |
