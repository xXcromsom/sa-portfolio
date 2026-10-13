"""quant_utils checked against values worked out by hand on a 5-day fixture.

periods=1 keeps the arithmetic small enough to verify on paper:
r = [+1%, -2%, +3%, -1%, +2%]
"""
import numpy as np
import pandas as pd
import pytest

from src import quant_utils as qu

DATES = pd.date_range("2026-01-05", periods=5, freq="B")
R = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02], index=DATES)
# Market fixture; the asset below is constructed as 2 * market + 0.1% per day,
# so beta must be exactly 2 and alpha exactly 0.1% per period.
M = pd.Series([0.005, -0.01, 0.02, 0.0, 0.01], index=DATES)
A = 2 * M + 0.001


def test_to_returns():
    prices = pd.Series([100.0, 110.0, 99.0], index=DATES[:3])
    assert qu.to_returns(prices).tolist() == pytest.approx([0.10, -0.10])


def test_periodic_rf_compounds_back_to_annual():
    assert (1 + qu.periodic_rf(0.10, 252)) ** 252 == pytest.approx(1.10)


def test_annualized_return_is_total_return_when_periods_equal_n():
    # 1.01 * 0.98 * 1.03 * 0.99 * 1.02 = 1.0294850412
    assert qu.annualized_return(R, periods=5) == pytest.approx(0.0294850412)


def test_annualized_mean():
    assert qu.annualized_mean(R, periods=252) == pytest.approx(0.006 * 252)


def test_volatility():
    # mean 0.006; squared deviations sum to 0.00172; / (n-1) = 0.00043
    assert qu.annualized_volatility(R, periods=1) == pytest.approx(np.sqrt(0.00043))
    assert qu.annualized_volatility(R, periods=4) == pytest.approx(np.sqrt(0.00043) * 2)


def test_sharpe():
    assert qu.sharpe_ratio(R, 0.0, periods=1) == pytest.approx(0.006 / np.sqrt(0.00043))


def test_sharpe_subtracts_risk_free():
    # With periods=1 the per-period rf equals the annual rf.
    assert qu.sharpe_ratio(R, 0.002, periods=1) == pytest.approx(0.004 / np.sqrt(0.00043))


def test_sortino():
    # Shortfalls -2% and -1%: (0.0004 + 0.0001) / 5 = 0.0001 -> downside dev 1%
    assert qu.sortino_ratio(R, 0.0, periods=1) == pytest.approx(0.6)


def test_max_drawdown():
    # Wealth 1.01, 0.9898 (-2% from 1.01), 1.019494, 1.00929906 (-1%), 1.0294850412
    assert qu.max_drawdown(R) == pytest.approx(-0.02)


def test_drawdown_counts_starting_wealth_as_peak():
    first_day_loss = pd.Series([-0.05, 0.01], index=DATES[:2])
    assert qu.max_drawdown(first_day_loss) == pytest.approx(-0.05)


def test_beta_alpha_treynor_on_constructed_asset():
    assert qu.beta(A, M) == pytest.approx(2.0)
    # mean(A) = 2 * 0.005 + 0.001 = 0.011
    assert qu.jensen_alpha(A, M, 0.0, periods=1) == pytest.approx(0.001)
    assert qu.treynor_ratio(A, M, 0.0, periods=1) == pytest.approx(0.011 / 2)


def test_alpha_is_unchanged_by_rf_when_beta_is_one():
    # alpha = mean(A - rf) - 1 * mean(M - rf): rf cancels exactly.
    one_beta = M + 0.001
    assert qu.jensen_alpha(one_beta, M, 0.05, periods=1) == pytest.approx(0.001)


def test_dataframe_input_is_column_wise():
    df = pd.DataFrame({"asset": A, "market": M})
    betas = qu.beta(df, M)
    assert betas["asset"] == pytest.approx(2.0)
    assert betas["market"] == pytest.approx(1.0)
    assert qu.max_drawdown(df).shape == (2,)


def test_misaligned_dates_raise():
    shifted = M.copy()
    shifted.index = shifted.index + pd.Timedelta(days=1)
    with pytest.raises(ValueError):
        qu.beta(A, shifted)


def test_tail_measures_on_ten_point_fixture():
    # Ten sorted returns; the 10% quantile sits between the two smallest.
    r = pd.Series([-0.05, -0.03, -0.01, 0.0, 0.01, 0.01, 0.02, 0.03, 0.04, 0.05])
    # pandas linear interpolation: position (n-1) x 0.10 = 0.9 -> -5% + 0.9 x 2% = -3.2%
    assert qu.historical_var(r, 0.90) == pytest.approx(0.032)
    # Only -5% lies at or below -3.2%
    assert qu.expected_shortfall(r, 0.90) == pytest.approx(0.05)


def test_skew_and_kurtosis_signs():
    left_tail = pd.Series([0.01] * 20 + [-0.10])
    assert qu.skewness(left_tail) < 0
    assert qu.excess_kurtosis(left_tail) > 0


def test_capm_required_return():
    assert qu.capm_required_return(1.2, 0.055, 0.07) == pytest.approx(0.055 + 0.084)
