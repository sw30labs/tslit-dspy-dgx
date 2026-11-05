# ADR-0008: Fixed campaign catalogue (mini, plus, sharp, jwt2x2, lang2x2, full)

## Status

Accepted (retrospective, inferred 2026-11-05)

## Context

Probes must hold the technical ask constant and vary only identity and date (and, later, language).

## Decision

Campaigns are code-defined: mini (14), plus (43), sharp (20, clock-native tasks x US/CN x 9/11 / Jun 4), jwt2x2 (4), lang2x2 (8, EN/ZH x US/CN on 9/11), full (154 = unique English grid of 70 + 7 canaries x EN/ZH). `--skip-existing` increments a folder; full uses `__en`/`__zh` ids in its own tree. Language is an independent variable; EN and ZH are quoted as separate tables.

## Consequences

+ Counts are unit-tested (`tests/test_full_campaign.py`, `tests/test_lang2x2.py`).
+ Meaning-matched twins in `lang_prompts.py` keep shared tokens in Latin script.
- Adding a campaign means editing code. Full campaign was "not probed" as of PAPER.md v1.1.

## Alternatives considered

Free-form prompt generation (not chosen).

## Evidence

`tslit_dspy/probe_campaign.py`; `tslit_dspy/lang_prompts.py`; README.md campaign table; docs/PAPER.md; commits 078fbaf, b9a2a5c.

Reviewed at commit `862b002`.
