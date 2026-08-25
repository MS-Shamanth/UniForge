"""Time every download route. The workbook must not stall the button.

    python tools/time_downloads.py [base]
"""
from __future__ import annotations

import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

print(f"\ndownloads from {BASE}")
print("-" * 56)
slow = []
for fmt in ("csv", "xlsx", "metrics", "evidence", "review"):
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(f"{BASE}/api/download/{fmt}", timeout=300) as fh:
            n = len(fh.read())
        ms = (time.perf_counter() - t) * 1000
        flag = "" if ms < 2000 else "   <- slow"
        print(f"  {fmt:<10} {ms:>8.0f} ms   {n:>10,} bytes{flag}")
        if ms >= 2000:
            slow.append((fmt, round(ms)))
    except Exception as e:
        print(f"  {fmt:<10}    FAILED   {type(e).__name__}: {e}")
        slow.append((fmt, -1))

print("-" * 56)
if slow:
    print("slow or failing: " + ", ".join(f"{f} ({m}ms)" for f, m in slow))
    sys.exit(1)
print("every download is immediate")
