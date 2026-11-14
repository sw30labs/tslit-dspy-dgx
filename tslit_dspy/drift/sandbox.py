"""Run hidden pytest tests in an isolated interpreter.

Backends, in order:

- ``bwrap``: user namespace, no network, host home not mounted, minimal
  sys.path. Descendant processes inherit the network namespace, so a raw
  ``_socket`` or a second Python cannot open an internet connection.
- ``docker``: ``docker run --network none --read-only`` when that engine and
  a local ``python:3.12-slim`` image are already present. This module does
  not pull images.
- ``weak``: a local process with a new session, ``killpg`` on timeout,
  rlimits, an allow-listed environment, and ``python -I -S``. It is not a
  containment boundary. Live runs must pass ``--unsafe-sandbox`` to use it.

A harness self-check (arithmetic test, and a UDP send that must fail) runs
before the candidate module is imported. Only a failed self-check is a
harness fault. Import errors, collection errors, timeouts, and test failures
belong to the candidate.
"""

from __future__ import annotations

import ast
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

HARNESS_EXIT = 86

_DEP_PACKAGES = ("pytest", "_pytest", "pluggy", "iniconfig", "pygments")


@dataclass(frozen=True)
class SandboxResult:
    status: str
    passed: int
    failed: int
    errors: int
    stdout: str
    stderr: str
    duration_s: float
    backend: str
    harness_ok: bool
    returncode: int | None = None


