"""Phase 2: building the portfolio over the years with a monthly SIP.

Each month a contribution is invested, split between the risky portfolio P and
a debt sleeve at the target equity share. The target glides down linearly as
the goal approaches, the portfolio is rebalanced to target once a year, and the
SIP grows with income each year. Pre-tax and pre-cost.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def glide_path(start: float, end: float, months: int) -> np.ndarray:
    """Target equity share for each month; constant if `end` is not below `start`."""
    if end >= start:
        return np.full(months, start)
    return np.linspace(start, end, months)


def contributions(monthly_amount: float, step_up: float, months: int) -> np.ndarray:
    """Monthly SIP amounts; the amount rises by `step_up` at the start of each new year."""
    return monthly_amount * (1 + step_up) ** (np.arange(months) // 12)


def simulate_sip(risky_returns: np.ndarray, equity_target: np.ndarray, debt_return: float,
                 amounts: np.ndarray, rebalance_every: int = 12) -> np.ndarray:
    """Corpus paths, shape (n_sims, months + 1), for monthly risky returns of shape (n_sims, months).

    Contributions are invested at the start of each month and earn that month's
    return. Equity and debt then drift apart until the next rebalance.
    """
    n_sims, months = risky_returns.shape
    equity = np.zeros(n_sims)
    debt = np.zeros(n_sims)
    corpus = np.zeros((n_sims, months + 1))
    for t in range(months):
        equity += amounts[t] * equity_target[t]
        debt += amounts[t] * (1 - equity_target[t])
        equity *= 1 + risky_returns[:, t]
        debt *= 1 + debt_return
        if (t + 1) % rebalance_every == 0 and t + 1 < months:
            total = equity + debt
            nxt = equity_target[t + 1]
            equity, debt = total * nxt, total * (1 - nxt)
        corpus[:, t + 1] = equity + debt
    return corpus


def monthly_bootstrap(monthly_history: np.ndarray, n_sims: int, months: int, block: int,
                      rng: np.random.Generator) -> np.ndarray:
    """Circular block bootstrap of historical monthly portfolio returns, shape (n_sims, months)."""
    t = len(monthly_history)
    n_blocks = -(-months // block)
    starts = rng.integers(0, t, size=(n_sims, n_blocks))
    idx = ((starts[:, :, None] + np.arange(block)) % t).reshape(n_sims, -1)[:, :months]
    return monthly_history[idx]


def summarize_sip(corpus: np.ndarray, amounts: np.ndarray, goals: list[float], inflation: float,
                  years: int) -> dict:
    terminal = corpus[:, -1]
    deflator = (1 + inflation) ** years
    return {
        "total_invested": float(amounts.sum()),
        "terminal_percentiles": {f"p{p}": float(np.percentile(terminal, p)) for p in (5, 25, 50, 75, 95)},
        "terminal_percentiles_real": {f"p{p}": float(np.percentile(terminal, p) / deflator)
                                      for p in (5, 50, 95)},
        "prob_reach_goal": {f"{g:.0f}": float((terminal >= g).mean()) for g in goals},
        "prob_below_invested": float((terminal < amounts.sum()).mean()),
    }


def sip_fan(corpus: np.ndarray, amounts: np.ndarray, pcts=(5, 25, 50, 75, 95)) -> pd.DataFrame:
    df = pd.DataFrame({f"p{p}": np.percentile(corpus, p, axis=0) for p in pcts})
    df["invested"] = np.concatenate([[0.0], np.cumsum(amounts)])
    return df
