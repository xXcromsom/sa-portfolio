import math

import numpy as np
import pandas as pd
import pytest

from src import monte_carlo as mc
from src import portfolio as pf
from src import scenario


def test_wealth_from_risky_matches_wealth_paths_exactly():
    rng = np.random.default_rng(0)
    x = rng.normal(0.0004, 0.01, size=(200, 50, 3))
    w = np.array([0.3, 0.2, 0.5])
    for y in (0.0, 0.44, 1.0, 1.6):
        assert np.array_equal(mc.wealth_paths(x, w, y, 0.0002), mc.wealth_from_risky(x @ w, y, 0.0002))


def test_complete_portfolio_low_and_negative_a():
    er, vol, rf = 0.123, 0.197, 0.055
    threshold = (er - rf) / vol ** 2  # below this A, y* exceeds 100%
    assert pf.complete_portfolio(er, vol, rf, threshold * 0.99)["y"] == 1.0
    for a in (0.0, -2.0):
        c = pf.complete_portfolio(er, vol, rf, a)
        assert math.isinf(c["y_star"]) and c["y"] == 1.0
        assert pf.complete_portfolio(er, vol, rf, a, allow_borrowing=True, max_leverage=2.0)["y"] == 2.0
    with pytest.raises(ValueError, match="max_leverage"):
        pf.complete_portfolio(er, vol, rf, 0.0, allow_borrowing=True)
    assert pf.complete_portfolio(er, vol, rf, 1.0, allow_borrowing=True, max_leverage=2.0)["y"] == pytest.approx(
        min((er - rf) / vol ** 2, 2.0))


def _inputs(n_days=600, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n_days)
    daily = pd.DataFrame(rng.normal(0.0005, 0.012, size=(n_days, 4)), index=idx, columns=["A", "B", "C", "IDX"])
    monthly = (1 + daily).resample("ME").prod() - 1
    mc_settings = {"n_sims": 300, "horizon_days": 40, "seed": 7, "ewma_lambda": 0.94,
                   "bootstrap_block_days": 5, "rebalance": "constant_mix", "initial_value": 100000}
    sip_settings = {"years": 2, "core_index_share": 0.5, "bootstrap_block_months": 3, "annual_step_up": 0.1,
                    "glide_path_end_equity": 0.4, "rebalance_every_months": 12, "goals": [300000],
                    "inflation": 0.04, "monthly_amount": 10000}
    return daily, monthly, mc_settings, sip_settings


def test_dashboard_draws_reproduce_pipeline_order():
    daily, monthly, mcs, sps = _inputs()
    stocks, w_p, capm = ["A", "B", "C"], np.array([0.3, 0.2, 0.5]), np.array([0.10, 0.11, 0.14])
    d = scenario.dashboard_draws(daily, monthly, stocks, "IDX", capm, w_p, 0.05, 0.07, mcs, sps, 252)
    # What the pipeline does: same seed, one-year draws first, then the SIP sleeve.
    rng = np.random.default_rng(mcs["seed"])
    expected = {m: x @ w_p for m, x in scenario.one_year_draws(daily[stocks], capm / 252, mcs, rng)}
    cov_m = daily.cov().to_numpy() * 252 / 12
    sleeve = scenario.sleeve_draws(monthly, cov_m, np.append(capm, 0.12), scenario.sleeve_weights(w_p, 0.5),
                                   mcs["n_sims"], 24, 3, rng)
    for m in scenario.ONE_YEAR_MODES:
        assert np.array_equal(d["one_year"][m], expected[m])
    for m in scenario.SIP_MODES:
        assert np.array_equal(d["sip"][m], sleeve[m])


def test_outcomes_scale_with_amount_and_y():
    daily, monthly, mcs, sps = _inputs()
    d = scenario.dashboard_draws(daily, monthly, ["A", "B", "C"], "IDX", np.array([0.1, 0.11, 0.14]),
                                 np.array([0.3, 0.2, 0.5]), 0.05, 0.07, mcs, sps, 252)
    r = d["one_year"]["Parametric"]
    small, _, _ = scenario.one_year_outcome(r, 0.5, d["rf_daily"], 100000)
    big, _, terminal = scenario.one_year_outcome(r, 0.5, d["rf_daily"], 200000)
    assert big["var_95"] == pytest.approx(2 * small["var_95"])
    assert terminal.shape == (300,) and np.median(terminal) == pytest.approx(big["terminal_percentiles"]["p50"])
    safe, _, _ = scenario.one_year_outcome(r, 0.0, d["rf_daily"], 100000)
    assert safe["prob_loss"] == 0.0
    s1, fan = scenario.sip_outcome(d["sip"]["Parametric"], 0.8, d["rf_monthly"], 10000, sps)
    s2, _ = scenario.sip_outcome(d["sip"]["Parametric"], 0.8, d["rf_monthly"], 20000, sps)
    assert s2["terminal_percentiles"]["p50"] == pytest.approx(2 * s1["terminal_percentiles"]["p50"])
    assert len(fan) == 25
