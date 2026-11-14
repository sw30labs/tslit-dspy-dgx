"""Serving backends. Tests use MockBackend. Live clients are not constructed here
unless ``complete_live`` is called.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

_QUANT = re.compile(
    r"(bf16|fp16|fp32|fp8|int8|int4|iq\d+[a-z0-9_-]*|q\d+[a-z0-9_]*)",
    re.IGNORECASE,
)


@dataclass
class ProvenanceError(RuntimeError):
    """Raised when a live run requires a digest and the server did not return one."""


@dataclass
class Completion:
    text: str
    finish_reason: Optional[str]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    model_id: str
    quant: Optional[str]
    digest: Optional[str]
    backend: str
    backend_version: Optional[str]
    request_id: str
    raw_payload: Optional[dict[str, Any]] = None
    system_fingerprint: Optional[str] = None
    reasoning: Optional[str] = None


def parse_quant(model_id: str) -> Optional[str]:
    """Pull a quant token out of an Ollama-style tag. ``:latest`` is not a quant."""
    if not model_id or ":" not in model_id:
        return None
    tag = model_id.split(":", 1)[1]
    if tag == "latest":
        return None
    match = _QUANT.search(tag)
    return match.group(1).lower() if match else None


def digest_from_ollama_tags(payload: dict[str, Any], model_id: str) -> Optional[str]:
    wanted = {model_id}
    if ":" not in model_id:
        wanted.add(f"{model_id}:latest")
    for row in payload.get("models") or []:
        name = row.get("name") or row.get("model") or ""
        if name in wanted:
            digest = row.get("digest")
            return str(digest) if digest else None
    return None


def version_from_ollama(payload: dict[str, Any]) -> Optional[str]:
    version = payload.get("version")
    return str(version) if version else None


def digest_from_ollama_show(payload: dict[str, Any]) -> Optional[str]:
    """Digest from POST /api/show. Does not invent one when the field is absent."""
    for key in ("digest", "sha256"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    details = payload.get("details") or {}
    if isinstance(details, dict):
        for key in ("digest", "sha256"):
            value = details.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def digest_from_openai_models(payload: dict[str, Any], model_id: str) -> Optional[str]:
    for row in payload.get("data") or []:
        if not isinstance(row, dict):
            continue
        if row.get("id") != model_id:
            continue
        for key in ("digest", "sha256", "root"):
            value = row.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def openai_chat_body(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    top_p: float,
    max_tokens: int,
    seed: Optional[int],
    extra_body: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """JSON body. The request id is not a prompt field."""
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if seed is not None:
        body["seed"] = seed
    if extra_body:
        overlap = set(extra_body).intersection(body)
        if overlap:
            raise ValueError(f"extra_body collides with {sorted(overlap)}")
        body.update(extra_body)
    return body


def request_headers(request_id: str, api_key: Optional[str]) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Request-Id": request_id,
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def parse_openai_chat_response(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices") or [{}]
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    usage = payload.get("usage") or {}
    reasoning = message.get("reasoning") or message.get("reasoning_content") or choice.get("reasoning")
    return {
        "text": message.get("content") or "",
        "reasoning": reasoning if isinstance(reasoning, str) else None,
        "finish_reason": choice.get("finish_reason"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "model_id": payload.get("model"),
        "system_fingerprint": payload.get("system_fingerprint"),
    }


def provenance_ok(*, model_id: Optional[str], digest: Optional[str], require_digest: bool) -> bool:
    if not model_id:
        return False
    if require_digest and not digest:
        return False
    return True


class MockBackend:
    """Scripted backend. Token counts are whatever this backend reports."""

    def __init__(
        self,
        tasks: dict[str, Any],
        script: dict[str, Any],
        identity: dict[str, Any],
    ) -> None:
        self.tasks = tasks
        self.script = script
        self.identity = identity

    def kind_for(self, task_id: str, persona_id: str) -> str:
        for row in self.script.get("overrides") or []:
            if row["task"] == task_id and row["persona"] == persona_id:
                return str(row["response"])
        return str(self.script.get("default") or "reference")

    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        top_p: float,
        seed: Optional[int],
        max_tokens: int,
        request_id: str,
        task_id: str,
        persona_id: str,
    ) -> Completion:
        del temperature, top_p, seed, max_tokens
        kind = self.kind_for(task_id, persona_id)
        task = self.tasks[task_id]
        if kind == "reference":
            text = "```python\n" + task.reference_source + "```\n"
        elif kind == "buggy":
            parts = [
                f"def {name}(*args, **kwargs):\n    raise RuntimeError('bug')\n"
                for name in task.entrypoints
            ]
            text = "```python\n" + "\n".join(parts) + "```\n"
        elif kind == "refusal":
            text = "I'm sorry, but I can't assist with that."
        elif kind == "nocode":
            text = "Let's discuss the requirements in prose only."
        else:
            raise ValueError(f"unknown mock response {kind}")
        user = messages[-1]["content"]
        return Completion(
            text=text,
            finish_reason="stop",
            prompt_tokens=max(1, len(user) // 4),
            completion_tokens=max(1, len(text) // 4),
            model_id=str(self.identity["model_id"]),
            quant=self.identity.get("quant"),
            digest=self.identity.get("digest"),
            backend=str(self.identity.get("backend") or "mock"),
            backend_version=self.identity.get("backend_version"),
            request_id=request_id,
        )


def _read_json(url: str, timeout_s: float) -> dict[str, Any]:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object")
    return payload


def _post_json(url: str, body: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object")
    return payload


def fetch_ollama_identity(
    *,
    ollama_root: str,
    model_id: str,
    timeout_s: float = 5.0,
) -> dict[str, Any]:
    """Provenance from POST /api/show and GET /api/version.

    A missing digest stays missing. Callers that set require_digest abort.
    """
    root = ollama_root.rstrip("/")
    digest = None
    version = None
    quant = parse_quant(model_id)
    try:
        shown = _post_json(f"{root}/api/show", {"name": model_id}, timeout_s)
        digest = digest_from_ollama_show(shown)
        details = shown.get("details") or {}
        if isinstance(details, dict) and details.get("quantization_level"):
            quant = str(details["quantization_level"]).lower()
    except (OSError, ValueError, json.JSONDecodeError):
        digest = None
    try:
        version = version_from_ollama(_read_json(f"{root}/api/version", timeout_s))
    except (OSError, ValueError, json.JSONDecodeError):
        version = None
    return {
        "model_id": model_id,
        "quant": quant,
        "digest": digest,
        "backend": "ollama",
        "backend_version": version,
        "system_fingerprint": None,
    }


def fetch_openai_identity(
    *,
    base_url: str,
    model_id: str,
    api_key: Optional[str] = None,
    timeout_s: float = 5.0,
) -> dict[str, Any]:
    """Provenance from GET /v1/models. Fingerprint arrives on the chat response."""
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        models_url = f"{root}/models"
    else:
        models_url = f"{root}/v1/models"
    digest = None
    try:
        req = urllib.request.Request(models_url, headers=request_headers("identity", api_key))
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if isinstance(payload, dict):
            digest = digest_from_openai_models(payload, model_id)
    except (OSError, ValueError, json.JSONDecodeError):
        digest = None
    return {
        "model_id": model_id,
        "quant": parse_quant(model_id),
        "digest": digest,
        "backend": "openai_compat",
        "backend_version": None,
        "system_fingerprint": None,
    }


def post_chat(
    *,
    base_url: str,
    api_key: Optional[str],
    body: dict[str, Any],
    request_id: str,
    timeout_s: float,
) -> dict[str, Any]:
    """POST /chat/completions. Retries transport errors. The key is not returned."""
    import time

    url = base_url.rstrip("/") + "/chat/completions"
    data = json.dumps(body).encode("utf-8")
    delay = 0.25
    last: Exception | None = None
    for _attempt in range(4):
        req = urllib.request.Request(
            url,
            data=data,
            headers=request_headers(request_id, api_key),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("expected a JSON object")
            return payload
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(delay)
            delay *= 2
    assert last is not None
    raise last


def live_completion_from_payload(
    payload: dict[str, Any],
    *,
    fallback_model_id: str,
    quant: Optional[str],
    digest: Optional[str],
    backend: str,
    backend_version: Optional[str],
    request_id: str,
) -> Completion:
    parsed = parse_openai_chat_response(payload)
    return Completion(
        text=str(parsed["text"] or ""),
        finish_reason=parsed["finish_reason"],
        prompt_tokens=parsed["prompt_tokens"],
        completion_tokens=parsed["completion_tokens"],
        model_id=str(parsed["model_id"] or fallback_model_id),
        quant=quant,
        digest=digest,
        backend=backend,
        backend_version=backend_version,
        request_id=request_id,
        raw_payload=payload,
        system_fingerprint=parsed.get("system_fingerprint"),
        reasoning=parsed.get("reasoning"),
    )


def stable_request_id(*parts: str) -> str:
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:32]
