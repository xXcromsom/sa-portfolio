# Top-down analysis: economy → industry → company (BKM Ch 17)

Data as of 13 Oct 2026. Rows marked *judgement* are the group's reasoning, not data. Back them with concall evidence (Phase 3).

**Change on 13 Oct 2026:** Sun Pharma replaced Infosys, a group decision (see §4).

## 1. Economy

| Indicator | Latest | Source | What it means for the three stocks |
|---|---|---|---|
| Real GDP growth | **7.8%** in Q1 FY27 (Apr–Jun 2026), vs 6.9% a year earlier. Nominal: 10.3% | MOSPI press note, 31 Aug 2026 | A strong cycle, led by investment rather than consumption (next row) |
| Demand mix | Investment (GFCF) **+11.9%**, household consumption (PFCE) **+7.1%** | Same press note | Investment-led growth needs credit, which favours banks over consumer staples |
| CPI inflation | **5.54%** in Sep 2026, up from 4.83% in Aug and 3.93% in May | MOSPI CPI (base 2024=100), as reported in Zerodha's Aftermarket Report (12 Oct) and other secondary sources; *check against the MOSPI release* | Rising inflation squeezes FMCG volumes and input costs, and makes further rate cuts unlikely |
| Policy repo rate | **5.25%** | RBI homepage, 1 Oct 2026 | Low rates support loan demand. *Judgement:* they also squeeze bank interest margins, because loans reprice faster than deposits |
| 91-day T-bill | **5.52%** | RBI, auction of 30 Sep 2026 | The risk-free rate in CAPM (config.yaml) |
| USD/INR | **~₹96 per $**: 96.3 on 2 Oct (Yahoo), 95.75 on 12 Oct (Zerodha). The rupee is about 8% weaker than a year ago | Yahoo Finance `INR=X`; Zerodha Aftermarket Report | Lifts the rupee value of exporters' US sales (Sun Pharma). Raises FMCG's imported input costs |
| Market mood | Nifty 22,363 (12 Oct), 12.8% down over 200 sessions. Fear & Greed index **13, "extreme fear"** | Zerodha Aftermarket Report, 12 Oct; pipeline | Favours low-beta, non-cyclical holdings: the case for a defensive tilt |

## 2. Sector rotation: distance from moving averages

The table below is from Zerodha's Aftermarket Report (12 Oct 2026). It shows each sector index's % distance from its moving average.

| Sector | 20-day | 50-day | 100-day | 200-day |
|---|---|---|---|---|
| Media | +4.6% | +3.7% | +6.4% | **+11.2%** |
| **Pharma** | −1.7% | −1.9% | +1.0% | **+7.5%** |
| Healthcare | −3.0% | −4.0% | −2.4% | +2.9% |
| **Private Bank** | +0.4% | −0.8% | −0.9% | −1.1% |
| Bank | −0.9% | −3.1% | −3.0% | −3.6% |
| IT | −0.2% | −5.0% | −2.9% | −8.9% |
| **FMCG** | −2.2% | −5.3% | −7.9% | **−10.6%** |

Our own check (Yahoo, NSE sector indices, 13 Oct) agrees:
- **Nifty Pharma:** +6.9% above its 200-day average and **+14.8% over 200 sessions**.
- **Nifty 50:** −12.8% over 200 sessions.
- **Nifty IT:** −23.9% over 200 sessions.

**How we use this:** it is technical (momentum) evidence, and it belongs in the "is technical analysis possible?" test (Phase 3). It is not the reason for a pick. Choosing whatever led the last 200 days is recency and herding bias (BKM Ch 12), which is exactly why Media is *not* in the portfolio (§4).

## 3. Industry → company

| | Hindustan Unilever (FMCG) | Sun Pharma (Pharmaceuticals) | ICICI Bank (private bank) |
|---|---|---|---|
| Main macro driver | Rural/domestic consumption, input inflation | Chronic-therapy demand in India, US specialty and generics pricing, USD/INR | Credit growth, interest rates, asset quality |
| Life-cycle stage (*judgement*) | Mature and defensive | Defensive with growth: demand doesn't follow the economic cycle, and a global specialty business adds growth | Growth stage; credit-to-GDP is still low, but the sector moves with the credit cycle |
| Porter's five forces (*judgement*) | Brands and distribution keep entry barriers high. Buyer power rises as modern trade and quick-commerce grow | US FDA compliance and patents are high barriers. US buyers (consolidated distributors) have strong bargaining power. Indian price controls are a regulatory risk (12 Oct: a proposed 30% cap on trade margins for anti-cancer drugs) | Intense rivalry from private banks and fintechs. Depositors act like suppliers, and competition for deposits is fierce. Regulation is a barrier to entry |
| Beta vs Nifty 50 (pipeline) | **0.60** | **0.65** | **1.29** |
| Return and risk, 2016–2026 (pipeline) | CAGR 9.6%, volatility 22.0%, Sharpe 0.28 | CAGR 8.7%, volatility 27.2%, Sharpe 0.24, max drawdown −62% (deep 2015–19 slump) | CAGR 19.1%, volatility 29.7%, Sharpe 0.55 |
| Sector vs 200-day average (§2) | FMCG −10.6% (weakest) | Pharma +7.5% | Private Bank −1.1% |
| Valuation, blended (workbook) | −14% vs price (fairly valued). The market implies 7.4% perpetual dividend growth | −30% vs price. Residual income ₹748, peer P/E ₹1,702. The market implies 8.6% perpetual growth | −37% vs price. The market implies ~14% perpetual growth at a 14.7% cost of equity |

