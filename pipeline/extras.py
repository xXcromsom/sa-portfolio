"""Efficiency tests, performance measures, Street check and mood, for one dataset.

These read a dataset's existing files and write new ones beside them (emh.json, performance.json,
street.json, mood.json), so no number already in data/submission changes. run_all calls this for
data/latest; for the frozen copy run it once by hand:
    python -m pipeline.extras --dataset submission
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime

import pandas as pd

from src import emh_tests as emh
from src import mood
from src import quant_utils as qu
from src import street
from src.config import load_config, project_path
from src.data_ingest import make_session

NEW_FILES = ["emh.json", "performance.json", "street.json", "mood.json", "india_vix.parquet"]


def _dump(obj, path) -> None:
    path.write_text(json.dumps(obj, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")


def _measures(r: pd.Series, market: pd.Series, rf: float, periods: int) -> dict:
    sig = qu.alpha_significance(r, market, rf, periods)
    return {"cagr": float(qu.annualized_return(r, periods)), "volatility": float(qu.annualized_volatility(r, periods)),
            "excess_return": float((r - qu.periodic_rf(rf, periods)).mean() * periods),  # Rp - Rf, the numerator of Sharpe and Treynor
            "excess_over_market": float((r - market).mean() * periods),                  # Rp - Rm
            "sharpe": float(qu.sharpe_ratio(r, rf, periods)), "beta": float(qu.beta(r, market)),
            "treynor": float(qu.treynor_ratio(r, market, rf, periods)), "jensen_alpha": sig["alpha"], "alpha_t": sig["t"],
            "information_ratio": sig["information_ratio"], "max_drawdown": float(qu.max_drawdown(r))}


def performance(returns: pd.DataFrame, portfolio: dict, stocks: list[str], bench: str, rf: float, erp: float, periods: int) -> dict:
    """Sharpe, Treynor and Jensen's alpha: stocks over the full sample, portfolios over the out-of-sample test."""
    market = returns[bench]
    P = portfolio["views"]["forward"]["tangency"]
    w = pd.Series(P["weights"])
    full = {t: _measures(returns[t], market, rf, periods) for t in stocks + [bench]}
    full["P at today's weights"] = _measures(returns[w.index] @ w, market, rf, periods)
    oos_block = portfolio["out_of_sample"]
    oos = returns[returns.index > pd.Timestamp(oos_block["in_sample"].split(" to ")[1])]
    tests = {name: _measures(oos[list(oos_block[name]["weights"])] @ pd.Series(oos_block[name]["weights"]), oos[bench], rf, periods)
             for name in ("Forward-looking P", "Equal weight", "History-based P")}
    tests["Nifty 50"] = _measures(oos[bench], oos[bench], rf, periods)
    profiles = {name: {"A": p["risk_aversion"], "y": p["y"], "alpha_on_your_money": tests["Forward-looking P"]["jensen_alpha"] * p["y"]}
                for name, p in portfolio["profiles"].items()}
    return {
        "as_of": returns.index[-1].date().isoformat(), "risk_free_rate": rf, "equity_risk_premium": erp, "newey_west_lags": 5,
        "full_sample": {"period": f"{returns.index[0].date()} to {returns.index[-1].date()}", "rows": full},
        "out_of_sample": {"period": oos_block["test"], "weights_fitted_on": oos_block["in_sample"], "rows": tests,
                          "weights": {k: oos_block[k]["weights"] for k in ("Forward-looking P", "Equal weight", "History-based P")}},
        "forward_view": {"alpha": 0.0, "treynor": erp, "p_sharpe": P["sharpe"], "market_sharpe": portfolio["views"]["forward"]["market"]["sharpe"],
                         "note": "With CAPM returns as inputs, every asset has alpha 0 and Treynor = ERP by construction, so these can only be measured on realised returns."},
        "by_profile": profiles,
    }


