"""Turn everything into one 252-column record, and enforce the publishing rule.

    a fact with no locator cannot be published.

The record is built by asking the ledger for the winning claim per column. Columns whose
evidence is missing stay EMPTY. That is not a gap in the implementation - the empties are
the abstention, and they are counted, categorised and reported.

Attribute slots are filled in the leaf's LOV sequence, so ATTR_LABEL_01 is the attribute
the category says comes first, not whichever one happened to parse first.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import PIPELINE_VERSION
from . import config as C
from .compose import Composition
from .entity import Resolution
from .evidence import DERIVED, INFERRED, SOURCED, SUPPLIER, VOCAB, RecordEvidence
from .extract import Extraction
from .ingest import Row
from .seed import headers as H
from .verify import Validation
from .vocab import Vocabulary


def build_record(row: Row, ex: Extraction, comp: Composition, res: Resolution,
                 val: Validation, rec: RecordEvidence, family_id: str,
                 compiled_at: str) -> dict[str, str]:
    r: dict[str, str] = {h: "" for h in H.HEADERS}

    def put(col: str, value: Any) -> None:
        if value is None:
            return
        s = str(value).strip()
        if s:
            r[col] = s

    # ---- identity ------------------------------------------------------------------
    put("SKU", f"UF-{row.row_id + 1:06d}")
    put("MFG_PART_NUM", row.part_number)
    put("MANUFACTURER_NAME", rec.value("MANUFACTURER_NAME"))
    put("MANUFACTURER_CODE", rec.value("MANUFACTURER_CODE"))
    put("BRAND_NAME", rec.value("BRAND_NAME"))
    put("BRAND_CODE", rec.value("BRAND_CODE"))
    put("SERIES_NAME", rec.value("SERIES_NAME"))
    put("MODEL_NUMBER", row.part_number)
    put("COUNTRY_OF_ORIGIN", rec.value("COUNTRY_OF_ORIGIN"))
    put("UNSPSC", rec.value("UNSPSC"))
    # UPC / GTIN need a manufacturer source we did not retrieve
    for col in ("UPC", "GTIN"):
        v = rec.value(col)
        if v:
            put(col, v)
        else:
            rec.abstain(col, "no manufacturer source retrieved",
                        "a barcode may not be derived from a description")

    # ---- taxonomy ------------------------------------------------------------------
    put("CLASSPATH", rec.value("CLASSPATH"))
    put("DEPT", rec.value("DEPT"))
    put("CLASS", rec.value("CLASS"))
    put("FINE", rec.value("FINE"))
    put("LEAF_NODE", rec.value("LEAF_NODE"))
    put("ITEM_TYPE", rec.value("ITEM_TYPE") or ex.item_type)
    put("CATEGORY_CODE", rec.value("CATEGORY_CODE"))
    put("TAXONOMY_CONFIDENCE", rec.value("TAXONOMY_CONFIDENCE"))

    # ---- descriptions ---------------------------------------------------------------
    put("INVOICE_DESC", comp.invoice)
    put("MOBILE_DESC", comp.mobile)
    put("SHORT_DESC", comp.short)
    put("PRODUCT_TITLE", comp.title)
    put("LONG_DESC", comp.long)
    put("WEB_DESC", comp.web)
    put("SEARCH_KEYWORDS", comp.keywords)
    mk = rec.value("MARKETING_DESC")
    if mk:
        put("MARKETING_DESC", mk)
    else:
        rec.abstain("MARKETING_DESC", "no manufacturer prose retrieved",
                    "marketing copy is never generated: a fluent description made of "
                    "invented values scores zero")

    # ---- features and applications ----------------------------------------------------
    for i in range(1, C.FEATURE_SLOTS + 1):
        put(f"FEATURE_{i:02d}", rec.value(f"FEATURE_{i:02d}"))
    for i in range(1, C.APPLICATION_SLOTS + 1):
        put(f"APPLICATION_{i:02d}", rec.value(f"APPLICATION_{i:02d}"))

    # ---- attributes, in the leaf's LOV sequence -----------------------------------
    for i, a in enumerate(ex.attributes[:C.ATTR_SLOTS], start=1):
        put(f"ATTR_LABEL_{i:02d}", a.label)
        put(f"ATTR_VALUE_{i:02d}", a.value)
        put(f"ATTR_UOM_{i:02d}", a.uom)

    # ---- dimensions pulled out of the attribute set --------------------------------
    dim_map = {
        "Overall Length": ("LENGTH", "LENGTH_UOM"),
        "Length": ("LENGTH", "LENGTH_UOM"),
        "Width": ("WIDTH", "WIDTH_UOM"),
        "Actual Width": ("WIDTH", "WIDTH_UOM"),
        "Height": ("HEIGHT", "HEIGHT_UOM"),
        "Depth": ("DEPTH", "DEPTH_UOM"),
        "Diameter": ("DIAMETER", "DIAMETER_UOM"),
        "Thickness": ("THICKNESS", "THICKNESS_UOM"),
        "Actual Thickness": ("THICKNESS", "THICKNESS_UOM"),
        "Package Weight": ("WEIGHT", "WEIGHT_UOM"),
    }
    for a in ex.attributes:
        target = dim_map.get(a.label)
        if not target:
            continue
        col_v, col_u = target
        if not r[col_v]:
            put(col_v, a.value)
            put(col_u, a.uom)

    # ---- packaging -------------------------------------------------------------------
    pq = ex.get("Package Quantity")
    if pq:
        parts = pq.split()
        put("PACKAGE_QUANTITY", parts[0])
        if len(parts) > 1:
            put("PACKAGE_UOM", parts[1])
            put("SELLING_UOM", parts[1])
            put("UNIT_OF_ISSUE", parts[1])
    else:
        put("SELLING_UOM", "ea")
        put("UNIT_OF_ISSUE", "ea")
    put("MIN_ORDER_QTY", "1")
    put("ORDER_INCREMENT", "1")

    # ---- assets ----------------------------------------------------------------------
    for col in ("SPEC_SHEET_URL", "INSTALL_GUIDE_URL", "MSDS_URL", "WARRANTY_DOC_URL",
                "BROCHURE_URL", "CAD_FILE_URL", "ASSET_SOURCE_DOMAIN", "ASSET_STATUS",
                "ASSET_COUNT", "IMAGE_ALT_TEXT"):
        put(col, rec.value(col))
    if not r["PRIMARY_IMAGE_URL"]:
        rec.abstain("PRIMARY_IMAGE_URL", "no manufacturer source retrieved",
                    "digital assets require the manufacturer's own media library")

    # ---- compliance --------------------------------------------------------------------
    for col in ("WARRANTY_TERM", "ENERGY_STAR", "UL_LISTED", "CSA_CERTIFIED",
                "ETL_LISTED", "NSF_CERTIFIED", "ADA_COMPLIANT", "CERTIFICATIONS"):
        put(col, rec.value(col))
    wt = r["WARRANTY_TERM"]
    if wt and " " in wt:
        mag, _sp, unit = wt.partition(" ")
        put("WARRANTY_TERM", mag)
        put("WARRANTY_UOM", unit)

    # ---- pricing: never derived ---------------------------------------------------------
    for col in H.PRICING:
        if not rec.value(col):
            rec.abstain(col, "no manufacturer source retrieved",
                        "price is commercial data and is not derivable from content")
    put("CURRENCY", "USD")

    # ---- provenance & QA ----------------------------------------------------------------
    counts = rec.counts_by_kind()
    put("RECORD_STATUS", val.status)
    put("CONFIDENCE_SCORE", f"{val.confidence:.4f}")
    put("CONFIDENCE_BAND", val.band)
    put("REVIEW_REASON", "; ".join(val.reasons))
    put("EVIDENCE_COUNT", str(sum(1 for _ in rec.all_evidence())))
    put("SOURCED_FIELD_COUNT", str(counts.get(SOURCED, 0)))
    put("INFERRED_FIELD_COUNT", str(counts.get(INFERRED, 0)))
    put("DERIVED_FIELD_COUNT", str(counts.get(DERIVED, 0) + counts.get(VOCAB, 0)))
    put("FAMILY_ID", family_id)
    put("PIPELINE_VERSION", PIPELINE_VERSION)
    put("COMPILED_AT", compiled_at)

    # ---- the publishing rule, enforced last -------------------------------------------
    # Any populated column that is not derivable and has no evidence is withdrawn.
    withdrawn: list[str] = []
    for col in H.SOURCE_REQUIRED_FIELDS:
        if not r.get(col):
            continue
        evs = rec.by_field.get(col, [])
        if not any(e.publishable for e in evs):
            r[col] = ""
            withdrawn.append(col)
    if withdrawn:
        rec.abstain("PUBLISHING_RULE", "withdrawn for want of a locator",
                    ", ".join(sorted(withdrawn)))

    # ---- count the honest empties ------------------------------------------------------
    empty_source_required = [c for c in H.SOURCE_REQUIRED_FIELDS if not r.get(c)]
    put("ABSTAINED_FIELD_COUNT", str(len(empty_source_required)))
    return r


def populated_cells(record: dict[str, str]) -> int:
    return sum(1 for v in record.values() if str(v).strip())


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
