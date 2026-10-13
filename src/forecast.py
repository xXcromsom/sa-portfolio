"""Phase 3: forecasts against analyst consensus, and an earnings-surprise event study.

- Consensus (Yahoo): EPS estimates for this year and next, analyst price targets
  and past earnings surprises.
- Our price targets: the peer median P/E (valuation workbook) times next year's
  consensus EPS, set beside our DDM / residual-income values.
- Event study (semi-strong efficiency, BKM Ch 11): the abnormal return from
  the day before to the day after each results date, using the market model
  estimated over the previous 250 trading days. If prices react to surprises
  within a day or two, public news is quickly priced in.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf


def consensus(ticker: str, session=None) -> dict:
    """Analyst consensus from Yahoo; any piece Yahoo lacks is recorded as None, not guessed."""
    t = yf.Ticker(ticker, session=session)
    out: dict = {"ticker": ticker}
    try:
        e = t.earnings_estimate
        out["eps_estimates"] = {p: {"avg": float(e.at[p, "avg"]), "analysts": int(e.at[p, "numberOfAnalysts"]),
                                    "growth": float(e.at[p, "growth"])}
                                for p in e.index if p in ("0y", "+1y")}
    except Exception as err:  # Yahoo omits this table for some tickers
        out["eps_estimates"], out["eps_estimates_error"] = None, type(err).__name__
    try:
        out["price_targets"] = {k: float(v) for k, v in t.analyst_price_targets.items()}
    except Exception as err:
        out["price_targets"], out["price_targets_error"] = None, type(err).__name__
    try:
        ed = t.earnings_dates.dropna(subset=["Reported EPS"])
        ed.index = ed.index.tz_convert("Asia/Kolkata").tz_localize(None).normalize()
        out["surprises"] = [{"date": d.date().isoformat(), "estimate": float(r["EPS Estimate"]),
                             "reported": float(r["Reported EPS"]), "surprise_pct": float(r["Surprise(%)"])}
                            for d, r in ed.iterrows()]
    except Exception as err:
        out["surprises"], out["surprises_error"] = [], type(err).__name__
    return out


def event_study(stock: pd.Series, market: pd.Series, dates: list[str], estimation: int = 250,
                window: tuple[int, int] = (-1, 1)) -> pd.DataFrame:
    """Cumulative abnormal return over `window` trading days around each date (market model)."""
    r = pd.concat({"s": stock, "m": market}, axis=1).dropna()
    rows = []
    for d in dates:
        pos = r.index.searchsorted(pd.Timestamp(d))      # first trading day on/after the announcement
        if pos - estimation + window[0] < 0 or pos + window[1] >= len(r):
            continue
        est = r.iloc[pos - estimation + window[0]: pos + window[0]]
        beta = np.cov(est["s"], est["m"])[0, 1] / est["m"].var()
        alpha = est["s"].mean() - beta * est["m"].mean()
        ev = r.iloc[pos + window[0]: pos + window[1] + 1]
        rows.append({"date": d, "car": float((ev["s"] - alpha - beta * ev["m"]).sum()),
                     "raw_return": float((1 + ev["s"]).prod() - 1)})
    return pd.DataFrame(rows)


def our_targets(eps_next: float | None, peer_pe: float, model_value: float, price: float) -> dict:
    """Simple target range: peer P/E on next year's EPS, beside the model value."""
    pe_target = peer_pe * eps_next if eps_next else None
    return {"peer_pe": peer_pe, "eps_next_year": eps_next, "pe_target": pe_target,
            "pe_target_upside": (pe_target / price - 1) if pe_target else None,
            "model_value": model_value, "model_upside": model_value / price - 1}
