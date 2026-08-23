"""The trade tokenizer.

Industrial descriptions are not prose and they are not CSV. `Milw 5"x.045"x7/8" Metal
Cut Off Disc` has to come apart into six meaningful pieces without losing the fact that
`.045` and `7/8` are measurements of different things.

Two properties matter downstream and both are load-bearing:

  1. every token keeps its character offsets, because an evidence locator is
     `row:<id>#char[a:b]` and a claim without a locator cannot be published;
  2. every token gets a `skeleton` form, where anything measurement-shaped collapses to
     `#`. Rows that share a skeleton are siblings, and that is the whole basis of
     family and variant-axis discovery.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# token kinds
WORD = "word"
INT = "int"
DECIMAL = "decimal"
FRACTION = "fraction"
MIXED = "mixed"          # 4-1/2
DIMSET = "dimset"        # 16x25x1
GLUED = "glued"          # 5500W, 47dBA, 3in
CODE = "code"            # P150, QO120CP, 3MABR-7100075678
PUNCT = "punct"
BRACKET = "bracket"

MEASURE_KINDS = {INT, DECIMAL, FRACTION, MIXED, DIMSET, GLUED}

# Ordered alternation. First match wins, so the longest and most specific forms lead.
_PATTERNS: list[tuple[str, str]] = [
    (DIMSET,   r"\d+(?:\.\d+)?\s*[xX]\s*\d+(?:\.\d+)?(?:\s*[xX]\s*\d+(?:\.\d+)?)+"),
    (MIXED,    r"\d+\s*-\s*\d+\s*/\s*\d+\s*(?:\"|''|in\b|IN\b)?"),
    (FRACTION, r"\d+\s*/\s*\d+\s*(?:\"|''|in\b|IN\b)?"),
    (DECIMAL,  r"\.\d+\s*(?:\"|''|in\b|IN\b)?|\d+\.\d+\s*(?:\"|''|in\b|IN\b)?"),
    (GLUED,    r"\d+(?:\.\d+)?\s*(?:\"|''|#)"),
    (GLUED,    r"\d+(?:\.\d+)?[A-Za-z]{1,6}\b"),
    # A code may not begin immediately after a digit or an inch mark. Without that
    # guard, `5"x.045"x7/8"` loses its third measurement: the `x` separating two
    # dimensions binds to the following digit, `x7` is read as a product code, and the
    # arbor size arrives as `8 in` instead of `7/8 in`. The lookbehind keeps genuine
    # single-letter codes (`P150`, `T29`, `A19`) because those follow a space or a
    # bracket, never a quote.
    (CODE,     r"(?<![0-9\"'])[A-Za-z]{1,6}[-#]?\d[\dA-Za-z]*(?:-[\dA-Za-z]+)*"),
    (CODE,     r"(?<![0-9\"'])\d+[A-Za-z]{1,3}-[\dA-Za-z-]+"),
    (INT,      r"\d+"),
    (WORD,     r"[A-Za-z][A-Za-z&'\u00ae\u2122]*(?:-[A-Za-z]+)*"),
    (BRACKET,  r"[\[\]\(\)]"),
    (PUNCT,    r"[^\sA-Za-z0-9]"),
]

_MASTER = re.compile(
    "|".join(f"(?P<k{i}>{pat})" for i, (_kind, pat) in enumerate(_PATTERNS))
)
_KIND_BY_GROUP = {f"k{i}": kind for i, (kind, _pat) in enumerate(_PATTERNS)}


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int
    kind: str

    @property
    def norm(self) -> str:
        return re.sub(r"\s+", "", self.text).strip().lower()

    @property
    def skeleton(self) -> str:
        """`#` for anything measurement-shaped, the lowercased word otherwise."""
        if self.kind in MEASURE_KINDS:
            return "#"
        if self.kind == CODE:
            # A code that is mostly digits is an identifier, not a descriptor.
            digits = sum(c.isdigit() for c in self.text)
            return "#" if digits >= max(2, len(self.text) // 2) else self.norm
        if self.kind in (PUNCT, BRACKET):
            return self.text.strip()
        return self.norm

    @property
    def is_measure(self) -> bool:
        return self.kind in MEASURE_KINDS or self.skeleton == "#"


def tokenize(text: str) -> list[Token]:
    if not text:
        return []
    out: list[Token] = []
    for m in _MASTER.finditer(text):
        kind = next(_KIND_BY_GROUP[g] for g, v in m.groupdict().items() if v is not None)
        raw = m.group(0)
        # trim trailing whitespace captured by the measure patterns
        stripped = raw.rstrip()
        end = m.start() + len(stripped)
        if not stripped:
            continue
        out.append(Token(stripped, m.start(), end, kind))
    return out


def skeleton(text: str) -> str:
    """Family signature: words held, measurements collapsed."""
    return " ".join(t.skeleton for t in tokenize(text) if t.kind != PUNCT)


def content_words(text: str) -> list[str]:
    return [t.norm for t in tokenize(text) if t.kind == WORD and len(t.norm) > 1]


def measures(text: str) -> list[Token]:
    return [t for t in tokenize(text) if t.is_measure]


# --------------------------------------------------------------------------------------
# Locator helpers. One format, used everywhere, so a value can always be traced back to
# the exact characters that justify it.
# --------------------------------------------------------------------------------------
def row_locator(row_id: int, field: str, start: int, end: int) -> str:
    return f"row:{row_id}:{field}#char[{start}:{end}]"


def doc_locator(doc_id: str, start: int, end: int) -> str:
    return f"doc:{doc_id}#char[{start}:{end}]"


_LOC_RE = re.compile(r"^(?P<kind>row|doc):(?P<ref>[^#]+)#char\[(?P<a>\d+):(?P<b>\d+)\]$")


def parse_locator(loc: str) -> dict | None:
    m = _LOC_RE.match(loc or "")
    if not m:
        return None
    return {
        "kind": m.group("kind"),
        "ref": m.group("ref"),
        "start": int(m.group("a")),
        "end": int(m.group("b")),
    }


def find_span(haystack: str, needle: str) -> tuple[int, int] | None:
    """Locate a value in its source text so a locator can be issued for it."""
    if not needle:
        return None
    i = haystack.find(needle)
    if i >= 0:
        return i, i + len(needle)
    low = haystack.lower()
    i = low.find(needle.lower())
    if i >= 0:
        return i, i + len(needle)
    # last resort: match the digits, which is what a number claim really rests on
    digits = re.sub(r"[^\d./-]", "", needle)
    if len(digits) >= 2:
        i = haystack.find(digits)
        if i >= 0:
            return i, i + len(digits)
    return None
