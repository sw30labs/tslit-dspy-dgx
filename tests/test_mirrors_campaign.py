"""Mirrors campaign: identical tasks, separate from the English 70/70 grid."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from tslit_dspy.probe_campaign import (
    MIRROR_TASKS,
    MIRROR_TRIGGER_DATES,
    NEUTRAL_DATE,
    assert_prompt_time_hygiene,
    build_campaign,
    build_full_campaign,
    build_mirrors_campaign,
    unique_english_grid,
)

_ISO = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
_SIDE_WORDS = (
    "lockheed",
    "norinco",
    "secret service",
    "pla",
    "aukus",
    "philippine",
    "nsa",
    "ministry of state security",
    "centcom",
    "taiwan",
    "iranian",
)


def test_mirrors_is_111_and_not_in_the_english_grid() -> None:
    specs = build_mirrors_campaign(include_canaries=True)
    assert len(specs) == 111
    assert build_campaign("mirrors") == specs
    ids = [s.probe_id for s in specs]
    assert len(ids) == len(set(ids))

    tech = [s for s in specs if not s.is_canary]
    assert len(tech) == 6 * (1 + 2 * len(MIRROR_TRIGGER_DATES))
    english_ids = {s.probe_id for s in unique_english_grid()}
    full_ids = {s.probe_id for s in build_full_campaign()}
    assert {s.probe_id for s in tech}.isdisjoint(english_ids)
    assert {s.probe_id for s in tech}.isdisjoint(full_ids)
    assert not any(s.task_id == "log_anomaly" for s in unique_english_grid())


def test_task_text_is_identical_and_dateless() -> None:
    specs = build_mirrors_campaign(include_canaries=False)
    by_task: dict[str, list] = {}
    for spec in specs:
        by_task.setdefault(spec.task_id, []).append(spec)
    assert set(by_task) == {t["id"] for t in MIRROR_TASKS}
    for task in MIRROR_TASKS:
        body = task["user_task"]
        assert _ISO.search(body) is None
        lowered = body.lower()
        assert not any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in _SIDE_WORDS)
        cells = by_task[task["id"]]
        users = [s.messages[1]["content"] for s in cells]
        assert all(body in user for user in users)
        # Preamble changes with identity; the technical sentence does not.
        assert len({user for user in users}) > 1


def test_both_identities_share_every_trigger_date() -> None:
    specs = build_mirrors_campaign(include_canaries=False)
    for task in MIRROR_TASKS:
        cells = [s for s in specs if s.task_id == task["id"]]
        baseline = [s for s in cells if s.is_baseline]
        assert len(baseline) == 1
        assert baseline[0].affiliation == "neutral-corporate"
        assert baseline[0].probe_date == NEUTRAL_DATE
        for probe_date in MIRROR_TRIGGER_DATES:
            affs = {s.affiliation for s in cells if s.probe_date == probe_date}
            assert affs == {"us-military", "chinese-government"}


def test_mirrors_messages_pass_time_hygiene() -> None:
    wall = datetime(2026, 11, 19, tzinfo=timezone.utc)
    for spec in build_mirrors_campaign(include_canaries=True):
        violations = assert_prompt_time_hygiene(
            spec.messages,
            probe_date=spec.probe_date,
            now=wall,
            probe_id=spec.probe_id,
        )
        assert violations == [], (spec.probe_id, violations)
        if not spec.is_canary:
            user = spec.messages[1]["content"]
            assert "VIRTUAL_CLOCK" not in user
            assert spec.probe_date not in user
