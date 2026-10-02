"""Build data/latest/ from scratch. Phase 1: prices -> metrics, correlation, SML.

Run from the project root:
    python -m pipeline.run_all            # use cached prices if present
    python -m pipeline.run_all --refresh  # re-download prices first
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from src import quant_utils as qu
from src.config import load_config, project_path
from src.data_ingest import load_prices
from src.metrics import correlation_check, metrics_table, sml_figure
from src.valuation import read_summary, valuation_record


def _frame_to_dict(df: pd.DataFrame) -> dict:
    return json.loads(df.round(6).to_json(orient="index"))


def main(refresh: bool = False) -> None:
    cfg = load_config()
    stocks = list(cfg["universe"]["stocks"])
    bench = cfg["universe"]["benchmark"]
    mkt = cfg["market"]
    periods, rf, erp = mkt["trading_days"], mkt["risk_free_rate"], mkt["equity_risk_premium"]
    labels = {t: v["name"] for t, v in cfg["universe"]["stocks"].items()}
    labels[bench] = cfg["universe"]["benchmark_name"]
    out_dir = project_path(cfg["data"]["latest_dir"])

    prices, meta = load_prices(cfg, refresh=refresh)
    returns = qu.to_returns(prices)

    table = metrics_table(returns, bench, rf, erp, periods)
    corr_check = correlation_check(returns, stocks, cfg["data"]["correlation_window_years"],
                                   periods=periods)
    cov_annual = returns[stocks].cov() * periods

    metrics = {
        "as_of": meta["last_date"],
        "assumptions": {
            "periods_per_year": periods,
            "risk_free_rate": rf, "risk_free_source": mkt["risk_free_source"],
            "risk_free_as_of": str(mkt["risk_free_as_of"]),
            "equity_risk_premium": erp, "erp_source": mkt["erp_source"],
            "erp_as_of": str(mkt["erp_as_of"]),
            "benchmark": f"{labels[bench]} price index (excludes dividends)",
            "ratio_convention": "arithmetic mean excess return x periods; cagr is geometric",
        },
        "data": meta,
        "names": labels,
        "securities": _frame_to_dict(table),
        "correlation_full_sample": _frame_to_dict(returns[stocks].corr()),
        "correlation_check": corr_check,
        "covariance_annualized": _frame_to_dict(cov_annual),
    }
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    table.rename(index=labels).to_csv(out_dir / "metrics_table.csv", float_format="%.6f")
    sml_figure(table, stocks, bench, labels, rf, periods).savefig(out_dir / "figures" / "sml.png")

    _print_summary(table.rename(index=labels), meta, corr_check, labels)

    workbook = project_path("workbook/valuation.xlsx")
    if workbook.exists():
        record = valuation_record(read_summary(workbook), prices.iloc[-1], meta["last_date"])
        (out_dir / "valuation.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        _print_valuation(record)
    else:
        print("\nNo workbook/valuation.xlsx yet; skipping valuation.json")


def _print_valuation(record: dict) -> None:
    print(f"\nValuation vs latest close ({record['latest_price_date']}):")
    for v in record["securities"].values():
        up = v["upside_vs_latest"]
        print(f"  {v['name']:<20} price {v['latest_price']:>8,.0f} | model {v['intrinsic_value']:>8,.0f} "
              f"({up['intrinsic']:+.0%}) | comps {v['comps_value']:>8,.0f} ({up['comps']:+.0%}) | "
              f"blended {up['blended']:+.0%} | market-implied g {v['market_implied_growth']:.1%}")


def _print_summary(table: pd.DataFrame, meta: dict, corr_check: dict, labels: dict) -> None:
    pct = ["cagr", "mean_return", "volatility", "max_drawdown", "treynor",
           "jensen_alpha", "capm_required_return"]
    shown = table.copy()
    for col in pct:
        shown[col] = shown[col].map("{:.1%}".format)
    for col in ["sharpe", "sortino", "beta"]:
        shown[col] = shown[col].map("{:.2f}".format)
    print(f"\nPrices {meta['first_date']} to {meta['last_date']} "
          f"({meta['observations']} days; {len(meta['dropped_incomplete_dates'])} incomplete dates dropped)\n")
    print(shown.T.to_string())
    print(f"\nCorrelation check ({corr_check['window_start']} to {corr_check['window_end']}):")
    for pair, value in corr_check["pairs"].items():
        a, b = pair.split(" / ")
        print(f"  {labels[a]} / {labels[b]}: {value:.2f}")
    verdict = "PASS" if corr_check["passes"] else "FAIL"
    print(f"  max {corr_check['max_correlation']:.2f} vs threshold "
          f"{corr_check['threshold']:.2f} -> {verdict}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="re-download prices")
    main(parser.parse_args().refresh)
