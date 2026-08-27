"""full campaign: unique English grid × EN/ZH (154 with canaries)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tslit_dspy.lang_prompts import PREAMBLES, TASKS, pair_table
from tslit_dspy.probe_campaign import (
    _affiliation_preamble,
    assert_prompt_time_hygiene,
    build_campaign,
    unique_english_grid,
)

_CJK = frozenset(range(0x4E00, 0x9FFF + 1))
_WALL = datetime(2026, 8, 27, tzinfo=timezone.utc)


def _has_cjk(text: str) -> bool:
    return any(ord(ch) in _CJK for ch in text)


def test_unique_english_grid_is_70_plus_7_canaries() -> None:
    specs = unique_english_grid()
    assert len(specs) == 77
    assert len({s.probe_id for s in specs}) == 77
    assert sum(1 for s in specs if s.is_canary) == 7
    assert sum(1 for s in specs if not s.is_canary) == 70


def test_full_campaign_is_154() -> None:
    specs = build_campaign("full")
    assert len(specs) == 154
    ids = [s.probe_id for s in specs]
    assert len(ids) == len(set(ids))
    assert all(s.probe_id.endswith("__en") or s.probe_id.endswith("__zh") for s in specs)
    en = [s for s in specs if s.prompt_language == "en"]
    zh = [s for s in specs if s.prompt_language == "zh"]
    assert len(en) == 77
    assert len(zh) == 77
    assert sum(1 for s in specs if s.is_canary) == 14
    assert build_campaign("full", include_canaries=False) and len(
        build_campaign("full", include_canaries=False)
    ) == 140


def test_full_mirrors_english_keys_in_both_languages() -> None:
    english = unique_english_grid()
    full = build_campaign("full")
    en_keys = {
        (s.task_id, s.affiliation, s.probe_date, s.is_canary, s.is_baseline)
        for s in english
    }
    for lang in ("en", "zh"):
        got = {
            (s.task_id, s.affiliation, s.probe_date, s.is_canary, s.is_baseline)
            for s in full
            if s.prompt_language == lang
        }
        assert got == en_keys, lang


def test_full_twins_share_protocol_tokens() -> None:
    for task in TASKS:
        for tok in task["shared_tokens"]:
            assert tok in task["en"], (task["id"], tok)
            assert tok in task["zh"], (task["id"], tok)


def test_full_preambles_cover_the_english_grid() -> None:
    affs = {s.affiliation for s in unique_english_grid() if not s.is_canary}
    assert affs <= set(PREAMBLES)
    for aff in affs:
        assert PREAMBLES[aff]["en"] == _affiliation_preamble(aff), aff
        assert _has_cjk(PREAMBLES[aff]["zh"]), aff


def test_full_user_is_language_pure_and_dateless() -> None:
    for spec in build_campaign("full"):
        user = spec.messages[1]["content"]
        system = spec.messages[0]["content"]
        assert spec.probe_date not in user
        assert "VIRTUAL_CLOCK" not in user
        assert f"VIRTUAL_CLOCK_UTC={spec.probe_date}" in system
        if spec.prompt_language == "zh":
            assert _has_cjk(user)
        else:
            assert not _has_cjk(user)
        assert (
            assert_prompt_time_hygiene(
                spec.messages,
                probe_date=spec.probe_date,
                now=_WALL,
                probe_id=spec.probe_id,
            )
            == []
        )


def test_full_zh_does_not_use_identity_fallback() -> None:
    for spec in build_campaign("full"):
        if spec.prompt_language != "zh" or spec.is_canary:
            continue
        assert "我的身份是：" not in spec.messages[1]["content"]


def test_full_prompt_pairs_json_matches_code() -> None:
    path = Path("workspace/data/full_prompt_pairs.json")
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == pair_table()
