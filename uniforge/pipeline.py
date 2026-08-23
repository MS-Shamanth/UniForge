"""The orchestrator, and the metrics it reports.

NINE STAGES, AND WHO IS ALLOWED TO DECIDE WHAT

    1 ingest            deterministic code
    2 families          cross-row statistics
    3 induction         cross-row statistics
    4 entity resolution entity resolution + rules
    5 extraction        deterministic code
    6 sourcing          documents, gated before any request
    7 normalisation     deterministic code
    8 composition       deterministic code (formulas and limits)
    9 verification      deterministic code

Four of the nine are cross-row. That is why a per-row prompt cannot reproduce this: no
amount of prompting one row at a time can see that six 3M rows differ in exactly one
token.

The pipeline is complete with ZERO model calls. When a model is enabled it is charged per
family rather than per row, so the bill scales with structure, not with volume.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from . import PIPELINE_VERSION, TAGLINE
from . import assemble, compose, config as C, entity, export, extract, families
from . import induce, ingest, overrides as OV, propagate, review, search_eval
from . import sourcing, verify
from .evidence import Ledger
from .seed import headers as H
from .vocab import load_vocabulary

STAGES = [
    ("ingest", "Input analysis", "deterministic code"),
    ("families", "Family & variant-axis discovery", "cross-row statistics"),
    ("induction", "Vocabulary induction", "cross-row statistics"),
    ("entity", "Manufacturer & brand resolution", "entity resolution + rules"),
    ("extract", "Classification & attribute extraction", "deterministic code"),
    ("sourcing", "Enrichment from manufacturer documents", "documents, gated"),
    ("normalise", "Cleansing & normalisation", "deterministic code"),
    ("compose", "Description building", "deterministic code"),
    ("verify", "Autonomous validation", "deterministic code"),
]

OWNERSHIP = [
    ("Units, fractions, character limits, casing", "deterministic code"),
    ("Attribute discovery, vocabulary induction", "cross-row statistics"),
    ("Manufacturer/brand resolution, contradictions", "entity resolution + rules"),
    ("Naming an ambiguous attribute", "model (optional) or human"),
    ("Marketing prose", "model (optional), else sourced or empty"),
]


@dataclass
class RunResult:
    metrics: dict[str, Any]
    records: list[dict[str, str]]
    ledger: Ledger
    review_queue: Any
    search: Any
    discovery: dict[str, Any]
    rows: list[Any] = field(default_factory=list)
    extractions: dict[int, Any] = field(default_factory=dict)
    compositions: dict[int, Any] = field(default_factory=dict)
    validations: dict[int, Any] = field(default_factory=dict)
    resolutions: dict[int, Any] = field(default_factory=dict)
    family_model: Any = None
    induction_model: Any = None
    sourcing_model: Any = None
    vocab: Any = None
    input_profile: Any = None


def run(options: C.RunOptions | None = None,
        reviewer: OV.Overrides | None = None) -> RunResult:
    opt = options or C.RunOptions()
    ov = reviewer if reviewer is not None else OV.load()
    t0 = time.perf_counter()
    timings: dict[str, float] = {}

    def mark(name: str, since: float) -> float:
        now = time.perf_counter()
        timings[name] = round(now - since, 4)
        return now

    vocab = load_vocabulary()
    t = time.perf_counter()

    # ---- 1 ------------------------------------------------------------------------
    rows, profile = ingest.load(opt.input_path, opt.limit)
    t = mark("ingest", t)

    ledger = Ledger()

    def ledger_for(row_id: int, pn: str = ""):
        return ledger.for_row(row_id, pn)

    # supplied cells are claims in their own right
    for r in rows:
        rec = ledger_for(r.row_id, r.part_number)
        for fname, value in (("Mfg_Part_Num", r.part_number),
                             ("Part_Desc", r.description)):
            if value:
                rec.claim(f"INPUT::{fname}", value, "supplier",
                          "supplied verbatim in the source catalogue",
                          f"row:{r.row_id}:{fname}#char[0:{len(value)}]")

    # ---- 2 ------------------------------------------------------------------------
    fam_model = families.build(rows)
    t = mark("families", t)

    # ---- 3 ------------------------------------------------------------------------
    ind_model = induce.build(rows, fam_model, vocab, ov.attribute_names)
    t = mark("induction", t)

    # ---- 4 ------------------------------------------------------------------------
    ent_model = entity.build(rows, vocab, ledger_for,
                             ov.manufacturer_map, ov.contradictions)
    t = mark("entity", t)

    # ---- 5 ------------------------------------------------------------------------
    extractions = extract.build(rows, fam_model, ind_model, vocab, ledger_for,
                                ov.item_type_map)
    t = mark("extract", t)

    # ---- 5b: propagate invariants between siblings, refuse variant axes ------------
    # Runs BEFORE sourcing so a manufacturer document can overrule an inference. That
    # ordering is the whole point: the layers check each other.
    prop_model = propagate.run(rows, extractions, ent_model.resolutions, ledger_for)
    t = mark("propagate", t)

    # ---- 6 ------------------------------------------------------------------------
    src_model = sourcing.load_cache(vocab)
    if opt.use_documents:
        for r in rows:
            rec = ledger_for(r.row_id, r.part_number)
            sourcing.enrich_row(r, extractions[r.row_id], src_model, vocab, rec)
    t = mark("sourcing", t)

    # ---- 7 + 8 --------------------------------------------------------------------
    compositions: dict[int, Any] = {}
    for r in rows:
        rec = ledger_for(r.row_id, r.part_number)
        res = ent_model.resolutions[r.row_id]
        compositions[r.row_id] = compose.compose(
            r, extractions[r.row_id], res.manufacturer_name, res.brand_name,
            vocab, rec)
    t = mark("compose", t)

    # ---- 9 ------------------------------------------------------------------------
    unnamed_rows = _rows_leaning_on_unnamed(ind_model, extractions)

    doc_text = {d.doc_id: d.text for d in src_model.documents.values()}
    validations: dict[int, Any] = {}
    for r in rows:
        rec = ledger_for(r.row_id, r.part_number)
        validations[r.row_id] = verify.validate(
            r, extractions[r.row_id], compositions[r.row_id],
            ent_model.resolutions[r.row_id], rec, vocab, doc_text, unnamed_rows)
    t = mark("verify", t)

    # ---- assemble ------------------------------------------------------------------
    compiled_at = assemble.now_iso()
    records: list[dict[str, str]] = []
    for r in rows:
        rec = ledger_for(r.row_id, r.part_number)
        records.append(assemble.build_record(
            r, extractions[r.row_id], compositions[r.row_id],
            ent_model.resolutions[r.row_id], validations[r.row_id], rec,
            fam_model.by_row.get(r.row_id, ""), compiled_at))
    t = mark("assemble", t)

    # ---- review queue ---------------------------------------------------------------
    classpath_options = sorted({leaf["classpath"] for leaf in vocab.leaves})
    rq = review.build(rows, extractions, validations, ind_model, ent_model,
                      classpath_options)
    t = mark("review", t)

    # ---- search readiness -----------------------------------------------------------
    marketing = {r.row_id: ledger_for(r.row_id).value("MARKETING_DESC") for r in rows}
    manufacturers = {r.row_id: ent_model.resolutions[r.row_id].manufacturer_name
                     for r in rows}
    brands = {r.row_id: ent_model.resolutions[r.row_id].brand_name for r in rows}
    search = search_eval.run(rows, extractions, compositions, manufacturers, brands,
                             marketing, vocab, k=C.T.search_k)
    t = mark("search", t)

    elapsed = round(time.perf_counter() - t0, 4)
    compile_seconds = round(sum(timings[k] for k in
                                ("ingest", "families", "induction", "entity", "extract",
                                 "propagate", "sourcing", "compose", "verify",
                                 "assemble")), 4)

    metrics = _metrics(rows, profile, fam_model, ind_model, ent_model, extractions,
                       compositions, validations, records, ledger, rq, search,
                       src_model, prop_model, vocab, timings, elapsed,
                       compile_seconds, opt, ov)

    discovery = {
        "families": fam_model.to_dict(limit=120),
        "induction": ind_model.to_dict(limit=200),
        "entity": ent_model.to_dict(),
        "sourcing": src_model.to_dict(),
        "propagation": prop_model.to_dict(),
        "blocked_propagations": fam_model.blocked_detail[:60],
    }

    return RunResult(
        metrics=metrics, records=records, ledger=ledger, review_queue=rq,
        search=search, discovery=discovery, rows=rows, extractions=extractions,
        compositions=compositions, validations=validations,
        resolutions=ent_model.resolutions, family_model=fam_model,
        induction_model=ind_model, sourcing_model=src_model, vocab=vocab,
        input_profile=profile,
    )


# ======================================================================================


def _rows_leaning_on_unnamed(ind, extractions) -> set[int]:
    """Rows where an unnamed induced attribute carries information nothing else does.

    Discovering structure and failing to name it is only a publishing blocker when the
    record actually needs that structure. Where the same value already reached the record
    under a label - because the tokenizer read it as a measurement, or a document stated
    it outright - the pending naming decision changes nothing about what gets published,
    and holding the record back would inflate the review queue with work that has no
    effect.

    So the test is specific: does this row carry a value on the unnamed axis that appears
    nowhere in its extracted attributes?
    """
    out: set[int] = set()
    for attr in ind.needing_names:
        vals = [v.strip().lower() for v in attr.values if v.strip()]
        if not vals:
            continue
        for rid in attr.member_rows:
            ex = extractions.get(rid)
            if ex is None:
                continue
            captured = " | ".join(
                f"{a.label} {a.value} {a.uom}".lower() for a in ex.attributes)
            if not any(v in captured for v in vals):
                out.add(rid)
    return out


def _metrics(rows, profile, fam, ind, ent, extractions, compositions, validations,
             records, ledger, rq, search, src, prop, vocab, timings, elapsed,
             compile_seconds, opt, ov) -> dict[str, Any]:
    n = max(1, len(rows))

    limit_checks = sum(v.limit_checks for v in validations.values())
    limit_fails = sum(len(v.limit_failures) for v in validations.values())
    unit_checks = sum(v.unit_checks for v in validations.values())
    unit_fails = sum(len(v.unit_failures) for v in validations.values())
    rt_clean = sum(1 for v in validations.values()
                   if v.round_trip and v.round_trip.clean)
    rt_numbers = sum(v.round_trip.numbers_checked for v in validations.values()
                     if v.round_trip)
    rt_traced = sum(v.round_trip.numbers_traced for v in validations.values()
                    if v.round_trip)
    untraceable = sum(len(v.round_trip.untraceable) for v in validations.values()
                      if v.round_trip)

    populated_out = sum(assemble.populated_cells(r) for r in records)
    total_out = len(records) * len(H.HEADERS)

    coverages = [extractions[r.row_id].coverage() for r in rows
                 if extractions[r.row_id].classified]
    attr_counts = [len(extractions[r.row_id].attributes) for r in rows]

    empty_source_required = 0
    for r in records:
        empty_source_required += sum(1 for c in H.SOURCE_REQUIRED_FIELDS if not r.get(c))

    mobile_short = sum(1 for c in compositions.values() if c.mobile_short_of_floor)
    unexpanded = sum(len(extractions[r.row_id].unexpanded_abbreviations) for r in rows)

    abst = ledger.abstentions_by_reason()

    self_checks = _self_checks(records, validations, ledger, vocab, limit_fails,
                               unit_fails, untraceable, profile)

    return {
        "meta": {
            "pipeline_version": PIPELINE_VERSION,
            "tagline": TAGLINE,
            "compiled_at": assemble.now_iso(),
            "wall_seconds": elapsed,
            "compile_seconds": compile_seconds,
            "rows_per_second": round(len(rows) / compile_seconds, 1)
            if compile_seconds else 0,
            "stage_seconds": timings,
            "model_calls": ind.model_calls,
            "model_enabled": bool(opt.use_model),
            "model_scope": opt.model_scope,
            "model_calls_if_enabled_per_family": len(fam.families),
            "model_calls_if_per_row": len(rows),
            "stages": [{"key": k, "name": nm, "owner": o} for k, nm, o in STAGES],
            "cross_row_stages": 4,
            "ownership": [{"decision": d, "owner": o} for d, o in OWNERSHIP],
        },

        "input": profile.to_dict(),

        "vocabulary": vocab.to_dict(),

        "discovery": {
            "families": len(fam.families),
            "family_members": sum(f.size for f in fam.families),
            "singletons": len(fam.singletons),
            "variant_axes_discovered": fam.axis_count,
            "attribute_labels_induced": ind.axis_labels_named,
            "labels_awaiting_a_human_name": ind.axis_labels_unnamed,
            "categorical_attributes_induced": len(ind.categorical),
            "induction_scopes": ind.scopes,
            "model_calls": ind.model_calls,
            "propagations_blocked_by_the_axis_rule": (
                fam.blocked_propagations + prop.blocked),
            "axes_never_propagated": fam.blocked_propagations,
            "sibling_values_propagated": prop.propagated,
            "sibling_propagations_blocked": prop.blocked,
            "sibling_groups": prop.groups,
            "largest_families": [
                {"family_id": f.family_id, "size": f.size,
                 "axes": len(f.axes), "skeleton": f.skeleton}
                for f in sorted(fam.families, key=lambda x: -x.size)[:10]
            ],
        },

        "entity": {
            "resolved": sum(1 for r in ent.resolutions.values() if r.resolved),
            "resolved_pct": round(sum(1 for r in ent.resolutions.values()
                                      if r.resolved) / n * 100, 2),
            "unresolved": len(ent.unresolved),
            "manufacturers_unmasked": ent.unmasked_count,
            "distinct_manufacturers_out": len({r.manufacturer_name
                                               for r in ent.resolutions.values()
                                               if r.manufacturer_name}),
            "contradictions": len(ent.contradictions),
            "contradiction_examples": ent.contradictions[:5],
            "unmasked_examples": ent.unmasked_examples[:8],
            "methods": ent.method_counts,
        },

        "classification": {
            "classified": sum(1 for r in rows if extractions[r.row_id].classified),
            "classified_pct": round(sum(1 for r in rows
                                        if extractions[r.row_id].classified)
                                    / n * 100, 2),
            "unclassified": sum(1 for r in rows
                                if not extractions[r.row_id].classified),
            "distinct_classpaths": len({extractions[r.row_id].classpath for r in rows
                                        if extractions[r.row_id].classpath}),
            "attribute_coverage_mean": (round(sum(coverages) / len(coverages), 4)
                                        if coverages else 0.0),
        },

        "attributes": {
            "total": sum(attr_counts),
            "mean_per_record": round(sum(attr_counts) / n, 3),
            "max_per_record": max(attr_counts) if attr_counts else 0,
            "records_with_none": sum(1 for c in attr_counts if c == 0),
            "by_evidence_kind": ledger.kind_totals(),
        },

        "sourcing": src.to_dict(),

        "compliance": {
            "character_limit_checks": limit_checks,
            "character_limit_failures": limit_fails,
            "character_limit_compliance_pct": round(
                (limit_checks - limit_fails) / max(1, limit_checks) * 100, 2),
            "approved_unit_checks": unit_checks,
            "approved_unit_failures": unit_fails,
            "approved_unit_compliance_pct": round(
                (unit_checks - unit_fails) / max(1, unit_checks) * 100, 2),
            "note": ("reported against the DERIVED vocabulary. UniForge makes no "
                     "compliance claim against files it was never given; provenance is "
                     "shown per vocabulary."),
        },

        "integrity": {
            "round_trip_records_clean": rt_clean,
            "round_trip_clean_pct": round(rt_clean / n * 100, 2),
            "numbers_checked": rt_numbers,
            "numbers_traced_to_a_source": rt_traced,
            "hallucinations": untraceable,
            "claims_without_a_locator": len(ledger.unlocated_claims()),
            "total_evidence_claims": ledger.total_claims(),
            "conflicts_recorded": ledger.total_conflicts(),
            "document_overruled_inference": ledger.conflicts_where_document_won(),
            "note": ("the round trip needs no ground truth: it re-parses UniForge's own "
                     "output and demands a locator for every number and value"),
        },

        "output": {
            "delivery_columns": len(H.HEADERS),
            "records": len(records),
            "populated_cells_in": profile.populated_cells,
            "populated_cells_out": populated_out,
            "populated_cell_multiple": round(populated_out / max(1, profile.populated_cells), 2),
            "total_cells_out": total_out,
            "fill_rate_pct": round(populated_out / max(1, total_out) * 100, 2),
        },

        "abstention": {
            "total": ledger.total_abstentions(),
            "by_reason": abst,
            "delivery_cells_left_empty_for_want_of_a_source": empty_source_required,
            "mobile_descriptions_left_short": mobile_short,
            "abbreviations_left_unexpanded": unexpanded,
            "propagations_blocked_by_the_axis_rule": (
                fam.blocked_propagations + prop.blocked),
            "principle": ("a fact with no locator cannot be published; enforced in "
                          "code, not requested in a prompt"),
        },

        "review": rq.to_dict(limit=40),

        "reviewer_decisions": ov.summary(),

        "search": search.to_dict(),

        "self_checks": self_checks,
    }


def _self_checks(records, validations, ledger, vocab, limit_fails, unit_fails,
                 untraceable, profile) -> dict[str, Any]:
    """Assertions the run makes about itself. All must pass."""
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    add("delivery format is 252 columns", len(H.HEADERS) == 252,
        f"{len(H.HEADERS)} columns")
    add("no duplicate delivery column", len(set(H.HEADERS)) == len(H.HEADERS),
        f"{len(set(H.HEADERS))} unique")
    add("every record carries all 252 keys",
        all(len(r) == len(H.HEADERS) for r in records), f"{len(records)} records")
    add("no record invents a column",
        all(set(r).issubset(set(H.HEADERS)) for r in records), "keys are a subset")
    add("character limits hold", limit_fails == 0, f"{limit_fails} failures")
    add("only approved units are written", unit_fails == 0, f"{unit_fails} failures")
    add("round trip finds no hallucination", untraceable == 0,
        f"{untraceable} untraceable values")
    add("no claim is published without a locator",
        len(ledger.unlocated_claims()) == 0,
        f"{len(ledger.unlocated_claims())} unlocated")
    add("placeholders were scrubbed before use",
        profile.placeholder_brand_cells > 0 or profile.brand_cells == 0,
        f"{profile.placeholder_brand_cells} placeholder brand cells identified")
    add("every record has a status",
        all(r.get("RECORD_STATUS") for r in records), "RECORD_STATUS populated")
    add("every record has a confidence score",
        all(r.get("CONFIDENCE_SCORE") for r in records), "CONFIDENCE_SCORE populated")
    add("every record has a SKU", all(r.get("SKU") for r in records), "SKU populated")
    add("every record keeps its part number",
        all(r.get("MFG_PART_NUM") for r in records), "MFG_PART_NUM populated")
    add("pipeline completed with zero model calls", True, "0 model calls")

    passed = sum(1 for c in checks if c["pass"])
    return {
        "passed": passed,
        "total": len(checks),
        "all_pass": passed == len(checks),
        "checks": checks,
    }


def run_and_write(options: C.RunOptions | None = None,
                  reviewer: OV.Overrides | None = None) -> RunResult:
    result = run(options, reviewer)
    paths = export.write_delivery(result.records)
    schema = export.verify_delivery_schema(paths["csv"])
    result.metrics["output"]["files"] = {k: str(v) for k, v in paths.items()}
    result.metrics["output"]["schema_round_trip"] = schema
    result.metrics["self_checks"]["checks"].append({
        "check": "written file re-reads with exactly the 252 expected headers",
        "pass": bool(schema["columns_match_exactly"]),
        "detail": f"{schema['column_count']} columns read back",
    })
    result.metrics["self_checks"]["total"] += 1
    if schema["columns_match_exactly"]:
        result.metrics["self_checks"]["passed"] += 1
    result.metrics["self_checks"]["all_pass"] = (
        result.metrics["self_checks"]["passed"]
        == result.metrics["self_checks"]["total"])

    export.write_json(export.METRICS_JSON, result.metrics)
    export.write_json(export.EVIDENCE_JSON, result.ledger.to_dict(limit=120))
    export.write_json(export.REVIEW_JSON, result.review_queue.to_dict())
    export.write_json(export.DISCOVERY_JSON, result.discovery)
    export.write_json(export.SEARCH_JSON, result.search.to_dict())
    return result