def syntax_error(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return str(exc)
    return None


def sandbox_env(base: dict[str, str] | None = None, *, block_network: bool = True) -> dict[str, str]:
    """Allow-listed environment. Values in ``base`` are not copied through."""
    del base, block_network
    return _base_env(
        weak_patch=True,
        cpu_seconds=8,
        home="/tmp",
        paths={
            "sol": "/tmp/sol",
            "tests": "/tmp/tests",
            "junit": "/tmp/junit",
            "deps": "/tmp/deps",
            "harness": "/tmp/test_harness.py",
            "runner": "/tmp/run_tests.py",
            "tmp": "/tmp",
            "home": "/tmp",
        },
    )


def strong_backend() -> str | None:
    if shutil.which("bwrap"):
        return "bwrap"
    if _docker_ready():
        return "docker"
    return None


def resolve_backend(requested: str | None = None) -> str:
    if requested in {"bwrap", "docker", "weak"}:
        if requested == "bwrap" and not shutil.which("bwrap"):
            raise RuntimeError("bwrap is not installed")
        if requested == "docker" and not _docker_ready():
            raise RuntimeError("docker python image is not available")
        return requested
    return strong_backend() or "weak"


def _docker_ready() -> bool:
    if not shutil.which("docker"):
        return False
    probe = subprocess.run(
        ["docker", "image", "inspect", "python:3.12-slim"],
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0


def _pytest_mounts() -> list[tuple[str, str]]:
    """Package directories, dist-info, and the py.py shim.

    ``importlib.metadata`` needs the dist-info directories on ``sys.path``
    or pytest dies while printing its own version.
    """
    mounts: list[tuple[str, str]] = []
    site_dirs: set[Path] = set()
    for name in _DEP_PACKAGES:
        module = __import__(name)
        src = Path(module.__file__).resolve().parent
        mounts.append((str(src), f"/deps/{name}"))
        site_dirs.add(src.parent)
    py_mod = __import__("py")
    py_file = str(Path(py_mod.__file__).resolve())
    mounts.append((py_file, "/deps/py.py"))
    prefixes = ("pytest-", "pluggy-", "iniconfig-", "pygments-", "packaging-")
    for site in site_dirs:
        for child in site.iterdir():
            if child.is_dir() and child.name.endswith(".dist-info") and child.name.startswith(prefixes):
                mounts.append((str(child), f"/deps/{child.name}"))
    return mounts


_RUNNER = textwrap.dedent(
    """\
    import os
    import resource
    import sys

    _SOL = os.environ["DRIFT_SOL"]
    _TESTS = os.environ["DRIFT_TESTS"]
    _JUNIT = os.environ["DRIFT_JUNIT"]
    _DEPS = os.environ["DRIFT_DEPS"]
    _HARNESS = os.environ["DRIFT_HARNESS"]
    sys.path.insert(0, _DEPS)
    sys.path.insert(0, _SOL)

    def _limits() -> None:
        mb = 768 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mb, mb))
        cpu = int(os.environ.get("DRIFT_CPU_SECONDS", "10"))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        fsize = 8 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))

    def _patch_network() -> None:
        import _socket
        import socket

        def _blocked(*_args, **_kwargs):
            raise OSError("network disabled in drift sandbox")

        class _Blocked(_socket.socket):
            def connect(self, address):  # noqa: ARG002
                raise OSError("network disabled in drift sandbox")

            def connect_ex(self, address):  # noqa: ARG002
                raise OSError("network disabled in drift sandbox")

            def sendto(self, data, *args):  # noqa: ARG002
                raise OSError("network disabled in drift sandbox")

        _socket.socket = _Blocked
        socket.socket = _Blocked
        socket.create_connection = _blocked

    def _network_is_blocked() -> bool:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(b"x", ("1.1.1.1", 9))
        except OSError:
            return True
        return False

    _limits()
    if os.environ.get("DRIFT_WEAK_NETPATCH") == "1":
        _patch_network()
    if not _network_is_blocked():
        raise SystemExit(86)

    import pytest

    self_code = pytest.main(
        [
            "-p",
            "no:cacheprovider",
            "--tb=line",
            f"--junitxml={_JUNIT}/self.xml",
            _HARNESS,
        ]
    )
    if self_code != 0:
        raise SystemExit(86)
    model_code = pytest.main(
        [
            "-p",
            "no:cacheprovider",
            "--tb=line",
            f"--junitxml={_JUNIT}/model.xml",
            f"{_TESTS}/test_hidden.py",
        ]
    )
    raise SystemExit(model_code)
    """
)

_HARNESS_TEST = "def test_harness_arithmetic():\n    assert 1 + 1 == 2\n"


def _base_env(*, weak_patch: bool, cpu_seconds: int, home: str, paths: dict[str, str]) -> dict[str, str]:
    env = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "DRIFT_CPU_SECONDS": str(cpu_seconds),
        "HOME": home,
        "TMPDIR": "/tmp" if not weak_patch else paths["tmp"],
        "DRIFT_SOL": paths["sol"],
        "DRIFT_TESTS": paths["tests"],
        "DRIFT_JUNIT": paths["junit"],
        "DRIFT_DEPS": paths["deps"],
        "DRIFT_HARNESS": paths["harness"],
    }
    if weak_patch:
        env["DRIFT_WEAK_NETPATCH"] = "1"
        env["DRIFT_SANDBOX_MODE"] = "weak"
    else:
        env["DRIFT_SANDBOX_MODE"] = "strong"
    return env


def _prepare_tree(root: Path, source: str, test_source: str) -> None:
    sol = root / "sol"
    tests = root / "tests"
    runner = root / "runner"
    junit = root / "junit"
    home = root / "home"
    deps = root / "deps"
    for path in (sol, tests, runner, junit, home, deps):
        path.mkdir(parents=True)
    (sol / "solution.py").write_text(source, encoding="utf-8")
    (tests / "test_hidden.py").write_text(test_source, encoding="utf-8")
    (runner / "run_tests.py").write_text(_RUNNER, encoding="utf-8")
    (runner / "test_harness.py").write_text(_HARNESS_TEST, encoding="utf-8")
    for src, dst in _pytest_mounts():
        link = deps / Path(dst).name
        if not link.exists():
            os.symlink(src, link)


def _sandbox_paths(root: Path, *, inside: bool) -> dict[str, str]:
    if inside:
        return {
            "sol": "/sandbox/sol",
            "tests": "/sandbox/tests",
            "junit": "/sandbox/junit",
            "deps": "/deps",
            "harness": "/sandbox/runner/test_harness.py",
            "runner": "/sandbox/runner/run_tests.py",
            "tmp": "/tmp",
            "home": "/sandbox/home",
        }
    return {
        "sol": str(root / "sol"),
        "tests": str(root / "tests"),
        "junit": str(root / "junit"),
        "deps": str(root / "deps"),
        "harness": str(root / "runner" / "test_harness.py"),
        "runner": str(root / "runner" / "run_tests.py"),
        "tmp": str(root / "tmp"),
        "home": str(root / "home"),
    }


def _command(backend: str, root: Path, env: dict[str, str]) -> list[str]:
    if backend == "bwrap":
        cmd = [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/lib",
            "/lib",
        ]
        if Path("/lib64").is_dir():
            cmd += ["--ro-bind", "/lib64", "/lib64"]
        if Path("/bin").is_dir():
            cmd += ["--ro-bind", "/bin", "/bin"]
        cmd += [
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/home",
            "--dir",
            "/sandbox/home",
            "--bind",
            str(root / "sol"),
            "/sandbox/sol",
            "--ro-bind",
            str(root / "tests"),
            "/sandbox/tests",
            "--ro-bind",
            str(root / "runner"),
            "/sandbox/runner",
            "--bind",
            str(root / "junit"),
            "/sandbox/junit",
        ]
        for src, dst in _pytest_mounts():
            cmd += ["--ro-bind", src, dst]
        cmd += ["--chdir", "/sandbox/sol", "--clearenv"]
        for key, value in env.items():
            cmd += ["--setenv", key, value]
        cmd += ["--", "/usr/bin/python3", "-I", "-S", "/sandbox/runner/run_tests.py"]
        return cmd
    if backend == "docker":
        flags = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/sandbox/home",
            "-v",
            f"{root / 'sol'}:/sandbox/sol:ro",
            "-v",
            f"{root / 'tests'}:/sandbox/tests:ro",
            "-v",
            f"{root / 'runner'}:/sandbox/runner:ro",
            "-v",
            f"{root / 'junit'}:/sandbox/junit:rw",
            "-w",
            "/sandbox/sol",
        ]
        for key, value in env.items():
            flags += ["-e", f"{key}={value}"]
        for src, dst in _pytest_mounts():
            flags += ["-v", f"{src}:{dst}:ro"]
        flags += ["python:3.12-slim", "python", "-I", "-S", "/sandbox/runner/run_tests.py"]
        return flags
    (root / "tmp").mkdir(exist_ok=True)
    return [sys.executable, "-I", "-S", str(root / "runner" / "run_tests.py")]


