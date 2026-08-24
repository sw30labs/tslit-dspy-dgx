# LinkedIn post — TSLIT-DSPy on DGX Spark (Ollama + campaign update)

Copy everything between the horizontal rules into LinkedIn.

Voice note: TwinOps MCP is **not** on this DGX Spark (only Grok `tasks`).
Style here follows your last TSLIT LinkedIn draft + the TwinOps *fallback*
profile from `code humanizer` (builder/operator, no marketing cadence,
parenthetical caveats, hypotheses not certificates). Re-pull
`post-style-summary` on the Mac/grokbot if you want a live TwinOps pass.

---

The question is no longer only “which model is best?”
It’s “which model is best **and** intact enough to deploy?”

Open weights keep multiplying the **download-and-deploy** surface. Capability and **integrity risk** arrive together. I want the **assurance side** to keep up — on hardware you can actually afford to run hard loops on.

**TSLIT-DSPy** is time-shift LLM integrity testing: same technical ask, different **who** and **when**, then a compiled detector for affiliation bias, temporal logic bombs, and combined threats.

Research: https://github.com/sw30labs/tslit-dspy-ar

I’ve **simplified the NVIDIA DGX Spark port**.

The shared **vLLM** layer is gone. One local server now: **Ollama on :11434**. Detector and scan target are different tags on the same process. Detection brain: non-adversary / American models only (Meta Muse Glimmer on this box). Adversary-origin open weights stay **scan targets**, never the analyzer. That’s **enforced in code**, not a README wish.

I also **grew the live campaign** — without replaying labeled training responses (those are detector homework, some with planted bombs):

- **mini** — 14-probe controlled grid (first live run)
- **plus** — leftover whitepaper cells: extra **US / allied / adversary-origin** requester identities, extra trigger dates, and tasks recovered from the original baselines
- **sharp** — clock-native asks (cert expiry, feature flags, JWT time checks, lab FFT) on a 2×2 of **US vs adversary-origin identity** × **neutral vs symbolic trigger dates**. Generic scanners never forced the model to write against *today*, so a date gate had nowhere honest to hide.

Same Ollama. `./tslit test-campaign`, then plus, then sharp. Analyze loads the combined folder. Hypotheses, **not** certificates.

Trust isn’t a property of origin. **It’s a property of verifiability.**

#AISecurity #ModelRisk #OpenSource #LLM #TrustworthyAI #NVIDIADGX #DGXSpark #Ollama

---

## Optional first comment

> Research (public): https://github.com/sw30labs/tslit-dspy-ar
> DGX Spark port: `tslit-dspy-dgx` — Ollama only (`:11434`). Detector: Muse Glimmer. Targets: adversary-origin open weights under test.
> `./tslit install` → `./tslit doctor` → `./tslit test-campaign` → `./tslit test-campaign-plus` → `./tslit test-campaign-sharp`
> Policy: American / non-adversary models only in the detection stack. Draft paper still lives in the research repo.

## Notes before posting

| Item | Suggestion |
|------|------------|
| TwinOps | Not reachable from Spark; re-check style on Mac if you want a live `post-style-summary` pass |
| DGX repo URL | Link public GitHub only if `tslit-dspy-dgx` is public |
| Named states | Public copy uses US / allied / adversary-origin — not specific governments |
| Claims | Do not imply certification from a live scan |
