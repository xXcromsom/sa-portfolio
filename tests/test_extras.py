"""Variance ratios, alpha significance, the Street bridge, and the mood score."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.extras import performance
from python_project import DividendDiscountModel, ResidualIncomeModel
from src import emh_tests as emh
from src import mood
from src import quant_utils as qu
from src import street

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "submission"


# ---------------------------------------------------------------- weak form
def test_random_returns_look_random():
    x = np.random.default_rng(0).normal(0, 0.01, 5000)
    for q in (5, 20):
        out = emh.variance_ratio(x, q)
        assert abs(out["vr"] - 1) < 0.1 and abs(out["z"]) < 2.5
    ac = emh.lag1_autocorrelation(x)
    assert abs(ac["rho"]) < 0.05 and abs(ac["z"]) < 2.5


def test_autocorrelated_returns_are_detected():
    rng = np.random.default_rng(1)
    e = rng.normal(0, 0.01, 5000)
    x = np.zeros(5000)
    for t in range(1, 5000):
        x[t] = 0.3 * x[t - 1] + e[t]
    assert emh.variance_ratio(x, 5)["vr"] > 1.3
    assert emh.variance_ratio(x, 5)["z"] > 5
    ac = emh.lag1_autocorrelation(x)
    assert ac["rho"] == pytest.approx(0.3, abs=0.05) and ac["z"] > 5


def test_mean_reversion_gives_a_ratio_below_one():
    e = np.random.default_rng(2).normal(0, 0.01, 5000)
    assert emh.variance_ratio(np.diff(e), 5)["vr"] < 0.5


# ---------------------------------------------------------------- semi-strong
def _market_days(n=800, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    m = rng.normal(0.0004, 0.01, n)
    return idx, m, rng


def test_drift_events_find_the_planted_reaction_and_drift():
    idx, m, rng = _market_days()
    s = 0.0001 + 1.0 * m + rng.normal(0, 0.002, len(idx))
    pos = 500
    s[pos] += 0.05         # the reaction
    s[pos + 10] += 0.03    # the drift
    returns = pd.DataFrame({"S": s, "M": m}, index=idx)
    consensus = {"S": {"surprises": [{"date": idx[pos].date().isoformat(), "estimate": 10, "reported": 11, "surprise_pct": 10.0}]}}
    ev = emh.drift_events(returns, consensus, ["S"], "M")
    assert len(ev) == 1
    assert ev.ev[0] == pytest.approx(0.05, abs=0.01)
    assert ev.d20[0] == pytest.approx(0.03, abs=0.015)


def test_event_reaction_matches_the_existing_event_study():
    returns = pd.read_parquet(DATA / "returns_daily.parquet")
    consensus = json.loads((DATA / "consensus.json").read_text(encoding="utf-8"))
    ai = json.loads((DATA / "ai_analysis.json").read_text(encoding="utf-8"))["event_study"]
    stocks = list(consensus)
    ev = emh.drift_events(returns, consensus, stocks, "^NSEI")
    assert len(ev) == ai["events"]
    assert ev[ev.surprise_pct > 0].ev.mean() == pytest.approx(ai["mean_car_positive_surprise"], abs=1e-6)
    assert ev[ev.surprise_pct < 0].ev.mean() == pytest.approx(ai["mean_car_negative_surprise"], abs=1e-6)
    out = emh.semi_strong(ev)
    assert out["flagged_surprises"][0]["surprise_pct"] > 50      # Sun, Nov 2020
    assert any(r["date"] == "2026-02-12" and r["ticker"] == "HINDUNILVR.NS" for r in out["flagged_surprises"])


def test_no_events_means_no_result():
    assert emh.semi_strong(pd.DataFrame()) is None


# ---------------------------------------------------------------- alpha
def test_alpha_t_finds_planted_alpha_and_equals_jensen():
    idx, m, rng = _market_days(4000)
    rf = 0.05
    d = qu.periodic_rf(rf)
    strong = pd.Series(d + 0.002 + 0.8 * (m - d) + rng.normal(0, 0.002, len(m)), index=idx)
    market = pd.Series(m, index=idx)
    out = qu.alpha_significance(strong, market, rf)
    assert out["alpha"] == pytest.approx(qu.jensen_alpha(strong, market, rf), abs=1e-10)
    assert out["t"] > 10 and out["information_ratio"] > 1
    none = pd.Series(d + 0.8 * (m - d) + rng.normal(0, 0.01, len(m)), index=idx)
    assert abs(qu.alpha_significance(none, market, rf)["t"]) < 3


def test_alpha_of_the_market_on_itself_is_zero():
    idx, m, _ = _market_days()
    market = pd.Series(m, index=idx)
    out = qu.alpha_significance(market, market, 0.05)
    assert out["alpha"] == pytest.approx(0, abs=1e-12) and out["information_ratio"] == 0


def test_performance_matches_frozen_backtests():
    returns = pd.read_parquet(DATA / "returns_daily.parquet")
    portfolio = json.loads((DATA / "portfolio.json").read_text(encoding="utf-8"))
    stocks = ["HINDUNILVR.NS", "SUNPHARMA.NS", "ICICIBANK.NS"]
    out = performance(returns, portfolio, stocks, "^NSEI", portfolio["risk_free_rate"], 0.0708, 252)
    for name in ("Forward-looking P", "Equal weight", "History-based P"):
        mine, frozen = out["out_of_sample"]["rows"][name], portfolio["out_of_sample"][name]["portfolio"]
        for key in ("cagr", "sharpe", "beta", "treynor", "jensen_alpha", "max_drawdown"):
            assert mine[key] == pytest.approx(frozen[key], abs=1e-9), (name, key)
    metrics = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))["securities"]
    for t in stocks:
        assert out["full_sample"]["rows"][t]["treynor"] == pytest.approx(metrics[t]["treynor"], abs=1e-5)
    # Excess return is what Sharpe and Treynor divide, and alpha is what is left after beta.
    nifty = out["out_of_sample"]["rows"]["Nifty 50"]
    for r in out["out_of_sample"]["rows"].values():
        assert r["excess_return"] == pytest.approx(r["sharpe"] * r["volatility"])
        assert r["excess_return"] == pytest.approx(r["treynor"] * r["beta"])
        assert r["jensen_alpha"] == pytest.approx(r["excess_return"] - r["beta"] * nifty["excess_return"])
        assert r["excess_over_market"] == pytest.approx(r["excess_return"] - nifty["excess_return"])
    # Alpha scales with y; Sharpe and Treynor do not depend on A.
    b = out["by_profile"]["Balanced"]
    assert b["alpha_on_your_money"] == pytest.approx(out["out_of_sample"]["rows"]["Forward-looking P"]["jensen_alpha"] * b["y"])
    assert out["forward_view"]["treynor"] == 0.0708


# ---------------------------------------------------------------- street
def _ddm():
    return DividendDiscountModel("D", 1861.9, 0.09779228, 0.055, 5, d0=41.0, g1=0.07)


def _ri():
    return ResidualIncomeModel("R", 1350.5, 0.14672924, 0.055, 5, 527.0, 0.159, 0.16, 0.16, 0.15)


def test_required_discount_rate_inverts_the_model():
    for model, target in ((_ddm(), 1935.0), (_ri(), 1401.7)):
        r = street.required_discount_rate(model, target)
        assert street.with_inputs(model, r=r).intrinsic_value() == pytest.approx(target, abs=0.01)
        assert r < model.r
    assert model.r == 0.14672924        # the original is untouched


def test_multi_stage_equals_two_stage():
    m = _ddm()
    assert street.multi_stage_ddm(m.d0, m.r, [(m.g1, 5), (m.g2, 5)], m.g2) == pytest.approx(m.intrinsic_value(), abs=1e-6)


def test_icici_bridge_moves_towards_the_price():
    steps = street.icici_bridge(_ri(), 0.96, 0.055199, 0.0708, {"subsidiaries_per_share": 265, "roe_high": 0.17, "roe_stable": 0.16},
                                1401.7, 1768.79)
    values = [s["value"] for s in steps]
    assert values[0] == pytest.approx(574.65, abs=0.01)
    assert values == sorted(values)
    assert values[1] == pytest.approx(833, abs=1)
    assert values[2] - values[1] == 265
    assert values[3] == pytest.approx(1216, abs=2)


def test_street_files_are_valid():
    views = street.load_views(ROOT / "data" / "street" / "street_views.csv")
    assert set(views.ticker) == {"HINDUNILVR.NS", "SUNPHARMA.NS", "ICICIBANK.NS"}
    assert (views.source_type != "broker PDF").sum() > 20         # mostly second-hand, and marked so
    snapshot = street.load_snapshot(ROOT / "data" / "street" / "snapshot.json")
    out = street.consensus_table(snapshot, views, list(snapshot["securities"]))
    assert out["ICICIBANK.NS"]["buy_share"] == 1.0
    assert out["SUNPHARMA.NS"]["lowest_broker"]["broker"] == "Bank of America"
    assert out["HINDUNILVR.NS"]["upside_to_mean"] == pytest.approx(0.1657, abs=0.001)


def test_views_reject_a_blank_target(tmp_path):
    bad = tmp_path / "v.csv"
    bad.write_text("ticker,broker,rating,target,basis,as_of,after_q2,source_type,source,note\nA,B,Buy,,,,yes,press,,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="blank"):
        street.load_views(bad)


# ---------------------------------------------------------------- mood
def test_mood_is_high_after_a_steady_rise_and_low_after_a_crash():
    idx = pd.bdate_range("2018-01-01", periods=1400)
    rng = np.random.default_rng(4)
    noise = rng.normal(0, 0.01, 1400)
    rising = pd.Series(100 * np.cumprod(1 + np.r_[noise[:1300], np.full(100, 0.004)]), index=idx)
    crash = pd.Series(100 * np.cumprod(1 + np.r_[noise[:1370], np.full(30, -0.02) + rng.normal(0, 0.02, 30)]), index=idx)
    assert mood.mood_series(rising)["mood"].iloc[-1] > 75
    assert mood.mood_series(crash)["mood"].iloc[-1] < 25


def test_mood_ranks_stay_in_range():
    idx = pd.bdate_range("2018-01-01", periods=900)
    p = pd.Series(100 * np.cumprod(1 + np.random.default_rng(5).normal(0, 0.01, 900)), index=idx)
    m = mood.mood_series(p)
    assert m.min().min() >= 0 and m.max().max() <= 100
    assert list(m.columns) == [*mood.COMPONENTS, "mood"]


def test_labels_match_the_tickertape_bands():
    assert [mood.label(x) for x in (10, 40, 60, 90)] == ["Extreme fear", "Fear", "Greed", "Extreme greed"]


def test_vix_study_shape():
    idx = pd.bdate_range("2019-01-01", periods=1000)
    rng = np.random.default_rng(6)
    vix = pd.Series(15 + np.abs(rng.normal(0, 4, 1000)), index=idx)
    nifty = pd.Series(10000 * np.cumprod(1 + rng.normal(0.0005, 0.01, 1000)), index=idx)
    out = mood.vix_study(vix, nifty)
    assert len(out["quintiles"]) == 5 and out["quintiles"][0]["high"] <= out["quintiles"][4]["low"]
    assert out["slope_without_covid"]["n"] < out["slope_all"]["n"]
