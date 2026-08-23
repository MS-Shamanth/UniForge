"""Stage 8 - description building.

The same product information gets rewritten five times at five different lengths and
casings: for the till receipt, the mobile app, the search results page, the product page
and the marketing copy. Getting these formats right is most of the task, so the formulas
and the limits live in `config.FIELD_RULES` and are applied here by code.

    INVOICE_DESC    <= 40, ALL CAPS, abbreviated
    MOBILE_DESC     60-80
    SHORT_DESC      <= 120
    PRODUCT_TITLE   <= 150
    LONG_DESC       <= 1000, attributes in the leaf's LOV sequence
    MARKETING_DESC  sourced only

Two refusals are built in.

    The 60-character floor on MOBILE_DESC is unreachable honestly from a 38-character
    input for many rows. Those rows get a short mobile description and an abstention
    record. Padding it with filler would be inventing content to satisfy a length check.

    MARKETING_DESC is never generated. If no manufacturer document supplied prose, the
    cell stays empty. "A fluent description made of invented values scores zero."
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import config as C
from . import normalize as N
from .evidence import DERIVED, RecordEvidence
from .extract import Extraction
from .ingest import Row
from .vocab import Vocabulary

# Attributes worth putting in a title, in the order a buyer scans for them.
_TITLE_PRIORITY = [
    "Diameter", "Nominal Size", "Trade Size", "Thickness", "Arbor Size",
    "Grit", "Tooth Count", "Amperage", "Voltage", "Wattage", "Power Rating",
    "Tank Capacity", "Cooling Capacity", "SEER Rating", "Flow Rate",
    "Number of Handles", "Mounting Type", "Wash Cycles", "MERV Rating",
    "Collection", "Colour", "Finish", "Material Construction", "Profile",
    "End Connection", "Pressure Rating", "Package Quantity",
]


@dataclass
class Composition:
    row_id: int
    invoice: str = ""
    mobile: str = ""
    short: str = ""
    title: str = ""
    long: str = ""
    web: str = ""
    keywords: str = ""
    mobile_short_of_floor: bool = False
    truncations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "INVOICE_DESC": self.invoice,
            "MOBILE_DESC": self.mobile,
            "SHORT_DESC": self.short,
            "PRODUCT_TITLE": self.title,
            "LONG_DESC": self.long,
            "WEB_DESC": self.web,
            "SEARCH_KEYWORDS": self.keywords,
            "mobile_short_of_floor": self.mobile_short_of_floor,
            "truncations": self.truncations,
        }


def _attr_pairs(ex: Extraction, vocab: Vocabulary) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for a in ex.attributes:
        val = f"{a.value} {a.uom}".strip() if a.uom else a.value
        val = N.normalise_value(val, vocab)
        if val:
            out.append((a.label, val))
    return out


def _ordered_for_title(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    rank = {lbl: i for i, lbl in enumerate(_TITLE_PRIORITY)}
    return sorted(pairs, key=lambda kv: rank.get(kv[0], 500))


def compose(row: Row, ex: Extraction, manufacturer: str, brand: str,
            vocab: Vocabulary, rec: RecordEvidence) -> Composition:
    comp = Composition(row_id=row.row_id)
    pairs = _attr_pairs(ex, vocab)
    ordered = _ordered_for_title(pairs)
    item_type = ex.item_type or N.title_case(ex.item_type_raw, vocab)
    mpn = row.part_number
    series = ex.series

    # ---------------------------------------------------------------- INVOICE_DESC --
    rule = C.FIELD_RULES["INVOICE_DESC"]
    invoice_bits = [item_type]
    for label, val in ordered:
        if label in ("Diameter", "Nominal Size", "Trade Size", "Thickness",
                     "Arbor Size", "Amperage", "Voltage", "Tank Capacity",
                     "Grit", "Package Quantity", "Colour", "Finish"):
            invoice_bits.append(val)
    invoice = N.abbreviate_for_invoice(" ".join(b for b in invoice_bits if b))
    before = invoice
    comp.invoice = N.fit(invoice, rule.max_chars, drop_separator=" ")
    if comp.invoice != before:
        comp.truncations.append("INVOICE_DESC")
    if comp.invoice:
        rec.claim("INVOICE_DESC", comp.invoice, DERIVED,
                  f"formula: {rule.formula}; {len(comp.invoice)}/{rule.max_chars} chars")

    # ----------------------------------------------------------------- MOBILE_DESC --
    rule = C.FIELD_RULES["MOBILE_DESC"]
    mob_bits = [b for b in (manufacturer, brand, item_type, series, mpn) if b]
    # drop an exact duplicate where brand and manufacturer are the same string
    seen: set[str] = set()
    mob_clean: list[str] = []
    for b in mob_bits:
        k = b.lower().replace("\u00ae", "").replace("\u2122", "").strip()
        if k in seen:
            continue
        seen.add(k)
        mob_clean.append(b)
    mobile = ", ".join(mob_clean)
    if len(mobile) > rule.max_chars:
        mobile = N.fit(mobile, rule.max_chars)
        comp.truncations.append("MOBILE_DESC")
    comp.mobile = mobile
    if rule.min_chars and len(comp.mobile) < rule.min_chars:
        comp.mobile_short_of_floor = True
        rec.abstain("MOBILE_DESC", "mobile description left short",
                    f"the {rule.min_chars}-character floor is unreachable honestly from "
                    f"a {len(row.description)}-character input; padding it would be "
                    f"inventing content ({len(comp.mobile)} chars)")
    if comp.mobile:
        rec.claim("MOBILE_DESC", comp.mobile, DERIVED,
                  f"formula: {rule.formula}; {len(comp.mobile)}/{rule.max_chars} chars")

    # ------------------------------------------------------- SHORT_DESC / TITLE ----
    head = " ".join(b for b in (brand, series, mpn, item_type) if b)
    attr_tail = ", ".join(f"{v}" for _l, v in ordered[:6])
    title_full = N.title_case(", ".join(x for x in (head, attr_tail) if x), vocab)

    r_short = C.FIELD_RULES["SHORT_DESC"]
    comp.short = N.fit(title_full, r_short.max_chars)
    if len(title_full) > r_short.max_chars:
        comp.truncations.append("SHORT_DESC")
    if comp.short:
        rec.claim("SHORT_DESC", comp.short, DERIVED,
                  f"formula: {r_short.formula}; "
                  f"{len(comp.short)}/{r_short.max_chars} chars")

    r_title = C.FIELD_RULES["PRODUCT_TITLE"]
    comp.title = N.fit(title_full, r_title.max_chars)
    if comp.title:
        rec.claim("PRODUCT_TITLE", comp.title, DERIVED,
                  f"formula: {r_title.formula}; "
                  f"{len(comp.title)}/{r_title.max_chars} chars")

    # ------------------------------------------------------------------- LONG_DESC --
    r_long = C.FIELD_RULES["LONG_DESC"]
    seq_rank = {lbl: i for i, lbl in enumerate(ex.attribute_sequence)}
    in_lov = sorted([p for p in pairs if p[0] in seq_rank],
                    key=lambda kv: seq_rank[kv[0]])
    rest = [p for p in pairs if p[0] not in seq_rank]
    # Labels appear only where the value alone would be ambiguous. "Brownstone" needs
    # "Colour" in front of it; "25 pc" and "13300 rpm" carry their own meaning.
    seen_vals: set[str] = set()
    body_bits: list[str] = []
    for lbl, val in in_lov + rest:
        key = val.strip().lower()
        if not key or key in seen_vals:
            continue
        seen_vals.add(key)
        body_bits.append(f"{lbl} {val}"
                         if lbl in ("Colour", "Finish", "Collection", "Series",
                                    "Profile", "Grade", "Style")
                         else val)
    lead = " ".join(b for b in (brand, item_type) if b)
    long_full = N.title_case(", ".join([x for x in [lead] + body_bits if x]), vocab)
    comp.long = N.fit(long_full, r_long.max_chars)
    if len(long_full) > r_long.max_chars:
        comp.truncations.append("LONG_DESC")
    if comp.long:
        rec.claim("LONG_DESC", comp.long, DERIVED,
                  f"formula: {r_long.formula}; attributes written in the leaf's LOV "
                  f"sequence; {len(comp.long)}/{r_long.max_chars} chars")

    # -------------------------------------------------------------------- WEB_DESC --
    r_web = C.FIELD_RULES["WEB_DESC"]
    feature_vals = [rec.value(f"FEATURE_{i:02d}") for i in range(1, 5)]
    web = ". ".join([comp.long] + [f for f in feature_vals if f])
    comp.web = N.fit(web, r_web.max_chars, drop_separator=". ")
    if comp.web:
        rec.claim("WEB_DESC", comp.web, DERIVED,
                  f"formula: {r_web.formula}; {len(comp.web)}/{r_web.max_chars} chars")

    # ------------------------------------------------------------- SEARCH_KEYWORDS --
    r_kw = C.FIELD_RULES["SEARCH_KEYWORDS"]
    syns = vocab.trade_synonyms.get(ex.leaf, [])
    kw_bits: list[str] = []
    for s in syns:
        if s.lower() not in kw_bits:
            kw_bits.append(s.lower())
    for _l, v in ordered[:8]:
        if v.lower() not in kw_bits:
            kw_bits.append(v.lower())
    comp.keywords = N.fit(", ".join(kw_bits), r_kw.max_chars)
    if comp.keywords:
        rec.claim("SEARCH_KEYWORDS", comp.keywords, DERIVED,
                  "trade synonyms of the item type from the derived lexicon, plus "
                  "extracted attribute values; no generated prose is used")

    return comp
