"""The evidence ledger.

One structural rule, enforced in code rather than requested in a prompt:

    a fact with no locator cannot be published.

Every value that reaches the delivery file carries at least one Evidence record. The
kinds are ranked, and the ranking is what lets a document overrule an inference without
any special-casing:

    sourced  (4)  a manufacturer document says so, at these characters
    supplier (3)  the supplied row says so, at these characters
    vocab    (2)  an approved vocabulary says so
    derived  (1)  a deterministic rule computed it from something already evidenced
    inferred (0)  borrowed from a sibling row; the weakest claim we will publish

An inference that disagrees with a document is not silently dropped. Both records stay,
the higher rank wins the field, and the disagreement is counted.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

SOURCED = "sourced"
SUPPLIER = "supplier"
VOCAB = "vocab"
DERIVED = "derived"
INFERRED = "inferred"

RANK = {SOURCED: 4, SUPPLIER: 3, VOCAB: 2, DERIVED: 1, INFERRED: 0}

BASE_CONFIDENCE = {
    SOURCED: 0.96,
    SUPPLIER: 0.90,
    VOCAB: 0.88,
    DERIVED: 0.84,
    INFERRED: 0.62,
}


@dataclass
class Evidence:
    field: str
    value: str
    kind: str
    rule: str
    locator: str | None = None
    confidence: float = 0.0
    note: str = ""
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        if not self.confidence:
            self.confidence = BASE_CONFIDENCE.get(self.kind, 0.5)

    @property
    def rank(self) -> int:
        return RANK.get(self.kind, 0)

    @property
    def publishable(self) -> bool:
        """derived values are justified by their rule; everything else needs a locator."""
        if self.kind in (DERIVED, VOCAB):
            return True
        return bool(self.locator)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "kind": self.kind,
            "rule": self.rule,
            "locator": self.locator,
            "confidence": round(self.confidence, 4),
            "note": self.note,
            "superseded_by": self.superseded_by,
        }


@dataclass
class Conflict:
    field: str
    kept: str
    kept_kind: str
    dropped: str
    dropped_kind: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "kept": self.kept,
            "kept_kind": self.kept_kind,
            "dropped": self.dropped,
            "dropped_kind": self.dropped_kind,
            "reason": self.reason,
        }


@dataclass
class RecordEvidence:
    """Every claim made about one product, and how each was settled."""
    row_id: int
    part_number: str = ""
    by_field: dict[str, list[Evidence]] = field(default_factory=lambda: defaultdict(list))
    conflicts: list[Conflict] = field(default_factory=list)
    abstentions: list[dict] = field(default_factory=list)

    # ------------------------------------------------------------------ writing --
    def add(self, ev: Evidence) -> None:
        self.by_field[ev.field].append(ev)

    def claim(self, field_name: str, value: str, kind: str, rule: str,
              locator: str | None = None, confidence: float = 0.0,
              note: str = "") -> None:
        if value is None or str(value).strip() == "":
            return
        self.add(Evidence(field_name, str(value), kind, rule, locator, confidence, note))

    def abstain(self, field_name: str, reason: str, detail: str = "") -> None:
        self.abstentions.append({
            "field": field_name, "reason": reason, "detail": detail})

    # ------------------------------------------------------------------ reading --
    def winner(self, field_name: str) -> Evidence | None:
        """Highest-ranked publishable claim. Ties break on confidence, then order."""
        cands = [e for e in self.by_field.get(field_name, []) if e.publishable]
        if not cands:
            return None
        best = max(cands, key=lambda e: (e.rank, e.confidence))
        for e in cands:
            if e is best:
                continue
            if e.value.strip().lower() == best.value.strip().lower():
                continue
            e.superseded_by = best.locator or best.rule
            self.conflicts.append(Conflict(
                field=field_name,
                kept=best.value, kept_kind=best.kind,
                dropped=e.value, dropped_kind=e.kind,
                reason=(f"{best.kind} outranks {e.kind}"
                        if best.rank != e.rank else "higher confidence"),
            ))
        return best

    def value(self, field_name: str) -> str:
        w = self.winner(field_name)
        return w.value if w else ""

    def kind_of(self, field_name: str) -> str:
        w = self.winner(field_name)
        return w.kind if w else ""

    def fields(self) -> list[str]:
        return list(self.by_field.keys())

    def all_evidence(self) -> Iterable[Evidence]:
        for evs in self.by_field.values():
            yield from evs

    def counts_by_kind(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for f in self.by_field:
            w = self.winner(f)
            if w:
                out[w.kind] += 1
        return dict(out)

    def confidence(self) -> float:
        """Mean confidence of the winning claims, weighted toward the identity fields."""
        weights = {
            "MANUFACTURER_NAME": 3.0, "BRAND_NAME": 3.0, "CLASSPATH": 3.0,
            "ITEM_TYPE": 2.5, "SHORT_DESC": 2.0, "PRODUCT_TITLE": 2.0,
            "LONG_DESC": 1.5, "INVOICE_DESC": 1.0, "MOBILE_DESC": 1.0,
        }
        num = den = 0.0
        for f in self.by_field:
            w = self.winner(f)
            if not w:
                continue
            wt = weights.get(f, 0.6)
            num += wt * w.confidence
            den += wt
        return round(num / den, 4) if den else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "part_number": self.part_number,
            "fields": {f: [e.to_dict() for e in evs] for f, evs in self.by_field.items()},
            "conflicts": [c.to_dict() for c in self.conflicts],
            "abstentions": self.abstentions,
            "counts_by_kind": self.counts_by_kind(),
            "confidence": self.confidence(),
        }


class Ledger:
    """All record evidence for one run, plus the run-level tallies."""

    def __init__(self) -> None:
        self.records: dict[int, RecordEvidence] = {}
        self.notes: list[str] = []

    def for_row(self, row_id: int, part_number: str = "") -> RecordEvidence:
        rec = self.records.get(row_id)
        if rec is None:
            rec = RecordEvidence(row_id=row_id, part_number=part_number)
            self.records[row_id] = rec
        elif part_number and not rec.part_number:
            rec.part_number = part_number
        return rec

    # ------------------------------------------------------------------ tallies --
    def total_claims(self) -> int:
        return sum(1 for r in self.records.values() for _ in r.all_evidence())

    def total_conflicts(self) -> int:
        return sum(len(r.conflicts) for r in self.records.values())

    def conflicts_where_document_won(self) -> int:
        n = 0
        for r in self.records.values():
            for c in r.conflicts:
                if c.kept_kind == SOURCED and c.dropped_kind == INFERRED:
                    n += 1
        return n

    def total_abstentions(self) -> int:
        return sum(len(r.abstentions) for r in self.records.values())

    def abstentions_by_reason(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for r in self.records.values():
            for a in r.abstentions:
                out[a["reason"]] += 1
        return dict(out)

    def kind_totals(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for r in self.records.values():
            for k, n in r.counts_by_kind().items():
                out[k] += n
        return dict(out)

    def unlocated_claims(self) -> list[dict]:
        """Claims that would have been published without a locator. Must stay empty."""
        bad = []
        for r in self.records.values():
            for e in r.all_evidence():
                if e.kind in (SOURCED, SUPPLIER, INFERRED) and not e.locator:
                    bad.append({"row_id": r.row_id, "field": e.field,
                                "value": e.value, "kind": e.kind, "rule": e.rule})
        return bad

    def to_dict(self, limit: int | None = None) -> dict[str, Any]:
        ids = sorted(self.records)
        if limit:
            ids = ids[:limit]
        return {
            "records": [self.records[i].to_dict() for i in ids],
            "totals": {
                "claims": self.total_claims(),
                "conflicts": self.total_conflicts(),
                "document_overruled_inference": self.conflicts_where_document_won(),
                "abstentions": self.total_abstentions(),
                "by_kind": self.kind_totals(),
                "unlocated_claims": len(self.unlocated_claims()),
            },
            "notes": self.notes,
        }
