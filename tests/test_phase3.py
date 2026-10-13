"""Technical rules, event study and extraction scoring, on synthetic data."""
import numpy as np
import pandas as pd
import pytest

from src import extraction_check as ec
from src import forecast as fc
from src import technical as tech

DATES = pd.bdate_range("2020-01-01", periods=400)


def test_rsi_extremes():
    up = pd.Series(np.arange(1, 60, dtype=float))
    assert tech.rsi(up).iloc[-1] == pytest.approx(100.0)
    zigzag = pd.Series([100.0, 101.0] * 30)
    assert 40 < tech.rsi(zigzag).iloc[-1] < 60


def test_trend_signal_on_a_rising_series():
    p = pd.Series(np.linspace(100, 200, 400), index=DATES)
    s = tech.trend_signal(p)
    assert s.iloc[:199].isna().all() and (s.iloc[199:] == 1).all()


def test_always_invested_without_costs_equals_buy_and_hold():
    rng = np.random.default_rng(1)
    p = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 400)), index=DATES)
    sig = pd.Series(1.0, index=DATES)
    out = tech.strategy_returns(p, sig, rf_annual=0.05, cost_one_way=0.0)
    bh = p.pct_change().loc[out.index]
    assert out.to_numpy() == pytest.approx(bh.to_numpy())


def test_switching_pays_the_cost():
    p = pd.Series(100.0, index=DATES[:5])                         # flat prices: only rf and costs matter
    sig = pd.Series([0, 1, 1, 0, 0], index=DATES[:5], dtype=float)
    out = tech.strategy_returns(p, sig, rf_annual=0.0, cost_one_way=0.01)
    # Positions (yesterday's signal) 0,1,1,0 -> switches at days 2 and 4
    assert out.tolist() == pytest.approx([0.0, -0.01, 0.0, -0.01])


def test_event_study_recovers_a_planted_jump():
    rng = np.random.default_rng(2)
    m = pd.Series(rng.normal(0, 0.01, 400), index=DATES)
    s = 1.2 * m + rng.normal(0, 0.002, 400)
    s.iloc[300] += 0.05                                           # +5% abnormal return on the event day
    res = fc.event_study(s, m, [DATES[300].date().isoformat()])
    assert res["car"].iloc[0] == pytest.approx(0.05, abs=0.01)


def test_extraction_classification():
    assert ec._classify(100.5, 100, "")[1] == "match"
    assert ec._classify(110, 100, "known definition gap")[1] == "definition difference"
    assert ec._classify(110, 100, "")[1] == "extraction error"
