"""python_project.py is a self-contained copy of the method: it must reach the pipeline's numbers."""
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import python_project as pp
from src import questionnaire as quiz
from src import technical

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "submission"


def _json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def project():
    return pp.load_project()


@pytest.fixture(scope="module")
def models():
    return pp.load_models()


@pytest.fixture(scope="module")
def draws(project):
    return pp.run_simulations(project.daily, project.monthly, project.capm, project.portfolio.weights, project.rf,
                              project.erp, project.settings["monte_carlo"], project.settings["sip"])


def test_file_imports_nothing_else_from_this_repository():
    tree = ast.parse((ROOT / "python_project.py").read_text(encoding="utf-8"))
    modules = {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    modules |= {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not modules & {"src", "pipeline", "scripts"}


# ---------------------------------------------------------------- valuation
def test_models_match_the_workbook_summary(models):
    summary = pd.read_excel(ROOT / "workbook" / "valuation.xlsx", sheet_name="Summary").set_index("ticker")
    for ticker, model in models.items():
        assert model.intrinsic_value() == pytest.approx(summary.at[ticker, "intrinsic_value"], abs=0.01)
        assert model.implied_growth() == pytest.approx(summary.at[ticker, "market_implied_growth"], abs=1e-6)


def test_recursion_matches_closed_forms(models):
    for model in models.values():
        assert model.intrinsic_value() == pytest.approx(model.closed_form_value(), abs=0.01)
        assert model.implied_growth() == pytest.approx(model.implied_growth_closed_form(), abs=1e-6)


def test_right_class_for_each_stock(models):
    assert isinstance(models["HINDUNILVR.NS"], pp.DividendDiscountModel)
    assert isinstance(models["SUNPHARMA.NS"], pp.ResidualIncomeModel)
    assert isinstance(models["ICICIBANK.NS"], pp.ResidualIncomeModel)
    with pytest.raises(TypeError):
        pp.ValuationModel("abstract", 100.0, 0.1, 0.05, 5)


def test_recursive_present_value():
    assert pp.ValuationModel.present_value([], 0.1) == 0
    assert pp.ValuationModel.present_value([110.0], 0.1) == pytest.approx(100)
    flows = [10.0, 20.0, 30.0]
    assert pp.ValuationModel.present_value(flows, 0.08) == pytest.approx(sum(f / 1.08 ** (i + 1) for i, f in enumerate(flows)))


def test_bad_inputs_raise():
    with pytest.raises(ValueError, match="must exceed"):
        pp.DividendDiscountModel("x", 100.0, r=0.05, g2=0.06, n=5, d0=1.0, g1=0.05)
    with pytest.raises(ValueError, match="high-growth years"):
        pp.DividendDiscountModel("x", 100.0, r=0.10, g2=0.05, n=11, d0=1.0, g1=0.05)
    with pytest.raises(ValueError, match="stable ROE"):
        pp.ResidualIncomeModel("x", 100.0, 0.10, 0.05, 5, 50.0, 0.15, 0.15, 0.3, 0.04)


def test_blank_workbook_cell_gives_a_clear_error(tmp_path):
    from openpyxl import load_workbook

    wb = load_workbook(ROOT / "workbook" / "valuation.xlsx", data_only=True)
    ws = wb["Inputs"]
    ws["B20"] = None        # HUL's dividend
    path = tmp_path / "blank.xlsx"
    wb.save(path)
    with pytest.raises(pp.DataError, match="Dividend per share"):
        pp.load_models(path)
    with pytest.raises(pp.DataError, match="not found"):
        pp.load_models(tmp_path / "missing.xlsx")


# ---------------------------------------------------------------- returns, portfolio
def test_metrics_match_metrics_json(project):
    frozen = _json("metrics.json")["securities"]
    table = pp.metrics_table(project.daily, pp.BENCHMARK, project.rf, project.erp)
    for t, row in table.iterrows():
        for col in table.columns:
            assert row[col] == pytest.approx(frozen[t][col], abs=2e-6), (t, col)


def test_tangency_matches_portfolio_json(project):
    frozen = _json("portfolio.json")["views"]["forward"]["tangency"]
    assert dict(zip(pp.STOCKS, project.portfolio.weights)) == pytest.approx(frozen["weights"], abs=1e-4)
    assert project.portfolio.expected_return == pytest.approx(frozen["expected_return"], abs=1e-5)
    assert project.portfolio.volatility == pytest.approx(frozen["volatility"], abs=1e-5)
    assert project.portfolio.sharpe(project.rf) == pytest.approx(frozen["sharpe"], abs=1e-5)


def test_grid_search_finds_the_same_optimum(project):
    weights, sharpe = pp.grid_search_max_sharpe(project.capm, project.portfolio.covariance, project.rf)
    assert sharpe == pytest.approx(project.portfolio.sharpe(project.rf), abs=1e-3)
    assert weights == pytest.approx(project.portfolio.weights, abs=0.02)


def test_allocation_for_balanced_investor(project):
    split = project.portfolio.allocation(pp.Investor("B", 4.0), project.rf)
    assert split["HUL"] == pytest.approx(13382, abs=20)
    assert split["Sun Pharma"] == pytest.approx(8394, abs=20)
    assert split["ICICI Bank"] == pytest.approx(21833, abs=20)
    assert split["T-bills"] == pytest.approx(56392, abs=20)
    assert sum(split.values()) == pytest.approx(100000)


def test_low_and_negative_a(project):
    p, rf = project.portfolio, project.rf
    assert p.complete(pp.Investor("n", 0.0), rf)["y"] == 1.0
    assert p.complete(pp.Investor("s", -1.0), rf)["y"] == 1.0
    assert p.complete(pp.Investor("s", -1.0), rf, borrow=True)["y"] == 2.0
    assert pp.Investor("n", 0.0).profile == "Risk-neutral"


def test_weights_are_validated():
    s = pp.Security("X", "X", 1.0, 0.1, 0.2)
    with pytest.raises(ValueError, match="sum to 1"):
        pp.Portfolio([s, s], [0.5, 0.6], np.eye(2))
    with pytest.raises(ValueError, match="one weight"):
        pp.Portfolio([s], [0.5, 0.5], np.eye(1))


def test_questionnaire_matches_the_dashboard():
    rng = np.random.default_rng(3)
    assert list(pp.QUESTIONS) == [q[0] for q in quiz.QUESTIONS]
    for _ in range(50):
        answers = {k: int(rng.integers(1, 6)) for k in pp.QUESTIONS}
        assert pp.risk_aversion_from(answers) == quiz.score(answers).risk_aversion
    with pytest.raises(ValueError, match="unanswered"):
        pp.risk_aversion_from({})


# ---------------------------------------------------------------- sorting and searching
def test_merge_sort_and_binary_search():
    rng = np.random.default_rng(1)
    items = list(rng.normal(size=500))
    ordered = pp.merge_sort(items)
    assert ordered == sorted(items)
    assert pp.merge_sort([]) == []
    assert pp.merge_sort(["bb", "a", "ccc"], key=len) == ["a", "bb", "ccc"]
    assert pp.binary_search(ordered, 0.0) == sum(x < 0.0 for x in items)
    for p in (0, 5, 50, 95, 100):
        assert pp.percentile(ordered, p) == pytest.approx(np.percentile(items, p))


def test_best_and_worst():
    worst, best = pp.Portfolio.best_and_worst([5, 1, 4, 2, 3], 2)
    assert worst == [1, 2] and best == [4, 5]


# ---------------------------------------------------------------- simulation
def test_simulations_reproduce_mc_and_sip_json(project, draws):
    mc_file, sip_file = _json("mc.json")["results"], _json("sip.json")["results"]
    rf_d, rf_m = pp.periodic_rf(project.rf), pp.periodic_rf(project.rf, 12)
    y = project.portfolio.complete(pp.Investor("B", 4.0), project.rf)["y"]
    for mode, key in (("Parametric", "Parametric"), ("Bootstrap", "Bootstrap"),
                      ("Parametric, today's volatility", "Parametric, current volatility (EWMA)")):
        got = pp.risk_summary(pp.wealth_paths(draws["one_year"][mode], y, rf_d), 100000)
        assert got["var_95"] == pytest.approx(mc_file[key]["Balanced"]["var_95"], abs=15), mode
        assert got["median"] == pytest.approx(mc_file[key]["Balanced"]["terminal_percentiles"]["p50"], abs=15), mode
    sip = project.settings["sip"]
    months = sip["years"] * 12
    amounts = pp.sip_contributions(sip["monthly_amount"], sip["annual_step_up"], months)
    glide = pp.glide_path(y, sip["glide_path_end_equity"], months)
    for mode in ("Parametric", "Bootstrap"):
        corpus = pp.simulate_sip(draws["sip"][mode], glide, rf_m, amounts)
        assert np.median(corpus) == pytest.approx(sip_file["Balanced"][mode]["terminal_percentiles"]["p50"], rel=2e-3), mode


# ---------------------------------------------------------------- efficiency and text
def test_rules_match_the_pipeline():
    prices = pd.read_parquet(DATA / "prices.parquet")
    rf = _json("metrics.json")["assumptions"]["risk_free_rate"]
    table = technical.evaluate(prices[["HINDUNILVR.NS"]], rf).set_index("rule")["sharpe"]
    got = pp.rule_sharpes(prices["HINDUNILVR.NS"].dropna(), rf)
    for rule, sharpe in got.items():
        assert sharpe == pytest.approx(table[rule], abs=1e-9)


def test_hedge_share_and_headlines():
    assert pp.hedge_share("Margins may fall") == pytest.approx(1 / 3)
    assert pp.hedge_share("") == 0.0
    news = pd.DataFrame({"ticker": ["A", "A", "B"], "tone": [0.5, -0.5, 0.2], "label": ["positive", "negative", "neutral"]})
    out = pp.headline_summary(news)
    assert out.at["A", "headlines"] == 2 and out.at["A", "mean_tone"] == 0 and out.at["A", "positive"] == 0.5


def test_files_raise_data_errors(tmp_path):
    with pytest.raises(pp.DataError, match="not found"):
        pp.read_json(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(pp.DataError, match="not valid JSON"):
        pp.read_json(bad)
    with pytest.raises(pp.DataError, match="lacks columns"):
        pp.read_returns(DATA / "returns_daily.parquet", ["NOPE"])
    gappy = tmp_path / "gappy.parquet"
    pd.DataFrame({"A": [0.1, None]}).to_parquet(gappy)
    with pytest.raises(pp.DataError, match="missing values"):
        pp.read_returns(gappy, ["A"])


def test_rupees():
    assert pp.rupees(100000) == "Rs 1,00,000"
    assert pp.rupees(1234567) == "Rs 12,34,567"
    assert pp.rupees(-950) == "-Rs 950"
