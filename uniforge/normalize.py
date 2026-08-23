"""Stage 7 - cleansing and normalisation. Deterministic code owns this layer entirely.

Units, fractions, character limits and casing are not judgement calls, so no model is
asked to make them. Everything here is a pure function with a testable answer:

    inches / IN. / inch / "   ->  in           one canonical spelling per unit
    24in                      ->  24 in        exactly one space before the unit
    0.5                       ->  1/2          published decimals, traded as fractions
    50.25 in                  ->  50-1/4 in    mixed numbers hyphenate the fraction
    0.045                     ->  0.045        NOT a fraction: it is not an exact 64th

That last line is the interesting one. A decimal is only rewritten as a fraction when it
is exactly representable, which every binary fraction is. `.045` is a real published
thickness that happens to sit near 3/64, and rewriting it would be inventing precision
the manufacturer never claimed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .seed import fractions as seed_fractions
from .vocab import Vocabulary

EXACT_TOL = 1e-9

# Words that keep their own casing wherever they appear.
_KEEP_CASE = {
    "PVC", "CPVC", "ABS", "PEX", "NPT", "NPSM", "BSP", "MIP", "FIP", "MPT", "FPT",
    "DWV", "SST", "SS", "LED", "GFCI", "AFCI", "EMT", "THHN", "THWN", "NM-B", "MC",
    "UL", "CSA", "ETL", "NSF", "ANSI", "ASTM", "ASME", "MSS", "EPA", "ADA", "NEMA",
    "MERV", "NRR", "SEER", "EER", "AFUE", "HSPF", "BTU", "BTUH", "MBH", "CRI",
    "PTFE", "ACQ", "OSB", "TPI", "AWG", "WOG", "TEFC", "ODP", "II", "III", "IV",
    "USA", "R-410A", "T&P", "DKO", "PSA", "OEM",
}

_LOWER_WORDS = {"and", "or", "with", "for", "of", "in", "to", "per", "the", "a", "an"}

# Compressions used only for the 40-character all-caps invoice line.
INVOICE_ABBREV = {
    "stainless steel": "SST",
    "stainless": "SST",
    "aluminum": "ALUM",
    "aluminium": "ALUM",
    "galvanized": "GALV",
    "galvanised": "GALV",
    "coupling": "CPLG",
    "adapter": "ADPT",
    "adaptor": "ADPT",
    "elbow": "ELB",
    "nipple": "NIP",
    "reducer": "RED",
    "bushing": "BUSH",
    "ball valve": "BALL VLV",
    "gate valve": "GATE VLV",
    "check valve": "CHK VLV",
    "valve": "VLV",
    "dishwasher": "DISHWASHER",
    "refrigerator": "REFRIG",
    "water heater": "WTR HTR",
    "condensing unit": "COND UNIT",
    "thermostat": "TSTAT",
    "receptacle": "RECEP",
    "circuit breaker": "CKT BRKR",
    "junction box": "JCT BOX",
    "building wire": "BLDG WIRE",
    "cut-off wheel": "CUT-OFF DISC",
    "cut-off disc": "CUT-OFF DISC",
    "grinding wheel": "GRIND WHL",
    "sanding disc": "SAND DISC",
    "flap disc": "FLAP DISC",
    "saw blade": "SAW BLD",
    "drill bit": "DRL BIT",
    "hole saw": "HOLE SAW",
    "decking board": "DECK BD",
    "deck board": "DECK BD",
    "composite": "COMP",
    "threadlocker": "THRDLKR",
    "thread sealant": "THRD SLNT",
    "penetrating oil": "PEN OIL",
    "spray paint": "SPRY PNT",
    "safety glasses": "SFTY GLASS",
    "work gloves": "WORK GLV",
    "hearing protection": "HEAR PROT",
    "air filter": "AIR FLTR",
    "ball bearing": "BALL BRG",
    "package": "PKG",
    "quantity": "QTY",
    "assembly": "ASSY",
    "commercial": "COMM",
    "residential": "RES",
    "professional": "PROF",
    "with": "W/",
    "without": "W/O",
    "and": "&",
}


@dataclass(frozen=True)
class Measure:
    magnitude: str          # trade form: "5", "0.045", "7/8", "50-1/4"
    unit: str | None        # canonical approved abbreviation
    decimal: float | None   # numeric value where one exists

    @property
    def text(self) -> str:
        return f"{self.magnitude} {self.unit}" if self.unit else self.magnitude


# --------------------------------------------------------------------------------------
# numbers
# --------------------------------------------------------------------------------------
_FRAC_RE = re.compile(r"^(\d+)\s*/\s*(\d+)$")
_MIXED_RE = re.compile(r"^(\d+)\s*-\s*(\d+)\s*/\s*(\d+)$")


def to_decimal(magnitude: str) -> float | None:
    s = magnitude.strip()
    m = _MIXED_RE.match(s)
    if m:
        whole, num, den = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return whole + num / den if den else None
    m = _FRAC_RE.match(s)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        return num / den if den else None
    try:
        return float(s)
    except ValueError:
        return None


def _exact_fraction(frac_part: float) -> str | None:
    """Return the fraction display only when the decimal is exactly a 64th or coarser."""
    for denom in (2, 4, 8, 16, 32, 64):
        num = round(frac_part * denom)
        if num <= 0 or num >= denom:
            continue
        if abs(num / denom - frac_part) <= EXACT_TOL:
            from fractions import Fraction
            f = Fraction(num, denom)
            return f"{f.numerator}/{f.denominator}"
    return None


def to_trade_number(magnitude: str) -> str:
    """Published decimals become trade fractions, but only when the value is exact."""
    s = magnitude.strip()
    if _MIXED_RE.match(s):
        return re.sub(r"\s*", "", s)
    if _FRAC_RE.match(s):
        m = _FRAC_RE.match(s)
        return f"{int(m.group(1))}/{int(m.group(2))}"
    if "." not in s:
        return s
    try:
        val = float(s)
    except ValueError:
        return s
    if val < 0:
        return s
    whole = int(val)
    frac = val - whole
    if frac <= EXACT_TOL:
        return str(whole)
    disp = _exact_fraction(frac)
    if disp is None:
        # keep the manufacturer's own precision, minus a pointless leading zero
        return s[1:] if s.startswith("0.") and len(s) > 2 else s
    return f"{whole}-{disp}" if whole else disp


# --------------------------------------------------------------------------------------
# units
# --------------------------------------------------------------------------------------
_MEASURE_SPLIT = re.compile(
    r"^\s*(?P<mag>\d+\s*-\s*\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d*\.\d+|\d+)\s*"
    r"(?P<unit>[A-Za-z%°\"'/]+(?:\s?[A-Za-z]+)?)?\s*$"
)


def canonical_unit(raw: str | None, vocab: Vocabulary) -> str | None:
    if not raw:
        return None
    key = raw.strip().strip(".").lower()
    if not key:
        return None
    if key in ('"', "''", "in", "inch", "inches"):
        return vocab.uom_alias.get("in", "in")
    if key == "#":
        return None  # ambiguous: pounds or psi. Never guessed.
    hit = vocab.uom_alias.get(key)
    if hit:
        return hit
    # try the plural / trailing-period variants
    for variant in (key.rstrip("s"), key + "s", key.replace(".", "")):
        hit = vocab.uom_alias.get(variant)
        if hit:
            return hit
    return None


def parse_measure(text: str, vocab: Vocabulary,
                  default_unit: str | None = None) -> Measure | None:
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    s = s.replace("''", '"')
    m = _MEASURE_SPLIT.match(s)
    if not m:
        return None
    mag_raw = re.sub(r"\s+", "", m.group("mag"))
    unit_raw = m.group("unit")
    unit = canonical_unit(unit_raw, vocab) if unit_raw else default_unit
    if unit_raw and unit is None:
        # an unapproved unit may not be written, so the measure is not usable
        return None
    mag = to_trade_number(mag_raw)
    return Measure(magnitude=mag, unit=unit, decimal=to_decimal(mag_raw))


def format_measure(magnitude: str, unit: str | None) -> str:
    """One space between magnitude and unit. Always."""
    mag = to_trade_number(str(magnitude))
    return f"{mag} {unit}".strip() if unit else mag


def normalise_value(value: str, vocab: Vocabulary) -> str:
    """Normalise a whole attribute value: every measure inside it gets fixed."""
    if value is None:
        return ""
    s = re.sub(r"\s+", " ", str(value)).strip()
    if not s:
        return ""

    def repl(m: re.Match) -> str:
        mag, unit_raw = m.group("mag"), m.group("unit")
        unit = canonical_unit(unit_raw, vocab)
        if unit is None:
            return m.group(0)
        return format_measure(re.sub(r"\s+", "", mag), unit)

    pattern = re.compile(
        r"(?P<mag>\d+\s*-\s*\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d*\.\d+|\d+)\s*"
        r"(?P<unit>\"|''|[A-Za-z]{1,5}\b)")
    s = pattern.sub(repl, s)
    return s.strip()


def dimension_string(parts: list[tuple[str, str, str]]) -> str:
    """[(magnitude, unit, qualifier)] -> '24 in W x 24-1/4 in D'."""
    chunks = []
    for mag, unit, qual in parts:
        base = format_measure(mag, unit)
        chunks.append(f"{base} {qual}".strip())
    return " x ".join(chunks)


# --------------------------------------------------------------------------------------
# casing
# --------------------------------------------------------------------------------------
def title_case(text: str, vocab: Vocabulary) -> str:
    if not text:
        return ""
    out: list[str] = []
    words = re.split(r"(\s+)", str(text))
    for i, w in enumerate(words):
        if not w.strip():
            out.append(w)
            continue
        bare = w.strip(",;:.()")
        lead = w[:len(w) - len(w.lstrip(",;:.()"))]
        trail = w[len(w.rstrip(",;:.()")):]
        if bare.upper() in _KEEP_CASE:
            out.append(lead + bare.upper() + trail)
        elif bare in vocab.approved_units:
            out.append(w)
        elif any(c.isdigit() for c in bare):
            out.append(w)
        elif bare.isupper() and len(bare) <= 5:
            out.append(w)
        elif "\u00ae" in bare or "\u2122" in bare:
            out.append(w)
        elif bare.lower() in _LOWER_WORDS and i > 0:
            out.append(lead + bare.lower() + trail)
        else:
            out.append(lead + bare[:1].upper() + bare[1:] + trail
                       if bare else w)
    return "".join(out)


def upper_case(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().upper()


def abbreviate_for_invoice(text: str) -> str:
    s = " " + re.sub(r"\s+", " ", str(text or "")).strip().lower() + " "
    for long, short in sorted(INVOICE_ABBREV.items(), key=lambda kv: -len(kv[0])):
        s = s.replace(f" {long} ", f" {short} ")
    return re.sub(r"\s+", " ", s).strip().upper()


# --------------------------------------------------------------------------------------
# character limits
# --------------------------------------------------------------------------------------
def fit(text: str, max_chars: int, drop_separator: str = ", ") -> str:
    """Trim to the limit by dropping whole trailing segments, never mid-word."""
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(s) <= max_chars:
        return s
    if drop_separator and drop_separator in s:
        parts = s.split(drop_separator)
        while len(parts) > 1:
            parts.pop()
            cand = drop_separator.join(parts).strip().rstrip(",;")
            if len(cand) <= max_chars:
                return cand
    words = s.split(" ")
    while len(words) > 1:
        words.pop()
        cand = " ".join(words).strip().rstrip(",;-")
        if len(cand) <= max_chars:
            return cand
    return s[:max_chars].rstrip().rstrip(",;-")


def _protected_spans(text: str, protected: tuple[str, ...]) -> list[tuple[int, int]]:
    """Character ranges that belong to a brand, part number or series.

    `3M(TM)` is not "3 m", and `775L` is not "775 L". Identifiers are quoted verbatim
    from the supplied row or a manufacturer page, so a unit check that walked into one
    would report a violation UniForge did not commit - and, worse, would invite
    "fixing" a manufacturer's own product name.
    """
    spans: list[tuple[int, int]] = []
    low = text.lower()
    for p in protected:
        if not p or len(p) < 2:
            continue
        needle = p.lower()
        start = 0
        while True:
            i = low.find(needle, start)
            if i < 0:
                break
            spans.append((i, i + len(needle)))
            start = i + 1
    return spans


def _overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    """True if the span touches a protected identifier at all.

    Containment is not enough. In `PVC017398 S X S` the digits of the part number are
    followed by a lone `S`, so a naive magnitude+unit match starts inside the identifier
    and ends outside it. Any overlap means the match is an artefact of an identifier, not
    a measurement.
    """
    return any(span[0] < b and a < span[1] for a, b in spans)


def approved_units_used(text: str, vocab: Vocabulary,
                        protected: tuple[str, ...] = (),
                        ignore_case: bool = False) -> tuple[set[str], set[str]]:
    """(approved units found, unapproved unit-shaped tokens found).

    `ignore_case` exists because two rules in the standard genuinely collide: the invoice
    line is ALL CAPS, and each unit has exactly one approved spelling. `5 lb` uppercased
    is `5 LB`, which is the approved unit written in the field's mandated casing - not an
    unapproved spelling. The field's own casing rule wins, so on those fields the unit is
    compared case-insensitively.
    """
    s = str(text or "")
    guard = _protected_spans(s, protected)
    approved = ({u.lower() for u in vocab.approved_units} if ignore_case
                else vocab.approved_units)
    ok: set[str] = set()
    bad: set[str] = set()
    for m in re.finditer(r"(\d+(?:[.\-/]\d+)*)\s+([A-Za-z%][A-Za-z%/]{0,7})", s):
        if _overlaps((m.start(), m.end()), guard):
            continue
        cand = m.group(2)
        probe = cand.lower() if ignore_case else cand
        if probe in approved:
            ok.add(cand)
        elif cand.lower() in _LOWER_WORDS or cand.upper() in _KEEP_CASE:
            continue
        elif canonical_unit(cand, vocab) == cand:
            ok.add(cand)
        elif cand.lower() in vocab.uom_alias:
            bad.add(cand)
    return ok, bad


def has_glued_unit(text: str, vocab: Vocabulary,
                   protected: tuple[str, ...] = ()) -> list[str]:
    """Find '24in' style violations of the space rule."""
    s = str(text or "")
    guard = _protected_spans(s, protected)
    bad: list[str] = []
    for m in re.finditer(r"(?<![A-Za-z0-9\-])(\d+(?:[.\-/]\d+)*)([A-Za-z]{1,5})"
                         r"(?![A-Za-z0-9\u00ae\u2122\-])", s):
        if _overlaps((m.start(), m.end()), guard):
            continue
        alpha = m.group(2)
        # A single capital letter glued to digits is an identifier far more often than a
        # unit: 3M, 775L, 600Z, 56C. Two or more characters, or a lowercase unit, is a
        # real violation: 24in, 5500w.
        if len(alpha) == 1 and alpha.isupper():
            continue
        if canonical_unit(alpha, vocab):
            bad.append(m.group(0))
    return bad
