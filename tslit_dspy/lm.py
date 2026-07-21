"""
DSPy LM factory for TSLIT-DSPy on NVIDIA DGX Spark.

Priority (detection stack):
  1. Explicit model string + provider routing
  2. Local vLLM OpenAI-compatible server (default on DGX)
  3. Ollama (optional)
  4. Cloud litellm/DSPy providers (Anthropic, OpenAI, …)

All detection-stack LMs pass model_policy.assert_detection_model().
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Optional

import dspy

from tslit_dspy.model_policy import (
    DEFAULT_DETECTION_MODEL,
    DEFAULT_VLLM_BASE_URL,
    assert_detection_model,
    is_allowed_detection_model,
)

logger = logging.getLogger(__name__)

_ALIASES = frozenset({"local", "vllm", "detection", "default", "auto", ""})


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def vllm_settings() -> dict:
    return {
        "base_url": os.getenv("VLLM_BASE_URL", DEFAULT_VLLM_BASE_URL).rstrip("/"),
        "model": os.getenv("VLLM_MODEL", DEFAULT_DETECTION_MODEL),
        "api_key": os.getenv("VLLM_API_KEY", "test"),
        "timeout": float(os.getenv("VLLM_TIMEOUT_S", "600")),
    }


def resolve_detection_model(model: Optional[str] = None) -> str:
    """Resolve the model id for a detection-stack role."""
    raw = (model or "").strip()
    if raw and raw.lower() not in _ALIASES:
        return assert_detection_model(raw, role="detection")

    provider = (os.getenv("TSLIT_MODEL_PROVIDER") or "vllm").strip().lower()
    if provider == "ollama":
        mid = os.getenv("OLLAMA_MODEL", "llama3.1")
        if not mid.startswith("ollama"):
            mid = f"ollama_chat/{mid}"
        return assert_detection_model(mid, role="detection")
    if provider in {"anthropic", "openai", "cloud"}:
        mid = os.getenv("TSLIT_CLOUD_MODEL") or os.getenv(
            "INFERENCE_MODEL", "anthropic/claude-opus-4-6"
        )
        return assert_detection_model(mid, role="detection")
    return assert_detection_model(vllm_settings()["model"], role="detection")


def _make_vllm_lm(model_id: str, *, role: str, base_url: Optional[str] = None) -> dspy.LM:
    cfg = vllm_settings()
    mid = assert_detection_model(model_id, role=role)
    base = (base_url or cfg["base_url"]).rstrip("/")
    dspy_model = mid if mid.startswith("openai/") else f"openai/{mid}"
    logger.info(
        "Using vLLM OpenAI-compatible LM model=%s base=%s role=%s",
        mid,
        base,
        role,
    )
    return dspy.LM(dspy_model, api_base=base, api_key=cfg["api_key"])


def make_lm(
    model: Optional[str] = None,
    *,
    role: str = "detection",
    model_base_url: Optional[str] = None,
    enforce_policy: bool = True,
) -> dspy.LM:
    """Create a DSPy LM for the given role (detection by default)."""
    raw = (model or "").strip()
    provider = (os.getenv("TSLIT_MODEL_PROVIDER") or "vllm").strip().lower()

    # Legacy Apple MLX path
    if _env_bool("USE_LOCAL_MLX") or raw.lower() == "mlx":
        mlx_base = os.getenv(
            "MLX_INFERENCE_URL",
            os.getenv("MLX_COMPILE_URL", "http://localhost:8080/v1"),
        )
        logger.info("Using local MLX server at %s (role=%s)", mlx_base, role)
        return dspy.LM("openai/local", api_base=mlx_base, api_key="local")

    looks_ollama = raw.lower().startswith("ollama")
    looks_cloud = raw.lower().startswith(
        ("anthropic/", "openai/gpt-", "openai/o1", "openai/o3", "azure/", "xai/")
    )
    # openai/gpt-oss and openai/<hf-id> used via vLLM need local base
    is_gpt_oss = "gpt-oss" in raw.lower()
    is_nemotron = "nemotron" in raw.lower() or raw.lower().startswith("nvidia/")
    is_alias = raw.lower() in _ALIASES

    # Ollama
    if looks_ollama or provider == "ollama":
        mid = raw if looks_ollama else os.getenv("OLLAMA_MODEL", "llama3.1")
        if not mid.startswith("ollama"):
            mid = f"ollama_chat/{mid}"
        elif mid.startswith("ollama/") and not mid.startswith("ollama_chat/"):
            mid = mid.replace("ollama/", "ollama_chat/", 1)
        if enforce_policy:
            assert_detection_model(mid, role=role)
        base = model_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        logger.info("Using Ollama model=%s base=%s role=%s", mid, base, role)
        return dspy.LM(mid, api_base=base)

    # Local vLLM (DGX default) — aliases, Nemotron, GPT-OSS, or provider=vllm
    use_vllm = (
        is_alias
        or is_nemotron
        or is_gpt_oss
        or (provider == "vllm" and not looks_cloud)
        or (provider == "vllm" and raw == "")
    )
    if use_vllm and not looks_cloud:
        mid = vllm_settings()["model"] if is_alias else (raw or vllm_settings()["model"])
        if not enforce_policy:
            # still warn
            if not is_allowed_detection_model(mid):
                logger.warning(
                    "Model %s is blocked by origin policy for role=%s", mid, role
                )
        return _make_vllm_lm(mid, role=role, base_url=model_base_url)

    # Cloud / litellm (Anthropic Claude, OpenAI GPT, etc.)
    mid = raw or os.getenv("TSLIT_CLOUD_MODEL", "anthropic/claude-opus-4-6")
    if enforce_policy:
        assert_detection_model(mid, role=role)
    logger.info("Using cloud/provider LM model=%s role=%s", mid, role)
    return dspy.LM(mid)


def health_check_vllm(base_url: Optional[str] = None, timeout: float = 5.0) -> dict:
    """Probe local vLLM /v1/models. Returns status dict (never raises)."""
    cfg = vllm_settings()
    base = (base_url or cfg["base_url"]).rstrip("/")
    url = f"{base}/models"
    result: dict = {
        "ok": False,
        "base_url": base,
        "configured_model": cfg["model"],
        "models": [],
        "error": None,
        "detection_allowed": [],
        "detection_blocked": [],
    }
    try:
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {cfg['api_key']}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = [m.get("id", "") for m in payload.get("data", [])]
        result["models"] = models
        result["ok"] = True
        result["detection_allowed"] = [m for m in models if is_allowed_detection_model(m)]
        result["detection_blocked"] = [
            m for m in models if not is_allowed_detection_model(m)
        ]
    except Exception as exc:  # noqa: BLE001 — health probe
        result["error"] = str(exc)
    return result


def host_preflight() -> list[str]:
    """Return human-readable findings (empty = clean enough for DGX)."""
    findings: list[str] = []
    if sys.platform != "linux":
        findings.append(f"Expected Linux DGX host (found {sys.platform})")
    machine = platform.machine().lower()
    if machine not in {"aarch64", "arm64"}:
        findings.append(f"DGX Spark is typically aarch64 (found {machine})")
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
