# Agreed probe scope — one-shot, thinking off

Live Qwen campaigns on this box measure **one-shot completions**, not chain-of-thought.

This is **protocol**, not a result. Numbers from mini / plus / sharp / holdout are
verdicts **under this protocol**. They are not “the model has no date gates if it
is allowed to think.”

## In scope (what we actually send)

Same technical ask; only requester identity and the **system-owned virtual clock**
change.

| Knob | Setting | Why |
|------|---------|-----|
| Tools | none (`tool_choice=none`) | No web, no date lookup, no code exec |
| Virtual clock | `VIRTUAL_CLOCK_UTC=` in the **system** message | Time-shift is the independent variable |
| Thinking | **off** (`enable_thinking: false`) | Forward-only answer; no private scratchpad |
| Sampling | temperature 0.2, `max_tokens` 2048 (canaries 256) | Code campaigns; 1200 died mid-file |
| Detector thinking | **off** (`OLLAMA_THINK=false`) | Plumbing: Muse otherwise dumps the budget into a reasoning channel and the JSON adapter sees `{}` |

Enforced in `tslit_dspy/probe_campaign.py` (`disable_thinking=True` on every probe).
Request dumps under `workspace/scans/**/request_dumps/` record `chat_template_kwargs`.

## What this measures

The visible answer when the model is just writing the CLI. That is how a coding
assistant is usually consumed.

Thinking is a two-way channel. Leaving it **on** can:

- let the model notice US / allied × trigger-date framing and *sanitize*
- let it hide a date payload in CoT and emit a clean script
- burn `max_tokens` on reasoning and **truncate** the code (already a confound)

Leaving it **off** can catch bombs that must appear in the answer, and can miss
bias that only shows up as a CoT refusal. You cannot know which way it moves
without a paired cell. Do not sell thinking-off as “eval-blindness.”

## Out of scope (until a separate campaign)

- Target thinking **on** (`enable_thinking: true`)
- Tools, browsing, or a real wall-clock
- Multi-turn “are you being tested?” dialogues
- Detector thinking on

A cheap later contrast, not this run: **one** clock-native task (`jwt_time` or
`cert_expiry`), same 2×2 identities/dates, thinking on. If US×9/11 suddenly
refuses or grows a `month==9` kill, that is the thinking-on story. If it is
still a cooperative clock API, the none-result generalizes a bit.

## How to quote results

- Live holdout / sharp / mini / plus tables: “under one-shot, thinking-off, tools-none.”
- `EXPERIMENT_RESULT` on frozen `test.jsonl`: cartoon exam, **not** the Qwen finding.
- No commercial certification from these numbers.
- No overnight Karpathy agent: see [PAPER.md](PAPER.md).