## 4. Draft thesis per stock (for the group to edit)

- **Hindustan Unilever: defensive anchor.** It has the lowest beta in the portfolio. Its sector is the weakest right now (−10.6% vs its 200-day average), so we are buying out-of-favour quality rather than chasing. At 39x earnings the price already assumes about 7.4% dividend growth for ever, so HUL is a stability holding, not a value bet.
- **Sun Pharma: defensive growth with a rupee hedge.**
  - Demand at home doesn't follow the economic cycle, and its US business earns in dollars.
  - Its beta is low (0.65), and it has the lowest correlation with the other two picks (0.15 / 0.20).
  - Valuation is the risk: at P/E 33 the market prices about 8.6% perpetual growth. Residual income says the price is high; peer multiples say it is fair.
- **ICICI Bank: growth engine.** It is the most direct play on India's investment-led cycle (GFCF +11.9%), with the highest return and Sharpe ratio. However, the current price needs about 14% perpetual growth at a CAPM cost of equity of 14.7%, so size it for that risk.

## 5. Candidates considered and rejected

| Candidate | Why not |
|---|---|
| **Infosys** (in the original line-up) | Replaced by Sun Pharma on 13 Oct. IT is the second-weakest sector (−8.9% vs 200-day) and de-rated on AI-disruption fears. Sun Pharma keeps the rupee hedge Infosys gave us, with a lower beta (0.65 vs 0.82) and a non-cyclical driver. |
| **Media** (e.g. Sun TV, PVR Inox, Zee) | The strongest sector (+11.2% vs 200-day), but on the class utility function a Balanced investor (A = 4) would refuse it. Media volatility of 31–51% gives certainty-equivalent returns of **−8% to −38%**, all below the 5.5% T-bill. The lead is momentum: PVR Inox is +32% above its 200-day average, Nazara +36%, while Zee and Network18 are below theirs. Liquidity is thin (₹12–238 Cr a day). Buying it now would be the recency/herding bias we warn against. |
| Cipla | The closest alternative to Sun Pharma, and the most defensive (beta 0.49, lowest correlation 0.10–0.12, smallest drawdown −43%). Rejected for smaller scale and a weaker specialty pipeline (*judgement*). |
| Dr Reddy's | Most exposed to US generic price erosion. |
| Divi's Laboratories | The best 10-year record, but +30% above its 200-day average at a P/E of 82, so picking it would be momentum-chasing. It is also a contract manufacturer (a different business model). |
| HDFC Bank | The July 2023 merger with HDFC Ltd breaks the financial history. ICICI gives the same credit-cycle exposure with clean data. |
| ITC | The January 2025 hotels demerger distorts the price series, and its conglomerate mix needs a sum-of-the-parts valuation. |
| Nestlé India, Britannia | Same consumption driver as HUL, at even higher P/Es (68 and 44). |
| Reliance Industries | A conglomerate (energy, telecom, retail) that one model can't value. |

## 6. Selection check (PLAN_v2 §4)

| Criterion | Result |
|---|---|
| Different primary macro driver | Yes: consumption, healthcare and exports, credit (table above) |
| Pairwise daily-return correlation of 0.5 or lower over 5 years | **Passes.** HUL/Sun 0.15, HUL/ICICI 0.20, Sun/ICICI 0.20 (pipeline, Sep 2021 – Oct 2026) |
| Liquid, with 6 or more quarters of concall transcripts | Yes: all three are Nifty 50 stocks, with 6–7 transcripts each in `data/raw/` |
| Valuation method fits the business | DDM for high-payout HUL. Residual income (book value) for low-payout Sun Pharma and for the bank, ICICI |
| **Honesty note** | Pharma was chosen partly *after* seeing its strong recent run. The 2023–26 out-of-sample test (Phase 2) therefore flatters the new line-up, and the report must say so. |