def _load_vix(folder, last_date: pd.Timestamp, refresh: bool) -> tuple[pd.Series | None, str | None]:
    """India VIX, kept outside the returns universe. A failed download is reported, never replaced by a guess."""
    path = folder / "india_vix.parquet"
    error = None
    if refresh or not path.exists():
        import yfinance as yf

        try:
            raw = yf.download("^INDIAVIX", start="2016-01-01", auto_adjust=True, progress=False, session=make_session())["Close"]
            series = (raw.iloc[:, 0] if isinstance(raw, pd.DataFrame) else raw).dropna().rename("india_vix")
            if series.empty:
                raise ValueError("Yahoo returned no rows")
            series.loc[:last_date].to_frame().to_parquet(path)
        except Exception as err:  # yfinance raises many network error types
            error = f"{type(err).__name__}: {err}"
            print(f"  WARNING: India VIX download failed ({error})")
    if not path.exists():
        return None, error
    return pd.read_parquet(path)["india_vix"].loc[:last_date], error


def run_extras(dataset: str = "latest", refresh: bool = False) -> None:
    cfg = load_config()
    folder = project_path(f"data/{dataset}")
    stocks, bench = list(cfg["universe"]["stocks"]), cfg["universe"]["benchmark"]
    m = cfg["market"]
    rf, erp, periods = m["risk_free_rate"], m["equity_risk_premium"], m["trading_days"]
    read = lambda name: json.loads((folder / name).read_text(encoding="utf-8"))  # noqa: E731
    returns = pd.read_parquet(folder / "returns_daily.parquet")
    prices = pd.read_parquet(folder / "prices.parquet")
    consensus, portfolio, ai = read("consensus.json"), read("portfolio.json"), read("ai_analysis.json")
    snapshot = street.load_snapshot(project_path("data/street/snapshot.json"))
    views = street.load_views(project_path("data/street/street_views.csv"))

    # EMH
    events = emh.drift_events(returns, consensus, stocks, bench)
    ta = pd.DataFrame(ai["technical_analysis"])
    hold = ta[ta.rule == "Buy and hold"].set_index("ticker").sharpe
    rules = ta[ta.rule != "Buy and hold"]
    _dump({"as_of": returns.index[-1].date().isoformat(), "weak_form": emh.weak_form(returns[stocks + [bench]]),
           "trading_rules": {"beat_buy_and_hold": int((rules.sharpe > rules.ticker.map(hold)).sum()), "tested": len(rules)},
           "semi_strong": emh.semi_strong(events), "strong_form": "Not tested: it needs inside information we do not have.",
           "surprises_error": {t: consensus[t].get("surprises_error") for t in stocks if consensus[t].get("surprises_error")}},
          folder / "emh.json")

    # Performance measures
    _dump(performance(returns, portfolio, stocks, bench, rf, erp, periods), folder / "performance.json")

    # Street check and what each price requires (dated 3 Nov, whichever dataset this is)
    _dump({"as_of": snapshot["as_of"], "note": snapshot["note"], "sources": snapshot["sources"],
           "consensus": street.consensus_table(snapshot, views, stocks),
           "must_believe": street.what_you_must_believe(returns, stocks, bench, rf, erp, snapshot, project_path("workbook/valuation.xlsx")),
           "at_5y_beta": street.weights_at_5y_beta(returns, stocks, bench, rf, erp, A=4.0),
           "organon": snapshot["organon"], "literature": snapshot["literature"], "brokers": views.fillna("").to_dict(orient="records"),
           "nifty_change_since_freeze": snapshot["nifty"] / float(prices[bench].loc[:"2026-10-13"].iloc[-1]) - 1},
          folder / "street.json")

    # Mood
    vix, vix_error = _load_vix(folder, prices.index[-1], refresh)
    news = pd.read_parquet(folder / "news_scored.parquet")
    _dump(mood.run(prices, vix, news, stocks, bench, snapshot, vix_error), folder / "mood.json")

    frozen = folder / "FROZEN.json"
    if frozen.exists():  # the manifest lists these additions, and says they changed no frozen number
        manifest = json.loads(frozen.read_text(encoding="utf-8"))
        manifest["files"] = sorted(set(manifest["files"]) | set(NEW_FILES))
        manifest["extras_added_at"] = datetime.now().isoformat(timespec="seconds")
        frozen.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Extras written to {folder.name}: {', '.join(NEW_FILES)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", default="latest", choices=["latest", "submission"])
    parser.add_argument("--refresh", action="store_true", help="re-download India VIX")
    args = parser.parse_args()
    run_extras(args.dataset, args.refresh)

