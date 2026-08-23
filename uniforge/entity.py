"""Stage 4 - manufacturer and brand resolution, and the contradiction check.

`Part_Manuf` names whoever invoiced the goods. That is not the same question as who made
them, which is why the field arrives full of buying co-ops, distributor names and vendor
account artefacts:

    Jam Industrial Supply            -> 3M Company
    Appliance Dealers Cooperative    -> Electrolux Home Products, Inc.
    Milwaukee Accessory (4031)       -> Milwaukee Tool

Resolution runs in a fixed order so the answer is explainable:

    1. is this a distributor or buying group?      -> unmask via the description
    2. exact match on an approved name or alias    -> accept
    3. token-set match above threshold             -> accept, note the score
    4. brand recovered from the description        -> accept the brand's parent
    5. nothing                                     -> leave empty, flag for review

THE CONTRADICTION CHECK
-----------------------
Once a manufacturer and a brand are both resolved, the approved list already knows who
owns which brand. Where the two disagree and both are known, the record cannot be
correct, and no amount of fluency in the description will fix it. UniForge does not
overwrite a sourced value: it drops confidence to the contradiction floor and asks a
human.

This is the check that, run against the client's own reference file, pairs
"Rheem Manufacturing" with brand "FRIGIDAIRE(R)".
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any

from . import config as C
from . import trade_tokens as TT
from .evidence import INFERRED, SOURCED, SUPPLIER, VOCAB, RecordEvidence
from .ingest import Row
from .seed import manufacturers as seed_mfr
from .vocab import Vocabulary, norm_key

_ACCOUNT_RE = re.compile(r"\((\d{2,6})\)\s*$")


@dataclass
class Resolution:
    row_id: int
    manufacturer_name: str = ""
    manufacturer_code: str = ""
    brand_name: str = ""
    brand_code: str = ""
    method: str = ""
    score: float = 0.0
    unmasked_from: str = ""
    contradiction: dict[str, Any] | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return bool(self.manufacturer_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "manufacturer_name": self.manufacturer_name,
            "manufacturer_code": self.manufacturer_code,
            "brand_name": self.brand_name,
            "brand_code": self.brand_code,
            "method": self.method,
            "score": round(self.score, 4),
            "unmasked_from": self.unmasked_from,
            "contradiction": self.contradiction,
            "notes": self.notes,
        }


@dataclass
class EntityModel:
    resolutions: dict[int, Resolution]
    unmasked_count: int = 0
    unmasked_examples: list[dict] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    unresolved: list[int] = field(default_factory=list)
    method_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self, limit: int | None = None) -> dict[str, Any]:
        return {
            "resolved": sum(1 for r in self.resolutions.values() if r.resolved),
            "unresolved": len(self.unresolved),
            "manufacturers_unmasked": self.unmasked_count,
            "unmasked_examples": self.unmasked_examples[:limit or 12],
            "contradictions": self.contradictions,
            "contradiction_count": len(self.contradictions),
            "method_counts": self.method_counts,
        }


# --------------------------------------------------------------------------------------


def _looks_like_distributor(s: str, vocab: Vocabulary) -> bool:
    low = s.lower()
    if any(norm_key(d) == norm_key(s) for d in vocab.distributor_names):
        return True
    return any(k in low for k in vocab.distributor_keywords)


def _strip_account_artefacts(s: str) -> tuple[str, str]:
    """'Milwaukee Accessory (4031)' -> ('Milwaukee', 'account code 4031, "Accessory")'."""
    note_bits: list[str] = []
    m = _ACCOUNT_RE.search(s)
    core = s
    if m:
        note_bits.append(f"account code {m.group(1)}")
        core = _ACCOUNT_RE.sub("", core)
    words = [w for w in re.split(r"\s+", core.strip()) if w]
    kept: list[str] = []
    for w in words:
        if w.strip(".,").lower() in seed_mfr.ACCOUNT_SUFFIX_TOKENS:
            note_bits.append(f'vendor-account word "{w}"')
            continue
        kept.append(w)
    return " ".join(kept).strip(" .,"), "; ".join(note_bits)


def _best_fuzzy(needle: str, vocab: Vocabulary) -> tuple[dict | None, float]:
    key = norm_key(needle)
    if not key:
        return None, 0.0
    if key in vocab.alias_to_entry:
        return vocab.alias_to_entry[key], 1.0
    keys = list(vocab.alias_to_entry)
    # token-set containment first: "milwaukee" inside "milwaukee tool"
    n_tokens = set(key.split())
    best: tuple[dict | None, float] = (None, 0.0)
    for k in keys:
        k_tokens = set(k.split())
        if not k_tokens:
            continue
        inter = n_tokens & k_tokens
        if not inter:
            continue
        jac = len(inter) / len(n_tokens | k_tokens)
        if jac > best[1]:
            best = (vocab.alias_to_entry[k], jac)
    if best[1] >= 0.62:
        return best
    close = difflib.get_close_matches(key, keys, n=1, cutoff=0.86)
    if close:
        return vocab.alias_to_entry[close[0]], difflib.SequenceMatcher(
            None, key, close[0]).ratio()
    return None, best[1]


def _brand_from_description(row: Row, vocab: Vocabulary) -> tuple[dict | None, str, float]:
    """Look for an approved brand or alias in the description, longest match first."""
    text = row.description
    low = text.lower()
    best: tuple[dict | None, str, float] = (None, "", 0.0)
    for key, entry in vocab.alias_to_entry.items():
        if len(key) < 2:
            continue
        # word-boundary match on the normalised alias
        if re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", low):
            score = min(1.0, 0.55 + 0.05 * len(key.split()) + 0.01 * len(key))
            if len(key) > len(best[1]):
                best = (entry, key, score)
    if best[0]:
        return best
    # first token as a last resort, e.g. "Milw ..."
    if row.tokens:
        first = row.tokens[0]
        if first.kind == TT.WORD and len(first.norm) >= 3:
            entry, score = _best_fuzzy(first.norm, vocab)
            if entry and score >= 0.62:
                return entry, first.norm, score * 0.9
    return None, "", 0.0


def resolve_row(row: Row, vocab: Vocabulary, rec: RecordEvidence,
                manufacturer_map: dict[str, str] | None = None,
                contradiction_calls: dict[str, str] | None = None) -> Resolution:
    res = Resolution(row_id=row.row_id)
    raw_manuf = row.part_manuf

    # ---- 0. a reviewer already mapped this vendor string ---------------------------
    if manufacturer_map and raw_manuf:
        target = manufacturer_map.get(norm_key(raw_manuf)) or \
            manufacturer_map.get(raw_manuf)
        if target:
            entry = next((m for m in vocab.manufacturers
                          if m["manufacturer_name"] == target), None)
            if entry:
                res.manufacturer_name = entry["manufacturer_name"]
                res.manufacturer_code = entry.get("manufacturer_code", "")
                res.brand_name = entry.get("brand_name") or res.manufacturer_name
                res.brand_code = entry.get("brand_code", "")
                res.method = "reviewer-mapped"
                res.score = 1.0
                res.notes.append(
                    f'a reviewer mapped "{raw_manuf}" to {res.manufacturer_name}; '
                    f"the mapping applies to every record from this vendor")
                rec.claim("MANUFACTURER_NAME", res.manufacturer_name, VOCAB,
                          f'reviewer mapping: "{raw_manuf}" -> '
                          f"{res.manufacturer_name}")
                rec.claim("MANUFACTURER_CODE", res.manufacturer_code, VOCAB,
                          "paired code from the approved manufacturer list")
                rec.claim("BRAND_NAME", res.brand_name, VOCAB,
                          "brand paired to the reviewer-mapped manufacturer")
                rec.claim("BRAND_CODE", res.brand_code, VOCAB,
                          "paired code from the approved manufacturer list")
                return res

    # ---- 1. distributor / buying group -------------------------------------------
    unmask_needed = bool(raw_manuf) and _looks_like_distributor(raw_manuf, vocab)
    core, artefact_note = _strip_account_artefacts(raw_manuf) if raw_manuf else ("", "")
    if artefact_note:
        res.notes.append(f"Part_Manuf carried {artefact_note}")

    entry: dict | None = None
    method = ""
    score = 0.0

    if not unmask_needed and core:
        entry, score = _best_fuzzy(core, vocab)
        if entry:
            method = "exact" if score >= 0.999 else "token-set"

    # ---- 2/3 failed, or the field named a distributor: unmask via the description --
    if entry is None:
        d_entry, matched_alias, d_score = _brand_from_description(row, vocab)
        if d_entry:
            entry = d_entry
            score = d_score
            method = "unmasked-from-description" if unmask_needed or not core \
                else "recovered-from-description"
            if unmask_needed or (core and norm_key(core) != norm_key(
                    d_entry["manufacturer_name"])):
                res.unmasked_from = raw_manuf
                res.notes.append(
                    f'Part_Manuf "{raw_manuf}" is not a manufacturer; the description '
                    f'names {d_entry["brand_name"]}, whose approved manufacturer is '
                    f'{d_entry["manufacturer_name"]}')

    # ---- 4. brand from the supplied brand columns ---------------------------------
    brand_entry: dict | None = None
    brand_src_field = ""
    for fname, val in (("E1_Brand", row.e1_brand),
                       ("Unilog_Brand", row.unilog_brand),
                       ("DIB_Brand", row.dib_brand)):
        if not val:
            continue
        be, bs = _best_fuzzy(val, vocab)
        if be and bs >= 0.62:
            brand_entry, brand_src_field = be, fname
            break

    if entry is None and brand_entry is not None:
        entry = brand_entry
        method = "from-brand-column"
        score = 0.8

    if entry is None:
        res.method = "unresolved"
        rec.abstain("MANUFACTURER_NAME", "no approved manufacturer match",
                    f'Part_Manuf="{raw_manuf}" did not resolve, and the description '
                    f"names no approved brand")
        return res

    res.manufacturer_name = entry["manufacturer_name"]
    res.manufacturer_code = entry.get("manufacturer_code", "")
    res.method = method
    res.score = score

    # brand: the supplied column wins if it resolved, otherwise the pair from the list.
    # "Where an item has no brand, the manufacturer name is used instead."
    if brand_entry is not None:
        res.brand_name = brand_entry["brand_name"]
        res.brand_code = brand_entry.get("brand_code", "")
    else:
        res.brand_name = entry.get("brand_name") or entry["manufacturer_name"]
        res.brand_code = entry.get("brand_code", "")

    # ---- the contradiction check ---------------------------------------------------
    owner = vocab.brand_owner.get(res.brand_name)
    call = (contradiction_calls or {}).get(str(row.row_id))
    if call and owner and owner != res.manufacturer_name:
        # A reviewer settled it. UniForge still records that it was contested.
        if call == "brand_owner":
            res.notes.append(
                f"a reviewer resolved the contradiction in favour of the brand: "
                f"manufacturer corrected from {res.manufacturer_name} to {owner}")
            res.manufacturer_name = owner
            entry2 = next((m for m in vocab.manufacturers
                           if m["manufacturer_name"] == owner), None)
            res.manufacturer_code = (entry2 or {}).get("manufacturer_code", "")
            rec.claim("MANUFACTURER_NAME", owner, VOCAB,
                      f"reviewer resolved a contradiction: {res.brand_name} is a brand "
                      f"of {owner}")
        else:
            res.notes.append(
                "a reviewer resolved the contradiction in favour of the supplied "
                "manufacturer; the brand is treated as unreliable for this record")
            rec.abstain("BRAND_NAME", "reviewer marked the supplied brand unreliable",
                        f"{res.brand_name} does not belong to "
                        f"{res.manufacturer_name}")
        return res

    if owner and res.manufacturer_name and owner != res.manufacturer_name \
            and not res.unmasked_from:
        sector_brand = vocab.manufacturer_sector.get(owner, "")
        sector_manuf = vocab.manufacturer_sector.get(res.manufacturer_name, "")
        res.contradiction = {
            "row_id": row.row_id,
            "part_number": row.part_number,
            "manufacturer_named": res.manufacturer_name,
            "manufacturer_sector": sector_manuf,
            "brand_named": res.brand_name,
            "brand_owner": owner,
            "brand_owner_sector": sector_brand,
            "brand_source_field": brand_src_field or "description",
            "explanation": (
                f"{res.brand_name} is a brand of {owner}, but the record names "
                f"{res.manufacturer_name} as the manufacturer."
                + (f" {res.manufacturer_name} makes {sector_manuf}. "
                   f"{owner} makes {sector_brand}. These cannot both be correct."
                   if sector_brand and sector_manuf
                   and sector_brand != sector_manuf else "")),
            "confidence": C.T.contradiction_confidence,
            "action": "human review required - UniForge does not overwrite a sourced value",
        }

    # ---- evidence -----------------------------------------------------------------
    if method in ("exact", "token-set") and raw_manuf:
        raw_cell = row.raw.get("Part_Manuf", "")
        span = TT.find_span(raw_cell, core or raw_manuf)
        if span is None:
            # The normalised core is not a literal substring, because normalising
            # collapsed whitespace or dropped a vendor-account word. The claim rests on
            # the whole cell either way, so the locator spans the whole cell rather than
            # going missing - a supplier claim without a locator may not be published.
            trimmed = raw_cell.rstrip()
            span = (len(raw_cell) - len(raw_cell.lstrip()), len(trimmed))
            res.notes.append(
                "locator spans the whole Part_Manuf cell: the approved name is not a "
                "literal substring of the supplied spelling")
        loc = TT.row_locator(row.row_id, "Part_Manuf", *span)
        rec.claim("MANUFACTURER_NAME", res.manufacturer_name, SUPPLIER,
                  f"entity resolution on Part_Manuf ({method}, score {score:.2f})",
                  loc, note=res.notes[0] if res.notes else "")
    else:
        span = TT.find_span(row.raw.get("Part_Desc", ""), row.description.split()[0]
                            if row.description else "")
        loc = (TT.row_locator(row.row_id, "Part_Desc", *span) if span else None)
        rec.claim("MANUFACTURER_NAME", res.manufacturer_name, SUPPLIER,
                  f"entity resolution via description ({method}, score {score:.2f})",
                  loc, note="; ".join(res.notes))
    rec.claim("MANUFACTURER_CODE", res.manufacturer_code, VOCAB,
              "paired code from the approved manufacturer list")

    if brand_entry is not None and brand_src_field:
        span = TT.find_span(row.raw.get(brand_src_field, ""),
                            getattr(row, brand_src_field.lower(), "") or "")
        loc = (TT.row_locator(row.row_id, brand_src_field, *span) if span else None)
        rec.claim("BRAND_NAME", res.brand_name, SUPPLIER,
                  f"approved brand matched from {brand_src_field}", loc)
    else:
        rec.claim("BRAND_NAME", res.brand_name, VOCAB,
                  "brand paired to the resolved manufacturer on the approved list "
                  "(where an item has no brand the manufacturer name is used)")
    rec.claim("BRAND_CODE", res.brand_code, VOCAB,
              "paired code from the approved manufacturer list")
    return res


def build(rows: list[Row], vocab: Vocabulary, ledger_for: Any,
          manufacturer_map: dict[str, str] | None = None,
          contradiction_calls: dict[str, str] | None = None) -> EntityModel:
    resolutions: dict[int, Resolution] = {}
    unmasked = 0
    unmasked_examples: list[dict] = []
    contradictions: list[dict] = []
    unresolved: list[int] = []
    methods: dict[str, int] = {}

    for row in rows:
        rec = ledger_for(row.row_id, row.part_number)
        res = resolve_row(row, vocab, rec, manufacturer_map, contradiction_calls)
        resolutions[row.row_id] = res
        methods[res.method] = methods.get(res.method, 0) + 1
        if not res.resolved:
            unresolved.append(row.row_id)
        if res.unmasked_from:
            unmasked += 1
            if len(unmasked_examples) < 40:
                unmasked_examples.append({
                    "row_id": row.row_id,
                    "part_number": row.part_number,
                    "invoiced_by": res.unmasked_from,
                    "actual_manufacturer": res.manufacturer_name,
                    "brand": res.brand_name,
                })
        if res.contradiction:
            contradictions.append(res.contradiction)

    return EntityModel(
        resolutions=resolutions,
        unmasked_count=unmasked,
        unmasked_examples=unmasked_examples,
        contradictions=contradictions,
        unresolved=unresolved,
        method_counts=methods,
    )
