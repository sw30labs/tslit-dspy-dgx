"""Run a candidate module against hidden pytest tests.

Network connects are blocked inside the child. The block is a test harness,
not a security boundary against a hostile interpreter. The parent also applies
a wall-clock timeout and does not pass secret-looking environment variables.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

_SECRETISH = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.IGNORECASE)

_RUNNER = """\
import os
import socket
import sys

def _blocked(*_args, **_kwargs):
    raise OSError("network disabled in drift sandbox")

if os.environ.get("DRIFT_BLOCK_NETWORK") == "1":
    class _BlockedSocket(socket.socket):
        def connect(self, address):  # noqa: ARG002
            raise OSError("network disabled in drift sandbox")

        def connect_ex(self, address):  # noqa: ARG002
            raise OSError("network disabled in drift sandbox")

    socket.socket = _BlockedSocket
    socket.create_connection = _blocked

import pytest

raise SystemExit(
    pytest.main(["-p", "no:cacheprovider", "-q", "--tb=line", "test_hidden.py"])
)
"""


@dataclass(frozen=True)
class SandboxResult:
    status: str
    passed: int
    failed: int
    stdout: str
    stderr: str
    duration_s: float


def sandbox_env(base: dict[str, str] | None = None, *, block_network: bool) -> dict[str, str]:
    source = base if base is not None else dict(os.environ)
    env = {key: value for key, value in source.items() if not _SECRETISH.search(key)}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["DRIFT_BLOCK_NETWORK"] = "1" if block_network else "0"
    return env


def _counts(blob: str) -> tuple[int, int]:
    failed = 0
    passed = 0
    failed_match = re.search(r"(\d+)\s+failed", blob)
    passed_match = re.search(r"(\d+)\s+passed", blob)
    if failed_match:
        failed = int(failed_match.group(1))
    if passed_match:
        passed = int(passed_match.group(1))
    return passed, failed


def syntax_error(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return str(exc)
    return None


def run_hidden_tests(
    source: str,
    test_source: str,
    *,
    timeout_s: float = 8.0,
    block_network: bool = True,
) -> SandboxResult:
    """Execute ``test_source`` against ``source`` saved as ``solution.py``."""
    with tempfile.TemporaryDirectory(prefix="drift-sbx-") as tmp:
        work = Path(tmp)
        (work / "solution.py").write_text(source, encoding="utf-8")
        (work / "test_hidden.py").write_text(test_source, encoding="utf-8")
        (work / "run_tests.py").write_text(_RUNNER, encoding="utf-8")
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "run_tests.py"],
                cwd=work,
                env=sandbox_env(block_network=block_network),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", "replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
            return SandboxResult(
                status="timeout",
                passed=0,
                failed=0,
                stdout=stdout,
                stderr=stderr,
                duration_s=float(timeout_s),
            )
        blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
        passed, failed = _counts(blob)
        if proc.returncode == 0 and failed == 0 and passed > 0:
            status = "passed"
        elif failed > 0 or passed > 0:
            status = "failed"
        else:
            status = "error"
        return SandboxResult(
            status=status,
            passed=passed,
            failed=failed,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            duration_s=time.perf_counter() - started,
        )
