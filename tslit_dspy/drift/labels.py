"""Load the persona label schema. The YAML file is the source of truth."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

ROOT = Path(__file__).resolve().parents[2]
PERSONAS_PATH = ROOT / "config" / "drift" / "personas.yaml"

STRATA = ("adversary", "aligned", "self", "neutral", "placebo", "none")
CLARITY = ("high", "moderate", "not_applicable")


@dataclass(frozen=True)
class Persona:
    persona_id: str
    slot_text: Optional[str]
    country: Optional[str]
    bloc: Optional[str]
    relation_to_model_origin: str
    org_kind: str
    alignment_clarity: str
    length_band: str
    redaction_spans: tuple[str, ...]
    model_origin: str

    @property
    def stratum(self) -> str:
        return self.relation_to_model_origin

    @property
    def slot_chars(self) -> int:
        return 0 if self.slot_text is None else len(self.slot_text)


def _band(n_chars: int, *, short_max: int, long_min: int, slot_present: bool) -> str:
    if not slot_present:
        return "none"
    if n_chars <= short_max:
        return "short"
    if n_chars >= long_min:
        return "long"
    return "medium"


def load_label_document(path: Optional[Path] = None) -> dict[str, Any]:
    doc_path = Path(path) if path else PERSONAS_PATH
    data = yaml.safe_load(doc_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError(f"unsupported persona schema in {doc_path}")
    return data


def load_personas(path: Optional[Path] = None) -> tuple[Persona, ...]:
    data = load_label_document(path)
    short_max = int(data["length_bands"]["short_max"])
    long_min = int(data["length_bands"]["long_min"])
    origin = str(data["model_origin"])
    personas: list[Persona] = []
    for row in data["personas"]:
        slot = row["slot_text"]
        if slot is not None and (not isinstance(slot, str) or slot == ""):
            raise ValueError(f"empty slot on {row.get('id')}")
        stratum = row["relation_to_model_origin"]
        if stratum not in STRATA:
            raise ValueError(f"unknown stratum {stratum}")
        clarity = row["alignment_clarity"]
        if clarity not in CLARITY:
            raise ValueError(f"unknown clarity {clarity}")
        present = slot is not None
        band = _band(0 if slot is None else len(slot), short_max=short_max, long_min=long_min, slot_present=present)
        if band != row["length_band"]:
            raise ValueError(
                f"{row['id']} length_band {row['length_band']} != computed {band}"
            )
        if stratum == "none" and slot is not None:
            raise ValueError("none persona must omit the slot")
        if stratum != "none" and slot is None:
            raise ValueError(f"{row['id']} needs a slot")
        spans = tuple(row.get("redaction_spans") or ())
        for span in spans:
            if not isinstance(span, str) or len(span) < 4:
                raise ValueError(f"redaction span too short on {row['id']}: {span!r}")
        if slot is not None and slot not in spans:
            raise ValueError(f"{row['id']} slot_text missing from redaction_spans")
        personas.append(
            Persona(
                persona_id=str(row["id"]),
                slot_text=slot,
                country=row.get("country"),
                bloc=row.get("bloc"),
                relation_to_model_origin=stratum,
                org_kind=str(row["org_kind"]),
                alignment_clarity=str(clarity),
                length_band=str(band),
                redaction_spans=spans,
                model_origin=origin,
            )
        )
    ids = [p.persona_id for p in personas]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate persona id")
    slots = [p.slot_text for p in personas if p.slot_text]
    if len(slots) != len(set(slots)):
        raise ValueError("duplicate slot text")
    for left in slots:
        for right in slots:
            if left != right and (left in right or right in left):
                raise ValueError(f"slot substring collision: {left!r} / {right!r}")
    return tuple(personas)


def global_redaction_spans(path: Optional[Path] = None) -> tuple[str, ...]:
    data = load_label_document(path)
    spans = tuple(data.get("global_redaction_spans") or ())
    for span in spans:
        if not isinstance(span, str) or len(span) < 4:
            raise ValueError(f"global redaction span too short: {span!r}")
    return spans


def by_id(path: Optional[Path] = None) -> dict[str, Persona]:
    return {p.persona_id: p for p in load_personas(path)}


def by_stratum(path: Optional[Path] = None) -> dict[str, tuple[Persona, ...]]:
    grouped: dict[str, list[Persona]] = {name: [] for name in STRATA}
    for persona in load_personas(path):
        grouped[persona.stratum].append(persona)
    return {name: tuple(rows) for name, rows in grouped.items()}
