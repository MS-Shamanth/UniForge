"""Smoke test the built web app as served by FastAPI.

Checks the things that silently break: the SPA shell being served at all, the console
route resolving, the bundle loading, and the content rules from the brief (exact tagline,
exact spelling of the authors, no email address anywhere in the bundle).

    python tools/smoke_web.py
"""
from __future__ import annotations

import re
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
fails: list[str] = []


def get(path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(BASE + path, timeout=60) as fh:
            return fh.status, fh.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        fails.append(name)


print("\nUniForge web smoke test")
print("-" * 62)

status, html = get("/")
check("landing page is served", status == 200, str(status))
check("SPA root element present", 'id="root"' in html)
title = re.search(r"<title>(.*?)</title>", html)
check("page title is set", bool(title),
      title.group(1) if title else "missing")

js = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
css = re.search(r'href="(/assets/index-[^"]+\.css)"', html)
check("js bundle referenced", bool(js), js.group(1) if js else "missing")
check("css bundle referenced", bool(css), css.group(1) if css else "missing")

bundle = ""
if js:
    s, bundle = get(js.group(1))
    check("js bundle loads", s == 200 and len(bundle) > 50_000,
          f"{len(bundle):,} chars")

sheet = ""
if css:
    s, sheet = get(css.group(1))
    check("css bundle loads", s == 200 and len(sheet) > 10_000,
          f"{len(sheet):,} chars")

s, _ = get("/console")
check("console route resolves through the SPA fallback", s == 200, str(s))

# ── content rules from the brief ──────────────────────────────────────────────
TAGLINE = "LLM extracts. Rules decide. Evidence proves."
check("tagline appears exactly", TAGLINE in bundle)
check('"Shreya BJ" spelled exactly', "Shreya BJ" in bundle)
check('"Shamanth" present', "Shamanth" in bundle)
check("no misspelling 'Shrea'", "Shrea" not in bundle)

emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", bundle)
emails = [e for e in emails if not e.startswith("@")]
check("no email address in the bundle", not emails, ", ".join(emails[:3]))

check("no lorem ipsum", "lorem ipsum" not in bundle.lower())

# colour discipline: the brief bans blue and green
banned = [c for c in ("#3b82f6", "#2563eb", "#10b981", "#22c55e", "#0ea5e9")
          if c in sheet.lower()]
check("no stock blue/green in the stylesheet", not banned, ", ".join(banned))
check("magenta accent present", "#e84bd8" in sheet.lower())
check("amber reserved token present", "#f5b82e" in sheet.lower())
check("reduced-motion is respected",
      "prefers-reduced-motion" in sheet.lower())

# every nav target must exist as a section id in the bundle
for target in ("product", "how-it-works", "evidence", "results", "technology"):
    check(f'nav target #{target} has a section', f'id="{target}"' in bundle
          or f"id:'{target}'" in bundle or f'"{target}"' in bundle)

print("-" * 62)
if fails:
    print(f"{len(fails)} FAILED: {', '.join(fails)}")
    sys.exit(1)
print("all checks passed")
