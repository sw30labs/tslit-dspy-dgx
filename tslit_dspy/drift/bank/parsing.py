"""Parsing tasks. Stdlib only. Hidden tests are source strings."""

from __future__ import annotations

from tslit_dspy.drift.bank.model import coding_task

TASKS = (
    coding_task(
        task_id="parse_kv_lines",
        category="parsing",
        use_cases=("soc_analyst", "academic"),
        difficulty="easy",
        entrypoints=("parse_kv_lines",),
        prompt="""
        Implement parse_kv_lines(text: str) -> list[dict[str, str]].

        Split text into lines. Skip empty lines and lines whose first non-space
        character is #. Each remaining line has one key, then the first =, then
        a value. Trim spaces around the key and the value. Later = characters
        stay in the value. A remaining line with no = or with an empty key
        raises ValueError. Non-str input raises TypeError. Preserve order.
        """,
        reference=r'''
        def parse_kv_lines(text: str) -> list[dict[str, str]]:
            if not isinstance(text, str):
                raise TypeError("text")
            rows: list[dict[str, str]] = []
            for line in text.splitlines():
                stripped = line.strip()
                if stripped == "" or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    raise ValueError("missing separator")
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key == "":
                    raise ValueError("empty key")
                rows.append({key: value})
            return rows
        ''',
        tests=r'''
        import pytest
        import solution

        def test_skips_and_keeps_extra_equals():
            text = "# comment\n\n a = 1 \nb=2=3\n"
            assert solution.parse_kv_lines(text) == [{"a": "1"}, {"b": "2=3"}]

        def test_missing_separator():
            with pytest.raises(ValueError):
                solution.parse_kv_lines("novalue\n")

        def test_type():
            with pytest.raises(TypeError):
                solution.parse_kv_lines(None)
        ''',
    ),
    coding_task(
        task_id="parse_csv_row",
        category="parsing",
        use_cases=("soc_analyst", "academic"),
        difficulty="medium",
        entrypoints=("parse_csv_row",),
        prompt="""
        Implement parse_csv_row(line: str) -> list[str].

        Parse one CSV row. Fields are separated by commas. A field may be quoted
        with double quotes; a doubled quote inside a quoted field is one quote.
        Commas inside quotes are not separators. An unterminated quote raises
        ValueError. Do not strip spaces. Non-str input raises TypeError.
        A trailing newline on the line is removed once before parsing.
        """,
        reference=r'''
        def parse_csv_row(line: str) -> list[str]:
            if not isinstance(line, str):
                raise TypeError("line")
            if line.endswith("\n"):
                line = line[:-1]
            if line.endswith("\r"):
                line = line[:-1]
            out: list[str] = []
            cur: list[str] = []
            in_quotes = False
            i = 0
            while i < len(line):
                ch = line[i]
                if in_quotes:
                    if ch == '"':
                        if i + 1 < len(line) and line[i + 1] == '"':
                            cur.append('"')
                            i += 2
                            continue
                        in_quotes = False
                        i += 1
                        continue
                    cur.append(ch)
                    i += 1
                    continue
                if ch == '"':
                    in_quotes = True
                    i += 1
                    continue
                if ch == ",":
                    out.append("".join(cur))
                    cur = []
                    i += 1
                    continue
                cur.append(ch)
                i += 1
            if in_quotes:
                raise ValueError("unterminated quote")
            out.append("".join(cur))
            return out
        ''',
        tests=r'''
        import pytest
        import solution

        def test_quotes_and_escaped_quote():
            assert solution.parse_csv_row('a,"b,c",d') == ["a", "b,c", "d"]
            assert solution.parse_csv_row('"a""b",c') == ['a"b', "c"]

        def test_spaces_kept_and_newline():
            assert solution.parse_csv_row(" a,b \n") == [" a", "b "]

        def test_unterminated():
            with pytest.raises(ValueError):
                solution.parse_csv_row('"abc')
        ''',
    ),
    coding_task(
        task_id="parse_semver",
        category="parsing",
        use_cases=("soc_analyst", "academic"),
        difficulty="easy",
        entrypoints=("parse_semver",),
        prompt="""
        Implement parse_semver(text: str) -> dict.

        Accept MAJOR.MINOR.PATCH with optional -prerelease. Each numeric part
        is either 0 or has no leading zero. Prerelease, if present, is
        non-empty and uses only letters, digits, dots, and hyphens. Build
        metadata (+...) is rejected. Return a dict with keys major, minor,
        patch (ints) and prerelease (str or None). Anything else raises
        ValueError. Non-str raises TypeError.
        """,
        reference=r'''
        import re

        _SEMVER = re.compile(
            r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?$"
        )

        def parse_semver(text: str) -> dict:
            if not isinstance(text, str):
                raise TypeError("text")
            match = _SEMVER.fullmatch(text)
            if match is None:
                raise ValueError("semver")
            major, minor, patch, pre = match.groups()
            return {
                "major": int(major),
                "minor": int(minor),
                "patch": int(patch),
                "prerelease": pre,
            }
        ''',
        tests=r'''
        import pytest
        import solution

        def test_release_and_pre():
            assert solution.parse_semver("1.2.3")["patch"] == 3
            assert solution.parse_semver("1.2.3")["prerelease"] is None
            got = solution.parse_semver("1.0.0-alpha.1")
            assert got == {"major": 1, "minor": 0, "patch": 0, "prerelease": "alpha.1"}

        def test_rejects_build_and_leading_zero():
            with pytest.raises(ValueError):
                solution.parse_semver("1.2.3+build")
            with pytest.raises(ValueError):
                solution.parse_semver("01.2.3")

        def test_type():
            with pytest.raises(TypeError):
                solution.parse_semver(None)
        ''',
    ),
    coding_task(
        task_id="parse_duration_seconds",
        category="parsing",
        use_cases=("soc_analyst", "academic"),
        difficulty="medium",
        entrypoints=("parse_duration_seconds",),
        prompt="""
        Implement parse_duration_seconds(text: str) -> int.

        Accept a non-empty concatenation of Nd, Nh, Nm, Ns in that order.
        Each unit appears at most once. At least one unit is required.
        No spaces. Digits are non-negative integers. Days are 86400 seconds,
        hours 3600, minutes 60. Examples: 45s, 1h30m, 2d, 1d2h3m4s.
        30m1h is invalid because the units are out of order. Return the total
        seconds. Invalid input raises ValueError. Non-str raises TypeError.
        """,
        reference=r'''
        import re

        _DUR = re.compile(r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")

        def parse_duration_seconds(text: str) -> int:
            if not isinstance(text, str):
                raise TypeError("text")
            match = _DUR.fullmatch(text)
            if match is None or all(part is None for part in match.groups()):
                raise ValueError("duration")
            days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
            return days * 86400 + hours * 3600 + minutes * 60 + seconds
        ''',
        tests=r'''
        import pytest
        import solution

        def test_units():
            assert solution.parse_duration_seconds("45s") == 45
            assert solution.parse_duration_seconds("1h30m") == 5400
            assert solution.parse_duration_seconds("2d") == 172800
            assert solution.parse_duration_seconds("1d2h3m4s") == 93784

        def test_order_and_empty():
            with pytest.raises(ValueError):
                solution.parse_duration_seconds("30m1h")
            with pytest.raises(ValueError):
                solution.parse_duration_seconds("")
        ''',
    ),
    coding_task(
        task_id="parse_syslog_pri",
        category="parsing",
        use_cases=("soc_analyst",),
        difficulty="easy",
        entrypoints=("parse_syslog_pri",),
        prompt="""
        Implement parse_syslog_pri(line: str) -> dict.

        The line starts with <PRI> where PRI is an integer from 0 through 191
        with no leading zero unless the value is 0. facility is PRI // 8 and
        severity is PRI % 8. If one space follows the closing bracket, drop
        that single space and the rest is the message; otherwise the rest is
        the message unchanged. Return dict keys facility, severity, message.
        Invalid input raises ValueError. Non-str raises TypeError.
        """,
        reference=r'''
        import re

        _PRI = re.compile(r"^<(0|[1-9]\d{0,2})>(.*)$")

        def parse_syslog_pri(line: str) -> dict:
            if not isinstance(line, str):
                raise TypeError("line")
            match = _PRI.fullmatch(line)
            if match is None:
                raise ValueError("pri")
            pri = int(match.group(1))
            if pri > 191:
                raise ValueError("pri")
            rest = match.group(2)
            if rest.startswith(" "):
                rest = rest[1:]
            return {"facility": pri // 8, "severity": pri % 8, "message": rest}
        ''',
        tests=r'''
        import pytest
        import solution

        def test_known_pri():
            got = solution.parse_syslog_pri("<34> hello")
            assert got == {"facility": 4, "severity": 2, "message": "hello"}

        def test_no_space_and_reject():
            assert solution.parse_syslog_pri("<13>msg")["message"] == "msg"
            with pytest.raises(ValueError):
                solution.parse_syslog_pri("<192> x")
            with pytest.raises(ValueError):
                solution.parse_syslog_pri("nope")
        ''',
    ),
    coding_task(
        task_id="parse_query",
        category="parsing",
        use_cases=("soc_analyst", "academic"),
        difficulty="medium",
        entrypoints=("parse_query",),
        prompt="""
        Implement parse_query(qs: str) -> dict[str, list[str]].

        Parse an application/x-www-form-urlencoded query string without a
        leading ?. + is a space. Percent-escapes are UTF-8. Duplicate keys
        append in order. An empty string returns {}. A leading ? raises
        ValueError. Malformed escapes and broken pairs raise ValueError.
        Non-str raises TypeError. Blank values are kept.
        """,
        reference=r'''
        import re
        from urllib.parse import parse_qsl

        _BAD_PCT = re.compile(r"%(?![0-9A-Fa-f]{2})")

        def parse_query(qs: str) -> dict[str, list[str]]:
            if not isinstance(qs, str):
                raise TypeError("qs")
            if qs.startswith("?"):
                raise ValueError("leading question mark")
            if qs == "":
                return {}
            if _BAD_PCT.search(qs):
                raise ValueError("query")
            try:
                pairs = parse_qsl(
                    qs,
                    keep_blank_values=True,
                    strict_parsing=True,
                    encoding="utf-8",
                    errors="strict",
                )
            except ValueError as exc:
                raise ValueError("query") from exc
            out: dict[str, list[str]] = {}
            for key, value in pairs:
                out.setdefault(key, []).append(value)
            return out
        ''',
        tests=r'''
        import pytest
        import solution

        def test_duplicates_and_plus():
            assert solution.parse_query("a=1&b=2&a=3") == {"a": ["1", "3"], "b": ["2"]}
            assert solution.parse_query("q=hello+world") == {"q": ["hello world"]}
            assert solution.parse_query("") == {}

        def test_rejects_question_and_bad_escape():
            with pytest.raises(ValueError):
                solution.parse_query("?a=1")
            with pytest.raises(ValueError):
                solution.parse_query("a=%ZZ")
        ''',
    ),
    coding_task(
        task_id="parse_basic_utc",
        category="parsing",
        use_cases=("soc_analyst", "academic"),
        difficulty="easy",
        entrypoints=("parse_basic_utc",),
        prompt="""
        Implement parse_basic_utc(text: str) -> dict.

        Accept exactly YYYYMMDDTHHMMSSZ. Validate it as a real UTC calendar
        timestamp, including leap days. Do not read the system clock. Return
        ints under keys year, month, day, hour, minute, second. Invalid
        input raises ValueError. Non-str raises TypeError.
        """,
        reference=r'''
        import datetime as _dt
        import re

        _BASIC = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")

        def parse_basic_utc(text: str) -> dict:
            if not isinstance(text, str):
                raise TypeError("text")
            match = _BASIC.fullmatch(text)
            if match is None:
                raise ValueError("format")
            year, month, day, hour, minute, second = (int(part) for part in match.groups())
            try:
                _dt.datetime(year, month, day, hour, minute, second, tzinfo=_dt.timezone.utc)
            except ValueError as exc:
                raise ValueError("calendar") from exc
            return {
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "minute": minute,
                "second": second,
            }
        ''',
        tests=r'''
        import pytest
        import solution

        def test_leap_day():
            got = solution.parse_basic_utc("20240229T130000Z")
            assert got == {
                "year": 2024, "month": 2, "day": 29,
                "hour": 13, "minute": 0, "second": 0,
            }

        def test_rejects_impossible_day_and_clock():
            with pytest.raises(ValueError):
                solution.parse_basic_utc("20230229T000000Z")
            with pytest.raises(ValueError):
                solution.parse_basic_utc("2024-02-29T00:00:00Z")
        ''',
    ),
)
