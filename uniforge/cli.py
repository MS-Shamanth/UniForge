"""Command line entry point.

    python -m uniforge.cli compile              compile the catalogue, write everything
    python -m uniforge.cli compile --limit 200  compile a slice
    python -m uniforge.cli report               print the headline numbers
    python -m uniforge.cli inspect 0            everything known about one record
    python -m uniforge.cli source --discover    build candidate URLs, gate them, report
    python -m uniforge.cli serve                run the prototype web app
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config as C
from . import export, pipeline


def _fmt(n: float, width: int = 0) -> str:
    s = f"{n:,.2f}" if isinstance(n, float) else f"{n:,}"
    return s.rjust(width) if width else s


def cmd_compile(args: argparse.Namespace) -> int:
    opt = C.RunOptions(
        limit=args.limit,
        use_documents=not args.no_documents,
        use_model=args.model,
        input_path=Path(args.input) if args.input else None,
        verbose=args.verbose,
    )
    result = pipeline.run_and_write(opt)
    m = result.metrics
    print_report(m)
    out = C.DATA_OUT
    print()
    print("written:")
    for name in (export.DELIVERY_CSV, export.DELIVERY_XLSX, export.METRICS_JSON,
                 export.EVIDENCE_JSON, export.REVIEW_JSON, export.DISCOVERY_JSON,
                 export.SEARCH_JSON):
        p = out / name
        if p.exists():
            print(f"  {p}  ({p.stat().st_size:,} bytes)")
    return 0 if m["self_checks"]["all_pass"] else 1


def print_report(m: dict) -> None:
    meta, inp, disc = m["meta"], m["input"], m["discovery"]
    ent, cls, attr = m["entity"], m["classification"], m["attributes"]
    comp, integ, out = m["compliance"], m["integrity"], m["output"]
    abst, rev, srch, sc = m["abstention"], m["review"], m["search"], m["self_checks"]
    src = m["sourcing"]

    def h(title: str) -> None:
        print()
        print(title)
        print("-" * len(title))

    print()
    print("UniForge  ·  " + meta["tagline"])
    print(f"{meta['pipeline_version']}   {inp['row_count']:,} rows compiled in "
          f"{meta['compile_seconds']}s  ({meta['rows_per_second']:,} rows/s)")

    h("what arrived")
    print(f"  source file                  {inp['source_file']}")
    print(f"  columns                      {len(inp['columns'])}")
    print(f"  populated input cells        {inp['populated_cells']:,} of "
          f"{inp['total_cells']:,}")
    print(f"  placeholder brand cells      {inp['placeholder_brand_cells']:,} of "
          f"{inp['brand_cells']:,}  ({inp['placeholder_brand_pct']}%)")
    print(f"  mean description length      {inp['desc_len_mean']} chars "
          f"(min {inp['desc_len_min']}, max {inp['desc_len_max']})")

    h("what it learned from the catalogue")
    print(f"  families                     {disc['families']:,}")
    print(f"  variant axes discovered      {disc['variant_axes_discovered']:,}")
    print(f"  attribute labels induced     {disc['attribute_labels_induced']:,}")
    print(f"  awaiting one human name      {disc['labels_awaiting_a_human_name']:,}")
    print(f"  categorical attributes       {disc['categorical_attributes_induced']:,}")
    print(f"  propagations blocked         {disc['propagations_blocked_by_the_axis_rule']:,}"
          f"   (variant axes are never propagated)")
    print(f"  model calls                  {disc['model_calls']}")

    h("entities")
    print(f"  manufacturers resolved       {ent['resolved']:,} "
          f"({ent['resolved_pct']}%)")
    print(f"  unmasked from distributors   {ent['manufacturers_unmasked']:,}")
    print(f"  distinct manufacturers out   {ent['distinct_manufacturers_out']:,}")
    print(f"  contradictions found         {ent['contradictions']:,}")
    for c in ent["contradiction_examples"][:2]:
        print(f"      · {c['brand_named']} is a brand of {c['brand_owner']}, "
              f"but the record names {c['manufacturer_named']}")

    h("enrichment from manufacturer documents")
    print(f"  candidates considered        {src['candidates_considered']:,}")
    print(f"  admitted (manufacturer)      {src['admitted']:,}")
    print(f"  rejected before request      {src['rejected_count']:,}   "
          f"{', '.join(sorted({d['domain'] for d in src['rejected_before_request']}))}")
    print(f"  blocked by the site          {src['blocked_count']:,}   "
          f"{', '.join(sorted({d['domain'] for d in src['blocked_by_site']}))}")
    print(f"  rows enriched                {src['rows_enriched']:,}")
    print(f"  attributes each              {src['attributes_before_mean']} -> "
          f"{src['attributes_after_mean']}  (x{src['attribute_multiple']})")
    print(f"  marketing descriptions       {src['marketing_descriptions_written']:,}")
    print(f"  feature bullets extracted    {src['feature_bullets_extracted']:,}")
    print(f"  document references mapped   {src['document_references_mapped']:,}")
    print(f"  inferences corrected by doc  "
          f"{src['inferences_corrected_by_a_document']:,}")
    for a in src["abbreviations_evidenced"][:2]:
        print(f"      · {a['abbreviation']} now evidenced: {a['domain']} writes "
              f"\"{a['quote'][:60]}\"")

    h("compliance and integrity")
    print(f"  character-limit compliance   {comp['character_limit_compliance_pct']}%  "
          f"({comp['character_limit_checks']:,} checks)")
    print(f"  approved-unit compliance     {comp['approved_unit_compliance_pct']}%  "
          f"({comp['approved_unit_checks']:,} checks)")
    print(f"  round trip clean             {integ['round_trip_clean_pct']}%   "
          f"{integ['hallucinations']} hallucinations")
    print(f"  numbers traced to a source   {integ['numbers_traced_to_a_source']:,} of "
          f"{integ['numbers_checked']:,}")
    print(f"  claims without a locator     {integ['claims_without_a_locator']}")
    print(f"  document overruled inference {integ['document_overruled_inference']:,}")
    print(f"  populated cells in -> out    {out['populated_cells_in']:,} -> "
          f"{out['populated_cells_out']:,}  (x{out['populated_cell_multiple']})")

    h("search readiness")
    g, tq, ex = srch["vocabulary_gap"], srch["trade_queries"], srch["exact_item"]
    print(f"  vocabulary-gap queries       {g['query_count']:,}")
    print(f"    recall@{srch['k']}                  "
          f"{g['recall_at_k_before'] * 100:.1f}%  ->  "
          f"{g['recall_at_k_after'] * 100:.1f}%")
    print(f"    zero-result rate           "
          f"{g['zero_result_rate_before'] * 100:.1f}%  ->  "
          f"{g['zero_result_rate_after'] * 100:.1f}%")
    print(f"  trade queries                {tq['query_count']:,}")
    print(f"    MRR@{srch['k']}                     "
          f"{tq['mrr_at_k_before']:.3f}  ->  {tq['mrr_at_k_after']:.3f}")
    print(f"  exact-item recall@{srch['k']}         "
          f"{ex['recall_at_k_before'] * 100:.1f}%  ->  "
          f"{ex['recall_at_k_after'] * 100:.1f}%   <- {ex['direction']}")

    h("refusing to guess")
    print(f"  cells left empty             "
          f"{abst['delivery_cells_left_empty_for_want_of_a_source']:,}")
    print(f"  mobile descs left short      {abst['mobile_descriptions_left_short']:,}")
    print(f"  abbreviations unexpanded     {abst['abbreviations_left_unexpanded']:,}")
    print(f"  propagations blocked         "
          f"{abst['propagations_blocked_by_the_axis_rule']:,}")

    h("human in the loop")
    print(f"  auto-publish                 {rev['auto_publish_records']:,} "
          f"({rev['auto_publish_pct']}%)")
    print(f"  to review                    {rev['review_records']:,} "
          f"({rev['review_pct']}%)")
    print(f"  review ACTIONS               {rev['action_count']:,}  "
          f"({rev['records_per_action']} records per decision)")
    for b in rev["blockers"][:5]:
        if not b["records"]:
            continue
        print(f"      · {b['blocker']:<42} {b['records']:>5} records, "
              f"{b['actions']:>4} actions -> {b['one_action_clears']} each")

    h("self checks")
    print(f"  {sc['passed']}/{sc['total']} passing")
    for c in sc["checks"]:
        if not c["pass"]:
            print(f"      FAIL  {c['check']}  ({c['detail']})")


def cmd_report(args: argparse.Namespace) -> int:
    p = C.DATA_OUT / export.METRICS_JSON
    if not p.exists():
        print("no metrics yet. run:  python -m uniforge.cli compile")
        return 1
    print_report(json.loads(p.read_text(encoding="utf-8")))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    opt = C.RunOptions(limit=args.limit)
    result = pipeline.run(opt)
    rid = args.row_id
    if rid not in result.extractions:
        print(f"row {rid} not in this run (0..{len(result.rows) - 1})")
        return 1
    row = next(r for r in result.rows if r.row_id == rid)
    ex = result.extractions[rid]
    comp = result.compositions[rid]
    val = result.validations[rid]
    res = result.resolutions[rid]
    rec = result.ledger.records[rid]

    print()
    print(f"row {rid}   {row.part_number}")
    print(f"  supplied:  {row.description}")
    print(f"  brands:    E1={row.e1_brand or '(placeholder)'}  "
          f"Unilog={row.unilog_brand or '(placeholder)'}  "
          f"DIB={row.dib_brand or '(placeholder)'}")
    print(f"  invoiced by: {row.part_manuf}")
    print()
    print(f"  manufacturer  {res.manufacturer_name}  [{res.method}, "
          f"score {res.score:.2f}]")
    if res.unmasked_from:
        print(f"                unmasked from \"{res.unmasked_from}\"")
    print(f"  brand         {res.brand_name}")
    print(f"  classpath     {ex.classpath or '(unclassified)'}")
    print(f"  family        {result.family_model.by_row.get(rid, '(singleton)')}")
    if res.contradiction:
        print()
        print("  CONTRADICTION")
        print(f"    {res.contradiction['explanation']}")
        print(f"    confidence {res.contradiction['confidence']} -> "
              f"{res.contradiction['action']}")
    print()
    print(f"  INVOICE_DESC   ({len(comp.invoice):>4}/40)   {comp.invoice}")
    print(f"  MOBILE_DESC    ({len(comp.mobile):>4}/80)   {comp.mobile}"
          + ("   [below the 60-char floor: withheld padding]"
             if comp.mobile_short_of_floor else ""))
    print(f"  SHORT_DESC     ({len(comp.short):>4}/120)  {comp.short}")
    print(f"  PRODUCT_TITLE  ({len(comp.title):>4}/150)  {comp.title}")
    print(f"  LONG_DESC      ({len(comp.long):>4}/1000) {comp.long}")
    mk = rec.value("MARKETING_DESC")
    print(f"  MARKETING_DESC ({len(mk):>4})       "
          f"{mk[:110] + '...' if len(mk) > 110 else mk or '(empty: not sourced, never generated)'}")
    print()
    print(f"  attributes ({len(ex.attributes)})")
    for a in ex.attributes:
        v = f"{a.value} {a.uom}".strip()
        print(f"    {a.label:<26} {v:<26} [{a.kind}]")
        print(f"      {a.rule}")
        if a.locator:
            print(f"      {a.locator}")
    if ex.unexpanded_abbreviations:
        print(f"  abbreviations left unexpanded: "
              f"{', '.join(ex.unexpanded_abbreviations)}")
    print()
    print(f"  confidence {val.confidence}  ({val.band})   status: {val.status}")
    if val.reasons:
        for r_ in val.reasons:
            print(f"    · {r_}")
    if val.round_trip:
        print(f"  round trip: {val.round_trip.numbers_traced}/"
              f"{val.round_trip.numbers_checked} numbers traced, "
              f"{len(val.round_trip.untraceable)} untraceable")
    print()
    print(f"  abstentions ({len(rec.abstentions)})")
    for a in rec.abstentions[:12]:
        print(f"    {a['field']:<22} {a['reason']}")
    return 0


def cmd_source(args: argparse.Namespace) -> int:
    from . import sourcing
    from .vocab import load_vocabulary
    vocab = load_vocabulary()
    model = sourcing.load_cache(vocab)
    d = model.to_dict()
    print()
    print("sourcing gate")
    print("-------------")
    print(f"  documents cached             {d['documents_cached']}")
    print(f"  reconstructed fixtures       {d['reconstructed']}")
    print(f"  candidates considered        {d['candidates_considered']}")
    print(f"  admitted                     {d['admitted']}")
    print()
    print("  rejected BEFORE any request was made:")
    for r in d["rejected_before_request"]:
        print(f"    {r['domain']:<22} {r['reason']}")
    print()
    print("  admitted but refused by the site:")
    for r in d["blocked_by_site"]:
        print(f"    {r['domain']:<22} {r['reason']}")
    print()
    print(f"  discarded because the page did not name the part: "
          f"{d['discarded_because_page_did_not_name_the_part']}")
    if args.discover:
        print()
        print("  candidate URL construction (gate applied, nothing requested):")
        for mfr, domains in sorted(vocab.manufacturer_domains.items())[:12]:
            for dom in sorted(domains):
                url = f"https://www.{dom}/products/EXAMPLE"
                verdict, reason = sourcing.classify_domain(url, mfr, vocab)
                print(f"    {verdict:<9} {dom:<26} {reason}")
    if not C.ENV_ALLOW_LIVE_FETCH and args.fetch:
        print()
        print("  live fetching is off. To enable it:")
        print('    $env:UNIFORGE_ALLOW_FETCH = "1"')
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn
    print(f"UniForge prototype on http://{args.host}:{args.port}")
    uvicorn.run("server.app:app", host=args.host, port=args.port, reload=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="uniforge", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compile", help="compile the catalogue and write all artefacts")
    c.add_argument("--limit", type=int, default=None)
    c.add_argument("--input", type=str, default=None)
    c.add_argument("--no-documents", action="store_true",
                   help="skip document enrichment to see the zero-source baseline")
    c.add_argument("--model", action="store_true",
                   help="allow optional model calls (charged per family, not per row)")
    c.add_argument("--verbose", action="store_true")
    c.set_defaults(func=cmd_compile)

    r = sub.add_parser("report", help="print the last run's headline numbers")
    r.set_defaults(func=cmd_report)

    i = sub.add_parser("inspect", help="everything known about one record")
    i.add_argument("row_id", type=int)
    i.add_argument("--limit", type=int, default=None)
    i.set_defaults(func=cmd_inspect)

    s = sub.add_parser("source", help="report the sourcing gate")
    s.add_argument("--discover", action="store_true")
    s.add_argument("--fetch", action="store_true")
    s.set_defaults(func=cmd_source)

    v = sub.add_parser("serve", help="run the prototype web app")
    v.add_argument("--host", default="127.0.0.1")
    v.add_argument("--port", type=int, default=8000)
    v.set_defaults(func=cmd_serve)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
