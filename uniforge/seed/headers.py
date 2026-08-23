"""The 252-column delivery format.

Header names are static: nothing may be removed, renamed, retyped or reordered.
`build_headers()` is the single source of truth; the exporter and the round-trip
checker both read it, so the two can never disagree.

Group sizes: 12 + 8 + 8 + 12 + 4 + 120 + 24 + 10 + 20 + 14 + 8 + 12 = 252
"""
from __future__ import annotations

from ..config import APPLICATION_SLOTS, ATTR_SLOTS, FEATURE_SLOTS, IMAGE_SLOTS

IDENTITY = [
    "SKU",
    "MFG_PART_NUM",
    "MANUFACTURER_NAME",
    "MANUFACTURER_CODE",
    "BRAND_NAME",
    "BRAND_CODE",
    "SERIES_NAME",
    "MODEL_NUMBER",
    "UPC",
    "GTIN",
    "COUNTRY_OF_ORIGIN",
    "UNSPSC",
]

TAXONOMY = [
    "CLASSPATH",
    "DEPT",
    "CLASS",
    "FINE",
    "LEAF_NODE",
    "ITEM_TYPE",
    "CATEGORY_CODE",
    "TAXONOMY_CONFIDENCE",
]

DESCRIPTIONS = [
    "INVOICE_DESC",
    "MOBILE_DESC",
    "SHORT_DESC",
    "PRODUCT_TITLE",
    "LONG_DESC",
    "MARKETING_DESC",
    "WEB_DESC",
    "SEARCH_KEYWORDS",
]

FEATURES = [f"FEATURE_{i:02d}" for i in range(1, FEATURE_SLOTS + 1)]
APPLICATIONS = [f"APPLICATION_{i:02d}" for i in range(1, APPLICATION_SLOTS + 1)]

ATTRIBUTES: list[str] = []
for _i in range(1, ATTR_SLOTS + 1):
    ATTRIBUTES.append(f"ATTR_LABEL_{_i:02d}")
for _i in range(1, ATTR_SLOTS + 1):
    ATTRIBUTES.append(f"ATTR_VALUE_{_i:02d}")
for _i in range(1, ATTR_SLOTS + 1):
    ATTRIBUTES.append(f"ATTR_UOM_{_i:02d}")

DIMENSIONS = [
    "LENGTH", "LENGTH_UOM",
    "WIDTH", "WIDTH_UOM",
    "HEIGHT", "HEIGHT_UOM",
    "DEPTH", "DEPTH_UOM",
    "DIAMETER", "DIAMETER_UOM",
    "THICKNESS", "THICKNESS_UOM",
    "WEIGHT", "WEIGHT_UOM",
    "SHIP_LENGTH", "SHIP_WIDTH", "SHIP_HEIGHT", "SHIP_WEIGHT", "SHIP_UOM",
    "CUBIC_VOLUME", "VOLUME_UOM",
    "HAZMAT_FLAG", "FREIGHT_CLASS", "NMFC_CODE",
]

PACKAGING = [
    "SELLING_UOM",
    "PACKAGE_QUANTITY",
    "PACKAGE_UOM",
    "INNER_PACK_QTY",
    "CASE_QTY",
    "PALLET_QTY",
    "MIN_ORDER_QTY",
    "ORDER_INCREMENT",
    "PACKAGE_TYPE",
    "UNIT_OF_ISSUE",
]

ASSETS = (
    ["PRIMARY_IMAGE_URL"]
    + [f"IMAGE_URL_{i:02d}" for i in range(2, IMAGE_SLOTS + 1)]
    + [
        "IMAGE_ALT_TEXT",
        "IMAGE_COUNT",
        "VIDEO_URL_01",
        "VIDEO_URL_02",
        "SPEC_SHEET_URL",
        "INSTALL_GUIDE_URL",
        "MSDS_URL",
        "WARRANTY_DOC_URL",
        "CAD_FILE_URL",
        "BROCHURE_URL",
        "ASSET_SOURCE_DOMAIN",
        "ASSET_LICENCE",
        "ASSET_STATUS",
        "ASSET_COUNT",
    ]
)

COMPLIANCE = [
    "PROP65_FLAG",
    "PROP65_TEXT",
    "ROHS_COMPLIANT",
    "REACH_COMPLIANT",
    "CA_TITLE_20",
    "ENERGY_STAR",
    "UL_LISTED",
    "CSA_CERTIFIED",
    "ETL_LISTED",
    "NSF_CERTIFIED",
    "ADA_COMPLIANT",
    "WARRANTY_TERM",
    "WARRANTY_UOM",
    "CERTIFICATIONS",
]

PRICING = [
    "LIST_PRICE",
    "PRICE_UOM",
    "CURRENCY",
    "MAP_PRICE",
    "COST",
    "PRICE_EFFECTIVE_DATE",
    "DISCOUNT_GROUP",
    "PRICE_SOURCE",
]

PROVENANCE = [
    "RECORD_STATUS",
    "CONFIDENCE_SCORE",
    "CONFIDENCE_BAND",
    "REVIEW_REASON",
    "EVIDENCE_COUNT",
    "SOURCED_FIELD_COUNT",
    "INFERRED_FIELD_COUNT",
    "DERIVED_FIELD_COUNT",
    "ABSTAINED_FIELD_COUNT",
    "FAMILY_ID",
    "PIPELINE_VERSION",
    "COMPILED_AT",
]

GROUPS: dict[str, list[str]] = {
    "Identity & keys": IDENTITY,
    "Taxonomy": TAXONOMY,
    "Descriptions": DESCRIPTIONS,
    "Features": FEATURES,
    "Applications": APPLICATIONS,
    "Attributes": ATTRIBUTES,
    "Dimensions & logistics": DIMENSIONS,
    "Packaging": PACKAGING,
    "Digital assets": ASSETS,
    "Compliance": COMPLIANCE,
    "Pricing": PRICING,
    "Provenance & QA": PROVENANCE,
}


def build_headers() -> list[str]:
    out: list[str] = []
    for cols in GROUPS.values():
        out.extend(cols)
    return out


HEADERS = build_headers()
HEADER_GROUP = {h: g for g, cols in GROUPS.items() for h in cols}

# Fields that require a manufacturer source we may not have retrieved. When there is
# no source these stay empty on purpose — that is the abstention, not a bug.
SOURCE_REQUIRED_FIELDS = set(ASSETS) | {
    "UPC", "GTIN", "UNSPSC", "COUNTRY_OF_ORIGIN",
    "PROP65_FLAG", "PROP65_TEXT", "ROHS_COMPLIANT", "REACH_COMPLIANT",
    "CA_TITLE_20", "ENERGY_STAR", "UL_LISTED", "CSA_CERTIFIED", "ETL_LISTED",
    "NSF_CERTIFIED", "ADA_COMPLIANT", "WARRANTY_TERM", "WARRANTY_UOM",
    "CERTIFICATIONS",
} | set(PRICING) | {
    "SHIP_LENGTH", "SHIP_WIDTH", "SHIP_HEIGHT", "SHIP_WEIGHT", "SHIP_UOM",
    "CUBIC_VOLUME", "VOLUME_UOM", "HAZMAT_FLAG", "FREIGHT_CLASS", "NMFC_CODE",
    "INNER_PACK_QTY", "CASE_QTY", "PALLET_QTY",
}

assert len(HEADERS) == 252, f"delivery format must be 252 columns, got {len(HEADERS)}"
assert len(set(HEADERS)) == 252, "duplicate header in delivery format"
