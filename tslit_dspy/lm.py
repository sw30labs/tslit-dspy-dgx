"""
DSPy LM factory for TSLIT-DSPy — local Ollama only.

All detection-stack LMs pass model_policy.assert_detection_model() and are
served by Ollama at OLLAMA_BASE_URL (default http://127.0.0.1:11434).
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from typing import Optional

import dspy

from tslit_dspy.model_policy import (
    DEFAULT_DETECTION_MODEL,
    DEFAULT_OLLAMA_BASE_URL,
    DETECTION_ALIASES,
    assert_detection_model,
    is_allowed_detection_model,
    strip_ollama_prefix,
)

logger = logging.getLogger(__name__)


def ollama_settings() -> dict:
    root = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    return {
        "base_url": root,
        "openai_base_url": f"{root}/v1",
        "model": os.getenv("OLLAMA_MODEL", DEFAULT_DETECTION_MODEL),
        "api_key": os.getenv("OLLAMA_API_KEY", "ollama"),
        "timeout": float(os.getenv("OLLAMA_TIMEOUT_S", "600")),
    }


def ollama_chat_id(model: Optional[str] = None) -> str:
    """Resolve a user/model string to `ollama_chat/<tag>` for DSPy."""
    raw = (model or "").strip()
    if not raw or raw.lower() in DETECTION_ALIASES:
        raw = ollama_settings()["model"]
    raw = strip_ollama_prefix(raw)
    return f"ollama_chat/{raw}"


def resolve_detection_model(model: Optional[str] = None) -> str:
    """Resolve the model id for a detection-stack role."""
    return assert_detection_model(ollama_chat_id(model), role="detection")


def make_lm(
    model: Optional[str] = None,
    *,
    role: str = "detection",
    model_base_url: Optional[str] = None,
    enforce_policy: bool = True,
) -> dspy.LM:
    """Create a DSPy LM pointed at local Ollama."""
    mid = ollama_chat_id(model)
    if enforce_policy:
        assert_detection_model(mid, role=role)
    elif not is_allowed_detection_model(mid):
        logger.warning("Model %s is blocked by origin policy for role=%s", mid, role)

    cfg = ollama_settings()
    base = (model_base_url or cfg["base_url"]).rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    # Muse Glimmer (and other "thinking" Ollama tags) dump the whole token
    # budget into a reasoning channel and then emit `{}` if DSPy also turns
    # on Ollama format=json. Detector calls need a JSON object in `content`.
    think = (os.getenv("OLLAMA_THINK") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "4096"))
    logger.info(
        "Using Ollama LM model=%s base=%s role=%s think=%s max_tokens=%s",
        mid,
        base,
        role,
        think,
        max_tokens,
    )
    return dspy.LM(
        mid,
        api_base=base,
        api_key=cfg["api_key"],
        temperature=0.0,
        max_tokens=max_tokens,
        timeout=cfg["timeout"],
        num_retries=2,
        think=think,
        drop_params=True,
    )


def health_check_ollama(base_url: Optional[str] = None, timeout: float = 5.0) -> dict:
    """Probe local Ollama catalog. Returns status dict (never raises)."""
    cfg = ollama_settings()
    root = (base_url or cfg["base_url"]).rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    configured = strip_ollama_prefix(cfg["model"])
    result: dict = {
        "ok": False,
        "base_url": root,
        "openai_base_url": f"{root}/v1",
        "configured_model": configured,
        "models": [],
        "error": None,
        "detection_allowed": [],
        "detection_blocked": [],
    }

    models: list[str] = []
    last_err: Optional[str] = None
    for url, parser in (
        (f"{root}/api/tags", _models_from_tags),
        (f"{root}/v1/models", _models_from_openai),
    ):
        try:
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            models = parser(payload)
            last_err = None
            break
        except Exception as exc:  # noqa: BLE001 — health probe
            last_err = str(exc)

    if last_err and not models:
        result["error"] = last_err
        return result

    result["ok"] = True
    result["models"] = models
    result["detection_allowed"] = [m for m in models if is_allowed_detection_model(m)]
    result["detection_blocked"] = [
        m for m in models if not is_allowed_detection_model(m)
    ]
    return result


def _models_from_tags(payload: dict) -> list[str]:
    names = []
    for m in payload.get("models", []) or []:
        name = m.get("name") or m.get("model") or ""
        if name:
            names.append(name)
    return names


def _models_from_openai(payload: dict) -> list[str]:
    return [m.get("id", "") for m in payload.get("data", []) if m.get("id")]


def host_preflight() -> list[str]:
    """Return human-readable findings (empty = clean enough for DGX)."""
    findings: list[str] = []
    if sys.platform != "linux":
        findings.append(f"Expected Linux DGX host (found {sys.platform})")
    machine = platform.machine().lower()
    if machine not in {"aarch64", "arm64"}:
        findings.append(f"DGX Spark is typically aarch64 (found {machine})")
    if shutil.which("ollama") is None:
        findings.append("ollama not on PATH")
    if shutil.which("nvidia-smi") is None:
        findings.append("nvidia-smi not on PATH")
    else:
        try:
            subprocess.run(
                ["nvidia-smi"],
                check=True,
                capture_output=True,
                timeout=10,
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(f"nvidia-smi failed: {exc}")
    return findings
