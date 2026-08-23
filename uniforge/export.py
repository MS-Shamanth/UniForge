"""Writers for the delivery file and the run artefacts.

The delivery file carries all 252 static headers, in order, with nothing removed,
renamed or retyped - including the columns UniForge deliberately left empty. A delivery
format with the abstentions quietly dropped would be a different schema.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from . import config as C
from .seed import headers as H

DELIVERY_CSV = "uniforge_delivery.csv"
DELIVERY_XLSX = "uniforge_delivery.xlsx"
METRICS_JSON = "metrics.json"
EVIDENCE_JSON = "evidence.json"
REVIEW_JSON = "review_queue.json"
DISCOVERY_JSON = "discovery.json"
SEARCH_JSON = "search_report.json"


def _frame(records: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(records, columns=H.HEADERS)
    return df.fillna("")


def write_csv(records: list[dict[str, str]], out_dir: Path | None = None) -> Path:
    out_dir = out_dir or C.DATA_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / DELIVERY_CSV
    _frame(records).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def write_xlsx(records: list[dict[str, str]], out_dir: Path | None = None) -> Path:
    """Write the formatted workbook.

    This is the slow artefact by a wide margin: 252 columns x 1,000 rows is a quarter of a
    million individually written cells, costing several times the entire nine-stage
    compile. The fix for that is NOT to write it faster but to write it less often — the
    server skips it during a run and generates it on demand, via
    `pipeline.run_and_write(write_xlsx=False)` and the download route.

    xlsxwriter's `constant_memory` option was tried here and rejected. It cut the time
    roughly in half and silently discarded ~46,000 of 47,000 populated cells, leaving a
    workbook with the right shape, the right headers and almost no data. A truncated
    export that opens cleanly is worse than a slow one, so correctness wins and
    `tools/verify_xlsx.py` now reads the file back and counts the cells.
    """
    out_dir = out_dir or C.DATA_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / DELIVERY_XLSX
    df = _frame(records)
    try:
        with pd.ExcelWriter(path, engine="xlsxwriter") as xw:
            df.to_excel(xw, index=False, sheet_name="Delivery Format")
            ws = xw.sheets["Delivery Format"]
            ws.freeze_panes(1, 2)
            ws.autofilter(0, 0, len(df), len(H.HEADERS) - 1)
            head = xw.book.add_format({
                "bold": True, "bg_color": "#15131F",
                "font_color": "#F7F7F8", "border": 1, "border_color": "#2A2438",
            })
            for j, col in enumerate(H.HEADERS):
                ws.write(0, j, col, head)
                ws.set_column(j, j, max(10, min(46, len(col) + 2)))
    except Exception:
        # openpyxl fallback keeps the export working without xlsxwriter
        df.to_excel(path, index=False, sheet_name="Delivery Format")
    return path


def write_delivery(records: list[dict[str, str]], out_dir: Path | None = None,
                   include_xlsx: bool = True) -> dict[str, Path]:
    paths = {"csv": write_csv(records, out_dir)}
    if include_xlsx:
        paths["xlsx"] = write_xlsx(records, out_dir)
    return paths


def write_json(name: str, payload: Any, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or C.DATA_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False,
                               default=str), encoding="utf-8")
    return path


def verify_delivery_schema(path: Path) -> dict[str, Any]:
    """Read the written file back and prove the schema survived the round trip."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols = list(df.columns)
    return {
        "file": path.name,
        "column_count": len(cols),
        "expected": len(H.HEADERS),
        "columns_match_exactly": cols == H.HEADERS,
        "missing": [c for c in H.HEADERS if c not in cols],
        "unexpected": [c for c in cols if c not in H.HEADERS],
        "row_count": len(df),
    }


def verify_xlsx_content(path: Path, records: list[dict[str, str]]) -> dict[str, Any]:
    """Read the workbook back and count what actually landed in it.

    Shape is not enough. A workbook can carry 1,000 rows and 252 correctly ordered headers
    while holding almost no data — that is exactly what xlsxwriter's `constant_memory`
    mode produced here. So this counts populated cells and checks the first and last part
    numbers, which is what makes a silent truncation impossible to miss.
    """
    expected = _frame(records)
    populated_expected = int((expected != "").sum().sum())
    try:
        got = pd.read_excel(path, dtype=str, sheet_name="Delivery Format").fillna("")
    except Exception as exc:
        return {
            "ok": False, "error": f"{type(exc).__name__}: {exc}",
            "rows_read": 0, "columns_read": 0,
            "populated_read": 0, "populated_expected": populated_expected,
        }

    populated_read = int((got != "").sum().sum())
    first_ok = last_ok = False
    if len(got) == len(expected) and "MFG_PART_NUM" in got.columns:
        first_ok = str(got.iloc[0]["MFG_PART_NUM"]) == str(
            expected.iloc[0]["MFG_PART_NUM"])
        last_ok = str(got.iloc[-1]["MFG_PART_NUM"]) == str(
            expected.iloc[-1]["MFG_PART_NUM"])

    return {
        "ok": (len(got) == len(expected)
               and list(got.columns) == H.HEADERS
               and populated_read == populated_expected
               and first_ok and last_ok),
        "rows_read": len(got),
        "rows_expected": len(expected),
        "columns_read": len(got.columns),
        "columns_match": list(got.columns) == H.HEADERS,
        "populated_read": populated_read,
        "populated_expected": populated_expected,
        "first_row_intact": first_ok,
        "last_row_intact": last_ok,
        "bytes": path.stat().st_size if path.exists() else 0,
    }
