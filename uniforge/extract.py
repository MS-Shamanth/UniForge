"""Stage 5 - classification and per-row attribute extraction.

Two jobs, in order.

CLASSIFICATION
    Match the description against the derived taxonomy's item-type keywords, longest
    first. An item type that does not resolve is NOT forced into the nearest bucket: the
    record is held, and the unmapped item type becomes ONE review decision that unblocks
    every record sharing it.

EXTRACTION
    Pull attributes from three places, in descending order of authority:

      1. the row's own text, via the tokenizer and the approved unit table
      2. the family's named variant axes (this row's value on each axis)
      3. the family's invariants, propagated from siblings

    Rule 3 carries the safety clause that makes the whole design defensible: a variant
    axis is never propagated. If a value differs between siblings it cannot be borrowed
    from one for another, so inference can never amplify a guess.

DIMENSION ORDER
    `Milw 5"x.045"x7/8"` has three unlabelled lengths. Which is diameter, which is
    thickness, which is arbor? The derived taxonomy already fixes the attribute sequence
    per leaf, so unlabelled measurements are assigned to that leaf's dimensional
    attributes in the order they appear. Positional, deterministic, and stated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import config as C
from . import normalize as N
from . import trade_tokens as TT
from .evidence import DERIVED, INFERRED, SUPPLIER, VOCAB, RecordEvidence
from .families import FamilyModel
from .induce import InductionModel
from .ingest import Row
from .seed import taxonomy as seed_tax
from .vocab import Vocabulary

# Attribute labels that are dimensional, in the order a description usually states them.
_DIMENSIONAL = {
    "Diameter", "Thickness", "Arbor Size", "Nominal Size", "Overall Length",
    "Width", "Height", "Depth", "Length", "Bore Diameter", "Outside Diameter",
    "Trade Size", "Center Distance", "Spout Reach", "Spout Height", "Actual Size",
}

_QTY_RE = re.compile(
    r"(?P<n>\d+)\s*(?:/|per\s+)?\s*(?P<u>pc|pcs|piece|pieces|pk|pack|bx|box|cs|case|"
    r"ea|each|pr|pair|set|dz|dozen|ct|count|disc|discs|sht|sheet|sheets|rl|roll|"
    r"bag|tube|kit|lb|lbs)\b", re.IGNORECASE)


@dataclass
class Attribute:
    label: str
    value: str
    uom: str = ""
    kind: str = SUPPLIER          # evidence kind
    rule: str = ""
    locator: str | None = None
    sequence: int = 999

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label, "value": self.value, "uom": self.uom,
            "kind": self.kind, "rule": self.rule, "locator": self.locator,
        }


@dataclass
class Extraction:
    row_id: int
    classpath: str = ""
    leaf: str = ""
    dept: str = ""
    klass: str = ""
    fine: str = ""
    unspsc: str = ""
    category_code: str = ""
    item_type: str = ""
    item_type_raw: str = ""
    taxonomy_confidence: float = 0.0
    classified: bool = False
    attributes: list[Attribute] = field(default_factory=list)
    series: str = ""
    unexpanded_abbreviations: list[str] = field(default_factory=list)
    attribute_sequence: list[str] = field(default_factory=list)

    def labels(self) -> set[str]:
        return {a.label for a in self.attributes}

    def get(self, label: str) -> str:
        for a in self.attributes:
            if a.label == label:
                return a.value if not a.uom else f"{a.value} {a.uom}".strip()
        return ""

    def coverage(self) -> float:
        """Share of the leaf's expected attribute sequence that was actually filled."""
        if not self.attribute_sequence:
            return 0.0
        hit = len(self.labels() & set(self.attribute_sequence))
        return round(hit / len(self.attribute_sequence), 4)

    def in_sequence(self) -> int:
        return len(self.labels() & set(self.attribute_sequence))

    def meets_attribute_floor(self, floor: int = 3) -> bool:
        """The publishable floor: enough of the category's own attributes to be useful.

        Coverage as a percentage is the wrong gate on its own. A leaf that specifies ten
        attributes is not twice as hard to publish as one that specifies five - a buyer
        filtering a category needs a handful of the right attributes, not a fixed
        fraction of however many the LOV happens to list. So the rule is stated in whole
        attributes, and it is stated in the record: a record needs `floor` of its
        category's attributes, or all of them where the category lists fewer.
        """
        if not self.attribute_sequence:
            return False
        return self.in_sequence() >= min(floor, len(self.attribute_sequence))

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "classpath": self.classpath,
            "leaf": self.leaf,
            "item_type": self.item_type,
            "item_type_raw": self.item_type_raw,
            "classified": self.classified,
            "taxonomy_confidence": self.taxonomy_confidence,
            "unspsc": self.unspsc,
            "series": self.series,
            "attributes": [a.to_dict() for a in self.attributes],
            "attribute_coverage": self.coverage(),
            "unexpanded_abbreviations": self.unexpanded_abbreviations,
        }


