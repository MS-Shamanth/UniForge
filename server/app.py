"""FastAPI layer over the compiler.

The web app is a view onto a real run, not a mockup with numbers typed into it. Every
endpoint here reads the same objects `uniforge.pipeline.run()` produces, so anything the
UI shows can be reproduced from the CLI.

Two endpoints do real work rather than reporting it:

    POST /api/upload            compiles an uploaded catalogue through the same pipeline
    POST /api/review/decide     records a reviewer decision and recompiles, so "name it
                                once, applied to 98 products" is a measured result

There is no authentication on this server. It is a local prototype for a hackathon
submission and binds to 127.0.0.1 by default. Do not expose it publicly as-is: the upload
and recompile endpoints accept arbitrary spreadsheets and trigger real work.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from uniforge import PIPELINE_VERSION, TAGLINE
from uniforge import config as C
from uniforge import export, overrides as OV, pipeline, sourcing
from uniforge import search_eval, trade_tokens as TT
from uniforge.seed import headers as H

app = FastAPI(title="UniForge", version=PIPELINE_VERSION,
              description="The product-content compiler. " + TAGLINE)

# In a hosted deployment the bundle is served from the same origin, so CORS only needs to
# cover the local Vite dev servers. UNIFORGE_CORS_ORIGINS can add more, comma separated.
_DEV_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:4173", "http://127.0.0.1:4173",
]
_EXTRA_ORIGINS = [
    o.strip() for o in os.environ.get("UNIFORGE_CORS_ORIGINS", "").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEV_ORIGINS + _EXTRA_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Free hosting tiers are memory-bound, so the deploy can cap how many rows a run
# compiles. Unset or 0 means the whole catalogue.
def _row_limit() -> int | None:
    raw = os.environ.get("UNIFORGE_ROW_LIMIT", "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if n > 0 else None


# ======================================================================================
# one cached run, rebuilt on demand
# ======================================================================================
_KEEP = object()   # sentinel: "leave this setting as it is"


class Run:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._result: pipeline.RunResult | None = None
        self._built_at: float = 0.0
        self._input: Path | None = None
        self._limit: int | None = _row_limit()
        self._building = False
        self._error: str | None = None

    @property
    def ready(self) -> bool:
        return self._result is not None

    def status(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "building": self._building,
            "error": self._error,
            "built_at": self._built_at,
            "input": self._input.name if self._input else None,
            "limit": self._limit,
        }

    def get(self) -> pipeline.RunResult:
        with self._lock:
            if self._result is None:
                self._build()
            assert self._result is not None
            return self._result

    def rebuild(self, input_path: Path | None = _KEEP,
                limit: int | None = _KEEP) -> pipeline.RunResult:
        """`_KEEP` leaves a setting alone; passing None genuinely clears it.

        Without the sentinel, "restore the bundled catalogue" could not be expressed:
        `input_path=None` would be indistinguishable from "don't change the input".
        """
        with self._lock:
            if input_path is not _KEEP:
                self._input = input_path
            if limit is not _KEEP:
                self._limit = limit
            self._build()
            assert self._result is not None
            return self._result

    def _build(self) -> None:
        self._building = True
        self._error = None
        try:
            opt = C.RunOptions(input_path=self._input, limit=self._limit)
            self._result = pipeline.run_and_write(opt)
            self._built_at = time.time()
        except Exception as exc:                      # surfaced to the client
            self._error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self._building = False


RUN = Run()


# ======================================================================================
# helpers
# ======================================================================================
def _record_summary(r: pipeline.RunResult, row_id: int) -> dict[str, Any]:
    row = next((x for x in r.rows if x.row_id == row_id), None)
    if row is None:
        raise HTTPException(404, f"row {row_id} not found")
    ex = r.extractions[row_id]
    comp = r.compositions[row_id]
    val = r.validations[row_id]
    res = r.resolutions[row_id]
    rec = r.ledger.records[row_id]
    src = r.sourcing_model.per_row.get(row_id)
    return {
        "row_id": row_id,
        "sku": f"UF-{row_id + 1:06d}",
        "part_number": row.part_number,
        "input": {
            "Mfg_Part_Num": row.raw.get("Mfg_Part_Num", ""),
            "Part_Desc": row.raw.get("Part_Desc", ""),
            "E1_Brand": row.raw.get("E1_Brand", ""),
            "Unilog_Brand": row.raw.get("Unilog_Brand", ""),
            "DIB_Brand": row.raw.get("DIB_Brand", ""),
            "Part_Manuf": row.raw.get("Part_Manuf", ""),
            "populated_cells": row.populated_input_cells,
        },
        "manufacturer": res.manufacturer_name,
        "manufacturer_code": res.manufacturer_code,
        "brand": res.brand_name,
        "brand_code": res.brand_code,
        "resolution": res.to_dict(),
        "classpath": ex.classpath,
        "leaf": ex.leaf,
        "item_type": ex.item_type,
        "classified": ex.classified,
        "family_id": r.family_model.by_row.get(row_id, ""),
        "descriptions": {
            "INVOICE_DESC": {"value": comp.invoice, "limit": 40,
                             "length": len(comp.invoice)},
            "MOBILE_DESC": {"value": comp.mobile, "limit": 80, "floor": 60,
                            "length": len(comp.mobile),
                            "below_floor": comp.mobile_short_of_floor},
            "SHORT_DESC": {"value": comp.short, "limit": 120,
                           "length": len(comp.short)},
            "PRODUCT_TITLE": {"value": comp.title, "limit": 150,
                              "length": len(comp.title)},
            "LONG_DESC": {"value": comp.long, "limit": 1000,
                          "length": len(comp.long)},
            "MARKETING_DESC": {"value": rec.value("MARKETING_DESC"), "limit": 2000,
                               "length": len(rec.value("MARKETING_DESC")),
                               "sourced_only": True},
            "SEARCH_KEYWORDS": {"value": comp.keywords, "limit": 255,
                                "length": len(comp.keywords)},
        },
        "attributes": [
            {**a.to_dict(), "sequence": a.sequence,
             "in_leaf_sequence": a.label in ex.attribute_sequence}
            for a in ex.attributes
        ],
        "attribute_sequence": ex.attribute_sequence,
        "attribute_coverage": ex.coverage(),
        "attributes_in_sequence": ex.in_sequence(),
        "features": [rec.value(f"FEATURE_{i:02d}") for i in range(1, 13)
                     if rec.value(f"FEATURE_{i:02d}")],
        "applications": [rec.value(f"APPLICATION_{i:02d}") for i in range(1, 5)
                         if rec.value(f"APPLICATION_{i:02d}")],
        "unexpanded_abbreviations": ex.unexpanded_abbreviations,
        "validation": val.to_dict(),
        "evidence": rec.to_dict(),
        "sourcing": src,
        "contradiction": res.contradiction,
    }


def _delivery_row(r: pipeline.RunResult, row_id: int) -> dict[str, str]:
    for rec in r.records:
        if rec.get("SKU") == f"UF-{row_id + 1:06d}":
            return rec
    raise HTTPException(404, f"row {row_id} not found")


# ======================================================================================
# meta
# ======================================================================================
@app.get("/api/health")
def health() -> dict[str, Any]:
    """Deliberately does NOT trigger a compile.

    A health check that waited for the pipeline would fail every cold start on a host
    that expects a response in a few seconds. This answers immediately and reports
    whether a run is ready, building, or has not started.
    """
    return {
        "ok": True,
        "pipeline_version": PIPELINE_VERSION,
        "tagline": TAGLINE,
        "run": RUN.status(),
        "delivery_columns": len(H.HEADERS),
        "row_limit": _row_limit(),
        "web_bundle_present": (C.ROOT / "web" / "dist" / "index.html").exists(),
    }


@app.get("/api/metrics")
def metrics() -> dict[str, Any]:
    return RUN.get().metrics


@app.get("/api/schema")
def schema() -> dict[str, Any]:
    from uniforge.seed import headers as HH
    return {
        "column_count": len(HH.HEADERS),
        "columns": HH.HEADERS,
        "groups": [{"group": g, "columns": cols} for g, cols in HH.GROUPS.items()],
        "source_required": sorted(HH.SOURCE_REQUIRED_FIELDS),
        "field_rules": [
            {"field": k, "max_chars": v.max_chars, "min_chars": v.min_chars,
             "casing": v.casing, "formula": v.formula}
            for k, v in C.FIELD_RULES.items()
        ],
    }


@app.get("/api/vocabulary")
def vocabulary() -> dict[str, Any]:
    r = RUN.get()
    v = r.vocab
    return {
        **v.to_dict(),
        "style_rules": [{"rule": k, "detail": d} for k, d in v.style_rules],
        "ambiguous_abbreviations": [
            {"abbreviation": k.upper(), "why_refused": why}
            for k, why in sorted(v.ambiguous.items())
        ],
        "safe_expansions": [
            {"abbreviation": k.upper(), "expansion": e, "scope": s}
            for k, (e, s) in sorted(v.abbreviations.items())
        ],
    }


# ======================================================================================
# records
# ======================================================================================
@app.get("/api/records")
def records(q: str = "", status: str = "", page: int = 1,
            size: int = Query(25, ge=1, le=200)) -> dict[str, Any]:
    r = RUN.get()
    needle = q.strip().lower()
    out: list[dict[str, Any]] = []
    for row in r.rows:
        val = r.validations[row.row_id]
        if status and val.status != status:
            continue
        ex = r.extractions[row.row_id]
        res = r.resolutions[row.row_id]
        comp = r.compositions[row.row_id]
        if needle:
            blob = " ".join([row.part_number, row.description, res.manufacturer_name,
                             res.brand_name, ex.classpath, comp.title]).lower()
            if needle not in blob:
                continue
        out.append({
            "row_id": row.row_id,
            "sku": f"UF-{row.row_id + 1:06d}",
            "part_number": row.part_number,
            "raw_description": row.description,
            "manufacturer": res.manufacturer_name,
            "brand": res.brand_name,
            "classpath": ex.classpath,
            "item_type": ex.item_type,
            "title": comp.title,
            "attributes": len(ex.attributes),
            "confidence": val.confidence,
            "band": val.band,
            "status": val.status,
            "reasons": val.reasons,
            "sourced": row.row_id in r.sourcing_model.per_row,
            "contradiction": bool(res.contradiction),
            "family_id": r.family_model.by_row.get(row.row_id, ""),
        })
    total = len(out)
    start = (page - 1) * size
    return {
        "total": total, "page": page, "size": size,
        "pages": max(1, (total + size - 1) // size),
        "items": out[start:start + size],
        "status_counts": {
            "auto-publish": sum(1 for v in r.validations.values()
                                if v.status == "auto-publish"),
            "review required": sum(1 for v in r.validations.values()
                                   if v.status == "review required"),
        },
    }


@app.get("/api/record/{row_id}")
def record(row_id: int) -> dict[str, Any]:
    return _record_summary(RUN.get(), row_id)


@app.get("/api/record/{row_id}/delivery")
def record_delivery(row_id: int) -> dict[str, Any]:
    r = RUN.get()
    rec = _delivery_row(r, row_id)
    return {
        "row_id": row_id,
        "columns": [
            {"column": c, "value": rec.get(c, ""), "group": H.HEADER_GROUP.get(c, ""),
             "source_required": c in H.SOURCE_REQUIRED_FIELDS,
             "populated": bool(str(rec.get(c, "")).strip())}
            for c in H.HEADERS
        ],
        "populated": sum(1 for c in H.HEADERS if str(rec.get(c, "")).strip()),
        "total": len(H.HEADERS),
    }


# ======================================================================================
# evidence: resolve a locator back to the characters that justify it
# ======================================================================================
@app.get("/api/locator")
def locator(ref: str) -> dict[str, Any]:
    r = RUN.get()
    parsed = TT.parse_locator(ref)
    if not parsed:
        raise HTTPException(400, f"not a locator: {ref}")
    start, end = parsed["start"], parsed["end"]

    if parsed["kind"] == "doc":
        doc = r.sourcing_model.documents.get(parsed["ref"])
        if not doc:
            raise HTTPException(404, f"document {parsed['ref']} not cached")
        text = doc.text
        ctx_a, ctx_b = max(0, start - 260), min(len(text), end + 260)
        return {
            "kind": "doc", "doc_id": doc.doc_id, "url": doc.url,
            "domain": doc.domain, "part_number": doc.part_number,
            "reconstructed": doc.reconstructed,
            "start": start, "end": end,
            "quote": text[start:end],
            "context_before": text[ctx_a:start],
            "context_after": text[end:ctx_b],
            "char_length": len(text),
        }

    # row:<id>:<field>#char[a:b]
    bits = parsed["ref"].split(":")
    rid = int(bits[0])
    field = bits[1] if len(bits) > 1 else "Part_Desc"
    row = next((x for x in r.rows if x.row_id == rid), None)
    if row is None:
        raise HTTPException(404, f"row {rid} not found")
    text = row.raw.get(field, "")
    return {
        "kind": "row", "row_id": rid, "field": field,
        "start": start, "end": end,
        "quote": text[start:end],
        "context_before": text[:start],
        "context_after": text[end:],
        "char_length": len(text),
    }


@app.get("/api/document/{doc_id}")
def document(doc_id: str) -> dict[str, Any]:
    r = RUN.get()
    doc = r.sourcing_model.documents.get(doc_id)
    if not doc:
        raise HTTPException(404, f"document {doc_id} not cached")
    return {
        "doc_id": doc.doc_id, "part_number": doc.part_number, "url": doc.url,
        "domain": doc.domain, "brand": doc.brand,
        "reconstructed": doc.reconstructed,
        "char_length": len(doc.text), "text": doc.text,
        "spec_block": [{"label": k, "value": v[0], "start": v[1], "end": v[2]}
                       for k, v in doc.spec_block().items()],
        "features": [{"value": v, "start": a, "end": b}
                     for v, a, b in doc.features()],
    }


@app.get("/api/sourcing")
def sourcing_gate() -> dict[str, Any]:
    r = RUN.get()
    m = r.sourcing_model
    return {
        **m.to_dict(),
        "documents": [
            {"doc_id": d.doc_id, "part_number": d.part_number, "domain": d.domain,
             "brand": d.brand, "url": d.url, "chars": len(d.text),
             "reconstructed": d.reconstructed}
            for d in m.documents.values()
        ],
        "excluded_domains": sorted(C.EXCLUDED_DOMAINS),
        "excluded_keywords": C.EXCLUDED_DOMAIN_KEYWORDS,
    }


@app.get("/api/gate/test")
def gate_test(url: str, manufacturer: str = "") -> dict[str, Any]:
    """Run the sourcing gate on any URL. Nothing is requested."""
    r = RUN.get()
    verdict, reason = sourcing.classify_domain(url, manufacturer, r.vocab)
    return {
        "url": url, "domain": sourcing.domain_of(url),
        "manufacturer": manufacturer, "verdict": verdict, "reason": reason,
        "note": "classification happens before any request is made",
    }


# ======================================================================================
# discovery
# ======================================================================================
@app.get("/api/discovery")
def discovery() -> dict[str, Any]:
    return RUN.get().discovery


@app.get("/api/family/{family_id}")
def family(family_id: str) -> dict[str, Any]:
    r = RUN.get()
    fam = next((f for f in r.family_model.families if f.family_id == family_id), None)
    if fam is None:
        raise HTTPException(404, f"family {family_id} not found")
    by_id = {x.row_id: x for x in r.rows}
    members = []
    for rid in fam.member_ids:
        row = by_id.get(rid)
        if row is None:
            continue
        toks = [t for t in row.tokens if t.kind != "punct"]
        members.append({
            "row_id": rid, "part_number": row.part_number,
            "description": row.description,
            "tokens": [{"text": t.text, "start": t.start, "end": t.end,
                        "kind": t.kind, "skeleton": t.skeleton} for t in toks],
        })
    return {
        "family_id": fam.family_id,
        "skeleton": fam.skeleton,
        "size": fam.size,
        "axes": [a.to_dict() for a in fam.axes],
        "invariants": {str(k): v for k, v in fam.invariants.items()},
        "members": members,
    }


@app.get("/api/contradictions")
def contradictions() -> dict[str, Any]:
    r = RUN.get()
    out = []
    for c in r.metrics["entity"]["contradiction_examples"] or []:
        out.append(c)
    full = [res.contradiction for res in r.resolutions.values() if res.contradiction]
    return {"count": len(full), "contradictions": full}


# ======================================================================================
# review queue, and decisions that actually apply
# ======================================================================================
@app.get("/api/review")
def review() -> dict[str, Any]:
    r = RUN.get()
    return {**r.review_queue.to_dict(), "decisions": OV.load().summary()}


@app.post("/api/review/decide")
def decide(payload: dict[str, Any]) -> dict[str, Any]:
    """Record one reviewer decision and recompile so its leverage is measured, not claimed.

    body: {"kind": "attribute_name"|"item_type"|"manufacturer"|"contradiction",
           "key": "...", "value": "...", "note": "..."}
    """
    kind = str(payload.get("kind", "")).strip()
    key = str(payload.get("key", "")).strip()
    value = str(payload.get("value", "")).strip()
    if kind not in {"attribute_name", "item_type", "manufacturer", "contradiction"}:
        raise HTTPException(400, f"unknown decision kind: {kind!r}")
    if not key or not value:
        raise HTTPException(400, "both key and value are required")

    before = RUN.get()
    before_publish = before.review_queue.auto_publish_records
    before_review = before.review_queue.total_review_records

    ov = OV.load()
    if kind == "item_type":
        key = OV.key_for_item_type(key)
    if kind == "manufacturer":
        from uniforge.vocab import norm_key
        key = norm_key(key)
    ov.record(kind, key, value, note=str(payload.get("note", "")))
    ov.save()

    after = RUN.rebuild()
    return {
        "applied": {"kind": kind, "key": key, "value": value},
        "auto_publish_before": before_publish,
        "auto_publish_after": after.review_queue.auto_publish_records,
        "records_unblocked": (after.review_queue.auto_publish_records
                              - before_publish),
        "review_before": before_review,
        "review_after": after.review_queue.total_review_records,
        "actions_before": len(before.review_queue.actions),
        "actions_after": len(after.review_queue.actions),
        "decisions": ov.summary(),
    }


@app.post("/api/review/reset")
def review_reset() -> dict[str, Any]:
    ov = OV.load()
    ov.clear()
    ov.save()
    after = RUN.rebuild()
    return {"cleared": True, "decisions": ov.summary(),
            "auto_publish": after.review_queue.auto_publish_records}


# ======================================================================================
# search: run both indexes live
# ======================================================================================
@app.get("/api/search")
def search(q: str, k: int = Query(10, ge=1, le=50)) -> dict[str, Any]:
    r = RUN.get()
    query = search_eval.strip_part_numbers(q)
    before_docs, after_docs = {}, {}
    marketing = {rid: r.ledger.records[rid].value("MARKETING_DESC")
                 for rid in r.extractions}
    for row in r.rows:
        before_docs[row.row_id] = search_eval.strip_part_numbers(
            search_eval._before_doc(row))
        if row.row_id in r.extractions and row.row_id in r.compositions:
            after_docs[row.row_id] = search_eval.strip_part_numbers(
                search_eval._after_doc(
                    row, r.extractions[row.row_id], r.compositions[row.row_id],
                    r.resolutions[row.row_id].manufacturer_name,
                    r.resolutions[row.row_id].brand_name,
                    marketing.get(row.row_id, "")))
    ib = search_eval.BM25(before_docs)
    ia = search_eval.BM25(after_docs)

    def hydrate(hits: list[tuple[int, float]]) -> list[dict[str, Any]]:
        out = []
        for rid, score in hits:
            row = next((x for x in r.rows if x.row_id == rid), None)
            if row is None:
                continue
            out.append({
                "row_id": rid, "score": round(score, 4),
                "part_number": row.part_number,
                "raw_description": row.description,
                "title": r.compositions[rid].title if rid in r.compositions else "",
                "classpath": r.extractions[rid].classpath if rid in r.extractions else "",
            })
        return out

    return {
        "query": q,
        "query_used": query,
        "note": ("part numbers are stripped: a unique key inflates any baseline. "
                 "Both indexes are field-weighted identically."),
        "before": hydrate(ib.search(query, k)),
        "after": hydrate(ia.search(query, k)),
    }


# ======================================================================================
# upload and download
# ======================================================================================
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    name = Path(file.filename or "upload.xlsx").name
    if Path(name).suffix.lower() not in {".xlsx", ".xls", ".csv"}:
        raise HTTPException(400, "upload an .xlsx, .xls or .csv catalogue")
    dest = C.DATA_IN / f"_uploaded_{name}"
    body = await file.read()
    if len(body) > 25 * 1024 * 1024:
        raise HTTPException(413, "file larger than 25 MB")
    dest.write_bytes(body)
    try:
        result = RUN.rebuild(input_path=dest, limit=None)
    except Exception as exc:
        raise HTTPException(422, f"could not compile {name}: {exc}") from exc
    return {
        "file": name,
        "bytes": len(body),
        "rows": result.metrics["input"]["row_count"],
        "compile_seconds": result.metrics["meta"]["compile_seconds"],
        "self_checks": result.metrics["self_checks"],
        "output": result.metrics["output"],
    }


@app.post("/api/reset-input")
def reset_input() -> dict[str, Any]:
    result = RUN.rebuild(input_path=None, limit=None)
    return {"input": result.metrics["input"]["source_file"],
            "rows": result.metrics["input"]["row_count"]}


@app.get("/api/download/{fmt}")
def download(fmt: str) -> Response:
    RUN.get()
    if fmt == "csv":
        p = C.DATA_OUT / export.DELIVERY_CSV
        media = "text/csv"
    elif fmt in ("xlsx", "excel"):
        p = C.DATA_OUT / export.DELIVERY_XLSX
        media = ("application/vnd.openxmlformats-officedocument"
                 ".spreadsheetml.sheet")
    elif fmt == "metrics":
        p = C.DATA_OUT / export.METRICS_JSON
        media = "application/json"
    elif fmt == "evidence":
        p = C.DATA_OUT / export.EVIDENCE_JSON
        media = "application/json"
    elif fmt == "review":
        p = C.DATA_OUT / export.REVIEW_JSON
        media = "application/json"
    else:
        raise HTTPException(404, f"unknown format {fmt}")
    if not p.exists():
        raise HTTPException(404, f"{p.name} has not been written yet")
    return FileResponse(p, media_type=media, filename=p.name)


# ======================================================================================
# static: the built React app, when it exists
#
# The app is a single-page app with real paths (`/`, `/console`), so unknown GET paths
# have to fall back to index.html. Mounting StaticFiles at "/" alone would 404 on
# /console, because there is no such file on disk. The catch-all is declared last so it
# can never shadow /api.
# ======================================================================================
WEB_DIST = C.ROOT / "web" / "dist"
INDEX = WEB_DIST / "index.html"

if WEB_DIST.exists() and (WEB_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")),
              name="assets")

API_PREFIXES = ("api/", "docs", "redoc", "openapi.json")


@app.get("/{full_path:path}")
def spa(full_path: str) -> Response:
    if full_path.startswith(API_PREFIXES):
        raise HTTPException(404, f"no such endpoint: /{full_path}")

    if not INDEX.exists():
        return JSONResponse({
            "service": "UniForge",
            "version": PIPELINE_VERSION,
            "tagline": TAGLINE,
            "note": ("the web app has not been built yet. Run `npm install && npm run "
                     "build` in web/, or `npm run dev` for the Vite dev server."),
            "api": ["/api/health", "/api/metrics", "/api/records", "/api/record/{id}",
                    "/api/discovery", "/api/review", "/api/search?q=",
                    "/api/sourcing", "/api/locator?ref=", "/api/schema"],
        })

    # serve a real file when one exists (favicon, robots.txt, and so on)
    if full_path:
        candidate = (WEB_DIST / full_path).resolve()
        try:
            candidate.relative_to(WEB_DIST.resolve())
        except ValueError:
            raise HTTPException(404, "not found")      # path traversal attempt
        if candidate.is_file():
            return FileResponse(candidate)

    return FileResponse(INDEX, media_type="text/html")
