"""Download, align and validate daily prices.

Prices are Yahoo Finance closes adjusted for splits, bonuses and dividends, pulled
with yfinance. yfinance is an unofficial scraper: it is free, but Yahoo can
rate-limit it or change its responses without notice. That is why every fetch is
validated and the pipeline fails closed instead of saving partial data.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from curl_cffi import requests as curl_requests

from src.config import project_path


def make_session() -> curl_requests.Session | None:
    """HTTP session for yfinance, with a custom CA bundle if CA_BUNDLE is set.

    Antivirus HTTPS scanning (e.g. Avast Web Shield) re-signs certificates with
    its own root. Windows trusts that root but curl_cffi only trusts certifi's
    bundle, so every request fails certificate verification and yfinance returns
    empty data. scripts/build_ca_bundle.py writes a bundle that adds the Windows
    trust store. CA_BUNDLE is left unset on GitHub Actions and Streamlit Cloud.
    """
    ca_bundle = os.getenv("CA_BUNDLE")
    if not ca_bundle:
        return None
    path = Path(ca_bundle) if Path(ca_bundle).is_absolute() else project_path(ca_bundle)
    if not path.exists():
        raise FileNotFoundError(f"CA_BUNDLE points to {path}, which does not exist; "
                                "run scripts/build_ca_bundle.py")
    return curl_requests.Session(impersonate="chrome", verify=str(path))


def fetch_prices(tickers: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    """Adjusted daily closes, one column per ticker. `end` is exclusive (yfinance rule)."""
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                      progress=False, session=make_session())
    if raw.empty:
        raise RuntimeError("yfinance returned no data at all; check the network / CA_BUNDLE")
    prices = raw["Close"].reindex(columns=tickers)
    # yfinance logs failed tickers instead of raising, so check explicitly.
    failed = [t for t in tickers if prices[t].isna().all()]
    if failed:
        raise RuntimeError(f"No prices returned for {failed}")
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    return prices


def align_calendar(prices: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Keep only dates on which every series has a price.

    Yahoo's Nifty series skips some NSE sessions (1 January, weekend Diwali
    muhurat sessions, a few odd days). Forward-filling the index on those days
    would give it a zero return that day and push its move into the next day,
    pairing stock and index returns from different periods. Dropping the date
    makes each return span the same two closes for every series.
    """
    complete = prices.notna().all(axis=1)
    dropped = [d.date().isoformat() for d in prices.index[~complete]]
    return prices[complete], dropped


def apply_demergers(prices: pd.DataFrame, demergers: list[dict]) -> pd.DataFrame:
    """Back-adjust prices for demergers that Yahoo leaves unadjusted.

    Every price before the ex-date is multiplied by
    1 - spun_off_value / cum_close, so the ex-date return reflects only the
    market move and not the value shareholders received as new shares.
    """
    adjusted = prices.copy()
    for d in demergers:
        factor = 1 - d["spun_off_value"] / d["cum_close"]
        before = adjusted.index < pd.Timestamp(d["ex_date"])
        adjusted.loc[before, d["ticker"]] *= factor
    return adjusted


def validate_prices(prices: pd.DataFrame, max_abs_move: float,
                    allowed: list[str] | None = None) -> None:
    """Raise ValueError if the price table is unusable or has unexplained jumps.

    A daily move above `max_abs_move` usually means an unadjusted corporate
    action (a demerger, for example). After checking that a move is a real event,
    add "TICKER:YYYY-MM-DD" to `allowed`.
    """
    if prices.empty:
        raise ValueError("price table is empty")
    if not prices.index.is_monotonic_increasing or prices.index.has_duplicates:
        raise ValueError("price index must be sorted with no duplicate dates")
    if prices.isna().any().any():
        raise ValueError("price table has gaps; run align_calendar first")
    if (prices <= 0).any().any():
        raise ValueError("non-positive prices found")

    moves = prices.pct_change(fill_method=None).iloc[1:]
    allowed = set(allowed or [])
    flagged = [f"{t}:{d.date().isoformat()} ({moves.at[d, t]:+.1%})"
               for t in moves.columns
               for d in moves.index[moves[t].abs() > max_abs_move]
               if f"{t}:{d.date().isoformat()}" not in allowed]
    if flagged:
        raise ValueError("unexplained daily moves above "
                         f"{max_abs_move:.0%}: {flagged}. Check for corporate actions, "
                         "then whitelist in config data.allowed_large_moves")


def load_prices(cfg: dict, refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    """Return (aligned prices, metadata). Uses the parquet cache unless `refresh`."""
    out_dir = project_path(cfg["data"]["latest_dir"])
    cache, meta_path = out_dir / "prices.parquet", out_dir / "prices_meta.json"
    if cache.exists() and meta_path.exists() and not refresh:
        return pd.read_parquet(cache), json.loads(meta_path.read_text(encoding="utf-8"))

    tickers = list(cfg["universe"]["stocks"]) + [cfg["universe"]["benchmark"]]
    end = cfg["data"]["end"]
    raw = fetch_prices(tickers, str(cfg["data"]["start"]), str(end) if end else None)
    prices, dropped = align_calendar(raw)
    demergers = cfg["data"].get("demergers") or []
    prices = apply_demergers(prices, demergers)
    validate_prices(prices, cfg["data"]["max_abs_daily_move"],
                    cfg["data"]["allowed_large_moves"])

    meta = {
        "source": "Yahoo Finance via yfinance (auto_adjust=True)",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "first_date": prices.index[0].date().isoformat(),
        "last_date": prices.index[-1].date().isoformat(),
        "observations": len(prices),
        "dropped_incomplete_dates": dropped,
        "demerger_adjustments": [
            {"ticker": d["ticker"], "ex_date": str(d["ex_date"]),
             "factor": round(1 - d["spun_off_value"] / d["cum_close"], 6)}
            for d in demergers],
    }
    # Only write once everything has passed validation (fail closed).
    out_dir.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(cache)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return prices, meta
