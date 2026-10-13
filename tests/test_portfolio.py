"""Portfolio maths checked against BKM closed forms for two assets."""
import numpy as np
import pandas as pd
import pytest

from src import portfolio as pf

# Two assets: sd 20% and 30%, correlation 0.2 -> covariance 0.012.
MU = pd.Series({"D": 0.10, "E": 0.15})
COV = pd.DataFrame([[0.04, 0.012], [0.012, 0.09]], index=["D", "E"], columns=["D", "E"])


def test_min_variance_matches_two_asset_formula():
    # w_D = (s_E^2 - cov) / (s_D^2 + s_E^2 - 2 cov) = 0.078 / 0.106
    w = pf.min_variance_weights(COV)
    assert w[0] == pytest.approx(0.078 / 0.106, abs=1e-6)


def test_tangency_matches_two_asset_formula():
    # BKM Ch 7 with excess returns R_D = 5%, R_E = 10% (rf = 5%):
    # w_D = (R_D s_E^2 - R_E cov) / (R_D s_E^2 + R_E s_D^2 - (R_D + R_E) cov) = 0.0033 / 0.0067
    w = pf.max_sharpe_weights(MU, COV, rf=0.05)
    assert w[0] == pytest.approx(0.0033 / 0.0067, abs=1e-5)


def test_bounds_bind_when_one_asset_dominates():
    # Asset C has by far the best Sharpe ratio, so unconstrained it would take most of
    # the portfolio; with a 50% cap it sits exactly at the cap.
    mu = pd.Series({"A": 0.08, "B": 0.09, "C": 0.30})
    cov = pd.DataFrame(np.diag([0.04, 0.05, 0.03]), index=mu.index, columns=mu.index)
    w = pf.max_sharpe_weights(mu, cov, rf=0.05, bounds=(0.1, 0.5))
    assert w[2] == pytest.approx(0.5, abs=1e-6)
    assert w.min() >= 0.1 - 1e-9 and w.sum() == pytest.approx(1.0)


def test_infeasible_bounds_fail_loudly():
    # Two assets each forced to hold at least 60% cannot sum to 100%.
    with pytest.raises(RuntimeError):
        pf.max_sharpe_weights(MU, COV, rf=0.05, bounds=(0.6, 1.0))


def test_frontier_starts_at_min_variance_and_rises():
    f = pf.efficient_frontier(MU, COV, points=10)
    w_min = pf.min_variance_weights(COV)
    assert f["volatility"].iloc[0] == pytest.approx(pf.portfolio_vol(w_min, COV), abs=1e-6)
    assert f["return"].is_monotonic_increasing and f["volatility"].is_monotonic_increasing


def test_utility_class_example():
    # Class 8-10 deck: E(r) 20%, sd 30%, T-bills 7%, A = 4. U = 0.20 - 0.5 x 4 x 0.09 = 2% < 7% -> T-bills.
    assert pf.utility(0.20, 0.30, 4) == pytest.approx(0.02)


def test_complete_portfolio():
    c = pf.complete_portfolio(0.15, 0.20, 0.05, risk_aversion=4)
    assert c["y_star"] == pytest.approx(0.10 / (4 * 0.04))           # 0.625
    assert c["expected_return"] == pytest.approx(0.05 + 0.625 * 0.10)
    assert c["volatility"] == pytest.approx(0.625 * 0.20)
    assert c["certainty_equivalent"] == pytest.approx(0.1125 - 0.5 * 4 * 0.125 ** 2)


def test_no_borrowing_caps_y_at_one():
    c = pf.complete_portfolio(0.15, 0.20, 0.05, risk_aversion=1)
    assert c["y_star"] == pytest.approx(2.5) and c["y"] == 1.0
    assert pf.complete_portfolio(0.15, 0.20, 0.05, 1, allow_borrowing=True)["y"] == pytest.approx(2.5)


def test_backtest_of_the_market_itself():
    dates = pd.date_range("2026-01-05", periods=6, freq="B")
    m = pd.Series([0.01, -0.02, 0.015, 0.0, 0.005, -0.01], index=dates)
    out = pf.backtest(pd.DataFrame({"A": m, "B": m}), {"A": 0.5, "B": 0.5}, m, rf=0.0, periods=252)
    assert out["portfolio"]["beta"] == pytest.approx(1.0)
    assert out["portfolio"]["jensen_alpha"] == pytest.approx(0.0, abs=1e-12)
