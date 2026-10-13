"""SIP simulation checked against the future value of an annuity due."""
import numpy as np
import pytest

from src import sip


def test_contributions_step_up_each_year():
    c = sip.contributions(1000, 0.10, 25)
    assert c[0] == c[11] == 1000
    assert c[12] == pytest.approx(1100) and c[24] == pytest.approx(1210)


def test_glide_path():
    g = sip.glide_path(0.9, 0.4, 13)
    assert g[0] == pytest.approx(0.9) and g[-1] == pytest.approx(0.4)
    assert np.all(np.diff(g) <= 0)
    assert np.all(sip.glide_path(0.3, 0.4, 5) == 0.3)        # never glides upward


def test_constant_returns_match_annuity_due():
    # Every month: invest c at the start, grow at m. FV = sum c_t (1+m)^(n-t).
    n, m = 36, 0.01
    amounts = sip.contributions(1000, 0.10, n)
    corpus = sip.simulate_sip(np.full((1, n), m), np.full(n, 0.6), m, amounts)
    expected = sum(a * (1 + m) ** (n - t) for t, a in enumerate(amounts))
    assert corpus[0, -1] == pytest.approx(expected)


def test_rebalancing_does_not_create_or_destroy_money():
    n = 24
    amounts = np.full(n, 100.0)
    risky = np.zeros((3, n))
    corpus = sip.simulate_sip(risky, sip.glide_path(0.9, 0.4, n), 0.0, amounts, rebalance_every=12)
    assert corpus[:, -1] == pytest.approx(np.full(3, 2400.0))


def test_summary_goal_probabilities():
    corpus = np.array([[0, 50], [0, 100], [0, 150], [0, 200]], dtype=float)
    s = sip.summarize_sip(corpus, np.array([60.0]), goals=[100, 175], inflation=0.0, years=1)
    assert s["prob_reach_goal"] == {"100": 0.75, "175": 0.25}
    assert s["prob_below_invested"] == 0.25
