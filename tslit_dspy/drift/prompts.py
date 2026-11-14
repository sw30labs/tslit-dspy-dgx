"""Render matched-swap prompts. Only the affiliation slot changes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from tslit_dspy.drift.bank.model import CodingTask
from tslit_dspy.drift.labels import Persona

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_PATH = ROOT / "config" / "drift" / "prompts.yaml"

SLOT_MARK = "«SLOT»"


@dataclass(frozen=True)
class Template:
    template_id: str
    sentence: str


@dataclass(frozen=True)
class PromptSkeleton:
    system: str
    closing: str
    virtual_clock_line: str
    templates: tuple[Template, ...]
    positions: tuple[str, ...]

    def template(self, template_id: str) -> Template:
        for item in self.templates:
            if item.template_id == template_id:
                return item
        raise KeyError(template_id)


def load_prompts(path: Optional[Path] = None) -> PromptSkeleton:
    doc_path = Path(path) if path else PROMPTS_PATH
    data = yaml.safe_load(doc_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported prompt schema in {doc_path}")
    templates = tuple(
        Template(template_id=str(row["id"]), sentence=str(row["sentence"]))
        for row in data["templates"]
    )
    if not templates:
        raise ValueError("no templates")
    for item in templates:
        if "{slot}" not in item.sentence:
            raise ValueError(f"{item.template_id} has no {{slot}}")
        if item.sentence.count("{slot}") != 1:
            raise ValueError(f"{item.template_id} must contain {{slot}} once")
    positions = tuple(str(p) for p in data["positions"])
    if set(positions) != {"prefix", "suffix"}:
        raise ValueError("positions must be prefix and suffix")
    return PromptSkeleton(
        system=str(data["system"]).strip(),
        closing=str(data["closing"]).strip(),
        virtual_clock_line=str(data["virtual_clock_line"]).strip(),
        templates=templates,
        positions=positions,
    )


def render_system(skeleton: PromptSkeleton, virtual_clock: Optional[str]) -> str:
    text = skeleton.system
    if virtual_clock:
        text = text + "\n" + skeleton.virtual_clock_line.format(date=virtual_clock)
    return text + "\n"


def render_user(
    *,
    skeleton: PromptSkeleton,
    task: CodingTask,
    template: Template,
    position: str,
    slot_text: Optional[str],
) -> str:
    if position not in {"prefix", "suffix"}:
        raise ValueError(position)
    sentence = None
    if slot_text is not None:
        sentence = template.sentence.format(slot=slot_text)
    blocks: list[str] = []
    if position == "prefix" and sentence:
        blocks.append(sentence)
    blocks.append(task.prompt.strip())
    if position == "suffix" and sentence:
        blocks.append(sentence)
    blocks.append(skeleton.closing)
    return "\n\n".join(blocks) + "\n"


def render_messages(
    *,
    skeleton: PromptSkeleton,
    task: CodingTask,
    persona: Persona,
    template: Template,
    position: str,
    virtual_clock: Optional[str] = None,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": render_system(skeleton, virtual_clock)},
        {
            "role": "user",
            "content": render_user(
                skeleton=skeleton,
                task=task,
                template=template,
                position=position,
                slot_text=persona.slot_text,
            ),
        },
    ]


def normalize_slot(user_text: str, slot_text: Optional[str]) -> str:
    """Replace the single affiliation slot so two renders can be compared."""
    if slot_text is None:
        return user_text
    count = user_text.count(slot_text)
    if count != 1:
        raise AssertionError(f"slot {slot_text!r} appears {count} times")
    return user_text.replace(slot_text, SLOT_MARK, 1)
