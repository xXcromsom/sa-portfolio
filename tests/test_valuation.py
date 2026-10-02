"""Workbook Summary reader, on small workbooks written with plain values."""
import pandas as pd
import pytest
from openpyxl import Workbook

from src.valuation import read_summary, valuation_record

HEADERS = ["ticker", "name", "model", "price", "cost_of_equity", "intrinsic_value",
           "comps_value", "blended_value", "market_implied_growth", "verdict"]
ROW = ["X.NS", "Example", "Two-stage DDM", 100.0, 0.12, 80.0, 120.0, 100.0, 0.07, "Fairly valued"]


def _write(tmp_path, row):
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(HEADERS)
    ws.append(row)
    path = tmp_path / "v.xlsx"
    wb.save(path)
    return path


def test_reads_summary_and_computes_upside_vs_latest(tmp_path):
    summary = read_summary(_write(tmp_path, ROW))
    record = valuation_record(summary, pd.Series({"X.NS": 50.0}), "2026-10-01")
    upside = record["securities"]["X.NS"]["upside_vs_latest"]
    assert upside == {"intrinsic": pytest.approx(0.6), "comps": pytest.approx(1.4),
                      "blended": pytest.approx(1.0)}


def test_blank_values_raise(tmp_path):
    # What an un-recalculated openpyxl workbook looks like to pandas.
    blank = ROW[:5] + [None] + ROW[6:]
    with pytest.raises(ValueError, match="Open and save"):
        read_summary(_write(tmp_path, blank))
