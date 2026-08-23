"""Run every verification suite against a running server and summarise.

    python -m uniforge.cli serve        # in one terminal
    python tools/verify_all.py          # in another
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

SUITES = [
    ("warm-up and request timings", ["tools/time_warmup.py", BASE]),
    ("every console call", ["tools/audit_console.py", BASE]),
    ("API assertions", ["tools/smoke_api.py", BASE]),
    ("built page and content rules", ["tools/smoke_web.py", BASE]),
    ("workbook integrity", ["tools/verify_xlsx.py"]),
]

results: list[tuple[str, bool, str]] = []

for name, args in SUITES:
    print(f"\n{'=' * 70}")
    print(f"  {name}")
    print("=" * 70)
    proc = subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out.rstrip())
    tail = [ln for ln in out.strip().splitlines() if ln.strip()]
    results.append((name, proc.returncode == 0, tail[-1] if tail else ""))

print(f"\n{'=' * 70}")
print("  SUMMARY")
print("=" * 70)
for name, ok, last in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<32} {last[:60]}")

failed = [n for n, ok, _ in results if not ok]
print()
if failed:
    print(f"{len(failed)} suite(s) failed: {', '.join(failed)}")
    sys.exit(1)
print("every suite passed")
