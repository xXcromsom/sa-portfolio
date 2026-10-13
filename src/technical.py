"""Phase 3: is technical analysis possible? A weak-form efficiency test (BKM Ch 11-12).

Two classic rules are traded on daily closes and compared with buy-and-hold:
- Trend: hold the stock while its 50-day average is above its 200-day average
  (the "golden cross"), otherwise hold T-bills.
- Mean reversion: buy when the 14-day RSI drops below 30, sell when it rises
  above 50; T-bills in between.

Signals use the previous day's close, so there is no look-ahead. Each switch
pays a one-way cost (default 0.125%, i.e. 0.25% round trip). That is an
assumption covering brokerage, STT, exchange charges and slippage for a retail
investor. If the rules can't beat buy-and-hold after costs, past prices alone
carry little exploitable information, which is what weak-form efficiency says.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import quant_utils as qu


def rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's relative strength index (0-100)."""
    delta = prices.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def trend_signal(prices: pd.Series, fast: int = 50, slow: int = 200) -> pd.Series:
    """1 when the fast moving average is above the slow one, else 0 (NaN until slow is defined)."""
    f, s = prices.rolling(fast).mean(), prices.rolling(slow).mean()
    return (f > s).astype(float).where(s.notna())


def rsi_signal(prices: pd.Series, buy_below: float = 30, sell_above: float = 50, window: int = 14) -> pd.Series:
    """Hold from an RSI dip below `buy_below` until it recovers above `sell_above`."""
    r = rsi(prices, window)
    state, out = 0.0, []
    for v in r:
        if np.isnan(v):
            out.append(np.nan)
            continue
        if state == 0 and v < buy_below:
            state = 1.0
        elif state == 1 and v > sell_above:
            state = 0.0
        out.append(state)
    return pd.Series(out, index=prices.index)


def strategy_returns(prices: pd.Series, signal: pd.Series, rf_annual: float, cost_one_way: float = 0.00125,
                     periods: int = 252) -> pd.Series:
    """Daily returns of following `signal` (yesterday's value) with T-bills when out and costs on switches."""
    r = prices.pct_change(fill_method=None)
    pos = signal.shift(1)
    rf = qu.periodic_rf(rf_annual, periods)
    switches = pos.diff().abs().fillna(0)
    out = pos * r + (1 - pos) * rf - switches * cost_one_way
    return out[pos.notna()].dropna()


def evaluate(prices: pd.DataFrame, rf_annual: float, cost_one_way: float = 0.00125, periods: int = 252) -> pd.DataFrame:
    """Buy-and-hold vs the trend and RSI rules for every column, over the same dates."""
    rows = []
    for t in prices.columns:
        p = prices[t].dropna()
        rules = {"Trend (50/200 DMA)": trend_signal(p), "RSI mean reversion": rsi_signal(p)}
        strat = {name: strategy_returns(p, sig, rf_annual, cost_one_way, periods) for name, sig in rules.items()}
        start = max(s.index[0] for s in strat.values())
        bh = p.pct_change(fill_method=None).loc[start:].dropna()
        for name, r in [("Buy and hold", bh)] + [(n, s.loc[start:]) for n, s in strat.items()]:
            sig = rules.get(name)
            rows.append({
                "ticker": t, "rule": name,
                "cagr": qu.annualized_return(r, periods), "volatility": qu.annualized_volatility(r, periods),
                "sharpe": qu.sharpe_ratio(r, rf_annual, periods), "max_drawdown": qu.max_drawdown(r),
                "time_invested": 1.0 if sig is None else float(sig.loc[start:].mean()),
                "trades_per_year": 0.0 if sig is None else
                float(sig.loc[start:].diff().abs().sum() / (len(r) / periods)),
            })
    return pd.DataFrame(rows)
