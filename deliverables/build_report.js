// Builds out/SA_Portfolio_Report.docx (4 pages + appendix) from the frozen dataset, styled on the
// group's reference report (CountryX_Strategic_Decision_Report.docx): A4, Calibri, navy tables.
//   node build_report.js                                        # numbers from data/submission
//   DASHBOARD_URL=https://....streamlit.app REPO_URL=https://github.com/... node build_report.js
const fs = require("fs");
const path = require("path");
const QRCode = require("qrcode");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  ImageRun, Footer, PageNumber, BorderStyle, LevelFormat, HeadingLevel, VerticalAlign, PageBreak,
} = require("docx");
const D = require("./data");

const URL = process.env.DASHBOARD_URL || null;
const REPO = process.env.REPO_URL || null;
const OUT = path.join(__dirname, "out", "SA_Portfolio_Report.docx");

const NAVY = "1D2C62", SLATE = "5A6590", ORANGE = "C84D00", CREAM = "FFFAED", BAND = "F7F1E3", TAN = "D9CBB0", SAND = "EADFC8";
const CONTENT = 11906 - 2 * 1247; // A4 width minus the reference report's side margins (DXA)
const PX = 96;                    // docx-js image sizes are pixels at 96 per inch

// ------------------------------------------------------------------ helpers
// Runs: a string, or [text, { b, i, c, s }] for bold / italic / colour / half-point size.
const runs = (parts, base = {}) => parts.map((x) => {
  const [t, o] = Array.isArray(x) ? x : [x, {}];
  return new TextRun({ text: t, bold: o.b ?? base.b, italics: o.i ?? base.i, color: o.c ?? base.c, size: o.s ?? base.s });
});
const P = (parts, o = {}) => new Paragraph({ children: runs([].concat(parts), o), spacing: { after: o.after ?? 100, before: o.before ?? 0 },
  alignment: o.align, keepNext: o.keepNext });
const H = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)], keepNext: true });
const bullet = (parts) => new Paragraph({ children: runs([].concat(parts)), numbering: { reference: "bullets", level: 0 }, spacing: { after: 40 } });
const caption = (text) => P([[text, { i: true, c: SLATE, s: 16 }]], { align: AlignmentType.CENTER, after: 120 });
const image = (file, widthIn, align = AlignmentType.CENTER) => {
  const { w, h } = pngSize(file);
  return new Paragraph({ alignment: align, keepNext: true, spacing: { after: 40 }, children: [new ImageRun({ type: "png",
    data: fs.readFileSync(file), transformation: { width: widthIn * PX, height: (widthIn * PX * h) / w } })] });
};
function pngSize(file) { const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; }

const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const line = (color) => ({ style: BorderStyle.SINGLE, size: 4, color });
// A data table in the reference style: navy header, banded cream rows, horizontal rules only.
function table(header, rows, widths, { align = [], boldFirst = true, size = 17 } = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cols = widths.map((w) => Math.round((w / total) * CONTENT));
  cols[cols.length - 1] += CONTENT - cols.reduce((a, b) => a + b, 0);
  const cell = (text, j, opts) => new TableCell({
    width: { size: cols[j], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: { fill: opts.fill, type: ShadingType.CLEAR, color: "auto" }, margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ keepNext: true, alignment: align[j] || AlignmentType.LEFT, children: runs([].concat(text), { s: size, b: opts.b, c: opts.c }) })],
  });
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA }, columnWidths: cols,
    borders: { top: none, left: none, right: none, insideVertical: none, bottom: line(TAN), insideHorizontal: line(SAND) },
    rows: [new TableRow({ tableHeader: true, cantSplit: true, children: header.map((h, j) => cell(h, j, { fill: NAVY, b: true, c: "FFFFFF" })) }),
      ...rows.map((r, i) => new TableRow({ cantSplit: true, children: r.map((c, j) => cell(c, j, { fill: i % 2 ? BAND : "FFFFFF", b: boldFirst && j === 0, c: NAVY })) }))],
  });
}
// The cream call-out box from the reference report.
function box(title, paragraphs) {
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA }, columnWidths: [CONTENT],
    borders: { top: line(TAN), bottom: line(TAN), left: line(TAN), right: line(TAN), insideHorizontal: none, insideVertical: none },
    rows: [new TableRow({ children: [new TableCell({ width: { size: CONTENT, type: WidthType.DXA },
      shading: { fill: CREAM, type: ShadingType.CLEAR, color: "auto" }, margins: { top: 140, bottom: 100, left: 200, right: 200 },
      children: [P([[title, { b: true, c: ORANGE }]], { after: 60 }), ...paragraphs] })] })],
  });
}
const gap = (after = 120) => new Paragraph({ children: [], spacing: { after } });
const R = (x) => D.rupee(x);
const AL = { L: AlignmentType.LEFT, R: AlignmentType.RIGHT, C: AlignmentType.CENTER };

