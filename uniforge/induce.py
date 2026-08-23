"""Stage 3 - vocabulary induction. Two engines, neither of which calls a model.

ENGINE A - name the variant axes
    A slot that varies between siblings is an attribute. Sometimes its identity is
    obvious from the shape of the values (`P150`, `P120`, `P80` is a grit scale; `240 V`
    is a voltage) and code can name it. When it is not obvious, UniForge does not guess:
    the axis gets a provisional handle and goes to a human as ONE naming decision that
    applies to every product on that axis.

ENGINE B - recover categorical attributes from co-occurrence
    Values that never share a row, but sit in otherwise identical company, are
    alternatives of the same attribute. Nothing declares that AZEK sells three
    collections in six colours; it falls out of the statistics:

        Collection: Harvest, Landmark, Vintage
        Colour:     Brownstone, Coastline, Mahogany, Weathered Teak, Slate Gray,
                    Castle Gate

    Multi-word values are recovered afterwards, by merging tokens that only ever occur
    adjacently. That is how "Weathered Teak" comes back as one value rather than two.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from . import config as C
from . import trade_tokens as TT
from .families import Family, FamilyModel
from .ingest import Row
from .seed import taxonomy as seed_tax
from .vocab import Vocabulary

_HINTS = [(re.compile(p, re.IGNORECASE), name) for p, name in seed_tax.AXIS_NAME_HINTS]


@dataclass
class InducedAttribute:
    attr_id: str
    label: str | None
    provisional: str
    values: list[str]
    support: int
    scope_id: str
    origin: str                # 'axis' | 'cooccurrence'
    label_source: str          # 'pattern' | 'lexicon' | 'unit' | 'unnamed'
    member_rows: list[int] = field(default_factory=list)
    evidence_rows: list[int] = field(default_factory=list)

    @property
    def needs_name(self) -> bool:
        return self.label is None

    @property
    def display(self) -> str:
        return self.label or self.provisional

    def to_dict(self) -> dict[str, Any]:
        return {
            "attr_id": self.attr_id,
            "signature": _signature(self),
            "label": self.label,
            "provisional": self.provisional,
            "display": self.display,
            "values": self.values,
            "value_count": len(self.values),
            "support": self.support,
            "scope_id": self.scope_id,
            "origin": self.origin,
            "label_source": self.label_source,
            "needs_name": self.needs_name,
            "member_rows": self.member_rows[:200],
            "affected_rows": len(self.member_rows),
        }


def _signature(a: InducedAttribute) -> str:
    """Stable identity for an induced attribute: its value set, not its position.

    A reviewer names the attribute whose values are {Harvest, Landmark, Vintage}. That
    identity has to survive a recompile, so decisions are keyed on the value set rather
    than on an id that shifts when the catalogue changes.
    """
    return "sig:" + "|".join(sorted(v.strip().lower() for v in a.values if v.strip()))


@dataclass
class InductionModel:
    attributes: list[InducedAttribute]
    axis_labels_named: int = 0
    axis_labels_unnamed: int = 0
    scopes: int = 0
    model_calls: int = 0
    named_by_reviewer: int = 0

    @property
    def needing_names(self) -> list[InducedAttribute]:
        return [a for a in self.attributes if a.needs_name]

    @property
    def categorical(self) -> list[InducedAttribute]:
        return [a for a in self.attributes if a.origin == "cooccurrence"]

    @property
    def from_axes(self) -> list[InducedAttribute]:
        return [a for a in self.attributes if a.origin == "axis"]

    def by_row(self) -> dict[int, list[InducedAttribute]]:
        out: dict[int, list[InducedAttribute]] = defaultdict(list)
        for a in self.attributes:
            for r in a.member_rows:
                out[r].append(a)
        return out

    def to_dict(self, limit: int | None = None) -> dict[str, Any]:
        attrs = sorted(self.attributes, key=lambda a: (-a.support, a.attr_id))
        if limit:
            attrs = attrs[:limit]
        return {
            "attribute_count": len(self.attributes),
            "labels_induced": self.axis_labels_named,
            "labels_awaiting_a_name": self.axis_labels_unnamed,
            "categorical_attributes": len(self.categorical),
            "axis_attributes": len(self.from_axes),
            "scopes": self.scopes,
            "model_calls": self.model_calls,
            "named_by_reviewer": self.named_by_reviewer,
            "attributes": [a.to_dict() for a in attrs],
        }

    def signature_of(self, attr_id: str) -> str | None:
        for a in self.attributes:
            if a.attr_id == attr_id:
                return _signature(a)
        return None


# ======================================================================================
# Engine A - naming variant axes
# ======================================================================================


def _name_axis(values: list[str], vocab: Vocabulary,
               context_left: str, context_right: str) -> tuple[str | None, str]:
    vals = [v.strip() for v in values if v.strip()]
    if not vals:
        return None, "unnamed"
    lowered = [v.lower() for v in vals]

    # 1. shape of the values
    for rx, name in _HINTS:
        if sum(1 for v in vals if rx.match(v.strip())) >= max(2, len(vals) * 0.6):
            return name, "pattern"

    # 2. known lexicons
    def frac_in(words: set[str]) -> float:
        hits = sum(1 for v in lowered if any(w in words for w in re.split(r"[\s\-]+", v)))
        return hits / len(lowered)

    if frac_in(vocab.colour_words) >= 0.6:
        return "Colour", "lexicon"
    if frac_in(vocab.finish_words) >= 0.6:
        return "Finish", "lexicon"

    # 3. a trailing approved unit tells us the measurement type, and the neighbouring
    #    word usually tells us which dimension it is
    units = []
    for v in vals:
        m = re.search(r"([A-Za-z%°\"']+)\s*$", v)
        if m:
            u = vocab.uom_alias.get(m.group(1).lower())
            if u:
                units.append(u)
    if units and len(set(units)) == 1:
        mt = vocab.uom_measurement_type.get(units[0], "")
        ctx = f"{context_left} {context_right}".lower()
        for word, name in (
            ("dia", "Diameter"), ("thick", "Thickness"), ("arbor", "Arbor Size"),
            ("width", "Width"), ("height", "Height"), ("depth", "Depth"),
            ("length", "Overall Length"), ("bore", "Bore Diameter"),
            ("reach", "Spout Reach"), ("gal", "Tank Capacity"),
        ):
            if word in ctx:
                return name, "unit"
        if mt:
            return mt, "unit"

    return None, "unnamed"


# ======================================================================================
# Engine B - co-occurrence
# ======================================================================================


def _scopes(rows: list[Row]) -> list[list[int]]:
    """Connected components of rows sharing >= 3 content words.

    Broad enough to see across families - which is the point, because AZEK's collections
    put each collection in a different family - and narrow enough that "Colour" in
    decking is not confused with "Colour" in receptacles.
    """
    index: dict[str, list[int]] = defaultdict(list)
    words_by_row: dict[int, set[str]] = {}
    for r in rows:
        ws = {w for w in r.words if len(w) > 2}
        words_by_row[r.row_id] = ws
        for w in ws:
            index[w].append(r.row_id)

    # ignore words so common they link everything
    n = max(1, len(rows))
    stop = {w for w, ids in index.items() if len(ids) > n * 0.35}

    parent: dict[int, int] = {r.row_id: r.row_id for r in rows}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for r in rows:
        overlap: Counter[int] = Counter()
        for w in words_by_row[r.row_id]:
            if w in stop:
                continue
            for other in index[w]:
                if other != r.row_id:
                    overlap[other] += 1
        for other, k in overlap.items():
            if k >= 3:
                union(r.row_id, other)

    groups: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        groups[find(r.row_id)].append(r.row_id)
    return [sorted(v) for v in groups.values()]


def _merge_phrases(group: list[str], rows_words: dict[int, list[str]],
                   member_rows: dict[str, set[int]]) -> list[str]:
    """Rebuild multi-word values from tokens that only ever appear adjacently."""
    adjacency: dict[tuple[str, str], int] = Counter()
    for _rid, words in rows_words.items():
        for a, b in zip(words, words[1:]):
            if a in group and b in group:
                adjacency[(a, b)] += 1

    merged: dict[str, str] = {}
    used: set[str] = set()
    for (a, b), n in sorted(adjacency.items(), key=lambda kv: -kv[1]):
        if a in used or b in used:
            continue
        # only merge when the pair is essentially inseparable
        if n >= max(1, int(0.8 * min(len(member_rows[a]), len(member_rows[b])))):
            merged[a] = f"{a} {b}"
            used.update({a, b})

    out: list[str] = []
    for v in group:
        if v in merged:
            out.append(merged[v])
        elif v in used:
            continue
        else:
            out.append(v)
    return out


def _cooccurrence(rows: list[Row], vocab: Vocabulary,
                  start_seq: int) -> list[InducedAttribute]:
    out: list[InducedAttribute] = []
    seq = start_seq
    by_id = {r.row_id: r for r in rows}

    for scope in _scopes(rows):
        if len(scope) < max(4, C.T.cooc_min_support * 2):
            continue
        scope_rows = [by_id[i] for i in scope]
        rows_words = {r.row_id: [w for w in r.words if len(w) > 2] for r in scope_rows}

        support: dict[str, set[int]] = defaultdict(set)
        for rid, ws in rows_words.items():
            for w in set(ws):
                support[w].add(rid)

        # a value that appears in nearly every row of the scope is a shared noun
        # (the item type), not an alternative
        cands = {w: ids for w, ids in support.items()
                 if C.T.cooc_min_support <= len(ids) <= len(scope) * 0.8}
        if len(cands) < 2:
            continue

        context: dict[str, Counter] = {}
        for w, ids in cands.items():
            c: Counter[str] = Counter()
            for rid in ids:
                for other in rows_words[rid]:
                    if other != w:
                        c[other] += 1
            context[w] = c

        def ctx_sim(a: str, b: str) -> float:
            ca, cb = set(context[a]), set(context[b])
            if not ca or not cb:
                return 0.0
            return len(ca & cb) / len(ca | cb)

        # edge = never co-occur AND keep the same company
        names = sorted(cands)
        parent = {w: w for w in names}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if cands[a] & cands[b]:
                    continue
                if ctx_sim(a, b) < C.T.cooc_min_context_overlap:
                    continue
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

        clusters: dict[str, list[str]] = defaultdict(list)
        for w in names:
            clusters[find(w)].append(w)

        scope_id = f"scope-{min(scope):04d}"
        for _root, members in clusters.items():
            if len(members) < max(2, C.T.cooc_min_group):
                continue
            values = _merge_phrases(sorted(members), rows_words, cands)
            if len(values) < 2:
                continue
            member_rows: set[int] = set()
            for w in members:
                member_rows |= cands[w]
            label, source = _name_axis(values, vocab, "", "")
            seq += 1
            out.append(InducedAttribute(
                attr_id=f"ind-{seq:03d}",
                label=label,
                provisional=f"Induced attribute {seq} ({scope_id})",
                values=[v.title() for v in values],
                support=len(member_rows),
                scope_id=scope_id,
                origin="cooccurrence",
                label_source=source,
                member_rows=sorted(member_rows),
            ))
    return out


# ======================================================================================


def build(rows: list[Row], fams: FamilyModel, vocab: Vocabulary,
          named_by_reviewer: dict[str, str] | None = None) -> InductionModel:
    """`named_by_reviewer` maps attr_id -> label: a decision made once, applied to all."""
    reviewer = named_by_reviewer or {}
    attributes: list[InducedAttribute] = []
    named = unnamed = 0
    seq = 0

    # ---- Engine A ------------------------------------------------------------------
    for fam in fams.families:
        for axis in fam.axes:
            label, source = _name_axis(axis.values, vocab,
                                       axis.context_left, axis.context_right)
            axis.label = label
            axis.label_source = source
            if label:
                named += 1
            else:
                unnamed += 1
            seq += 1
            attributes.append(InducedAttribute(
                attr_id=f"axis-{seq:04d}",
                label=label,
                provisional=(f"Axis {axis.slot} of {fam.family_id} "
                             f"({', '.join(sorted(set(axis.values))[:3])}...)"),
                values=sorted({v.strip() for v in axis.values if v.strip()}),
                support=fam.size,
                scope_id=fam.family_id,
                origin="axis",
                label_source=source,
                member_rows=list(fam.member_ids),
            ))

    # ---- Engine B ------------------------------------------------------------------
    cooc = _cooccurrence(rows, vocab, seq)
    attributes.extend(cooc)

    # ---- a reviewer's naming decision, applied everywhere it holds ------------------
    # Applied by attr_id where the run is stable, and by value-set signature otherwise,
    # so a name given on one run survives the next even if ids shift.
    by_signature = {_signature(a): lbl for a, lbl in
                    ((x, reviewer.get(x.attr_id)) for x in attributes) if lbl}
    for a in attributes:
        if a.label:
            continue
        lbl = reviewer.get(a.attr_id) or reviewer.get(_signature(a)) \
            or by_signature.get(_signature(a))
        if lbl:
            a.label = lbl
            a.label_source = "human"

    named = sum(1 for a in attributes if a.label)
    unnamed = sum(1 for a in attributes if not a.label)

    model = InductionModel(
        attributes=attributes,
        axis_labels_named=named,
        axis_labels_unnamed=unnamed,
        named_by_reviewer=sum(1 for a in attributes if a.label_source == "human"),
        scopes=len({a.scope_id for a in attributes}),
        model_calls=0,
    )
    vocab.register_derived(
        "Induced attribute vocabulary", len(attributes),
        f"{named} named by rule, {unnamed} awaiting one human name each, "
        f"{model.model_calls} model calls")
    return model


def label_axes_for_family(fam: Family, rows_by_id: dict[int, Row]) -> dict[int, str]:
    """row_id -> the value this row carries on each named axis of its family."""
    out: dict[int, str] = {}
    for axis in fam.axes:
        if not axis.label:
            continue
        for i, rid in enumerate(fam.member_ids):
            if i < len(axis.values):
                out[rid] = axis.values[i]
    return out
