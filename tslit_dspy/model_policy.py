"""
Model-origin policy for TSLIT-DSPy on DGX.

Hard rule (from project design / whitepaper):
  Detection infrastructure (compile, inference, autoresearch brain) must use
  non-adversary / American-origin models. Adversary-origin open-weight models
  (Qwen, DeepSeek, MiniMax, …) are *scan targets only* — never part of the
  detector stack.

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
        r"meta-llama",
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

# Recipes on this DGX that are approved for the detection brain.
DGX_DETECTION_RECIPES: dict[str, str] = {
    "nemotron-super": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
}

# Recipes that exist on the shared Desktop vLLM stack but must NOT run the detector.
DGX_TARGET_ONLY_RECIPES: dict[str, str] = {
    "qwen27": "Qwen/Qwen3.6-27B-FP8",
    "coder-next": "Qwen/Qwen3-Coder-Next-FP8",
}

DEFAULT_DETECTION_MODEL = DGX_DETECTION_RECIPES["nemotron-super"]
DEFAULT_VLLM_BASE_URL = "http://127.0.0.1:8000/v1"


def _normalize(model_id: str) -> str:
    return (model_id or "").strip()


def is_adversary_origin(model_id: str) -> bool:
    """True if the model id looks adversary-origin (block for detection roles)."""
    mid = _normalize(model_id).lower()
    if not mid:
        return False
    # Explicit US open validation model
    if "gpt-oss" in mid or "nemotron" in mid or "nvidia" in mid:
        return False
    return any(marker in mid for marker in ADVERSARY_ORIGIN_MARKERS)


def is_allowed_detection_model(model_id: str) -> bool:
    """True if model may be used as compile / infer / agent brain."""
    mid = _normalize(model_id)
    if not mid:
        return False
    if is_adversary_origin(mid):
        return False
    # Aliases used by this port
    if mid in {"local", "vllm", "detection", "default"}:
        return True
    return any(p.search(mid) for p in DETECTION_ALLOW_PATTERNS)


def assert_detection_model(model_id: str, *, role: str = "detection") -> str:
    """Raise ValueError if model_id is not allowed for the detection stack."""
    mid = _normalize(model_id)
    if mid in {"local", "vllm", "detection", "default"}:
        return mid
    if not is_allowed_detection_model(mid):
        raise ValueError(
            f"Model {mid!r} is not allowed for TSLIT {role} role.\n"
            "Detection stack must use non-adversary / American models "
            "(e.g. NVIDIA Nemotron, GPT-OSS, Claude, OpenAI, Llama, Grok).\n"
            "Qwen / DeepSeek / MiniMax / Moonshot / etc. are scan *targets* only — "
            "never the detector brain.\n"
            f"Approved local DGX recipe: ~/Desktop/start-vllm.sh nemotron-super\n"
            f"Default model id: {DEFAULT_DETECTION_MODEL}"
        )
    return mid


def describe_policy() -> str:
    lines = [
        "TSLIT model-origin policy (detection stack)",
        "==========================================",
        "",
        "ALLOWED for compile / inference / autoresearch brain:",
        "  - NVIDIA Nemotron (local DGX default)",
        "  - OpenAI GPT-OSS / GPT-4/5 (US)",
        "  - Anthropic Claude (US)",
        "  - Meta Llama (US)",
        "  - xAI Grok (US)",
        "  - Amazon Nova, Google Gemini, Microsoft Phi (US cloud)",
        "  - Mistral (Western open; non-adversary)",
        "",
        "BLOCKED for detection stack (scan targets only):",
        "  " + ", ".join(ADVERSARY_ORIGIN_MARKERS[:12]) + ", …",
        "",
        "DGX local detection recipe:",
        f"  start-vllm.sh nemotron-super → {DEFAULT_DETECTION_MODEL}",
        "",
        "DGX local target-only recipes (do not set as VLLM_MODEL for analyzer):",
    ]
    for recipe, mid in DGX_TARGET_ONLY_RECIPES.items():
        lines.append(f"  {recipe} → {mid}")
    return "\n".join(lines)


def filter_allowed(models: Iterable[str]) -> list[str]:
    return [m for m in models if is_allowed_detection_model(m)]
