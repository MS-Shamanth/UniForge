"""Stage 9 - autonomous validation: round trip, compliance, confidence, abstention.

THE ROUND TRIP
    Re-parse UniForge's own output and trace every number and every attribute value back
    to a locator. Anything that cannot be traced is a hallucination. This needs no ground
    truth, which is the point: it works on the 1,000-row file where no labelled answer
    exists, not just on the 200 rows where one does.

COMPLIANCE
    Character limits and approved units are checked on the finished text, not asserted.
    Both are reported as a percentage of checks passed, with the failures listed.

CONFIDENCE AND THE REVIEW GATE
    Confidence is the evidence-weighted mean over the winning claims, then reduced for
    named blockers. A contradiction pins it to the contradiction floor, because no
    quantity of good attributes makes a record with the wrong manufacturer publishable.

ABSTENTION
    Counted, categorised and surfaced. Refusing to guess is a feature, so the refusals
    are first-class output rather than silence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import config as C
from . import normalize as N
from . import trade_tokens as TT
from .compose import Composition
from .entity import Resolution
from .evidence import INFERRED, SOURCED, RecordEvidence
from .extract import Extraction
from .ingest import Row
from .vocab import Vocabulary

STATUS_PUBLISH = "auto-publish"
STATUS_REVIEW = "review required"

REASON_UNCLASSIFIED = "item type outside the derived taxonomy"
REASON_UNNAMED_ATTR = "attribute label awaiting a name"
REASON_LOW_COVERAGE = "attribute coverage below target"
REASON_CONTRADICTION = "source contradiction"
REASON_NO_MANUFACTURER = "manufacturer unresolved"


@dataclass
class RoundTrip:
    row_id: int
    numbers_checked: int = 0
    numbers_traced: int = 0
    values_checked: int = 0
    values_traced: int = 0
    untraceable: list[dict] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.untraceable

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "numbers_checked": self.numbers_checked,
            "numbers_traced": self.numbers_traced,
            "values_checked": self.values_checked,
            "values_traced": self.values_traced,
            "clean": self.clean,
            "untraceable": self.untraceable,
        }


@dataclass
class Validation:
    row_id: int
    status: str = STATUS_PUBLISH
    confidence: float = 0.0
    band: str = ""
    reasons: list[str] = field(default_factory=list)
    limit_failures: list[dict] = field(default_factory=list)
    unit_failures: list[dict] = field(default_factory=list)
    limit_checks: int = 0
    unit_checks: int = 0
    round_trip: RoundTrip | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "status": self.status,
            "confidence": self.confidence,
            "band": self.band,
            "reasons": self.reasons,
            "limit_failures": self.limit_failures,
            "unit_failures": self.unit_failures,
            "round_trip": self.round_trip.to_dict() if self.round_trip else None,
        }


def _band(conf: float) -> str:
    if conf >= 0.85:
        return "high"
    if conf >= C.T.auto_publish_floor:
        return "medium"
    if conf >= 0.5:
        return "low"
    return "very low"


# ======================================================================================
# round trip
# ======================================================================================

_NUM_RE = re.compile(r"\d+(?:[.\-/]\d+)*")


def round_trip(row: Row, comp: Composition, ex: Extraction,
               rec: RecordEvidence, sources: dict[str, str]) -> RoundTrip:
    """Re-read our own output and demand a locator for everything in it."""
    rt = RoundTrip(row_id=row.row_id)

    # Build the set of numbers that are justified, from the evidence itself.
    justified: set[str] = set()
    for ev in rec.all_evidence():
        if not ev.publishable:
            continue
        for m in _NUM_RE.finditer(ev.value):
            justified.add(m.group(0).lstrip("0") or "0")
    # numbers present in the supplied row are justified by definition
    for field_name, text in row.raw.items():
        for m in _NUM_RE.finditer(str(text)):
            justified.add(m.group(0).lstrip("0") or "0")
    # numbers present in the cited documents are justified
    for text in sources.values():
        for m in _NUM_RE.finditer(text):
            justified.add(m.group(0).lstrip("0") or "0")

    generated = {
        "INVOICE_DESC": comp.invoice,
        "MOBILE_DESC": comp.mobile,
        "SHORT_DESC": comp.short,
        "PRODUCT_TITLE": comp.title,
        "LONG_DESC": comp.long,
        "WEB_DESC": comp.web,
    }
    for field_name, text in generated.items():
        if not text:
            continue
        for m in _NUM_RE.finditer(text):
            tok = m.group(0).lstrip("0") or "0"
            rt.numbers_checked += 1
            if tok in justified:
                rt.numbers_traced += 1
            else:
                rt.untraceable.append({
                    "field": field_name, "value": m.group(0),
                    "problem": "number appears in generated text with no locator"})

    # every attribute value must carry a locator or a rule
    for a in ex.attributes:
        rt.values_checked += 1
        if a.locator or a.kind in ("derived", "vocab"):
            rt.values_traced += 1
        else:
            rt.untraceable.append({
                "field": f"ATTR::{a.label}", "value": a.value,
                "problem": "attribute value has no locator"})
    return rt


# ======================================================================================
# compliance
# ======================================================================================


def check_limits(comp: Composition, vocab: Vocabulary) -> tuple[int, list[dict]]:
    checks = 0
    fails: list[dict] = []
    values = {
        "INVOICE_DESC": comp.invoice,
        "MOBILE_DESC": comp.mobile,
        "SHORT_DESC": comp.short,
        "PRODUCT_TITLE": comp.title,
        "LONG_DESC": comp.long,
    }
    for name in C.CHAR_LIMIT_CHECKED:
        rule = C.FIELD_RULES[name]
        text = values.get(name, "")
        checks += 1
        if rule.max_chars is not None and len(text) > rule.max_chars:
            fails.append({"field": name, "length": len(text),
                          "limit": rule.max_chars, "problem": "over the limit"})
        if rule.casing == C.CASE_UPPER and text and text != text.upper():
            fails.append({"field": name, "problem": "casing rule is ALL CAPS"})
    return checks, fails


def check_units(comp: Composition, ex: Extraction, vocab: Vocabulary,
                protected: tuple[str, ...] = ()) -> tuple[int, list[dict]]:
    # The unit rule applies to text UniForge CONSTRUCTS. It does not apply to text
    # UniForge QUOTES. MARKETING_DESC and the feature bullets are the manufacturer's own
    # sentences, cited to a character span; "95 percent recycled material" and "blending
    # at 15 to 35 degrees" are correct English in a manufacturer's prose, and silently
    # rewriting a sourced sentence to satisfy an abbreviation standard would break the
    # thing that makes it evidence. WEB_DESC embeds those bullets, so it is excluded too.
    checks = 0
    fails: list[dict] = []
    texts = {
        "INVOICE_DESC": comp.invoice, "MOBILE_DESC": comp.mobile,
        "SHORT_DESC": comp.short, "PRODUCT_TITLE": comp.title,
        "LONG_DESC": comp.long,
    }
    for name, text in texts.items():
        if not text:
            continue
        checks += 1
        upper_field = C.FIELD_RULES[name].casing == C.CASE_UPPER
        _ok, bad = N.approved_units_used(text, vocab, protected,
                                         ignore_case=upper_field)
        glued = N.has_glued_unit(text, vocab, protected)
        if bad:
            fails.append({"field": name, "problem": "unapproved unit spelling",
                          "detail": sorted(bad)})
        if glued:
            fails.append({"field": name,
                          "problem": "no space between magnitude and unit",
                          "detail": glued[:5]})
    for a in ex.attributes:
        if not a.uom:
            continue
        checks += 1
        if a.uom not in vocab.approved_units:
            fails.append({"field": f"ATTR::{a.label}",
                          "problem": "unit not on the approved list",
                          "detail": a.uom})
    return checks, fails


# ======================================================================================


def validate(row: Row, ex: Extraction, comp: Composition, res: Resolution,
             rec: RecordEvidence, vocab: Vocabulary,
             sources: dict[str, str],
             unnamed_attr_rows: set[int]) -> Validation:
    v = Validation(row_id=row.row_id)

    # Identifiers are quoted verbatim and must not be "corrected": 3M is not 3 m.
    protected = tuple(x for x in (
        res.brand_name, res.manufacturer_name, row.part_number, ex.series,
        ex.get("Series"), ex.get("Collection"), ex.get("Product Family"),
        ex.get("Die Cut"), ex.get("Frame Size"), ex.get("NEMA Configuration"),
    ) if x)

    v.limit_checks, v.limit_failures = check_limits(comp, vocab)
    v.unit_checks, v.unit_failures = check_units(comp, ex, vocab, protected)
    v.round_trip = round_trip(row, comp, ex, rec, sources)

    conf = rec.confidence()

    if not res.resolved:
        v.reasons.append(REASON_NO_MANUFACTURER)
        conf = min(conf, 0.45)
    if not ex.classified:
        v.reasons.append(REASON_UNCLASSIFIED)
        conf = min(conf, 0.55)
    # An unnamed induced attribute is only a blocker when the record is leaning on it.
    # A record already carrying enough named attributes is publishable while the naming
    # decision is pending, and gains the extra attribute when the name arrives.
    if row.row_id in unnamed_attr_rows and \
            ex.in_sequence() < C.T.unnamed_attr_tolerance:
        v.reasons.append(REASON_UNNAMED_ATTR)
        conf = min(conf, 0.70)
    if ex.classified and not ex.meets_attribute_floor(C.T.attr_floor):
        v.reasons.append(REASON_LOW_COVERAGE)
        conf = min(conf, 0.71)
    if res.contradiction:
        v.reasons.append(REASON_CONTRADICTION)
        conf = C.T.contradiction_confidence
    if v.limit_failures:
        v.reasons.append("character limit failure")
        conf = min(conf, 0.5)
    if v.unit_failures:
        v.reasons.append("unapproved unit")
        conf = min(conf, 0.6)
    if v.round_trip and not v.round_trip.clean:
        v.reasons.append("value could not be traced to a source")
        conf = min(conf, 0.4)

    v.confidence = round(conf, 4)
    v.band = _band(v.confidence)
    v.status = (STATUS_PUBLISH
                if not v.reasons and v.confidence >= C.T.auto_publish_floor
                else STATUS_REVIEW)

    rec.claim("CONFIDENCE_SCORE", f"{v.confidence:.4f}", "derived",
              "evidence-weighted mean over winning claims, reduced for named blockers")
    rec.claim("CONFIDENCE_BAND", v.band, "derived", "confidence band")
    rec.claim("RECORD_STATUS", v.status, "derived",
              f"auto-publish floor is {C.T.auto_publish_floor}")
    if v.reasons:
        rec.claim("REVIEW_REASON", "; ".join(v.reasons), "derived",
                  "named blockers, each of which maps to one review action")
    return v