# ======================================================================================
# classification
# ======================================================================================


def _guess_item_type_phrase(row: Row) -> str:
    """The noun phrase a clerk would call the thing. Used when nothing matches."""
    words = [t.norm for t in row.tokens if t.kind == TT.WORD]
    tail = [w for w in words if w not in
            {"display", "only", "new", "w", "with", "for", "and", "the"}]
    if not tail:
        return ""
    return " ".join(tail[-3:])


def classify(row: Row, vocab: Vocabulary, rec: RecordEvidence,
             item_type_map: dict[str, str] | None = None) -> Extraction:
    ex = Extraction(row_id=row.row_id)
    low = " " + row.description.lower() + " "

    best: tuple[dict, str] | None = None
    for kw, leaf in vocab.keyword_to_leaf:
        if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", low):
            best = (leaf, kw)
            break
    if best is None:
        # try the singular / hyphen-free forms of the keyword
        squashed = re.sub(r"[^a-z0-9]+", "", low)
        for kw, leaf in vocab.keyword_to_leaf:
            k = re.sub(r"[^a-z0-9]+", "", kw)
            if len(k) >= 5 and k in squashed:
                best = (leaf, kw)
                break

    ex.item_type_raw = _guess_item_type_phrase(row)

    # A reviewer's mapping decision, applied to every record that shares the item type.
    reviewer_leaf: dict | None = None
    if best is None and item_type_map:
        from .overrides import key_for_item_type
        key = key_for_item_type(ex.item_type_raw)
        target = item_type_map.get(key)
        if target:
            reviewer_leaf = next((lf for lf in vocab.leaves
                                  if lf["classpath"] == target), None)

    if best is None and reviewer_leaf is None:
        ex.classified = False
        ex.item_type = N.title_case(ex.item_type_raw, vocab)
        rec.abstain("CLASSPATH", "item type outside the derived taxonomy",
                    f'no leaf matched "{row.description}"')
        return ex

    if reviewer_leaf is not None:
        leaf, kw = reviewer_leaf, "(reviewer mapping)"
    else:
        leaf, kw = best
    ex.classified = True
    ex.classpath = leaf["classpath"]
    ex.leaf = leaf["leaf_node"]
    ex.dept = leaf["dept"]
    ex.klass = leaf["class"]
    ex.fine = leaf["fine"]
    ex.unspsc = leaf.get("unspsc", "")
    ex.category_code = leaf.get("category_code", "")
    ex.attribute_sequence = list(leaf.get("attribute_sequence", []))
    # the leaf name is singular where the node is plural: "Cut-Off Wheels" -> the type
    ex.item_type = leaf["leaf_node"][:-1] if leaf["leaf_node"].endswith("s") \
        else leaf["leaf_node"]

    # Locate the keyword so the classification carries a locator. Where the match came
    # from the stem form ("gloves" matching "Glove"), the literal keyword is not in the
    # text, so we locate the stem instead. If even that fails the claim is recorded as
    # DERIVED - justified by its rule - rather than as a supplier claim with no span,
    # because a supplier claim without a locator may not be published.
    raw_desc = row.raw.get("Part_Desc", "")
    if reviewer_leaf is not None:
        ex.taxonomy_confidence = 0.99
        rec.claim("CLASSPATH", ex.classpath, VOCAB,
                  f'mapped by a reviewer: item type "{ex.item_type_raw}" -> this '
                  f"classpath. One decision, applied to every record sharing the "
                  f"item type.")
        rec.claim("LEAF_NODE", ex.leaf, VOCAB, "leaf node of the mapped classpath")
        rec.claim("ITEM_TYPE", ex.item_type, VOCAB, "item type of the mapped leaf")
        rec.claim("DEPT", ex.dept, VOCAB, "department of the mapped classpath")
        rec.claim("CLASS", ex.klass, VOCAB, "class of the mapped classpath")
        rec.claim("FINE", ex.fine, VOCAB, "fine class of the mapped classpath")
        rec.claim("CATEGORY_CODE", ex.category_code, DERIVED,
                  "derived from the classpath")
        rec.claim("TAXONOMY_CONFIDENCE", "0.99", DERIVED, "reviewer-confirmed mapping")
        if ex.unspsc:
            rec.claim("UNSPSC", ex.unspsc, VOCAB, "UNSPSC of the mapped leaf")
        return ex

    span = TT.find_span(raw_desc, kw)
    if span is None:
        for stem in (kw.rstrip("s"), kw.split()[-1], kw.split()[-1].rstrip("s")):
            if len(stem) >= 4:
                span = TT.find_span(raw_desc, stem)
                if span:
                    break
    loc = TT.row_locator(row.row_id, "Part_Desc", *span) if span else None
    ex.taxonomy_confidence = round(min(0.98, 0.72 + 0.02 * len(kw.split())), 4)
    if loc:
        rec.claim("CLASSPATH", ex.classpath, SUPPLIER,
                  f'item type keyword "{kw}" matched the derived taxonomy', loc)
    else:
        rec.claim("CLASSPATH", ex.classpath, DERIVED,
                  f'item type stem "{kw}" matched the derived taxonomy after '
                  f"punctuation and plural normalisation; no exact span in the "
                  f"supplied text, so this is recorded as a derived claim")
    rec.claim("LEAF_NODE", ex.leaf, VOCAB, "leaf node of the matched classpath")
    rec.claim("ITEM_TYPE", ex.item_type, VOCAB, "item type of the matched leaf")
    rec.claim("DEPT", ex.dept, VOCAB, "department of the matched classpath")
    rec.claim("CLASS", ex.klass, VOCAB, "class of the matched classpath")
    rec.claim("FINE", ex.fine, VOCAB, "fine class of the matched classpath")
    rec.claim("CATEGORY_CODE", ex.category_code, DERIVED, "derived from the classpath")
    rec.claim("TAXONOMY_CONFIDENCE", f"{ex.taxonomy_confidence:.2f}", DERIVED,
              "keyword specificity and match length")
    if ex.unspsc:
        rec.claim("UNSPSC", ex.unspsc, VOCAB, "UNSPSC of the matched leaf")
    return ex


