"""Read the written workbook back and prove it holds the whole delivery file.

A workbook that opens is not a workbook that is complete. This checks the shape and the
content, because a silently truncated export is the worst kind of bug: the file looks fine
until someone counts the rows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniforge import config as C, export  # noqa: E402
from uniforge.seed import headers as H  # noqa: E402

csv_path = C.DATA_OUT / export.DELIVERY_CSV
xlsx_path = C.DATA_OUT / export.DELIVERY_XLSX

if not csv_path.exists():
    raise SystemExit("no CSV yet — run: python -m uniforge.cli compile")

csv = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
print(f"\nCSV   {csv_path.name}")
print(f"  {len(csv):,} rows x {len(csv.columns)} columns   "
      f"{csv_path.stat().st_size:,} bytes")

if not xlsx_path.exists():
    print("\nno XLSX on disk; generating one")
    export.write_xlsx(csv.to_dict("records"))

xl = pd.read_excel(xlsx_path, dtype=str, sheet_name="Delivery Format")
xl = xl.fillna("")
print(f"\nXLSX  {xlsx_path.name}")
print(f"  {len(xl):,} rows x {len(xl.columns)} columns   "
      f"{xlsx_path.stat().st_size:,} bytes")

ok = True


def check(name: str, passed: bool, detail: str = "") -> None:
    global ok
    print(f"  {'PASS' if passed else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not passed:
        ok = False


print()
check("XLSX row count matches the CSV", len(xl) == len(csv),
      f"{len(xl):,} vs {len(csv):,}")
check("XLSX has all 252 columns", len(xl.columns) == 252, str(len(xl.columns)))
check("column order is exact", list(xl.columns) == H.HEADERS)

if len(xl) == len(csv) and len(xl.columns) == len(csv.columns):
    populated_csv = int((csv != "").sum().sum())
    populated_xl = int((xl != "").sum().sum())
    check("populated cell counts agree",
          abs(populated_csv - populated_xl) <= 0,
          f"{populated_xl:,} vs {populated_csv:,}")
    check("first row survives",
          str(xl.iloc[0]["MFG_PART_NUM"]) == str(csv.iloc[0]["MFG_PART_NUM"]),
          f"{xl.iloc[0]['MFG_PART_NUM']!r}")
    check("last row survives",
          str(xl.iloc[-1]["MFG_PART_NUM"]) == str(csv.iloc[-1]["MFG_PART_NUM"]),
          f"{xl.iloc[-1]['MFG_PART_NUM']!r}")

print()
sys.exit(0 if ok else 1)
