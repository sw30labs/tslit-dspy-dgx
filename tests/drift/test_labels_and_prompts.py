"""Label schema and matched-swap invariant."""

from __future__ import annotations

import re

from tslit_dspy.drift.bank import load_tasks
from tslit_dspy.drift.labels import STRATA, by_stratum, load_personas
from tslit_dspy.drift.prompts import load_prompts, normalize_slot, render_messages, render_system
from tslit_dspy.probe_campaign import ADVERSARIAL_AFFILIATIONS


def test_legacy_campaign_labels_are_untouched() -> None:
    # Historical probe list. The drift schema does not rewrite it.
    assert ADVERSARIAL_AFFILIATIONS[0] == "us-military"
    assert "chinese-government" not in ADVERSARIAL_AFFILIATIONS


def test_strata_and_required_fields() -> None:
    personas = load_personas()
    grouped = by_stratum()
    assert set(grouped) == set(STRATA)
    for stratum in ("adversary", "aligned", "neutral", "placebo"):
        assert len(grouped[stratum]) == 6
    assert len(grouped["none"]) == 1
    assert {p.model_origin for p in personas} == {"CN"}
    for stratum, rows in grouped.items():
        if stratum == "none":
            continue
        bands = {p.length_band for p in rows}
        assert bands == {"short", "medium", "long"}, stratum
    means = []
    for stratum in ("adversary", "aligned", "neutral", "placebo"):
        lens = [p.slot_chars for p in grouped[stratum]]
        means.append(sum(lens) / len(lens))
    assert max(means) - min(means) < 3


def test_matched_swap_invariant() -> None:
    skeleton = load_prompts()
    personas = [p for p in load_personas() if p.slot_text]
    none = next(p for p in load_personas() if p.stratum == "none")
    slots = [p.slot_text for p in personas]
    for task in load_tasks():
        for template in skeleton.templates:
            for position in skeleton.positions:
                renders = []
                for persona in personas:
                    messages = render_messages(
                        skeleton=skeleton,
                        task=task,
                        persona=persona,
                        template=template,
                        position=position,
                    )
                    assert messages[0]["content"] == render_system(skeleton, None)
                    renders.append(normalize_slot(messages[1]["content"], persona.slot_text))
                assert len(set(renders)) == 1
                bare = render_messages(
                    skeleton=skeleton,
                    task=task,
                    persona=none,
                    template=template,
                    position=position,
                )[1]["content"]
                for slot in slots:
                    assert slot not in bare
                    assert slot not in task.prompt


def test_prompts_do_not_contain_affiliation_spans() -> None:
    skeleton = load_prompts()
    spans = [span for p in load_personas() for span in p.redaction_spans]
    blob = "\n".join(
        [skeleton.system, skeleton.closing]
        + [t.sentence for t in skeleton.templates]
        + [task.prompt for task in load_tasks()]
    )
    for span in spans:
        assert re.search(rf"\b{re.escape(span)}\b", blob) is None, span


def test_virtual_clock_is_system_only_and_shared() -> None:
    skeleton = load_prompts()
    task = load_tasks()[0]
    personas = load_personas()[:2]
    systems = []
    for persona in personas:
        messages = render_messages(
            skeleton=skeleton,
            task=task,
            persona=persona,
            template=skeleton.templates[0],
            position="prefix",
            virtual_clock="2024-01-15",
        )
        systems.append(messages[0]["content"])
        assert "2024-01-15" not in messages[1]["content"]
        assert "VIRTUAL_CLOCK_UTC=2024-01-15" in messages[0]["content"]
    assert systems[0] == systems[1]
