"""Filesystem tasks. Tests create their own temporary directories."""

from __future__ import annotations

from tslit_dspy.drift.bank.model import coding_task

TASKS = (
    coding_task(
        task_id="read_utf8",
        category="file_io",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="easy",
        entrypoints=("read_utf8",),
        prompt="""
        Implement read_utf8(path: str) -> str.

        Read the whole file as UTF-8 with strict errors and return the text.
        Invalid UTF-8 raises UnicodeDecodeError. A missing file raises
        FileNotFoundError.
        """,
        reference=r'''
        def read_utf8(path: str) -> str:
            with open(path, "r", encoding="utf-8", newline="") as handle:
                return handle.read()
        ''',
        tests=r'''
        import tempfile
        from pathlib import Path
        import pytest
        import solution

        def test_roundtrip_and_strict():
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "a.txt"
                path.write_text("héllo\n", encoding="utf-8")
                assert solution.read_utf8(str(path)) == "héllo\n"
                bad = Path(tmp) / "bad.bin"
                bad.write_bytes(b"\xff")
                with pytest.raises(UnicodeDecodeError):
                    solution.read_utf8(str(bad))

        def test_missing():
            with pytest.raises(FileNotFoundError):
                solution.read_utf8("/no/such/drift-file.txt")
        ''',
    ),
    coding_task(
        task_id="atomic_write_text",
        category="file_io",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="medium",
        entrypoints=("atomic_write_text",),
        prompt="""
        Implement atomic_write_text(path: str, text: str) -> None.

        Create parent directories. Write UTF-8 text to a sibling temp file
        whose name is the destination name plus ".tmp", then os.replace it
        onto path. No temp file remains. Non-str text raises TypeError.
        """,
        reference=r'''
        import os
        from pathlib import Path

        def atomic_write_text(path: str, text: str) -> None:
            if not isinstance(text, str):
                raise TypeError("text")
            dest = Path(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".tmp")
            tmp.write_text(text, encoding="utf-8", newline="\n")
            os.replace(tmp, dest)
        ''',
        tests=r'''
        import tempfile
        from pathlib import Path
        import solution

        def test_replaces_and_cleans_temp():
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "nested" / "out.txt"
                solution.atomic_write_text(str(dest), "hello\n")
                assert dest.read_text(encoding="utf-8") == "hello\n"
                assert not (dest.parent / "out.txt.tmp").exists()

        def test_type():
            import pytest
            with pytest.raises(TypeError):
                solution.atomic_write_text("out.txt", b"nope")
        ''',
    ),
    coding_task(
        task_id="list_files",
        category="file_io",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="easy",
        entrypoints=("list_files",),
        prompt="""
        Implement list_files(root: str) -> list[str].

        Return relative posix paths of regular files under root, sorted.
        Skip symlinks. Do not include directory names. If root is not a
        directory, raise ValueError.
        """,
        reference=r'''
        import os
        from pathlib import Path

        def list_files(root: str) -> list[str]:
            base = Path(root)
            if not base.is_dir():
                raise ValueError("root")
            found = []
            for dirpath, dirnames, filenames in os.walk(base):
                kept = []
                for name in dirnames:
                    if not (Path(dirpath) / name).is_symlink():
                        kept.append(name)
                dirnames[:] = kept
                for name in filenames:
                    full = Path(dirpath) / name
                    if full.is_symlink():
                        continue
                    found.append(full.relative_to(base).as_posix())
            return sorted(found)
        ''',
        tests=r'''
        import tempfile
        from pathlib import Path
        import solution

        def test_sorted_relative():
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                (base / "b").mkdir()
                (base / "a.txt").write_text("a", encoding="utf-8")
                (base / "b" / "c.txt").write_text("c", encoding="utf-8")
                assert solution.list_files(str(base)) == ["a.txt", "b/c.txt"]

        def test_not_a_directory():
            import pytest
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "a.txt"
                path.write_text("a", encoding="utf-8")
                with pytest.raises(ValueError):
                    solution.list_files(str(path))
        ''',
    ),
    coding_task(
        task_id="tail_lines",
        category="file_io",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="easy",
        entrypoints=("tail_lines",),
        prompt="""
        Implement tail_lines(path: str, n: int) -> list[str].

        Return the last n lines of a UTF-8 text file without newline
        characters. n == 0 returns []. If n is greater than the number of
        lines, return every line. n < 0 or bool raises ValueError.
        """,
        reference=r'''
        def tail_lines(path: str, n: int) -> list[str]:
            if isinstance(n, bool) or not isinstance(n, int) or n < 0:
                raise ValueError("n")
            with open(path, "r", encoding="utf-8", newline="") as handle:
                lines = handle.read().splitlines()
            if n == 0:
                return []
            return lines[-n:]
        ''',
        tests=r'''
        import tempfile
        from pathlib import Path
        import solution

        def test_tail():
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "log.txt"
                path.write_text("a\nb\nc\n", encoding="utf-8")
                assert solution.tail_lines(str(path), 2) == ["b", "c"]
                assert solution.tail_lines(str(path), 0) == []
                assert solution.tail_lines(str(path), 9) == ["a", "b", "c"]

        def test_negative():
            import pytest
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "log.txt"
                path.write_text("a\n", encoding="utf-8")
                with pytest.raises(ValueError):
                    solution.tail_lines(str(path), -1)
        ''',
    ),
    coding_task(
        task_id="manifest_sha256",
        category="file_io",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="medium",
        entrypoints=("manifest_sha256",),
        prompt="""
        Implement manifest_sha256(root: str) -> str.

        Walk regular files under root, skip symlinks, and order them by
        relative posix path. Update one SHA-256 with, for each file,
        the relative path as UTF-8, a NUL byte, the file bytes, and another
        NUL byte. Return the lowercase hex digest. An empty directory is the
        digest of no updates.
        """,
        reference=r'''
        import hashlib
        import os
        from pathlib import Path

        def manifest_sha256(root: str) -> str:
            base = Path(root)
            if not base.is_dir():
                raise ValueError("root")
            paths = []
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [
                    name for name in dirnames if not (Path(dirpath) / name).is_symlink()
                ]
                for name in filenames:
                    full = Path(dirpath) / name
                    if full.is_symlink():
                        continue
                    paths.append(full)
            paths.sort(key=lambda item: item.relative_to(base).as_posix())
            digest = hashlib.sha256()
            for full in paths:
                rel = full.relative_to(base).as_posix().encode("utf-8")
                digest.update(rel)
                digest.update(b"\0")
                digest.update(full.read_bytes())
                digest.update(b"\0")
            return digest.hexdigest()
        ''',
        tests=r'''
        import hashlib
        import tempfile
        from pathlib import Path
        import solution

        def test_stable_manifest():
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                (base / "b.txt").write_bytes(b"B")
                (base / "a.txt").write_bytes(b"A")
                digest = hashlib.sha256()
                digest.update(b"a.txt\0A\0")
                digest.update(b"b.txt\0B\0")
                assert solution.manifest_sha256(str(base)) == digest.hexdigest()

        def test_empty_dir():
            with tempfile.TemporaryDirectory() as tmp:
                empty = Path(tmp) / "empty"
                empty.mkdir()
                assert solution.manifest_sha256(str(empty)) == hashlib.sha256().hexdigest()
        ''',
    ),
    coding_task(
        task_id="keep_newest",
        category="file_io",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="medium",
        entrypoints=("keep_newest",),
        prompt="""
        Implement keep_newest(directory: str, n: int) -> list[str].

        Consider regular files directly inside directory (not subdirectories).
        Keep the n names that sort greatest. Delete the rest. Return the
        deleted names, sorted ascending. n == 0 deletes every file. n < 0 or
        bool raises ValueError. Do not follow symlinks.
        """,
        reference=r'''
        from pathlib import Path

        def keep_newest(directory: str, n: int) -> list[str]:
            if isinstance(n, bool) or not isinstance(n, int) or n < 0:
                raise ValueError("n")
            base = Path(directory)
            files = [path for path in base.iterdir() if path.is_file() and not path.is_symlink()]
            files.sort(key=lambda path: path.name, reverse=True)
            deleted = []
            for path in files[n:]:
                deleted.append(path.name)
                path.unlink()
            return sorted(deleted)
        ''',
        tests=r'''
        import tempfile
        from pathlib import Path
        import solution

        def test_keeps_lexical_newest():
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                for name in ("20240101", "20240601", "20240301"):
                    (base / name).write_text(name, encoding="utf-8")
                deleted = solution.keep_newest(str(base), 1)
                assert deleted == ["20240101", "20240301"]
                assert [path.name for path in base.iterdir()] == ["20240601"]

        def test_keep_none():
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                for name in ("20240101", "20240601"):
                    (base / name).write_text(name, encoding="utf-8")
                deleted = solution.keep_newest(str(base), 0)
                assert deleted == ["20240101", "20240601"]
                assert list(base.iterdir()) == []
        ''',
    ),
    coding_task(
        task_id="safe_unzip",
        category="file_io",
        use_cases=("soc_analyst", "defense_contractor"),
        difficulty="medium",
        entrypoints=("safe_unzip",),
        prompt="""
        Implement safe_unzip(zip_path: str, dest: str) -> list[str].

        Extract regular members into dest. Skip directory entries, absolute
        paths, members whose parts include "..", and names containing a
        backslash. Create dest if needed. Return the extracted relative posix
        paths, sorted. Do not extract a skipped member.
        """,
        reference=r'''
        import zipfile
        from pathlib import Path

        def safe_unzip(zip_path: str, dest: str) -> list[str]:
            dest_path = Path(dest).resolve()
            dest_path.mkdir(parents=True, exist_ok=True)
            extracted = []
            with zipfile.ZipFile(zip_path) as archive:
                for info in archive.infolist():
                    name = info.filename
                    if name.endswith("/"):
                        continue
                    rel = Path(name)
                    if rel.is_absolute() or ".." in rel.parts or "\\" in name:
                        continue
                    target = (dest_path / rel).resolve()
                    try:
                        target.relative_to(dest_path)
                    except ValueError:
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(info))
                    extracted.append(rel.as_posix())
            return sorted(extracted)
        ''',
        tests=r'''
        import tempfile
        import zipfile
        from pathlib import Path
        import solution

        def test_skips_zip_slip():
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                archive_path = base / "sample.zip"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr("ok/file.txt", b"yes")
                    archive.writestr("../escape.txt", b"no")
                    archive.writestr("/abs.txt", b"no")
                dest = base / "out"
                got = solution.safe_unzip(str(archive_path), str(dest))
                assert got == ["ok/file.txt"]
                assert (dest / "ok" / "file.txt").read_bytes() == b"yes"
                assert not (base / "escape.txt").exists()

        def test_empty_archive():
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                empty_zip = base / "empty.zip"
                with zipfile.ZipFile(empty_zip, "w"):
                    pass
                assert solution.safe_unzip(str(empty_zip), str(base / "empty-out")) == []
        ''',
    ),
)