# ======================================================================================
# extraction
# ======================================================================================


def _add(ex: Extraction, rec: RecordEvidence, label: str, value: str, uom: str,
         kind: str, rule: str, locator: str | None) -> bool:
    if not label or not str(value).strip():
        return False
    # The label is constrained too, not just the value. If the category has its own word
    # for this attribute, use the category's word so the record is filterable.
    aligned = seed_tax.align_label(label, ex.attribute_sequence)
    if aligned != label:
        rule = f"{rule}; label aligned to the leaf vocabulary ({label} -> {aligned})"
        label = aligned
    if label in ex.labels():
        return False
    # The same characters cannot justify two different attributes. A variant axis named
    # "Length" by its unit and a dimensional slot named "Diameter" by the leaf's order can
    # both point at `5"` in `Milw 5"x.045"x7/8"` - and if both are published the record
    # states one fact twice under two names, which is worse than stating it once. First
    # claim on a span keeps it.
    val = str(value).strip()
    if locator and any(a.locator == locator for a in ex.attributes):
        return False
    if any(a.locator == locator and f"{a.value} {a.uom}".strip() == f"{val} {uom}".strip()
           for a in ex.attributes):
        return False
    seq = (ex.attribute_sequence.index(label)
           if label in ex.attribute_sequence else 900 + len(ex.attributes))
    ex.attributes.append(Attribute(label=label, value=str(value).strip(), uom=uom,
                                   kind=kind, rule=rule, locator=locator,
                                   sequence=seq))
    rec.claim(f"ATTR::{label}", f"{value} {uom}".strip(), kind, rule, locator)
    return True


def _dimensional_targets(ex: Extraction) -> list[str]:
    return [a for a in ex.attribute_sequence if a in _DIMENSIONAL]


