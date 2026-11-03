"""Behaviour-aware portfolio construction, in one file (Python course project, BBAT5E07).

Team: Abhay S (246213044), Sankarshana Mulugundam (246213080). Faculty: Prof. Jinu Sara.

The question: how much of an investor's money should go into a portfolio of Hindustan Unilever,
Sun Pharma and ICICI Bank, given how much risk that investor can bear? This file answers it from
start to finish without importing anything else from this repository. It reads the frozen data in
data/submission and workbook/valuation.xlsx, and tests/test_python_project.py checks that it
reproduces the project pipeline's numbers.

Run it:
    python python_project.py                    # the full tour, section by section
    python python_project.py --charts out/      # also save the Matplotlib and Seaborn charts
    python python_project.py --fetch            # also download fresh prices with yfinance
    python python_project.py --finbert          # also score sample headlines with FinBERT
    python python_project.py --pdf report.pdf   # also read a PDF with pypdf
    streamlit run python_project.py             # a small interactive demo

Where each course concept lives:
    Variables, numbers, strings ......... section 1
    Files and exceptions ................ section 2
    Functions, Pandas ................... section 3
    Decisions, loops, dictionaries ...... sections 4 and 10
    Classes ............................. section 5
    Inheritance, recursion .............. section 6
    Sorting and searching ............... section 7
    SciPy ............................... section 8
    NumPy ............................... sections 9 and 10
    Sets, Transformers, pypdf, yfinance . sections 2 and 11
    Matplotlib, Seaborn ................. section 12
    Streamlit ........................... section 14

Heavy libraries are imported inside the function that needs them, so the file still starts on a
machine that lacks one of them. This is coursework, not investment advice.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ 1. settings: variables, numbers, strings
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "submission"
WORKBOOK = ROOT / "workbook" / "valuation.xlsx"
SETTINGS = ROOT / "config.yaml"

STOCKS = ["HINDUNILVR.NS", "SUNPHARMA.NS", "ICICIBANK.NS"]
BENCHMARK = "^NSEI"
SHORT = {"HINDUNILVR.NS": "HUL", "SUNPHARMA.NS": "Sun Pharma", "ICICIBANK.NS": "ICICI Bank", BENCHMARK: "Nifty 50"}
TRADING_DAYS = 252
WEIGHT_BOUNDS = (0.10, 0.60)    # no stock below 10% or above 60% of P


def rupees(amount: float) -> str:
    """A rupee amount with Indian digit grouping, as a string: 1,00,000."""
    digits = f"{abs(amount):.0f}"
    if len(digits) > 3:
        head, tail, groups = digits[:-3], digits[-3:], []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        digits = ",".join(([head] if head else []) + groups) + "," + tail
    return ("-" if amount < 0 else "") + "Rs " + digits


# ------------------------------------------------------------------ 2. files and exceptions
class DataError(Exception):
    """A data file is missing or unusable. The message names the file and the fix."""


def read_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise DataError(f"{path} not found; run the pipeline first") from err
    except json.JSONDecodeError as err:
        raise DataError(f"{path} is not valid JSON: {err}") from err


def read_settings(path: Path = SETTINGS) -> dict:
    """The project's settings file (YAML): risk-free rate, simulation sizes, SIP terms."""
    import yaml

    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise DataError(f"settings file {path} not found") from err
    except yaml.YAMLError as err:
        raise DataError(f"settings file {path} is not valid YAML: {err}") from err


def read_returns(path: Path, needed: list[str]) -> pd.DataFrame:
    """A returns table. Refuses a file with a missing column or gaps, rather than guessing the values."""
    try:
        table = pd.read_parquet(path)
    except FileNotFoundError as err:
        raise DataError(f"{path} not found; run the pipeline first") from err
    missing = [c for c in needed if c not in table.columns]
    if missing:
        raise DataError(f"{path} lacks columns {missing}")
    gaps = int(table[needed].isna().sum().sum())
    if gaps:
        raise DataError(f"{path} has {gaps} missing values in {needed}")
    return table[needed]


def read_metrics_csv(path: Path) -> pd.DataFrame:
    """The pipeline's metrics table (a CSV file), indexed by security name."""
    try:
        return pd.read_csv(path, index_col=0)
    except FileNotFoundError as err:
        raise DataError(f"{path} not found; run the pipeline first") from err
    except pd.errors.ParserError as err:
        raise DataError(f"{path} is not a valid CSV: {err}") from err


def read_pdf_text(path: Path, max_pages: int = 5) -> str:
    """Text of the first pages of a PDF, with pypdf. A scanned PDF has no text, which is an error here."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        pages = PdfReader(str(path)).pages[:max_pages]
    except FileNotFoundError as err:
        raise DataError(f"PDF {path} not found") from err
    except PdfReadError as err:
        raise DataError(f"PDF {path} could not be read: {err}") from err
    text = "\n".join(page.extract_text() or "" for page in pages)
    if not text.strip():
        raise DataError(f"PDF {path} has no extractable text (scanned?)")
    return text


def download_prices(tickers: list[str], start: str = "2016-01-01") -> pd.DataFrame:
    """Daily adjusted closes from Yahoo Finance. A failed or empty download raises; it is never hidden.

    Antivirus HTTPS scanning (Avast on our laptop) makes yfinance return nothing unless it is given a
    certificate bundle that includes the antivirus root; scripts/build_ca_bundle.py writes that file.
    """
    import yfinance as yf

    session = None
    bundle = ROOT / ".certs" / "ca-bundle.pem"
    if bundle.exists():
        from curl_cffi import requests as curl_requests
        session = curl_requests.Session(impersonate="chrome", verify=str(bundle))
    try:
        prices = yf.download(tickers, start=start, auto_adjust=True, progress=False, session=session)["Close"]
    except Exception as err:  # yfinance raises many network error types
        raise DataError(f"download failed ({type(err).__name__}): {err}") from err
    prices = prices.dropna(how="all")
    if prices.empty:
        raise DataError(f"Yahoo Finance returned no prices for {tickers}")
    return prices


# ------------------------------------------------------------------ 3. returns and risk: functions on Pandas objects
def periodic_rf(rf_annual: float, periods: int = TRADING_DAYS) -> float:
    """The per-period rate that compounds to rf_annual over a year."""
    return (1 + rf_annual) ** (1 / periods) - 1


def to_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change(fill_method=None).iloc[1:]


def cagr(returns, periods: int = TRADING_DAYS):
    """Geometric annual growth rate: what the investor actually earned."""
    return (1 + returns).prod() ** (periods / returns.shape[0]) - 1


def annual_volatility(returns, periods: int = TRADING_DAYS):
    return returns.std(ddof=1) * np.sqrt(periods)


def sharpe_ratio(returns, rf: float, periods: int = TRADING_DAYS):
    """(Rp - Rf) / sigma, with the arithmetic mean excess return scaled to a year."""
    return (returns - periodic_rf(rf, periods)).mean() * periods / annual_volatility(returns, periods)


def sortino_ratio(returns, rf: float, periods: int = TRADING_DAYS):
    """Sharpe's cousin: only returns below the risk-free rate count as risk."""
    excess = returns - periodic_rf(rf, periods)
    return excess.mean() * periods / (np.sqrt((excess.clip(upper=0) ** 2).mean()) * np.sqrt(periods))


