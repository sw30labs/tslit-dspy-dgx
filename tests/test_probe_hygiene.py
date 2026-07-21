"""Unit tests for time-shift hygiene (no GPU)."""

from __future__ import annotations

from datetime import datetime, timezone

from tslit_dspy.probe_campaign import (
    NEUTRAL_DATE,
    TRIGGER_DATE,
    assert_prompt_time_hygiene,
    build_canary_messages,
    build_messages,
    build_mini_campaign,
    evaluate_canary_response,
)


def test_system_message_owns_virtual_clock() -> None:
    msgs = build_messages(
        probe_date=TRIGGER_DATE,
        affiliation="us-military",
        task="Write hello world",
    )
    assert msgs[0]["role"] == "system"
    assert TRIGGER_DATE in msgs[0]["content"]
    assert "VIRTUAL_CLOCK_UTC=" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    # User message must not carry the virtual clock (system owns it)
    assert "VIRTUAL_CLOCK_UTC=" not in msgs[1]["content"]
    assert TRIGGER_DATE not in msgs[1]["content"]


def test_hygiene_passes_for_clean_messages() -> None:
    wall = datetime(2026, 7, 21, tzinfo=timezone.utc)
    msgs = build_messages(
        probe_date=NEUTRAL_DATE,
        affiliation="neutral-corporate",
        task="Write a parser",
    )
    v = assert_prompt_time_hygiene(msgs, probe_date=NEUTRAL_DATE, now=wall)
    assert v == []


def test_hygiene_flags_real_iso_in_user() -> None:
    wall = datetime(2026, 7, 21, tzinfo=timezone.utc)
    msgs = [
        {"role": "system", "content": f"VIRTUAL_CLOCK_UTC={NEUTRAL_DATE}\n{NEUTRAL_DATE}"},
        {"role": "user", "content": "Today is really 2026-07-21 in the lab."},
    ]
    v = assert_prompt_time_hygiene(msgs, probe_date=NEUTRAL_DATE, now=wall)
    assert any("2026-07-21" in x for x in v)


def test_canary_detects_real_leak() -> None:
    wall = datetime(2026, 7, 21, tzinfo=timezone.utc)
    r = evaluate_canary_response("2026-07-21", probe_date=TRIGGER_DATE, now=wall)
    assert r["status"] == "REAL_CALENDAR_LEAK"
    assert "canary:real_calendar_leak" in r["flags"]


def test_canary_accepts_virtual() -> None:
    wall = datetime(2026, 7, 21, tzinfo=timezone.utc)
    r = evaluate_canary_response(TRIGGER_DATE, probe_date=TRIGGER_DATE, now=wall)
    assert r["status"] == "virtual_ok"


def test_campaign_includes_canaries_first() -> None:
    specs = build_mini_campaign(include_canaries=True)
    assert specs[0].is_canary
    assert specs[1].is_canary
    assert any(not s.is_canary for s in specs)
    # canary messages are system+user only
    assert [m["role"] for m in build_canary_messages(TRIGGER_DATE)] == [
        "system",
        "user",
    ]
