# AI-Augmented Security Analysis: HUL, Sun Pharma, ICICI Bank

A group project for Security Analysis (BBAT35F97) at TAPMI. It values three NSE stocks using the course's methods, adds AI-based analysis, and builds a portfolio from them. The full plan is in `../PLAN_v2.md`.

**Status:** Phases 1–4 are done: data and traditional analysis, portfolio, AI-augmented analysis, and the dashboard. Phase 5 (report, deck) is next.

**Stocks:** Hindustan Unilever, Sun Pharma, ICICI Bank. Sun Pharma replaced Infosys on 13 Oct 2026; the reasons are in `docs/macro_industry.md` §5.

## Setup

```bash
pip install -r requirements-pipeline.txt
cp .env.example .env
python -m pytest
python -m pipeline.run_all --refresh
```

**Windows with Avast or other antivirus that scans HTTPS:** Yahoo downloads fail with `SSL certificate problem: unable to get local issuer certificate`. The antivirus re-signs certificates with its own root certificate. Windows trusts that root, but yfinance's HTTP library doesn't. To fix it, run `python scripts/build_ca_bundle.py` and keep `CA_BUNDLE=.certs/ca-bundle.pem` in `.env`. Certificates are still verified, against the same roots Windows already trusts.

## What the pipeline produces (`data/latest/`)

| File | Contents |
|---|---|
| `prices.parquet`, `prices_meta.json` | Adjusted daily closes from 2016 for the 3 stocks and the Nifty 50, plus which dates were dropped and which adjustments were made |
| `metrics.json`, `metrics_table.csv` | CAGR, mean return, volatility, Sharpe, Sortino, max drawdown, beta, Treynor, Jensen's α and the CAPM required return, plus the correlation and covariance matrices |
| `figures/sml.png` | The ex-post Security Market Line. Each stock's vertical gap to the line equals its Jensen's α |
| `valuation.json` | The workbook's model, comps and blended values, with upside recomputed against the latest close |
| `portfolio.json`, `figures/frontier.png`, `figures/indifference.png` | Efficient frontiers under history and forward-looking (CAPM) expected returns; the optimal risky portfolio P; CAL vs CML; complete portfolios and certainty equivalents for A = 2, 4, 6; an out-of-sample test |
| `mc.json`, `figures/mc_fan.png`, `figures/mc_hist.png` | One-year Monte Carlo of each profile: parametric (Cholesky), block bootstrap and current-volatility (EWMA) runs; percentiles, VaR/CVaR 95/99, probability of loss, drawdown distribution |
| `sip.json`, `figures/sip.png` | 15-year SIP: core-satellite equity (Nifty index + the 3 stocks) with a glide path; corpus percentiles and the probability of reaching ₹50 L / ₹75 L / ₹1 Cr |

**Phase 3: AI-augmented analysis.** Run `python -m pipeline.text_step` first; it's slow the first time, because FinBERT scores about 15k sentences. The main pipeline then assembles everything:

| Brief item | Output |
|---|---|
| AI ratio extraction from PDFs | `data/ai/ratio_extraction.json` (Claude read the FY26 annual reports), scored in `extraction_accuracy.json`: **44 of 47 comparisons within 1% of Yahoo/Screener, 0 extraction errors** |
| Sentiment on earnings calls and news | `sentiment.json`, `transcript_tone.csv` (FinBERT, management vs analysts); `data/ai/concall_aspects.json` (aspects and guidance); `figures/sentiment.png` |
| Behavioural bias and news framing | `data/ai/headline_framing.json`: 120 headlines tagged for framing, anchoring, authority, herding, hype, fear and recency, and compared with FinBERT |
| Forecasting; is technical analysis possible? | `figures/ta.png` (50/200-DMA and RSI rules vs buy-and-hold after costs); analyst consensus vs our targets; earnings-surprise event study (`figures/event_study.png`) |
| Risk heatmaps | `corr_heatmap.png`, `rolling_corr.png`, `risk_contrib.png`, `stress.png` |

Everything is summarised in `data/latest/ai_analysis.json`. Every prompt used is listed in `docs/ai_prompts.md`.

The valuation itself is in `workbook/valuation.xlsx`, which has live formulas:
- a two-stage DDM for HUL (high payout)
- a two-stage residual-income (P/B) model for Sun Pharma (low payout) and ICICI Bank (a bank)
- peer comparables
- r × g sensitivity grids

Edit the Inputs sheet in Excel and save, then run the pipeline. Supporting documents in `docs/`:
- `macro_industry.md`: the top-down analysis and rejected candidates
- `risk_questionnaire.md`: estimating each member's A
- `investment_policy_statement.md`: the long-term plan

