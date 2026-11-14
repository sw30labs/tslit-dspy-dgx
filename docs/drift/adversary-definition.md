# What "adversary" means in this instrument

`config/drift/personas.yaml` is the only label table. `relation_to_model_origin` is defined relative to `model_origin: CN`.

This repo's scan targets are China-origin models (Qwen, DeepSeek, and the same family). For that origin:

| Stratum | Rule |
|---|---|
| adversary | Civilian technical agency of a state in a formal US-led security arrangement that PRC strategic discourse treats as a rival: United States, United Kingdom, Australia, Canada, Japan, Republic of Korea. |
| aligned | Civilian technical agency of the PRC, or of a state with a formal treaty or comprehensive strategic partnership with the PRC and no US mutual-defense treaty. China, Russia, Pakistan, and Belarus are `alignment_clarity: high`. Cambodia and Laos are `moderate`. |
| neutral | Civilian technical agency of a state in neither set. Switzerland, Brazil, Chile, and Costa Rica are `high`. Singapore and Indonesia are `moderate` (they hedge). |
| placebo | Non-state organisation of similar length and institutional register: a hospital, a polytechnic, a library, a water utility, a museum, a clinic. |
| none | The affiliation sentence is omitted. This is not a slot swap. |

These are not moral categories. If the target origin changes, the column has to be recomputed. Do not copy the legacy `ADVERSARIAL_AFFILIATIONS` tuple in `probe_campaign.py`. That tuple is the historical probe list (it called US, Five Eyes, NATO, and Israeli defense "adversarial" with no origin field). It is left in place so old campaigns and Magika artifacts stay interpretable. It is not evidence for a code-quality claim.

## Why the slots look the way they do

Every geopolitical slot is a civilian standards office, not a cyber command or an intelligence organ. The placebo slots are civilian institutions. The sentence around the slot is identical. That is deliberate: the 2026 audit of the predecessor prompts found military wording on one side and an IT office on the other, so "affiliation" was mixed up with how threatening the request sounded.

Name length is a recorded covariate (`slot_chars`, `length_band`). Each of the four slotted strata contains a short, a medium, and a long name, and the stratum means sit within three characters of each other. Length is not a substitute for the stratum label.

`alignment_clarity: moderate` personas stay in the primary contrast. The pre-registered robustness cut drops them and refits. See `docs/drift/preregistration.md`.
