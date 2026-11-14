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
    }


def execute(
    spec: RunSpec,
    backend: Any,
    *,
    output_dir: Optional[Path] = None,
    run_static: bool = True,
) -> list[dict[str, Any]]:
    """Run every cell. Writes JSONL only when ``output_dir`` is set.

    This path does not call the Magika durable-write gate. Drift artifacts are
    outside the five campaign choke families.
    """
    ordered = order_cells(spec.cells, seed=spec.master_seed, randomize=spec.randomize_order)
    records: list[dict[str, Any]] = []
    for order_index, cell in enumerate(ordered):
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
        seed = derive_seed(spec.master_seed, cell.cell_id, cell.repeat_index)
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
        records.append(record)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "records.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        meta = {
            "instrument": spec.name,
            "backend": spec.backend,
            "master_seed": spec.master_seed,
            "n_records": len(records),
            "model_id": records[0]["model_id"] if records else None,
            "model_digest": records[0]["model_digest"] if records else None,
        }
        (output_dir / "run_meta.json").write_text(
            json.dumps(meta, indent=2) + "\n",
            encoding="utf-8",
        )
    return records


def mock_backend_for(spec: RunSpec) -> MockBackend:
    if spec.backend != "mock":
        raise ValueError(f"spec backend is {spec.backend}, not mock")
    if spec.mock_script is None or spec.mock_identity is None:
        raise ValueError("mock spec is missing mock_script or mock_identity")
    return MockBackend(spec.tasks, spec.mock_script, spec.mock_identity)


def live_backend_for(spec: RunSpec) -> LiveChatBackend:
    """Build a live client from the spec. Reads the API key from the environment."""
    if spec.backend == "mock":
        raise ValueError("mock spec has no live backend")
    api_key = os.environ.get(spec.api_key_env) if spec.api_key_env else None
    if spec.backend == "ollama" and not api_key:
        api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
    model_id = spec.model_id or os.environ.get("DRIFT_TARGET_MODEL") or ""
    base = spec.base_url or os.environ.get("OPENAI_BASE_URL") or ""
    if not model_id or not base:
        raise ValueError("live run needs model_id and base_url")
    return LiveChatBackend(
        base_url=base,
        model_id=model_id,
        api_key=api_key,
        backend_name=spec.backend,
        quant=parse_quant(model_id),
        digest=None,
        backend_version=None,
        extra_body=spec.extra_body,
        send_seed=spec.send_seed,
    )
