"""Monte Carlo building blocks: correlation preserved, bootstrap uses real rows, maths of paths."""
import numpy as np
import pandas as pd
import pytest

from src import monte_carlo as mc

RNG = np.random.default_rng(0)


def test_parametric_draws_reproduce_mean_and_covariance():
    mu = np.array([0.001, 0.002])
    cov = np.array([[1e-4, 6e-5], [6e-5, 4e-4]])
    x = mc.simulate_parametric(mu, cov, 4000, 50, RNG).reshape(-1, 2)
    assert x.mean(axis=0) == pytest.approx(mu, abs=2e-4)
    assert np.cov(x.T) == pytest.approx(cov, rel=0.03)


def test_bootstrap_rows_are_real_days_in_contiguous_blocks():
    history = np.arange(20, dtype=float).reshape(10, 2)        # day t = [2t, 2t + 1]
    x = mc.simulate_bootstrap(history, n_sims=50, horizon=7, block=3, rng=RNG)
    assert x.shape == (50, 7, 2)
    rows = x.reshape(-1, 2)
    assert np.all(rows[:, 1] == rows[:, 0] + 1)               # whole days kept together
    day = x[:, :, 0] / 2
    assert np.all((day[:, 1] - day[:, 0]) % 10 == 1)          # consecutive days within a block (circular)


def test_shift_means_keeps_shape():
    h = RNG.normal(0.001, 0.02, size=(500, 3))
    target = np.array([0.0004, 0.0005, 0.0006])
    s = mc.shift_means(h, target)
    assert s.mean(axis=0) == pytest.approx(target)
    assert s.std(axis=0) == pytest.approx(h.std(axis=0))


def test_all_tbills_grow_at_the_risk_free_rate():
    x = RNG.normal(size=(5, 4, 2)) * 0.01
    w = mc.wealth_paths(x, np.array([0.5, 0.5]), y=0.0, rf_period=0.001)
    assert w[:, -1] == pytest.approx(np.full(5, 1.001 ** 4))


def test_rebalancing_rules_agree_over_one_period():
    x = RNG.normal(size=(5, 1, 2)) * 0.01
    a = mc.wealth_paths(x, np.array([0.3, 0.7]), 0.8, 0.001, "constant_mix")
    b = mc.wealth_paths(x, np.array([0.3, 0.7]), 0.8, 0.001, "buy_and_hold")
    assert a == pytest.approx(b)


def test_summarize_on_known_paths():
    # Four paths ending at 0.9, 1.0, 1.1, 1.2 of the initial value.
    wealth = np.array([[1, 0.95, 0.9], [1, 1.0, 1.0], [1, 1.05, 1.1], [1, 1.1, 1.2]])
    s = mc.summarize(wealth, 100)
    assert s["prob_loss"] == pytest.approx(0.25)
    assert s["mean_terminal"] == pytest.approx(105)
    assert s["max_drawdown_percentiles"]["p5"] == pytest.approx(-0.1, abs=0.02)


def test_ewma_cov_recursion():
    r = pd.DataFrame({"a": [0.01, -0.01, 0.02, 0.03], "b": [0.0, 0.01, -0.01, 0.02]})
    s = np.cov(r.iloc[:2].to_numpy().T)
    for row in r.iloc[2:].to_numpy():
        s = 0.9 * s + 0.1 * np.outer(row, row)
    assert mc.ewma_cov(r, lam=0.9, seed_days=2).to_numpy() == pytest.approx(s)
