"""Hit every endpoint the console calls, in the order it calls them, and report status.

The console reports a bare status code when something fails, which is not enough to find
the culprit. This walks the same call graph and names it.

    python tools/audit_console.py [base]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def hit(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, object]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as fh:
            payload = json.loads(fh.read().decode())
            return fh.status, (payload, round(time.perf_counter() - t0, 2))
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode()[:200], round(time.perf_counter() - t0, 2))
    except Exception as e:                                  # connection refused etc.
        return 0, (f"{type(e).__name__}: {e}", round(time.perf_counter() - t0, 2))


CALLS = [
    ("Console mount -> health", "/api/health"),
    ("Console mount -> metrics", "/api/metrics"),
    ("Records tab", "/api/records?q=&status=&page=1&size=20"),
    ("Record drawer", "/api/record/0"),
    ("Record delivery", "/api/record/0/delivery"),
    ("Discovery tab", "/api/discovery"),
    ("Sourcing tab", "/api/sourcing"),
    ("Review tab", "/api/review"),
    ("Search tab", "/api/search?q=thin+cut-off+wheel&k=10"),
    ("Schema", "/api/schema"),
    ("Vocabulary", "/api/vocabulary"),
    ("Contradictions", "/api/contradictions"),
]

print(f"\nauditing {BASE}")
print("-" * 74)
bad = []
for name, path in CALLS:
    status, (payload, secs) = hit(path)
    ok = status == 200
    flag = "ok  " if ok else "FAIL"
    print(f"  {flag} {secs:>6.2f}s  {status:>3}  {name:<28} {path}")
    if not ok:
        bad.append((name, path, status, payload))

# dynamic ones the console derives from earlier responses
status, (disc, _s) = hit("/api/discovery")
if status == 200:
    fid = disc["families"]["families"][0]["family_id"]
    s2, (_p, secs) = hit(f"/api/family/{fid}")
    print(f"  {'ok  ' if s2 == 200 else 'FAIL'} {secs:>6.2f}s  {s2:>3}  "
          f"{'Family drawer':<28} /api/family/{fid}")
    if s2 != 200:
        bad.append(("Family drawer", fid, s2, ""))

status, (rec, _s) = hit("/api/record/0")
if status == 200:
    loc = next((a["locator"] for a in rec["attributes"]
                if a.get("locator", "").startswith("doc:")), None)
    if loc:
        q = "/api/locator?ref=" + urllib.parse.quote(loc, safe="")
        s3, (_p, secs) = hit(q)
        print(f"  {'ok  ' if s3 == 200 else 'FAIL'} {secs:>6.2f}s  {s3:>3}  "
              f"{'Evidence popover':<28} {q[:44]}…")
        if s3 != 200:
            bad.append(("Evidence popover", loc, s3, ""))

s4, (_p, secs) = hit("/api/gate/test?" + urllib.parse.urlencode(
    {"url": "https://www.homedepot.com/p/1", "manufacturer": "Milwaukee Tool"}))
print(f"  {'ok  ' if s4 == 200 else 'FAIL'} {secs:>6.2f}s  {s4:>3}  "
      f"{'Gate test':<28} /api/gate/test")
if s4 != 200:
    bad.append(("Gate test", "", s4, ""))

for fmt in ("csv", "xlsx", "metrics"):
    try:
        req = urllib.request.Request(f"{BASE}/api/download/{fmt}", method="GET")
        with urllib.request.urlopen(req, timeout=120) as fh:
            n = len(fh.read())
        print(f"  ok       -    {fh.status:>3}  {'Download ' + fmt:<28} {n:,} bytes")
    except urllib.error.HTTPError as e:
        print(f"  FAIL     -    {e.code:>3}  {'Download ' + fmt:<28}")
        bad.append((f"download {fmt}", "", e.code, ""))

print("-" * 74)
if bad:
    print(f"{len(bad)} FAILING:")
    for name, path, status, payload in bad:
        print(f"  {status}  {name}  {path}")
        if payload:
            print(f"        {payload}")
    sys.exit(1)
print("every console call returns 200")