def extract_row(row: Row, ex: Extraction, fams: FamilyModel, induction: InductionModel,
                induced_by_row: dict[int, list], vocab: Vocabulary,
                rec: RecordEvidence) -> Extraction:
    raw_desc = row.raw.get("Part_Desc", "")

    # ---- 1. the row's own measurements ---------------------------------------------
    dim_targets = _dimensional_targets(ex)
    dim_i = 0
    for tok in row.tokens:
        if not tok.is_measure:
            continue
        loc = TT.row_locator(row.row_id, "Part_Desc", tok.start, tok.end)

        # a x b x c triple: a nominal size in its own right
        if tok.kind == TT.DIMSET:
            val = N.normalise_value(tok.text.replace("X", "x"), vocab)
            _add(ex, rec, "Nominal Size", val, "", SUPPLIER,
                 "dimension set read verbatim from the supplied description", loc)
            continue

        m = N.parse_measure(tok.text, vocab)
        if m is None:
            continue

        # an explicit unit tells us the measurement type outright
        if m.unit:
            mt = vocab.uom_measurement_type.get(m.unit, "")
            label = None
            if mt in ("Voltage", "Current", "Power", "Frequency", "Sound Level",
                      "Rotational Speed", "Flow Rate", "Pressure", "Gauge",
                      "Wire Size", "Torque", "Heat", "Temperature", "Luminous Flux",
                      "Colour Rendering", "Efficiency", "Cooling Capacity"):
                label = {
                    "Voltage": "Voltage", "Current": "Amperage", "Power": "Wattage",
                    "Frequency": "Frequency", "Sound Level": "Sound Level",
                    "Rotational Speed": "Rotational Speed", "Flow Rate": "Flow Rate",
                    "Pressure": "Pressure Rating", "Gauge": "Gauge",
                    "Wire Size": "Wire Size", "Torque": "Torque", "Heat": "Input Rating",
                    "Temperature": "Colour Temperature",
                    "Luminous Flux": "Luminous Flux", "Colour Rendering": "CRI",
                    "Efficiency": "Efficiency Rating",
                    "Cooling Capacity": "Cooling Capacity",
                }.get(mt)
                if m.unit == "hp":
                    label = "Power Rating"
                if m.unit == "gal":
                    label = "Tank Capacity"
                if m.unit == "K":
                    label = "Colour Temperature"
                if m.unit == "ton":
                    label = "Cooling Capacity"
            elif mt in ("Length", "Area") and dim_i < len(dim_targets):
                label = dim_targets[dim_i]
                dim_i += 1
            elif mt == "Count":
                label = "Package Quantity"
            elif mt == "Volume":
                label = "Container Size"
            elif mt == "Weight":
                label = "Package Weight"
            elif mt == "Time":
                label = "Warranty Term"
            elif mt == "Angle":
                label = "Angle"
            elif mt == "Grit":
                label = "Grit"
            elif mt == "Thread Pitch":
                label = "Thread Pitch"
            elif mt == "Tooth Count":
                label = "Tooth Count"
            if label:
                _add(ex, rec, label, m.magnitude, m.unit, SUPPLIER,
                     f"measurement read from the supplied description; unit "
                     f"normalised to the approved abbreviation ({m.unit})", loc)
                continue

        # no unit written: fall back to the leaf's dimensional sequence, in order
        if m.unit is None and dim_i < len(dim_targets):
            implied = "in" if ('"' in tok.text or "/" in tok.text
                               or "." in tok.text) else ""
            if implied:
                _add(ex, rec, dim_targets[dim_i], m.magnitude, implied, SUPPLIER,
                     f'unlabelled length assigned to "{dim_targets[dim_i]}" by the '
                     f"leaf's dimensional attribute order (position {dim_i + 1})", loc)
                dim_i += 1
                continue

    # ---- 1b. pack quantity written as "50 Disc/Box" or "25/bx" ---------------------
    if "Package Quantity" not in ex.labels():
        m = _QTY_RE.search(row.description)
        if m:
            unit = N.canonical_unit(m.group("u"), vocab) or "pc"
            span = (m.start(), m.end())
            _add(ex, rec, "Package Quantity", m.group("n"), unit, SUPPLIER,
                 "pack quantity parsed from the supplied description; unit normalised",
                 TT.row_locator(row.row_id, "Part_Desc", *span))

    # ---- 1c. safe abbreviation expansions, and the refusals -------------------------
    for tok in row.tokens:
        if tok.kind != TT.WORD:
            continue
        key = tok.norm.lower()
        if key in vocab.ambiguous:
            if key.upper() not in ex.unexpanded_abbreviations:
                ex.unexpanded_abbreviations.append(key.upper())
                rec.abstain("ABBREVIATION", "abbreviation left unexpanded",
                            f'"{key.upper()}": {vocab.ambiguous[key]}')
            continue
        hit = vocab.abbreviations.get(key)
        if not hit:
            continue
        expansion, why = hit
        loc = TT.row_locator(row.row_id, "Part_Desc", tok.start, tok.end)
        if expansion.lower() in ("stainless steel", "brass", "carbon steel", "copper",
                                "pvc", "cpvc", "abs", "pex", "aluminum", "galvanized"):
            _add(ex, rec, "Material Construction", expansion, "", DERIVED,
                 f'"{tok.text}" expanded to "{expansion}" ({why})', loc)
        elif expansion.lower() in ("black", "white", "brown", "grey", "chrome",
                                   "brushed nickel", "matte black", "polished chrome",
                                   "oil rubbed bronze", "zinc plated", "yellow zinc",
                                   "blue", "red", "green", "tan"):
            _add(ex, rec, "Colour", expansion, "", DERIVED,
                 f'"{tok.text}" expanded to "{expansion}" ({why})', loc)

    # ---- 2. this row's value on each named variant axis ------------------------------
    fam = fams.family_of(row.row_id)
    if fam:
        slot_tokens = [t for t in row.tokens if t.kind != TT.PUNCT]
        try:
            member_pos = fam.member_ids.index(row.row_id)
        except ValueError:
            member_pos = -1
        for axis in fam.axes:
            if not axis.label or member_pos < 0:
                continue
            if axis.slot >= len(slot_tokens):
                continue
            tok = slot_tokens[axis.slot]
            loc = TT.row_locator(row.row_id, "Part_Desc", tok.start, tok.end)
            m = N.parse_measure(tok.text, vocab)
            if m and m.unit:
                _add(ex, rec, axis.label, m.magnitude, m.unit, DERIVED,
                     f"variant axis {axis.slot} of {fam.family_id}: this slot varies "
                     f"across {fam.size} siblings, so it is an attribute "
                     f"(named by {axis.label_source})", loc)
            else:
                _add(ex, rec, axis.label, N.title_case(tok.text, vocab), "", DERIVED,
                     f"variant axis {axis.slot} of {fam.family_id}: this slot varies "
                     f"across {fam.size} siblings, so it is an attribute "
                     f"(named by {axis.label_source})", loc)

        # ---- 3. invariants propagated from siblings ---------------------------------
        for slot, val in fam.invariants.items():
            if slot >= len(slot_tokens):
                continue
            tok = slot_tokens[slot]
            if not tok.is_measure:
                continue
            m = N.parse_measure(tok.text, vocab)
            if not m or not m.unit:
                continue
            mt = vocab.uom_measurement_type.get(m.unit, "")
            label = {"Count": "Package Quantity", "Pressure": "Pressure Rating",
                     "Voltage": "Voltage", "Grit": "Grit"}.get(mt)
            if not label or label in ex.labels():
                continue
            loc = TT.row_locator(row.row_id, "Part_Desc", tok.start, tok.end)
            _add(ex, rec, label, m.magnitude, m.unit, INFERRED,
                 f"invariant across all {fam.size} members of {fam.family_id}, so it is "
                 f"a shared fact rather than a per-row value; propagated", loc)

    # ---- 4. induced categorical attributes -------------------------------------------
    for attr in induced_by_row.get(row.row_id, []):
        if not attr.label:
            continue
        for v in attr.values:
            span = TT.find_span(raw_desc, v)
            if span is None:
                continue
            _add(ex, rec, attr.label, N.title_case(v, vocab), "", DERIVED,
                 f"induced from co-occurrence in {attr.scope_id}: {len(attr.values)} "
                 f"values that never share a row are alternatives of one attribute "
                 f"({attr.attr_id})", TT.row_locator(row.row_id, "Part_Desc", *span))
            break

    # ---- 5. series ------------------------------------------------------------------
    ex.series = ex.get("Series") or ex.get("Collection")
    if ex.series:
        rec.claim("SERIES_NAME", ex.series, DERIVED,
                  "series/collection taken from the extracted attributes")

    ex.attributes.sort(key=lambda a: a.sequence)
    return ex


def build(rows: list[Row], fams: FamilyModel, induction: InductionModel,
          vocab: Vocabulary, ledger_for: Any,
          item_type_map: dict[str, str] | None = None) -> dict[int, Extraction]:
    induced_by_row = induction.by_row()
    out: dict[int, Extraction] = {}
    for row in rows:
        rec = ledger_for(row.row_id, row.part_number)
        ex = classify(row, vocab, rec, item_type_map)
        ex = extract_row(row, ex, fams, induction, induced_by_row, vocab, rec)
        out[row.row_id] = ex
    return out
