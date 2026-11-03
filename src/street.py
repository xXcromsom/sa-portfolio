"""What the Street thinks, and what you must believe to agree with it.

data/street/ holds hand-entered, dated figures: broker calls (mostly second-hand press summaries,
flagged as such) and a 3 Nov 2026 snapshot of Yahoo consensus. Our valuation classes then answer the
useful question: not "who is right" but "what discount rate, growth or ROE does each price require?"

The models are the ones in python_project.py, which reproduce the Excel workbook to the paisa.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from python_project import DividendDiscountModel, ValuationModel, load_models

COLUMNS = ["ticker", "broker", "rating", "target", "basis", "as_of", "after_q2", "source_type", "source", "note"]
FIVE_YEARS = int(5 * 248)     # trading rows in the 5-year beta window


def load_views(path: Path) -> pd.DataFrame:
    views = pd.read_csv(path)
    missing = set(COLUMNS) - set(views.columns)
    if missing:
        raise ValueError(f"{path} lacks columns {sorted(missing)}")
    if views["target"].isna().any() or (views["target"] <= 0).any():
        raise ValueError(f"{path} has a blank or non-positive target")
    return views


def load_snapshot(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def with_inputs(model: ValuationModel, **changes) -> ValuationModel:
    """A copy of a model with some inputs changed; validates nothing beyond what the formulas need."""
    other = copy.copy(model)
    vars(other).update(changes)
    return other


def required_discount_rate(model: ValuationModel, target: float, high: float = 0.40) -> float:
    """The r at which the model equals `target`, with every other input unchanged."""
    return float(brentq(lambda r: with_inputs(model, r=r).intrinsic_value() - target, model.g2 + 1e-4, high, xtol=1e-8))


def multi_stage_ddm(d0: float, r: float, stages: list[tuple[float, int]], terminal_g: float) -> float:
    """Dividend discount value with several growth stages, each (growth, years), then Gordon growth."""
    value, dividend, year = 0.0, d0, 0
    for growth, years in stages:
        for _ in range(years):
            dividend *= 1 + growth
            year += 1
            value += dividend / (1 + r) ** year
    return value + dividend * (1 + terminal_g) / (r - terminal_g) / (1 + r) ** year


def consensus_table(snapshot: dict, views: pd.DataFrame, stocks: list[str]) -> dict:
    """Per stock: rating mix, target range and upside on 3 Nov, change since the freeze, and broker range."""
    out = {}
    for t in stocks:
        s = snapshot["securities"][t]
        ratings, target, eps = s["ratings"], s["target"], s["eps"]
        total = sum(ratings.values())
        recent = views[(views.ticker == t) & (views.after_q2 == "yes")]
        low, high = recent.loc[recent.target.idxmin()], recent.loc[recent.target.idxmax()]
        out[t] = {
            "price": s["price"], "analysts": total, "buy_share": (ratings["strong_buy"] + ratings["buy"]) / total,
            "ratings": ratings, "target": target, "upside_to_mean": target["mean"] / s["price"] - 1,
            "target_change_since_freeze": target["mean"] / s["at_freeze"]["target_mean"] - 1,
            "eps_fy28": eps["FY28"]["value"], "eps_fy28_change_since_freeze": eps["FY28"]["value"] / s["at_freeze"]["eps_FY28"] - 1,
            "pe_fy28": s["price"] / eps["FY28"]["value"],
            "brokers_after_q2": len(recent),
            "lowest_broker": {"broker": low.broker, "rating": low.rating, "target": float(low.target)},
            "highest_broker": {"broker": high.broker, "rating": high.rating, "target": float(high.target)},
            "q2": s["q2"], "screener": s["screener"], "holdings_jun25_sep26": s["holdings_jun25_sep26"],
        }
    return out


def _beta(returns: pd.DataFrame, t: str, bench: str, rows: int | None = None) -> float:
    d = returns if rows is None else returns.iloc[-rows:]
    return float(np.cov(d[t], d[bench])[0, 1] / d[bench].var())


def beta_windows(returns: pd.DataFrame, stocks: list[str], bench: str) -> dict:
    windows = {"full": None, "5y": FIVE_YEARS, "3y": int(3 * 248), "1y": int(1 * 248)}
    return {t: {name: _beta(returns, t, bench, rows) for name, rows in windows.items()} for t in stocks}


def icici_bridge(model: ValuationModel, beta_5y: float, rf: float, erp: float, inputs: dict, price: float, target: float) -> list[dict]:
    """Walk from our ICICI value to the price, changing one assumption at a time."""
    steps = [{"step": "Our model (full-sample beta)", "detail": f"r = {model.r:.2%}, ROE 16% then 15%", "value": model.intrinsic_value()}]
    r_5y = rf + beta_5y * erp
    m = with_inputs(model, r=r_5y)
    steps.append({"step": "Use the 5-year beta", "detail": f"beta {beta_5y:.2f}, so r = {r_5y:.2%}", "value": m.intrinsic_value()})
    subs = inputs["subsidiaries_per_share"]
    steps.append({"step": "Add the subsidiaries", "detail": f"Rs {subs} a share (Motilal's sum of the parts)", "value": m.intrinsic_value() + subs})
    m = with_inputs(m, roe_high=inputs["roe_high"], roe_stable=inputs["roe_stable"])
    steps.append({"step": "Use the Street's ROE", "detail": f"{inputs['roe_high']:.0%} for five years, then {inputs['roe_stable']:.0%}",
                  "value": m.intrinsic_value() + subs})
    steps.append({"step": "Price, 3 Nov", "detail": "The gap left is what the market pays for growth above 5.5%", "value": price})
    steps.append({"step": "Analysts' mean target", "detail": "Yahoo consensus, 3 Nov", "value": target})
    return steps


def what_you_must_believe(returns: pd.DataFrame, stocks: list[str], bench: str, rf: float, erp: float, snapshot: dict,
                          workbook: Path) -> dict:
    """The required discount rate at price and target, the value at the 5-year beta, and the HUL and ICICI detail."""
    models = load_models(workbook)
    betas = beta_windows(returns, stocks, bench)
    out = {"betas": betas, "stocks": {}}
    for t in stocks:
        model, s = models[t], snapshot["securities"][t]
        r_5y = rf + betas[t]["5y"] * erp
        out["stocks"][t] = {
            "model": type(model).__name__, "our_r": model.r, "our_value": model.intrinsic_value(), "r_5y_beta": r_5y,
            "value_at_5y_beta": with_inputs(model, r=r_5y).intrinsic_value(),
            "r_needed_for_price": required_discount_rate(model, s["price"]),
            "r_needed_for_target": required_discount_rate(model, s["target"]["mean"]),
        }
    hul = models["HINDUNILVR.NS"]
    assert isinstance(hul, DividendDiscountModel)
    out["hul_growth_paths"] = [
        {"path": f"{a:.0%} for {n1} years, {b:.0%} for {n2} years, then {g:.1%}", "value": multi_stage_ddm(hul.d0, hul.r, [(a, n1), (b, n2)], g)}
        for a, n1, b, n2, g in ((0.10, 10, 0.08, 10, 0.055), (0.12, 10, 0.09, 10, 0.06))]
    icici = snapshot["securities"]["ICICIBANK.NS"]
    out["icici_bridge"] = icici_bridge(models["ICICIBANK.NS"], betas["ICICIBANK.NS"]["5y"], rf, erp, snapshot["icici_bridge_inputs"],
                                       icici["price"], icici["target"]["mean"])
    return out


def weights_at_5y_beta(returns: pd.DataFrame, stocks: list[str], bench: str, rf: float, erp: float, A: float, bounds=(0.10, 0.60)) -> dict:
    """How far the portfolio would move on the 5-year beta (not used: the base case stays at the full-sample beta)."""
    from python_project import max_sharpe_weights

    cov = returns[stocks].cov().to_numpy() * 252
    capm = np.array([rf + _beta(returns, t, bench, FIVE_YEARS) * erp for t in stocks])
    w = max_sharpe_weights(capm, cov, rf, bounds)
    er, vol = float(w @ capm), float(np.sqrt(w @ cov @ w))
    return {"weights": dict(zip(stocks, map(float, w))), "expected_return": er, "volatility": vol, "sharpe": (er - rf) / vol,
            "y": min((er - rf) / (A * vol ** 2), 1.0)}
