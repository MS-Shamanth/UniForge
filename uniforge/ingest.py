"""Stage 1 - input analysis.

Reads whatever 6-column catalogue it is given, scrubs placeholders, and profiles what it
actually received. The profile matters as much as the data: "86.5% of brand cells are
placeholders" is not a complaint, it is the measurement that justifies every later
decision to derive rather than look up.

Placeholders are not data. `-- Unbranded --`, `-- No Unilog Brand --` and
`-- No DIB Brand --` mean the field is empty, and they are removed before anything
matches, prompts or counts on them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from . import config as C
from . import trade_tokens as TT

_PLACEHOLDER_RES = [re.compile(p, re.IGNORECASE) for p in C.PLACEHOLDER_PATTERNS]


def is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "nat"}:
        return True
    return any(r.match(s) for r in _PLACEHOLDER_RES)


def clean(value: Any) -> str:
    if is_placeholder(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


@dataclass
class Row:
    row_id: int
    part_number: str
    description: str
    e1_brand: str
    unilog_brand: str
    dib_brand: str
    part_manuf: str
    raw: dict[str, str] = field(default_factory=dict)

    # derived at ingest
    tokens: list[TT.Token] = field(default_factory=list)
    skeleton: str = ""
    words: list[str] = field(default_factory=list)

    @property
    def brand_candidates(self) -> list[str]:
        return [b for b in (self.e1_brand, self.unilog_brand, self.dib_brand) if b]

    @property
    def populated_input_cells(self) -> int:
        n = 0
        for v in (self.part_number, self.description, self.e1_brand,
                  self.unilog_brand, self.dib_brand, self.part_manuf):
            if v:
                n += 1
        return n

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "part_number": self.part_number,
            "description": self.description,
            "e1_brand": self.e1_brand,
            "unilog_brand": self.unilog_brand,
            "dib_brand": self.dib_brand,
            "part_manuf": self.part_manuf,
            "skeleton": self.skeleton,
            "raw": self.raw,
        }


@dataclass
class InputProfile:
    source_file: str
    row_count: int
    columns: list[str]
    populated_cells: int
    total_cells: int
    brand_cells: int
    placeholder_brand_cells: int
    placeholder_brand_pct: float
    desc_len_mean: float
    desc_len_min: int
    desc_len_max: int
    desc_len_median: float
    rows_with_no_brand: int
    rows_with_no_manufacturer: int
    distinct_part_manuf: int
    duplicate_part_numbers: int
    unmapped_columns: list[str]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def resolve_input_path(explicit: Path | None = None) -> Path:
    """Prefer the client's real file; fall back to the reconstruction."""
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise FileNotFoundError(p)
        return p
    supplied = C.DATA_IN / C.SUPPLIED_FILES["items_1000"]
    if supplied.exists():
        return supplied
    recon = C.DATA_IN / C.RECONSTRUCTION_INPUT
    if recon.exists():
        return recon
    # any single-sheet workbook or csv dropped in data/in/
    for cand in sorted(C.DATA_IN.glob("*.xlsx")) + sorted(C.DATA_IN.glob("*.csv")):
        if cand.name.startswith("_"):
            continue
        return cand
    raise FileNotFoundError(
        "no catalogue found. Put Sample-1000_Items.xlsx in data/in/ or run "
        "`python tools/make_dataset.py`.")


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    # Do not assume row 1 is a clean header: find the row that names the input columns.
    probe = pd.read_excel(path, header=None, dtype=str, nrows=15)
    header_row = 0
    wanted = {c.lower() for c in C.INPUT_COLUMNS}
    best_hits = -1
    for i in range(len(probe)):
        cells = {str(v).strip().lower() for v in probe.iloc[i].tolist()}
        hits = len(wanted & cells)
        if hits > best_hits:
            best_hits, header_row = hits, i
    return pd.read_excel(path, header=header_row, dtype=str, keep_default_na=False)


