"""Reviewer decisions, persisted, so human-in-the-loop is leverage rather than theatre.

A review queue that only *reports* what a decision would unblock is a mockup. Every action
in the queue writes here, and every stage reads here, so naming an attribute once really
does apply to every product on that axis at the next compile.

    item_type_map      item type      -> classpath          (stage 5, classification)
    attribute_names    induced attr id -> label             (stage 3, induction)
    manufacturer_map   supplied string -> approved manufacturer (stage 4, resolution)
    contradictions     row id         -> which side is right (stage 4, resolution)

Each decision records who made it and when, because a derived vocabulary that compounds
over time is only trustworthy if its provenance survives.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import config as C

PATH = C.DATA / "overrides.json"


@dataclass
class Overrides:
    item_type_map: dict[str, str] = field(default_factory=dict)
    attribute_names: dict[str, str] = field(default_factory=dict)
    manufacturer_map: dict[str, str] = field(default_factory=dict)
    contradictions: dict[str, str] = field(default_factory=dict)
    log: list[dict] = field(default_factory=list)

    # ------------------------------------------------------------------ counting --
    @property
    def count(self) -> int:
        return (len(self.item_type_map) + len(self.attribute_names)
                + len(self.manufacturer_map) + len(self.contradictions))

    def summary(self) -> dict[str, Any]:
        return {
            "decisions": self.count,
            "item_types_mapped": len(self.item_type_map),
            "attributes_named": len(self.attribute_names),
            "manufacturers_mapped": len(self.manufacturer_map),
            "contradictions_resolved": len(self.contradictions),
            "log": self.log[-50:],
        }

    # ------------------------------------------------------------------ recording --
    def record(self, kind: str, key: str, value: str, actor: str = "reviewer",
               note: str = "") -> None:
        target = {
            "item_type": self.item_type_map,
            "attribute_name": self.attribute_names,
            "manufacturer": self.manufacturer_map,
            "contradiction": self.contradictions,
        }.get(kind)
        if target is None:
            raise ValueError(f"unknown decision kind: {kind}")
        target[key] = value
        self.log.append({
            "kind": kind, "key": key, "value": value, "actor": actor, "note": note,
            "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        })

    def clear(self) -> None:
        self.item_type_map.clear()
        self.attribute_names.clear()
        self.manufacturer_map.clear()
        self.contradictions.clear()
        self.log.append({
            "kind": "clear", "key": "", "value": "", "actor": "reviewer", "note": "",
            "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        })

    # ------------------------------------------------------------------ storage --
    def to_dict(self) -> dict[str, Any]:
        return {
            "item_type_map": self.item_type_map,
            "attribute_names": self.attribute_names,
            "manufacturer_map": self.manufacturer_map,
            "contradictions": self.contradictions,
            "log": self.log,
        }

    def save(self) -> None:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        PATH.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def load() -> Overrides:
    if not PATH.exists():
        return Overrides()
    try:
        raw = json.loads(PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Overrides()
    return Overrides(
        item_type_map=dict(raw.get("item_type_map", {})),
        attribute_names=dict(raw.get("attribute_names", {})),
        manufacturer_map=dict(raw.get("manufacturer_map", {})),
        contradictions=dict(raw.get("contradictions", {})),
        log=list(raw.get("log", [])),
    )


def key_for_item_type(item_type: str) -> str:
    return " ".join((item_type or "").strip().lower().split())
