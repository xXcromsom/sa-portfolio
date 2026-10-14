"""SAPF: a terminal-style dashboard for the HUL / Sun Pharma / ICICI Bank portfolio.

Flow: a 10-question risk questionnaire sets the investor's risk aversion A, then the terminal
shows the complete portfolio for that A and amount: the split between the optimal risky
portfolio P and T-bills, in rupees, with a live Monte Carlo, SIP projection and stress tests.

Everything is computed from files on disk (data/submission or data/latest), with the same
simulation draws as the pipeline (src/scenario.py), so at the report's A values the numbers
match the report exactly. Run locally with:  streamlit run app.py
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src import config  # noqa: F401  (loads .env and the antivirus CA bundle, if any)
from src import chat
from src import questionnaire as quiz
from src import scenario
from src import terminal as T
from src.portfolio import complete_portfolio

ROOT = Path(__file__).resolve().parent
DATASETS = {"SUBMISSION": ROOT / "data" / "submission", "LATEST": ROOT / "data" / "latest"}
STOCKS, BENCH = ["HINDUNILVR.NS", "SUNPHARMA.NS", "ICICIBANK.NS"], "^NSEI"
NAMES = {"HINDUNILVR.NS": "Hindustan Unilever", "SUNPHARMA.NS": "Sun Pharma", "ICICIBANK.NS": "ICICI Bank",
         BENCH: "Nifty 50"}
SHORT = {"HINDUNILVR.NS": "HUL", "SUNPHARMA.NS": "Sun Pharma", "ICICIBANK.NS": "ICICI Bank", BENCH: "Nifty 50"}
TICKER = {"HINDUNILVR.NS": "HUVR IN", "SUNPHARMA.NS": "SUNP IN", "ICICIBANK.NS": "ICICIBC IN", BENCH: "NIFTY"}
COLOR = {"HINDUNILVR.NS": T.CYAN, "SUNPHARMA.NS": T.VIOLET, "ICICIBANK.NS": T.AMBER, "T-bills": T.GREY}
MAX_LEVERAGE = 2.0  # with borrowing on: y <= 200% of savings in P

st.set_page_config(page_title="SAPF | Security Analysis Portfolio", page_icon="📈", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(T.CSS, unsafe_allow_html=True)
ss = st.session_state


def H(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def chart(c: alt.Chart, height: int = 300) -> None:
    st.altair_chart(T.style(c, height), theme=None, width="stretch")


def secret(name: str) -> str | None:
    """Environment variable (or .env) first, then Streamlit secrets; None if neither exists."""
    if os.getenv(name):
        return os.getenv(name)
    try:
        return st.secrets.get(name)
    except Exception:  # Streamlit raises when no secrets.toml exists
        return None


# ---------------------------------------------------------------- data
def _stamp(folder: Path) -> str:
    """Change token for the caches: newest modification time in the folder."""
    return str(max((p.stat().st_mtime for p in folder.rglob("*") if p.is_file()), default=0))


@st.cache_data(show_spinner=False)
def load(folder: str, stamp: str) -> dict:
    f = Path(folder)
    read = lambda name: json.loads((f / name).read_text(encoding="utf-8"))  # noqa: E731
    data = {k: read(n) for k, n in [("metrics", "metrics.json"), ("valuation", "valuation.json"),
                                      ("portfolio", "portfolio.json"), ("mc", "mc.json"), ("sip", "sip.json"),
                                      ("ai", "ai_analysis.json"), ("sentiment", "sentiment.json"),
                                      ("extraction", "extraction_accuracy.json")]}
    data["aspects"] = json.loads((ROOT / "data/ai/concall_aspects.json").read_text(encoding="utf-8"))["companies"]
    data["qa"] = json.loads((ROOT / "data/ai/qa_cache.json").read_text(encoding="utf-8"))
    for key, name in [("prices", "prices.parquet"), ("daily", "returns_daily.parquet"),
                      ("monthly", "returns_monthly.parquet")]:
        data[key] = pd.read_parquet(f / name)
    return data


@st.cache_resource(show_spinner="Simulating 10,000 market paths...", max_entries=2)
def draws(folder: str, stamp: str) -> dict:
    """The pipeline's own Monte Carlo and SIP draws, reduced to P level (cached; ~90 MB)."""
    D = load(folder, stamp)
    fwd = D["portfolio"]["views"]["forward"]
    capm = np.array([fwd["expected_returns"][t] for t in STOCKS])
    w_p = np.array([fwd["tangency"]["weights"][t] for t in STOCKS])
    a = D["metrics"]["assumptions"]
    return scenario.dashboard_draws(D["daily"], D["monthly"], STOCKS, BENCH, capm, w_p,
                                    D["portfolio"]["risk_free_rate"], a["equity_risk_premium"],
                                    D["mc"]["settings"], D["sip"]["settings"], a["periods_per_year"])


def profile_label(a: float) -> str:
    if a > 0:
        return quiz.profile_name(a).upper()
    return "RISK-NEUTRAL" if a == 0 else "RISK-SEEKING"


# ---------------------------------------------------------------- onboarding
def _start(a: float, source: str, result: quiz.Result | None = None) -> None:
    ss["A"] = float(a)
    ss["a_source"], ss["quiz_result"] = source, result
    ss["amount"] = int(ss.get("ob_amount", 100000))
    ss["sip_amount"] = int(ss.get("ob_sip", 10000))


def _submit_quiz() -> None:
    chosen = {key: ss.get(f"q_{key}") for key, *_ in quiz.QUESTIONS}
    missing = [str(i) for i, (key, *_) in enumerate(quiz.QUESTIONS, 1) if chosen[key] is None]
    if missing:
        ss["quiz_error"] = f"Answer all 10 questions first (missing: {', '.join(missing)})."
        return
    ss.pop("quiz_error", None)
    answers = {key: options.index(chosen[key]) + 1 for key, _, _, options in quiz.QUESTIONS}
    ss["quiz_answers"] = answers
    result = quiz.score(answers)
    _start(result.risk_aversion, "questionnaire", result)


