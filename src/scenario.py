"""Monte Carlo and SIP scenario draws, shared by the pipeline and the dashboard.

Both build their draws here from the same inputs and seed, in the same order, so the
dashboard reproduces the report's numbers exactly at the report's risk-aversion levels
and re-prices any other A (or amount) with identical arithmetic.

Inputs come from two files the pipeline writes next to its results:
- returns_daily.parquet: daily returns of the stocks and the benchmark (estimated total return)
- returns_monthly.parquet: month-end returns of the same series, benchmark incl. dividends
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd

from src import monte_carlo as mc
from src import quant_utils as qu
from src import sip

ONE_YEAR_MODES = ("Parametric", "Bootstrap", "Parametric, current volatility (EWMA)")
SIP_MODES = ("Parametric", "Bootstrap")


def one_year_draws(stock_returns: pd.DataFrame, target_daily: np.ndarray, settings: dict,
                   rng: np.random.Generator) -> Iterator[tuple[str, np.ndarray]]:
    """Daily asset-return paths (n_sims, horizon, n_assets) for each mode, one mode at a time.

    Yielding keeps only one ~60 MB array alive; the RNG is consumed in the same order either way.
    """
    n, horizon = settings["n_sims"], settings["horizon_days"]
    ewma = mc.ewma_cov(stock_returns, settings["ewma_lambda"]).to_numpy()
    yield "Parametric", mc.simulate_parametric(target_daily, stock_returns.cov().to_numpy(), n, horizon, rng)
    yield "Bootstrap", mc.simulate_bootstrap(mc.shift_means(stock_returns.to_numpy(), target_daily), n, horizon,
                                             settings["bootstrap_block_days"], rng)
    yield ONE_YEAR_MODES[2], mc.simulate_parametric(target_daily, ewma, n, horizon, rng)


def sleeve_draws(monthly_returns: pd.DataFrame, cov_monthly: np.ndarray, mu_annual: np.ndarray,
                 w_sleeve: np.ndarray, n_sims: int, months: int, block: int,
                 rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Monthly returns (n_sims, months) of the SIP equity sleeve (index core + the stocks)."""
    mu_m = mu_annual / 12
    boot_hist = mc.shift_means(monthly_returns.to_numpy(), mu_m) @ w_sleeve
    return {"Parametric": mc.simulate_parametric(mu_m, cov_monthly, n_sims, months, rng) @ w_sleeve,
            "Bootstrap": sip.monthly_bootstrap(boot_hist, n_sims, months, block, rng)}


def sleeve_weights(w_p: np.ndarray, core_share: float) -> np.ndarray:
    """Stocks at (1 - core) x P's weights, then the index core (benchmark last)."""
    return np.append((1 - core_share) * w_p, core_share)


def dashboard_draws(daily: pd.DataFrame, monthly: pd.DataFrame, stocks: list[str], bench: str,
                    capm: np.ndarray, w_p: np.ndarray, rf: float, erp: float,
                    mc_settings: dict, sip_settings: dict, periods: int) -> dict:
    """The pipeline's forward-looking draws, reduced to P-level (1 year) and sleeve-level (SIP) returns.

    Same seed and order as pipeline.run_all, so the result for the report's A values matches mc.json
    and sip.json exactly. The sensitivity run that follows in the pipeline is not needed here.
    """
    if mc_settings["rebalance"] != "constant_mix":
        raise ValueError("the dashboard re-prices A from P-level returns, which needs constant-mix rebalancing")
    rng = np.random.default_rng(mc_settings["seed"])
    one_year = {mode: x @ w_p for mode, x in one_year_draws(daily[stocks], capm / periods, mc_settings, rng)}
    four = stocks + [bench]
    months = sip_settings["years"] * 12
    cov_m = daily[four].cov().to_numpy() * periods / 12
    sleeve = sleeve_draws(monthly[four], cov_m, np.append(capm, rf + erp),
                          sleeve_weights(w_p, sip_settings["core_index_share"]),
                          mc_settings["n_sims"], months, sip_settings["bootstrap_block_months"], rng)
    return {"one_year": one_year, "sip": sleeve, "rf_daily": qu.periodic_rf(rf, periods),
            "rf_monthly": qu.periodic_rf(rf, 12)}


def one_year_outcome(risky_daily: np.ndarray, y: float, rf_daily: float,
                     amount: float) -> tuple[dict, pd.DataFrame, np.ndarray]:
    """Summary (VaR, CVaR, P(loss), percentiles), fan and terminal values for `amount` with y in P."""
    wealth = mc.wealth_from_risky(risky_daily, y, rf_daily)
    return mc.summarize(wealth, amount), mc.fan(wealth, amount), wealth[:, -1] * amount


def sip_outcome(risky_monthly: np.ndarray, y: float, rf_monthly: float, monthly_amount: float,
                sip_settings: dict) -> tuple[dict, pd.DataFrame]:
    """15-year SIP summary and fan for a monthly amount, starting at equity share y and gliding down."""
    months = sip_settings["years"] * 12
    amounts = sip.contributions(monthly_amount, sip_settings["annual_step_up"], months)
    glide = sip.glide_path(y, sip_settings["glide_path_end_equity"], months)
    corpus = sip.simulate_sip(risky_monthly, glide, rf_monthly, amounts, sip_settings["rebalance_every_months"])
    return (sip.summarize_sip(corpus, amounts, sip_settings["goals"], sip_settings["inflation"], sip_settings["years"]),
            sip.sip_fan(corpus, amounts))