async function build() {
  const sec = D.metrics.securities, val = D.valuation.securities, fc = D.ai.forecasts, rat = D.ai.extraction.ratios;
  const P_ = D.P, mkt = D.fwd.market, o = D.oos, prof = D.prof, icici = D.aspects["ICICIBANK.NS"].headline_numbers;
  const fr = D.ai.framing, es = D.ai.event_study, calls = D.calls, ex = D.extraction;
  const corr = D.metrics.correlation_full_sample;
  const pairs = [["HINDUNILVR.NS", "SUNPHARMA.NS"], ["HINDUNILVR.NS", "ICICIBANK.NS"], ["SUNPHARMA.NS", "ICICIBANK.NS"]].map(([a, b]) => corr[a][b]);
  const pairs5 = Object.values(D.metrics.correlation_check.pairs).map((p) => p.correlation ?? p);
  const range = (xs) => `${Math.min(...xs).toFixed(2)}–${Math.max(...xs).toFixed(2)}`;
  const w = (t) => D.pct(P_.weights[t]);
  const bal = D.sipRes.Balanced.Parametric;
  const goal = (p, m) => D.pct(D.goal(p, m, 7500000));
  const hulRoe = rat["HINDUNILVR.NS"].roe_continuing;

  const body = [];
  // ---------------------------------------------------------------- title block
  body.push(P([[`SECURITY ANALYSIS (BBAT35F97) · GROUP REPORT · DATA AS OF ${D.date(D.asOf).toUpperCase()}`, { b: true, c: ORANGE, s: 17 }]], { after: 40 }),
    P([["Pick, Price, Portfolio", { b: true, c: NAVY, s: 48 }]], { after: 40 }),
    P([["An AI-augmented security analysis of Hindustan Unilever, Sun Pharma and ICICI Bank, and the 15-year SIP we would build from them", { c: SLATE, s: 24 }]], { after: 80 }),
    P([["Investor: ", { b: true }], "us, TAPMI BBA(H) Semester V students starting a ₹10,000 monthly SIP.  ", ["Data: ", { b: true }],
      `Yahoo Finance, Screener, BSE filings, RBI, MOSPI, Damodaran, Google News; frozen on ${D.date(D.asOf)}.`], { s: 17, after: 160 }));
  body.push(box("Our recommendation", [
    P([`Own the three stocks as a satellite (HUL ${w("HINDUNILVR.NS")}, Sun Pharma ${w("SUNPHARMA.NS")}, ICICI Bank ${w("ICICIBANK.NS")}) around a Nifty 50 index core, `
      + `and buy them monthly rather than as a lump sum. All three trade above our blended intrinsic values (`
      + D.STOCKS.map((t) => `${D.SHORT[t]} ${D.spct(val[t].upside_vs_latest.blended)}`).join(", ")
      + `), so HUL is a `, ["Buy", { b: true }], " and Sun Pharma and ICICI Bank are ", ["Holds", { b: true }],
    `. A Balanced investor (A = 4) puts ${D.pct(prof.Balanced.y)} of savings into the three stocks and the rest into T-bills. A ₹10,000 SIP rising 10% a year `
      + `has a median 15-year value of ${D.lakh(bal.terminal_percentiles.p50)} from ${D.lakh(bal.total_invested)} invested.`], { after: 40 }),
  ]), gap(80));

  // ---------------------------------------------------------------- 1. selection
  body.push(H("1. Company selection: three sectors, three different drivers"),
    P(["We worked top-down (BKM Ch 17). India's real GDP grew 7.8% in Q1 FY27, led by investment (GFCF +11.9%) rather than household "
      + `consumption (+7.1%); the repo rate is 5.25% and the 91-day T-bill ${D.pct(D.portfolio.risk_free_rate, 2)} (MOSPI, RBI). We looked for `
      + "stocks with (i) a different primary macro driver, (ii) a five-year daily-return correlation of 0.5 or less with each other, (iii) Nifty 50 "
      + "liquidity and at least six quarters of call transcripts, and (iv) a business that a standard valuation model fits."]),
    table(["Company", "Sector and main driver", "Role in the portfolio", "Beta", "CAGR 2016–26", "Sharpe"], [
      ["Hindustan Unilever", "FMCG: consumption, input costs", "Defensive anchor: lowest beta, in the weakest sector (FMCG 10.6% below its 200-day average)",
        sec["HINDUNILVR.NS"].beta.toFixed(2), D.pct(sec["HINDUNILVR.NS"].cagr, 1), sec["HINDUNILVR.NS"].sharpe.toFixed(2)],
      ["Sun Pharma", "Pharma: chronic therapy, US specialty, USD/INR", "Defensive growth: demand ignores the cycle and US sales earn dollars",
        sec["SUNPHARMA.NS"].beta.toFixed(2), D.pct(sec["SUNPHARMA.NS"].cagr, 1), sec["SUNPHARMA.NS"].sharpe.toFixed(2)],
      ["ICICI Bank", "Private bank: credit growth, rates, asset quality", `Growth engine of an investment-led cycle: loans +${(icici.loan_growth * 100).toFixed(1)}% a year`,
        sec["ICICIBANK.NS"].beta.toFixed(2), D.pct(sec["ICICIBANK.NS"].cagr, 1), sec["ICICIBANK.NS"].sharpe.toFixed(2)],
      ["Nifty 50 (est. TR)", "Benchmark", "Price index + 1.22% a year estimated dividends", "1.00", D.pct(sec["^NSEI"].cagr, 1), sec["^NSEI"].sharpe.toFixed(2)],
    ], [17, 24, 37, 7, 9, 7], { align: [AL.L, AL.L, AL.L, AL.R, AL.R, AL.R] }),
    caption("Table 1. The three picks. Risk and return from daily data, 2016 to 13 Oct 2026."),
    P([`Pairwise correlations are ${range(pairs)} over 2016–2026 (${range(pairs5)} over five years), so the three diversify each other. `
      + "We rejected Media, the strongest sector (11.2% above its 200-day average): at A = 4 its certainty equivalents are −8% to −38%, "
      + "below the T-bill, and buying it now would be recency bias. Infosys, our first choice, was replaced by Sun Pharma, which keeps the "
      + "dollar hedge at a lower beta (0.65 vs 0.82); HDFC Bank's 2023 merger and ITC's 2025 demerger break their histories. ",
    ["Honesty note: ", { b: true }], "we chose Sun Pharma partly after its strong run, which flatters our 2023–26 back-test (§4)."]));

  // ---------------------------------------------------------------- 2. traditional analysis
  body.push(H("2. Traditional analysis: good companies at full prices"),
    P([`The cost of equity is the CAPM required return, r = rf + β × ERP, with rf = ${D.pct(D.portfolio.risk_free_rate, 2)} and Damodaran's India ERP of `
      + `${D.pct(D.metrics.assumptions.equity_risk_premium, 2)}. HUL pays out ${D.pct(rat["HINDUNILVR.NS"].payout)} of its profit, so we value it with a two-stage dividend `
      + `discount model. Sun Pharma (payout ${D.pct(rat["SUNPHARMA.NS"].payout)}) and ICICI Bank, whose borrowings are raw material, use a two-stage residual-income `
      + "model, equivalent to a justified P/B of (ROE − g) / (r − g). Peer multiples give a second view (P/E for HUL and Sun Pharma, "
      + "ROE-adjusted P/B for ICICI), and the blended value averages the two. Every working is a live formula in valuation.xlsx, with r × g sensitivity grids."]),
    table(["Stock", "Price", "r", "Model value", "Peer value", "Blended", "Blended vs price", "Implied growth", "Analyst target"],
      D.STOCKS.map((t) => [D.SHORT[t], R(val[t].latest_price), D.pct(val[t].cost_of_equity, 1), R(val[t].intrinsic_value), R(val[t].comps_value),
        R(val[t].blended_value), D.spct(val[t].upside_vs_latest.blended), D.pct(val[t].market_implied_growth, 1),
        `${R(fc[t].analyst_target_mean)} (${D.spct(fc[t].analyst_target_upside)})`]),
      [12, 9, 7, 10, 10, 10, 11, 10, 15], { align: [AL.L, ...Array(8).fill(AL.R)] }),
    caption("Table 2. Intrinsic value vs market price, 13 Oct 2026. Implied growth: the perpetual growth rate at which our model equals the price."),
    table(["Stock", "P/E", "P/B", "ROE", "Payout", "Beta", "Jensen's α", "Treynor", "Max drawdown", "Daily VaR 95%"],
      D.STOCKS.map((t) => [D.SHORT[t], (fc[t].price / fc[t].eps_ttm).toFixed(1), (fc[t].price / rat[t].bvps).toFixed(1),
        D.pct(t === "HINDUNILVR.NS" ? hulRoe : rat[t].roe, 1) + (t === "HINDUNILVR.NS" ? "*" : ""), D.pct(rat[t].payout),
        sec[t].beta.toFixed(2), D.spct(sec[t].jensen_alpha, 1), D.pct(sec[t].treynor, 1), D.pct(sec[t].max_drawdown), D.pct(sec[t].var_95_daily, 1)]),
      [14, 8, 8, 9, 9, 8, 11, 9, 12, 12], { align: [AL.L, ...Array(9).fill(AL.R)] }),
    caption("Table 3. Key ratios. FY26 fundamentals extracted from the annual reports (§3); market ratios 2016–2026. *HUL ROE excludes a one-off gain of about ₹3,900 Cr."));
  const alphaIcici = sec["ICICIBANK.NS"].jensen_alpha;
  body.push(new Table({
    width: { size: CONTENT, type: WidthType.DXA }, columnWidths: [Math.round(CONTENT * 0.5), CONTENT - Math.round(CONTENT * 0.5)],
    borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none },
    rows: [new TableRow({ children: [
      new TableCell({ width: { size: Math.round(CONTENT * 0.5), type: WidthType.DXA }, margins: { right: 120 },
        children: [image(D.figure("sml.png"), 3.15), caption("Figure 1. Ex-post Security Market Line, 2016–2026.")] }),
      new TableCell({ width: { size: CONTENT - Math.round(CONTENT * 0.5), type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, children: [
        P(["Every price is above our blended value, but reversing the models shows why. The market implies perpetual growth of "
          + D.STOCKS.map((t) => `${D.pct(val[t].market_implied_growth, 1)} (${D.SHORT[t]})`).join(", ")
          + `. ICICI is growing loans ${(icici.loan_growth * 100).toFixed(1)}% a year, so most of its gap is our ${D.pct(val["ICICIBANK.NS"].cost_of_equity, 1)} discount rate `
          + `(β ${sec["ICICIBANK.NS"].beta.toFixed(2)}), not unrealistic growth. Analysts are more bullish, with mean targets `
          + `${D.pct(Math.min(...D.STOCKS.map((t) => fc[t].analyst_target_upside)))}–${D.pct(Math.max(...D.STOCKS.map((t) => fc[t].analyst_target_upside)))} above the price.`]),
        P([`On the SML (Figure 1), ICICI earned a Jensen's α of ${D.spct(alphaIcici, 1)} a year above its CAPM return; HUL and Sun Pharma sit close to the line. `
          + "Past alpha is not a forecast, which is why the portfolio uses forward-looking CAPM returns (§4)."], { after: 0 }),
      ] }),
    ] })],
  }));

  // ---------------------------------------------------------------- 3. AI
  const gaps = D.STOCKS.map((t) => `${calls[t].tone_gap.toFixed(2)} (${D.SHORT[t]})`).join(", ");
  body.push(H("3. AI-augmented analysis: five tasks, each checked"),
    P(["We used AI where it reads or labels text faster than we can, and checked each task against an independent benchmark. Numbers are computed "
      + "in Python, never generated by a model. The prompts (P1–P5) and their outputs are saved in docs/ai_prompts.md and data/ai/."]),
    table(["Task (brief)", "What the AI did", "Checked against", "Result"], [
      ["Ratio extraction from PDFs", `Claude read the FY26 annual reports and returned ${ex.comparisons} line items as JSON, each with a page reference`,
        "Yahoo Finance and Screener", `${ex.counts.match} of ${ex.comparisons} within 1%; ${ex.counts["definition difference"]} definition differences (e.g. Yahoo's bank cash includes money at call); ${ex.counts["extraction error"]} errors`],
      ["Sentiment: calls and news", `FinBERT scored ${D.headlineCount.toLocaleString("en-IN")} headlines (12 months) and ${D.callSentences.toLocaleString("en-IN")} call sentences, split into management and analysts`,
        `Claude's call tone (P4): same sign on ${D.callToneAgreement.agree} of ${D.callToneAgreement.of} latest calls`, `Management sounds more positive than analysts on every call: gap ${gaps}`],
      ["Behavioural bias, news framing", `Claude tagged ${fr.sample} headlines for gain/loss framing, anchoring on targets, authority, herding, hype, fear and recency`,
        `FinBERT labels (${D.pct(fr.finbert_vs_llm_agreement)} agreement)`, `${D.pct(fr.share_with_bias_cue)} carry a bias cue, mostly authority and herding; ${D.pct(fr.irrelevant_share)} are not about the company; Sun Pharma coverage ${D.pct(fr.frame_mix["SUNPHARMA.NS"].gain)} gain-framed`],
      ["Forecasting; is TA possible?", "50/200-day trend and RSI rules after 0.25% costs; earnings event study (CAR[−1,+1]); consensus EPS and targets",
        "Buy-and-hold; earnings surprises", `${D.taWins} of ${D.taRules.length} rules beat buy-and-hold on Sharpe; ${D.spct(es.mean_car_positive_surprise, 1)} after beats, ${D.spct(es.mean_car_negative_surprise, 1)} after misses (${es.events} events)`],
      ["Risk heatmaps", "Correlation, 120-day rolling correlation, risk contribution, stress tests", "Four sell-offs since 2020",
        `ICICI supplies ${D.pct(D.ai.risk.risk_share_latest["ICICI Bank"])} of risk at ${w("ICICIBANK.NS")} weight; P fell less than the Nifty in ${D.stressBetter} of 4`],
    ], [17, 33, 17, 33]),
    caption("Table 4. The five AI tasks in the brief, with their checks."),
    image(D.figure("sentiment.png"), 5.9),
    caption("Figure 2. FinBERT tone: headlines by month (left) and earnings calls, management vs analysts (right)."),
    P([["What we learned. ", { b: true }], "AI made it practical to read every page and headline, but two findings argue for scepticism. Managements talk up "
      + `their results, so we discount call tone. Sun Pharma's coverage is ${D.pct(fr.frame_mix["SUNPHARMA.NS"].gain)} gain-framed and only ${D.pct(fr.frame_mix["SUNPHARMA.NS"].loss)} `
      + "loss-framed, the one-sided optimism our valuation warns about. And technical analysis is not profitable here after costs: the rules cut "
      + "drawdowns but lose return, consistent with weak-form efficiency, while prices absorb earnings news within days (semi-strong form)."]));

  // ---------------------------------------------------------------- 4. portfolio
  body.push(H("4. Portfolio and the long-term plan"),
    P([`We maximise the Sharpe ratio with 10–60% in each stock, using the 2016–26 covariance matrix. With historical mean returns, the optimiser pushes `
      + `ICICI to the ${D.pct(D.hist.weights["ICICIBANK.NS"])} cap (Sharpe ${D.hist.sharpe.toFixed(2)}), which is hindsight: weights fitted on 2016–22 earned `
      + `${D.pct(o["History-based P"].portfolio.cagr, 1)} a year in 2023–26, against ${D.pct(o["Equal weight"].market.cagr, 1)} for the Nifty. We therefore use `
      + `forward-looking CAPM expected returns, which give P = HUL ${w("HINDUNILVR.NS")}, Sun Pharma ${w("SUNPHARMA.NS")}, ICICI ${w("ICICIBANK.NS")}: `
      + `E(r) ${D.pct(P_.expected_return, 1)}, σ ${D.pct(P_.volatility, 1)}, Sharpe ${P_.sharpe.toFixed(2)}. Fitted the same way on 2016–22, they earned `
      + `${D.pct(o["Forward-looking P"].portfolio.cagr, 1)} a year out of sample.`]),
    image(D.figure("frontier.png"), 6.3),
    caption("Figure 3. Efficient frontier, CAL (T-bills + P) and CML (T-bills + Nifty) under historical and forward-looking expected returns."),
    P([`P's Sharpe ratio (${P_.sharpe.toFixed(2)}) is below the market's (${mkt.sharpe.toFixed(2)}): three stocks cannot match the index's diversification, so our CAL `
      + "lies under the CML. That is why the long-term plan is core-satellite. Each investor's share in P is y* = (E[rP] − rf) / (AσP²), capped "
      + "at 100% (no borrowing); the rest goes to T-bills."]),
    table(["Profile", "A", "Share in P", "E(rc)", "σc", "Certainty equiv.", "1-yr 95% VaR on ₹1 lakh", "P(loss), 1 yr", "15-yr SIP median", "P(≥ ₹75 lakh)"],
      ["Aggressive", "Balanced", "Conservative"].map((p) => {
        const par = D.mc.results.Parametric[p], boot = D.mc.results.Bootstrap[p], s = D.sipRes[p].Parametric;
        return [p, String(prof[p].risk_aversion), D.pct(prof[p].y), D.pct(prof[p].expected_return, 1), D.pct(prof[p].volatility, 1),
          D.pct(prof[p].certainty_equivalent, 1), `${R(par.var_95)} / ${R(boot.var_95)}`, `${D.pct(par.prob_loss)} / ${D.pct(boot.prob_loss)}`,
          D.lakh(s.terminal_percentiles.p50), `${goal(p, "Parametric")} / ${goal(p, "Bootstrap")}`];
      }), [12, 4, 8, 7, 7, 10, 18, 11, 12, 11], { align: [AL.L, ...Array(9).fill(AL.R)] }),
    caption("Table 5. Complete portfolios and their risk. Pairs are parametric (normal) / block-bootstrap Monte Carlo, 10,000 paths each."),
    image(D.figure("sip.png"), 6.3),
    caption("Figure 4. Corpus from a \u20B910,000 monthly SIP rising 10% a year: median, 25th\u201375th and 5th\u201395th percentiles, against money invested."),
    P([["Building it over the years. ", { b: true }], "Each of us estimates A with a short questionnaire (docs/risk_questionnaire.md) and starts a ₹10,000 SIP "
      + "that rises 10% a year: half into a Nifty 50 index fund and half into P, with equity gliding to 40% as the goal nears. Our Investment Policy "
      + "Statement sets the rules. Keep six months of expenses outside the portfolio. Rebalance yearly, with new money first. Review after every results "
      + "season. Never sell in the month after a 20% fall, and never buy because a stock has just risen. The bootstrap keeps real fat tails and "
      + "volatility clustering; its VaR is close to the normal model's, so fat tails matter little over one year."]));

  // ---------------------------------------------------------------- 5. recommendation
  const rec = D.recommendation;
  body.push(H("5. Recommendation, risks and limitations"),
    table(["Stock", "Call", "Range", "Price", "Why"], [
      ["Hindustan Unilever", rec["HINDUNILVR.NS"].action, `${R(rec["HINDUNILVR.NS"].low)}–${R(rec["HINDUNILVR.NS"].high)}`, R(rec["HINDUNILVR.NS"].price),
        "Fairly valued on our models; lowest beta; bought while its sector is out of favour"],
      ["Sun Pharma", rec["SUNPHARMA.NS"].action, `${R(rec["SUNPHARMA.NS"].low)}–${R(rec["SUNPHARMA.NS"].high)}`, R(rec["SUNPHARMA.NS"].price),
        "Residual income says expensive, peers say fair; momentum and one-sided coverage argue for patience"],
      ["ICICI Bank", rec["ICICIBANK.NS"].action, `${R(rec["ICICIBANK.NS"].low)}–${R(rec["ICICIBANK.NS"].high)}`, R(rec["ICICIBANK.NS"].price),
        `Highest expected return, but ${D.pct(D.ai.risk.risk_share_latest["ICICI Bank"])} of portfolio risk and a price that needs ${D.pct(val["ICICIBANK.NS"].market_implied_growth, 1)} growth for ever`],
    ], [17, 7, 16, 9, 51], { align: [AL.L, AL.L, AL.R, AL.R, AL.L] }),
    caption("Table 6. Calls. The range runs from our blended value to the analysts' mean target. Hold = add only through the SIP."),
    P([["Risks. ", { b: true }], `Concentration: ICICI is ${w("ICICIBANK.NS")} of the weight but ${D.pct(D.ai.risk.risk_share_latest["ICICI Bank"])} of the risk. `
      + "Valuation: all three prices assume high growth for ever. Regulation: a proposed cap on trade margins for anti-cancer drugs (Sun Pharma). "
      + "Cycle: a credit slowdown would hit ICICI and the Nifty together."], { after: 100 }),
    table(["Sell-off", "HUL", "Sun Pharma", "ICICI Bank", "Portfolio P", "Nifty 50"],
      Object.entries(D.stress).map(([ep, r]) => [ep, ...["HUL", "Sun Pharma", "ICICI Bank", "Portfolio P", "Nifty 50"].map((k) => D.spct(r[k], 1))]),
      [36, 12, 13, 13, 13, 13], { align: [AL.L, ...Array(5).fill(AL.R)] }),
    caption(`Table 7. Stress tests: price change through four real sell-offs. P fell less than the Nifty in ${D.stressBetter} of ${Object.keys(D.stress).length}.`),
    P([["Limitations. ", { b: true }], "One risk-free rate is applied to 2016–26; the Nifty total return is estimated (+1.22% a year); CAPM is a single-factor "
      + "model and forward returns depend on the ERP; the Monte Carlo assumes stable volatility and correlation; results are pre-tax and before fees; "
      + "and Sun Pharma was chosen after its run. This is coursework, not investment advice."]));

  // ---------------------------------------------------------------- appendix
  const qrPng = URL ? Buffer.from((await QRCode.toDataURL(URL, { margin: 1, width: 400, color: { dark: "#1D2C62", light: "#FFFFFF" } })).split(",")[1], "base64") : null;
  body.push(new Paragraph({ children: [new PageBreak()] }),
    P([["APPENDIX · NOT PART OF THE FOUR-PAGE REPORT", { b: true, c: ORANGE, s: 17 }]], { after: 40 }),
    H("A. How to view the dashboard"),
    ...(qrPng ? [new Paragraph({ alignment: AlignmentType.LEFT, children: [new ImageRun({ type: "png", data: qrPng, transformation: { width: 1.1 * PX, height: 1.1 * PX } })] })] : []),
    P([["Link: ", { b: true }], URL || "added once the app is deployed on Streamlit Community Cloud (see README)."]),
    bullet("If you see “This app has gone to sleep”, click the button; it loads in about a minute. Free apps sleep when idle."),
    bullet("The data selector opens on Submission, the numbers in this report. Latest is refreshed every weekday evening after the NSE close."),
    bullet("It opens with a 10-question risk questionnaire that sets your risk aversion A (or skip it with A = 4). The terminal then shows your portfolio in rupees, and every figure (allocation, one-year VaR, the 15-year SIP, stress losses) recomputes when you move A or the amount."),
    bullet("“Ask the portfolio” shows saved answers; live questions use a free OpenRouter model and cite the file behind each number."),
    P([["Code and data: ", { b: true }], REPO || "GitHub repository (link added once published); a ZIP of the tagged submission is attached."], { before: 60 }),
    H("B. What we submit"),
    table(["File", "Contents"], [
      ["SA_Portfolio_Report.pdf", "This report"],
      ["SA_Portfolio_Deck.pptx / .pdf", "The 10–12 minute presentation, with speaker notes"],
      ["valuation.xlsx", "DDM, residual income, peer multiples and sensitivity grids, as live formulas"],
      ["sa-portfolio (GitHub / ZIP)", "Python pipeline, tests, dashboard, AI outputs and the frozen data behind every number"],
    ], [30, 70]),
    gap(80),
    H("C. Data sources and AI steps"),
    table(["Source", "Used for"], [
      ["Yahoo Finance (yfinance)", "Daily prices 2016–2026, statements, analyst consensus, earnings dates"],
      ["Screener.in", "Ten-year financials; peer multiples"],
      ["BSE filings, company IR sites", "FY26 annual reports and 6–7 quarters of call transcripts per company"],
      ["RBI; MOSPI", `Risk-free rate (91-day T-bill, ${D.pct(D.portfolio.risk_free_rate, 2)}) and repo rate; GDP and demand mix`],
      ["Damodaran (Jan 2026)", `India equity risk premium, ${D.pct(D.metrics.assumptions.equity_risk_premium, 2)}`],
      ["Google News RSS; Zerodha Aftermarket Report", "12 months of headlines; sector distance from moving averages (12 Oct 2026)"],
      ["P1, P4, P5: Claude (Anthropic)", "Ratio extraction; call aspects and guidance; headline framing and bias tags"],
      ["P2, P3: FinBERT (ProsusAI/finbert)", "Sentence-level tone of calls and headlines"],
    ], [34, 66]),
  );

  const doc = new Document({
    creator: "TAPMI BBA(H) Semester V", title: "Pick, Price, Portfolio: HUL, Sun Pharma and ICICI Bank",
    styles: {
      default: { document: { run: { font: "Calibri", size: 20, color: "222222" }, paragraph: { spacing: { line: 252 } } } },
      paragraphStyles: [{ id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Calibri", size: 25, bold: true, color: NAVY }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 0 } }],
    },
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 360, hanging: 220 } } } }] }] },
    sections: [{
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, right: 1247, bottom: 1020, left: 1247, footer: 500 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [
        new TextRun({ text: "HUL · Sun Pharma · ICICI Bank · Security Analysis group report · page ", color: SLATE, size: 16 }),
        new TextRun({ children: [PageNumber.CURRENT], color: SLATE, size: 16 })] })] }) },
      children: body,
    }],
  });
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, await Packer.toBuffer(doc));
  console.log(`wrote ${OUT} (data as of ${D.asOf})`);
}

build().catch((e) => { console.error(e); process.exit(1); });