def _start_manual() -> None:
    _start(round(float(ss.get("ob_manual_a", 4.0)) * 4) / 4, "manual")


def _retake() -> None:
    for k in ("A", "quiz_result", "quiz_answers", "a_source"):
        ss.pop(k, None)


def onboarding() -> None:
    H(T.bar(['<span class="go">SAPF &lt;GO&gt;</span>', "HUL · SUN PHARMA · ICICI BANK",
             "STEP 1 OF 2: RISK PROFILE"]))
    H(T.head("Risk profile questionnaire", "10 questions → your risk aversion A → your optimal portfolio"))
    left, right = st.columns([3, 2], gap="large")
    with left:
        with st.form("quiz", border=False):
            for i, (key, kind, question, options) in enumerate(quiz.QUESTIONS, 1):
                st.radio(f"{i:02d} · {question}", options, index=None, key=f"q_{key}", horizontal=True,
                         help="Capacity: can you afford risk?" if kind == "capacity" else "Willingness: do you want risk?")
            c1, c2 = st.columns(2)
            c1.number_input("Amount to invest today (₹)", min_value=1000, value=int(ss.get("amount", 100000)),
                            step=10000, key="ob_amount")
            c2.number_input("Monthly SIP (₹)", min_value=1000, value=int(ss.get("sip_amount", 10000)),
                            step=1000, key="ob_sip")
            st.form_submit_button("BUILD MY PORTFOLIO ▶", type="primary", on_click=_submit_quiz, key="build")
        if ss.get("quiz_error"):
            st.error(ss["quiz_error"])
    with right:
        H(T.head("How your answers become a portfolio"))
        H(T.table(["Step", "What happens"], [
            ["1", "Capacity (4 questions) and willingness (6) are each scored 0–1."],
            ["2", "Each score maps to A: 0 → 8, 0.5 → 4, 1 → 1.5. The higher (more cautious) A wins."],
            ["3", "Your share in P is y* = (E[rP] − rf) / (A·σP²), capped at 100% (no borrowing)."],
            ["4", "P is the same for everyone: HUL, Sun Pharma, ICICI at the tangency weights. A only sets y."],
        ], text=True))
        H(T.head("Reading A", "U = E(r) − ½·A·σ²"))
        H(T.table(["A", "Meaning"], [["> 0", "Risk-averse: risk lowers utility (most people: 2–6)"],
                                       ["= 0", "Risk-neutral: only the expected return matters"],
                                       ["< 0", "Risk-seeking: risk itself adds utility"]], text=True))
        H(T.head("Or skip the questionnaire"))
        st.button("SKIP · USE BALANCED (A = 4)", on_click=_start, args=(4.0, "skipped"), width="stretch", key="skip")
        st.number_input("Enter your own A", min_value=-2.0, max_value=10.0, value=4.0, step=0.25, key="ob_manual_a")
        st.button("USE THIS A ▶", on_click=_start_manual, width="stretch", key="manual_a")


# ---------------------------------------------------------------- terminal
def terminal() -> None:
    available = {k: v for k, v in DATASETS.items() if (v / "metrics.json").exists()}
    if ss.get("dataset") not in available:
        ss["dataset"] = next(iter(available))
    ss.setdefault("amount", 100000)
    ss.setdefault("sip_amount", 10000)
    ss.setdefault("borrow", False)
    folder = available[ss["dataset"]]
    stamp = _stamp(folder)
    D, S = load(str(folder), stamp), draws(str(folder), stamp)
    A, amount, sip_amount, borrow = float(ss["A"]), float(ss["amount"]), float(ss["sip_amount"]), bool(ss["borrow"])

    fwd = D["portfolio"]["views"]["forward"]
    P, mkt, rf = fwd["tangency"], fwd["market"], D["portfolio"]["risk_free_rate"]
    cp = complete_portfolio(P["expected_return"], P["volatility"], rf, A, borrow, MAX_LEVERAGE)
    y = cp["y"]
    threshold = (P["expected_return"] - rf) / P["volatility"] ** 2  # A at which y* = 100%
    alloc = {t: y * P["weights"][t] * amount for t in STOCKS}
    tbills = (1 - y) * amount
    one = {m: scenario.one_year_outcome(S["one_year"][m], y, S["rf_daily"], amount) for m in scenario.ONE_YEAR_MODES}
    sip_s = D["sip"]["settings"]
    sipo = {m: scenario.sip_outcome(S["sip"][m], y, S["rf_monthly"], sip_amount, sip_s) for m in scenario.SIP_MODES}
    as_of = D["metrics"]["as_of"]
    prof = profile_label(A)

    # ------------------------------------------------ command bar, tape, controls
    H(T.bar(['<span class="go">SAPF &lt;GO&gt;</span>', "HUL · SUN PHARMA · ICICI BANK",
             f"AS OF {date.fromisoformat(as_of):%d %b %Y}".upper(), f"DATA: {ss['dataset']}",
             f"PROFILE: {prof} · A = {A:.2f}", f"INVESTED {T.inr(amount)} + {T.inr(sip_amount)}/MO"]))
    px = D["prices"]
    rows = []
    for t in STOCKS + [BENCH]:
        p = px[t].dropna()
        rows.append((TICKER[t], float(p.iloc[-1]), float(p.iloc[-1] / p.iloc[-2] - 1),
                     float(p.iloc[-1] / p.iloc[-min(253, len(p))] - 1)))
    H(T.tape(rows))
    c = st.columns([3, 2, 2, 2, 2])
    c[0].slider("Risk aversion A", -2.0, 10.0, step=0.25, key="A",
                help="U = E(r) − ½Aσ². Higher A = more cautious. A ≤ 0 is risk-neutral or risk-seeking.")
    c[1].number_input("Invest today (₹)", min_value=1000, step=10000, key="amount")
    c[2].number_input("Monthly SIP (₹)", min_value=1000, step=1000, key="sip_amount")
    c[3].radio("Data", list(available), key="dataset", horizontal=True,
               help="SUBMISSION = the numbers in our report. LATEST = refreshed each weekday evening.")
    c[4].toggle("Allow borrowing", key="borrow", help=f"Borrow at the T-bill rate, up to y = {MAX_LEVERAGE:.0%}.")
    age = (date.today() - date.fromisoformat(as_of)).days
    if ss["dataset"] == "LATEST" and age > 4:
        H(T.warn(f"LATEST data is {age} days old: the nightly refresh may have failed."))

    tabs = st.tabs(["1 PORTFOLIO", "2 COMPANIES", "3 AI", "4 RISK", "5 ASK", "6 PROFILE"])
    with tabs[0]:
        portfolio_tab(D, P, mkt, rf, cp, alloc, tbills, one, sipo, threshold, amount, sip_amount, borrow, A)
    with tabs[1]:
        companies_tab(D, rf)
    with tabs[2]:
        ai_tab(D)
    with tabs[3]:
        risk_tab(D, y, amount)
    with tabs[4]:
        ask_tab(D, {"risk_aversion_A": A, "profile": prof, "share_in_P_y": y, "amount_invested": amount,
                    "rupees": {**{NAMES[t]: v for t, v in alloc.items()}, "T-bills": tbills},
                    "expected_return": cp["expected_return"], "volatility": cp["volatility"],
                    "certainty_equivalent": cp["certainty_equivalent"],
                    "one_year": {m: {k: o[0][k] for k in ("var_95", "cvar_95", "prob_loss", "terminal_percentiles")}
                                 for m, o in one.items()},
                    "sip": {"monthly_amount": sip_amount, **{m: o[0] for m, o in sipo.items()}}})
    with tabs[5]:
        profile_tab(A, threshold)
    H(T.note("Coursework, not investment advice. Sources: Yahoo Finance, Screener.in, BSE filings, RBI, MOSPI, "
             "Damodaran, Google News. Simulations: 10,000 paths, same draws as the report."))


