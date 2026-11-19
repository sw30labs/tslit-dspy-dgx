"""Secondary static metrics. Missing tools are recorded, not treated as failures."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tslit_dspy.drift.detectors import security_pattern_hits


def _run(cmd: list[str], *, timeout_s: float = 20.0) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _ruff(path: Path, select: str) -> dict[str, Any]:
    exe = shutil.which("ruff")
    if exe is None:
        return {"status": "not_installed", "count": None}
    proc = _run([exe, "check", "--select", select, "--output-format", "json", str(path)])
    if proc is None:
        return {"status": "error", "count": None}
    try:
        payload = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return {"status": "error", "count": None}
    if not isinstance(payload, list):
        return {"status": "error", "count": None}
    return {"status": "ok", "count": len(payload)}


def _bandit(path: Path) -> dict[str, Any]:
    exe = shutil.which("bandit")
    if exe is None:
        return {"status": "not_installed", "count": None}
    proc = _run([exe, "-q", "-f", "json", str(path)])
    if proc is None:
        return {"status": "error", "count": None}
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"status": "error", "count": None}
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return {"status": "error", "count": None}
    return {"status": "ok", "count": len(results)}


def _pyflakes(path: Path) -> dict[str, Any]:
    # Ruff's F rules are pyflakes. Prefer that so CI does not need a second tool.
    via_ruff = _ruff(path, "F")
    if via_ruff["status"] == "ok":
        return via_ruff
    exe = shutil.which("pyflakes")
    if exe is None:
        return {"status": "not_installed", "count": None}
    proc = _run([exe, str(path)])
    if proc is None:
        return {"status": "error", "count": None}
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    return {"status": "ok", "count": len(lines)}


def analyze_source(source: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="drift-lint-") as tmp:
        path = Path(tmp) / "solution.py"
        path.write_text(source, encoding="utf-8")
        ruff = _ruff(path, "E,W")
        pyflakes = _pyflakes(path)
        bandit = _bandit(path)
    return {
        "ruff": ruff,
        "pyflakes": pyflakes,
        "bandit": bandit,
        "security_pattern_hits": security_pattern_hits(source),
    }
