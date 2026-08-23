"""Propagation between siblings, and the rule that keeps it safe.

Stage 2 established the principle on tokens. This applies it to extracted attributes,
which is where it earns its keep: a fact stated on three rows of a product line and
omitted from the fourth is almost certainly true of the fourth as well.

    tokens that hold constant  ->  invariant facts  ->  safe to propagate to siblings

And the guard, which is the whole reason this is defensible:

    a variant axis is never propagated.

If the value differs anywhere in the group, it is a variant axis and it is not borrowed -
not for the members that agree, not for the members that are silent. Every refusal is
counted, so the rule is visible in the metrics rather than merely claimed in a slide.

A propagated value enters the ledger as `inferred`, the weakest kind UniForge will
publish. That ranking is what lets a manufacturer document overrule it later without any
special case: Milwaukee says the box holds 25, our siblings implied 10, the document
outranks the inference, and the disagreement is written into the trail.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from . import trade_tokens as TT
from .entity import Resolution
from .evidence import INFERRED, RecordEvidence
from .extract import Attribute, Extraction
from .ingest import Row

# Attributes that describe the pack or the standard rather than the individual item, so
# a sibling's value is genuinely informative. Dimensions are excluded on purpose: they
# are exactly what varies within a line.
PROPAGATABLE = {
    "Package Quantity", "Pressure Rating", "Material Construction", "Body Material",
    "End Connection", "Standard", "Schedule", "Abrasive Material", "Backing",
    "Attachment Type", "Product Family", "Series", "Collection", "Maximum Speed",
    "Maximum Temperature", "Reinforcement", "Wheel Type", "Disc Type", "Point Type",
    "Head Type", "Drive Type", "Shank Type", "Refrigerant", "Compressor Type",
    "Grade", "Lead Free", "Surface Texture", "Blade Material", "Tooth Material",
    "Valve Type", "Seat Material", "Ball Material", "Port Type", "Handle Type",
    "Insulation", "Conductor Material", "Media Type", "Enclosure", "Chemistry",
}


@dataclass
class PropagationModel:
    propagated: int = 0
    blocked: int = 0
    groups: int = 0
    detail: list[dict] = field(default_factory=list)
    blocked_detail: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sibling_groups": self.groups,
            "values_propagated": self.propagated,
            "propagations_blocked_by_the_axis_rule": self.blocked,
            "rule": "a variant axis is never propagated",
            "examples": self.detail[:40],
            "blocked_examples": self.blocked_detail[:40],
        }


def _group_key(row: Row, ex: Extraction, res: Resolution) -> tuple[str, str] | None:
    """A sibling group is one manufacturer's products inside one leaf.

    Coarser than a skeleton family on purpose. Milwaukee's cut-off wheels do not all
    describe their pack quantity, and the ones that stay silent are precisely the ones a
    sibling can help. The axis guard is what makes the coarse grouping safe: anything
    that varies inside the group is refused, whatever the group's size.
    """
    if not res.manufacturer_name or not ex.leaf:
        return None
    return res.manufacturer_name, ex.leaf


def run(rows: list[Row], extractions: dict[int, Extraction],
        resolutions: dict[int, Resolution],
        ledger_for: Any) -> PropagationModel:
    model = PropagationModel()

    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in rows:
        key = _group_key(r, extractions[r.row_id], resolutions[r.row_id])
        if key:
            groups[key].append(r.row_id)

    for key, ids in groups.items():
        if len(ids) < 2:
            continue
        model.groups += 1

        # what does each candidate label look like across the group?
        seen: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
        holder: dict[str, Attribute] = {}
        for rid in ids:
            for a in extractions[rid].attributes:
                if a.label not in PROPAGATABLE:
                    continue
                val = f"{a.value} {a.uom}".strip()
                seen[a.label][val].append(rid)
                holder.setdefault(f"{a.label}::{val}", a)

        for label, by_value in seen.items():
            havers = {rid for ids_ in by_value.values() for rid in ids_}
            missing = [rid for rid in ids if rid not in havers]

            if len(by_value) > 1:
                # variant axis: refused, and counted
                model.blocked += len(missing) or 1
                if len(model.blocked_detail) < 300:
                    model.blocked_detail.append({
                        "manufacturer": key[0], "leaf": key[1], "label": label,
                        "values": sorted(by_value)[:6],
                        "members_silent": len(missing),
                        "reason": ("value varies between siblings, so it is a variant "
                                   "axis and cannot be borrowed"),
                    })
                continue

            if not missing:
                continue
            value = next(iter(by_value))
            source_rows = by_value[value]
            src = holder.get(f"{label}::{value}")
            for rid in missing:
                ex = extractions[rid]
                if label in ex.labels():
                    continue
                rec: RecordEvidence = ledger_for(rid)
                # the locator points at the sibling that actually states it
                loc = src.locator if src and src.locator else None
                parts = value.rsplit(" ", 1)
                mag, uom = (parts[0], parts[1]) if len(parts) == 2 and any(
                    c.isdigit() for c in parts[0]) else (value, "")
                ex.attributes.append(Attribute(
                    label=label, value=mag, uom=uom, kind=INFERRED,
                    rule=(f"invariant across {len(source_rows)} sibling"
                          f"{'s' if len(source_rows) != 1 else ''} in "
                          f"{key[0]} / {key[1]}; this row is silent, so the shared "
                          f"value is propagated. Weakest publishable evidence kind: a "
                          f"manufacturer document supersedes it."),
                    locator=loc,
                    sequence=(ex.attribute_sequence.index(label)
                              if label in ex.attribute_sequence
                              else 900 + len(ex.attributes))))
                rec.claim(f"ATTR::{label}", value, INFERRED,
                          f"propagated from {len(source_rows)} sibling(s) in "
                          f"{key[0]} / {key[1]} where the value is invariant", loc)
                ex.attributes.sort(key=lambda a: a.sequence)
                model.propagated += 1
                if len(model.detail) < 300:
                    model.detail.append({
                        "row_id": rid, "manufacturer": key[0], "leaf": key[1],
                        "label": label, "value": value,
                        "from_siblings": source_rows[:6],
                    })
    return model
