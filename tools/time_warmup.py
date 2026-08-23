"""How long until the console can open, and how fast is it once warm?

    python tools/time_warmup.py [base]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def get(path: str, timeout: int = 180):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as fh:
        return json.loads(fh.read().decode())


print(f"\nwatching {BASE}")
print("-" * 60)

t0 = time.perf_counter()
ready_at = None
for _ in range(300):
    try:
        st = get("/api/status", timeout=20)
    except Exception as e:
        print(f"  t+{time.perf_counter() - t0:6.1f}s  waiting for the server ({type(e).__name__})")
        time.sleep(1.0)
        continue
    el = time.perf_counter() - t0
    if st.get("error"):
        print(f"  t+{el:6.1f}s  ERROR {st['error']}")
        sys.exit(1)
    if st["ready"]:
        ready_at = el
        print(f"  t+{el:6.1f}s  ready   rows={st.get('rows')}")
        break
    print(f"  t+{el:6.1f}s  building for {st.get('building_for')}s")
    time.sleep(1.0)

print("-" * 60)
if ready_at is None:
    print("never became ready")
    sys.exit(1)

# now measure what a console open actually costs
for label, path in (
    ("health", "/api/health"),
    ("metrics", "/api/metrics"),
    ("records", "/api/records?page=1&size=20"),
    ("discovery", "/api/discovery"),
    ("sourcing", "/api/sourcing"),
    ("review", "/api/review"),
    ("search", "/api/search?q=cut-off+wheel&k=10"),
):
    t = time.perf_counter()
    get(path)
    print(f"  {label:<10} {(time.perf_counter() - t) * 1000:8.0f} ms")

print("-" * 60)
print(f"warm-up completed {ready_at:.1f}s after this script started watching")
print("a visitor opening /console after that pays only the request times above")
