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


def write_delivery(records: list[dict[str, str]],
                   out_dir: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or C.DATA_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    df = _frame(records)

    csv_path = out_dir / DELIVERY_CSV
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    xlsx_path = out_dir / DELIVERY_XLSX
    try:
        with pd.ExcelWriter(xlsx_path, engine="xlsxwriter") as xw:
            df.to_excel(xw, index=False, sheet_name="Delivery Format")
            ws = xw.sheets["Delivery Format"]
            ws.freeze_panes(1, 2)
            ws.autofilter(0, 0, len(df), len(H.HEADERS) - 1)
            head = xw.book.add_format({"bold": True, "bg_color": "#0B1220",
                                       "font_color": "#E6EDF7", "border": 1})
            for j, col in enumerate(H.HEADERS):
                ws.write(0, j, col, head)
                width = max(10, min(46, len(col) + 2))
                ws.set_column(j, j, width)
    except Exception:
        # openpyxl fallback keeps the export working without xlsxwriter
        df.to_excel(xlsx_path, index=False, sheet_name="Delivery Format")

    return {"csv": csv_path, "xlsx": xlsx_path}


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
