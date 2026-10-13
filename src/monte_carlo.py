"""Phase 2: Monte Carlo simulation of portfolio outcomes, in two modes.

Parametric: multivariate normal daily returns. Correlation is preserved by the
Cholesky factor of the covariance matrix, never by drawing assets independently.
Bootstrap: blocks of actual historical days, which keeps fat tails and some
volatility clustering.

Expected returns are an input, not an estimate from the paths. By default they
are CAPM required returns, and bootstrap history is re-centred on them so the
last decade's winners don't automatically win again.

Known limitation: both treat returns as stable over the horizon. Neither models
regime shifts, and the parametric mode also ignores fat tails, which is why the
two are shown side by side.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ewma_cov(returns: pd.DataFrame, lam: float = 0.94, seed_days: int = 60) -> pd.DataFrame:
    """RiskMetrics exponentially weighted covariance at the last date (daily units).

    Recent days get more weight, so the estimate reflects the current volatility
    regime. Seeded with the sample covariance of the first `seed_days`.
    Zero-mean form, as in RiskMetrics.
    """
    x = returns.to_numpy()
    s = np.cov(x[:seed_days].T)
    for r in x[seed_days:]:
        s = lam * s + (1 - lam) * np.outer(r, r)
    return pd.DataFrame(s, index=returns.columns, columns=returns.columns)


def simulate_parametric(mu: np.ndarray, cov: np.ndarray, n_sims: int, horizon: int,
                        rng: np.random.Generator) -> np.ndarray:
    """Correlated normal returns, shape (n_sims, horizon, n_assets)."""
    chol = np.linalg.cholesky(cov)
    z = rng.standard_normal((n_sims, horizon, len(mu)))
    return z @ chol.T + mu


def simulate_bootstrap(history: np.ndarray, n_sims: int, horizon: int, block: int,
                       rng: np.random.Generator) -> np.ndarray:
    """Circular block bootstrap of historical rows (each row = one day, all assets).

    Whole days are resampled together, so cross-asset correlation is kept as it
    actually occurred.
    """
    t = len(history)
    n_blocks = -(-horizon // block)  # ceiling division
    starts = rng.integers(0, t, size=(n_sims, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)) % t        # wrap around the end
    idx = idx.reshape(n_sims, -1)[:, :horizon]
    return history[idx]


def shift_means(history: np.ndarray, target_mean: np.ndarray) -> np.ndarray:
    """Re-centre historical returns on target means, keeping their shape (volatility, tails, co-movement)."""
    return history - history.mean(axis=0) + target_mean


def wealth_paths(asset_returns: np.ndarray, weights: np.ndarray, y: float, rf_period: float,
                 rebalance: str = "constant_mix") -> np.ndarray:
    """Growth of 1 invested: y in the risky mix, 1 - y in T-bills. Shape (n_sims, horizon + 1)."""
    n_sims, horizon, _ = asset_returns.shape
    if rebalance == "constant_mix":
        port = y * (asset_returns @ weights) + (1 - y) * rf_period
        growth = np.cumprod(1 + port, axis=1)
    elif rebalance == "buy_and_hold":
        risky = (y * weights) * np.cumprod(1 + asset_returns, axis=1)   # each asset drifts
        safe = (1 - y) * (1 + rf_period) ** np.arange(1, horizon + 1)
        growth = risky.sum(axis=2) + safe
    else:
        raise ValueError(f"unknown rebalance rule {rebalance!r}")
    return np.hstack([np.ones((n_sims, 1)), growth])


def summarize(wealth: np.ndarray, initial_value: float) -> dict:
    """Terminal-value distribution, VaR/CVaR, probability of loss and drawdown distribution."""
    terminal = wealth[:, -1] * initial_value
    ret = wealth[:, -1] - 1
    out = {
        "mean_terminal": float(terminal.mean()),
        "terminal_percentiles": {f"p{p}": float(np.percentile(terminal, p)) for p in (5, 25, 50, 75, 95)},
        "prob_loss": float((ret < 0).mean()),
    }
    for level in (0.95, 0.99):
        cutoff = np.percentile(ret, 100 * (1 - level))
        out[f"var_{int(level * 100)}"] = float(-cutoff * initial_value)
        out[f"cvar_{int(level * 100)}"] = float(-ret[ret <= cutoff].mean() * initial_value)
    drawdowns = (wealth / np.maximum.accumulate(wealth, axis=1) - 1).min(axis=1)
    out["max_drawdown_percentiles"] = {f"p{p}": float(np.percentile(drawdowns, p)) for p in (5, 50, 95)}
    return out


def fan(wealth: np.ndarray, initial_value: float, pcts=(5, 25, 50, 75, 95)) -> pd.DataFrame:
    """Percentile path of portfolio value at each step (for fan charts)."""
    return pd.DataFrame({f"p{p}": np.percentile(wealth, p, axis=0) * initial_value for p in pcts})
