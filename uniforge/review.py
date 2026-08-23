"""Human-in-the-loop as leverage, not labour.

A review queue of 551 records is not 551 rows of work, and presenting it that way wastes
the reviewer. Every blocker in UniForge is grouped by the decision that clears it, so the
queue is sized in DECISIONS:

    item type outside the taxonomy   ->  map an item type to a classpath, once,
                                        and every record sharing it unblocks
    attribute label awaiting a name  ->  name an induced group, once, and it applies
                                        to every product on that axis
    attribute coverage below target  ->  confirm the induced attributes for a family
    source contradiction             ->  resolve with the manufacturer

Each action carries its own leverage: how many records one decision releases. That is the
number worth putting in front of a content manager.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .entity import EntityModel
from .extract import Extraction
from .induce import InductionModel
from .ingest import Row
from .verify import (REASON_CONTRADICTION, REASON_LOW_COVERAGE,
                     REASON_NO_MANUFACTURER, REASON_UNCLASSIFIED,
                     REASON_UNNAMED_ATTR, STATUS_REVIEW, Validation)


@dataclass
class ReviewAction:
    action_id: str
    kind: str
    prompt: str
    detail: str
    records_unblocked: int
    records: list[int] = field(default_factory=list)
    options: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "kind": self.kind,
            "prompt": self.prompt,
            "detail": self.detail,
            "records_unblocked": self.records_unblocked,
            "records": self.records[:200],
            "options": self.options[:40],
            "evidence": self.evidence[:12],
        }


@dataclass
class ReviewQueue:
    actions: list[ReviewAction] = field(default_factory=list)
    blocker_records: dict[str, int] = field(default_factory=dict)
    blocker_actions: dict[str, int] = field(default_factory=dict)
    total_review_records: int = 0
    total_records: int = 0

    @property
    def auto_publish_records(self) -> int:
        return self.total_records - self.total_review_records

    def to_dict(self, limit: int | None = None) -> dict[str, Any]:
        acts = sorted(self.actions, key=lambda a: -a.records_unblocked)
        return {
            "total_records": self.total_records,
            "auto_publish_records": self.auto_publish_records,
            "auto_publish_pct": (round(self.auto_publish_records
                                       / max(1, self.total_records) * 100, 2)),
            "review_records": self.total_review_records,
            "review_pct": round(self.total_review_records
                                / max(1, self.total_records) * 100, 2),
            "action_count": len(self.actions),
            "records_per_action": (round(self.total_review_records
                                         / max(1, len(self.actions)), 2)),
            "blockers": [
                {
                    "blocker": name,
                    "records": self.blocker_records.get(name, 0),
                    "actions": self.blocker_actions.get(name, 0),
                    "one_action_clears": (
                        round(self.blocker_records.get(name, 0)
                              / max(1, self.blocker_actions.get(name, 0)), 2)),
                }
                for name in sorted(self.blocker_records,
                                   key=lambda n: -self.blocker_records[n])
            ],
            "actions": [a.to_dict() for a in (acts[:limit] if limit else acts)],
        }


def build(rows: list[Row], extractions: dict[int, Extraction],
          validations: dict[int, Validation], induction: InductionModel,
          entities: EntityModel, classpath_options: list[str]) -> ReviewQueue:
    q = ReviewQueue(total_records=len(rows))
    by_id = {r.row_id: r for r in rows}

    review_ids = [rid for rid, v in validations.items() if v.status == STATUS_REVIEW]
    q.total_review_records = len(review_ids)

    for name in (REASON_UNCLASSIFIED, REASON_UNNAMED_ATTR, REASON_LOW_COVERAGE,
                 REASON_CONTRADICTION, REASON_NO_MANUFACTURER):
        q.blocker_records[name] = sum(
            1 for rid in review_ids if name in validations[rid].reasons)

    seq = 0

    # ---- 1. unmapped item types: one mapping unblocks every record sharing it ------
    by_item_type: dict[str, list[int]] = defaultdict(list)
    for rid in review_ids:
        if REASON_UNCLASSIFIED not in validations[rid].reasons:
            continue
        ex = extractions[rid]
        key = (ex.item_type or ex.item_type_raw or "(no item type read)").strip().title()
        by_item_type[key].append(rid)
    for item_type, ids in sorted(by_item_type.items(), key=lambda kv: -len(kv[1])):
        seq += 1
        q.actions.append(ReviewAction(
            action_id=f"act-{seq:04d}",
            kind=REASON_UNCLASSIFIED,
            prompt=f'Map item type "{item_type}" to a classpath',
            detail=("This item type is not in the derived taxonomy. UniForge will not "
                    "force it into the nearest bucket. One mapping decision classifies "
                    f"every record that shares it."),
            records_unblocked=len(ids),
            records=sorted(ids),
            options=classpath_options,
            evidence=[by_id[i].description for i in ids[:8]],
        ))
    q.blocker_actions[REASON_UNCLASSIFIED] = len(by_item_type)

    # ---- 2. induced attributes awaiting one human name -----------------------------
    unnamed = [a for a in induction.needing_names if a.support >= 2]
    unnamed.sort(key=lambda a: -a.support)
    named_count = 0
    for attr in unnamed:
        affected = [r for r in attr.member_rows if r in validations]
        if not affected:
            continue
        seq += 1
        named_count += 1
        q.actions.append(ReviewAction(
            action_id=f"act-{seq:04d}",
            kind=REASON_UNNAMED_ATTR,
            prompt=(f"Name this attribute: {', '.join(attr.values[:6])}"
                    + ("..." if len(attr.values) > 6 else "")),
            detail=(f"{len(attr.values)} values discovered in {attr.scope_id} that never "
                    f"share a row, so they are alternatives of one attribute. UniForge "
                    f"found the structure but will not invent the label. Naming it once "
                    f"applies to {len(attr.member_rows)} products."),
            records_unblocked=len(attr.member_rows),
            records=sorted(attr.member_rows),
            options=["Collection", "Colour", "Finish", "Series", "Material",
                     "Profile", "Grade", "Style", "Configuration", "Type"],
            evidence=[f"{attr.attr_id} · {attr.origin} · support {attr.support}"],
        ))
    q.blocker_actions[REASON_UNNAMED_ATTR] = named_count

    # ---- 3. low attribute coverage: confirm per family ------------------------------
    by_family: dict[str, list[int]] = defaultdict(list)
    for rid in review_ids:
        if REASON_LOW_COVERAGE not in validations[rid].reasons:
            continue
        ex = extractions[rid]
        by_family[ex.leaf or "(unclassified)"].append(rid)
    for leaf, ids in sorted(by_family.items(), key=lambda kv: -len(kv[1])):
        seq += 1
        ex = extractions[ids[0]]
        missing = [a for a in ex.attribute_sequence if a not in ex.labels()]
        q.actions.append(ReviewAction(
            action_id=f"act-{seq:04d}",
            kind=REASON_LOW_COVERAGE,
            prompt=f"Confirm induced attributes for {leaf}",
            detail=(f"{len(ids)} records in this leaf carry fewer than "
                    f"{min(3, len(ex.attribute_sequence))} of the category's own "
                    f"attributes. The attributes the leaf expects but the supplied text "
                    f"never stated: {', '.join(missing[:8]) or 'none'}."),
            records_unblocked=len(ids),
            records=sorted(ids),
            options=missing[:20],
            evidence=[by_id[i].description for i in ids[:6]],
        ))
    q.blocker_actions[REASON_LOW_COVERAGE] = len(by_family)

    # ---- 4. contradictions: precision, not volume -----------------------------------
    for c in entities.contradictions:
        seq += 1
        q.actions.append(ReviewAction(
            action_id=f"act-{seq:04d}",
            kind=REASON_CONTRADICTION,
            prompt=(f"Resolve: {c['brand_named']} is a brand of {c['brand_owner']}, "
                    f"but the record names {c['manufacturer_named']}"),
            detail=c["explanation"] + " " + c["action"],
            records_unblocked=1,
            records=[c["row_id"]],
            options=[f"Manufacturer is {c['brand_owner']}",
                     f"Brand is wrong, manufacturer {c['manufacturer_named']} is right",
                     "Escalate to the supplier"],
            evidence=[f"part {c['part_number']}",
                      f"brand read from {c['brand_source_field']}",
                      f"confidence pinned to {c['confidence']}"],
        ))
    q.blocker_actions[REASON_CONTRADICTION] = len(entities.contradictions)

    # ---- 5. unresolved manufacturers -------------------------------------------------
    unresolved = [rid for rid in review_ids
                  if REASON_NO_MANUFACTURER in validations[rid].reasons]
    if unresolved:
        by_invoice: dict[str, list[int]] = defaultdict(list)
        for rid in unresolved:
            by_invoice[by_id[rid].part_manuf or "(empty)"].append(rid)
        for name, ids in sorted(by_invoice.items(), key=lambda kv: -len(kv[1])):
            seq += 1
            q.actions.append(ReviewAction(
                action_id=f"act-{seq:04d}",
                kind=REASON_NO_MANUFACTURER,
                prompt=f'Map "{name}" to an approved manufacturer',
                detail=("Part_Manuf names whoever invoiced the goods. This value did not "
                        "resolve to an approved manufacturer and the description names no "
                        "approved brand. One mapping clears every record from this "
                        "vendor."),
                records_unblocked=len(ids),
                records=sorted(ids),
                options=[],
                evidence=[by_id[i].description for i in ids[:6]],
            ))
        q.blocker_actions[REASON_NO_MANUFACTURER] = len(by_invoice)

    return q
