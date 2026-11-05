# ADR-0007: Live probes are one-shot, tools-none, target thinking off (agreed scope)

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Commit ea72252 is titled "Promote Muse-light as the detective and pin thinking-off live scope." docs/PAPER.md lists thinking-on and tools-on as future campaigns.

## Decision

Probes send `chat_template_kwargs.enable_thinking=false` unless `--thinking` is passed; single answer, no tools. Results are quoted only as thinking-off; docs warn not to claim "the model has no date gate."

## Consequences

+ Bounded, reproducible campaigns.
- Behaviour that only appears with reasoning or tools is out of scope; 70/70 `none` is explicitly a hypothesis.

## Alternatives considered

Thinking-on and tools-on (deferred to future campaigns per PAPER.md roadmap).

## Evidence

`tslit_dspy/probe_campaign.py` (`_chat_create_no_tools`, `run_probe_campaign`); `tslit_dspy/cli.py` (`--thinking`); docs/PAPER.md (Protocol, Status); commit ea72252.

Reviewed at commit `862b002`.
