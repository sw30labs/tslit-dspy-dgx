"""Unit tests for non-adversary detection model policy."""

from __future__ import annotations

import pytest

from tslit_dspy.model_policy import (
    DEFAULT_DETECTION_MODEL,
    assert_detection_model,
    is_adversary_origin,
    is_allowed_detection_model,
)


@pytest.mark.parametrize(
    "model_id",
    [
        "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
        "openai/gpt-oss-120b",
        "anthropic/claude-opus-4-6",
        "anthropic/claude-sonnet-4-6",
        "openai/gpt-4o",
        "meta-llama/Llama-3.3-70B-Instruct",
        "xai/grok-4",
        "ollama_chat/llama3.1",
    ],
)
def test_allowed_detection_models(model_id: str) -> None:
    assert is_allowed_detection_model(model_id)
    assert assert_detection_model(model_id) == model_id


@pytest.mark.parametrize(
    "model_id",
    [
        "Qwen/Qwen3.6-27B-FP8",
        "Qwen/Qwen3-Coder-Next-FP8",
        "deepseek-ai/DeepSeek-R1",
        "moonshotai/kimi-k2.6",
        "minimax/MiniMax-Text",
        "ollama_chat/qwen2.5",
    ],
)
def test_blocked_adversary_models(model_id: str) -> None:
    assert is_adversary_origin(model_id)
    assert not is_allowed_detection_model(model_id)
    with pytest.raises(ValueError, match="not allowed"):
        assert_detection_model(model_id)


def test_default_detection_model_is_nemotron() -> None:
    assert "nemotron" in DEFAULT_DETECTION_MODEL.lower()
    assert "nvidia" in DEFAULT_DETECTION_MODEL.lower()