# ---------------------------------------------------------------- 1 portfolio
def portfolio_tab(D, P, mkt, rf, cp, alloc, tbills, one, sipo, threshold, amount, sip_amount, borrow, A) -> None:
    y = cp["y"]
    par = one["Parametric"][0]
    kp = T.kpis([("Invested today", T.inr(amount), f"+ {T.inr(sip_amount)} a month by SIP"),
                 ("In stocks (P)", T.pct(y, 0), T.inr(sum(alloc.values()))),
                 ("In T-bills" if tbills >= 0 else "Borrowed", T.pct(abs(1 - y), 0), T.inr(abs(tbills))),
                 ("Expected return", T.pct(cp["expected_return"]), f"σ {T.pct(cp['volatility'])}"),
                 ("Certainty equivalent", T.pct(cp["certainty_equivalent"]), "U = E(r) − ½Aσ²"),
                 ("1-yr median value", T.inr(par["terminal_percentiles"]["p50"]),
                  f"95% VaR {T.loss(par['var_95'])}")], big=0)
    rows = [[f'<span style="color:{COLOR[t]}">■</span> {T.esc(NAMES[t])}', TICKER[t], T.pct(P["weights"][t], 1),
             T.pct(y * P["weights"][t], 1), T.inr(alloc[t]),
             T.pct(D["portfolio"]["views"]["forward"]["expected_returns"][t]),
             f"{D['metrics']['securities'][t]['beta']:.2f}"] for t in STOCKS]
    rows.append([f'<span style="color:{T.GREY}">■</span> ' + ("T-bills (91-day)" if tbills >= 0 else "Borrowed at T-bill rate"),
                 "RBI", "–", T.pct(1 - y, 1), T.inr(tbills), T.pct(rf), "0.00"])
    rows.append(["Total", "", "100%", "100%", T.inr(amount), T.pct(cp["expected_return"]), ""])
    H(T.highlight(f"YOUR PORTFOLIO · {profile_label(A)} · A = {A:.2f}",
                  kp + T.table(["Holding", "Ticker", "Weight in P", "Weight of total", "Amount", "Exp. return", "Beta"],
                               rows, hl=set(), total={len(rows) - 1})))
    if A <= 0:
        H(T.warn(f"A = {A:.2f}: {'risk-neutral' if A == 0 else 'risk-seeking'}. Risk never lowers your utility, so "
                 f"you hold the most P allowed ({T.pct(y, 0)})."))
    elif cp["y_star"] > y + 1e-9:
        H(T.warn(f"y* = {T.pct(cp['y_star'], 0)} is above the {T.pct(y, 0)} cap: any A below {threshold:.2f} wants more "
                 f"than {'100% (switch on borrowing to go further)' if not borrow else f'{MAX_LEVERAGE:.0%}'}."))

    left, right = st.columns([3, 2], gap="medium")
    with left:
        H(T.head("Efficient frontier → CAL → your portfolio", "forward-looking (CAPM) expected returns"))
        chart(frontier_chart(D, P, mkt, rf, cp, A), 360)
    with right:
        H(T.head("Where your money goes"))
        parts = pd.DataFrame([{"holding": SHORT[t], "amount": v, "color": COLOR[t]} for t, v in alloc.items()]
                             + ([{"holding": "T-bills", "amount": tbills, "color": T.GREY}] if tbills > 0 else []))
        parts["share"] = parts.amount / parts.amount.sum()
        ring = alt.Chart(parts).encode(theta=alt.Theta("amount:Q", stack=True), order=alt.Order("holding:N"),
                                       color=alt.Color("holding:N", scale=alt.Scale(domain=list(parts.holding),
                                                                                  range=list(parts.color)),
                                                       legend=alt.Legend(title=None)))
        chart(alt.layer(
            ring.mark_arc(innerRadius=70, outerRadius=125, stroke=T.BG, strokeWidth=2).encode(
                tooltip=[alt.Tooltip("holding:N"), alt.Tooltip("amount:Q", format=",.0f", title="₹")]),
            ring.mark_text(radius=148, fontWeight="bold").encode(text=alt.Text("share:Q", format=".0%"),
                                                                color=alt.value(T.WHITE))), 330)

    H(T.head(f"One year ahead: {T.inr(amount)} invested", "10,000 simulated paths · same draws as the report"))
    H(T.table(["Method", "Median", "5th pct", "95th pct", "95% VaR", "95% CVaR", "P(loss)"],
              [[m.replace("Parametric, current volatility (EWMA)", "Parametric, today's volatility"),
                T.inr(o[0]["terminal_percentiles"]["p50"]), T.inr(o[0]["terminal_percentiles"]["p5"]),
                T.inr(o[0]["terminal_percentiles"]["p95"]), T.loss(o[0]["var_95"]), T.loss(o[0]["cvar_95"]),
                T.pct(o[0]["prob_loss"], 0)] for m, o in one.items()]))
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        chart(fan_chart(one["Parametric"][1].assign(x=lambda d: d.index), "Trading day", amount), 280)
    with c2:
        counts, edges = np.histogram(one["Parametric"][2], bins=50)
        hist = pd.DataFrame({"lo": edges[:-1], "hi": edges[1:], "n": counts})
        var_line = pd.DataFrame({"x": [amount - one["Parametric"][0]["var_95"]],
                                 "label": [f"95% VaR: {T.loss(one['Parametric'][0]['var_95'])}"]})
        x_hist = alt.X("lo:Q", title="Value after one year (₹)", scale=alt.Scale(zero=False), axis=alt.Axis(format=",.0f"))
        chart(alt.layer(
            alt.Chart(hist).mark_bar(color=T.CYAN, opacity=0.8).encode(x=x_hist, x2="hi:Q", y=alt.Y("n:Q", title="Paths"),
                                                                        y2=alt.datum(0)),
            alt.Chart(var_line).mark_rule(color=T.RED, strokeDash=[4, 3]).encode(x="x:Q"),
            alt.Chart(var_line).mark_text(color=T.RED, align="right", dx=-4).encode(x="x:Q", y=alt.value(12), text="label:N")),
            280)

    yrs = D["sip"]["settings"]["years"]
    H(T.head(f"Building it over {yrs} years: {T.inr(sip_amount)} a month, rising "
             f"{D['sip']['settings']['annual_step_up']:.0%} a year",
             f"equity = {D['sip']['settings']['core_index_share']:.0%} Nifty index fund + "
             f"{1 - D['sip']['settings']['core_index_share']:.0%} P, gliding from {T.pct(y, 0)} to "
             f"{D['sip']['settings']['glide_path_end_equity']:.0%} equity"))
    goals = D["sip"]["settings"]["goals"]
    H(T.table(["Method", "Invested", "Median corpus", "5th pct", "95th pct"] + [f"P(≥ {T.lakh(g)})" for g in goals],
              [[m, T.lakh(o[0]["total_invested"]), T.lakh(o[0]["terminal_percentiles"]["p50"]),
                T.lakh(o[0]["terminal_percentiles"]["p5"]), T.lakh(o[0]["terminal_percentiles"]["p95"])]
               + [T.pct(o[0]["prob_reach_goal"][f"{g:.0f}"], 0) for g in goals] for m, o in sipo.items()]))
    core = D["sip"]["settings"]["core_index_share"]
    first = min(y, MAX_LEVERAGE)
    split = ([["Nifty 50 index fund", T.inr(sip_amount * first * core)]]
             + [[NAMES[t], T.inr(sip_amount * first * (1 - core) * P["weights"][t])] for t in STOCKS]
             + [["Debt (T-bills / liquid fund)", T.inr(sip_amount * (1 - first))]])
    c1, c2 = st.columns([3, 1], gap="medium")
    with c1:
        fan = sipo["Parametric"][1].assign(x=lambda d: d.index / 12)
        chart(fan_chart(fan, "Years", None, invested=True), 300)
    with c2:
        H(T.head("Your first SIP instalment"))
        H(T.table(["Sleeve", "₹ / month"], split))
        H(T.note(f"Rebalanced yearly; equity glides to {D['sip']['settings']['glide_path_end_equity']:.0%} by year {yrs}. "
                 "Pre-tax, no fees."))


