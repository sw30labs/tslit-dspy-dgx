"""Execute a prepared cell list. Live HTTP is opt-in via LiveChatBackend."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from tslit_dspy.drift.backends import (
    Completion,
    MockBackend,
    live_completion_from_payload,
    openai_chat_body,
    parse_quant,
    post_chat,
    provenance_ok,
    stable_request_id,
)
from tslit_dspy.drift.detectors import detector_flags
from tslit_dspy.drift.prompts import render_messages
from tslit_dspy.drift.protocol import Cell, RunSpec, derive_seed, order_cells
from tslit_dspy.drift.scoring import score_response


def messages_sha256(messages: list[dict[str, str]]) -> tuple[str, int]:
    blob = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(blob)


class LiveChatBackend:
    """OpenAI-compatible chat. Constructing it does not open a socket."""

    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        api_key: Optional[str],
        backend_name: str,
        quant: Optional[str],
        digest: Optional[str],
        backend_version: Optional[str],
        extra_body: dict[str, Any],
        send_seed: bool,
        timeout_s: float = 120.0,
    ) -> None:
        self.base_url = base_url
        self.model_id = model_id
        self.api_key = api_key
        self.backend_name = backend_name
        self.quant = quant
        self.digest = digest
        self.backend_version = backend_version
        self.extra_body = extra_body
        self.send_seed = send_seed
        self.timeout_s = timeout_s

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
        del task_id, persona_id
        body = openai_chat_body(
            model=self.model_id,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed if self.send_seed else None,
            extra_body=self.extra_body,
        )
        payload = post_chat(
            base_url=self.base_url,
            api_key=self.api_key,
            body=body,
            request_id=request_id,
            timeout_s=self.timeout_s,
        )
        return live_completion_from_payload(
            payload,
            fallback_model_id=self.model_id,
            quant=self.quant if self.quant is not None else parse_quant(self.model_id),
            digest=self.digest,
            backend=self.backend_name,
            backend_version=self.backend_version,
            request_id=request_id,
        )


def _record(
    *,
    spec: RunSpec,
    cell: Cell,
    order_index: int,
    messages: list[dict[str, str]],
    completion: Completion,
    score: dict[str, Any],
    seed: int,
    started: str,
    finished: str,
) -> dict[str, Any]:
    persona = spec.personas[cell.persona_id]
    digest, nbytes = messages_sha256(messages)
    user = messages[1]["content"]
    system = messages[0]["content"]
    flags = detector_flags(
        completion.text,
        slot_text=persona.slot_text,
        stratum=persona.stratum,
    )
    static = score.get("static") or {}
    return {
        "record_id": cell.cell_id,
        "order_index": order_index,
        "slice_name": cell.slice_name,
        "task_id": cell.task_id,
        "persona_id": cell.persona_id,
        "stratum": persona.stratum,
        "alignment_clarity": persona.alignment_clarity,
        "country": persona.country,
        "bloc": persona.bloc,
        "template_id": cell.template_id,
        "position": cell.position,
        "profile": cell.profile,
        "repeat_index": cell.repeat_index,
        "temperature": cell.temperature,
        "top_p": spec.top_p,
        "seed": seed,
        "seed_sent": spec.send_seed,
        "max_tokens": spec.max_tokens,
        "model_id": completion.model_id,
        "quant": completion.quant,
        "model_digest": completion.digest,
        "backend": completion.backend,
        "backend_version": completion.backend_version,
        "provenance_ok": provenance_ok(
            model_id=completion.model_id,
            digest=completion.digest,
            require_digest=spec.require_digest,
        ),
        "request_id": completion.request_id,
        "system_prompt": system,
        "system_prompt_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
        "rendered_prompt": user,
        "rendered_prompt_bytes": len(user.encode("utf-8")),
        "messages_sha256": digest,
        "messages_bytes": nbytes,
        "virtual_clock_utc": spec.virtual_clock,
        "started_at": started,
        "finished_at": finished,
        "prompt_tokens": completion.prompt_tokens,
        "completion_tokens": completion.completion_tokens,
        "finish_reason": completion.finish_reason,
        "response_text": completion.text,
        "slot_chars": persona.slot_chars,
        "detector_flags": flags,
        "outcome": score["outcome"],
        "buggy": score["buggy"],
        "refused_no_code": score["refused_no_code"],
        "no_code": score["no_code"],
        "refusal_prose": score["refusal_prose"],
        "code_extracted": score["code_extracted"],
        "tests_passed": score["tests_passed"],
        "tests_passed_n": score["tests_passed_n"],
        "tests_failed_n": score["tests_failed_n"],
        "response_chars": score["response_chars"],
        "ruff_count": (static.get("ruff") or {}).get("count"),
        "pyflakes_count": (static.get("pyflakes") or {}).get("count"),
        "bandit_count": (static.get("bandit") or {}).get("count"),
        "bandit_status": (static.get("bandit") or {}).get("status"),
        "security_pattern_hits": (static.get("security_pattern_hits")),
        "not_correct": score.get("not_correct"),
        "harness_error": score.get("harness_error"),
        "truncated": score.get("truncated"),
        "extraction_method": score.get("extraction_method"),
        "fence_count": score.get("fence_count"),
        "sandbox_backend": score.get("sandbox_backend"),
        "reasoning": completion.reasoning,
        "system_fingerprint": completion.system_fingerprint,
        "response_raw": _raw_response(completion),
        "keep_alive": spec.keep_alive,
        "num_ctx": spec.num_ctx,
    }


def _raw_response(completion: Completion) -> dict[str, Any]:
    """Server payload fields that describe the completion. No credentials."""
    if completion.raw_payload:
        choice = ((completion.raw_payload.get("choices") or [{}])[0]) or {}
        message = choice.get("message") or {}
        return {
            "finish_reason": choice.get("finish_reason"),
            "message": {
                "content": message.get("content"),
                "reasoning": message.get("reasoning") or message.get("reasoning_content"),
            },
            "system_fingerprint": completion.raw_payload.get("system_fingerprint"),
        }
    return {
        "finish_reason": completion.finish_reason,
        "message": {"content": completion.text, "reasoning": completion.reasoning},
        "system_fingerprint": completion.system_fingerprint,
    }


def _completed_ids(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.is_file():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            done.add(str(json.loads(line)["record_id"]))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return done


def execute(
    spec: RunSpec,
    backend: Any,
    *,
    output_dir: Optional[Path] = None,
    run_static: bool = True,
    run_id: Optional[str] = None,
    unsafe_sandbox: bool = False,
) -> list[dict[str, Any]]:
    """Run every cell. Appends each record before the next request.

    A live backend refuses the weak sandbox unless ``unsafe_sandbox`` is set.
    Passing ``run_id`` again resumes cells whose ids are already in the jsonl.
    """
    from tslit_dspy.drift.sandbox import strong_backend

    if spec.backend != "mock" and not unsafe_sandbox and strong_backend() is None:
        raise RuntimeError(
            "refusing a live run under the weak sandbox; pass --unsafe-sandbox to override"
        )
    ordered = order_cells(spec.cells, seed=spec.master_seed, randomize=spec.randomize_order)
    records: list[dict[str, Any]] = []
    handle = None
    record_path: Optional[Path] = None
    if output_dir is not None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = output_dir / (run_id or f"{spec.master_seed}-{stamp}")
        dest.mkdir(parents=True, exist_ok=True)
        record_path = dest / "records.jsonl"
        done = _completed_ids(record_path)
        handle = record_path.open("a", encoding="utf-8")
        for line in record_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    else:
        done = set()
    try:
        for order_index, cell in enumerate(ordered):
            if cell.cell_id in done:
                continue
            record = _run_cell(
                spec,
                backend,
                cell,
                order_index=order_index,
                run_static=run_static,
            )
            records.append(record)
            if handle is not None:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
    finally:
        if handle is not None:
            handle.close()
    if record_path is not None:
        meta = {
            "instrument": spec.name,
            "backend": spec.backend,
            "master_seed": spec.master_seed,
            "n_records": len(records),
            "run_dir": str(record_path.parent),
            "model_id": records[0]["model_id"] if records else None,
            "model_digest": records[0]["model_digest"] if records else None,
            "keep_alive": spec.keep_alive,
            "num_ctx": spec.num_ctx,
        }
        (record_path.parent / "run_meta.json").write_text(
            json.dumps(meta, indent=2) + "\n",
            encoding="utf-8",
        )
    return records


def _run_cell(
    spec: RunSpec,
    backend: Any,
    cell: Cell,
    *,
    order_index: int,
    run_static: bool,
) -> dict[str, Any]:
    task = spec.tasks[cell.task_id]
    persona = spec.personas[cell.persona_id]
    template = spec.skeleton.template(cell.template_id)
    messages = render_messages(
        skeleton=spec.skeleton,
        task=task,
        persona=persona,
        template=template,
        position=cell.position,
        virtual_clock=spec.virtual_clock,
    )
    seed_repeat = 0 if cell.slice_name == "determinism" else cell.repeat_index
    seed = derive_seed(
        spec.master_seed,
        task_id=cell.task_id,
        template_id=cell.template_id,
        position=cell.position,
        profile=cell.profile,
        repeat_index=seed_repeat,
    )
    request_id = stable_request_id(str(spec.master_seed), cell.cell_id, str(order_index))
    started = datetime.now(timezone.utc).isoformat()
    completion = backend.complete(
        messages=messages,
        temperature=cell.temperature,
        top_p=spec.top_p,
        seed=seed if spec.send_seed else None,
        max_tokens=spec.max_tokens,
        request_id=request_id,
        task_id=cell.task_id,
        persona_id=cell.persona_id,
    )
    score = score_response(
        task,
        completion.text,
        timeout_s=spec.sandbox_timeout_s,
        block_network=spec.block_network,
        run_static=run_static,
        finish_reason=completion.finish_reason,
    )
    finished = datetime.now(timezone.utc).isoformat()
    record = _record(
        spec=spec,
        cell=cell,
        order_index=order_index,
        messages=messages,
        completion=completion,
        score=score,
        seed=seed,
        started=started,
        finished=finished,
    )
    return record


def mock_backend_for(spec: RunSpec) -> MockBackend:
    if spec.backend != "mock":
        raise ValueError(f"spec backend is {spec.backend}, not mock")
    if spec.mock_script is None or spec.mock_identity is None:
        raise ValueError("mock spec is missing mock_script or mock_identity")
    return MockBackend(spec.tasks, spec.mock_script, spec.mock_identity)


def resolve_live_target(spec: RunSpec) -> tuple[str, str]:
    """Model id and base URL, including the env names on the OpenAI-compat config."""
    model = ""
    if spec.model_id_env and os.environ.get(spec.model_id_env):
        model = os.environ[spec.model_id_env]
    if not model:
        model = spec.model_id or ""
    if not model:
        model = os.environ.get("DRIFT_TARGET_MODEL", "")
    base = spec.base_url or ""
    if spec.base_url_env and os.environ.get(spec.base_url_env):
        base = os.environ[spec.base_url_env]
    if not base and spec.backend == "ollama":
        root = spec.ollama_root or "http://127.0.0.1:11434"
        base = root.rstrip("/") + "/v1"
    if not base:
        base = os.environ.get("OPENAI_BASE_URL", "")
    return model, base


def live_backend_for(spec: RunSpec) -> LiveChatBackend:
    """Fetch identity, then build the client. Aborts when a required digest is missing."""
    from tslit_dspy.drift.backends import ProvenanceError, fetch_ollama_identity, fetch_openai_identity

    if spec.backend == "mock":
        raise ValueError("mock spec has no live backend")
    api_key = os.environ.get(spec.api_key_env) if spec.api_key_env else None
    if spec.backend == "ollama" and not api_key:
        api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
    model_id, base = resolve_live_target(spec)
    if not model_id or not base:
        raise ValueError("live run needs model_id and base_url")
    if spec.backend == "ollama":
        root = spec.ollama_root or base.removesuffix("/v1")
        identity = fetch_ollama_identity(ollama_root=root, model_id=model_id)
    else:
        identity = fetch_openai_identity(base_url=base, model_id=model_id, api_key=api_key)
    if spec.require_digest and not identity.get("digest"):
        raise ProvenanceError(
            f"require_digest is set and {spec.backend} did not return a digest for {model_id}"
        )
    extra = dict(spec.extra_body)
    if spec.keep_alive is not None:
        extra["keep_alive"] = spec.keep_alive
    if spec.num_ctx is not None:
        options = dict(extra.get("options") or {})
        options["num_ctx"] = spec.num_ctx
        extra["options"] = options
    return LiveChatBackend(
        base_url=base,
        model_id=model_id,
        api_key=api_key,
        backend_name=spec.backend,
        quant=identity.get("quant") or parse_quant(model_id),
        digest=identity.get("digest"),
        backend_version=identity.get("backend_version"),
        extra_body=extra,
        send_seed=spec.send_seed,
    )
