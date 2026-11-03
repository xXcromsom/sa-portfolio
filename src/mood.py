"""Sentiment beyond headlines: a fear-and-greed reading for the market and for each stock.

Market level: India VIX, and Tickertape's Market Mood Index (a dated hand snapshot; we hold no history).
Stock level: no public index exists, so we build one. Four price-based signals (momentum, RSI, calm,
distance from the high) are ranked against the stock's own last three years and averaged, 0 = fear and
100 = greed. Because it is built from prices it describes mood rather than measures it independently,
and we say so. Then two tests: does mood or FinBERT news tone predict the next few weeks' excess return?
"""
from __future__ import annotations

import pandas as pd
from scipy import stats

from src.technical import rsi

LOOKBACK = 750          # about three years of trading days
COMPONENTS = {"momentum": "Price vs its 125-day average", "rsi": "14-day RSI", "calm": "Low 20-day volatility",
              "near_high": "Distance from the 250-day high"}


def mood_series(prices: pd.Series) -> pd.DataFrame:
    """Percentile rank (0-100) of each signal over the last LOOKBACK days, plus their mean as `mood`."""
    signals = pd.concat({"momentum": prices / prices.rolling(125).mean() - 1, "rsi": rsi(prices),
                         "calm": -prices.pct_change(fill_method=None).rolling(20).std(),
                         "near_high": prices / prices.rolling(250).max() - 1}, axis=1).dropna()
    ranks = signals.rolling(LOOKBACK, min_periods=250).apply(lambda w: (w <= w[-1]).mean() * 100, raw=True).dropna()
    return ranks.assign(mood=ranks.mean(axis=1))


def stock_mood(prices: pd.Series, market: pd.Series, horizon: int = 20) -> dict:
    """Today's reading, and the stock's excess return over the market after fearful and greedy readings."""
    m = mood_series(prices)
    latest = m.iloc[-1]
    excess = (prices.shift(-horizon) / prices - 1) - (market.shift(-horizon) / market - 1)
    d = pd.concat({"mood": m["mood"], "x": excess}, axis=1).dropna()
    fear, greed = d[d.mood < 25].x, d[d.mood > 75].x
    # Non-overlapping samples: one observation per horizon, so the p-value is not flattered.
    step = d.iloc[::horizon]
    a, b = step[step.mood < 25].x, step[step.mood > 75].x
    p = float(stats.ttest_ind(a, b, equal_var=False).pvalue) if len(a) > 2 and len(b) > 2 else None
    return {"as_of": m.index[-1].date().isoformat(), "mood": float(latest["mood"]), "zone": label(float(latest["mood"])),
            "components": {k: float(latest[k]) for k in COMPONENTS}, "excess_after_fear": float(fear.mean()) if len(fear) else None,
            "excess_after_greed": float(greed.mean()) if len(greed) else None, "fear_days": len(fear), "greed_days": len(greed),
            "p_nonoverlapping": p, "n_nonoverlapping": len(step)}


def label(score: float) -> str:
    if score < 30:
        return "Extreme fear"
    if score < 50:
        return "Fear"
    return "Greed" if score <= 70 else "Extreme greed"


def _slope(d: pd.DataFrame) -> dict:
    fit = stats.linregress(d["v"], d["f"])
    return {"n": len(d), "slope_per_point": float(fit.slope), "r": float(fit.rvalue), "p": float(fit.pvalue)}


def vix_study(vix: pd.Series, nifty: pd.Series, horizon: int = 20, covid=("2020-02-01", "2020-06-30")) -> dict:
    """Does high fear precede higher returns? Quintiles of VIX, and a slope on non-overlapping windows, with and without COVID."""
    d = pd.concat({"v": vix, "n": nifty}, axis=1).dropna()
    d["f"] = d.n.shift(-horizon) / d.n - 1
    d["q"] = pd.qcut(d.v, 5, labels=False) + 1
    table = d.dropna(subset=["f"]).groupby("q").agg(low=("v", "min"), high=("v", "max"), forward=("f", "mean"), days=("f", "size"))
    sample = d.dropna(subset=["f"]).iloc[::horizon]
    without = sample[(sample.index < covid[0]) | (sample.index > covid[1])]
    changes = d[["v", "n"]].pct_change().dropna()
    last = vix.dropna()
    return {"as_of": last.index[-1].date().isoformat(), "level": float(last.iloc[-1]),
            "one_year_percentile": float(last.iloc[-250:].rank(pct=True).iloc[-1]),
            "quintiles": [{"quintile": int(q), **{k: float(v) for k, v in r.items()}} for q, r in table.iterrows()],
            "slope_all": _slope(sample), "slope_without_covid": _slope(without), "same_day_correlation": float(changes.corr().iloc[0, 1])}


def tone_test(news: pd.DataFrame, prices: pd.DataFrame, stocks: list[str], bench: str, window: int = 5) -> dict:
    """FinBERT tone over `window` days vs the next `window` days' excess return, on non-overlapping windows."""
    published = pd.to_datetime(news["published"], errors="coerce", utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    news = news.assign(day=published.dt.normalize()).dropna(subset=["day"])
    out = {}
    for t in stocks:
        p, m = prices[t].dropna(), prices[bench].dropna()
        daily = news[news.ticker == t].groupby("day")["tone"].mean().reindex(p.index)
        tone = daily.rolling(window, min_periods=1).mean()
        ahead = (p.shift(-window) / p - 1) - (m.shift(-window) / m - 1)
        same = p.pct_change(fill_method=None) - m.pct_change(fill_method=None)
        d = pd.concat({"tone": tone, "ahead": ahead, "same": same}, axis=1).dropna()
        step = d.iloc[::window]
        fit, now = stats.linregress(step.tone, step.ahead), stats.linregress(d.tone, d.same)
        out[t] = {"next_r": float(fit.rvalue), "next_p": float(fit.pvalue), "next_n": len(step),
                  "same_day_r": float(now.rvalue), "same_day_p": float(now.pvalue), "same_day_n": len(d)}
    return out


def run(prices: pd.DataFrame, vix: pd.Series | None, news: pd.DataFrame, stocks: list[str], bench: str, snapshot: dict,
        vix_error: str | None = None) -> dict:
    return {
        "as_of": prices.index[-1].date().isoformat(), "components": COMPONENTS,
        "stocks": {t: stock_mood(prices[t].dropna(), prices[bench].dropna()) for t in stocks},
        "vix": vix_study(vix, prices[bench]) if vix is not None and len(vix) else None, "vix_error": vix_error,
        "tone": tone_test(news, prices, stocks, bench), "market_mood_snapshot": snapshot["market_mood"],
    }