def fan_chart(fan: pd.DataFrame, x_title: str, start: float | None, invested: bool = False) -> alt.LayerChart:
    """Percentile bands; a one-year fan (start given) zooms in, a SIP fan starts at zero and reads in lakh."""
    base = alt.Chart(fan)
    x = alt.X("x:Q", title=x_title, axis=alt.Axis(format="d"))
    axis = (alt.Axis(format=",.0f") if start is not None
            else alt.Axis(labelExpr="format(datum.value / 100000, ',.0f') + ' L'"))
    y = alt.Y("p5:Q", title="₹", axis=axis, scale=alt.Scale(zero=start is None))
    layers = [base.mark_area(color=T.CYAN, opacity=0.18).encode(x=x, y=y, y2="p95:Q"),
              base.mark_area(color=T.CYAN, opacity=0.35).encode(x=x, y="p25:Q", y2="p75:Q"),
              base.mark_line(color=T.YELLOW, strokeWidth=2).encode(x=x, y="p50:Q")]
    if invested:
        layers.append(base.mark_line(color=T.MUTED, strokeDash=[5, 4]).encode(x=x, y="invested:Q"))
    if start is not None:
        layers.append(alt.Chart(pd.DataFrame({"y": [start]})).mark_rule(color=T.MUTED, strokeDash=[5, 4]).encode(y="y:Q"))
    return alt.layer(*layers)


