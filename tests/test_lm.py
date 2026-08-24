"""LM factory helpers (no live completion)."""

from __future__ import annotations

from tslit_dspy.lm import ollama_chat_id, ollama_settings
from tslit_dspy.model_policy import DEFAULT_DETECTION_MODEL, DEFAULT_OLLAMA_BASE_URL


def test_ollama_chat_id_prefixes_tag() -> None:
    assert ollama_chat_id("muse-glimmer:30b-bf16") == "ollama_chat/muse-glimmer:30b-bf16"


def test_ollama_chat_id_normalizes_prefixes() -> None:
    assert ollama_chat_id("ollama/llama3.1") == "ollama_chat/llama3.1"
    assert ollama_chat_id("ollama_chat/llama3.1") == "ollama_chat/llama3.1"


def test_ollama_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    cfg = ollama_settings()
    assert cfg["base_url"] == DEFAULT_OLLAMA_BASE_URL
    assert cfg["openai_base_url"] == f"{DEFAULT_OLLAMA_BASE_URL}/v1"
    assert cfg["model"] == DEFAULT_DETECTION_MODEL


def test_ollama_settings_strips_v1(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    cfg = ollama_settings()
    assert cfg["base_url"] == "http://127.0.0.1:11434"
    assert cfg["openai_base_url"] == "http://127.0.0.1:11434/v1"
