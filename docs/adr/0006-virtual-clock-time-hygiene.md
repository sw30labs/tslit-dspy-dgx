# ADR-0006: Virtual clock in system message with pre-flight hygiene, canaries and no tools

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Date-triggered behaviour can only be tested if the target believes the injected date and cannot see the real one.

## Decision

Each probe has a system message carrying `VIRTUAL_CLOCK_UTC=<date>`; the user message is dateless. Before each request `assert_prompt_time_hygiene` checks role order, marker, date presence, no tool keys, and no real-calendar strings; with strict hygiene (default) a violation aborts the campaign. Requests set `tool_choice=none`. Optional canary probes ask for today's date and flag real-calendar leaks. Every request is dumped to `request_dumps/`.

## Consequences

+ Auditable per-request bundles.
+ Unit-tested (`tests/test_probe_hygiene.py`).
- Canary only checks the stated date, not whether the model trusts it inside generated code.
- Server-side template injection not checked on Ollama (A-006).

## Alternatives considered

Date only in user prose (rejected in module docstring: "not only user prose").

## Evidence

`tslit_dspy/probe_campaign.py` (module docstring, `build_system_message`, `assert_prompt_time_hygiene`, `evaluate_canary_response`, `dump_request_bundle`); `tests/test_probe_hygiene.py`.

Reviewed at commit `862b002`.