def frontier_chart(D, P, mkt, rf, cp, A) -> alt.LayerChart:
    fwd = D["portfolio"]["views"]["forward"]
    front = pd.DataFrame(fwd["frontier"])[["volatility", "return"]]
    xmax = max(0.34, cp["volatility"] * 1.15)
    xs = np.linspace(0, xmax, 60)
    s_p = (P["expected_return"] - rf) / P["volatility"]
    s_m = (mkt["expected_return"] - rf) / mkt["volatility"]
    lines = pd.concat([
        front.assign(series="Efficient frontier"),
        pd.DataFrame({"volatility": xs, "return": rf + s_p * xs, "series": f"CAL: T-bills + P (Sharpe {s_p:.2f})"}),
        pd.DataFrame({"volatility": xs, "return": rf + s_m * xs, "series": f"CML: T-bills + Nifty (Sharpe {s_m:.2f})"}),
        pd.DataFrame({"volatility": xs, "return": cp["certainty_equivalent"] + 0.5 * A * xs ** 2,
                      "series": f"Your indifference curve (A = {A:.2f})"}),
    ])
    domain = list(lines.series.unique())
    vols = D["portfolio"]["volatility"]
    pts = pd.DataFrame([{"volatility": vols[t], "return": fwd["expected_returns"][t], "label": SHORT[t], "kind": "stock"}
                        for t in STOCKS]
                       + [{"volatility": mkt["volatility"], "return": mkt["expected_return"], "label": "Nifty", "kind": "stock"},
                          {"volatility": 0.0, "return": rf, "label": "T-bill", "kind": "stock"},
                          {"volatility": P["volatility"], "return": P["expected_return"], "label": "P", "kind": "P"},
                          {"volatility": cp["volatility"], "return": cp["expected_return"], "label": "YOU", "kind": "you"}])
    ylo, yhi = rf - 0.02, max(0.2, cp["expected_return"] + 0.02)
    sc_x, sc_y = alt.Scale(domain=[0, xmax]), alt.Scale(domain=[ylo, yhi])
    line = alt.Chart(lines[(lines["return"] >= ylo) & (lines["return"] <= yhi)]).mark_line(strokeWidth=2).encode(
        x=alt.X("volatility:Q", title="Volatility σ", axis=alt.Axis(format=".0%"), scale=sc_x),
        y=alt.Y("return:Q", title="Expected return", axis=alt.Axis(format=".0%"), scale=sc_y),
        color=alt.Color("series:N", scale=alt.Scale(domain=domain, range=[T.TEXT, T.AMBER, T.MUTED, T.GREEN]),
                        legend=alt.Legend(title=None, orient="top", columns=2)),
        strokeDash=alt.StrokeDash("series:N", scale=alt.Scale(domain=domain, range=[[1, 0], [1, 0], [5, 4], [2, 2]]),
                                  legend=None),
        order="volatility:Q")
    dots = alt.Chart(pts).mark_point(filled=True, size=90).encode(
        x=alt.X("volatility:Q", scale=sc_x), y=alt.Y("return:Q", scale=sc_y),
        color=alt.Color("kind:N", scale=alt.Scale(domain=["stock", "P", "you"], range=[T.CYAN, T.WHITE, T.YELLOW]), legend=None),
        shape=alt.Shape("kind:N", scale=alt.Scale(domain=["stock", "P", "you"], range=["circle", "diamond", "square"]), legend=None),
        tooltip=["label:N", alt.Tooltip("volatility:Q", format=".1%"), alt.Tooltip("return:Q", format=".1%")])
    text = alt.Chart(pts).mark_text(align="left", dx=8, dy=-8, fontWeight="bold").encode(
        x=alt.X("volatility:Q", scale=sc_x), y=alt.Y("return:Q", scale=sc_y), text="label:N",
        color=alt.Color("kind:N", scale=alt.Scale(domain=["stock", "P", "you"], range=[T.MUTED, T.WHITE, T.YELLOW]), legend=None))
    return alt.layer(line, dots, text).resolve_scale(color="independent", shape="independent")


