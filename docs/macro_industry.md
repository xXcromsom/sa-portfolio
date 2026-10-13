# Top-down analysis: economy → industry → company (BKM Ch 17)

Data as of 2 Oct 2026. Rows marked *judgement* are the group's reasoning, not data. Back them with concall evidence in Phase 3.

## 1. Economy

| Indicator | Latest | Source | What it means for the three stocks |
|---|---|---|---|
| Real GDP growth | **7.8%** in Q1 FY27 (Apr–Jun 2026), vs 6.9% a year earlier. Nominal: 10.3% | MOSPI press note, 31 Aug 2026 | A strong cycle, led by investment rather than consumption (next row) |
| Demand mix | Investment (GFCF) **+11.9%**, household consumption (PFCE) **+7.1%** | Same press note | Investment-led growth needs credit, which favours banks over consumer staples |
| CPI inflation | **4.82%** in Aug 2026, up from 3.93% in May. Food 5.95%; rural 5.23% vs urban 4.31% | MOSPI CPI (base 2024=100), as reported by secondary sources; *check against the MOSPI release* | Rising rural food inflation squeezes rural discretionary spending and FMCG input costs. It also leaves little room for further rate cuts |
| Policy repo rate | **5.25%** | RBI homepage, 1 Oct 2026 | Low rates support loan demand. *Judgement:* they also squeeze bank interest margins, because loans reprice faster than deposits |
| 91-day T-bill | **5.52%** | RBI, auction of 30 Sep 2026 | The risk-free rate used in CAPM (config.yaml) |
| USD/INR | **96.3**, rupee **8.4% weaker** than a year ago | Yahoo Finance `INR=X`, 2 Oct 2026 | Lifts IT exporters' rupee revenue. Raises FMCG's imported input costs (palm oil, crude-based packaging) |

## 2. Industry → company

| | Hindustan Unilever (FMCG) | Infosys (IT services) | ICICI Bank (private bank) |
|---|---|---|---|
| Main macro driver | Rural/domestic consumption, input inflation | USD/INR, US and European tech budgets | Credit growth, interest rates, asset quality |
| Industry life-cycle stage (*judgement*) | Mature and defensive | Mature; growth depends on client budgets; AI automation could shrink some services work | Growth stage; credit-to-GDP is still low, but the sector moves with the credit cycle |
| Porter's five forces (*judgement*) | Brands and distribution keep entry barriers high. Buyer power rises as modern trade and quick-commerce grow | Intense rivalry (TCS, HCL, Wipro, Accenture). Clients have strong bargaining power. Substitutes: AI tools and in-house capability centres | Intense rivalry from private banks and fintechs. Depositors act like suppliers, and competition for deposits is fierce. Regulation is a barrier to entry |
| Beta vs Nifty 50 (pipeline) | **0.60**, the lowest | 0.82 | **1.29**, the highest |
| Return and risk, 2016–2026 (pipeline) | CAGR 9.4%, volatility 22.0%, Sharpe 0.28 | CAGR 9.4%, volatility 26.9%, Sharpe 0.27 | CAGR 18.8%, volatility 29.8%, Sharpe 0.55 |
| 5-yr share price CAGR (Screener) | −7% (de-rated) | −9% (de-rated, P/E 13.5) | +14% |
| Valuation, blended (workbook) | −14% vs price. The market prices in 7.4% perpetual dividend growth | −2% vs price. Close to fair value | −35% vs price. The market prices in ~14% perpetual growth at a 14.7% cost of equity |

## 3. Draft thesis per stock (for the group to edit)

- **Hindustan Unilever: defensive anchor.** It has the lowest beta in the portfolio and stays steady when the cycle turns. At 39x earnings, the price already assumes about 7.4% dividend growth for ever, so HUL is a stability holding, not a value bet.
- **Infosys: a rupee hedge at a de-rated price.** A weaker rupee and a 4.6% dividend yield offset slower client spending. The price is close to our DDM value, so the risk is that growth slows further, not that the stock is overvalued.
- **ICICI Bank: growth engine.** It is the most direct play on India's investment-led cycle (GFCF +11.9%), with the highest return and Sharpe ratio. However, the current price needs about 14% perpetual growth at a CAPM cost of equity of 14.7%, so size it for that risk.

## 4. Candidates considered and rejected

| Candidate | Why not |
|---|---|
| HDFC Bank | The July 2023 merger with HDFC Ltd breaks the financial history, so ratios and growth rates before and after can't be compared. ICICI gives the same credit-cycle exposure with clean data. |
| ITC | The January 2025 hotels demerger distorts the price series, and its mix (cigarettes, FMCG, hotels, paper) needs a sum-of-the-parts valuation rather than one model. |
| TCS | Same macro driver as Infosys (USD/INR, US tech budgets), so holding both would raise correlation without adding a new risk factor. We kept Infosys for its lower P/E and higher dividend yield. |
| Nestlé India, Britannia | Same consumption driver as HUL. At P/Es of 68 and 44, they make the valuation lesson (price vs DDM value) more extreme rather than different. |
| Reliance Industries | A conglomerate (energy, telecom, retail). One dividend or P/B model can't value it, and it would need a segment-by-segment build. |
| Sun Pharma | A mix of the defensive driver (like HUL) and the USD-earner driver (like Infosys), so it overlaps two picks rather than adding a third factor. |

## 5. Selection check (PLAN_v2 §4)

| Criterion | Result |
|---|---|
| Different primary macro driver | Yes: consumption, the exchange rate, credit (table above) |
| Pairwise daily-return correlation of 0.5 or lower over 5 years | **Passes.** HUL/INFY 0.19, HUL/ICICI 0.20, INFY/ICICI 0.22 (pipeline, Aug 2021 – Oct 2026) |
| Liquid, with 8 or more quarters of concall transcripts | Yes: all three are Nifty 50 stocks, and Screener lists transcripts back to 2016 or earlier |
| Valuation method fits the business | DDM for the two high-payout firms. Book value and justified P/B for the bank (free cash flow is not meaningful for banks) |
