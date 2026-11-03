"""Tests of market efficiency beyond the trading rules (BKM Ch 11-12).

Weak form: if past returns predict future returns, daily returns should autocorrelate and the
variance of q-day returns should differ from q times the daily variance. Both use standard errors
that allow for volatility clustering (Lo & MacKinlay, 1988).

Semi-strong form: prices should react to earnings news at once and show no drift afterwards, so the
test is the abnormal return after the announcement window, not only the reaction inside it. Windows
are in trading days around the first session on or after the results date; abnormal returns come
from a market model fitted on the 250 days before day -1.

We do not test strong-form efficiency: it needs inside information we do not have.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

WINDOWS = {"pre": (-20, -2), "ev": (-1, 1), "d20": (2, 20), "d60": (2, 60)}


def lag1_autocorrelation(returns: np.ndarray) -> dict:
    """First-order autocorrelation with a heteroskedasticity-robust z."""
    e = np.asarray(returns) - np.mean(returns)
    denom = (e ** 2).sum()
    rho = (e[1:] * e[:-1]).sum() / denom
    se = np.sqrt((e[1:] ** 2 * e[:-1] ** 2).sum()) / denom
    return {"rho": float(rho), "z": float(rho / se)}


def variance_ratio(returns: np.ndarray, q: int) -> dict:
    """Lo-MacKinlay VR(q) with the heteroskedasticity-robust z. Under a random walk VR = 1 and z ~ N(0, 1)."""
    x = np.asarray(returns) - np.mean(returns)
    n = len(x)
    s1 = (x ** 2).sum() / (n - 1)
    q_sums = np.convolve(x, np.ones(q), "valid")
    vr = (q_sums ** 2).sum() / (q * (n - q + 1) * (1 - q / n)) / s1
    total = (x ** 2).sum() ** 2
    theta = sum((2 * (q - j) / q) ** 2 * n * (x[j:] ** 2 * x[:-j] ** 2).sum() / total for j in range(1, q))
    return {"vr": float(vr), "z": float((vr - 1) * np.sqrt(n) / np.sqrt(theta))}


def weak_form(returns: pd.DataFrame, horizons=(5, 20, 60)) -> dict:
    out = {}
    for col in returns.columns:
        x = returns[col].dropna().to_numpy()
        out[col] = {"n": len(x), **lag1_autocorrelation(x), "variance_ratios": {str(q): variance_ratio(x, q) for q in horizons}}
    return out


def drift_events(returns: pd.DataFrame, consensus: dict, stocks: list[str], bench: str, estimation: int = 250) -> pd.DataFrame:
    """One row per results date: the surprise, and the abnormal return in each window (NaN if it runs off the data)."""
    rows = []
    market, dates = returns[bench], returns.index
    for t in stocks:
        for s in consensus[t].get("surprises", []):
            pos = dates.searchsorted(pd.Timestamp(s["date"]))
            if pos - estimation - 1 < 0 or pos + 1 >= len(dates):
                continue
            fit = np.arange(pos - estimation - 1, pos - 1)
            slope = np.cov(returns[t].iloc[fit], market.iloc[fit])[0, 1] / market.iloc[fit].var()
            intercept = returns[t].iloc[fit].mean() - slope * market.iloc[fit].mean()
            abnormal = returns[t] - intercept - slope * market
            row = {"ticker": t, "date": s["date"], "estimate": s["estimate"], "reported": s["reported"],
                   "surprise_pct": s["surprise_pct"]}
            for name, (a, b) in WINDOWS.items():
                row[name] = float(abnormal.iloc[pos + a: pos + b + 1].sum()) if pos + b < len(dates) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def _mean_t(x: pd.Series) -> dict:
    x = x.dropna()
    return {"n": len(x), "mean": float(x.mean()), "t": float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))}


def _difference(a: pd.Series, b: pd.Series) -> dict:
    """Welch difference in means, with a 95% interval."""
    a, b = a.dropna(), b.dropna()
    diff = a.mean() - b.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    test = stats.ttest_ind(a, b, equal_var=False)
    return {"diff": float(diff), "low": float(diff - 1.96 * se), "high": float(diff + 1.96 * se),
            "t": float(test.statistic), "p": float(test.pvalue)}


def _slope(x: pd.Series, y: pd.Series) -> dict:
    d = pd.concat({"x": x, "y": y}, axis=1).dropna()
    fit = stats.linregress(d["x"], d["y"])
    return {"n": len(d), "slope_per_point": float(fit.slope), "r": float(fit.rvalue), "p": float(fit.pvalue)}


def semi_strong(events: pd.DataFrame, clean_limit: float = 30.0) -> dict | None:
    """Reaction and drift after beats and misses. Surprises of clean_limit% or more are reported and tested separately."""
    if events.empty:
        return None
    beats, misses = events[events.surprise_pct > 0], events[events.surprise_pct < 0]
    relative = events.surprise_pct - events.groupby("ticker").surprise_pct.transform("median")
    clean = events[events.surprise_pct.abs() < clean_limit]
    record = {t: {"events": len(g), "beat_share": float((g.surprise_pct > 0).mean()), "median_surprise": float(g.surprise_pct.median()),
                  "median_absolute_surprise": float(g.surprise_pct.abs().median())}
              for t, g in events.groupby("ticker")}
    flagged = events[events.surprise_pct.abs() >= clean_limit].sort_values("surprise_pct", key=abs, ascending=False)
    return {
        "events": len(events), "estimation_days": 250, "windows": {k: list(v) for k, v in WINDOWS.items()},
        "beats": {w: _mean_t(beats[w]) for w in WINDOWS},
        "misses": {w: _mean_t(misses[w]) for w in WINDOWS},
        "beat_minus_miss": {w: _difference(beats[w], misses[w]) for w in ("ev", "d20", "d60")},
        "above_minus_below_own_median": {w: _difference(events.loc[relative > 0, w], events.loc[relative < 0, w])
                                         for w in ("ev", "d20", "d60")},
        "reaction_on_surprise": {"all": _slope(events.surprise_pct, events.ev), "clean": _slope(clean.surprise_pct, clean.ev)},
        "drift60_on_surprise": {"all": _slope(events.surprise_pct, events.d60), "clean": _slope(clean.surprise_pct, clean.d60)},
        "consensus_record": record,
        "flagged_surprises": flagged[["ticker", "date", "estimate", "reported", "surprise_pct"]].round(2).to_dict(orient="records"),
        "clean_limit_pct": clean_limit,
    }
