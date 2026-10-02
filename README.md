# AI-Augmented Security Analysis: HUL, Infosys, ICICI Bank

A group project for Security Analysis (BBAT35F97) at TAPMI. It values three NSE stocks using the course's methods, adds AI-based analysis, and builds a portfolio from them. The full plan is in `../PLAN_v2.md`.

**Status:** Phase 1 (data and traditional analysis) is done. Phases 2–5 are next.

## Setup

```bash
pip install -r requirements-pipeline.txt
cp .env.example .env
python -m pytest
python -m pipeline.run_all --refresh
```

**Windows with Avast or other antivirus that scans HTTPS:** Yahoo downloads fail with `SSL certificate problem: unable to get local issuer certificate`. The antivirus re-signs certificates with its own root certificate. Windows trusts that root, but yfinance's HTTP library doesn't. To fix it, run `python scripts/build_ca_bundle.py` and keep `CA_BUNDLE=.certs/ca-bundle.pem` in `.env`. Certificates are still verified, against the same roots Windows already trusts.

## What Phase 1 produces (`data/latest/`)

| File | Contents |
|---|---|
| `prices.parquet`, `prices_meta.json` | Adjusted daily closes from 2016 for the 3 stocks and the Nifty 50, plus which dates were dropped and which adjustments were made |
| `metrics.json`, `metrics_table.csv` | CAGR, mean return, volatility, Sharpe, Sortino, max drawdown, beta, Treynor, Jensen's α and the CAPM required return, plus the correlation and covariance matrices |
| `figures/sml.png` | The ex-post Security Market Line. Each stock's vertical gap to the line equals its Jensen's α |
| `valuation.json` | The workbook's model, comps and blended values, with upside recomputed against the latest close |

The valuation itself is in `workbook/valuation.xlsx`, which has live formulas:
- a two-stage DDM for HUL and Infosys
- a two-stage P/B (residual income) model for ICICI Bank
- peer comparables
- r × g sensitivity grids

Edit the Inputs sheet in Excel and save, then run the pipeline. The top-down analysis is in `docs/macro_industry.md`.

## Assumptions and known limitations

- **Risk-free rate:** the 91-day T-bill rate (5.52%, RBI, 30 Sep 2026) is applied to the whole 2016–2026 history. In reality the T-bill yield moved between about 3.3% and 6.9% over that period.
- **Benchmark:** the Nifty 50 *price* index, which excludes dividends. Jensen's α is overstated by roughly its dividend yield (~1–1.5% a year).
- **Ratio convention:** ratios use the arithmetic mean of excess returns × 252. CAGR is geometric.
- **Missing Nifty dates:** Yahoo skips 11 dates in the Nifty series (1 January sessions and weekend Diwali muhurat sessions). Those dates are dropped rather than forward-filled, so every return spans the same two closes for every series.
- **HUL demerger:** HUL's Kwality Wall's demerger (5 Dec 2025, 1:1) is not adjusted by Yahoo. Prices before that date are multiplied by 1 − 40.20/2462.20. The ₹40.20 is KWIL's implied price from NSE's special pre-open session. Without this fix, the value handed to shareholders would show up as a 5% one-day loss.
- **HUL earnings:** HUL's FY26 EPS includes a one-off gain of about ₹3,900 Cr. The valuation uses price ÷ Screener P/E (~₹47), which excludes it.
- **Cost of equity:** r = rf + β × ERP, with Damodaran's India ERP of 7.08%. The valuations are very sensitive to r and g, so see the Sensitivity sheet.
- **Data source:** yfinance is an unofficial Yahoo scraper. Every download is validated, and the pipeline writes nothing if validation fails.
