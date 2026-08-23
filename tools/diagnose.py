"""Diagnostics for a run: what failed, what did not resolve, and why.

Not part of the pipeline. Used while tuning, and kept because "why is this record in
review?" is the first question anyone asks.

    python tools/diagnose.py units
    python tools/diagnose.py locators
    python tools/diagnose.py unclassified
    python tools/diagnose.py review
    python tools/diagnose.py all
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniforge import config as C, pipeline  # noqa: E402


def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    r = pipeline.run(C.RunOptions(limit=limit or None))

    if what in ("units", "all"):
        print("\n=== unit failures ===")
        c = Counter()
        shown = 0
        for v in r.validations.values():
            for f in v.unit_failures:
                c[(f["problem"], str(f.get("detail"))[:40])] += 1
                if shown < 14:
                    comp = r.compositions[v.row_id]
                    print(f"  row {v.row_id:<5} {f['field']:<14} {f['problem']}"
                          f"  {f.get('detail')}")
                    print(f"      {comp.short[:120]}")
                    shown += 1
        for k, n in c.most_common(20):
            print(f"  {n:>5}  {k}")

    if what in ("locators", "all"):
        print("\n=== claims without a locator ===")
        c = Counter()
        for u in r.ledger.unlocated_claims():
            c[(u["field"], u["kind"], u["rule"][:70])] += 1
        for k, n in c.most_common(20):
            print(f"  {n:>5}  {k}")

    if what in ("unclassified", "all"):
        print("\n=== unclassified item types ===")
        c = Counter()
        ex_by = {}
        for row in r.rows:
            ex = r.extractions[row.row_id]
            if not ex.classified:
                key = (ex.item_type or ex.item_type_raw or "?").title()
                c[key] += 1
                ex_by.setdefault(key, row.description)
        for k, n in c.most_common(60):
            print(f"  {n:>4}  {k:<38} | {ex_by[k][:56]}")
        print(f"  total unclassified rows: {sum(c.values())}")

    if what in ("review", "all"):
        print("\n=== review reasons ===")
        c = Counter()
        for v in r.validations.values():
            if v.status.startswith("review"):
                for reason in v.reasons:
                    c[reason] += 1
                if not v.reasons:
                    c["(no reason, below floor)"] += 1
        for k, n in c.most_common():
            print(f"  {n:>5}  {k}")
        print("\n=== coverage distribution (classified rows) ===")
        buckets = Counter()
        for row in r.rows:
            ex = r.extractions[row.row_id]
            if ex.classified:
                buckets[round(ex.coverage() * 10) / 10] += 1
        for k in sorted(buckets):
            print(f"  {k:>4}  {'#' * min(60, buckets[k])} {buckets[k]}")
        print("\n=== attributes-in-sequence distribution ===")
        b2 = Counter()
        for row in r.rows:
            ex = r.extractions[row.row_id]
            if ex.classified:
                b2[len(ex.labels() & set(ex.attribute_sequence))] += 1
        for k in sorted(b2):
            print(f"  {k:>4}  {b2[k]}")

    if what in ("axes", "all"):
        print("\n=== unnamed induced attributes (top 30 by support) ===")
        for a in sorted(r.induction_model.needing_names,
                        key=lambda x: -x.support)[:30]:
            print(f"  support {a.support:>4}  rows {len(a.member_rows):>4}  "
                  f"{a.origin:<14} {', '.join(a.values[:6])[:70]}")


if __name__ == "__main__":
    main()