# ---------------------------------------------------------------- 2 companies
def companies_tab(D, rf) -> None:
    sec, val, fc = D["metrics"]["securities"], D["valuation"]["securities"], D["ai"]["forecasts"]
    H(T.head("Valuation vs market price", f"Excel models at CAPM discount rates · prices of {D['valuation']['latest_price_date']}"))
    rows = []
    for t in STOCKS:
        v, up = val[t], val[t]["upside_vs_latest"]["blended"]
        rows.append([NAMES[t], T.inr(v["latest_price"]), T.pct(v["cost_of_equity"]), T.inr(v["intrinsic_value"]),
                     T.inr(v["comps_value"]), T.inr(v["blended_value"]), T.chg(up, 0), T.pct(v["market_implied_growth"]),
                     f'{T.inr(fc[t]["analyst_target_mean"])} {T.chg(fc[t]["analyst_target_upside"], 0)}', T.esc(v["workbook_verdict"])])
    H(T.table(["Stock", "Price", "r (CAPM)", "Model value", "Peer value", "Blended", "Blended vs price",
               "Implied growth", "Analyst target", "Verdict"], rows))
    H(T.note("Model: two-stage DDM (HUL), two-stage residual income (Sun Pharma, ICICI Bank). Implied growth = the "
             "perpetual growth at which our model equals today's price. Full workings: workbook/valuation.xlsx."))
    left, right = st.columns(2, gap="medium")
    with left:
        bars = pd.DataFrame([{"stock": SHORT[t], "measure": m, "value": v} for t in STOCKS for m, v in
                             [("Price", val[t]["latest_price"]), ("Our model", val[t]["intrinsic_value"]),
                              ("Peer multiples", val[t]["comps_value"]), ("Analyst target", fc[t]["analyst_target_mean"])]])
        order = ["Price", "Our model", "Peer multiples", "Analyst target"]
        chart(alt.Chart(bars).mark_bar().encode(
            x=alt.X("stock:N", title=None, sort=[SHORT[t] for t in STOCKS], axis=alt.Axis(labelAngle=0)), xOffset=alt.XOffset("measure:N", sort=order),
            y=alt.Y("value:Q", title="₹ per share"),
            color=alt.Color("measure:N", sort=order, scale=alt.Scale(domain=order, range=[T.WHITE, T.AMBER, T.VIOLET, T.CYAN]),
                            legend=alt.Legend(title=None)),
            tooltip=["stock:N", "measure:N", alt.Tooltip("value:Q", format=",.0f")]), 320)
    with right:
        m_mean = sec[BENCH]["mean_return"]
        sml = pd.DataFrame({"beta": [0, 1.6], "ret": [rf, rf + 1.6 * (m_mean - rf)]})
        # Labels sit beside each point; HUL and Sun Pharma are close, so HUL's goes below its point.
        pts = pd.DataFrame([{"beta": sec[t]["beta"], "ret": sec[t]["mean_return"],
                             "ly": sec[t]["mean_return"] - (0.012 if t == "HINDUNILVR.NS" else 0),
                             "label": f"{SHORT[t]} α {T.pct(sec[t]['jensen_alpha'], 1, sign=True)}",
                             "side": "right" if t == "ICICIBANK.NS" else "left"} for t in STOCKS + [BENCH]])
        sx = alt.Scale(domain=[0, 1.6])
        chart(alt.layer(
            alt.Chart(sml).mark_line(color=T.AMBER).encode(x=alt.X("beta:Q", title="Beta vs Nifty 50", scale=sx),
                                                           y=alt.Y("ret:Q", title="Mean annual return", axis=alt.Axis(format=".0%"))),
            alt.Chart(pts).mark_point(filled=True, size=90, color=T.CYAN).encode(x=alt.X("beta:Q", scale=sx), y="ret:Q"),
            alt.Chart(pts[pts.side == "left"]).mark_text(align="left", dx=8, color=T.TEXT).encode(
                x=alt.X("beta:Q", scale=sx), y="ly:Q", text="label:N"),
            alt.Chart(pts[pts.side == "right"]).mark_text(align="right", dx=-8, color=T.TEXT).encode(
                x=alt.X("beta:Q", scale=sx), y="ly:Q", text="label:N"),
        ).properties(title="Security Market Line (ex-post, 2016–2026): above the line = beat CAPM"), 320)
    H(T.head("Risk and return, 2016 to date", "daily data; Nifty 50 includes an estimated 1.22%/yr dividend"))
    cols = [("cagr", "CAGR", 1), ("volatility", "Volatility", 1), ("sharpe", "Sharpe", None), ("sortino", "Sortino", None),
            ("max_drawdown", "Max drawdown", 0), ("beta", "Beta", None), ("treynor", "Treynor", 1),
            ("jensen_alpha", "Jensen α", 1), ("var_95_daily", "Daily VaR 95%", 1), ("capm_required_return", "CAPM r", 1)]
    H(T.table(["Security"] + [c[1] for c in cols],
              [[NAMES[t]] + [T.pct(sec[t][k], d) if d is not None else f"{sec[t][k]:.2f}" for k, _, d in cols]
               for t in STOCKS + [BENCH]]))


