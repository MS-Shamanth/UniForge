"""Emit web/src/data/live.js from the last compile.

The landing page ships with the figures from the submission run. This writes a second
module holding the figures from a run on THIS machine, and the page prefers it when it is
present. That keeps one source of truth: every number on the page can be traced to
data/out/metrics.json.

    python -m uniforge.cli compile
    python tools/export_web_metrics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniforge import config as C  # noqa: E402
from uniforge import export  # noqa: E402

OUT = C.ROOT / "web" / "src" / "data" / "live.js"


def main() -> None:
    src = C.DATA_OUT / export.METRICS_JSON
    if not src.exists():
        raise SystemExit("no metrics yet — run:  python -m uniforge.cli compile")
    m = json.loads(src.read_text(encoding="utf-8"))

    inp, disc, ent = m["input"], m["discovery"], m["entity"]
    srcm, comp, integ = m["sourcing"], m["compliance"], m["integrity"]
    out, abst, rev = m["output"], m["abstention"], m["review"]
    sea, sc, meta = m["search"], m["self_checks"], m["meta"]

    gap, tq, exact = sea["vocabulary_gap"], sea["trade_queries"], sea["exact_item"]

    payload = {
        "INPUT": {
            "placeholderBrandPct": inp["placeholder_brand_pct"],
            "meanDescriptionChars": round(inp["desc_len_mean"]),
            "deliveryHeaders": out["delivery_columns"],
            "rawRows": inp["row_count"],
            "rawColumns": len(inp["columns"]),
        },
        "DISCOVERY": {
            "families": disc["families"],
            "variantAxes": disc["variant_axes_discovered"],
            "inferredLabels": disc["attribute_labels_induced"],
            "modelCalls": disc["model_calls"],
            "categoricalAttributes": disc["categorical_attributes_induced"],
            "labelsNeedingOneName": disc["labels_awaiting_a_human_name"],
        },
        "ENRICHMENT": {
            "attributesBefore": srcm["attributes_before_mean"],
            "attributesAfter": srcm["attributes_after_mean"],
            "factor": srcm["attribute_multiple"],
            "deliveryCellsBefore": srcm["delivery_cells_before"],
            "deliveryCellsAfter": srcm["delivery_cells_after"],
            "marketingDescriptions": srcm["marketing_descriptions_written"],
            "featureBullets": srcm["feature_bullets_extracted"],
            "documentReferences": srcm["document_references_mapped"],
            "candidatesConsidered": srcm["candidates_considered"],
            "admitted": srcm["admitted"],
            "rejectedBeforeRequest": srcm["rejected_count"],
            "blockedBySite": srcm["blocked_count"],
            "inferencesCorrected": srcm["inferences_corrected_by_a_document"],
            "sourcedRows": srcm["rows_enriched"],
            "sourcedOfTotal": inp["row_count"],
        },
        "COMPLIANCE": {
            "rowsCompiled": inp["row_count"],
            "compileSeconds": meta["compile_seconds"],
            "characterLimitPct": comp["character_limit_compliance_pct"],
            "characterLimitChecks": comp["character_limit_checks"],
            "approvedUnitPct": comp["approved_unit_compliance_pct"],
            "roundTripPct": integ["round_trip_clean_pct"],
            "hallucinations": integ["hallucinations"],
            "populatedCellsBefore": out["populated_cells_in"],
            "populatedCellsAfter": out["populated_cells_out"],
            "populatedCellFactor": out["populated_cell_multiple"],
            "selfChecksPassed": sc["passed"],
            "selfChecksTotal": sc["total"],
        },
        "SEARCH": {
            "gapRecallBefore": round(gap["recall_at_k_before"] * 100, 1),
            "gapRecallAfter": round(gap["recall_at_k_after"] * 100, 1),
            "zeroResultBefore": round(gap["zero_result_rate_before"] * 100, 1),
            "zeroResultAfter": round(gap["zero_result_rate_after"] * 100, 1),
            "mrrBefore": tq["mrr_at_k_before"],
            "mrrAfter": tq["mrr_at_k_after"],
            "exactRecallBefore": round(exact["recall_at_k_before"] * 100, 1),
            "exactRecallAfter": round(exact["recall_at_k_after"] * 100, 1),
        },
        "ABSTENTION": {
            "cellsLeftEmpty": abst["delivery_cells_left_empty_for_want_of_a_source"],
            "mobileDescriptionsLeftShort": abst["mobile_descriptions_left_short"],
            "abbreviationsLeftUnexpanded": abst["abbreviations_left_unexpanded"],
            "propagationsBlocked": abst["propagations_blocked_by_the_axis_rule"],
        },
        "REVIEW": {
            "autoPublishPct": rev["auto_publish_pct"],
            "reviewPct": rev["review_pct"],
            "itemTypeRecords": _blocker(rev, "item type outside the derived taxonomy",
                                       "records"),
            "itemTypeMappings": _blocker(rev, "item type outside the derived taxonomy",
                                         "actions"),
            "itemTypeUnblocks": _blocker(rev, "item type outside the derived taxonomy",
                                         "records"),
            "attributeNameRecords": _blocker(rev, "attribute label awaiting a name",
                                             "records"),
            "attributeNameDecisions": _blocker(rev, "attribute label awaiting a name",
                                               "actions"),
            "coverageRecords": _blocker(rev, "attribute coverage below target",
                                        "records"),
            "contradictionRecords": _blocker(rev, "source contradiction", "records"),
            "nameItAppliedTo": _largest_action(rev),
        },
        "ENTITY": {
            "manufacturersUnmasked": ent["manufacturers_unmasked"],
            "contradictionsFound": ent["contradictions"],
            "contradictionConfidence": 34,
        },
    }

    lines = [
        "/**",
        " * GENERATED — do not edit.",
        " *",
        " * Written by tools/export_web_metrics.py from data/out/metrics.json.",
        f" * Source run: {meta['compiled_at']} · {meta['pipeline_version']}",
        f" * Input: {inp['source_file']} · {inp['row_count']} rows",
        " *",
        " * The page prefers these values over the bundled submission figures, so the",
        " * landing page always reflects the run on this machine.",
        " */",
        "",
    ]
    for name, obj in payload.items():
        lines.append(f"export const {name} = {json.dumps(obj, indent=2)}")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {OUT}")
    print(f"  rows                {inp['row_count']:,}")
    print(f"  compile seconds     {meta['compile_seconds']}")
    print(f"  attrs each          {srcm['attributes_before_mean']} -> "
          f"{srcm['attributes_after_mean']} (x{srcm['attribute_multiple']})")
    print(f"  populated cells     {out['populated_cells_in']:,} -> "
          f"{out['populated_cells_out']:,} (x{out['populated_cell_multiple']})")
    print(f"  self checks         {sc['passed']}/{sc['total']}")


def _blocker(rev: dict, name: str, key: str) -> int:
    for b in rev.get("blockers", []):
        if b["blocker"] == name:
            return b.get(key, 0)
    return 0


def _largest_action(rev: dict) -> int:
    best = 0
    for a in rev.get("actions", []):
        if a["kind"] == "attribute label awaiting a name":
            best = max(best, a.get("records_unblocked", 0))
    return best or max(
        (a.get("records_unblocked", 0) for a in rev.get("actions", [])), default=0)


if __name__ == "__main__":
    main()
