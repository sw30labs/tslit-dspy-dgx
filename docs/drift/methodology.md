# Adversary-drift instrument

This is the measurement path for affiliation-conditioned drift in model output. It replaces that use of the old persona prompts. It does not replace the temporal probe campaigns, and it does not add a Magika choke.

## What was wrong with the previous claim

An audit of the predecessor TSLIT prompts and of the four Qwen 2.5 scans in this repo (2026-08-26/27, `qwen2.5:latest` via Ollama, temperature 0.2, 82 probes) found that "Qwen 2.5 writes buggier code for non-adversary personas" was not supported:

1. Persona and task were confounded. Only 2 of 10 persona prompts were matched swaps. Some neutral tasks matched a persona substring by accident (`us-` inside `malicious-payload-filter`).
2. One sample per cell, temperature 0.7 in the predecessor, seed not logged. A few hundred samples cannot see a 5 point effect.
3. Code was never executed. "Risk" was a keyword count, and it penalised `cryptography` and `requests`. A judge saw the persona and a biased aggregate, then invented statistics.
4. Aggregates summed unequal groups instead of reporting rates.
5. The persona-bias detector could only fire for Western personas. The refusal detector missed "I'm sorry, but I can't assist with that."
6. Time was only prompt text. Model digest, quant, and serving stack were not recorded together.
7. "Adversarial" meant US, Five Eyes, NATO, and Israel in one README and something else in another, with no statement of whose adversary.

## Design

Factorial cells are task × persona × template × position × decoding profile × repeat.

- **49 tasks** in seven categories (parsing, stdlib crypto API, concurrency, validation, SQL, file I/O, numeric). Each has a reference solution and a hidden pytest module. The prompt names the function. The tests do not ship in the prompt.
- **25 personas.** 6 adversary, 6 aligned, 6 neutral, 6 placebo, 1 none. See `docs/drift/adversary-definition.md`.
- **3 sentence templates** (`t_direct`, `t_role`, `t_org`). The primary estimate uses `t_direct` only.
- **2 positions** (affiliation sentence before the task, or after it), fully crossed in the primary so position is not aliased with persona.
- Within a task, template, and position, user prompts for slotted personas differ only by the slot string. A unit test renders the whole bank and checks that. `none` deletes the sentence; it is a different arm, not a fake slot.
- Correctness is the sandbox: subprocess, timeout, socket `connect` blocked, secret-looking environment variables removed. Pass, fail, syntax error, timeout, and harness error are different outcomes.
- Refusal and no-code are separate indicators. They are not coded as buggy.
- Static tools (ruff, pyflakes via ruff's F rules, bandit if installed) are secondary. A missing tool is `not_installed`, not a failure.
- Run order is a seeded shuffle. Each cell gets a derived seed, logged. Requests are single-turn. `X-Request-Id` is a header, not a prompt token, so it cannot break the swap. vLLM-style `cache_prompt: false` is sent only on the OpenAI-compatible config. Ollama does not get that field. The shared prefix is the system prompt, which contains no persona.
- A virtual clock, if set, is one line on the system prompt for every cell alike. Default is null. It is prompt text. This instrument does not claim the server honours it.
- Provenance on every record: model id, quant parsed from the tag, digest when the server returns one, backend name and version, prompt bytes and sha256, system prompt, timestamps, token counts and finish reason as the backend reported them, seed, temperature, `top_p`.

## How to run

```bash
./tslit drift-power          # sample-size plan, no model
./tslit drift-smoke          # 8 mock cells, hidden tests, no model
./tslit drift-run --config config/drift/ollama.yaml            # refuses
./tslit drift-run --config config/drift/ollama.yaml --allow-live
./tslit drift-run --config config/drift/openai_compat.yaml --allow-live
```

`ollama.yaml` targets `qwen3.8:27b-mtp-bf16` on `127.0.0.1:11434`, the repo's existing Ollama target. `qwen2.5:latest` is the tag from the August 2026 scans; it is not a pin, and a run without a digest is marked `provenance_ok: false`. `openai_compat.yaml` is the same protocol against `OPENAI_BASE_URL` and `DRIFT_TARGET_MODEL`, which covers a vLLM or MLX server that already speaks the chat-completions API this repo uses. Neither config is executed by tests. Do not download weights from CI.

Smoke writes nothing unless `--output` is set. Live runs default to `workspace/drift-runs/`, which is gitignored. Drift artifacts are not one of the five Magika durable-write families, and this package does not call the gate.

## Threats to validity

- **Construct.** "Adversary" is a rule about a China-origin model's geopolitical neighbourhood, not a property of the person. Mis-specified countries move the contrast. Moderate-clarity personas are tagged so they can be dropped.
- **Lexical artifacts.** Slot length, sentence template, and position can move the model. Length is a covariate in the secondary regression. Template is a separate audit. Position is counterbalanced and averaged, which estimates an effect marginalised over position, not a pure "name only" effect inside one sentence location. The matched-swap test shows the strings differ only by the slot; it does not show the model ignores length.
- **Safety policy.** Civilian offices were chosen so one side is not a military cyber command. Pariah-state organs were left out because they trigger refusals for reasons other than the contrast. Residual safety policy can still differ by country name. That is why refusal is not folded into buggy.
- **Floor and ceiling.** These are small standard-library functions. A model that always passes, or always fails, cannot show a 5 point gap. Report the neutral-arm failure rate before interpreting a difference. Results do not transfer to large programs.
- **Oracle gap.** Hidden tests miss bugs they do not assert. A reference that passes is necessary, not a proof that the tests are complete.
- **Sandbox.** The network block patches `socket` in the child before import. It is a harness. It is not a jail. Timeout is its own outcome.
- **Dependence.** The power calculation's 4.5 point figure assumes persona-level noise inside a task. If the model fails a whole stratum the same way, the relevant N is closer to 49 tasks and the detectable effect is much larger (about 27 points for a single draw). Publish the CI.
- **Multiple comparisons.** Five contrasts × three families. Holm is inside each family. Slicing by use case after seeing the data is exploratory.
- **`none` is under-powered for 5 points** at the default (one persona). Do not read a null placebo-versus-none result as "affiliation text does nothing."
- **Judge.** If a framing judge is added later, it has to stay blind and qualitative. A number that originated in the judge is not a result of this instrument.
- **Server.** Temperature 0 is not extra N. A digest-less `:latest` tag is not a replicate of a previous scan. KV cache of the system prompt is shared on purpose; conversation state is not. If a server rejects `seed` or `cache_prompt`, record that and do not silently drop it from the log.
- **Language and turn shape.** English, one shot, no tools. A drift result here does not speak to Chinese prompts or multi-turn sessions.
- **Recognition.** A model may notice the template. The placebo arm and the lexical audit are the checks we have, not a guarantee of blindness.

## Out of scope

Implanting a backdoor, evasive jailbreaks, and operational targeting of a real organisation are out of scope. The tasks are ordinary utilities. HOTP, HKDF, and zip-member screening are defensive exercises with public test vectors.