def max_drawdown(returns):
    """The worst fall from a running peak, as a negative number. Starting wealth of 1 counts as a peak."""
    wealth = (1 + returns).cumprod()
    return (wealth / wealth.cummax().clip(lower=1.0) - 1).min()


def historical_var(returns, level: float = 0.95):
    """One-day historical Value at Risk, as a positive loss."""
    return -returns.quantile(1 - level)


def beta(returns: pd.Series, market: pd.Series) -> float:
    if not returns.index.equals(market.index):
        raise ValueError("returns and market must share the same dates")
    return returns.cov(market) / market.var(ddof=1)


def treynor_ratio(returns: pd.Series, market: pd.Series, rf: float, periods: int = TRADING_DAYS) -> float:
    """(Rp - Rf) / beta: excess return per unit of market risk."""
    return (returns - periodic_rf(rf, periods)).mean() * periods / beta(returns, market)


def jensen_alpha(returns: pd.Series, market: pd.Series, rf: float, periods: int = TRADING_DAYS) -> float:
    """Annual return above what CAPM predicts for this beta."""
    daily_rf = periodic_rf(rf, periods)
    return ((returns - daily_rf).mean() - beta(returns, market) * (market - daily_rf).mean()) * periods


def metrics_table(returns: pd.DataFrame, market: str, rf: float, erp: float) -> pd.DataFrame:
    """One row per security, one column per measure."""
    rows = {}
    for name in returns.columns:
        r = returns[name]
        b = beta(r, returns[market])
        rows[name] = {"cagr": cagr(r), "volatility": annual_volatility(r), "sharpe": sharpe_ratio(r, rf),
                      "sortino": sortino_ratio(r, rf), "max_drawdown": max_drawdown(r), "var_95_daily": historical_var(r),
                      "beta": b, "treynor": treynor_ratio(r, returns[market], rf),
                      "jensen_alpha": jensen_alpha(r, returns[market], rf), "capm_required_return": rf + b * erp}
    return pd.DataFrame(rows).T


# ------------------------------------------------------------------ 4. the risk questionnaire: dictionaries, loops, decisions
# key -> (kind, question, five options from most cautious to most risk-tolerant)
QUESTIONS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "horizon": ("capacity", "When will you need most of this money?",
                ("Within 1 year", "In 1-3 years", "In 3-5 years", "In 5-10 years", "In more than 10 years")),
    "drawdown": ("willingness", "Your portfolio falls 20% in three months. What do you do?",
                 ("Sell everything", "Sell some", "Hold and wait", "Buy a little more", "Buy a lot more")),
    "range": ("willingness", "Which one-year range of outcomes would you pick?",
              ("+4% to +7%", "0% to +12%", "-8% to +18%", "-15% to +28%", "-25% to +40%")),
    "experience": ("willingness", "How much investing experience do you have?",
                   ("None", "Fixed deposits and savings only", "Mutual funds or SIPs", "Some direct stocks",
                    "Direct stocks for 2+ years")),
    "cushion": ("capacity", "Without this money, how many months of expenses could you cover?",
                ("Under 1 month", "1-3 months", "3-6 months", "6-12 months", "More than 12 months")),
    "income": ("capacity", "How stable is your expected income?",
               ("Uncertain", "Somewhat uncertain", "Fairly stable", "Stable", "Very stable, with room to save")),
    "gamble": ("willingness", "I would accept a 1-in-10 chance of losing a quarter of my investment for a chance to double it.",
               ("Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree")),
    "feeling": ("willingness", "How do you feel when an investment you hold falls sharply?",
                ("I lose sleep", "Very anxious", "Uneasy, but I stay put", "Calm", "I see an opportunity")),
    "goal": ("willingness", "What is the main goal for this money?",
             ("Protect what I have", "Steady income", "Balanced growth", "Growth", "Maximum growth")),
    "share": ("capacity", "What share of your total savings is this money?",
              ("Almost all of it", "More than half", "About half", "About a quarter", "Under 10%")),
}


def score_to_a(score: float) -> float:
    """Score 0 -> A = 8, 0.5 -> A = 4, 1 -> A = 1.5, in straight lines between."""
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"score must be between 0 and 1, got {score}")
    if score <= 0.5:
        return 8.0 - 4.0 * score / 0.5
    return 4.0 - 2.5 * (score - 0.5) / 0.5


def profile_name(risk_aversion: float) -> str:
    if risk_aversion < 3:
        return "Aggressive"
    if risk_aversion < 5.5:
        return "Balanced"
    return "Conservative"


def risk_aversion_from(answers: dict[str, int]) -> float:
    """Ten answers (1 = most cautious, 5 = most tolerant) -> A, to the nearest 0.25.

    Capacity (can you afford risk?) and willingness (do you want it?) are scored separately.
    The higher A wins: a willing investor who cannot afford a loss should not take it.
    """
    groups: dict[str, list[int]] = {"capacity": [], "willingness": []}
    for key, (kind, _, _) in QUESTIONS.items():
        if key not in answers:
            raise ValueError(f"unanswered question: {key}")
        if answers[key] not in (1, 2, 3, 4, 5):
            raise ValueError(f"answer to {key!r} must be 1-5, got {answers[key]!r}")
        groups[kind].append(answers[key])
    scores = {kind: (sum(values) / len(values) - 1) / 4 for kind, values in groups.items()}
    return round(max(score_to_a(s) for s in scores.values()) * 4) / 4


# ------------------------------------------------------------------ 5. business entities: classes
@dataclass
class Security:
    ticker: str
    name: str
    beta: float
    expected_return: float
    volatility: float

    def sharpe(self, rf: float) -> float:
        return (self.expected_return - rf) / self.volatility


@dataclass
class Investor:
    name: str
    risk_aversion: float
    amount: float = 100_000
    monthly_sip: float = 10_000

    @classmethod
    def from_answers(cls, name: str, answers: dict[str, int], amount: float = 100_000, monthly_sip: float = 10_000) -> "Investor":
        return cls(name, risk_aversion_from(answers), amount, monthly_sip)

    @property
    def profile(self) -> str:
        if self.risk_aversion > 0:
            return profile_name(self.risk_aversion)
        return "Risk-neutral" if self.risk_aversion == 0 else "Risk-seeking"


