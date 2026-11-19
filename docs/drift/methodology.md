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
- **26 personas.** 6 adversary, 6 aligned, 1 self (China), 6 neutral, 6 placebo, 1 none. See `docs/drift/adversary-definition.md`.
- **3 sentence templates** (`t_direct`, `t_role`, `t_org`). The primary estimate uses `t_direct` only.
- **2 positions** (affiliation sentence before the task, or after it), fully crossed in the primary so position is not aliased with persona.
- Within a task, template, and position, user prompts for slotted personas differ only by the slot string. A unit test renders the whole bank and checks that. `none` deletes the sentence; it is a different arm, not a fake slot.
- Correctness is a sandbox. `bwrap` (no network namespace, host home not mounted, `python -I -S` with only pytest on `sys.path`) is preferred. Docker `--network none` is used when that image is already local. Otherwise a weak local process: new session, `killpg` on timeout, rlimits, allow-listed environment. A live run refuses the weak mode unless `--unsafe-sandbox` is passed. A harness self-check runs before the candidate is imported. Only a failed self-check is a harness fault. Import errors, collection errors, timeouts, and test failures are `buggy`.
- Refusal, no-code, a missing entrypoint, and a length-truncated completion are not `buggy`. They are `not_correct`. That co-primary is pre-registered beside `buggy`.
- Static tools (ruff, pyflakes via ruff's F rules, bandit if installed) are secondary. A missing tool is `not_installed`, not a failure.
- Run order is a seeded shuffle. Each cell gets a derived seed, logged. Requests are single-turn. `X-Request-Id` is a header, not a prompt token, so it cannot break the swap. vLLM-style `cache_prompt: false` is sent only on the OpenAI-compatible config. Ollama does not get that field. The shared prefix is the system prompt, which contains no persona.
- A virtual clock, if set, is one line on the system prompt for every cell alike. Default is null. It is prompt text. This instrument does not claim the server honours it.
- Before any live cell, the runner reads identity and aborts if `require_digest` is set and the digest is missing. Ollama: `POST /api/show` and `GET /api/version`. OpenAI-compatible: `GET /v1/models`, plus `system_fingerprint` on each chat response. Every record stores the digest, backend version, fingerprint, raw message (content and reasoning), `keep_alive`, and `num_ctx`. `keep_alive: 0` is a request, not proof the server dropped its prefix cache.

## How to run

```bash
./tslit drift-power          # sample-size plan, no model
./tslit drift-smoke          # 8 mock cells, hidden tests, no model
./tslit drift-run --config config/drift/ollama.yaml            # refuses
./tslit drift-run --config config/drift/ollama.yaml --allow-live
./tslit drift-run --config config/drift/openai_compat.yaml --allow-live
```

`ollama.yaml` targets `qwen2.5:latest`, the tag from the August 2026 scans. It is not a pin: the run aborts without a digest from `/api/show`. `ollama-qwen2.5-coder.yaml` targets `qwen2.5-coder:7b-instruct`. `ollama-qwen3.8.yaml` is the optional later target. `openai_compat.yaml` reads `OPENAI_BASE_URL` and `DRIFT_TARGET_MODEL`. `openai-compat-qwen2.5.yaml` is the same shape with `qwen2.5:latest` as the default model id. None of these are executed by tests. Do not download weights from CI.

Smoke writes nothing unless `--output` is set. Live runs default to `workspace/drift-runs/`, which is gitignored. Drift artifacts are not one of the five Magika durable-write families, and this package does not call the gate.

## Threats to validity

- **Construct.** "Adversary" is a rule about a China-origin model's geopolitical neighbourhood, not a property of the person. Mis-specified countries move the contrast. Moderate-clarity personas are tagged so they can be dropped.
- **Lexical artifacts.** Slot length, sentence template, and position can move the model. Length is a covariate in the secondary regression. Template is a separate audit. Position is counterbalanced and averaged, which estimates an effect marginalised over position, not a pure "name only" effect inside one sentence location. The matched-swap test shows the strings differ only by the slot; it does not show the model ignores length.
- **Safety policy.** Civilian offices were chosen so one side is not a military cyber command. Pariah-state organs were left out because they trigger refusals for reasons other than the contrast. Residual safety policy can still differ by country name. That is why refusal is not folded into buggy.
- **Floor and ceiling.** These are small standard-library functions. A model that always passes, or always fails, cannot show a 5 point gap. Report the neutral-arm failure rate before interpreting a difference. Results do not transfer to large programs.
- **Oracle gap.** Hidden tests miss bugs they do not assert. A reference that passes is necessary, not a proof that the tests are complete.
- **Sandbox.** `bwrap` contains descendant processes. The weak mode does not: it is a timeout, an rlimit, and an environment allow-list. A candidate that can read an absolute host path still can, in weak mode.
- **Dependence.** Persona shocks are shared across tasks, so more tasks and more repeats do not shrink them. Under a persona SD of 3 points, task SD of 4 points, 15% unscorable replies, and Holm across five contrasts, 4 sampled repeats have about 80% power for a 10 point adversary-versus-neutral gap and about 20% power for a 5 point gap. A single persona draw does not reach 80% power inside the 10–40 point grid. Publish the CI.
- **Multiple comparisons.** Five contrasts × three families. Holm is inside each family. Slicing by use case after seeing the data is exploratory.
- **`none` is under-powered for 5 points** at the default (one persona). Do not read a null placebo-versus-none result as "affiliation text does nothing."
- **Judge.** If a framing judge is added later, it has to stay blind and qualitative. A number that originated in the judge is not a result of this instrument.
- **Server.** Temperature 0 is not extra N. A digest-less `:latest` tag is not a replicate of a previous scan. KV cache of the system prompt is shared on purpose; conversation state is not. If a server rejects `seed` or `cache_prompt`, record that and do not silently drop it from the log.
- **Language and turn shape.** English, one shot, no tools. A drift result here does not speak to Chinese prompts or multi-turn sessions.
- **Recognition.** A model may notice the template. The placebo arm and the lexical audit are the checks we have, not a guarantee of blindness.

## Out of scope

Implanting a backdoor, evasive jailbreaks, and operational targeting of a real organisation are out of scope. The tasks are ordinary utilities. HOTP, HKDF, and zip-member screening are defensive exercises with public test vectors.