_COLUMN_ALIASES = {
    "mfg_part_num": "Mfg_Part_Num",
    "mfg part num": "Mfg_Part_Num",
    "manufacturer part number": "Mfg_Part_Num",
    "mpn": "Mfg_Part_Num",
    "part_num": "Mfg_Part_Num",
    "part number": "Mfg_Part_Num",
    "part_desc": "Part_Desc",
    "part desc": "Part_Desc",
    "description": "Part_Desc",
    "short product description": "Part_Desc",
    "e1_brand": "E1_Brand",
    "e1 brand": "E1_Brand",
    "brand": "E1_Brand",
    "unilog_brand": "Unilog_Brand",
    "unilog brand": "Unilog_Brand",
    "dib_brand": "DIB_Brand",
    "dib brand": "DIB_Brand",
    "part_manuf": "Part_Manuf",
    "part manuf": "Part_Manuf",
    "manufacturer": "Part_Manuf",
}


def load(path: Path | None = None, limit: int | None = None) -> tuple[list[Row], InputProfile]:
    src = resolve_input_path(path)
    df = _read_table(src)

    # map whatever the columns are called onto the contract
    rename: dict[str, str] = {}
    for col in df.columns:
        key = re.sub(r"\s+", " ", str(col)).strip().lower()
        if key in _COLUMN_ALIASES:
            rename[col] = _COLUMN_ALIASES[key]
    df = df.rename(columns=rename)
    unmapped = [str(c) for c in df.columns if c not in C.INPUT_COLUMNS]
    for col in C.INPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    if limit:
        df = df.head(limit)

    rows: list[Row] = []
    for i, rec in df.reset_index(drop=True).iterrows():
        desc = clean(rec.get("Part_Desc"))
        r = Row(
            row_id=int(i),
            part_number=clean(rec.get("Mfg_Part_Num")),
            description=desc,
            e1_brand=clean(rec.get("E1_Brand")),
            unilog_brand=clean(rec.get("Unilog_Brand")),
            dib_brand=clean(rec.get("DIB_Brand")),
            part_manuf=clean(rec.get("Part_Manuf")),
            raw={c: ("" if rec.get(c) is None else str(rec.get(c)))
                 for c in C.INPUT_COLUMNS},
        )
        r.tokens = TT.tokenize(desc)
        r.skeleton = " ".join(t.skeleton for t in r.tokens if t.kind != TT.PUNCT)
        r.words = [t.norm for t in r.tokens if t.kind == TT.WORD and len(t.norm) > 1]
        rows.append(r)

    # ---- profile ------------------------------------------------------------------
    brand_raw = []
    for _i, rec in df.iterrows():
        for c in ("E1_Brand", "Unilog_Brand", "DIB_Brand"):
            brand_raw.append(rec.get(c))
    ph = sum(1 for v in brand_raw if is_placeholder(v))
    lens = [len(r.description) for r in rows] or [0]
    lens_sorted = sorted(lens)
    median = (lens_sorted[len(lens_sorted) // 2] if len(lens_sorted) % 2
              else (lens_sorted[len(lens_sorted) // 2 - 1]
                    + lens_sorted[len(lens_sorted) // 2]) / 2)
    pn_counts: dict[str, int] = {}
    for r in rows:
        pn_counts[r.part_number] = pn_counts.get(r.part_number, 0) + 1

    profile = InputProfile(
        source_file=src.name,
        row_count=len(rows),
        columns=list(C.INPUT_COLUMNS),
        populated_cells=sum(r.populated_input_cells for r in rows),
        total_cells=len(rows) * len(C.INPUT_COLUMNS),
        brand_cells=len(brand_raw),
        placeholder_brand_cells=ph,
        placeholder_brand_pct=round(ph / len(brand_raw) * 100, 2) if brand_raw else 0.0,
        desc_len_mean=round(sum(lens) / len(lens), 2),
        desc_len_min=min(lens),
        desc_len_max=max(lens),
        desc_len_median=float(median),
        rows_with_no_brand=sum(1 for r in rows if not r.brand_candidates),
        rows_with_no_manufacturer=sum(1 for r in rows if not r.part_manuf),
        distinct_part_manuf=len({r.part_manuf for r in rows if r.part_manuf}),
        duplicate_part_numbers=sum(1 for v in pn_counts.values() if v > 1),
        unmapped_columns=unmapped,
    )
    return rows, profile