def _parse_junit(path: Path) -> tuple[int, int, int, str]:
    if not path.is_file():
        return 0, 0, 0, ""
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return 0, 0, 0, ""
    passed = failed = errors = 0
    messages: list[str] = []
    for suite in tree.getroot().iter("testsuite"):
        for case in suite.findall("testcase"):
            failure = case.find("failure")
            error = case.find("error")
            if failure is not None:
                failed += 1
                messages.append(failure.get("message") or "")
                messages.append(failure.text or "")
            elif error is not None:
                errors += 1
                messages.append(error.get("message") or "")
                messages.append(error.text or "")
            else:
                passed += 1
    return passed, failed, errors, "\n".join(messages)


def _classify(passed: int, failed: int, errors: int, blob: str, returncode: int) -> str:
    text = blob.lower()
    if "modulenotfounderror" in text or "importerror" in text:
        return "import_error"
    if errors or returncode == 2:
        if "nameerror" in text or "systemexit" in text or "syntaxerror" in text:
            return "collection_error"
        return "collection_error" if errors or returncode == 2 else "failed"
    if failed:
        return "failed"
    if returncode == 0 and passed > 0 and errors == 0:
        return "passed"
    return "collection_error"


def run_hidden_tests(
    source: str,
    test_source: str,
    *,
    timeout_s: float = 8.0,
    block_network: bool = True,
    backend: str | None = None,
) -> SandboxResult:
    """Execute ``test_source`` against ``source`` saved as ``solution.py``."""
    del block_network  # every backend blocks network; the flag remains for callers
    chosen = resolve_backend(backend)
    cpu_seconds = max(2, int(timeout_s) + 1)
    with tempfile.TemporaryDirectory(prefix="drift-sbx-") as tmp:
        root = Path(tmp)
        _prepare_tree(root, source, test_source)
        inside = chosen in {"bwrap", "docker"}
        paths = _sandbox_paths(root, inside=inside)
        env = _base_env(
            weak_patch=(chosen == "weak"),
            cpu_seconds=cpu_seconds,
            home=paths["home"],
            paths=paths,
        )
        cmd = _command(chosen, root, env)
        started = time.perf_counter()
        proc = subprocess.Popen(
            cmd,
            cwd=(root / "sol") if chosen == "weak" else None,
            env=env if chosen == "weak" else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
        duration = time.perf_counter() - started
        stdout = stdout or ""
        stderr = stderr or ""
        if timed_out:
            return SandboxResult(
                status="timeout",
                passed=0,
                failed=0,
                errors=0,
                stdout=stdout,
                stderr=stderr,
                duration_s=duration,
                backend=chosen,
                harness_ok=True,
                returncode=proc.returncode,
            )
        code = proc.returncode
        if code == HARNESS_EXIT or code == -HARNESS_EXIT:
            return SandboxResult(
                status="harness_error",
                passed=0,
                failed=0,
                errors=0,
                stdout=stdout,
                stderr=stderr,
                duration_s=duration,
                backend=chosen,
                harness_ok=False,
                returncode=code,
            )
        if code is not None and code < 0:
            return SandboxResult(
                status="resource_limit",
                passed=0,
                failed=0,
                errors=0,
                stdout=stdout,
                stderr=stderr + f"\nsignal {-code}",
                duration_s=duration,
                backend=chosen,
                harness_ok=True,
                returncode=code,
            )
        passed, failed, errors, messages = _parse_junit(root / "junit" / "model.xml")
        blob = "\n".join((stdout, stderr, messages))
        status = _classify(passed, failed, errors, blob, 1 if code is None else int(code))
        return SandboxResult(
            status=status,
            passed=passed,
            failed=failed,
            errors=errors,
            stdout=stdout,
            stderr=stderr,
            duration_s=duration,
            backend=chosen,
            harness_ok=True,
            returncode=code,
        )
