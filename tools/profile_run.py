"""Where does a compile spend its time? Stage timings plus the artefact writes."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniforge import config as C, export, pipeline  # noqa: E402

t0 = time.perf_counter()
result = pipeline.run(C.RunOptions())
t_run = time.perf_counter() - t0

print("\nstage seconds")
for k, v in result.metrics["meta"]["stage_seconds"].items():
    print(f"  {k:<12} {v:>7.3f}")
print(f"  {'TOTAL run':<12} {t_run:>7.3f}")

print("\nartefact writes")
for name, payload in (
    ("delivery csv+xlsx", None),
    (export.METRICS_JSON, result.metrics),
    (export.EVIDENCE_JSON, result.ledger.to_dict(limit=120)),
    (export.REVIEW_JSON, result.review_queue.to_dict()),
    (export.DISCOVERY_JSON, result.discovery),
    (export.SEARCH_JSON, result.search.to_dict()),
):
    t = time.perf_counter()
    if payload is None:
        paths = export.write_delivery(result.records)
        size = sum(p.stat().st_size for p in paths.values())
    else:
        p = export.write_json(name, payload)
        size = p.stat().st_size
    print(f"  {name:<22} {time.perf_counter() - t:>7.3f}s  {size:>10,} bytes")

print(f"\nwall total {time.perf_counter() - t0:.3f}s")