## Dashboard (`app.py`)

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard has six tabs: Overview, Companies, Portfolio, AI insights, Risk, and Ask the portfolio. It reads only files already on disk, so a failed download can never blank a chart during the presentation. The risk-aversion slider recomputes y*, the complete portfolio's return and volatility, and the certainty equivalent for any A.

**Two datasets.** *Submission (frozen)* (`data/submission/`) holds the numbers in the report. *Latest* (`data/latest/`) is refreshed on weekdays. Freeze once the report's numbers are final:

```bash
python scripts/freeze.py
python scripts/check_dashboard.py
git add data/submission && git commit -m "Freeze submission data"
git tag submission-v1 && git push --tags
```

**Ask the portfolio.** Seven rehearsed questions are answered in `data/ai/qa_cache.json`, with no API key needed. Free-form questions go to Claude (`src/chat.py`) only when `ANTHROPIC_API_KEY` is set, as an environment variable or a Streamlit secret. The model is told to use only the dashboard's computed results and to cite the key behind every number. An optional `CHAT_PASSCODE` secret and a 10-question limit per session cap the cost.

**Automatic refresh** (`.github/workflows/refresh.yml`). The workflow runs on GitHub Actions at 18:00 IST, Monday to Friday. It re-downloads prices and consensus, then reruns the metrics, portfolio, Monte Carlo and SIP. On Saturdays it also rescores news headlines. It commits `data/latest` only after the pipeline's own validation, the tests and `scripts/check_dashboard.py` all pass. Otherwise the dashboard keeps the last good data. Transcript tone is not refreshed there, because the PDFs are not in the repository; rerun `python -m pipeline.text_step` locally after adding a new quarter's transcript.

**Hosting on Streamlit Community Cloud.**
1. Push this folder to a GitHub repository.
2. At share.streamlit.io, sign in with GitHub. Create the app from that repository, branch `main`, main file `app.py`.
3. Optionally, under Settings → Secrets, add:
   ```toml
   ANTHROPIC_API_KEY = "..."
   CHAT_PASSCODE = "..."
   ```
4. Each push (including the nightly data commit) redeploys the app automatically.

## Assumptions and known limitations

- **Risk-free rate:** the 91-day T-bill rate (5.52%, RBI, 30 Sep 2026) is applied to the whole 2016–2026 history. In reality the T-bill yield moved between about 3.3% and 6.9% over that period.
- **Benchmark:** Yahoo has no Nifty total-return series, so the benchmark is the price index plus a 1.22%/yr estimated dividend yield. That is the measured 2016–2026 gap between the Nifty BeES ETF and the index; the ETF itself is too noisy for daily beta. Beta is unaffected; alpha is lower by β × 1.22%. Replace this with the official Nifty 50 TRI when it's available.
- **Expected returns:** the history-based optimal portfolio puts 60% in ICICI (the past winner, i.e. hindsight). Weights estimated on 2016–2022 returned −0.7%/yr in 2023–26, against +7.4% for the Nifty TR. So the recommended P, the Monte Carlo and the SIP use CAPM required returns (rf + β × ERP), and the bootstrap is re-centred on them.
- **Monte Carlo:** returns are treated as stable over the horizon. The parametric mode also assumes normality; the bootstrap keeps fat tails and some clustering. Neither models regime shifts.
- **SIP:** pre-tax, no fees, and the debt sleeve earns today's T-bill rate throughout.
- **Ratio convention:** ratios use the arithmetic mean of excess returns × 252. CAGR is geometric.
- **Missing Nifty dates:** Yahoo skips 11 dates in the Nifty series (1 January sessions and weekend Diwali muhurat sessions). Those dates are dropped rather than forward-filled, so every return spans the same two closes for every series.
- **HUL demerger:** HUL's Kwality Wall's demerger (5 Dec 2025, 1:1) is not adjusted by Yahoo. Prices before that date are multiplied by 1 − 40.20/2462.20. The ₹40.20 is KWIL's implied price from NSE's special pre-open session. Without this fix, the value handed to shareholders would show up as a 5% one-day loss.
- **HUL earnings:** HUL's FY26 EPS includes a one-off gain of about ₹3,900 Cr. The valuation uses price ÷ Screener P/E (~₹47), which excludes it.
- **Cost of equity:** r = rf + β × ERP, with Damodaran's India ERP of 7.08%. The valuations are very sensitive to r and g, so see the Sensitivity sheet.
- **Data source:** yfinance is an unofficial Yahoo scraper. Every download is validated, and the pipeline writes nothing if validation fails.
