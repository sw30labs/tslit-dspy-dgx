"""Unit tests for non-adversary detection model policy."""

from __future__ import annotations

import pytest

from tslit_dspy.model_policy import (
    DEFAULT_DETECTION_MODEL,
    DEFAULT_TARGET_MODEL,
    assert_detection_model,
    is_adversary_origin,
    is_allowed_detection_model,
    strip_ollama_prefix,
)


@pytest.mark.parametrize(
    "model_id",
    [
        "muse-glimmer:30b-bf16",
        "ollama_chat/muse-glimmer:30b-bf16",
        "ollama/llama3.1",
        "ollama_chat/llama3.1",
        "openai/gpt-oss-120b",
        "meta-llama/Llama-3.3-70B-Instruct",
        "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
    ],
)
def test_allowed_detection_models(model_id: str) -> None:
    assert is_allowed_detection_model(model_id)
    assert assert_detection_model(model_id) == model_id


@pytest.mark.parametrize(
    "model_id",
    [
        "qwen3.8:27b-mtp-bf16",
        "ollama_chat/qwen3.8:27b-mtp-bf16",
        "Qwen/Qwen3.6-27B-FP8",
        "deepseek-v4-flash-0731:ud-iq2-m",
        "ornith-1.5:35b",
        "ollama_chat/qwen2.5",
        "moonshotai/kimi-k2.6",
        "minimax/MiniMax-Text",
    ],
)
def test_blocked_adversary_models(model_id: str) -> None:
    assert is_adversary_origin(model_id)
    assert not is_allowed_detection_model(model_id)
    with pytest.raises(ValueError, match="not allowed"):
        assert_detection_model(model_id)


def test_default_detection_model_is_muse_glimmer() -> None:
    assert "muse-glimmer" in DEFAULT_DETECTION_MODEL.lower()
    assert is_allowed_detection_model(DEFAULT_DETECTION_MODEL)


def test_default_target_is_qwen() -> None:
    assert "qwen" in DEFAULT_TARGET_MODEL.lower()
    assert is_adversary_origin(DEFAULT_TARGET_MODEL)
    assert not is_allowed_detection_model(DEFAULT_TARGET_MODEL)


def test_aliases_are_allowed() -> None:
    for alias in ("local", "ollama", "detection", "default", "vllm"):
        assert is_allowed_detection_model(alias)
        assert assert_detection_model(alias) == alias


def test_strip_ollama_prefix() -> None:
    assert strip_ollama_prefix("ollama_chat/muse-glimmer:30b-bf16") == "muse-glimmer:30b-bf16"
    assert strip_ollama_prefix("ollama/llama3.1") == "llama3.1"
    assert strip_ollama_prefix("muse-glimmer:30b-bf16") == "muse-glimmer:30b-bf16"
