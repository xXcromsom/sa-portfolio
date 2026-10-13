"""Streamlit dashboard: HUL, Sun Pharma and ICICI Bank. Security Analysis group project.

Reads only files already on disk (data/latest, and data/submission once frozen),
so no chart can go blank because a download failed. Run locally with:
    streamlit run app.py
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from src import chat

ROOT = Path(__file__).resolve().parent
DATASETS = {"Submission (frozen)": ROOT / "data" / "submission", "Latest": ROOT / "data" / "latest"}
NAMES = {"HINDUNILVR.NS": "Hindustan Unilever", "SUNPHARMA.NS": "Sun Pharma", "ICICIBANK.NS": "ICICI Bank",
         "^NSEI": "Nifty 50 TR (est.)"}
STOCKS = ["HINDUNILVR.NS", "SUNPHARMA.NS", "ICICIBANK.NS"]

st.set_page_config(page_title="Security Analysis Portfolio", page_icon="📈", layout="wide")


def _stamp(folder: Path) -> str:
    """Change token for the cache: newest modification time in the folder."""
    return str(max((p.stat().st_mtime for p in folder.rglob("*") if p.is_file()), default=0))


@st.cache_data(show_spinner=False)
def load(folder: str, stamp: str) -> dict:
    f = Path(folder)
    read = lambda name: json.loads((f / name).read_text(encoding="utf-8"))  # noqa: E731
    data = {k: read(n) for k, n in [("metrics", "metrics.json"), ("valuation", "valuation.json"),
                                      ("portfolio", "portfolio.json"), ("mc", "mc.json"), ("sip", "sip.json"),
                                      ("ai", "ai_analysis.json")]}
    data["aspects"] = json.loads((ROOT / "data/ai/concall_aspects.json").read_text(encoding="utf-8"))["companies"]
    data["qa"] = json.loads((ROOT / "data/ai/qa_cache.json").read_text(encoding="utf-8"))
    data["extraction"] = read("extraction_accuracy.json")
    return data


def fig(folder: Path, name: str, caption: str | None = None) -> None:
    path = folder / "figures" / name
    if path.exists():
        st.image(str(path), caption=caption, width="stretch")
    else:
        st.info(f"Figure {name} is not available for this dataset.")


def secret(name: str) -> str | None:
    """Environment variable first, then Streamlit secrets; None if neither exists (no secrets file is fine)."""
    if os.getenv(name):
        return os.getenv(name)
    try:
        return st.secrets.get(name)
    except Exception:  # Streamlit raises when no secrets.toml exists
        return None


def pct(x, digits=1):
    return "–" if x is None or pd.isna(x) else f"{x:.{digits}%}"


def rupees(x):
    return "–" if x is None or pd.isna(x) else f"₹{x:,.0f}"


# ---------------------------------------------------------------- sidebar
available = {k: v for k, v in DATASETS.items() if (v / "metrics.json").exists()}
with st.sidebar:
    st.markdown("### Security Analysis portfolio")
    st.caption("TAPMI · BBA(H) Sem V · BBAT35F97")
    choice = st.radio("Data", list(available), index=0,
                      help="Submission = the numbers in our report. Latest = refreshed since.")
    folder = available[choice]
    D = load(str(folder), _stamp(folder))
    as_of = D["metrics"]["as_of"]
    age = (date.today() - date.fromisoformat(as_of)).days
    st.markdown(f"**Data as of {as_of}**")
    if choice == "Latest" and age > 4:
        st.warning(f"Stale: last refresh {age} days ago.")
    st.divider()
    st.markdown("**Your risk aversion (A)**")
    A = st.slider("A in U = E(r) − ½Aσ²", 1.0, 10.0, 4.0, 0.5,
                  help="2 = aggressive, 4 = balanced, 6 = conservative. Take docs/risk_questionnaire.md to find yours.")
    st.divider()
    st.caption("Coursework, not investment advice. Sources: Yahoo Finance, Screener.in, BSE filings, RBI, MOSPI, "
               "Damodaran, Google News.")

P = D["portfolio"]["views"]["forward"]["tangency"]
rf = D["portfolio"]["risk_free_rate"]
nifty = D["portfolio"]["views"]["forward"]["market"]
y_star = (P["expected_return"] - rf) / (A * P["volatility"] ** 2)
y = min(max(y_star, 0.0), 1.0)
er_c, vol_c = rf + y * (P["expected_return"] - rf), y * P["volatility"]
ce = er_c - 0.5 * A * vol_c ** 2

st.title("HUL · Sun Pharma · ICICI Bank")
st.caption("An AI-augmented security analysis and portfolio for a student investor starting a monthly SIP.")

tabs = st.tabs(["Overview", "Companies", "Portfolio", "AI insights", "Risk", "Ask the portfolio"])

# ---------------------------------------------------------------- overview
with tabs[0]:
    c = st.columns(4)
    c[0].metric("Expected return of P", pct(P["expected_return"]), help="Forward-looking (CAPM) expected return")
    c[1].metric("Volatility of P", pct(P["volatility"]))
    c[2].metric("Sharpe ratio of P", f"{P['sharpe']:.2f}", f"{P['sharpe'] - nifty['sharpe']:+.2f} vs Nifty",
                delta_color="normal")
    c[3].metric(f"Your share in P (A = {A:g})", pct(y, 0), help="The rest goes to T-bills")
    rows = []
    for t in STOCKS:
        v = D["valuation"]["securities"][t]
        m = D["metrics"]["securities"][t]
        rows.append({"Stock": NAMES[t], "Weight in P": P["weights"][t], "Beta": m["beta"],
                     "Price": v["latest_price"], "Model value": v["intrinsic_value"], "Peer value": v["comps_value"],
                     "Blended upside": v["upside_vs_latest"]["blended"], "Verdict": v["workbook_verdict"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
        "Weight in P": st.column_config.NumberColumn(format="percent"),
        "Beta": st.column_config.NumberColumn(format="%.2f"),
        "Price": st.column_config.NumberColumn(format="₹%.0f"),
        "Model value": st.column_config.NumberColumn(format="₹%.0f"),
        "Peer value": st.column_config.NumberColumn(format="₹%.0f"),
        "Blended upside": st.column_config.NumberColumn(format="percent")})
    st.markdown(
        f"- **Recommended risky portfolio P:** HUL {pct(P['weights']['HINDUNILVR.NS'], 0)}, "
        f"Sun Pharma {pct(P['weights']['SUNPHARMA.NS'], 0)}, ICICI {pct(P['weights']['ICICIBANK.NS'], 0)}. "
        "Weights use forward-looking CAPM returns, not last decade's winners.\n"
        f"- **The index beats a 3-stock portfolio on risk-adjusted terms** (Sharpe {nifty['sharpe']:.2f} vs "
        f"{P['sharpe']:.2f}), so the long-term SIP is core-satellite: 50% Nifty index fund + 50% these stocks.\n"
        "- **Valuation is the main risk:** the market prices in more growth than our models at CAPM discount rates.")
    fig(folder, "frontier.png")

# ---------------------------------------------------------------- companies
with tabs[1]:
    sec = D["metrics"]["securities"]
    order = STOCKS + ["^NSEI"]
    table = pd.DataFrame({NAMES[t]: sec[t] for t in order}).T
    show = table[["cagr", "volatility", "sharpe", "sortino", "max_drawdown", "beta", "treynor", "jensen_alpha",
                  "var_95_daily", "capm_required_return"]]
    show.columns = ["CAGR", "Volatility", "Sharpe", "Sortino", "Max drawdown", "Beta", "Treynor", "Jensen's α",
                    "Daily VaR 95%", "CAPM r"]
    st.subheader("Risk and return, 2016 to date")
    st.dataframe(show.style.format({c: "{:.1%}" for c in show.columns if c not in ("Sharpe", "Sortino", "Beta")}
                                   | {"Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Beta": "{:.2f}"}),
                 width="stretch")
    col1, col2 = st.columns(2)
    with col1:
        fig(folder, "sml.png")
    with col2:
        st.subheader("Valuation vs consensus")
        fc = D["ai"]["forecasts"]
        vt = pd.DataFrame([{"Stock": NAMES[t], "Model upside": fc[t]["our_model_upside"],
                            "Peer multiple on FY28 EPS": fc[t]["our_comps_fwd_upside"],
                            "Analyst mean target": fc[t]["analyst_target_upside"],
                            "Market-implied growth": D["valuation"]["securities"][t]["market_implied_growth"]}
                           for t in STOCKS])
        st.dataframe(vt.style.format({c: "{:+.0%}" for c in vt.columns[1:4]} | {"Market-implied growth": "{:.1%}"}),
                     hide_index=True, width="stretch")
        st.caption("Model = DDM (HUL) or residual income (Sun Pharma, ICICI) at CAPM discount rates. Analyst targets "
                   "from Yahoo Finance consensus. Full workings: workbook/valuation.xlsx.")

# ---------------------------------------------------------------- portfolio
with tabs[2]:
    c = st.columns(4)
    c[0].metric("Optimal share in P (y*)", pct(y_star, 0), help="y* = (E[rP] − rf) / (A σP²), capped at 100%")
    c[1].metric("Complete-portfolio return", pct(er_c))
    c[2].metric("Complete-portfolio volatility", pct(vol_c))
    c[3].metric("Certainty equivalent", pct(ce), help="The risk-free return you would accept instead")
    col1, col2 = st.columns(2)
    with col1:
        fig(folder, "indifference.png")
    with col2:
        oos = D["portfolio"]["out_of_sample"]
        st.subheader(f"Out-of-sample test, {oos['test']}")
        st.dataframe(pd.DataFrame([{"Rule": k, "CAGR": oos[k]["portfolio"]["cagr"], "Sharpe": oos[k]["portfolio"]["sharpe"],
                                    "Max drawdown": oos[k]["portfolio"]["max_drawdown"]}
                                   for k in ("History-based P", "Forward-looking P", "Equal weight")]
                                  + [{"Rule": "Nifty 50 TR", "CAGR": oos["Equal weight"]["market"]["cagr"],
                                      "Sharpe": oos["Equal weight"]["market"]["sharpe"],
                                      "Max drawdown": oos["Equal weight"]["market"]["max_drawdown"]}])
                     .style.format({"CAGR": "{:.1%}", "Sharpe": "{:.2f}", "Max drawdown": "{:.1%}"}),
                     hide_index=True, width="stretch")
        st.caption(f"Weights estimated on {oos['in_sample']}. Sun Pharma was picked partly after its recent run, "
                   "so this test flatters the current line-up.")
    st.subheader("One-year Monte Carlo (₹1 lakh)")
    mc = D["mc"]["results"]
    st.dataframe(pd.DataFrame([{"Method": mode, "Profile": prof, "Median": r["terminal_percentiles"]["p50"],
                                "5th percentile": r["terminal_percentiles"]["p5"], "95% VaR": r["var_95"],
                                "P(loss)": r["prob_loss"]}
                               for mode, res in mc.items() for prof, r in res.items()])
                 .style.format({"Median": "₹{:,.0f}", "5th percentile": "₹{:,.0f}", "95% VaR": "₹{:,.0f}",
                                "P(loss)": "{:.0%}"}), hide_index=True, width="stretch")
    col1, col2 = st.columns(2)
    with col1:
        fig(folder, "mc_fan.png")
    with col2:
        fig(folder, "mc_hist.png")
    st.subheader("Building it over 15 years: monthly SIP")
    sip = D["sip"]["results"]
    st.dataframe(pd.DataFrame([{"Profile": prof, "Method": mode, "Median corpus": r[mode]["terminal_percentiles"]["p50"],
                                "5th percentile": r[mode]["terminal_percentiles"]["p5"],
                                **{f"P(≥ ₹{int(g) / 1e5:.0f} L)": p for g, p in r[mode]["prob_reach_goal"].items()}}
                               for prof, r in sip.items() for mode in ("Parametric", "Bootstrap")])
                 .style.format({"Median corpus": "₹{:,.0f}", "5th percentile": "₹{:,.0f}"}
                               | {c: "{:.0%}" for c in ("P(≥ ₹50 L)", "P(≥ ₹75 L)", "P(≥ ₹100 L)")}),
                 hide_index=True, width="stretch")
    fig(folder, "sip.png")

# ---------------------------------------------------------------- AI insights
with tabs[3]:
    ex = D["extraction"]
    c = st.columns(3)
    c[0].metric("AI extraction: fields within 1%", f"{ex['counts']['match']} / {ex['comparisons']}")
    c[1].metric("Extraction errors", ex["counts"]["extraction error"])
    fr = D["ai"]["framing"]
    c[2].metric("Headlines with a bias cue", pct(fr["share_with_bias_cue"], 0))
    with st.expander("AI ratio extraction vs Yahoo and Screener (every comparison)"):
        st.dataframe(pd.DataFrame(ex["rows"]).assign(ticker=lambda d: d["ticker"].map(NAMES))
                     .style.format({"ai": "{:,.2f}", "ref": "{:,.2f}", "gap": "{:+.2%}"}),
                     hide_index=True, width="stretch")
    st.subheader("Sentiment in news and earnings calls")
    fig(folder, "sentiment.png")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**News framing (120 sampled headlines)**")
        st.markdown(f"- Not about the company at all: **{pct(fr['irrelevant_share'], 0)}** (name collisions)\n"
                    f"- FinBERT agrees with the LLM labels on **{pct(fr['finbert_vs_llm_agreement'], 0)}**\n"
                    f"- Gain-framed share: " + ", ".join(f"{NAMES[t]} {pct(v.get('gain'), 0)}"
                                                        for t, v in fr["frame_mix"].items()))
    with col2:
        st.markdown("**Latest earnings calls: what management said**")
        for t in STOCKS:
            a = D["aspects"][t]
            with st.expander(f"{NAMES[t]}: {a['call']}"):
                for g in a["guidance"]:
                    st.markdown(f"- *Guidance, {g['item']}:* {g['statement']}")
                st.dataframe(pd.DataFrame(a["aspects"]), hide_index=True, width="stretch")
    st.subheader("Is technical analysis possible?")
    fig(folder, "ta.png")
    ta = pd.DataFrame(D["ai"]["technical_analysis"]).assign(ticker=lambda d: d["ticker"].map(
        {**NAMES, "^NSEI": "Nifty 50 (price)"}))
    st.dataframe(ta.style.format({"cagr": "{:.1%}", "volatility": "{:.1%}", "sharpe": "{:.2f}", "max_drawdown": "{:.1%}",
                                  "time_invested": "{:.0%}", "trades_per_year": "{:.1f}"}),
                 hide_index=True, width="stretch")
    st.subheader("Do prices react to earnings surprises?")
    fig(folder, "event_study.png")

# ---------------------------------------------------------------- risk
with tabs[4]:
    fig(folder, "corr_heatmap.png")
    col1, col2 = st.columns(2)
    with col1:
        fig(folder, "rolling_corr.png")
    with col2:
        fig(folder, "stress.png")
    fig(folder, "risk_contrib.png")

# ---------------------------------------------------------------- ask
with tabs[5]:
    qa = D["qa"]
    st.caption(f"Saved answers: {qa['prepared_by']}")
    q = st.selectbox("Pick a question", [x["q"] for x in qa["questions"]])
    st.markdown(next(x["a"] for x in qa["questions"] if x["q"] == q))
    key = secret("ANTHROPIC_API_KEY")
    st.divider()
    if not key:
        st.info("Live questions are off on this deployment (no API key configured). The saved answers above "
                "come from the same data.")
    else:
        passcode = secret("CHAT_PASSCODE")
        if passcode and st.text_input("Passcode", type="password") != passcode:
            st.stop()
        used = st.session_state.setdefault("questions_used", 0)
        if used >= 10:
            st.warning("Question limit for this session reached.")
        else:
            # A form, so other widgets (e.g. the risk slider) rerunning the script never re-send the question.
            with st.form("ask"):
                question = st.text_input("Ask your own question about this portfolio")
                sent = st.form_submit_button("Ask")
            if sent and question.strip():
                with st.spinner("Thinking…"):
                    answer, status = chat.ask(question, chat.build_context(D), key)
                st.session_state["questions_used"] = used + 1
                st.session_state["last_answer"] = (answer, status)
        if last := st.session_state.get("last_answer"):
            answer, status = last
            if answer:
                st.markdown(answer)
                st.caption(f"Live answer from {chat.MODEL}, grounded only in this dashboard's data.")
            else:
                st.warning(f"Live answer unavailable ({status}). See the saved answers above.")
