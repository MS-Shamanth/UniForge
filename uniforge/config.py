"""Paths, thresholds and the field-level rule book.

Every limit in here is traceable to the UniHack content-guideline description:
formulas, character limits and casing rules per field. Nothing is a magic number
without a name.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA_IN = DATA / "in"
DATA_DOCS = DATA / "docs"
DATA_OUT = DATA / "out"
DATA_VOCAB = DATA / "vocab"
WEB = ROOT / "web"
DOCS = ROOT / "docs"

for _p in (DATA_IN, DATA_DOCS, DATA_OUT, DATA_VOCAB):
    _p.mkdir(parents=True, exist_ok=True)

# Filenames the real UniHack pack ships under. If present they are used and the
# vocabulary provenance flips from "derived" to "supplied".
SUPPLIED_FILES = {
    "items_1000": "Sample-1000_Items.xlsx",
    "items_200": "Unilog-Sample_200_Items-Input-vs-Output.xlsx",
    "manufacturers": "UniCat_Manufacturer_and_Brand_List.xlsx",
    "lov": "Unicat_Lov_v1_0_Updated_With_Remarks.xlsx",
    "uom": "Unilog_Master_UOM_Standards_Abbreviations_and_Terms.xlsx",
    "fractions": "Decimal_Fraction.xlsx",
    "faucets": "FAUCETS_LOV.xlsx",
    "fittings": "Fittings_LOV.xlsx",
    "reference_index": "Reference_Documents_Summary.xlsx",
}

RECONSTRUCTION_INPUT = "uniforge_reconstruction_1000.xlsx"

# --------------------------------------------------------------------------------------
# Input contract
# --------------------------------------------------------------------------------------
INPUT_COLUMNS = [
    "Mfg_Part_Num",
    "Part_Desc",
    "E1_Brand",
    "Unilog_Brand",
    "DIB_Brand",
    "Part_Manuf",
]

# "Placeholders are not data." Anything matching these is treated as an empty cell.
PLACEHOLDER_PATTERNS = [
    r"^\s*--\s*unbranded\s*--\s*$",
    r"^\s*--\s*no\s+unilog\s+brand\s*--\s*$",
    r"^\s*--\s*no\s+dib\s+brand\s*--\s*$",
    r"^\s*--\s*no\s+brand\s*--\s*$",
    r"^\s*--+\s*$",
    r"^\s*n/?a\s*$",
    r"^\s*none\s*$",
    r"^\s*null\s*$",
    r"^\s*unknown\s*$",
    r"^\s*tbd\s*$",
    r"^\s*\.+\s*$",
    r"^\s*0\s*$",
]

# --------------------------------------------------------------------------------------
# Field rule book — construction formula, limit and casing per delivery field
# --------------------------------------------------------------------------------------
CASE_UPPER = "upper"
CASE_TITLE = "title"
CASE_SENTENCE = "sentence"
CASE_AS_IS = "as_is"


@dataclass(frozen=True)
class FieldRule:
    name: str
    max_chars: int | None = None
    min_chars: int | None = None
    casing: str = CASE_AS_IS
    formula: str = ""
    # If the honest input cannot reach min_chars we abstain rather than pad.
    abstain_below_min: bool = True


FIELD_RULES: dict[str, FieldRule] = {
    "INVOICE_DESC": FieldRule(
        "INVOICE_DESC",
        max_chars=40,
        casing=CASE_UPPER,
        formula="ITEM_TYPE + key dimensions + pack qty, abbreviated, ALL CAPS, <= 40 char",
    ),
    "MOBILE_DESC": FieldRule(
        "MOBILE_DESC",
        max_chars=80,
        min_chars=60,
        casing=CASE_AS_IS,
        formula="MANUFACTURER + BRAND + ITEM_TYPE + SERIES + MPN, 60-80 char",
    ),
    "SHORT_DESC": FieldRule(
        "SHORT_DESC",
        max_chars=120,
        casing=CASE_AS_IS,
        formula="BRAND + SERIES + MPN + ITEM_TYPE + top attributes, <= 120 char",
    ),
    "PRODUCT_TITLE": FieldRule(
        "PRODUCT_TITLE",
        max_chars=150,
        casing=CASE_AS_IS,
        formula="BRAND + SERIES + MPN + ITEM_TYPE + key attributes, <= 150 char",
    ),
    "LONG_DESC": FieldRule(
        "LONG_DESC",
        max_chars=1000,
        casing=CASE_AS_IS,
        formula="BRAND + ITEM_TYPE + all attributes in LOV sequence, <= 1000 char",
    ),
    "MARKETING_DESC": FieldRule(
        "MARKETING_DESC",
        max_chars=2000,
        casing=CASE_AS_IS,
        formula="manufacturer marketing prose, sourced only — never generated from nothing",
    ),
    "WEB_DESC": FieldRule(
        "WEB_DESC",
        max_chars=600,
        casing=CASE_AS_IS,
        formula="LONG_DESC + feature bullets, <= 600 char",
    ),
    "SEARCH_KEYWORDS": FieldRule(
        "SEARCH_KEYWORDS",
        max_chars=255,
        casing=CASE_AS_IS,
        formula="trade synonyms of ITEM_TYPE + attribute values, comma separated",
    ),
}

# The five checked in the compliance metric (5 checks x N rows).
CHAR_LIMIT_CHECKED = ["INVOICE_DESC", "MOBILE_DESC", "SHORT_DESC", "PRODUCT_TITLE", "LONG_DESC"]

# --------------------------------------------------------------------------------------
# Thresholds
# --------------------------------------------------------------------------------------


@dataclass
class Thresholds:
    # --- family / axis discovery -------------------------------------------------
    family_min_members: int = 2
    family_min_shared_tokens: int = 3
    axis_min_distinct: int = 2

    # --- co-occurrence vocabulary induction --------------------------------------
    cooc_min_support: int = 3           # a token must appear in >= N rows of a scope
    cooc_min_group: int = 2             # an induced attribute needs >= N alternatives
    cooc_min_context_overlap: float = 0.45

    # --- confidence ---------------------------------------------------------------
    auto_publish_floor: float = 0.72
    contradiction_confidence: float = 0.34
    # Stated in whole attributes, not as a fraction: a record needs this many of its
    # category's own attributes (or all of them, where the category lists fewer).
    #
    # Two, not three. A 36-character supplier line supports two category attributes
    # honestly and a third only sometimes; a record with a resolved manufacturer, a
    # classpath, five normalised descriptions and two filterable attributes is publishable
    # content for a distributor. Setting the bar at three would send records to review for
    # the sin of having a short input, which is not a defect UniForge can fix by asking a
    # human to look at it.
    attr_floor: int = 2
    # An unnamed induced attribute only blocks publication when the record is actually
    # leaning on it - see pipeline._rows_leaning_on_unnamed.
    unnamed_attr_tolerance: int = 3

    # --- search evaluation --------------------------------------------------------
    search_k: int = 10

    # --- sourcing -----------------------------------------------------------------
    doc_must_name_part: bool = True


T = Thresholds()

# --------------------------------------------------------------------------------------
# Sourcing hierarchy — the brief excludes marketplaces and distributor sites, so the
# classification happens BEFORE a request is ever made.
# --------------------------------------------------------------------------------------
EXCLUDED_DOMAINS = {
    # marketplaces
    "amazon.com", "ebay.com", "walmart.com", "alibaba.com", "aliexpress.com",
    "etsy.com", "temu.com", "newegg.com",
    # retail / distributor
    "homedepot.com", "lowes.com", "acehardware.com", "truevalue.com",
    "menards.com", "supplyhouse.com", "ferguson.com", "grainger.com",
    "fastenal.com", "mscdirect.com", "zoro.com", "globalindustrial.com",
    "wesco.com", "platt.com", "cesco.com", "pexsupply.com", "webstaurantstore.com",
    "toolnut.com", "acmetools.com", "ohiopowertool.com", "northerntool.com",
    # aggregator / content farms
    "wikipedia.org", "reddit.com", "quora.com", "pinterest.com", "youtube.com",
    "alibaba.co", "indiamart.com", "made-in-china.com",
}

EXCLUDED_DOMAIN_KEYWORDS = [
    "supply", "supplies", "depot", "warehouse", "wholesale", "distribut",
    "marketplace", "shop", "store", "buy", "deals", "surplus", "liquidat",
]

# A domain is admitted only if it is the manufacturer's own property.
# Populated from the seed manufacturer list; extended by data/docs/index.json.
ENV_ALLOW_LIVE_FETCH = os.environ.get("UNIFORGE_ALLOW_FETCH", "0") == "1"

# --------------------------------------------------------------------------------------
# Attribute slots in the delivery format
# --------------------------------------------------------------------------------------
ATTR_SLOTS = 40
FEATURE_SLOTS = 12
APPLICATION_SLOTS = 4
IMAGE_SLOTS = 6


@dataclass
class RunOptions:
    """Everything the CLI and the API can vary about a run."""
    limit: int | None = None
    use_documents: bool = True
    use_model: bool = False
    model_scope: str = "family"       # per family, not per row
    seed: int = 20260823
    verbose: bool = False
    input_path: Path | None = None
    tags: list[str] = field(default_factory=list)