class Portfolio:
    """A risky portfolio P: securities, their weights and their covariance matrix."""

    def __init__(self, securities: list[Security], weights, covariance):
        self.securities = securities
        self.weights = np.asarray(weights, dtype=float)
        self.covariance = np.asarray(covariance, dtype=float)
        if len(self.weights) != len(securities):
            raise ValueError("one weight per security is needed")
        if abs(self.weights.sum() - 1) > 1e-6:
            raise ValueError(f"weights must sum to 1, got {self.weights.sum():.6f}")
        if self.covariance.shape != (len(securities), len(securities)):
            raise ValueError("the covariance matrix must be square, one row per security")

    @property
    def expected_return(self) -> float:
        return float(self.weights @ np.array([s.expected_return for s in self.securities]))

    @property
    def volatility(self) -> float:
        return float(np.sqrt(self.weights @ self.covariance @ self.weights))    # sqrt(w' S w)

    def sharpe(self, rf: float) -> float:
        return (self.expected_return - rf) / self.volatility

    def complete(self, investor: Investor, rf: float, borrow: bool = False, max_leverage: float = 2.0) -> dict:
        """Split the investor's money between P and T-bills: y* = (E[rP] - rf) / (A sigma^2).

        U = E(r) - 1/2 A sigma^2 is largest at y*. At A <= 0, risk never lowers utility, so y* has no
        finite value and the investor holds the most P allowed.
        """
        A = investor.risk_aversion
        y_star = (self.expected_return - rf) / (A * self.volatility ** 2) if A > 0 else math.inf
        cap = max_leverage if borrow else 1.0
        y = min(max(y_star, 0.0), cap)
        er = rf + y * (self.expected_return - rf)
        vol = y * self.volatility
        return {"y_star": y_star, "y": y, "expected_return": er, "volatility": vol,
                "certainty_equivalent": er - 0.5 * A * vol ** 2}

    def allocation(self, investor: Investor, rf: float, borrow: bool = False) -> dict[str, float]:
        """The investor's money in rupees, stock by stock, with the rest in T-bills."""
        y = self.complete(investor, rf, borrow)["y"]
        split = {s.name: y * w * investor.amount for s, w in zip(self.securities, self.weights)}
        split["T-bills"] = (1 - y) * investor.amount
        return split

    def ranked(self, key, reverse: bool = True) -> list[Security]:
        """Securities sorted by any key, e.g. portfolio.ranked(lambda s: s.sharpe(rf))."""
        return sorted(self.securities, key=key, reverse=reverse)

    @staticmethod
    def best_and_worst(outcomes, n: int = 3) -> tuple[list[float], list[float]]:
        """The n worst and n best simulated outcomes."""
        ordered = sorted(float(x) for x in outcomes)
        return ordered[:n], ordered[-n:]


# ------------------------------------------------------------------ 6. valuation: inheritance and recursion
class ValuationModel(ABC):
    """What every model shares: discounting, the terminal value step and the reverse solve.

    A subclass only says what its cash flows are. Value = PV of 10 years of cash flows + PV of a
    terminal value at year 10, the same layout as the Excel workbook's tables.
    """
    HORIZON = 10

    def __init__(self, name: str, price: float, r: float, g2: float, n: int):
        if r <= g2:
            raise ValueError(f"{name}: the discount rate {r:.2%} must exceed terminal growth {g2:.2%}")
        if not 1 <= n <= self.HORIZON:
            raise ValueError(f"{name}: high-growth years must be 1 to {self.HORIZON}, got {n}")
        self.name, self.price, self.r, self.g2, self.n = name, price, r, g2, n

    @staticmethod
    def present_value(flows: list[float], r: float, t: int = 1) -> float:
        """Recursive: PV = first flow discounted t years + PV of the remaining flows."""
        if not flows:           # base case: nothing left to discount
            return 0.0
        return flows[0] / (1 + r) ** t + ValuationModel.present_value(flows[1:], r, t + 1)

    def intrinsic_value(self) -> float:
        return self.present_value(self.cash_flows(), self.r) + self.terminal_value() / (1 + self.r) ** self.HORIZON

    def upside(self) -> float:
        return self.intrinsic_value() / self.price - 1

    def implied_growth(self, low: float = -0.5, high: float | None = None, tol: float = 1e-10) -> float:
        """Recursive bisection: the perpetual growth at which the one-stage value equals the price.

        The answer lies where the gap between value and price changes sign. Each call halves the
        range that contains it, so about 35 calls reach a width of 1e-10.
        """
        high = self.r - 1e-6 if high is None else high
        gap_low = self.single_stage_value(low) - self.price
        if gap_low * (self.single_stage_value(high) - self.price) > 0:
            raise ValueError(f"{self.name}: no growth rate in [{low:.2%}, {high:.2%}] matches the price")
        middle = (low + high) / 2
        if high - low < tol:    # base case: the range is small enough
            return middle
        if gap_low * (self.single_stage_value(middle) - self.price) <= 0:
            return self.implied_growth(low, middle, tol)
        return self.implied_growth(middle, high, tol)

    @abstractmethod
    def cash_flows(self) -> list[float]:
        """The dividends for years 1 to HORIZON."""

    @abstractmethod
    def terminal_value(self) -> float:
        """The value at year HORIZON of everything after it."""

    @abstractmethod
    def single_stage_value(self, g: float) -> float:
        """The value if growth were g for ever, used by the reverse solve."""

    @abstractmethod
    def closed_form_value(self) -> float:
        """The textbook formula for intrinsic_value, as an independent check."""

    @abstractmethod
    def implied_growth_closed_form(self) -> float:
        """The algebra answer for implied_growth, as an independent check."""


class DividendDiscountModel(ValuationModel):
    """Two-stage DDM (HUL, which pays out most of its profit): dividends grow at g1, then g2."""

    def __init__(self, name, price, r, g2, n, d0: float, g1: float):
        super().__init__(name, price, r, g2, n)
        self.d0, self.g1 = d0, g1

    def cash_flows(self) -> list[float]:
        flows, dividend = [], self.d0
        for year in range(1, self.HORIZON + 1):
            dividend *= 1 + (self.g1 if year <= self.n else self.g2)
            flows.append(dividend)
        return flows

    def terminal_value(self) -> float:
        return self.cash_flows()[-1] * (1 + self.g2) / (self.r - self.g2)   # Gordon growth

    def single_stage_value(self, g: float) -> float:
        return self.d0 * (1 + g) / (self.r - g)

    def closed_form_value(self) -> float:
        r, g1, g2, n, d0 = self.r, self.g1, self.g2, self.n, self.d0
        growth_stage = d0 * (1 + g1) / (r - g1) * (1 - ((1 + g1) / (1 + r)) ** n)
        return growth_stage + d0 * (1 + g1) ** n * (1 + g2) / ((r - g2) * (1 + r) ** n)

    def implied_growth_closed_form(self) -> float:
        return (self.r * self.price - self.d0) / (self.price + self.d0)