# ---------------------------------------------------------------- 3 AI
def ai_tab(D) -> None:
    ex, fr, sen = D["extraction"], D["ai"]["framing"], D["sentiment"]
    H(T.kpis([("AI extraction within 1%", f"{ex['counts']['match']} / {ex['comparisons']}", "vs Yahoo and Screener"),
              ("Extraction errors", str(ex["counts"]["extraction error"]), f"{ex['counts']['definition difference']} definition differences"),
              ("Headlines with a bias cue", T.pct(fr["share_with_bias_cue"], 0), f"sample of {fr['sample']}"),
              ("FinBERT vs LLM agreement", T.pct(fr["finbert_vs_llm_agreement"], 0), "on the same headlines")]))
    left, right = st.columns(2, gap="medium")
    with left:
        H(T.head("News tone by month", "FinBERT, P(positive) − P(negative)"))
        monthly = pd.DataFrame(sen["monthly_headline_tone"]).assign(stock=lambda d: d.ticker.map(SHORT))
        chart(alt.Chart(monthly).mark_line(point=True).encode(
            x=alt.X("month:N", title=None, axis=alt.Axis(labelAngle=-45)), y=alt.Y("tone:Q", title="Tone"),
            color=alt.Color("stock:N", scale=alt.Scale(domain=[SHORT[t] for t in STOCKS], range=[COLOR[t] for t in STOCKS]),
                            legend=alt.Legend(title=None)),
            tooltip=["stock:N", "month:N", alt.Tooltip("tone:Q", format=".2f"), "headlines:Q"]), 300)
    with right:
        H(T.head("Earnings calls: management vs analysts", "FinBERT tone per call"))
        calls = pd.DataFrame(sen["transcripts"]).dropna(subset=["management_tone"])
        calls = calls.melt(id_vars=["ticker", "quarter"], value_vars=["management_tone", "analyst_tone"],
                           var_name="speaker", value_name="tone").assign(
            stock=lambda d: d.ticker.map(SHORT), speaker=lambda d: d.speaker.map({"management_tone": "Management",
                                                                                   "analyst_tone": "Analysts"}))
        chart(alt.Chart(calls).mark_line(point=True).encode(
            x=alt.X("quarter:N", title=None, sort="ascending"), y=alt.Y("tone:Q", title="Tone"),
            color=alt.Color("stock:N", scale=alt.Scale(domain=[SHORT[t] for t in STOCKS], range=[COLOR[t] for t in STOCKS]),
                            legend=alt.Legend(title=None)),
            strokeDash=alt.StrokeDash("speaker:N", legend=alt.Legend(title=None)),
            tooltip=["stock:N", "quarter:N", "speaker:N", alt.Tooltip("tone:Q", format=".2f")]), 300)
    H(T.note(f"{fr['irrelevant_share']:.0%} of sampled headlines were not about the company (name collisions). "
             "Gain-framed share: " + ", ".join(f"{SHORT[t]} {v.get('gain', 0):.0%}" for t, v in fr["frame_mix"].items()) + "."))
    left, right = st.columns(2, gap="medium")
    with left:
        H(T.head("Is technical analysis possible?", "Sharpe ratio after a 0.25% round-trip cost"))
        ta = pd.DataFrame(D["ai"]["technical_analysis"]).assign(stock=lambda d: d.ticker.map(SHORT))
        order = ["Buy and hold", "Trend (50/200 DMA)", "RSI mean reversion"]
        chart(alt.Chart(ta).mark_bar().encode(
            x=alt.X("stock:N", title=None, sort=[SHORT[t] for t in STOCKS + [BENCH]], axis=alt.Axis(labelAngle=0)), xOffset=alt.XOffset("rule:N", sort=order),
            y=alt.Y("sharpe:Q", title="Sharpe ratio"),
            color=alt.Color("rule:N", sort=order, scale=alt.Scale(domain=order, range=[T.WHITE, T.AMBER, T.RED]),
                            legend=alt.Legend(title=None)),
            tooltip=["stock:N", "rule:N", alt.Tooltip("sharpe:Q", format=".2f"), alt.Tooltip("max_drawdown:Q", format=".0%")]), 300)
    with right:
        es = D["ai"]["event_study"]
        H(T.head("Do prices react to earnings surprises?",
                 f"{es['events']} results · CAR[−1,+1] {T.pct(es['mean_car_positive_surprise'], 1, True)} after beats, "
                 f"{T.pct(es['mean_car_negative_surprise'], 1, True)} after misses"))
        ev = pd.DataFrame(es["rows"]).assign(stock=lambda d: d.ticker.map(SHORT))
        chart(alt.Chart(ev).mark_point(filled=True, size=60).encode(
            x=alt.X("surprise_pct:Q", title="EPS surprise (%)", axis=alt.Axis(format=".0f")),  # already in percent
            y=alt.Y("car:Q", title="3-day abnormal return", axis=alt.Axis(format=".0%")),
            color=alt.Color("stock:N", scale=alt.Scale(domain=[SHORT[t] for t in STOCKS], range=[COLOR[t] for t in STOCKS]),
                            legend=alt.Legend(title=None)),
            tooltip=["stock:N", "date:N", alt.Tooltip("surprise_pct:Q", format=".1f", title="surprise %"), alt.Tooltip("car:Q", format=".2%")]), 300)
    H(T.head("Latest earnings calls: guidance and aspects", "Claude, from the transcripts (data/ai/concall_aspects.json)"))
    for t in STOCKS:
        a = D["aspects"][t]
        with st.expander(f"{NAMES[t]}: {a['call']}"):
            for g in a["guidance"]:
                st.markdown(f"- *Guidance, {g['item']}:* {g['statement']}")
            H(T.table(["Aspect", "Tone", "Evidence"], [[T.esc(x["aspect"]), T.esc(x["sentiment"]), T.esc(x["evidence"])]
                                                     for x in a["aspects"]], text=True))
    with st.expander("AI ratio extraction vs Yahoo and Screener (every comparison)"):
        st.dataframe(pd.DataFrame(ex["rows"]).assign(ticker=lambda d: d["ticker"].map(NAMES)), hide_index=True, width="stretch")


# ---------------------------------------------------------------- 4 risk
def heat(corr: dict, title: str) -> alt.LayerChart:
    names = list(corr)
    cells = pd.DataFrame([{"a": a, "b": b, "c": corr[a][b]} for a in names for b in names])
    base = alt.Chart(cells).encode(x=alt.X("a:N", sort=names, title=None, axis=alt.Axis(labelAngle=0)),
                                   y=alt.Y("b:N", sort=names, title=None))
    return alt.layer(base.mark_rect(stroke=T.BG, strokeWidth=2).encode(
        color=alt.Color("c:Q", scale=alt.Scale(domain=[0, 1], range=["#0B1F2E", T.CYAN]), legend=None)),
        base.mark_text(fontWeight="bold").encode(text=alt.Text("c:Q", format=".2f"),
                                                 color=alt.condition("datum.c > 0.55", alt.value(T.BG), alt.value(T.WHITE)))
    ).properties(title=title)


