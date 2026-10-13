"""Phase 2: the optimal risky portfolio, capital allocation and utility (BKM Ch 6-7, 24).

Every investor holds the same optimal risky portfolio P (the tangency portfolio)
and differs only in how much goes into P versus T-bills (the separation
property). P comes from mean-variance optimisation on historical inputs, which
are noisy: the optimiser rewards whichever stock happened to have the best past
mean. The 10-60% weight bounds and the out-of-sample test are the guards.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src import quant_utils as qu


def annual_inputs(returns: pd.DataFrame, periods: int = 252) -> tuple[pd.Series, pd.DataFrame]:
    """Arithmetic annual mean returns and annual covariance matrix."""
    return returns.mean() * periods, returns.cov() * periods


def portfolio_return(w: np.ndarray, mu: pd.Series) -> float:
    return float(np.asarray(w) @ mu.to_numpy())


def portfolio_vol(w: np.ndarray, cov: pd.DataFrame) -> float:
    w = np.asarray(w)
    return float(np.sqrt(w @ cov.to_numpy() @ w))


def _solve(objective, n: int, bounds: tuple[float, float], constraints=()) -> np.ndarray:
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}, *constraints]
    res = minimize(objective, np.full(n, 1.0 / n), method="SLSQP",
                   bounds=[bounds] * n, constraints=cons, options={"ftol": 1e-12, "maxiter": 500})
    if not res.success:
        raise RuntimeError(f"optimiser failed: {res.message}")
    return res.x


def min_variance_weights(cov: pd.DataFrame, bounds=(0.0, 1.0)) -> np.ndarray:
    return _solve(lambda w: w @ cov.to_numpy() @ w, len(cov), bounds)


def max_sharpe_weights(mu: pd.Series, cov: pd.DataFrame, rf: float, bounds=(0.0, 1.0)) -> np.ndarray:
    """Tangency portfolio: the risky mix with the steepest capital allocation line."""
    return _solve(lambda w: -(portfolio_return(w, mu) - rf) / portfolio_vol(w, cov), len(mu), bounds)


def efficient_frontier(mu: pd.Series, cov: pd.DataFrame, bounds=(0.0, 1.0), points: int = 40) -> pd.DataFrame:
    """Minimum-variance portfolio for each target return between the min-variance and max-return mixes."""
    n = len(mu)
    w_min = min_variance_weights(cov, bounds)
    w_max = _solve(lambda w: -portfolio_return(w, mu), n, bounds)
    rows = []
    for target in np.linspace(portfolio_return(w_min, mu), portfolio_return(w_max, mu), points):
        w = _solve(lambda w: w @ cov.to_numpy() @ w, n, bounds,
                   [{"type": "eq", "fun": lambda w, t=target: portfolio_return(w, mu) - t}])
        rows.append({"return": portfolio_return(w, mu), "volatility": portfolio_vol(w, cov),
                     **dict(zip(mu.index, w))})
    return pd.DataFrame(rows)


def utility(expected_return: float, volatility: float, risk_aversion: float) -> float:
    """U = E(r) - 0.5 A sigma^2. U is also the certainty-equivalent return (BKM Ch 6)."""
    return expected_return - 0.5 * risk_aversion * volatility ** 2


def complete_portfolio(er_p: float, vol_p: float, rf: float, risk_aversion: float,
                       allow_borrowing: bool = False) -> dict:
    """Optimal split between P and T-bills: y* = (E[r_P] - rf) / (A sigma_P^2)."""
    y_star = (er_p - rf) / (risk_aversion * vol_p ** 2)
    y = y_star if allow_borrowing else min(max(y_star, 0.0), 1.0)
    er_c, vol_c = rf + y * (er_p - rf), y * vol_p
    # Utility = the certainty-equivalent return: the risk-free rate this investor
    # would accept instead of holding the complete portfolio.
    return {"risk_aversion": risk_aversion, "y_star": y_star, "y": y, "expected_return": er_c,
            "volatility": vol_c, "certainty_equivalent": utility(er_c, vol_c, risk_aversion)}


def backtest(returns: pd.DataFrame, weights: dict[str, float], market: pd.Series, rf: float,
             periods: int = 252) -> dict:
    """Realised performance of a constant-mix portfolio (rebalanced to target daily) vs the market."""
    w = pd.Series(weights)
    port = returns[w.index] @ w
    out = {}
    for name, r in (("portfolio", port), ("market", market)):
        out[name] = {
            "cagr": qu.annualized_return(r, periods),
            "volatility": qu.annualized_volatility(r, periods),
            "sharpe": qu.sharpe_ratio(r, rf, periods),
            "max_drawdown": qu.max_drawdown(r),
            "beta": qu.beta(r, market),
            "treynor": qu.treynor_ratio(r, market, rf, periods),
            "jensen_alpha": qu.jensen_alpha(r, market, rf, periods),
        }
    out["start"] = returns.index[0].date().isoformat()
    out["end"] = returns.index[-1].date().isoformat()
    return out