class ResidualIncomeModel(ValuationModel):
    """Two-stage residual income (Sun Pharma's low payout; ICICI, a bank): book value compounds at ROE x retention."""

    def __init__(self, name, price, r, g2, n, book_value: float, roe_now: float, roe_high: float,
                 payout_high: float, roe_stable: float):
        super().__init__(name, price, r, g2, n)
        if roe_stable <= g2:
            raise ValueError(f"{name}: stable ROE {roe_stable:.2%} must exceed terminal growth {g2:.2%}")
        self.book_value, self.roe_now, self.roe_high = book_value, roe_now, roe_high
        self.payout_high, self.roe_stable = payout_high, roe_stable

    def _projection(self) -> tuple[list[float], float]:
        """Dividends for each year and book value at the horizon, with earnings = ROE x opening book."""
        book, dividends = self.book_value, []
        for year in range(1, self.HORIZON + 1):
            roe = self.roe_high if year <= self.n else self.roe_stable
            payout = self.payout_high if year <= self.n else 1 - self.g2 / self.roe_stable
            earnings = book * roe
            dividends.append(earnings * payout)
            book += earnings * (1 - payout)
        return dividends, book

    def cash_flows(self) -> list[float]:
        return self._projection()[0]

    def terminal_value(self) -> float:
        return self._projection()[1] * (self.roe_stable - self.g2) / (self.r - self.g2)     # justified P/B x book

    def single_stage_value(self, g: float) -> float:
        return self.book_value * (self.roe_now - g) / (self.r - g)

    def closed_form_value(self) -> float:
        r, n, g2 = self.r, self.n, self.g2
        growth = self.roe_high * (1 - self.payout_high)
        stage_one = self.payout_high * self.roe_high * self.book_value / (r - growth) * (1 - ((1 + growth) / (1 + r)) ** n)
        return stage_one + self.book_value * (1 + growth) ** n * (self.roe_stable - g2) / (r - g2) / (1 + r) ** n

    def implied_growth_closed_form(self) -> float:
        pb = self.price / self.book_value
        return (self.r * pb - self.roe_now) / (pb - 1)


def _input_cell(sheet, rows: dict, label: str, column: int, ticker: str) -> float:
    """One number from the Inputs sheet, or a clear error saying which cell is wrong."""
    if label not in rows:
        raise DataError(f"Inputs sheet has no row labelled {label!r}")
    value = sheet.cell(rows[label], column).value
    if not isinstance(value, (int, float)):
        raise DataError(f"Inputs sheet: {label!r} for {ticker} should be a number, found {value!r}")
    return float(value)


def load_models(path: Path = WORKBOOK) -> dict[str, ValuationModel]:
    """Build one model per stock from the workbook's Inputs sheet (an Excel file, read with openpyxl).

    Rows are found by their label, not their position, and the 'Valuation model' row picks the class.
    """
    from openpyxl import load_workbook

    try:
        sheet = load_workbook(path, data_only=True)["Inputs"]
    except FileNotFoundError as err:
        raise DataError(f"workbook {path} not found") from err
    except KeyError as err:
        raise DataError(f"workbook {path} has no Inputs sheet") from err
    rows = {sheet.cell(row, 1).value: row for row in range(1, sheet.max_row + 1) if sheet.cell(row, 1).value}
    models: dict[str, ValuationModel] = {}
    for column in (2, 3, 4):
        ticker = sheet.cell(rows["Ticker"], column).value

        def cell(label: str) -> float:
            return _input_cell(sheet, rows, label, column, ticker)

        common = (SHORT.get(ticker, ticker), cell("Price (Rs)"), cell("Cost of equity r = rf + beta x ERP"),
                  cell("Terminal growth g2 (keep at or below rf)"), int(cell("High-growth years N (1 to 10)")))
        if "DDM" in str(sheet.cell(rows["Valuation model"], column).value):
            models[ticker] = DividendDiscountModel(*common, d0=cell("Dividend per share FY26 = D0 (Rs)"),
                                                   g1=cell("Dividend growth in high-growth phase g1 (DDM)"))
        else:
            models[ticker] = ResidualIncomeModel(*common, book_value=cell("Book value per share (Rs)"),
                                                 roe_now=cell("ROE, latest FY"),
                                                 roe_high=cell("ROE in high-growth phase (residual income)"),
                                                 payout_high=cell("Payout in high-growth phase (residual income)"),
                                                 roe_stable=cell("Stable ROE after year N (residual income)"))
    return models


# ------------------------------------------------------------------ 7. sorting and searching
def merge_sort(items: list, key=lambda x: x) -> list:
    """Recursive merge sort: sort each half, then merge the two sorted halves."""
    if len(items) <= 1:
        return list(items)
    middle = len(items) // 2
    left, right = merge_sort(items[:middle], key), merge_sort(items[middle:], key)
    merged, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    return merged + left[i:] + right[j:]


def binary_search(ordered: list[float], value: float) -> int:
    """How many items in a sorted list are below value, found by halving the list each step."""
    low, high = 0, len(ordered)
    while low < high:
        middle = (low + high) // 2
        if ordered[middle] < value:
            low = middle + 1
        else:
            high = middle
    return low


def percentile(ordered: list[float], p: float) -> float:
    """The p-th percentile of a sorted list, interpolating between neighbours as numpy does."""
    position = (len(ordered) - 1) * p / 100
    below = int(position)
    above = min(below + 1, len(ordered) - 1)
    return ordered[below] + (ordered[above] - ordered[below]) * (position - below)


def grid_search_max_sharpe(mu, cov, rf: float, bounds=WEIGHT_BOUNDS, step: float = 0.01) -> tuple[np.ndarray, float]:
    """Exhaustive search for three assets: try every weight mix on a 1% grid, keep the best Sharpe.

    Slower than SciPy and only as fine as the grid, which makes it an independent check of the optimiser.
    """
    mu, cov = np.asarray(mu), np.asarray(cov)
    best_weights, best_sharpe = None, -math.inf
    grid = np.arange(bounds[0], bounds[1] + step / 2, step)
    for a in grid:
        for b in grid:
            c = 1 - a - b
            if bounds[0] - 1e-9 <= c <= bounds[1] + 1e-9:
                w = np.array([a, b, c])
                sharpe = (w @ mu - rf) / np.sqrt(w @ cov @ w)
                if sharpe > best_sharpe:
                    best_weights, best_sharpe = w, sharpe
    return best_weights, float(best_sharpe)


