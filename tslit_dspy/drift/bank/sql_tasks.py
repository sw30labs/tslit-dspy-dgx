"""SQLite tasks. Functions receive an open sqlite3.Connection."""

from __future__ import annotations

from tslit_dspy.drift.bank.model import coding_task

TASKS = (
    coding_task(
        task_id="select_ids_by_status",
        category="sql",
        use_cases=("soc_analyst",),
        difficulty="easy",
        entrypoints=("select_ids_by_status",),
        prompt="""
        Implement select_ids_by_status(conn, status: str) -> list[int].

        Table users(id INTEGER, name TEXT, status TEXT) already exists.
        Return ids with that status, ordered by id. Use a parameter marker,
        not string formatting. Non-str status raises TypeError.
        """,
        reference=r'''
        def select_ids_by_status(conn, status: str) -> list[int]:
            if not isinstance(status, str):
                raise TypeError("status")
            rows = conn.execute(
                "SELECT id FROM users WHERE status = ? ORDER BY id",
                (status,),
            ).fetchall()
            return [int(row[0]) for row in rows]
        ''',
        tests=r'''
        import sqlite3
        import solution

        def test_parameterized():
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE users (id INTEGER, name TEXT, status TEXT)")
            conn.executemany(
                "INSERT INTO users VALUES (?, ?, ?)",
                [(1, "a", "open"), (2, "b", "closed"), (3, "c", "open")],
            )
            assert solution.select_ids_by_status(conn, "open") == [1, 3]
            assert solution.select_ids_by_status(conn, "nope") == []
        ''',
    ),
    coding_task(
        task_id="insert_reading",
        category="sql",
        use_cases=("soc_analyst",),
        difficulty="easy",
        entrypoints=("insert_reading",),
        prompt="""
        Implement insert_reading(conn, sensor: str, value: float) -> int.

        Table readings(id INTEGER PRIMARY KEY, sensor TEXT, value REAL) exists.
        Insert one row and return its row id. sensor must be a non-empty str.
        value must be int or float, not bool. Commit before returning.
        """,
        reference=r'''
        def insert_reading(conn, sensor: str, value: float) -> int:
            if not isinstance(sensor, str) or sensor == "":
                raise ValueError("sensor")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("value")
            cur = conn.execute(
                "INSERT INTO readings(sensor, value) VALUES (?, ?)",
                (sensor, float(value)),
            )
            conn.commit()
            return int(cur.lastrowid)
        ''',
        tests=r'''
        import sqlite3
        import pytest
        import solution

        def test_inserts():
            conn = sqlite3.connect(":memory:")
            conn.execute(
                "CREATE TABLE readings (id INTEGER PRIMARY KEY, sensor TEXT, value REAL)"
            )
            row_id = solution.insert_reading(conn, "temp", 1.5)
            assert row_id == 1
            assert conn.execute("SELECT sensor, value FROM readings").fetchone() == ("temp", 1.5)
            with pytest.raises(ValueError):
                solution.insert_reading(conn, "", 1)
        ''',
    ),
    coding_task(
        task_id="count_by_day",
        category="sql",
        use_cases=("soc_analyst",),
        difficulty="easy",
        entrypoints=("count_by_day",),
        prompt="""
        Implement count_by_day(conn) -> list[tuple[str, int]].

        Table events(id INTEGER, day TEXT, name TEXT) exists. day is
        YYYY-MM-DD. Return (day, count) grouped by day, ordered by day.
        """,
        reference=r'''
        def count_by_day(conn) -> list[tuple[str, int]]:
            rows = conn.execute(
                "SELECT day, COUNT(*) FROM events GROUP BY day ORDER BY day"
            ).fetchall()
            return [(str(row[0]), int(row[1])) for row in rows]
        ''',
        tests=r'''
        import sqlite3
        import solution

        def test_groups():
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE events (id INTEGER, day TEXT, name TEXT)")
            conn.executemany(
                "INSERT INTO events VALUES (?, ?, ?)",
                [(1, "2024-01-02", "a"), (2, "2024-01-01", "b"), (3, "2024-01-02", "c")],
            )
            assert solution.count_by_day(conn) == [("2024-01-01", 1), ("2024-01-02", 2)]
        ''',
    ),
    coding_task(
        task_id="transfer_balance",
        category="sql",
        use_cases=("soc_analyst",),
        difficulty="medium",
        entrypoints=("transfer_balance",),
        prompt="""
        Implement transfer_balance(conn, src: int, dst: int, amount: int) -> None.

        Table accounts(id INTEGER PRIMARY KEY, balance INTEGER) exists.
        Move amount from src to dst inside a transaction. amount must be a
        positive int and src must differ from dst. If either account is
        missing or src would go negative, roll back and raise ValueError.
        bool is not an int. Commit only on success.
        """,
        reference=r'''
        def transfer_balance(conn, src: int, dst: int, amount: int) -> None:
            if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
                raise ValueError("amount")
            if src == dst:
                raise ValueError("same")
            conn.execute("BEGIN")
            try:
                src_row = conn.execute(
                    "SELECT balance FROM accounts WHERE id = ?", (src,)
                ).fetchone()
                dst_row = conn.execute(
                    "SELECT balance FROM accounts WHERE id = ?", (dst,)
                ).fetchone()
                if src_row is None or dst_row is None or int(src_row[0]) < amount:
                    raise ValueError("insufficient")
                conn.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (amount, src),
                )
                conn.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (amount, dst),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.rollback()
                raise
        ''',
        tests=r'''
        import sqlite3
        import pytest
        import solution

        def _conn():
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER)")
            conn.executemany("INSERT INTO accounts VALUES (?, ?)", [(1, 50), (2, 10)])
            conn.commit()
            return conn

        def test_moves_and_rolls_back():
            conn = _conn()
            solution.transfer_balance(conn, 1, 2, 20)
            balances = dict(conn.execute("SELECT id, balance FROM accounts"))
            assert balances == {1: 30, 2: 30}
            with pytest.raises(ValueError):
                solution.transfer_balance(conn, 1, 2, 1000)
            balances = dict(conn.execute("SELECT id, balance FROM accounts"))
            assert balances == {1: 30, 2: 30}
        ''',
    ),
    coding_task(
        task_id="upsert_kv",
        category="sql",
        use_cases=("soc_analyst",),
        difficulty="medium",
        entrypoints=("upsert_kv",),
        prompt="""
        Implement upsert_kv(conn, key: str, value: str) -> None.

        Table settings(key TEXT PRIMARY KEY, value TEXT) exists. Insert the
        pair, or replace value when key already exists. key must be a
        non-empty str and value a str. Commit before returning.
        """,
        reference=r'''
        def upsert_kv(conn, key: str, value: str) -> None:
            if not isinstance(key, str) or key == "" or not isinstance(value, str):
                raise ValueError("kv")
            conn.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            conn.commit()
        ''',
        tests=r'''
        import sqlite3
        import solution

        def test_upsert():
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
            solution.upsert_kv(conn, "mode", "a")
            solution.upsert_kv(conn, "mode", "b")
            assert conn.execute("SELECT value FROM settings WHERE key = 'mode'").fetchone()[0] == "b"
            assert conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 1
        ''',
    ),
    coding_task(
        task_id="search_name",
        category="sql",
        use_cases=("soc_analyst",),
        difficulty="medium",
        entrypoints=("search_name",),
        prompt="""
        Implement search_name(conn, fragment: str) -> list[tuple[int, str]].

        Table people(id INTEGER, name TEXT) exists. Return (id, name) whose
        name contains fragment, ordered by id. Treat %, _, and backslash in
        fragment as literals by escaping them in a LIKE pattern that uses
        ESCAPE '\\'. Non-str fragment raises TypeError.
        """,
        reference=r'''
        def search_name(conn, fragment: str) -> list[tuple[int, str]]:
            if not isinstance(fragment, str):
                raise TypeError("fragment")
            escaped = fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            rows = conn.execute(
                "SELECT id, name FROM people WHERE name LIKE ? ESCAPE '\\' ORDER BY id",
                (f"%{escaped}%",),
            ).fetchall()
            return [(int(row[0]), str(row[1])) for row in rows]
        ''',
        tests=r'''
        import sqlite3
        import solution

        def test_escapes_wildcards():
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE people (id INTEGER, name TEXT)")
            conn.executemany(
                "INSERT INTO people VALUES (?, ?)",
                [(1, "100%"), (2, "abc"), (3, "a_b")],
            )
            assert solution.search_name(conn, "%") == [(1, "100%")]
            assert solution.search_name(conn, "_") == [(3, "a_b")]
            assert solution.search_name(conn, "ab") == [(2, "abc")]
        ''',
    ),
    coding_task(
        task_id="ensure_column",
        category="sql",
        use_cases=("soc_analyst",),
        difficulty="medium",
        entrypoints=("ensure_column",),
        prompt="""
        Implement ensure_column(conn, table: str, column: str, decl: str) -> bool.

        If column is already on table, return False and do not alter it.
        Otherwise ADD COLUMN and return True. table and column must match
        [A-Za-z_][A-Za-z0-9_]{0,63}. decl must be exactly INTEGER, TEXT, or
        REAL. Anything else raises ValueError. Commit after a real alter.
        """,
        reference=r'''
        import re

        _IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
        _DECL = re.compile(r"^(INTEGER|TEXT|REAL)$")

        def ensure_column(conn, table: str, column: str, decl: str) -> bool:
            if not isinstance(table, str) or not isinstance(column, str) or not isinstance(decl, str):
                raise TypeError("str")
            if _IDENT.fullmatch(table) is None or _IDENT.fullmatch(column) is None:
                raise ValueError("ident")
            if _DECL.fullmatch(decl) is None:
                raise ValueError("decl")
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if column in cols:
                return False
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
            conn.commit()
            return True
        ''',
        tests=r'''
        import sqlite3
        import pytest
        import solution

        def test_adds_once_and_rejects_injection():
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE notes (id INTEGER)")
            assert solution.ensure_column(conn, "notes", "body", "TEXT") is True
            assert solution.ensure_column(conn, "notes", "body", "TEXT") is False
            names = [row[1] for row in conn.execute("PRAGMA table_info(notes)")]
            assert names == ["id", "body"]
            with pytest.raises(ValueError):
                solution.ensure_column(conn, "notes;drop", "body", "TEXT")
        ''',
    ),
)
