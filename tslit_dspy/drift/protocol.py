"""Build the factorial cell list from a YAML config. Does not call a model."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from tslit_dspy.drift.bank import load_tasks
from tslit_dspy.drift.bank.model import CodingTask
from tslit_dspy.drift.labels import Persona, load_personas
from tslit_dspy.drift.prompts import PromptSkeleton, load_prompts

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Profile:
    name: str
    temperature: float
    repeats: int


@dataclass(frozen=True)
class Cell:
    cell_id: str
    task_id: str
    persona_id: str
    template_id: str
    position: str
    profile: str
    temperature: float
    repeat_index: int
    slice_name: str


@dataclass
class RunSpec:
    name: str
    backend: str
    master_seed: int
    randomize_order: bool
    cells: list[Cell]
    top_p: float
    max_tokens: int
    send_seed: bool
    virtual_clock: Optional[str]
    require_digest: bool
    sandbox_timeout_s: float
    block_network: bool
    extra_body: dict[str, Any]
    mock_script: Optional[dict[str, Any]]
    mock_identity: Optional[dict[str, Any]]
    model_id: Optional[str]
    base_url: Optional[str]
    ollama_root: Optional[str]
    api_key_env: Optional[str]
    tasks: dict[str, CodingTask]
    personas: dict[str, Persona]
    skeleton: PromptSkeleton


def derive_seed(master: int, cell_id: str, repeat_index: int) -> int:
    digest = hashlib.sha256(f"{master}|{cell_id}|{repeat_index}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1)


def order_cells(cells: list[Cell], *, seed: int, randomize: bool) -> list[Cell]:
    ordered = list(cells)
    if randomize:
        random.Random(seed).shuffle(ordered)
    return ordered


def _profiles_from_map(raw: dict[str, Any]) -> list[Profile]:
    profiles = []
    for name, row in raw.items():
        profiles.append(
            Profile(name=str(name), temperature=float(row["temperature"]), repeats=int(row["repeats"]))
        )
    return profiles


def _append(
    cells: list[Cell],
    *,
    tasks: list[CodingTask],
    personas: list[Persona],
    template_ids: list[str],
    positions: list[str],
    profiles: list[Profile],
    slice_name: str,
) -> None:
    for task in tasks:
        for persona in personas:
            for template_id in template_ids:
                for position in positions:
                    for profile in profiles:
                        for repeat in range(profile.repeats):
                            cell_id = (
                                f"{task.task_id}__{persona.persona_id}__{template_id}"
                                f"__{position}__{profile.name}__r{repeat}"
                            )
                            cells.append(
                                Cell(
                                    cell_id=cell_id,
                                    task_id=task.task_id,
                                    persona_id=persona.persona_id,
                                    template_id=template_id,
                                    position=position,
                                    profile=profile.name,
                                    temperature=profile.temperature,
                                    repeat_index=repeat,
                                    slice_name=slice_name,
                                )
                            )


def _select_personas(all_personas: list[Persona], spec: Any) -> list[Persona]:
    if spec == "all" or spec is None:
        return list(all_personas)
    if isinstance(spec, dict):
        wanted = set(spec.values())
        return [p for p in all_personas if p.persona_id in wanted]
    if isinstance(spec, list):
        wanted = set(spec)
        return [p for p in all_personas if p.persona_id in wanted]
    raise ValueError(f"cannot select personas from {spec!r}")


def load_run_spec(path: Path | str) -> RunSpec:
    doc_path = Path(path)
    data = yaml.safe_load(doc_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported drift config {doc_path}")
    if data.get("protocol") and "tasks" not in data and "primary_slice" not in data:
        protocol_path = (doc_path.parent / data["protocol"]).resolve() if not Path(data["protocol"]).is_absolute() else Path(data["protocol"])
        if not protocol_path.is_file():
            protocol_path = (ROOT / data["protocol"]).resolve()
        protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
        merged = dict(protocol)
        merged.update({k: v for k, v in data.items() if k != "protocol"})
        data = merged
    tasks = {t.task_id: t for t in load_tasks()}
    personas = {p.persona_id: p for p in load_personas()}
    skeleton = load_prompts()
    if "primary_slice" in data:
        cells: list[Cell] = []
        primary = data["primary_slice"]
        profiles = [
            profile
            for profile in _profiles_from_map(data["decoding"]["profiles"])
            if profile.name in set(primary["profiles"])
        ]
        _append(
            cells,
            tasks=list(tasks.values()),
            personas=_select_personas(list(personas.values()), primary.get("personas")),
            template_ids=list(primary["templates"]),
            positions=list(primary["positions"]),
            profiles=profiles,
            slice_name="primary",
        )
        audit = data.get("lexical_audit") or {}
        if audit.get("enabled"):
            audit_profiles = [
                profile
                for profile in _profiles_from_map(data["decoding"]["profiles"])
                if profile.name in set(audit["profiles"])
            ]
            _append(
                cells,
                tasks=list(tasks.values()),
                personas=_select_personas(list(personas.values()), audit.get("personas")),
                template_ids=list(audit["templates"]),
                positions=list(audit["positions"]),
                profiles=audit_profiles,
                slice_name="lexical_audit",
            )
        sandbox = data.get("sandbox") or {}
        return RunSpec(
            name=str(data.get("instrument") or "adversary-drift-v2"),
            backend=str(data.get("backend") or "unspecified"),
            master_seed=int(data["master_seed"]),
            randomize_order=bool(data.get("randomize_order", True)),
            cells=cells,
            top_p=float(data["decoding"]["top_p"]),
            max_tokens=int(data["decoding"]["max_tokens"]),
            send_seed=bool(data["decoding"].get("send_seed", True)),
            virtual_clock=data.get("virtual_clock_utc"),
            require_digest=bool(data.get("require_digest", True)),
            sandbox_timeout_s=float(sandbox.get("timeout_s", 8)),
            block_network=bool(sandbox.get("block_network", True)),
            extra_body=dict(data.get("extra_body") or {}),
            mock_script=None,
            mock_identity=None,
            model_id=data.get("model_id"),
            base_url=data.get("base_url"),
            ollama_root=data.get("ollama_root"),
            api_key_env=data.get("api_key_env"),
            tasks=tasks,
            personas=personas,
            skeleton=skeleton,
        )
    # Smoke / explicit slice.
    selected_tasks = [tasks[task_id] for task_id in data["tasks"]]
    selected_personas = [personas[persona_id] for persona_id in data["personas"]]
    profiles = [
        Profile(name=str(row["name"]), temperature=float(row["temperature"]), repeats=int(row["repeats"]))
        for row in data["profiles"]
    ]
    cells = []
    _append(
        cells,
        tasks=selected_tasks,
        personas=selected_personas,
        template_ids=list(data["templates"]),
        positions=list(data["positions"]),
        profiles=profiles,
        slice_name="smoke",
    )
    sandbox = data.get("sandbox") or {}
    return RunSpec(
        name="smoke",
        backend=str(data["backend"]),
        master_seed=int(data["master_seed"]),
        randomize_order=bool(data.get("randomize_order", True)),
        cells=cells,
        top_p=float(data["top_p"]),
        max_tokens=int(data["max_tokens"]),
        send_seed=bool(data.get("send_seed", True)),
        virtual_clock=data.get("virtual_clock_utc"),
        require_digest=bool(data.get("require_digest", False)),
        sandbox_timeout_s=float(sandbox.get("timeout_s", 8)),
        block_network=bool(sandbox.get("block_network", True)),
        extra_body=dict(data.get("extra_body") or {}),
        mock_script=data.get("mock_script"),
        mock_identity=data.get("mock_identity"),
        model_id=data.get("model_id"),
        base_url=data.get("base_url"),
        ollama_root=data.get("ollama_root"),
        api_key_env=data.get("api_key_env"),
        tasks=tasks,
        personas=personas,
        skeleton=skeleton,
    )