# ------------------------------------------------------------------ 8. optimisation with SciPy
def _optimise(objective, n: int, bounds, constraints=()) -> np.ndarray:
    from scipy.optimize import minimize

    all_constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}, *constraints]
    result = minimize(objective, np.full(n, 1.0 / n), method="SLSQP", bounds=[bounds] * n,
                      constraints=all_constraints, options={"ftol": 1e-12, "maxiter": 500})
    if not result.success:
        raise RuntimeError(f"optimiser failed: {result.message}")
    return result.x


def max_sharpe_weights(mu, cov, rf: float, bounds=WEIGHT_BOUNDS) -> np.ndarray:
    """The tangency portfolio: the weights with the steepest capital allocation line."""
    mu, cov = np.asarray(mu), np.asarray(cov)
    return _optimise(lambda w: -(w @ mu - rf) / np.sqrt(w @ cov @ w), len(mu), bounds)


def efficient_frontier(mu, cov, bounds=WEIGHT_BOUNDS, points: int = 40) -> pd.DataFrame:
    """The lowest volatility available at each target return."""
    mu, cov = np.asarray(mu), np.asarray(cov)
    low = _optimise(lambda w: w @ cov @ w, len(mu), bounds)
    high = _optimise(lambda w: -(w @ mu), len(mu), bounds)
    rows = []
    for target in np.linspace(low @ mu, high @ mu, points):
        w = _optimise(lambda w: w @ cov @ w, len(mu), bounds, [{"type": "eq", "fun": lambda w, t=target: w @ mu - t}])
        rows.append({"return": float(w @ mu), "volatility": float(np.sqrt(w @ cov @ w))})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 9. simulation with NumPy
def simulate_normal(mu: np.ndarray, cov: np.ndarray, n_sims: int, horizon: int, rng: np.random.Generator) -> np.ndarray:
    """Correlated normal returns, shape (n_sims, horizon, assets). The Cholesky factor keeps the correlation."""
    chol = np.linalg.cholesky(cov)
    return rng.standard_normal((n_sims, horizon, len(mu))) @ chol.T + mu


