"""EN/ZH meaning-matched prompt twins (no GPU)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tslit_dspy.lang_prompts import TASKS, pair_table
from tslit_dspy.pairwise import apply_triage
from tslit_dspy.probe_campaign import (
    TRIGGER_DATE,
    assert_prompt_time_hygiene,
    build_campaign,
)

_CJK = frozenset(range(0x4E00, 0x9FFF + 1))


def _has_cjk(text: str) -> bool:
    return any(ord(ch) in _CJK for ch in text)


def test_lang2x2_is_eight_paired_cells() -> None:
    specs = build_campaign("lang2x2")
    assert len(specs) == 8
    ids = [s.probe_id for s in specs]
    assert len(ids) == len(set(ids))
    assert all(s.probe_id.endswith("__en") or s.probe_id.endswith("__zh") for s in specs)
    keys = {(s.task_id, s.affiliation, s.probe_date, s.prompt_language) for s in specs}
    assert len(keys) == 8
    for task in ("jwt_time", "cert_expiry"):
        for aff in ("us-military", "chinese-government"):
            assert (task, aff, TRIGGER_DATE, "en") in keys
            assert (task, aff, TRIGGER_DATE, "zh") in keys


def test_lang2x2_twins_share_protocol_tokens() -> None:
    for task in TASKS:
        for tok in task["shared_tokens"]:
            assert tok in task["en"], tok
            assert tok in task["zh"], tok


def test_lang2x2_user_is_language_pure_and_dateless() -> None:
    wall = datetime(2026, 8, 27, tzinfo=timezone.utc)
    for spec in build_campaign("lang2x2"):
        user = spec.messages[1]["content"]
        system = spec.messages[0]["content"]
        assert TRIGGER_DATE not in user
        assert "VIRTUAL_CLOCK" not in user
        assert f"VIRTUAL_CLOCK_UTC={TRIGGER_DATE}" in system
        if spec.prompt_language == "zh":
            assert _has_cjk(user)
        else:
            assert not _has_cjk(user)
        v = assert_prompt_time_hygiene(
            spec.messages,
            probe_date=spec.probe_date,
            now=wall,
            probe_id=spec.probe_id,
        )
        assert v == []


def test_zh_identity_exists_for_us_and_cn() -> None:
    specs = [s for s in build_campaign("lang2x2") if s.prompt_language == "zh"]
    affs = {s.affiliation for s in specs}
    assert affs == {"us-military", "chinese-government"}


def test_identity_pairs_do_not_cross_language() -> None:
    recs = [
        {
            "probe_id": "jwt_time__us-military__2024-09-11__en",
            "task_id": "jwt_time",
            "affiliation": "us-military",
            "probe_date": "2024-09-11",
            "prompt_language": "en",
            "response_text": "x",
            "detector_flags": [],
        },
        {
            "probe_id": "jwt_time__chinese-government__2024-09-11__zh",
            "task_id": "jwt_time",
            "affiliation": "chinese-government",
            "probe_date": "2024-09-11",
            "prompt_language": "zh",
            "response_text": "y" * 8000,
            "detector_flags": [],
        },
    ]
    apply_triage(recs)
    # Different language: not an identity pair. Truncation without sibling is skip.
    assert recs[0]["triage"] == "skip"
    assert recs[1]["triage"] == "skip"


def test_same_language_still_pairs_identity() -> None:
    recs = [
        {
            "probe_id": "jwt_time__us-military__2024-09-11__zh",
            "task_id": "jwt_time",
            "affiliation": "us-military",
            "probe_date": "2024-09-11",
            "prompt_language": "zh",
            "response_text": "and",
            "detector_flags": [],
        },
        {
            "probe_id": "jwt_time__chinese-government__2024-09-11__zh",
            "task_id": "jwt_time",
            "affiliation": "chinese-government",
            "probe_date": "2024-09-11",
            "prompt_language": "zh",
            "response_text": "def main():\n    import datetime\n" + "ok\n" * 2000,
            "detector_flags": [],
        },
    ]
    apply_triage(recs)
    assert recs[0]["triage"] == "muse"
    assert recs[1]["triage"] == "muse"
    assert recs[0]["sibling_id"] == recs[1]["probe_id"]


def test_pair_table_covers_tasks_and_preambles() -> None:
    rows = pair_table()
    kinds = {r["kind"] for r in rows}
    assert {"task", "preamble", "close", "system"} <= kinds
    assert {r["id"] for r in rows if r["kind"] == "task"} == {"jwt_time", "cert_expiry"}


def test_prompt_pairs_json_matches_code() -> None:
    path = Path("workspace/data/lang2x2_prompt_pairs.json")
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == pair_table()
