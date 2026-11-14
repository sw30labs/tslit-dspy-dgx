"""Sandbox pass, fail, network block, timeout, and secret stripping."""

from __future__ import annotations

from tslit_dspy.drift.bank import tasks_by_id
from tslit_dspy.drift.sandbox import run_hidden_tests, sandbox_env

_PING = (
    "import socket\n"
    "def ping():\n"
    "    sock = socket.socket()\n"
    "    sock.connect(('203.0.113.1', 9))\n"
    "    return 1\n"
)
_PING_TEST = "import solution\n\ndef test_ping():\n    solution.ping()\n"
_LOOP = "def loop():\n    while True:\n        pass\n"
_LOOP_TEST = "import solution\n\ndef test_loop():\n    solution.loop()\n"


def test_reference_and_buggy_module() -> None:
    task = tasks_by_id()["parse_kv_lines"]
    good = run_hidden_tests(task.reference_source, task.hidden_test_source, timeout_s=30)
    assert good.status == "passed"
    assert good.passed >= 1
    bad_source = "def parse_kv_lines(text):\n    raise RuntimeError('bug')\n"
    bad = run_hidden_tests(bad_source, task.hidden_test_source, timeout_s=30)
    assert bad.status == "failed"
    assert bad.failed >= 1


def test_network_is_blocked() -> None:
    result = run_hidden_tests(_PING, _PING_TEST, timeout_s=15, block_network=True)
    blob = result.stdout + result.stderr
    assert result.status == "failed"
    assert "network disabled" in blob


def test_timeout() -> None:
    result = run_hidden_tests(_LOOP, _LOOP_TEST, timeout_s=1, block_network=True)
    assert result.status == "timeout"


def test_secret_env_is_dropped() -> None:
    env = sandbox_env(
        {"PATH": "/usr/bin", "OPENAI_API_KEY": "sk-test", "HOME": "/tmp", "USER": "me"},
        block_network=True,
    )
    assert "OPENAI_API_KEY" not in env
    assert env["PATH"] == "/usr/bin"
    assert env["DRIFT_BLOCK_NETWORK"] == "1"
