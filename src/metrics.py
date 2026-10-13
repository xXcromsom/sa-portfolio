"""Phase 1 analysis: per-security risk/return, tail risk, correlation and CAPM."""
from __future__ import annotations

import pandas as pd

from src import quant_utils as qu


def add_dividend_yield(returns: pd.Series, dividend_yield: float, periods: int = 252) -> pd.Series:
    """Turn price-index returns into estimated total returns by adding the yield per period."""
    return returns + qu.periodic_rf(dividend_yield, periods)


def metrics_table(returns: pd.DataFrame, market_col: str, rf: float, erp: float,
                  periods: int = 252) -> pd.DataFrame:
    """One row per security (benchmark included) with every Phase 1 metric."""
    market = returns[market_col]
    table = pd.DataFrame({
        "cagr": qu.annualized_return(returns, periods),
        "mean_return": qu.annualized_mean(returns, periods),
        "volatility": qu.annualized_volatility(returns, periods),
        "sharpe": qu.sharpe_ratio(returns, rf, periods),
        "sortino": qu.sortino_ratio(returns, rf, periods),
        "max_drawdown": qu.max_drawdown(returns),
        "skewness": qu.skewness(returns),
        "excess_kurtosis": qu.excess_kurtosis(returns),
        "var_95_daily": qu.historical_var(returns, 0.95),
        "es_95_daily": qu.expected_shortfall(returns, 0.95),
        "beta": qu.beta(returns, market),
        "treynor": qu.treynor_ratio(returns, market, rf, periods),
        "jensen_alpha": qu.jensen_alpha(returns, market, rf, periods),
    })
    # Forward-looking discount rate for valuation, from today's rf and ERP.
    table["capm_required_return"] = qu.capm_required_return(table["beta"], rf, erp)
    return table


def correlation_check(returns: pd.DataFrame, stocks: list[str], years: int,
                      threshold: float = 0.5, periods: int = 252) -> dict:
    """Selection criterion: pairwise correlation of daily returns over the last `years`."""
    recent = returns[stocks].iloc[-years * periods:]
    corr = recent.corr()
    # Plain floats (not numpy scalars) so the result serialises to JSON.
    pairs = {f"{a} / {b}": round(float(corr.at[a, b]), 3)
             for i, a in enumerate(stocks) for b in stocks[i + 1:]}
    return {
        "window_start": recent.index[0].date().isoformat(),
        "window_end": recent.index[-1].date().isoformat(),
        "pairs": pairs,
        "max_pair": max(pairs, key=pairs.get),
        "max_correlation": max(pairs.values()),
        "threshold": threshold,
        "passes": max(pairs.values()) <= threshold,
    }
