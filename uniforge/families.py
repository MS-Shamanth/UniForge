"""Stage 2 - families and variant axes. This is where the rule book starts being learned.

No dictionary was provided, so the catalogue becomes the dictionary.

Six rows that differ in exactly one token are not six unrelated products. They are one
product family with one variant axis, and the axis is an attribute nobody defined:

    3MABR-7100075678   3M 775L Stikit Film [P150] - Cubitron II 50 Disc/Box
    3MABR-7100045865   3M 775L Stikit Film [P120] - Cubitron II 50 Disc/Box
    3MABR-7100048736   3M 775L Stikit Film [P80 ] - Cubitron II 50 Disc/Box
    ...

  * tokens that VARY across siblings   -> variant axes -> these are the attributes
  * tokens that HOLD CONSTANT          -> invariant facts -> safe to propagate

And the safety rule that keeps inference from amplifying a guess:

    a variant axis is never propagated.

If a value differs between siblings, it cannot be borrowed from one for another. Every
blocked propagation is counted, because the count is the evidence that the rule is real.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from . import config as C
from . import trade_tokens as TT
from .ingest import Row


@dataclass
class Axis:
    """One skeleton slot whose value changes between siblings."""
    slot: int
    values: list[str]
    kinds: list[str]
    label: str | None = None          # filled in by stage 3
    label_source: str = ""            # 'pattern' | 'lexicon' | 'human' | 'model'
    context_left: str = ""
    context_right: str = ""

    @property
    def distinct(self) -> int:
        return len(set(self.values))

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "values": sorted(set(self.values)),
            "distinct": self.distinct,
            "label": self.label,
            "label_source": self.label_source,
            "context_left": self.context_left,
            "context_right": self.context_right,
        }


@dataclass
class Family:
    family_id: str
    skeleton: str
    member_ids: list[int] = field(default_factory=list)
    axes: list[Axis] = field(default_factory=list)
    invariants: dict[int, str] = field(default_factory=dict)   # slot -> constant value
    exemplar_id: int | None = None

    @property
    def size(self) -> int:
        return len(self.member_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "skeleton": self.skeleton,
            "size": self.size,
            "member_ids": self.member_ids,
            "exemplar_id": self.exemplar_id,
            "axes": [a.to_dict() for a in self.axes],
            "invariants": {str(k): v for k, v in self.invariants.items()},
        }


@dataclass
class FamilyModel:
    families: list[Family]
    by_row: dict[int, str]
    singletons: list[int]
    blocked_propagations: int = 0
    blocked_detail: list[dict] = field(default_factory=list)

    @property
    def axis_count(self) -> int:
        return sum(len(f.axes) for f in self.families)

    def family_of(self, row_id: int) -> Family | None:
        fid = self.by_row.get(row_id)
        if not fid:
            return None
        for f in self.families:
            if f.family_id == fid:
                return f
        return None

    def to_dict(self, limit: int | None = None) -> dict[str, Any]:
        fams = sorted(self.families, key=lambda f: -f.size)
        if limit:
            fams = fams[:limit]
        return {
            "family_count": len(self.families),
            "axis_count": self.axis_count,
            "singleton_count": len(self.singletons),
            "blocked_propagations": self.blocked_propagations,
            "families": [f.to_dict() for f in fams],
        }


# --------------------------------------------------------------------------------------


def _slot_tokens(row: Row) -> list[TT.Token]:
    return [t for t in row.tokens if t.kind != TT.PUNCT]


def build(rows: list[Row]) -> FamilyModel:
    """Cluster on skeleton, then find which slots vary."""
    buckets: dict[str, list[int]] = defaultdict(list)
    by_id = {r.row_id: r for r in rows}

    for r in rows:
        if not r.skeleton:
            continue
        # Require enough held words that the match means something. A skeleton of
        # "# # #" would otherwise pull unrelated products together.
        held = [s for s in r.skeleton.split() if s != "#" and len(s) > 1]
        if len(held) < C.T.family_min_shared_tokens:
            # fall back to a coarser key so short rows still group with their own kind
            key = "SHORT::" + " ".join(held) if held else ""
            if not key.strip("SHORT:: "):
                continue
            buckets[key].append(r.row_id)
        else:
            buckets[r.skeleton].append(r.row_id)

    families: list[Family] = []
    by_row: dict[int, str] = {}
    singletons: list[int] = []
    blocked = 0
    blocked_detail: list[dict] = []
    seq = 0

    for skel, ids in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(ids) < C.T.family_min_members:
            singletons.extend(ids)
            continue
        seq += 1
        fid = f"fam-{seq:04d}"
        fam = Family(family_id=fid, skeleton=skel, member_ids=sorted(ids))
        fam.exemplar_id = fam.member_ids[0]

        # slot-aligned comparison across siblings
        token_lists = {i: _slot_tokens(by_id[i]) for i in fam.member_ids}
        width = min(len(t) for t in token_lists.values())
        for slot in range(width):
            vals = [token_lists[i][slot].text.strip() for i in fam.member_ids]
            kinds = [token_lists[i][slot].kind for i in fam.member_ids]
            distinct = {v.lower() for v in vals}
            if len(distinct) >= C.T.axis_min_distinct:
                left = (token_lists[fam.member_ids[0]][slot - 1].text
                        if slot > 0 else "")
                right = (token_lists[fam.member_ids[0]][slot + 1].text
                         if slot + 1 < width else "")
                fam.axes.append(Axis(slot=slot, values=vals, kinds=kinds,
                                     context_left=left, context_right=right))
                # every axis is one value that may never be borrowed between siblings
                blocked += len(distinct)
                blocked_detail.append({
                    "family_id": fid, "slot": slot,
                    "values": sorted(distinct)[:8],
                    "reason": "variant axis - varies between siblings, cannot be borrowed",
                })
            else:
                fam.invariants[slot] = vals[0]

        families.append(fam)
        for i in fam.member_ids:
            by_row[i] = fid

    return FamilyModel(families=families, by_row=by_row, singletons=sorted(singletons),
                       blocked_propagations=blocked, blocked_detail=blocked_detail)


def propagatable(fam: Family, rows_by_id: dict[int, Row]) -> dict[str, str]:
    """Invariant facts a sibling may safely lend: held words that are not measurements.

    Anything on a variant axis is excluded by construction, since it never lands in
    `invariants` in the first place.
    """
    out: dict[str, str] = {}
    if fam.exemplar_id is None:
        return out
    toks = _slot_tokens(rows_by_id[fam.exemplar_id])
    for slot, val in fam.invariants.items():
        if slot >= len(toks):
            continue
        t = toks[slot]
        if t.is_measure:
            # a constant measurement across the whole family is a real shared fact
            out[f"slot{slot}"] = val
        elif t.kind == TT.WORD and len(val) > 1:
            out[f"slot{slot}"] = val
    return out
