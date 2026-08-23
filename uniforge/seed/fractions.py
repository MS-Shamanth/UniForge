"""The 63 exact inch conversions, 1/64 through 63/64.

Manufacturers publish decimals. Trade buyers search fractions. This table is the
bridge, and it is generated rather than transcribed so it cannot contain a typo:
every value is exact in binary, so equality is safe at 1/64 resolution.
"""
from __future__ import annotations

from fractions import Fraction

# tolerance for matching a published decimal to a 64th
MATCH_TOL = 1.0 / 128.0 - 1e-12   # half of 1/64


def build_table() -> list[tuple[str, float, int, int]]:
    """[(display, decimal, numerator, denominator)] in lowest terms, 1/64..63/64."""
    rows: list[tuple[str, float, int, int]] = []
    for n in range(1, 64):
        f = Fraction(n, 64)
        rows.append((f"{f.numerator}/{f.denominator}", n / 64.0, f.numerator, f.denominator))
    return rows


TABLE = build_table()

# decimal -> canonical fraction display, keyed on the exact 64th
BY_DECIMAL: dict[float, str] = {dec: disp for disp, dec, _n, _d in TABLE}

# Common trade fractions get priority when two forms are equally close.
PREFERRED_DENOMINATORS = (2, 4, 8, 16, 32, 64)


def nearest_fraction(value: float) -> tuple[str, float] | None:
    """Snap a decimal in (0,1) to the nearest 64th. Returns (display, error) or None."""
    if value <= 0 or value >= 1:
        return None
    best: tuple[str, float] | None = None
    for denom in PREFERRED_DENOMINATORS:
        num = round(value * denom)
        if num <= 0 or num >= denom:
            continue
        f = Fraction(num, denom)
        err = abs(float(f) - value)
        if err <= MATCH_TOL:
            cand = (f"{f.numerator}/{f.denominator}", err)
            if best is None or cand[1] < best[1] - 1e-12:
                best = cand
            # prefer the coarsest denominator that still matches exactly
            if err < 1e-12:
                return cand
    return best