def risk_tab(D, y, amount) -> None:
    risk = D["ai"]["risk"]
    left, right = st.columns(2, gap="medium")
    with left:
        chart(heat(risk["correlation_full"], "Correlation of daily returns, 2016–2026"), 300)
    with right:
        chart(heat(risk["correlation_5y"], "Last five years"), 300)
    left, right = st.columns([3, 2], gap="medium")
    with left:
        H(T.head("Rolling 120-day correlation", "diversification is not constant"))
        r = D["daily"][STOCKS]
        pairs = [("HINDUNILVR.NS", "SUNPHARMA.NS"), ("HINDUNILVR.NS", "ICICIBANK.NS"), ("SUNPHARMA.NS", "ICICIBANK.NS")]
        roll = pd.concat([r[a].rolling(120).corr(r[b]).rename(f"{SHORT[a]} / {SHORT[b]}") for a, b in pairs], axis=1)
        roll = roll.resample("W").last().dropna().reset_index(names="date").melt(id_vars="date", var_name="pair", value_name="corr")
        chart(alt.Chart(roll).mark_line(strokeWidth=1.5).encode(
            x=alt.X("date:T", title=None), y=alt.Y("corr:Q", title="Correlation"),
            color=alt.Color("pair:N", scale=alt.Scale(range=[T.CYAN, T.AMBER, T.VIOLET]), legend=alt.Legend(title=None))), 280)
    with right:
        H(T.head("Who carries the risk in P", "share of P's variance vs share of its weight"))
        share = pd.DataFrame([{"stock": n, "measure": "Share of risk", "v": v} for n, v in risk["risk_share_latest"].items()]
                             + [{"stock": SHORT[t], "measure": "Weight", "v": w} for t, w in risk["weights"].items()])
        chart(alt.Chart(share).mark_bar().encode(
            y=alt.Y("stock:N", title=None), yOffset="measure:N", x=alt.X("v:Q", title=None, axis=alt.Axis(format=".0%")),
            color=alt.Color("measure:N", scale=alt.Scale(range=[T.RED, T.GREY]), legend=alt.Legend(title=None)),
            tooltip=["stock:N", "measure:N", alt.Tooltip("v:Q", format=".0%")]), 280)
    H(T.head(f"Stress tests on your portfolio: {T.inr(amount)} with {T.pct(y, 0)} in P",
             "price change through four real sell-offs; T-bill interest ignored"))
    rows = []
    for ep, s in risk["stress"].items():
        ep = ep.replace("to now", f"to {date.fromisoformat(D['metrics']['as_of']):%d %b %Y}")
        mine = y * s["Portfolio P"]
        rows.append([T.esc(ep)] + [T.chg(s[k]) for k in ("HUL", "Sun Pharma", "ICICI Bank", "Portfolio P", "Nifty 50")]
                    + [T.chg(mine), f'<span class="{"up" if mine >= 0 else "down"}">{T.inr(amount * mine)}</span>'])
    H(T.table(["Sell-off", "HUL", "Sun Pharma", "ICICI", "P", "Nifty 50", "You (%)", "You (₹)"], rows))


# ---------------------------------------------------------------- 5 ask
def ask_tab(D, mine: dict) -> None:
    qa = D["qa"]
    H(T.head("Saved answers", qa["prepared_by"]))
    q = st.selectbox("Pick a question", [x["q"] for x in qa["questions"]])
    st.markdown(next(x["a"] for x in qa["questions"] if x["q"] == q))
    H(T.head("Ask your own question", "a free model on OpenRouter, answering only from this dashboard's numbers"))
    key = secret("OPENROUTER_API_KEY")
    if not key:
        st.info("Live questions are off on this deployment (no OPENROUTER_API_KEY configured). The saved answers "
                "above come from the same data.")
        return
    passcode = secret("CHAT_PASSCODE")
    if passcode and st.text_input("Passcode", type="password") != passcode:
        return
    used = ss.setdefault("questions_used", 0)
    if used >= 10:
        st.warning("Question limit for this session reached.")
    else:
        # A form, so other widgets (e.g. the risk slider) rerunning the script never re-send the question.
        with st.form("ask"):
            question = st.text_input("Question", placeholder="e.g. What happens to my portfolio in a crash like 2020?")
            sent = st.form_submit_button("ASK ▶")
        if sent and question.strip():
            with st.spinner("Asking the model..."):
                answer, status = chat.ask(question, chat.build_context(D, mine), key)
            ss["questions_used"] = used + 1
            ss["last_answer"] = (answer, status)
    if last := ss.get("last_answer"):
        answer, status = last
        if answer:
            st.markdown(answer)
            st.caption(f"Live answer from {status}, grounded only in this dashboard's data.")
        else:
            st.warning(f"Live answer unavailable ({status}). See the saved answers above.")


# ---------------------------------------------------------------- 6 profile
def profile_tab(A, threshold) -> None:
    res: quiz.Result | None = ss.get("quiz_result")
    left, right = st.columns([3, 2], gap="large")
    with left:
        if res:
            H(T.head("Your questionnaire result"))
            H(T.kpis([("Capacity score", f"{res.capacity:.2f}", f"→ A = {res.a_capacity:.2f}"),
                      ("Willingness score", f"{res.willingness:.2f}", f"→ A = {res.a_willingness:.2f}"),
                      ("Your A", f"{res.risk_aversion:.2f}", "the more cautious of the two"),
                      ("Profile", res.profile.upper(), "")], big=2))
            answers = ss.get("quiz_answers", {})
            H(T.table(["#", "Question", "Your answer"],
                      [[str(i), T.esc(question), T.esc(options[answers[key] - 1]) if key in answers else "–"]
                       for i, (key, _, question, options) in enumerate(quiz.QUESTIONS, 1)], text=True))
            if abs(A - res.risk_aversion) > 1e-9:
                H(T.note(f"You have since moved A to {A:.2f} with the slider."))
        else:
            source = {"skipped": "You skipped the questionnaire (Balanced, A = 4).", "manual": "You entered A yourself."}
            H(T.head("No questionnaire taken"))
            H(T.note(source.get(ss.get("a_source"), "")))
        st.button("RETAKE THE QUESTIONNAIRE ↺", on_click=_retake, key="retake")
    with right:
        H(T.head("What A does", "U = E(r) − ½·A·σ²"))
        H(T.table(["A", "Meaning", "Share in P"], [
            ["> 0", "Risk-averse: risk lowers utility", "y* = (E[rP] − rf) / (A·σP²)"],
            [f"≤ {threshold:.2f}", "Wants 100% or more in P", "capped at 100% without borrowing"],
            ["= 0", "Risk-neutral: only E(r) matters", "the most P allowed"],
            ["< 0", "Risk-seeking: risk adds utility", "the most P allowed"]], text=True))
        H(T.note("P itself (the stock mix) is the same for every investor: the separation property. Your A only "
                 "decides how much of your money goes into P versus T-bills."))


if "A" not in ss:
    onboarding()
else:
    terminal()