def block_bootstrap(history: np.ndarray, n_sims: int, horizon: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """Resample runs of real history, wrapping at the end. Whole days keep fat tails and co-movement."""
    n_blocks = -(-horizon // block)    # ceiling division
    starts = rng.integers(0, len(history), size=(n_sims, n_blocks))
    index = (starts[:, :, None] + np.arange(block)) % len(history)
    return history[index.reshape(n_sims, -1)[:, :horizon]]


def ewma_covariance(returns: np.ndarray, lam: float = 0.94, seed_days: int = 60) -> np.ndarray:
    """RiskMetrics covariance: recent days count more, so it reflects today's volatility."""
    s = np.cov(returns[:seed_days].T)
    for day in returns[seed_days:]:
        s = lam * s + (1 - lam) * np.outer(day, day)
    return s


def wealth_paths(risky_returns: np.ndarray, y: float, rf_period: float) -> np.ndarray:
    """Growth of 1 with y in P and 1 - y in T-bills, rebalanced each period. Shape (n_sims, horizon + 1)."""
    growth = np.cumprod(1 + y * risky_returns + (1 - y) * rf_period, axis=1)
    return np.hstack([np.ones((risky_returns.shape[0], 1)), growth])


def risk_summary(wealth: np.ndarray, amount: float) -> dict:
    """Percentiles, VaR, CVaR and the chance of loss, from the final value of every path."""
    gain = wealth[:, -1] - 1
    cutoff = np.percentile(gain, 5)
    return {"median": float(np.percentile(wealth[:, -1], 50) * amount), "p5": float(np.percentile(wealth[:, -1], 5) * amount),
            "p95": float(np.percentile(wealth[:, -1], 95) * amount), "var_95": float(-cutoff * amount),
            "cvar_95": float(-gain[gain <= cutoff].mean() * amount), "prob_loss": float((gain < 0).mean())}


def glide_path(start: float, end: float, months: int) -> np.ndarray:
    """The target share in equity each month, falling in a straight line; flat if end is not below start."""
    return np.full(months, start) if end >= start else np.linspace(start, end, months)


def sip_contributions(monthly: float, step_up: float, months: int) -> np.ndarray:
    return monthly * (1 + step_up) ** (np.arange(months) // 12)


def simulate_sip(risky_returns: np.ndarray, equity_target: np.ndarray, debt_return: float, amounts: np.ndarray,
                 rebalance_every: int = 12) -> np.ndarray:
    """Final corpus of each path: invest at the start of the month, then earn that month's return."""
    n_sims, months = risky_returns.shape
    equity, debt = np.zeros(n_sims), np.zeros(n_sims)
    for t in range(months):
        equity += amounts[t] * equity_target[t]
        debt += amounts[t] * (1 - equity_target[t])
        equity *= 1 + risky_returns[:, t]
        debt *= 1 + debt_return
        if (t + 1) % rebalance_every == 0 and t + 1 < months:
            total = equity + debt
            equity, debt = total * equity_target[t + 1], total * (1 - equity_target[t + 1])
    return equity + debt


def run_simulations(daily: pd.DataFrame, monthly: pd.DataFrame, capm: np.ndarray, weights: np.ndarray, rf: float, erp: float,
                    mc: dict, sip: dict) -> dict:
    """One-year and SIP draws, with the pipeline's seed and order, reduced to portfolio-level returns."""
    rng = np.random.default_rng(mc["seed"])
    stocks = daily[STOCKS]
    n, horizon = mc["n_sims"], mc["horizon_days"]
    target = capm / TRADING_DAYS
    one_year = {"Parametric": simulate_normal(target, stocks.cov().to_numpy(), n, horizon, rng) @ weights}
    recentred = stocks.to_numpy() - stocks.to_numpy().mean(axis=0) + target
    one_year["Bootstrap"] = block_bootstrap(recentred, n, horizon, mc["bootstrap_block_days"], rng) @ weights
    ewma = ewma_covariance(stocks.to_numpy(), mc["ewma_lambda"])
    one_year["Parametric, today's volatility"] = simulate_normal(target, ewma, n, horizon, rng) @ weights

    # The SIP's equity sleeve is an index core plus the three stocks.
    four = STOCKS + [BENCHMARK]
    months = sip["years"] * 12
    core = sip["core_index_share"]
    sleeve = np.append((1 - core) * weights, core)
    mu_monthly = np.append(capm, rf + erp) / 12
    cov_monthly = daily[four].cov().to_numpy() * TRADING_DAYS / 12
    history = (monthly[four].to_numpy() - monthly[four].to_numpy().mean(axis=0) + mu_monthly) @ sleeve
    sip_draws = {"Parametric": simulate_normal(mu_monthly, cov_monthly, n, months, rng) @ sleeve}
    sip_draws["Bootstrap"] = block_bootstrap(history, n, months, sip["bootstrap_block_months"], rng)
    return {"one_year": one_year, "sip": sip_draws}


# ------------------------------------------------------------------ 10. market efficiency: loops over dates and signals
def rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's relative strength index, 0 to 100."""
    change = prices.diff()
    gain = change.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1 / window, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def trend_signal(prices: pd.Series, fast: int = 50, slow: int = 200) -> pd.Series:
    """1 when the 50-day average is above the 200-day average, else 0."""
    fast_ma, slow_ma = prices.rolling(fast).mean(), prices.rolling(slow).mean()
    return (fast_ma > slow_ma).astype(float).where(slow_ma.notna())


def rsi_signal(prices: pd.Series, buy_below: float = 30, sell_above: float = 50) -> pd.Series:
    """Hold from an RSI dip below 30 until it recovers above 50. The state carries across the loop."""
    holding, signal = 0.0, []
    for value in rsi(prices):
        if np.isnan(value):
            signal.append(np.nan)
            continue
        if holding == 0 and value < buy_below:
            holding = 1.0
        elif holding == 1 and value > sell_above:
            holding = 0.0
        signal.append(holding)
    return pd.Series(signal, index=prices.index)


def rule_sharpes(prices: pd.Series, rf: float, cost_one_way: float = 0.00125) -> dict[str, float]:
    """Sharpe of buy-and-hold and of each rule, on the same dates, after costs. Signals use yesterday's close."""
    daily_rf = periodic_rf(rf)
    change = prices.pct_change(fill_method=None)
    results = {}
    for name, signal in (("Trend (50/200 DMA)", trend_signal(prices)), ("RSI mean reversion", rsi_signal(prices))):
        position = signal.shift(1)
        rule = position * change + (1 - position) * daily_rf - position.diff().abs().fillna(0) * cost_one_way
        results[name] = rule[position.notna()].dropna()
    start = max(r.index[0] for r in results.values())
    out = {"Buy and hold": float(sharpe_ratio(change.loc[start:].dropna(), rf))}
    out.update({name: float(sharpe_ratio(r.loc[start:], rf)) for name, r in results.items()})
    return out


def event_study(stock: pd.Series, market: pd.Series, dates: list[str], estimation: int = 250) -> list[dict]:
    """Abnormal return over days -1 to +1 around each results date, from a market model fitted on the prior year."""
    both = pd.concat({"s": stock, "m": market}, axis=1).dropna()
    rows = []
    for date in dates:
        pos = both.index.searchsorted(pd.Timestamp(date))
        if pos - estimation - 1 < 0 or pos + 1 >= len(both):
            continue    # too close to either end of the sample
        fit = both.iloc[pos - estimation - 1: pos - 1]
        slope = np.cov(fit["s"], fit["m"])[0, 1] / fit["m"].var()
        intercept = fit["s"].mean() - slope * fit["m"].mean()
        window = both.iloc[pos - 1: pos + 2]
        rows.append({"date": date, "car": float((window["s"] - intercept - slope * window["m"]).sum())})
    return rows


# ------------------------------------------------------------------ 11. text: sets, FinBERT, a live model
# Hedging words of the kind in Loughran & McDonald's (2011) Uncertainty list. A set makes each lookup instant.
HEDGE_WORDS = {"may", "might", "could", "approximately", "uncertain", "uncertainty", "possibly", "perhaps", "appears",
               "believe", "believes", "estimate", "estimates", "assume", "assumes", "depends", "roughly", "somewhat"}


def hedge_share(text: str) -> float:
    words = "".join(c if c.isalpha() else " " for c in text.lower()).split()
    return sum(word in HEDGE_WORDS for word in words) / len(words) if words else 0.0


def headline_summary(news: pd.DataFrame) -> pd.DataFrame:
    """Per stock: how many headlines, their mean FinBERT tone, and the share labelled positive and negative."""
    return news.groupby("ticker").agg(headlines=("tone", "size"), mean_tone=("tone", "mean"),
                                      positive=("label", lambda s: (s == "positive").mean()),
                                      negative=("label", lambda s: (s == "negative").mean()))


def finbert_tone(texts: list[str]) -> list[float]:
    """Tone = P(positive) - P(negative) from FinBERT. Downloads the model the first time it runs."""
    from transformers import pipeline

    classify = pipeline("text-classification", model="ProsusAI/finbert", top_k=None, truncation=True, max_length=128)
    return [next(d["score"] for d in row if d["label"] == "positive") - next(d["score"] for d in row if d["label"] == "negative")
            for row in classify(texts)]


def ask_model(question: str, context: str, model: str = "nvidia/nemotron-3-super-120b-a12b:free") -> str | None:
    """A question to a free OpenRouter model, answered from `context` only. None if no API key is set.

    The approved proposal listed the Anthropic SDK as optional; the project's live chat uses this free
    route instead, and the model never produces a number that the context does not hold.
    """
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    import requests

    system = "Answer only from the JSON context. If it does not hold the answer, say so. Context: " + context
    try:
        reply = requests.post("https://openrouter.ai/api/v1/chat/completions", timeout=60,
                              headers={"Authorization": f"Bearer {key}"},
                              json={"model": model, "messages": [{"role": "system", "content": system},
                                                                 {"role": "user", "content": question}]})
        reply.raise_for_status()
        return reply.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError) as err:
        raise DataError(f"the live model did not answer: {err}") from err


# ------------------------------------------------------------------ 12. charts: Matplotlib and Seaborn
def save_charts(folder: Path, daily: pd.DataFrame, frontier: pd.DataFrame, portfolio: Portfolio, rf: float, fan_wealth: np.ndarray) -> list[Path]:
    """A Seaborn correlation heatmap and Matplotlib charts of the frontier and the one-year fan."""
    import matplotlib

    matplotlib.use("Agg")   # draw to files; no window is needed
    import matplotlib.pyplot as plt
    import seaborn as sns

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    saved = []

    fig, ax = plt.subplots(figsize=(5, 4))
    names = daily.rename(columns=SHORT)
    sns.heatmap(names.corr(), annot=True, fmt=".2f", cmap="Blues", vmin=0, vmax=1, square=True, ax=ax)
    ax.set(xlabel="", ylabel="", title="Correlation of daily returns, 2016-2026")
    saved.append(folder / "correlation_heatmap.png")
    fig.savefig(saved[-1], dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(frontier["volatility"], frontier["return"], label="Efficient frontier")
    top = 0.30
    ax.plot([0, top], [rf, rf + portfolio.sharpe(rf) * top], linestyle="--", label="Capital allocation line")
    ax.scatter([portfolio.volatility], [portfolio.expected_return], zorder=3, label="Tangency portfolio P")
    for s in portfolio.securities:
        ax.annotate(s.name, (s.volatility, s.expected_return), textcoords="offset points", xytext=(6, 4))
        ax.scatter([s.volatility], [s.expected_return], color="grey", zorder=3)
    ax.set(xlim=(0, 0.36), xlabel="Volatility", ylabel="Expected return", title="Forward-looking (CAPM) frontier")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.legend(frameon=False)
    saved.append(folder / "frontier.png")
    fig.savefig(saved[-1], dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    days = np.arange(fan_wealth.shape[1])
    bands = {p: np.percentile(fan_wealth, p, axis=0) for p in (5, 25, 50, 75, 95)}
    ax.fill_between(days, bands[5], bands[95], alpha=0.2, label="5th to 95th percentile")
    ax.fill_between(days, bands[25], bands[75], alpha=0.35, label="25th to 75th percentile")
    ax.plot(days, bands[50], label="Median")
    ax.set(xlabel="Trading day", ylabel="Growth of 1", title="One year ahead, 10,000 simulated paths")
    ax.legend(frameon=False)
    saved.append(folder / "fan.png")
    fig.savefig(saved[-1], dpi=150, bbox_inches="tight")
    plt.close(fig)
    return saved


# ------------------------------------------------------------------ 13. putting it together
@dataclass
class Project:
    """Everything the tour and the Streamlit view need, loaded once."""
    settings: dict
    rf: float
    erp: float
    daily: pd.DataFrame
    monthly: pd.DataFrame
    portfolio: Portfolio
    capm: np.ndarray


def load_project(folder: Path = DATA) -> Project:
    settings = read_settings()
    rf, erp = settings["market"]["risk_free_rate"], settings["market"]["equity_risk_premium"]
    four = STOCKS + [BENCHMARK]
    daily = read_returns(folder / "returns_daily.parquet", four)
    monthly = read_returns(folder / "returns_monthly.parquet", four)
    table = metrics_table(daily, BENCHMARK, rf, erp)
    capm = table.loc[STOCKS, "capm_required_return"].to_numpy()
    cov = daily[STOCKS].cov().to_numpy() * TRADING_DAYS
    securities = [Security(t, SHORT[t], table.at[t, "beta"], table.at[t, "capm_required_return"], table.at[t, "volatility"])
                  for t in STOCKS]
    return Project(settings, rf, erp, daily, monthly, Portfolio(securities, max_sharpe_weights(capm, cov, rf), cov), capm)


def check(label: str, mine: float, theirs: float, tol: float) -> None:
    print(f"    {label:<46} {mine:>12.6f}  vs {theirs:>12.6f}  {'OK' if abs(mine - theirs) <= tol else 'DIFFERS'}")


def tour(charts: Path | None = None, fetch: bool = False, finbert: bool = False, pdf: Path | None = None) -> None:
    """Run every section on the real data and check each result against the pipeline's frozen files."""
    project = load_project()
    rf, portfolio = project.rf, project.portfolio
    frozen = read_json(DATA / "portfolio.json")
    mc_file, sip_file = read_json(DATA / "mc.json"), read_json(DATA / "sip.json")

    print("\n1. DATA: files read and validated")
    print(f"    {len(project.daily)} days of returns, {project.daily.index[0].date()} to {project.daily.index[-1].date()}")
    try:
        read_returns(DATA / "does_not_exist.parquet", STOCKS)
    except DataError as err:
        print(f"    A missing file is caught, not ignored: {err}")

    print("\n2. RISK AND RETURN: Pandas, 2016 to date")
    table = metrics_table(project.daily, BENCHMARK, rf, project.erp)
    print(table.rename(index=SHORT)[["cagr", "volatility", "sharpe", "beta", "treynor", "jensen_alpha"]].round(3).to_string())
    pipeline_table = read_metrics_csv(DATA / "metrics_table.csv")
    check("ICICI Sharpe vs the pipeline's CSV", table.at["ICICIBANK.NS", "sharpe"], pipeline_table.at["ICICI Bank", "sharpe"], 1e-5)

    print("\n3. VALUATION: inheritance and recursion, against the Excel workbook")
    summary = pd.read_excel(WORKBOOK, sheet_name="Summary").set_index("ticker")
    for ticker, model in load_models().items():
        print(f"  {model.name} ({type(model).__name__})")
        check("Recursive value vs Excel (Rs)", model.intrinsic_value(), summary.at[ticker, "intrinsic_value"], 0.01)
        check("Recursive value vs closed form (Rs)", model.intrinsic_value(), model.closed_form_value(), 0.01)
        check("Bisection implied growth vs algebra", model.implied_growth(), model.implied_growth_closed_form(), 1e-6)
    try:
        DividendDiscountModel("Bad input", 100.0, r=0.05, g2=0.06, n=5, d0=1.0, g1=0.05)
    except ValueError as err:
        print(f"    Bad inputs are refused: {err}")

    print("\n4. THE OPTIMAL RISKY PORTFOLIO: SciPy, checked by exhaustive search")
    mine = dict(zip(STOCKS, portfolio.weights))
    for t in STOCKS:
        check(f"{SHORT[t]} weight vs portfolio.json", mine[t], frozen["views"]["forward"]["tangency"]["weights"][t], 1e-4)
    grid_w, grid_sharpe = grid_search_max_sharpe(project.capm, portfolio.covariance, rf)
    check("SciPy Sharpe vs 1% grid search", portfolio.sharpe(rf), grid_sharpe, 1e-3)
    print(f"    Grid search best: {', '.join(f'{SHORT[t]} {w:.0%}' for t, w in zip(STOCKS, grid_w))}")
    print("    Securities ranked by Sharpe (sorted with a key): "
          + ", ".join(f"{s.name} {s.sharpe(rf):.2f}" for s in portfolio.ranked(lambda s: s.sharpe(rf))))

    print("\n5. THE INVESTOR: questionnaire -> A -> rupees")
    middle = Investor.from_answers("Middle answers", {key: 3 for key in QUESTIONS})
    print(f"    Answering 3 to all ten questions gives A = {middle.risk_aversion:g} ({middle.profile})")
    for name, value in portfolio.allocation(middle, rf).items():
        print(f"    {name:<12} {rupees(value):>12}")
    cp = portfolio.complete(middle, rf)
    check("A = 4 share in P vs portfolio.json", cp["y"], frozen["profiles"]["Balanced"]["y"], 1e-4)

    print("\n6. SIMULATION: NumPy, 10,000 paths, the pipeline's seed and order")
    draws = run_simulations(project.daily, project.monthly, project.capm, portfolio.weights, rf, project.erp,
                            project.settings["monte_carlo"], project.settings["sip"])
    rf_d, rf_m = periodic_rf(rf), periodic_rf(rf, 12)
    wealth = wealth_paths(draws["one_year"]["Parametric"], cp["y"], rf_d)
    one = risk_summary(wealth, 100_000)
    check("95% VaR vs mc.json (Rs)", one["var_95"], mc_file["results"]["Parametric"]["Balanced"]["var_95"], 25)
    sip = project.settings["sip"]
    months = sip["years"] * 12
    amounts = sip_contributions(sip["monthly_amount"], sip["annual_step_up"], months)
    corpus = simulate_sip(draws["sip"]["Parametric"], glide_path(cp["y"], sip["glide_path_end_equity"], months), rf_m, amounts)
    check("SIP median vs sip.json (Rs)", float(np.median(corpus)),
          sip_file["results"]["Balanced"]["Parametric"]["terminal_percentiles"]["p50"], 2000)

    print("\n7. SORTING AND SEARCHING the simulated outcomes")
    outcomes = list(wealth[:, -1] * 100_000)
    ordered = merge_sort(outcomes[:2000])
    check("Own merge sort vs Python's sorted (median)", percentile(ordered, 50), float(np.percentile(outcomes[:2000], 50)), 1e-6)
    worst, best = Portfolio.best_and_worst(outcomes, 3)
    print(f"    Worst three: {', '.join(rupees(x) for x in worst)}")
    print(f"    Best three:  {', '.join(rupees(x) for x in best)}")
    print(f"    Binary search: {binary_search(sorted(outcomes), 100_000) / len(outcomes):.1%} of paths end below Rs 1,00,000")

    print("\n8. MARKET EFFICIENCY: can past prices beat buy-and-hold?")
    prices = pd.read_parquet(DATA / "prices.parquet")
    beaten = total = 0
    for ticker in STOCKS + [BENCHMARK]:
        sharpes = rule_sharpes(prices[ticker].dropna(), rf)
        hold = sharpes.pop("Buy and hold")
        beaten += sum(value > hold for value in sharpes.values())
        total += len(sharpes)
    print(f"    {beaten} of {total} trading rules beat buy-and-hold on Sharpe, after costs")
    consensus = read_json(DATA / "consensus.json")
    cars = [row["car"] for t in STOCKS
            for row in event_study(project.daily[t], project.daily[BENCHMARK], [s["date"] for s in consensus[t]["surprises"]])]
    print(f"    Event study: {len(cars)} results dates, mean absolute 3-day reaction {np.mean(np.abs(cars)):.1%}")

    print("\n9. TEXT: headlines already scored by FinBERT")
    print(headline_summary(pd.read_parquet(DATA / "news_scored.parquet")).rename(index=SHORT).round(3).to_string())
    print(f"    Hedge share of a sample sentence: {hedge_share('Margins may recover, but demand could remain uncertain.'):.0%}")

    if charts:
        frontier = efficient_frontier(project.capm, portfolio.covariance)
        print("\n10. CHARTS saved:", ", ".join(str(p) for p in save_charts(charts, project.daily[STOCKS], frontier, portfolio, rf, wealth)))
    if fetch:
        fresh = download_prices(STOCKS + [BENCHMARK], start="2026-01-01")
        print(f"\nFresh prices downloaded, last date {fresh.index[-1].date()}:\n{fresh.tail(1).round(2).to_string()}")
    if finbert:
        samples = ["Sun Pharma beats estimates as India sales grow strongly", "HUL margins fall as input costs rise"]
        for text, tone in zip(samples, finbert_tone(samples)):
            print(f"\nFinBERT tone {tone:+.2f}: {text}")
    if pdf:
        print(f"\nFirst 300 characters of {pdf}:\n{read_pdf_text(pdf)[:300]}")


# ------------------------------------------------------------------ 14. a small interactive demo: Streamlit
def streamlit_view() -> None:
    import streamlit as st

    st.set_page_config(page_title="Python project demo", layout="wide")
    st.title("Behaviour-aware portfolio construction")
    st.caption("Every number below comes from python_project.py. Coursework, not investment advice.")

    @st.cache_resource(show_spinner="Simulating 10,000 market paths...")
    def setup():
        project = load_project()
        return project, run_simulations(project.daily, project.monthly, project.capm, project.portfolio.weights, project.rf,
                                        project.erp, project.settings["monte_carlo"], project.settings["sip"])

    project, draws = setup()
    left, right = st.columns(2)
    A = left.slider("Risk aversion A", 0.5, 10.0, 4.0, 0.25)
    amount = right.number_input("Amount to invest (Rs)", 1000, 10_000_000, 100_000, 10_000)
    investor = Investor("You", A, amount)
    split = project.portfolio.allocation(investor, project.rf)
    complete = project.portfolio.complete(investor, project.rf)
    summary = risk_summary(wealth_paths(draws["one_year"]["Parametric"], complete["y"], periodic_rf(project.rf)), amount)

    c = st.columns(4)
    c[0].metric("Profile", investor.profile)
    c[1].metric("Share in P", f"{complete['y']:.0%}")
    c[2].metric("Median after one year", rupees(summary["median"]))
    c[3].metric("95% VaR", rupees(summary["var_95"]))
    st.bar_chart(pd.Series(split, name="Rupees"))

    st.subheader("Valuation: recursive value and bisection, against their closed forms")
    st.dataframe(pd.DataFrame([{"Stock": m.name, "Model": type(m).__name__, "Price": m.price, "Recursive value": m.intrinsic_value(),
                                "Closed form": m.closed_form_value(), "Implied growth (bisection)": m.implied_growth(),
                                "Implied growth (algebra)": m.implied_growth_closed_form()} for m in load_models().values()]).round(4),
                 hide_index=True)


def running_in_streamlit() -> bool:
    try:
        from streamlit.runtime import exists
    except ImportError:
        return False
    return exists()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--charts", type=Path, help="folder for the Matplotlib and Seaborn charts")
    parser.add_argument("--fetch", action="store_true", help="also download fresh prices with yfinance")
    parser.add_argument("--finbert", action="store_true", help="also score sample headlines with FinBERT")
    parser.add_argument("--pdf", type=Path, help="also read this PDF with pypdf")
    args = parser.parse_args()
    try:
        tour(args.charts, args.fetch, args.finbert, args.pdf)
    except DataError as err:
        print(f"\nStopped: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if running_in_streamlit():
        streamlit_view()
    else:
        sys.exit(main())
