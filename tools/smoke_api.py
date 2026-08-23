"""Smoke test the running API. Asserts the things the UI depends on.

    python -m uvicorn server.app:app --port 8000     # in one terminal
    python tools/smoke_api.py                        # in another
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
fails: list[str] = []


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=180) as fh:
        return json.loads(fh.read().decode("utf-8"))


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        fails.append(name)


print("\nUniForge API smoke test")
print("-" * 60)

h = get("/api/health")
check("health responds", h.get("ok") is True)
check("delivery format is 252 columns", h.get("delivery_columns") == 252,
      str(h.get("delivery_columns")))

m = get("/api/metrics")
sc = m["self_checks"]
check("all self checks pass", sc["all_pass"], f"{sc['passed']}/{sc['total']}")
check("rows compiled", m["input"]["row_count"] > 0, str(m["input"]["row_count"]))
check("zero hallucinations", m["integrity"]["hallucinations"] == 0)
check("no unlocated claims", m["integrity"]["claims_without_a_locator"] == 0)
check("character-limit compliance is 100%",
      m["compliance"]["character_limit_compliance_pct"] == 100.0,
      f"{m['compliance']['character_limit_compliance_pct']}%")
check("approved-unit compliance is 100%",
      m["compliance"]["approved_unit_compliance_pct"] == 100.0,
      f"{m['compliance']['approved_unit_compliance_pct']}%")
check("zero model calls", m["discovery"]["model_calls"] == 0)
check("a document overruled an inference",
      m["integrity"]["document_overruled_inference"] > 0,
      str(m["integrity"]["document_overruled_inference"]))
check("contradictions were found", m["entity"]["contradictions"] > 0,
      str(m["entity"]["contradictions"]))
check("manufacturers were unmasked", m["entity"]["manufacturers_unmasked"] > 0,
      str(m["entity"]["manufacturers_unmasked"]))
check("marketplace candidates were rejected pre-request",
      m["sourcing"]["rejected_count"] > 0,
      ", ".join(sorted({d["domain"] for d in
                        m["sourcing"]["rejected_before_request"]})))

s = get("/api/schema")
check("schema exposes 252 columns", s["column_count"] == 252)

rec = get("/api/records?size=3")
check("records list paginates", len(rec["items"]) == 3, f"total {rec['total']}")

r0 = get("/api/record/0")
check("record 0 is the Milwaukee cut-off disc",
      r0["part_number"] == "49-94-0013", r0["part_number"])
check("record 0 has attributes", len(r0["attributes"]) >= 5,
      str(len(r0["attributes"])))
pq = next((a for a in r0["attributes"] if a["label"] == "Package Quantity"), None)
check("pack quantity came from the document", pq is not None and pq["kind"] == "sourced",
      (pq or {}).get("value", "missing"))
check("every attribute carries a locator or a rule",
      all(a["locator"] or a["kind"] in ("derived", "vocab")
          for a in r0["attributes"]))

d = get("/api/record/0/delivery")
check("delivery row has 252 columns", d["total"] == 252,
      f"{d['populated']} populated")

loc = next((a["locator"] for a in r0["attributes"]
            if a["locator"] and a["locator"].startswith("doc:")), None)
if loc:
    lo = get("/api/locator?ref=" + urllib.parse.quote(loc, safe=""))
    check("a document locator resolves to real characters",
          bool(lo.get("quote")), f"{lo['domain']} -> {lo['quote']!r}")
else:
    check("a document locator resolves to real characters", False, "no doc locator")

g1 = get("/api/gate/test?" + urllib.parse.urlencode(
    {"url": "https://www.homedepot.com/p/123", "manufacturer": "Milwaukee Tool"}))
check("the gate rejects a marketplace", g1["verdict"] == "rejected", g1["reason"])
g2 = get("/api/gate/test?" + urllib.parse.urlencode(
    {"url": "https://www.milwaukeetool.com/x", "manufacturer": "Milwaukee Tool"}))
check("the gate admits the manufacturer's own domain",
      g2["verdict"] == "admitted", g2["reason"])

sr = get("/api/search?q=" + urllib.parse.quote("thin cut-off wheel 5 in"))
check("search returns both indexes",
      isinstance(sr["before"], list) and isinstance(sr["after"], list),
      f"before {len(sr['before'])}, after {len(sr['after'])}")

rv = get("/api/review")
check("review queue is sized in decisions", rv["action_count"] > 0,
      f"{rv['review_records']} records, {rv['action_count']} actions")

dis = get("/api/discovery")
check("families were discovered", dis["families"]["family_count"] > 0,
      str(dis["families"]["family_count"]))

fid = dis["families"]["families"][0]["family_id"]
fam = get(f"/api/family/{fid}")
check("a family exposes its members and axes",
      len(fam["members"]) >= 2 and "axes" in fam,
      f"{fid}: {len(fam['members'])} members, {len(fam['axes'])} axes")

print("-" * 60)
if fails:
    print(f"{len(fails)} FAILED: {', '.join(fails)}")
    sys.exit(1)
print("all checks passed")
