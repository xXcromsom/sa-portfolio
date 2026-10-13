"""Read the valuation workbook's Summary sheet. Excel is the source of truth.

Intrinsic and comps values change only when someone edits the workbook. Prices
change every day, so upside is also recomputed against the latest close.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

VALUE_COLUMNS = ["price", "cost_of_equity", "intrinsic_value", "comps_value",
                 "blended_value", "market_implied_growth"]
TEXT_COLUMNS = ["ticker", "name", "model", "verdict"]


def read_summary(path: Path) -> pd.DataFrame:
    """Summary sheet as a DataFrame indexed by ticker.

    Raises ValueError if values are blank: openpyxl-written formulas have no
    computed values until Excel calculates and saves the file.
    """
    df = pd.read_excel(path, sheet_name="Summary")
    missing = set(VALUE_COLUMNS + TEXT_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Summary sheet is missing columns {sorted(missing)}; keep its layout")
    if df[VALUE_COLUMNS + TEXT_COLUMNS].isna().any().any():
        raise ValueError("Summary sheet has blank values. Open and save the workbook in Excel "
                         "(or run scripts/recalc_excel.py) so its formulas are calculated.")
    return df.set_index("ticker")


def valuation_record(summary: pd.DataFrame, latest_prices: pd.Series, as_of: str,
                     stocks: list[str] | None = None) -> dict:
    """Workbook values plus upside against the latest close, one entry per ticker.

    Raises ValueError if the workbook covers different stocks from the config
    (e.g. after a stock swap), so a stale valuation is never published.
    """
    if stocks is not None and set(summary.index) != set(stocks):
        raise ValueError(f"valuation workbook covers {sorted(summary.index)} but config.yaml lists "
                         f"{sorted(stocks)}; update scripts/build_valuation_workbook.py and rebuild it")
    record = {"latest_price_date": as_of, "securities": {}}
    for ticker, row in summary.iterrows():
        latest = float(latest_prices[ticker])
        record["securities"][ticker] = {
            "name": row["name"],
            "model": row["model"],
            "workbook_price": round(float(row["price"]), 2),
            "latest_price": round(latest, 2),
            "cost_of_equity": round(float(row["cost_of_equity"]), 6),
            "intrinsic_value": round(float(row["intrinsic_value"]), 2),
            "comps_value": round(float(row["comps_value"]), 2),
            "blended_value": round(float(row["blended_value"]), 2),
            "market_implied_growth": round(float(row["market_implied_growth"]), 6),
            "upside_vs_latest": {
                key: round(float(row[f"{key}_value"]) / latest - 1, 6)
                for key in ("intrinsic", "comps", "blended")
            },
            "workbook_verdict": row["verdict"],
        }
    return record
