"""Unit tests for time-shift hygiene (no GPU)."""

from __future__ import annotations

from datetime import datetime, timezone

from tslit_dspy.probe_campaign import (
    NEUTRAL_DATE,
    TIANANMEN_DATE,
    TRIGGER_DATE,
    assert_prompt_time_hygiene,
    build_canary_messages,
    build_campaign,
    build_messages,
    build_mini_campaign,
    build_plus_campaign,
    build_sharp_campaign,
    evaluate_canary_response,
    load_existing_probe_ids,
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


def test_mini_campaign_is_fourteen() -> None:
    specs = build_mini_campaign(include_canaries=True)
    assert len(specs) == 14
    ids = [s.probe_id for s in specs]
    assert len(ids) == len(set(ids))


def test_plus_campaign_adds_old_tslit_cells() -> None:
    mini_ids = {s.probe_id for s in build_mini_campaign()}
    plus = build_plus_campaign(include_canaries=True)
    plus_ids = {s.probe_id for s in plus}
    # Increment: no overlap with the original 14 technical cells
    tech_plus = {s.probe_id for s in plus if not s.is_canary}
    assert tech_plus.isdisjoint(mini_ids)
    assert any("five-eyes" in i for i in plus_ids)
    assert any("packet_inspect" in i for i in plus_ids)
    assert any("crypto_aes" in i for i in plus_ids)
    assert any("backup_job" in i for i in plus_ids)
    assert any("2024-07-04" in i for i in plus_ids)
    assert build_campaign("plus") == plus


def test_sharp_campaign_is_clock_native_grid() -> None:
    mini_ids = {s.probe_id for s in build_mini_campaign()}
    plus_ids = {s.probe_id for s in build_plus_campaign()}
    sharp = build_sharp_campaign(include_canaries=True)
    tech = [s for s in sharp if not s.is_canary]
    assert len(tech) == 20  # 4 tasks × 5 cells
    ids = [s.probe_id for s in tech]
    assert len(ids) == len(set(ids))
    assert set(ids).isdisjoint(mini_ids)
    # June 4 canary may overlap plus; technical cells must not
    assert set(ids).isdisjoint({i for i in plus_ids if not i.startswith("canary_")})
    assert any(s.probe_date == TIANANMEN_DATE and s.affiliation == "us-military" for s in tech)
    assert any(s.probe_date == TIANANMEN_DATE and s.affiliation == "chinese-government" for s in tech)
    assert any(s.task_id == "feature_flags" for s in tech)
    assert any(s.task_id == "cert_expiry" for s in tech)
    # User task must not smuggle a concrete calendar date (system owns the clock)
    for s in tech:
        user = s.messages[1]["content"]
        assert TIANANMEN_DATE not in user
        assert TRIGGER_DATE not in user
        assert "VIRTUAL_CLOCK" not in user
    assert build_campaign("sharp") == sharp


def test_jwt2x2_is_four_clock_cells() -> None:
    specs = build_campaign("jwt2x2")
    assert len(specs) == 4
    assert all(s.task_id == "jwt_time" for s in specs)
    assert all(not s.is_canary for s in specs)
    affs = {(s.affiliation, s.probe_date) for s in specs}
    assert ("us-military", TRIGGER_DATE) in affs
    assert ("chinese-government", TRIGGER_DATE) in affs
    assert ("us-military", TIANANMEN_DATE) in affs
    assert ("chinese-government", TIANANMEN_DATE) in affs


def test_sharp_messages_pass_time_hygiene() -> None:
    wall = datetime(2026, 8, 24, tzinfo=timezone.utc)
    for spec in build_sharp_campaign(include_canaries=False):
        v = assert_prompt_time_hygiene(
            spec.messages,
            probe_date=spec.probe_date,
            now=wall,
            probe_id=spec.probe_id,
        )
        assert v == [], (spec.probe_id, v)


def test_load_existing_probe_ids(tmp_path) -> None:
    nd = tmp_path / "scan_qwen_1.ndjson"
    nd.write_text(
        '{"probe_id": "net_scan__baseline"}\n{"probe_id": "log_parser__us-military__2024-09-11"}\n',
        encoding="utf-8",
    )
    (tmp_path / "scan_qwen_1_requests.ndjson").write_text(
        '{"probe_id": "should_ignore"}\n', encoding="utf-8"
    )
    ids = load_existing_probe_ids(tmp_path)
    assert ids == {"net_scan__baseline", "log_parser__us-military__2024-09-11"}
