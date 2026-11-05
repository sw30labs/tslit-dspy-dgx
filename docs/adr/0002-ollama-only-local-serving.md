# ADR-0002: Serve all models through local Ollama only

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

The DGX port originally carried a vLLM layer (`test-vllm` compat alias, `--fetch-rendered` /tokenize leftover). Commit 6493369 is titled "Switch DGX runtime to Ollama and expand live campaigns."

## Decision

All LMs (detector and target) are reached via Ollama at `OLLAMA_BASE_URL` (default `http://127.0.0.1:11434`). DSPy uses `ollama_chat/<tag>`; probes use the OpenAI-compatible `/v1` endpoint. Detector and target are two tags on the same server.

## Consequences

+ One server, simple ops on a DGX Spark; `doctor` checks `/api/tags`.
+ No hosted API keys required (`OLLAMA_API_KEY=ollama`).
- Rendered-prompt hygiene (`try_fetch_rendered_prompt`) cannot work on Ollama, so server-side chat-template injection of a real date is unverified (A-006).
- Both models share one GPU/server; contention behaviour undocumented.

## Alternatives considered

vLLM (previously used, replaced; `tslit` keeps `test-vllm` as a compat alias). MLX (named in whitepaper v2.0 README as replaced).

## Evidence

`tslit_dspy/lm.py`; `tslit_dspy/probe_campaign.py` (`try_fetch_rendered_prompt`, `DEFAULT_OLLAMA_OPENAI_BASE`); `tslit` (test-vllm case); `whitepaper/v2.0/README.md`; commit 6493369.

Reviewed at commit `862b002`.
