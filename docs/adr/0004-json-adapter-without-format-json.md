# ADR-0004: Custom JSON adapter that drops Ollama format=json and keeps detector thinking off

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Comments in `lm.py`, `modules.py` and `.env.example` state Muse Glimmer spends its token budget in a reasoning channel and returns `{}` when Ollama `format=json` is on.

## Decision

`ThinkingStrippedAdapter` (a JSONAdapter subclass) removes `response_format`, strips `<think>` blocks and thinking preambles, removes markdown fences, maps short field aliases to signature names, and falls back to ChatAdapter parsing. It is registered globally at import. `OLLAMA_THINK=false` by default.

## Consequences

+ Local thinking models produce parseable output.
+ Unit-tested (`tests/test_json_adapter.py`).
- Global `dspy.configure(adapter=...)` at import is a side effect of importing `modules`.
- Preamble stripping is keyword-heuristic.

## Alternatives considered

Native Ollama JSON mode (rejected per comments: yields `{}`).

## Evidence

`tslit_dspy/modules.py`; `tslit_dspy/lm.py`; `.env.example`; `tests/test_json_adapter.py`.

Reviewed at commit `862b002`.
