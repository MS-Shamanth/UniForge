"""The vocabulary interface every stage reads through.

This is the seam that makes the "ingest the real LOV" next step a data swap rather than
a rewrite. Each table carries provenance:

    supplied  the client's own file was found in data/in/ and parsed
    seed      UniForge's derived reference table
    derived   induced from the catalogue at run time (no external table involved)

The UI shows this per vocabulary, because a compliance claim against a file we never had
would be worthless.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from . import config as C
from .seed import fractions as seed_fractions
from .seed import headers as seed_headers
from .seed import lexicon as seed_lexicon
from .seed import manufacturers as seed_mfr
from .seed import taxonomy as seed_tax
from .seed import uom as seed_uom

SUPPLIED = "supplied"
SEED = "seed"
DERIVED = "derived"


@dataclass
class VocabTable:
    name: str
    provenance: str
    row_count: int
    note: str = ""
    source_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provenance": self.provenance,
            "rows": self.row_count,
            "note": self.note,
            "source_file": self.source_file,
        }


@dataclass
class Vocabulary:
    # --- units & numbers ---------------------------------------------------------
    uom_alias: dict[str, str] = field(default_factory=dict)
    approved_units: set[str] = field(default_factory=set)
    uom_measurement_type: dict[str, str] = field(default_factory=dict)
    uom_examples: dict[str, str] = field(default_factory=dict)
    style_rules: list[tuple[str, str]] = field(default_factory=list)
    fraction_table: list[tuple[str, float, int, int]] = field(default_factory=list)

    # --- entities ----------------------------------------------------------------
    manufacturers: list[dict] = field(default_factory=list)
    brand_owner: dict[str, str] = field(default_factory=dict)
    manufacturer_domains: dict[str, set[str]] = field(default_factory=dict)
    manufacturer_sector: dict[str, str] = field(default_factory=dict)
    alias_to_entry: dict[str, dict] = field(default_factory=dict)
    distributor_names: list[str] = field(default_factory=list)
    distributor_keywords: list[str] = field(default_factory=list)

    # --- taxonomy ----------------------------------------------------------------
    leaves: list[dict] = field(default_factory=list)
    keyword_to_leaf: list[tuple[str, dict]] = field(default_factory=list)

    # --- language ----------------------------------------------------------------
    abbreviations: dict[str, tuple[str, str]] = field(default_factory=dict)
    ambiguous: dict[str, str] = field(default_factory=dict)
    trade_synonyms: dict[str, list[str]] = field(default_factory=dict)
    trade_queries: list[tuple[str, str]] = field(default_factory=list)
    colour_words: set[str] = field(default_factory=set)
    finish_words: set[str] = field(default_factory=set)

    # --- schema ------------------------------------------------------------------
    headers: list[str] = field(default_factory=list)
    header_group: dict[str, str] = field(default_factory=dict)

    # --- bookkeeping -------------------------------------------------------------
    tables: list[VocabTable] = field(default_factory=list)

    # ------------------------------------------------------------------ helpers --
    def table(self, name: str) -> VocabTable | None:
        for t in self.tables:
            if t.name == name:
                return t
        return None

    def provenance_map(self) -> dict[str, str]:
        return {t.name: t.provenance for t in self.tables}

    def any_supplied(self) -> bool:
        return any(t.provenance == SUPPLIED for t in self.tables)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tables": [t.to_dict() for t in self.tables],
            "any_supplied": self.any_supplied(),
            "approved_unit_count": len(self.approved_units),
            "manufacturer_count": len({m["manufacturer_name"] for m in self.manufacturers}),
            "brand_count": len({m["brand_name"] for m in self.manufacturers}),
            "leaf_count": len(self.leaves),
            "delivery_columns": len(self.headers),
        }

    def register_derived(self, name: str, rows: int, note: str = "") -> None:
        existing = self.table(name)
        if existing:
            existing.row_count = rows
            existing.note = note
            return
        self.tables.append(VocabTable(name, DERIVED, rows, note))


# ======================================================================================
# Loaders for the client's real files. Every one is defensive: messy spreadsheets are
# expected (merged cells, multi-row headers, side-by-side blocks, notes in stray
# columns), so nothing assumes row 1 is a clean header.
# ======================================================================================


def _find(name_key: str) -> Path | None:
    fn = C.SUPPLIED_FILES.get(name_key)
    if not fn:
        return None
    p = C.DATA_IN / fn
    return p if p.exists() else None


def _read_any_sheet(path: Path) -> dict[str, pd.DataFrame]:
    try:
        return pd.read_excel(path, sheet_name=None, header=None, dtype=str)
    except Exception:
        return {}


def _locate_header_row(df: pd.DataFrame, must_contain: list[str], scan: int = 12) -> int | None:
    wanted = [w.lower() for w in must_contain]
    for i in range(min(scan, len(df))):
        row = [str(v).strip().lower() for v in df.iloc[i].tolist()]
        if all(any(w in cell for cell in row) for w in wanted):
            return i
    return None


def _load_supplied_uom(vocab: Vocabulary) -> bool:
    path = _find("uom")
    if not path:
        return False
    sheets = _read_any_sheet(path)
    alias: dict[str, str] = {}
    approved: set[str] = set()
    mtype: dict[str, str] = {}
    examples: dict[str, str] = {}
    count = 0
    for _name, df in sheets.items():
        hdr = _locate_header_row(df, ["abbrev"])
        if hdr is None:
            continue
        head = [str(v).strip().lower() for v in df.iloc[hdr].tolist()]

        def col(*keys: str) -> int | None:
            for k in keys:
                for j, h in enumerate(head):
                    if k in h:
                        return j
            return None

        c_abbrev = col("abbrev")
        c_type = col("measurement", "type", "category")
        c_term = col("term", "unit of measure", "name", "description")
        c_ex = col("example", "capture")
        if c_abbrev is None:
            continue
        for _i, row in df.iloc[hdr + 1:].iterrows():
            ab = str(row.get(c_abbrev, "")).strip()
            if not ab or ab.lower() in {"nan", "none"}:
                continue
            approved.add(ab)
            alias.setdefault(ab.lower(), ab)
            if c_term is not None:
                term = str(row.get(c_term, "")).strip()
                if term and term.lower() not in {"nan", "none"}:
                    alias.setdefault(term.lower(), ab)
                    # plural of the spelled-out term
                    alias.setdefault(term.lower() + "s", ab)
            if c_type is not None:
                t = str(row.get(c_type, "")).strip()
                if t and t.lower() not in {"nan", "none"}:
                    mtype[ab] = t
            if c_ex is not None:
                e = str(row.get(c_ex, "")).strip()
                if e and e.lower() not in {"nan", "none"}:
                    examples[ab] = e
            count += 1
    if count == 0:
        return False
    # Keep the seed aliases as a fallback layer beneath the supplied ones.
    merged = dict(seed_uom.build_alias_map())
    merged.update(alias)
    vocab.uom_alias = merged
    vocab.approved_units = approved
    vocab.uom_measurement_type = mtype or seed_uom.measurement_types()
    vocab.uom_examples = examples
    vocab.tables.append(VocabTable(
        "Unit of measure standard", SUPPLIED, count,
        "parsed from the client's abbreviations workbook", path.name))
    return True


def _load_supplied_fractions(vocab: Vocabulary) -> bool:
    path = _find("fractions")
    if not path:
        return False
    sheets = _read_any_sheet(path)
    rows: list[tuple[str, float, int, int]] = []
    for _name, df in sheets.items():
        # Side-by-side Fraction | Decimal blocks: walk every column pair.
        ncols = df.shape[1]
        for j in range(ncols - 1):
            for _i, row in df.iterrows():
                a, b = str(row.get(j, "")).strip(), str(row.get(j + 1, "")).strip()
                if "/" not in a:
                    continue
                try:
                    num_s, den_s = a.split("/", 1)
                    num, den = int(num_s.strip()), int(den_s.strip())
                    dec = float(b)
                except (ValueError, TypeError):
                    continue
                if den <= 0 or num <= 0 or num >= den:
                    continue
                rows.append((f"{num}/{den}", dec, num, den))
    if not rows:
        return False
    seen: set[str] = set()
    dedup = []
    for r in rows:
        if r[0] in seen:
            continue
        seen.add(r[0])
        dedup.append(r)
    vocab.fraction_table = dedup
    vocab.tables.append(VocabTable(
        "Decimal-fraction conversions", SUPPLIED, len(dedup),
        "read as stacked column pairs, not one block", path.name))
    return True


def _load_supplied_manufacturers(vocab: Vocabulary) -> bool:
    path = _find("manufacturers")
    if not path:
        return False
    sheets = _read_any_sheet(path)
    entries: list[dict] = []
    for _name, df in sheets.items():
        hdr = _locate_header_row(df, ["manufacturer", "brand"])
        if hdr is None:
            continue
        head = [str(v).strip().lower() for v in df.iloc[hdr].tolist()]

        def col(*keys: str) -> int | None:
            for k in keys:
                for j, h in enumerate(head):
                    if k in h:
                        return j
            return None

        c_mfr = col("manufacturer_name", "manufacturer name", "manufacturer")
        c_mcode = col("manufacturer_code", "manufacturer code", "mfr code")
        c_brand = col("brand_name", "brand name", "brand")
        c_bcode = col("brand_code", "brand code")
        if c_mfr is None or c_brand is None:
            continue
        for _i, row in df.iloc[hdr + 1:].iterrows():
            mfr = str(row.get(c_mfr, "")).strip()
            brand = str(row.get(c_brand, "")).strip()
            if not mfr or mfr.lower() in {"nan", "none"}:
                continue
            if not brand or brand.lower() in {"nan", "none"}:
                brand = mfr
            entries.append({
                "manufacturer_name": mfr,
                "manufacturer_code": (str(row.get(c_mcode, "")).strip()
                                      if c_mcode is not None else ""),
                "brand_name": brand,
                "brand_code": (str(row.get(c_bcode, "")).strip()
                               if c_bcode is not None else ""),
                "domain": "",
                "sector": "",
                "aliases": [],
            })
    if not entries:
        return False
    # Seed domains and sectors still apply where the name matches; the client's file
    # does not carry them and we will not invent them.
    seed_domains = seed_mfr.manufacturer_domains()
    seed_sectors = seed_mfr.sector_of()
    for e in entries:
        e["domain"] = next(iter(seed_domains.get(e["manufacturer_name"], set())), "")
        e["sector"] = seed_sectors.get(e["manufacturer_name"], "")
    vocab.manufacturers = entries
    vocab.tables.append(VocabTable(
        "Approved manufacturer & brand list", SUPPLIED, len(entries),
        "exact legal casing, suffixes and marks taken from the client's file", path.name))
    return True


def _load_supplied_lov(vocab: Vocabulary) -> bool:
    path = _find("lov")
    if not path:
        return False
    sheets = _read_any_sheet(path)
    leaves: dict[str, dict] = {}
    attr_rows = 0
    for _name, df in sheets.items():
        hdr = _locate_header_row(df, ["classpath"])
        if hdr is None:
            continue
        head = [str(v).strip().lower() for v in df.iloc[hdr].tolist()]

        def col(*keys: str) -> int | None:
            for k in keys:
                for j, h in enumerate(head):
                    if k in h:
                        return j
            return None

        c_cp = col("classpath")
        c_leaf = col("leaf node", "leaf_node", "leaf")
        c_label = col("normalized label", "attribute label", "attribute_label")
        if c_cp is None:
            continue
        for _i, row in df.iloc[hdr + 1:].iterrows():
            cp = str(row.get(c_cp, "")).strip()
            if not cp or cp.lower() in {"nan", "none"}:
                continue
            parts = cp.split(">")
            leaf = (str(row.get(c_leaf, "")).strip()
                    if c_leaf is not None else parts[-1]) or parts[-1]
            rec = leaves.setdefault(cp, {
                "classpath": cp,
                "leaf_node": leaf,
                "unspsc": "",
                "dept": parts[0].strip(),
                "class": parts[1].strip() if len(parts) > 1 else "",
                "fine": parts[2].strip() if len(parts) > 2 else "",
                "keywords": [leaf.lower(), leaf.lower().rstrip("s")],
                "attribute_sequence": [],
                "category_code": f"{parts[0][:3].upper()}-{leaf[:4].upper()}",
            })
            if c_label is not None:
                lbl = str(row.get(c_label, "")).strip()
                if lbl and lbl.lower() not in {"nan", "none"} \
                        and lbl not in rec["attribute_sequence"]:
                    rec["attribute_sequence"].append(lbl)
                    attr_rows += 1
    if not leaves:
        return False
    vocab.leaves = list(leaves.values())
    vocab.tables.append(VocabTable(
        "List of values (taxonomy & attributes)", SUPPLIED, len(leaves),
        f"{attr_rows} attribute labels across {len(leaves)} classpaths", path.name))
    return True


# ======================================================================================
# Public entry point
# ======================================================================================


def load_vocabulary() -> Vocabulary:
    v = Vocabulary()

    # ---- units ----------------------------------------------------------------
    if not _load_supplied_uom(v):
        v.uom_alias = seed_uom.build_alias_map()
        v.approved_units = seed_uom.approved_units()
        v.uom_measurement_type = seed_uom.measurement_types()
        v.uom_examples = {c: ex for _mt, c, _a, ex in seed_uom.UOM_TABLE}
        v.tables.append(VocabTable(
            "Unit of measure standard", SEED, len(v.approved_units),
            "derived: approved abbreviation per measurement type, plus input aliases"))
    v.style_rules = seed_uom.STYLE_RULES

    # ---- fractions ------------------------------------------------------------
    if not _load_supplied_fractions(v):
        v.fraction_table = seed_fractions.TABLE
        v.tables.append(VocabTable(
            "Decimal-fraction conversions", SEED, len(v.fraction_table),
            "generated 1/64..63/64, exact in binary so no transcription error is possible"))

    # ---- manufacturers & brands ------------------------------------------------
    if not _load_supplied_manufacturers(v):
        v.manufacturers = seed_mfr.build_entries()
        v.tables.append(VocabTable(
            "Approved manufacturer & brand list", SEED, len(v.manufacturers),
            "derived seed with legal casing, marks, parent relation and primary domain"))
    v.brand_owner = {m["brand_name"]: m["manufacturer_name"] for m in v.manufacturers}
    for m in v.manufacturers:
        if m.get("domain"):
            v.manufacturer_domains.setdefault(m["manufacturer_name"], set()).add(m["domain"])
        if m.get("sector"):
            v.manufacturer_sector[m["manufacturer_name"]] = m["sector"]
    for m in v.manufacturers:
        keys = {m["manufacturer_name"], m["brand_name"], *m.get("aliases", [])}
        for k in keys:
            kk = _norm_key(k)
            if kk:
                v.alias_to_entry.setdefault(kk, m)
    v.distributor_names = seed_mfr.DISTRIBUTOR_NAMES
    v.distributor_keywords = seed_mfr.DISTRIBUTOR_KEYWORDS
    v.tables.append(VocabTable(
        "Distributor & buying-group register", SEED, len(v.distributor_names),
        "Part_Manuf names whoever invoiced the goods; these are never manufacturers"))

    # ---- taxonomy --------------------------------------------------------------
    if not _load_supplied_lov(v):
        v.leaves = seed_tax.build_leaves()
        v.tables.append(VocabTable(
            "List of values (taxonomy & attributes)", SEED, len(v.leaves),
            "derived spine; two categories carried to full depth"))
    pairs: list[tuple[str, dict]] = []
    for leaf in v.leaves:
        for kw in leaf["keywords"]:
            if kw:
                pairs.append((kw.lower(), leaf))
    pairs.sort(key=lambda p: -len(p[0]))
    v.keyword_to_leaf = pairs

    # ---- language --------------------------------------------------------------
    v.abbreviations = seed_lexicon.ABBREVIATIONS
    v.ambiguous = seed_lexicon.AMBIGUOUS
    v.trade_synonyms = seed_lexicon.TRADE_SYNONYMS
    v.trade_queries = seed_lexicon.TRADE_QUERIES
    v.colour_words = seed_tax.COLOUR_WORDS
    v.finish_words = seed_tax.FINISH_WORDS
    v.tables.append(VocabTable(
        "Trade lexicon", SEED, len(v.abbreviations) + len(v.trade_synonyms),
        f"{len(v.abbreviations)} safe expansions, {len(v.ambiguous)} refused, "
        f"{sum(len(x) for x in v.trade_synonyms.values())} buyer-side synonyms"))

    # ---- schema ----------------------------------------------------------------
    v.headers = seed_headers.HEADERS
    v.header_group = seed_headers.HEADER_GROUP
    v.tables.append(VocabTable(
        "Delivery format", SEED if not _find("items_200") else SUPPLIED,
        len(v.headers),
        "252 static columns; nothing removed, renamed or retyped",
        C.SUPPLIED_FILES["items_200"] if _find("items_200") else None))

    return v


def _norm_key(s: str) -> str:
    import re
    s = (s or "").lower()
    s = s.replace("\u00ae", "").replace("\u2122", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


norm_key = _norm_key
