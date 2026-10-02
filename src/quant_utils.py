"""Return and risk metrics shared across the project.

Every function takes daily simple returns as a pandas Series (one asset) or a
DataFrame (one column per asset) and works column-wise, so the same call gives
either a single number or a per-asset Series.

Conventions, stated once and used everywhere:
- Returns are simple (not log) returns computed from dividend- and split-adjusted
  prices.
- `periods` is the number of return observations per year (252 trading days).
- `rf_annual` is an annual rate. It is converted to a per-period rate by
  compounding, so (1 + rf_period) ** periods == 1 + rf_annual.
- Ratios (Sharpe, Sortino, Treynor, Jensen's alpha) use the *arithmetic* mean of
  excess returns multiplied by `periods`. That is the convention behind the
  Sharpe ratio and the CAPM regression (BKM Ch 24). `annualized_return` is the
  *geometric* rate an investor actually earned; it is for reporting, not ratios.

Refactored from the earlier BRK-A script. Its drawdown logic is kept, with one
fix: the starting wealth of 1.0 now counts as a peak, so a loss on day one shows
up as a drawdown.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

Returns = pd.Series | pd.DataFrame


def to_returns(prices: Returns) -> Returns:
    """Simple period returns from a price Series/DataFrame (first row dropped)."""
    return prices.pct_change(fill_method=None).iloc[1:]


def periodic_rf(rf_annual: float, periods: int = 252) -> float:
    """Convert an annual risk-free rate to the equivalent per-period rate."""
    return (1 + rf_annual) ** (1 / periods) - 1


def annualized_return(returns: Returns, periods: int = 252) -> float | pd.Series:
    """Geometric (compound) annual growth rate over the whole sample."""
    n = returns.shape[0]
    return (1 + returns).prod() ** (periods / n) - 1


def annualized_mean(returns: Returns, periods: int = 252) -> float | pd.Series:
    """Arithmetic mean return scaled to a year. Used for CAPM/SML and as optimiser input."""
    return returns.mean() * periods


def annualized_volatility(returns: Returns, periods: int = 252) -> float | pd.Series:
    """Sample standard deviation (ddof=1) scaled by sqrt(periods)."""
    return returns.std(ddof=1) * np.sqrt(periods)


def sharpe_ratio(returns: Returns, rf_annual: float = 0.0, periods: int = 252) -> float | pd.Series:
    """Annualised mean excess return divided by annualised volatility.

    The volatility of excess returns equals the volatility of raw returns because
    the per-period risk-free rate is a constant.
    """
    excess = returns - periodic_rf(rf_annual, periods)
    return excess.mean() * periods / annualized_volatility(returns, periods)


def sortino_ratio(returns: Returns, rf_annual: float = 0.0, periods: int = 252) -> float | pd.Series:
    """Sharpe-style ratio that only penalises returns below the risk-free rate.

    Downside deviation averages squared shortfalls over *all* periods, not only
    the losing ones (Sortino & Price, 1994). Dividing by the count of losing days
    instead would overstate downside risk.
    """
    excess = returns - periodic_rf(rf_annual, periods)
    downside_dev = np.sqrt((excess.clip(upper=0) ** 2).mean()) * np.sqrt(periods)
    return excess.mean() * periods / downside_dev


def drawdown(returns: Returns) -> Returns:
    """Percentage fall of wealth from its running peak at each date (0 or negative)."""
    wealth = (1 + returns).cumprod()
    # Starting wealth is 1.0, which is itself a peak.
    peak = wealth.cummax().clip(lower=1.0)
    return wealth / peak - 1


def max_drawdown(returns: Returns) -> float | pd.Series:
    """Worst peak-to-trough fall, as a negative number (e.g. -0.38 = -38%)."""
    return drawdown(returns).min()


def _check_aligned(returns: Returns, market: pd.Series) -> None:
    # Misaligned dates silently pair the wrong days; fail loudly instead.
    if not returns.index.equals(market.index):
        raise ValueError("returns and market must share the same date index; align them first")


def beta(returns: Returns, market: pd.Series) -> float | pd.Series:
    """CAPM beta: Cov(r_i, r_m) / Var(r_m).

    Raw returns give the same beta as excess returns because subtracting a
    constant risk-free rate leaves covariances unchanged.
    """
    _check_aligned(returns, market)
    var_m = market.var(ddof=1)
    if isinstance(returns, pd.DataFrame):
        return returns.apply(lambda col: col.cov(market) / var_m)
    return returns.cov(market) / var_m


def treynor_ratio(returns: Returns, market: pd.Series, rf_annual: float = 0.0,
                  periods: int = 252) -> float | pd.Series:
    """Annualised mean excess return per unit of beta (systematic risk)."""
    excess = returns - periodic_rf(rf_annual, periods)
    return excess.mean() * periods / beta(returns, market)


def jensen_alpha(returns: Returns, market: pd.Series, rf_annual: float = 0.0,
                 periods: int = 252) -> float | pd.Series:
    """Annualised return in excess of what CAPM predicts for the asset's beta.

    alpha = mean(r_i - rf) - beta * mean(r_m - rf), scaled by `periods`.
    Equal to the intercept of the OLS regression of excess asset returns on
    excess market returns.
    """
    rf = periodic_rf(rf_annual, periods)
    b = beta(returns, market)
    return ((returns - rf).mean() - b * (market - rf).mean()) * periods


def capm_required_return(beta_value: float | pd.Series, rf_annual: float,
                         equity_risk_premium: float) -> float | pd.Series:
    """Forward-looking CAPM required return: rf + beta * ERP. Used as the discount rate."""
    return rf_annual + beta_value * equity_risk_premium
