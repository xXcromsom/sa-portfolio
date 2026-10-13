"""Phase 3: AI-augmented analysis, assembled from the pieces built elsewhere.

Inputs:
- data/latest from Phases 1-2 (prices, portfolio, valuation)
- the text step (sentiment.json, transcript_tone.csv; run `python -m pipeline.text_step`)
- the in-session AI outputs in data/ai/ (ratio extraction, concall aspects, headline framing)

Outputs: data/latest/ai_analysis.json plus the Phase 3 figures. Network calls (Yahoo
consensus and statements) are cached in data/latest/consensus.json and
yahoo_statements.json; pass refresh=True to re-fetch.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from openpyxl import load_workbook

from src import charts_ai
from src import extraction_check as ec
from src import forecast as fc
from src import quant_utils as qu
from src import technical
from src.config import project_path
from src.data_ingest import make_session

STRESS = {  # name: (start, end). The last window is filled in from the data (the latest Nifty drawdown).
    "COVID crash (Feb-Mar 2020)": ("2020-02-19", "2020-03-23"),
    "Rate-hike sell-off (Jan-Jun 2022)": ("2022-01-17", "2022-06-17"),
    "Election-result shock (4 Jun 2024)": ("2024-06-03", "2024-06-04"),
}


def _cached(path, fetch, refresh: bool):
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetch()
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return data


def _short(labels: dict) -> dict:
    return {t: n.replace("Hindustan Unilever", "HUL").replace(" (est.)", "") for t, n in labels.items()}


def run_phase3(ctx, refresh: bool = False) -> dict:
    out, r, rf, periods = ctx.out, ctx.returns, ctx.rf, ctx.periods
    stocks, bench = ctx.stocks, ctx.bench
    short = _short(ctx.labels)
    portfolio = json.loads((out / "portfolio.json").read_text(encoding="utf-8"))
    w = pd.Series(portfolio["views"]["forward"]["tangency"]["weights"])
    result: dict = {"as_of": ctx.meta["last_date"]}

    # 1. Is technical analysis possible?
    ta = technical.evaluate(ctx.prices[stocks + [bench]], rf)
    result["technical_analysis"] = ta.round(4).to_dict(orient="records")
    curves = {}
    for t in stocks + [bench]:
        p = ctx.prices[t]
        rules = {"Trend (50/200 DMA)": technical.trend_signal(p), "RSI mean reversion": technical.rsi_signal(p)}
        strat = {k: technical.strategy_returns(p, s, rf) for k, s in rules.items()}
        start = max(s.index[0] for s in strat.values())
        bh = p.pct_change(fill_method=None).loc[start:].dropna()
        curves[t] = pd.DataFrame({"Buy and hold": (1 + bh).cumprod(),
                                  **{k: (1 + s.loc[start:]).cumprod() for k, s in strat.items()}}).dropna()
    labels_ta = {**short, bench: "Nifty 50 (price index)"}
    ctx.fig(charts_ai.ta_figure(curves, labels_ta), "ta.png")

    # 2. Risk heatmaps: correlation (full, 5y), rolling correlation, risk contributions, stress tests.
    cols = stocks + [bench]
    full = r[cols].corr().rename(index=short, columns=short)
    recent_r = r[cols].iloc[-5 * periods:]
    recent = recent_r.corr().rename(index=short, columns=short)
    ctx.fig(charts_ai.corr_heatmap_figure(full, recent, f"Last 5 years ({recent_r.index[0]:%b %Y} on)"),
            "corr_heatmap.png")
    window = 120
    pairs = [(a, b) for i, a in enumerate(stocks) for b in stocks[i + 1:]]
    roll = pd.DataFrame({f"{short[a]} / {short[b]}": r[a].rolling(window).corr(r[b]) for a, b in pairs}).dropna()
    ctx.fig(charts_ai.rolling_corr_figure(roll, window), "rolling_corr.png")
    quarter_ends = r.index.to_series().groupby(r.index.to_period("Q")).max().iloc[4:]
    contrib = {}
    for d in quarter_ends:
        c = r[stocks].loc[:d].iloc[-periods:].cov().to_numpy()
        wv = w[stocks].to_numpy()
        mrc = wv * (c @ wv)
        contrib[d] = pd.Series(mrc / mrc.sum(), index=[short[t] for t in stocks])
    contrib = pd.DataFrame(contrib).T
    ctx.fig(charts_ai.risk_contrib_figure(contrib), "risk_contrib.png")
    port = r[stocks] @ w[stocks]
    nifty_px = ctx.prices[bench]
    peak = nifty_px.loc["2025-01-01":].idxmax()
    windows = {**STRESS, f"2026 drawdown ({peak:%d %b %Y} to now)": (str(peak.date()), str(r.index[-1].date()))}
    stress = {}
    for name, (a, b) in windows.items():
        seg = pd.concat([r[stocks], port.rename("Portfolio P"), r[bench]], axis=1).loc[a:b].iloc[1:]
        stress[name] = (1 + seg).prod() - 1
    stress = pd.DataFrame(stress).T.rename(columns={**short, bench: "Nifty 50"})
    ctx.fig(charts_ai.stress_figure(stress), "stress.png")
    result["risk"] = {
        "correlation_full": full.round(3).to_dict(), "correlation_5y": recent.round(3).to_dict(),
        "rolling_corr_window_days": window,
        "rolling_corr_range": {c: [round(float(roll[c].min()), 3), round(float(roll[c].max()), 3)] for c in roll},
        "risk_share_latest": contrib.iloc[-1].round(3).to_dict(), "weights": w.round(4).to_dict(),
        "stress": stress.round(4).to_dict(orient="index"),
    }

    # 3. Forecasts vs analyst consensus; earnings-surprise event study.
    session = make_session()
    consensus = _cached(out / "consensus.json", lambda: {t: fc.consensus(t, session) for t in stocks}, refresh)
    valuation = json.loads((out / "valuation.json").read_text(encoding="utf-8"))["securities"]
    wb = load_workbook(project_path("workbook/valuation.xlsx"), data_only=True)["Inputs"]
    eps_ttm = {t: float(wb[f"{c}17"].value) for t, c in zip(stocks, "BCD")}
    forecasts, events = {}, []
    for t in stocks:
        c, v = consensus[t], valuation[t]
        price = float(ctx.prices[t].iloc[-1])
        eps_next = (c.get("eps_estimates") or {}).get("+1y", {}).get("avg")
        comps_fwd = v["comps_value"] * eps_next / eps_ttm[t] if eps_next else None
        pt = c.get("price_targets") or {}
        forecasts[t] = {
            "price": price, "eps_ttm": eps_ttm[t], "consensus_eps": c.get("eps_estimates"),
            "analyst_target_mean": pt.get("mean"), "analyst_target_upside": pt["mean"] / price - 1 if pt.get("mean") else None,
            "analyst_target_range": [pt.get("low"), pt.get("high")],
            "our_comps_on_next_year_eps": comps_fwd, "our_comps_fwd_upside": comps_fwd / price - 1 if comps_fwd else None,
            "our_model_value": v["intrinsic_value"], "our_model_upside": v["intrinsic_value"] / price - 1,
            "our_blended_upside": v["upside_vs_latest"]["blended"],
        }
        dates = [s["date"] for s in c.get("surprises", [])]
        es = fc.event_study(r[t], r[bench], dates)
        if len(es):
            surprise = {s["date"]: s["surprise_pct"] for s in c["surprises"]}
            es["surprise_pct"] = es["date"].map(surprise)
            es["ticker"] = t
            events.append(es)
    events = pd.concat(events, ignore_index=True) if events else pd.DataFrame()
    if len(events):
        ctx.fig(charts_ai.event_figure(events, stocks, short), "event_study.png")
        pos, neg = events[events.surprise_pct > 0], events[events.surprise_pct < 0]
        slope = float(np.polyfit(events.surprise_pct / 100, events.car, 1)[0]) if len(events) > 2 else None
        result["event_study"] = {
            "events": len(events), "mean_car_positive_surprise": float(pos.car.mean()) if len(pos) else None,
            "mean_car_negative_surprise": float(neg.car.mean()) if len(neg) else None,
            "slope_car_on_surprise": slope,
            "correlation": float(events.surprise_pct.corr(events.car)),
            "rows": events.round(5).to_dict(orient="records"),
        }
    result["forecasts"] = forecasts

    # 4. AI ratio extraction, scored against Yahoo and Screener.
    extraction = json.loads(project_path("data/ai/ratio_extraction.json").read_text(encoding="utf-8"))
    yahoo = _cached(out / "yahoo_statements.json", lambda: {t: ec.yahoo_reference(t, session) for t in stocks}, refresh)
    banks = {t for t in stocks if "bank" in ctx.cfg["universe"]["stocks"][t]["valuation_method"]
             or "Bank" in ctx.cfg["universe"]["stocks"][t]["sector"]}
    scored = ec.score(extraction, yahoo, banks)
    (out / "extraction_accuracy.json").write_text(json.dumps(scored, indent=2), encoding="utf-8")
    result["extraction"] = {"counts": scored["counts"], "comparisons": scored["comparisons"],
                            "ratios": ec.ratios(extraction, banks)}

    # 5. Sentiment (text step) and the in-session framing tags.
    sent_path, tone_path = out / "sentiment.json", out / "transcript_tone.csv"
    if sent_path.exists() and tone_path.exists():
        sent = json.loads(sent_path.read_text(encoding="utf-8"))
        monthly = pd.DataFrame(sent["monthly_headline_tone"])
        calls = pd.read_csv(tone_path)
        ctx.fig(charts_ai.sentiment_figure(monthly, calls, stocks, short), "sentiment.png")
        result["sentiment"] = {"headlines": sent["headlines"],
                               "calls_mean": calls.groupby("ticker")[["management_tone", "analyst_tone", "tone_gap",
                                                                      "management_hedge_share"]].mean()
                               .round(3).to_dict(orient="index")}
    tags = pd.DataFrame(json.loads(project_path("data/ai/headline_framing.json").read_text(encoding="utf-8"))["tags"])
    sample = pd.read_csv(project_path("data/ai/headline_sample.csv"))
    d = sample.merge(tags, on="id")
    rel = d[d["relevant"]]
    cues = rel.explode("cues").dropna(subset=["cues"])
    result["framing"] = {
        "sample": len(d), "irrelevant_share": round(float(1 - d["relevant"].mean()), 3),
        "finbert_vs_llm_agreement": round(float((rel["label"] == rel["sentiment"]).mean()), 3),
        "confusion": pd.crosstab(rel["sentiment"], rel["label"]).to_dict(),
        "share_with_bias_cue": round(float((rel["cues"].str.len() > 0).mean()), 3),
        "cue_counts": cues.groupby(["ticker", "cues"]).size().unstack(fill_value=0).to_dict(orient="index"),
        "frame_mix": rel.groupby("ticker")["frame"].value_counts(normalize=True).round(3).unstack(fill_value=0)
        .to_dict(orient="index"),
    }
    (out / "ai_analysis.json").write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
    return result
