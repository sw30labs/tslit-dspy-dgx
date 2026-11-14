"""Containment checks for the strong backend and the weak-mode guarantees."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from tslit_dspy.drift.sandbox import run_hidden_tests, strong_backend

_PROBE = "import solution\n\ndef test_probe():\n    solution.probe()\n"


def _run(source: str, *, backend: str = "bwrap", timeout_s: float = 15):
    return run_hidden_tests(source, _PROBE, timeout_s=timeout_s, backend=backend)


@pytest.mark.skipif(strong_backend() != "bwrap", reason="bwrap is not available")
def test_bwrap_blocks_raw_socket_subprocess_home_and_repo() -> None:
    socket_src = (
        "import _socket\n"
        "def probe():\n"
        "    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)\n"
        "    sock.sendto(b'x', ('1.1.1.1', 53))\n"
    )
    result = _run(socket_src)
    assert result.status == "failed"
    blob = result.stdout + result.stderr
    assert "Network is unreachable" in blob or "network disabled" in blob

    child = (
        "import subprocess\n"
        "def probe():\n"
        "    return subprocess.check_output(\n"
        "        ['python3', '-c', 'import urllib.request; urllib.request.urlopen(\"http://1.1.1.1\", timeout=2)'],\n"
        "        timeout=3,\n"
        "    )\n"
    )
    result = _run(child)
    assert result.status == "failed"

    home = (
        "def probe():\n"
        "    open('/home/ubuntu/.profile').read()\n"
    )
    result = _run(home)
    assert result.status == "failed"

    repo = "def probe():\n    import tslit_dspy\n"
    result = _run(repo)
    assert result.status == "import_error"

    relative = "def probe():\n    open('test_hidden.py').read()\n"
    result = _run(relative)
    assert result.status == "failed"

    os.environ["DATABASE_URL"] = "postgres://leak"
    os.environ["GITHUB_PAT"] = "ghp_leak"
    try:
        env_src = (
            "import os\n"
            "def probe():\n"
            "    bad = [k for k in os.environ if k == 'DATABASE_URL' or k.endswith('_PAT')]\n"
            "    if bad:\n"
            "        raise AssertionError(bad)\n"
        )
        result = _run(env_src)
        assert result.status == "passed"
    finally:
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("GITHUB_PAT", None)


def test_weak_mode_killpg_rlimit_and_env(tmp_path: Path) -> None:
    marker = tmp_path / "child-escaped"
    source = (
        "import os, time\n"
        f"def probe():\n"
        f"    if os.fork() == 0:\n"
        f"        time.sleep(1.5)\n"
        f"        open({str(marker)!r}, 'w').write('x')\n"
        f"        os._exit(0)\n"
        f"    while True:\n"
        f"        pass\n"
    )
    result = _run(source, backend="weak", timeout_s=0.6)
    assert result.status == "timeout"
    time.sleep(1.6)
    assert not marker.exists()

    limited = (
        "import resource\n"
        "def probe():\n"
        "    soft, _hard = resource.getrlimit(resource.RLIMIT_FSIZE)\n"
        "    if soft > 8 * 1024 * 1024:\n"
        "        raise AssertionError(soft)\n"
        "    nproc, _h = resource.getrlimit(resource.RLIMIT_NPROC)\n"
        "    if nproc > 1024:\n"
        "        raise AssertionError(nproc)\n"
        "    try:\n"
        "        open('big.bin', 'wb').write(b'x' * (9 * 1024 * 1024))\n"
        "    except OSError:\n"
        "        return\n"
        "    raise AssertionError('write was not limited')\n"
    )
    result = _run(limited, backend="weak", timeout_s=15)
    assert result.status == "passed", result.stderr[-400:] + result.stdout[-400:]
