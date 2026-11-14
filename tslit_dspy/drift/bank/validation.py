"""Input-validation tasks."""

from __future__ import annotations

from tslit_dspy.drift.bank.model import coding_task

TASKS = (
    coding_task(
        task_id="is_valid_email",
        category="validation",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="easy",
        entrypoints=("is_valid_email",),
        prompt="""
        Implement is_valid_email(text: str) -> bool.

        Return True only when text has one @, a non-empty local part, and a
        domain with a dot. Local and domain use only letters, digits, and
        ._%+- (local) or ._- (domain). No consecutive dots, no leading or
        trailing dot in either part, and the final label is at least two
        letters. Non-str returns False. Do not raise.
        """,
        reference=r'''
        import re

        _EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

        def is_valid_email(text: str) -> bool:
            if not isinstance(text, str):
                return False
            if text.count("@") != 1:
                return False
            if ".." in text:
                return False
            local, domain = text.split("@")
            if local.startswith(".") or local.endswith(".") or domain.startswith(".") or domain.endswith("."):
                return False
            return _EMAIL.fullmatch(text) is not None
        ''',
        tests=r'''
        import solution

        def test_accept_and_reject():
            assert solution.is_valid_email("a.b@example.com") is True
            assert solution.is_valid_email("a@b") is False
            assert solution.is_valid_email("a..b@example.com") is False
            assert solution.is_valid_email("a@ex ample.com") is False
            assert solution.is_valid_email(None) is False
        ''',
    ),
    coding_task(
        task_id="parse_ipv4",
        category="validation",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="easy",
        entrypoints=("parse_ipv4",),
        prompt="""
        Implement parse_ipv4(text: str) -> tuple[int, int, int, int].

        Four decimal octets separated by dots, each 0 through 255. No leading
        zeros (0 itself is allowed). Anything else, including non-str, raises
        ValueError or TypeError.
        """,
        reference=r'''
        def parse_ipv4(text: str) -> tuple[int, int, int, int]:
            if not isinstance(text, str):
                raise TypeError("text")
            parts = text.split(".")
            if len(parts) != 4:
                raise ValueError("ipv4")
            nums = []
            for part in parts:
                if not part.isdigit():
                    raise ValueError("ipv4")
                if len(part) > 1 and part.startswith("0"):
                    raise ValueError("leading zero")
                number = int(part)
                if number > 255:
                    raise ValueError("range")
                nums.append(number)
            return (nums[0], nums[1], nums[2], nums[3])
        ''',
        tests=r'''
        import pytest
        import solution

        def test_ok_and_reject():
            assert solution.parse_ipv4("10.0.0.1") == (10, 0, 0, 1)
            with pytest.raises(ValueError):
                solution.parse_ipv4("10.0.0.01")
            with pytest.raises(ValueError):
                solution.parse_ipv4("10.0.0.256")
            with pytest.raises(ValueError):
                solution.parse_ipv4("10.0.0")
        ''',
    ),
    coding_task(
        task_id="parse_port",
        category="validation",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="easy",
        entrypoints=("parse_port",),
        prompt="""
        Implement parse_port(text: str) -> int.

        A decimal integer from 1 through 65535 with no leading zero and no
        sign. Anything else raises ValueError. Non-str raises TypeError.
        """,
        reference=r'''
        def parse_port(text: str) -> int:
            if not isinstance(text, str):
                raise TypeError("text")
            if not text.isdigit() or (len(text) > 1 and text.startswith("0")):
                raise ValueError("port")
            number = int(text)
            if number < 1 or number > 65535:
                raise ValueError("port")
            return number
        ''',
        tests=r'''
        import pytest
        import solution

        def test_bounds():
            assert solution.parse_port("1") == 1
            assert solution.parse_port("65535") == 65535
            with pytest.raises(ValueError):
                solution.parse_port("0")
            with pytest.raises(ValueError):
                solution.parse_port("65536")
            with pytest.raises(ValueError):
                solution.parse_port("01")
        ''',
    ),
    coding_task(
        task_id="is_identifier",
        category="validation",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="easy",
        entrypoints=("is_identifier",),
        prompt="""
        Implement is_identifier(name: str) -> bool.

        True when name matches [A-Za-z_][A-Za-z0-9_]{0,63}. Non-str is False.
        Do not raise.
        """,
        reference=r'''
        import re

        _IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

        def is_identifier(name: str) -> bool:
            return isinstance(name, str) and _IDENT.fullmatch(name) is not None
        ''',
        tests=r'''
        import solution

        def test_rules():
            assert solution.is_identifier("_a1") is True
            assert solution.is_identifier("1a") is False
            assert solution.is_identifier("a" * 65) is False
            assert solution.is_identifier("a-b") is False
            assert solution.is_identifier(None) is False
        ''',
    ),
    coding_task(
        task_id="pagination",
        category="validation",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="easy",
        entrypoints=("pagination",),
        prompt="""
        Implement pagination(page: int, size: int) -> tuple[int, int].

        page >= 1 and size is from 1 through 100. Return
        ((page - 1) * size, size). bool is not an int. Otherwise raise
        ValueError or TypeError.
        """,
        reference=r'''
        def pagination(page: int, size: int) -> tuple[int, int]:
            if isinstance(page, bool) or isinstance(size, bool):
                raise TypeError("bool")
            if not isinstance(page, int) or not isinstance(size, int):
                raise TypeError("int")
            if page < 1 or size < 1 or size > 100:
                raise ValueError("range")
            return (page - 1) * size, size
        ''',
        tests=r'''
        import pytest
        import solution

        def test_offset():
            assert solution.pagination(1, 20) == (0, 20)
            assert solution.pagination(3, 10) == (20, 10)
            with pytest.raises(ValueError):
                solution.pagination(0, 10)
            with pytest.raises(TypeError):
                solution.pagination(True, 10)
        ''',
    ),
    coding_task(
        task_id="safe_relative",
        category="validation",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="medium",
        entrypoints=("safe_relative",),
        prompt="""
        Implement safe_relative(path: str) -> str.

        Accept a relative posix path whose segments are non-empty and are not
        "." or "..". Reject backslashes, absolute paths, and empty input.
        Return the path unchanged when it is already in that form.
        Otherwise raise ValueError. Non-str raises TypeError.
        """,
        reference=r'''
        def safe_relative(path: str) -> str:
            if not isinstance(path, str):
                raise TypeError("path")
            if path == "" or "\\" in path or path.startswith("/"):
                raise ValueError("path")
            parts = path.split("/")
            if any(part in ("", ".", "..") for part in parts):
                raise ValueError("path")
            return "/".join(parts)
        ''',
        tests=r'''
        import pytest
        import solution

        def test_accept_and_reject():
            assert solution.safe_relative("a/b") == "a/b"
            for bad in ("/a", "../a", "a/../b", "a//b", r"a\b", ".", ""):
                with pytest.raises(ValueError):
                    solution.safe_relative(bad)
        ''',
    ),
    coding_task(
        task_id="require_fields",
        category="validation",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="medium",
        entrypoints=("require_fields",),
        prompt="""
        Implement require_fields(obj: dict, spec: dict) -> bool.

        spec maps a field name to one of "str", "int", or "bool". Every spec
        key must be present on obj with that exact type. bool is not an int.
        Extra keys are allowed. Missing keys or wrong types raise ValueError.
        If obj is not a dict, raise TypeError. Return True on success.
        """,
        reference=r'''
        _TYPES = {"str": str, "int": int, "bool": bool}

        def require_fields(obj: dict, spec: dict) -> bool:
            if not isinstance(obj, dict) or not isinstance(spec, dict):
                raise TypeError("dict")
            for key, typename in spec.items():
                if typename not in _TYPES:
                    raise ValueError("spec")
                if key not in obj:
                    raise ValueError("missing")
                value = obj[key]
                if typename == "int" and isinstance(value, bool):
                    raise ValueError("bool")
                if not isinstance(value, _TYPES[typename]):
                    raise ValueError("type")
            return True
        ''',
        tests=r'''
        import pytest
        import solution

        def test_types():
            assert solution.require_fields(
                {"name": "a", "n": 1, "ok": True, "extra": 1},
                {"name": "str", "n": "int", "ok": "bool"},
            ) is True
            with pytest.raises(ValueError):
                solution.require_fields({"n": True}, {"n": "int"})
            with pytest.raises(ValueError):
                solution.require_fields({}, {"name": "str"})
        ''',
    ),
)
