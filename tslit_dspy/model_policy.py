"""
Model-origin policy for TSLIT-DSPy on DGX.

Hard rule (from project design / whitepaper):
  Detection infrastructure (compile, inference, autoresearch brain) must use
  non-adversary / American-origin models. Adversary-origin open-weight models
  (Qwen, DeepSeek, MiniMax, …) are *scan targets only* — never part of the
  detector stack.

Local serving is Ollama only (`http://127.0.0.1:11434`).

Roles:
  - detection: analyzer LM (ThreatClassifier → QAValidator), MIPROv2 compile LM,
    autoresearch agent brain, deployment validation LM
  - target: models under integrity test (may be any origin, including adversary)
"""

from __future__ import annotations

import re
from typing import Iterable

# Substrings (case-insensitive) that mark adversary-origin / non-US stacks.
# Match against the full model id string (provider prefix + name).
ADVERSARY_ORIGIN_MARKERS: tuple[str, ...] = (
    "qwen",
    "ornith",  # Qwen-family MoE served under a local tag
    "deepseek",
    "minimax",
    "moonshot",
    "kimi",
    "baichuan",
    "01-ai",
    "01ai",
    "yi-",
    "/yi",
    "zhipu",
    "glm-4",
    "chatglm",
    "stepfun",
    "step-3",
    "baidu",
    "ernie",
    "tencent",
    "hunyuan",
    "alibaba",
    "dashscope",
    "tongyi",
    "internlm",
    "sensechat",
    "skywork",
)

# Positive allow patterns for detection-stack models (US / non-adversary).
# A model must match at least one of these *or* fail closed if policy is strict.
DETECTION_ALLOW_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"nvidia",
        r"nemotron",
        r"muse[-_]?glimmer",  # Meta Superintelligence Labs
        r"meta-models",
        r"meta-llama",
        r"gpt-oss",
        r"openai/",
        r"openai_",
        r"gpt-4",
        r"gpt-5",
        r"gpt-3\.5",
        r"o1",
        r"o3",
        r"o4",
        r"anthropic/",
        r"claude",
        r"llama[-_]?3",
        r"llama[-_]?4",
        r"grok",
        r"xai/",
        r"amazon/",
        r"nova-",
        r"google/",
        r"gemini",
        r"mistralai/",  # EU; allowed as non-adversary Western open stack
        r"mistral",
        r"phi-4",
        r"phi-3",
        r"microsoft/",
    )
)

# Ollama tags on this DGX that are approved for the detection brain.
DGX_DETECTION_MODELS: dict[str, str] = {
    "muse-glimmer:30b-bf16": "Meta Muse Glimmer 30B (detection default)",
}

# Ollama tags that must NOT run the detector (scan targets only).
DGX_TARGET_ONLY_MODELS: dict[str, str] = {
    "qwen3.8:27b-mtp-bf16": "Qwen 3.8 27B MTP (scan target default)",
    "ornith-1.5:35b": "Qwen-family MoE (scan target)",
    "deepseek-v4-flash-0731:ud-iq2-m": "DeepSeek V4 Flash (scan target)",
}

DEFAULT_DETECTION_MODEL = "muse-glimmer:30b-bf16"
DEFAULT_TARGET_MODEL = "qwen3.8:27b-mtp-bf16"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# Aliases that resolve to OLLAMA_MODEL / DEFAULT_DETECTION_MODEL.
DETECTION_ALIASES: frozenset[str] = frozenset(
    {"local", "ollama", "detection", "default", "auto", "vllm", ""}
)


def _normalize(model_id: str) -> str:
    return (model_id or "").strip()


def strip_ollama_prefix(model_id: str) -> str:
    """Drop ollama/ or ollama_chat/ so tags compare to `ollama list` names."""
    mid = _normalize(model_id)
    lower = mid.lower()
    for prefix in ("ollama_chat/", "ollama/"):
        if lower.startswith(prefix):
            return mid[len(prefix) :]
    return mid


def is_adversary_origin(model_id: str) -> bool:
    """True if the model id looks adversary-origin (block for detection roles)."""
    mid = _normalize(model_id).lower()
    if not mid:
        return False
    # Explicit US open / Meta local models
    if (
        "gpt-oss" in mid
        or "nemotron" in mid
        or "nvidia" in mid
        or "muse-glimmer" in mid
        or "muse_glimmer" in mid
    ):
        return False
    return any(marker in mid for marker in ADVERSARY_ORIGIN_MARKERS)


def is_allowed_detection_model(model_id: str) -> bool:
    """True if model may be used as compile / infer / agent brain."""
    mid = _normalize(model_id)
    if not mid:
        return False
    if is_adversary_origin(mid):
        return False
    if mid.lower() in DETECTION_ALIASES:
        return True
    return any(p.search(mid) for p in DETECTION_ALLOW_PATTERNS)


def assert_detection_model(model_id: str, *, role: str = "detection") -> str:
    """Raise ValueError if model_id is not allowed for the detection stack."""
    mid = _normalize(model_id)
    if mid.lower() in DETECTION_ALIASES:
        return mid
    if not is_allowed_detection_model(mid):
        raise ValueError(
            f"Model {mid!r} is not allowed for TSLIT {role} role.\n"
            "Detection stack must use non-adversary / American models "
            "(e.g. Meta Muse Glimmer, Llama, GPT-OSS, Nemotron).\n"
            "Qwen / DeepSeek / MiniMax / Moonshot / etc. are scan *targets* only — "
            "never the detector brain.\n"
            f"Local server: Ollama @ {DEFAULT_OLLAMA_BASE_URL}\n"
            f"Default detection tag: {DEFAULT_DETECTION_MODEL}"
        )
    return mid


def describe_policy() -> str:
    lines = [
        "TSLIT model-origin policy (detection stack)",
        "==========================================",
        "",
        "Local server: Ollama only (http://127.0.0.1:11434).",
        "",
        "ALLOWED for compile / inference / autoresearch brain:",
        "  - Meta Muse Glimmer (local Ollama default)",
        "  - Meta Llama, NVIDIA Nemotron, OpenAI GPT-OSS",
        "  - Anthropic Claude, xAI Grok, Amazon Nova, Google Gemini, Microsoft Phi",
        "  - Mistral (Western open; non-adversary)",
        "",
        "BLOCKED for detection stack (scan targets only):",
        "  " + ", ".join(ADVERSARY_ORIGIN_MARKERS[:12]) + ", …",
        "",
        "Ollama detection tags:",
    ]
    for tag, note in DGX_DETECTION_MODELS.items():
        lines.append(f"  {tag}  — {note}")
    lines.append("")
    lines.append("Ollama target-only tags (do not set as OLLAMA_MODEL for analyzer):")
    for tag, note in DGX_TARGET_ONLY_MODELS.items():
        lines.append(f"  {tag}  — {note}")
    return "\n".join(lines)


def filter_allowed(models: Iterable[str]) -> list[str]:
    return [m for m in models if is_allowed_detection_model(m)]
