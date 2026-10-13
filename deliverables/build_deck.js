// Builds out/SA_Portfolio_Deck.pptx from the frozen dataset. Styled on the group's reference
// deck (CountryX_Crisis_Strategy.pptx): cream and navy panels, burnt-orange display type,
// numbered cards, big stat callouts.
//   node build_deck.js                                   # numbers from data/submission
//   DASHBOARD_URL=https://....streamlit.app node build_deck.js   # adds QR codes
const path = require("path");
process.env.NODE_PATH = path.join(__dirname, "node_modules");
require("module").Module._initPaths(); // lets the skill's apply_theme.js find this folder's pptxgenjs

const fs = require("fs");
const pptxgen = require("pptxgenjs");
const QRCode = require("qrcode");
const D = require("./data");

const SKILL = process.env.PPTX_SKILL || "C:/Users/abhay.ABHAYSLAPTOP/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/603515dc-4b72-4f9a-b223-f734b83beecd/b2a81119-0cca-429f-b56c-4b6607e72c29/skills/pptx";
const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));

const URL = process.env.DASHBOARD_URL || null;
const OUT = path.join(__dirname, "out", "SA_Portfolio_Deck.pptx");

// Reference deck palette (measured from its XML).
const HEX = { navy: "1D2C62", cream: "FFFAED", slate: "5A6590", gold: "EBB24D", orange: "C84D00",
  teal: "3A7C74", brick: "B95142", tan: "D9CBB0", sand: "EADFC8", white: "FFFFFF" };
const THEME = { name: "SA Portfolio", headFontFace: "Arial", bodyFontFace: "Arial",
  colors: { dk1: HEX.navy, lt1: HEX.white, dk2: HEX.slate, lt2: HEX.cream, accent1: HEX.orange, accent2: HEX.gold,
    accent3: HEX.teal, accent4: HEX.brick, accent5: HEX.tan, accent6: HEX.sand, hlink: HEX.orange, folHlink: HEX.slate } };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "HUL, Sun Pharma and ICICI Bank: an AI-augmented security analysis";
pres.subject = "Security Analysis (BBAT35F97) group project";
pres.author = "TAPMI BBA(H) Semester V";
pres.company = "TAPMI";
const C = pres.SchemeColor;
const NAVY = C.text1, SLATE = C.text2, WHITE = C.background1, CREAM = C.background2;
const ORANGE = C.accent1, GOLD = C.accent2, TEAL = C.accent3, BRICK = C.accent4, TAN = C.accent5, SAND = C.accent6;

const W = 13.333, M = 0.6;
const STRAP = "HUL \u00B7 SUN PHARMA \u00B7 ICICI BANK";
const PANEL_R = 8.9;  // left edge of the right-hand navy panel
const PANEL_L = 4.4;  // width of the left-hand navy panel

// ------------------------------------------------------------------ layouts
const strap = (color, x, w) => ({ text: { text: STRAP, options: { x, y: 0.42, w, h: 0.3, fontSize: 9, bold: true,
  color, align: "right", charSpacing: 1.5, margin: 0, isTextBox: true } } });
const ph = (name, type, o) => ({ placeholder: { options: { name, type, margin: 0, valign: "top", align: "left", ...o }, text: "" } });
const label = (color, w) => ph("label", "body", { x: M, y: 0.42, w, h: 0.3, fontSize: 10, bold: true, color });
const title = (color, w, x = M) => ph("title", "title", { x, y: 0.8, w, h: 1.05, fontSize: 28, bold: true, color });
const sub = (color, w, x = M, y = 1.95) => ph("sub", "body", { x, y, w, h: 0.5, fontSize: 14, color });
const slideNo = (color) => ({ x: W - 1.1, y: 6.98, w: 0.5, h: 0.3, fontSize: 9, color, align: "right" });

pres.defineSlideMaster({ title: "COVER", background: { color: CREAM }, objects: [
  { rect: { x: 8.43, y: 0, w: W - 8.43, h: 7.5, fill: { color: NAVY } } }, strap(WHITE, 9.0, 3.73),
  label(NAVY, 7.4),
  ph("title", "title", { x: M, y: 1.15, w: 7.6, h: 1.15, fontSize: 60, bold: true, color: ORANGE }),
  ph("sub", "body", { x: M, y: 2.5, w: 7.3, h: 1.35, fontSize: 24, bold: true, color: NAVY }),
] });
pres.defineSlideMaster({ title: "CREAM", background: { color: CREAM }, slideNumber: slideNo(SLATE), objects: [
  strap(SLATE, 8.4, 4.33), label(ORANGE, 7.4), title(ORANGE, 12.1), sub(NAVY, 12.1)] });
pres.defineSlideMaster({ title: "NAVY", background: { color: NAVY }, slideNumber: slideNo(TAN), objects: [
  strap(WHITE, 8.4, 4.33), label(GOLD, 7.4), title(WHITE, 12.1), sub(CREAM, 12.1)] });
pres.defineSlideMaster({ title: "PANEL_RIGHT", background: { color: CREAM }, slideNumber: slideNo(TAN), objects: [
  { rect: { x: PANEL_R, y: 0, w: W - PANEL_R, h: 7.5, fill: { color: NAVY } } }, strap(WHITE, 9.3, 3.43),
  label(ORANGE, 7.9), title(ORANGE, 7.9), sub(NAVY, 7.9)] });
pres.defineSlideMaster({ title: "PANEL_LEFT", background: { color: CREAM }, slideNumber: slideNo(SLATE), objects: [
  { rect: { x: 0, y: 0, w: PANEL_L, h: 7.5, fill: { color: NAVY } } }, strap(SLATE, 8.4, 4.33),
  label(GOLD, PANEL_L - 2 * M), title(WHITE, PANEL_L - 2 * M), sub(CREAM, PANEL_L - 2 * M, M, 1.95)] });

// ------------------------------------------------------------------ helpers
const text = (slide, value, o) => slide.addText(value, { isTextBox: true, margin: 0, valign: "top", ...o });
const card = (slide, x, y, w, h, name, fill = WHITE) =>
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: SAND, width: 0.75 }, objectName: name });
const rule = (slide, x, y, w, color = TAN) =>
  slide.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color, width: 0.75 } });
const source = (slide, value, w = 11.4, color = SLATE) => text(slide, value, { x: M, y: 6.98, w, h: 0.3, fontSize: 10, color });
const fill = (slide, l, t, s) => {
  if (l) slide.addText(l, { placeholder: "label", charSpacing: 1.5 });
  if (t) slide.addText(t, { placeholder: "title" });
  if (s) slide.addText(s, { placeholder: "sub" });
};
const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt",
  dataLabelFontFace: "+mn-lt" };
const qr = async (url) => (await QRCode.toDataURL(url, { margin: 1, width: 600, color: { dark: "#1D2C62", light: "#FFFFFF" } }))
  .replace(/^data:/, "");
const w100 = (t) => Math.round(D.P.weights[t] * 100);
const weights = D.STOCKS.map(w100).join(" \u00B7 ");
const spoken = (items) => items.slice(0, -1).join(", ") + " and " + items[items.length - 1];

async function build() {
  const qrData = URL ? await qr(URL) : null;
  const balanced = D.sipRes.Balanced;
  const invested = balanced.Parametric.total_invested;
  const median = balanced.Parametric.terminal_percentiles.p50;
  const corr = D.metrics.correlation_full_sample;
  const pairs = [["HINDUNILVR.NS", "SUNPHARMA.NS"], ["HINDUNILVR.NS", "ICICIBANK.NS"], ["SUNPHARMA.NS", "ICICIBANK.NS"]]
    .map(([a, b]) => corr[a][b]);
  const corrRange = `${Math.min(...pairs).toFixed(2)}\u2013${Math.max(...pairs).toFixed(2)}`;
  const sec = D.metrics.securities;
  const val = D.valuation.securities;
  const icici = D.aspects["ICICIBANK.NS"].headline_numbers;

  // ================================================================ 1. cover
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "COVER", sectionTitle: "Opening" });
  fill(s, `SECURITY ANALYSIS (BBAT35F97) \u00B7 DATA AS OF ${D.date(D.asOf).toUpperCase()}`, "\u20B910,000 A MONTH",
    "INTO HUL, SUN PHARMA AND ICICI BANK: HOW A STUDENT SHOULD OWN THEM");
  text(s, `Median 15-year corpus ${D.lakh(median)} from ${D.lakh(invested)} invested, for a Balanced investor (A = 4), `
    + "from a 10,000-path Monte Carlo of our portfolio.", { x: M, y: 3.95, w: 7.2, h: 0.9, fontSize: 14, color: SLATE });
  [[`${D.P.sharpe.toFixed(2)} vs ${D.fwd.market.sharpe.toFixed(2)}`, "SHARPE RATIO: OUR 3 STOCKS VS THE NIFTY"],
    [`${D.extraction.counts.match} / ${D.extraction.comparisons}`, "AI-EXTRACTED FIGURES WITHIN 1%"],
    [`${D.taWins} of ${D.taRules.length}`, "TRADING RULES THAT BEAT BUY-AND-HOLD"]].forEach(([v, l], i) => {
    const x = M + i * 2.45;
    text(s, v, { x, y: 5.15, w: 2.3, h: 0.5, fontSize: 24, bold: true, color: NAVY });
    text(s, l, { x, y: 5.68, w: 2.2, h: 0.5, fontSize: 10, bold: true, color: SLATE });
  });
  text(s, "TAPMI \u00B7 BBA(H) SEMESTER V \u00B7 GROUP PROJECT", { x: M, y: 6.75, w: 7.4, h: 0.3, fontSize: 10, bold: true,
    color: NAVY, charSpacing: 1.5 });
  text(s, "OUR ANSWER IN THREE MOVES", { x: 9.0, y: 1.35, w: 3.7, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5 });
  const moves = [["PICK", `Three sectors, three macro drivers, correlations of ${corrRange}`],
    ["PRICE", "All three trade above our blended value, so we buy slowly, through a SIP"],
    ["PORTFOLIO", `${weights} satellite around a Nifty 50 index core`]];
  moves.forEach(([h, d], i) => {
    const y = 1.85 + i * 1.22;
    text(s, `0${i + 1}`, { x: 9.0, y: y + 0.05, w: 0.5, h: 0.3, fontSize: 11, bold: true, color: GOLD });
    text(s, h, { x: 9.55, y, w: 3.2, h: 0.4, fontSize: 20, bold: true, color: WHITE });
    text(s, d, { x: 9.55, y: y + 0.45, w: 3.2, h: 0.55, fontSize: 12, color: SAND });
    rule(s, 9.0, y + 1.08, 3.73);
  });
  if (qrData) {
    s.addImage({ data: qrData, x: 9.0, y: 5.75, w: 1.0, h: 1.0, objectName: "qr-dashboard" });
    text(s, ["TRY THE DASHBOARD", URL.replace(/^https?:\/\//, "")].map((v, i) => ({ text: v, options: {
      bold: i === 0, fontSize: i === 0 ? 10 : 11, color: i === 0 ? GOLD : WHITE, breakLine: i === 0 } })),
      { x: 10.15, y: 5.95, w: 2.6, h: 0.6 });
  }
  s.addNotes("[0:30] Ten thousand rupees a month. That is what each of us expects to invest after graduation, and this "
    + "project asks one question: should that money own Hindustan Unilever, Sun Pharma and ICICI Bank, and how? Our answer "
    + `has three moves. Pick three businesses whose returns don't move together. Price them honestly: all three trade above `
    + `our blended values, so we buy slowly. And size the portfolio to each of us: ${weights.replace(/ \u00B7 /g, ", ")} `
    + "percent, as a satellite around a Nifty index core.");

  // ================================================================ 2. the picks
  pres.addSection({ title: "Analysis" });
  s = pres.addSlide({ masterName: "PANEL_RIGHT", sectionTitle: "Analysis" });
  fill(s, "01 - THE PICKS", "THREE SECTORS, THREE DIFFERENT DRIVERS",
    "Top-down: an investment-led economy, then three businesses driven by different demand.");
  D.macro.forEach((m, i) => {
    const x = M + i * (1.84 + 0.17);
    card(s, x, 2.55, 1.84, 0.98, `macro-${i}`);
    text(s, m.value, { x: x + 0.15, y: 2.65, w: 1.6, h: 0.42, fontSize: 22, bold: true, color: ORANGE });
    text(s, m.label, { x: x + 0.15, y: 3.08, w: 1.6, h: 0.4, fontSize: 10, bold: true, color: SLATE });
  });
  const picks = [
    ["HINDUNILVR.NS", "FMCG", TEAL, WHITE, "Defensive anchor", "Lowest beta in the weakest sector: out-of-favour quality."],
    ["SUNPHARMA.NS", "PHARMA", GOLD, NAVY, "Defensive growth", "Demand ignores the cycle; US sales earn dollars."],
    ["ICICIBANK.NS", "PRIVATE BANK", ORANGE, WHITE, "Growth engine",
      `The direct play on investment-led growth: loans +${(icici.loan_growth * 100).toFixed(1)}%.`],
  ];
  picks.forEach(([t, sector, chip, chipText, role, thesis], i) => {
    const x = M + i * (2.52 + 0.165), y = 3.75;
    card(s, x, y, 2.52, 2.95, `pick-${D.SHORT[t]}`);
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.18, y: y + 0.2, w: 1.45, h: 0.3, fill: { color: chip }, line: { color: chip, width: 0 } });
    text(s, sector, { x: x + 0.18, y: y + 0.2, w: 1.45, h: 0.3, fontSize: 10, bold: true, color: chipText, align: "center",
      valign: "middle", charSpacing: 1 });
    text(s, D.LONG[t], { x: x + 0.18, y: y + 0.65, w: 2.2, h: 0.4, fontSize: 17, bold: true, color: NAVY });
    text(s, role.toUpperCase(), { x: x + 0.18, y: y + 1.1, w: 2.2, h: 0.28, fontSize: 10, bold: true, color: ORANGE, charSpacing: 1 });
    text(s, thesis, { x: x + 0.18, y: y + 1.45, w: 2.2, h: 1.0, fontSize: 14, color: NAVY });
    text(s, `\u03B2 ${sec[t].beta.toFixed(2)} \u00B7 CAGR ${D.pct(sec[t].cagr, 1)}`, { x: x + 0.18, y: y + 2.5, w: 2.2, h: 0.28,
      fontSize: 11, bold: true, color: SLATE });
  });
  text(s, "WHY THEY BELONG TOGETHER", { x: 9.3, y: 1.35, w: 3.5, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5 });
  text(s, corrRange, { x: 9.3, y: 1.7, w: 3.5, h: 0.75, fontSize: 40, bold: true, color: WHITE });
  text(s, "PAIRWISE CORRELATIONS, 2016\u20132026", { x: 9.3, y: 2.45, w: 3.5, h: 0.3, fontSize: 10, bold: true, color: SAND });
  text(s, `Betas of ${D.STOCKS.map((t) => sec[t].beta.toFixed(2)).join(", ")}: two defensives and one cyclical.`,
    { x: 9.3, y: 2.8, w: 3.5, h: 0.6, fontSize: 12, color: SAND });
  rule(s, 9.3, 3.55, 3.5);
  text(s, "WHAT WE REJECTED", { x: 9.3, y: 3.75, w: 3.5, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5 });
  [["MEDIA", "Strongest sector (+11.2% vs 200-day), but its certainty equivalent at A = 4 is \u22128% to \u221238%: chasing it is recency bias."],
    ["INFOSYS", "IT is 8.9% below its 200-day; Sun keeps the dollar hedge at a lower beta."],
    ["HDFC BANK", "The 2023 merger breaks its history."]].forEach(([h, d], i) => {
    const y = [4.1, 5.25, 6.1][i];
    text(s, [{ text: h, options: { bold: true, color: WHITE, fontSize: 13, breakLine: true } },
      { text: d, options: { color: SAND, fontSize: 12 } }], { x: 9.3, y, w: 3.5, h: [1.05, 0.8, 0.55][i] });
  });
  source(s, "Sources: MOSPI, RBI, Zerodha Aftermarket Report (12 Oct 2026). Full funnel: docs/macro_industry.md.", 8.1);
  s.addNotes("[1:30] We worked top-down. The economy is growing 7.8%, led by investment, up 11.9%, rather than consumption. "
    + "So we wanted three different engines. ICICI Bank is the credit engine of an investment-led cycle. Hindustan Unilever "
    + `is the defensive anchor: the lowest beta, ${sec["HINDUNILVR.NS"].beta.toFixed(2)}, in the weakest sector right now, so we are buying `
    + "out-of-favour quality rather than chasing. Sun Pharma's demand doesn't follow the cycle, and its US business earns "
    + `dollars. The proof that they diversify each other: pairwise correlations of only ${corrRange}. Just as important is `
    + "what we rejected. Media was the strongest sector, 11% above its 200-day average. But on our class utility function a "
    + "balanced investor would refuse it, with certainty equivalents of minus 8 to minus 38 percent. Buying it would be "
    + "recency bias, the behaviour our own policy statement bans.");

  // ================================================================ 3. valuation
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Analysis" });
  fill(s, "02 - VALUATION", "PRICED FOR MORE GROWTH THAN WE CAN JUSTIFY",
    "Intrinsic value from our Excel models at CAPM discount rates, against today's price and the analysts' targets.");
  card(s, M, 2.5, 7.75, 4.3, "valuation-chart-card");
  const names = D.STOCKS.map((t) => D.SHORT[t]);
  s.addChart(pres.charts.BAR, [
    { name: "Price", labels: names, values: D.STOCKS.map((t) => val[t].latest_price) },
    { name: "Our model", labels: names, values: D.STOCKS.map((t) => val[t].intrinsic_value) },
    { name: "Peer multiples", labels: names, values: D.STOCKS.map((t) => val[t].comps_value) },
    { name: "Analyst mean target", labels: names, values: D.STOCKS.map((t) => D.ai.forecasts[t].analyst_target_mean) },
  ], { x: M + 0.15, y: 2.6, w: 7.45, h: 4.1, barDir: "col", barGrouping: "clustered", barGapWidthPct: 55,
    chartColors: [HEX.navy, HEX.orange, HEX.gold, HEX.teal], showLegend: true, legendPos: "t", legendFontSize: 11,
    legendColor: HEX.navy, showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: HEX.navy,
    dataLabelFormatCode: "#,##0", catAxisLabelColor: HEX.navy, catAxisLabelFontSize: 12, valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, catAxisLineShow: true,
    catAxisLineColor: HEX.tan, objectName: "valuation-chart", ...chartText });
  D.STOCKS.forEach((t, i) => {
    const y = 2.5 + i * 1.12, v = val[t];
    text(s, D.spct(v.upside_vs_latest.blended), { x: 8.7, y, w: 1.55, h: 0.6, fontSize: 30, bold: true,
      color: v.upside_vs_latest.blended < -0.15 ? ORANGE : TEAL });
    text(s, "BLENDED VS PRICE", { x: 8.7, y: y + 0.6, w: 1.55, h: 0.3, fontSize: 10, bold: true, color: SLATE });
    text(s, [{ text: D.LONG[t], options: { bold: true, fontSize: 14, color: NAVY, breakLine: true } },
      { text: `Price implies ${D.pct(v.market_implied_growth, 1)} growth a year for ever, at r = ${D.pct(v.cost_of_equity, 1)}`,
        options: { fontSize: 12, color: SLATE } }], { x: 10.35, y, w: 2.4, h: 1.0 });
  });
  card(s, 8.7, 5.9, 4.03, 0.9, "valuation-callout", NAVY);
  text(s, `ICICI grew loans ${(icici.loan_growth * 100).toFixed(1)}% last quarter. The gap is mostly our ${D.pct(val["ICICIBANK.NS"].cost_of_equity, 1)} `
    + `cost of equity (\u03B2 ${sec["ICICIBANK.NS"].beta.toFixed(2)}), not unrealistic growth.`,
    { x: 8.85, y: 5.98, w: 3.75, h: 0.75, fontSize: 12, color: WHITE, valign: "middle" });
  source(s, "Two-stage DDM (HUL), two-stage residual income (Sun Pharma, ICICI Bank), peer P/E and ROE-adjusted P/B: workbook/valuation.xlsx. "
    + "Blended = average of model and peer values. Analyst targets: Yahoo Finance consensus.");
  s.addNotes("[1:30] Excel is our source of truth: a two-stage dividend discount model for HUL, which pays out most of its "
    + "profit, and residual income for Sun Pharma and for ICICI, a bank. Against today's prices, the blended values are "
    + spoken(D.STOCKS.map((t, i) => `${D.pct(-val[t].upside_vs_latest.blended)}${i ? "" : " below"} for ${D.SHORT[t]}`))
    + ". So is the market wrong? Reverse the model and ask what growth the price implies: "
    + spoken(D.STOCKS.map((t, i) => `${D.pct(val[t].market_implied_growth, 1)}${i ? "" : " a year for ever"} for ${D.SHORT[t]}`))
    + `. ICICI grew loans ${(icici.loan_growth * 100).toFixed(1)}% last quarter, so its implied growth is not crazy; the gap comes mostly from our `
    + `${D.pct(val["ICICIBANK.NS"].cost_of_equity, 1)} cost of equity, driven by a beta of ${sec["ICICIBANK.NS"].beta.toFixed(2)}. Analysts are far more `
    + "bullish, with mean targets well above the price. Our honest reading: good companies at full prices.");

  // ================================================================ 4. AI tasks
  s = pres.addSlide({ masterName: "NAVY", sectionTitle: "Analysis" });
  fill(s, "03 - AI-AUGMENTED ANALYSIS", "FIVE AI TASKS, EACH CHECKED AGAINST A BENCHMARK",
    "AI reads and labels; Python computes every number. Each task reports how far it can be trusted.");
  const fr = D.ai.framing, ex = D.extraction.counts;
  const hulGap = D.calls["HINDUNILVR.NS"].tone_gap;
  const tasks = [
    ["RATIO EXTRACTION", TEAL, WHITE, "Claude reads the FY26 annual reports and returns line items as JSON.",
      "Yahoo Finance and Screener.", `${ex.match} / ${D.extraction.comparisons}`,
      `within 1%; ${ex["extraction error"]} extraction errors`],
    ["SENTIMENT", ORANGE, WHITE, `FinBERT scores ${D.headlineCount.toLocaleString("en-IN")} headlines and ${D.callSentences.toLocaleString("en-IN")} call sentences.`,
      "Management vs analysts on every call.", `+${hulGap.toFixed(2)}`, "HUL tone gap: management far more upbeat"],
    ["BIAS & FRAMING", GOLD, NAVY, `An LLM tags ${fr.sample} headlines for framing, authority, herding and hype.`,
      `${D.pct(fr.finbert_vs_llm_agreement)} agreement with FinBERT.`, D.pct(fr.share_with_bias_cue),
      `carry a bias cue; ${D.pct(fr.irrelevant_share)} aren't about the company`],
    ["FORECASTING", BRICK, WHITE, "Moving-average and RSI rules, an earnings event study, analyst consensus.",
      "Buy-and-hold, after a 0.25% trading cost.", `${D.taWins} of ${D.taRules.length}`, "trading rules beat buy-and-hold"],
    ["RISK HEATMAPS", SLATE, WHITE, "Correlation, rolling correlation, risk contribution, stress tests.",
      "Four real sell-offs since 2020.", D.pct(D.ai.risk.risk_share_latest["ICICI Bank"]), "of portfolio risk is ICICI, at 50% weight"],
  ];
  tasks.forEach(([name, head, headText, what, check, result, caption], i) => {
    const x = M + i * (2.29 + 0.17), y = 2.55;
    card(s, x, y, 2.29, 4.25, `ai-task-${i + 1}`);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.29, h: 0.75, fill: { color: head }, line: { color: head, width: 0 } });
    text(s, [{ text: `0${i + 1}`, options: { fontSize: 10, bold: true, breakLine: true } }, { text: name, options: { fontSize: 14, bold: true } }],
      { x: x + 0.15, y: y + 0.1, w: 2.0, h: 0.6, color: headText });
    text(s, [{ text: "WHAT", options: { fontSize: 10, bold: true, color: SLATE, breakLine: true } },
      { text: what, options: { fontSize: 12, color: NAVY } }], { x: x + 0.15, y: y + 0.9, w: 2.0, h: 1.15 });
    text(s, [{ text: "CHECKED AGAINST", options: { fontSize: 10, bold: true, color: SLATE, breakLine: true } },
      { text: check, options: { fontSize: 12, color: NAVY } }], { x: x + 0.15, y: y + 2.1, w: 2.0, h: 0.85 });
    rule(s, x + 0.15, y + 3.0, 2.0, SAND);
    text(s, result, { x: x + 0.15, y: y + 3.08, w: 2.0, h: 0.55, fontSize: 26, bold: true, color: ORANGE });
    text(s, caption, { x: x + 0.15, y: y + 3.62, w: 2.0, h: 0.55, fontSize: 11, color: SLATE });
  });
  source(s, "Prompts: docs/ai_prompts.md. Extraction: data/ai/ratio_extraction.json (page references for every figure). "
    + "FinBERT: ProsusAI/finbert. Headlines: Google News RSS, last 12 months.", 11.4, TAN);
  s.addNotes(`[1:00] The brief asked how AI can augment this, so we ran five tasks, and each one is checked against `
    + `something independent. Claude read the FY26 annual reports and extracted ${D.extraction.comparisons} numbers: ${ex.match} match Yahoo `
    + `and Screener within 1%, and the rest are definition differences, not errors. FinBERT scored over `
    + `${(Math.floor(D.headlineCount / 100) * 100).toLocaleString("en-IN")} headlines and every earnings-call sentence: HUL's management is far more upbeat than the `
    + `analysts questioning them. An LLM tagged ${fr.sample} headlines for behavioural cues: ${D.pct(fr.share_with_bias_cue)} carry one, `
    + `mostly broker authority and herding, and ${D.pct(fr.irrelevant_share)} weren't about the company at all. The rule throughout: `
    + "AI reads and labels; every number is computed.");

  // ================================================================ 5. live demo
  s = pres.addSlide({ masterName: "PANEL_LEFT", sectionTitle: "Analysis" });
  fill(s, "04 - LIVE DEMO", "SEE IT LIVE", "Two minutes, four stops on our dashboard.");
  const y2 = D.prof.Aggressive.y, y4 = D.prof.Balanced.y;
  [["AI INSIGHTS", "Monthly sentiment; news framing"], ["RISK", "Correlation heatmap; stress tests"],
    ["ASK THE PORTFOLIO", "One question, answered with its sources"],
    ["YOUR OWN PORTFOLIO", `Slide A from 4 to 2: your share in P goes from ${D.pct(y4)} to ${D.pct(y2)}`]].forEach(([h, d], i) => {
    const y = 2.65 + i * 0.86;
    text(s, `0${i + 1}`, { x: M, y: y + 0.03, w: 0.45, h: 0.3, fontSize: 11, bold: true, color: GOLD });
    text(s, [{ text: h, options: { fontSize: 15, bold: true, color: WHITE, breakLine: true } },
      { text: d, options: { fontSize: 12, color: SAND } }], { x: M + 0.5, y, w: 3.15, h: 0.8 });
  });
  if (qrData) {
    s.addImage({ data: qrData, x: M, y: 6.1, w: 0.9, h: 0.9, objectName: "qr-dashboard" });
    text(s, URL.replace(/^https?:\/\//, ""), { x: M + 1.05, y: 6.35, w: 2.7, h: 0.5, fontSize: 11, color: WHITE });
  } else {
    text(s, [{ text: "LOCAL COPY", options: { fontSize: 10, bold: true, color: GOLD, breakLine: true } },
      { text: "streamlit run app.py", options: { fontSize: 12, color: WHITE } }], { x: M, y: 6.3, w: 3.2, h: 0.6 });
  }
  card(s, 4.95, 1.0, 7.78, 4.66, "demo-screenshot-frame");
  s.addImage({ path: D.asset("dash_ai.png"), x: 5.0, y: 1.05, w: 7.68, h: 4.56, objectName: "demo-screenshot" });
  text(s, [{ text: "IF ANYTHING TAKES MORE THAN 10 SECONDS", options: { fontSize: 10, bold: true, color: ORANGE, breakLine: true } },
    { text: "1 Live link  \u2192  2 Local copy  \u2192  3 Recorded walkthrough  \u2192  4 Screenshots (A3)",
      options: { fontSize: 13, color: NAVY } }], { x: 4.95, y: 5.95, w: 7.78, h: 0.7 });
  s.addNotes("[2:00] DEMO DRIVER: open the dashboard on Submission data, so the screen matches the slides. "
    + "(1) AI insights: 'This is a year of headlines and every earnings call, scored by FinBERT. Notice HUL's management "
    + "sounds far more positive than the analysts asking the questions.' "
    + `(2) Risk: 'The heatmap shows why these three diversify; in all ${D.stressBetter === 4 ? "four" : D.stressBetter} sell-offs since 2020 our portfolio fell `
    + "less than the Nifty.' "
    + "(3) Ask the portfolio: pick 'Why is ICICI Bank the largest weight?'. 'Every number in the answer cites the file it came from.' "
    + `(4) Sidebar: move risk aversion from 4 to 2. 'This is your own portfolio: your share in P goes from ${D.pct(y4)} to ${D.pct(y2)}.' `
    + "Then flip the data selector to Latest and say what has changed since submission. "
    + "If any step takes more than 10 seconds, drop down the backup ladder without apologising.");

  // ================================================================ 6. technical analysis
  s = pres.addSlide({ masterName: "PANEL_RIGHT", sectionTitle: "Analysis" });
  fill(s, "05 - FORECASTING", "TECHNICAL ANALYSIS LOSES AFTER COSTS",
    "The brief asked: is technical analysis possible? Sharpe ratio 2016\u20132026, after a 0.25% round-trip cost.");
  card(s, M, 2.5, 7.9, 4.3, "ta-chart-card");
  const series = [...D.STOCKS, "^NSEI"];
  const rules = [["Buy and hold", "Buy and hold"], ["Trend (50/200 DMA)", "Trend: 50/200-day average"], ["RSI mean reversion", "RSI mean reversion"]];
  s.addChart(pres.charts.BAR, rules.map(([rule, nm]) => ({ name: nm, labels: series.map((t) => D.SHORT[t]),
    values: series.map((t) => D.ta.find((r) => r.ticker === t && r.rule === rule).sharpe) })),
  { x: M + 0.15, y: 2.6, w: 7.6, h: 4.1, barDir: "col", barGrouping: "clustered", barGapWidthPct: 55,
    chartColors: [HEX.navy, HEX.gold, HEX.brick], showLegend: true, legendPos: "t", legendFontSize: 11, legendColor: HEX.navy,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: HEX.navy, dataLabelFormatCode: "0.00",
    catAxisLabelColor: HEX.navy, catAxisLabelFontSize: 12, valAxisHidden: true, valGridLine: { style: "none" },
    catGridLine: { style: "none" }, catAxisLineShow: true, catAxisLineColor: HEX.tan, objectName: "ta-chart", ...chartText });
  const es = D.ai.event_study;
  text(s, "WEAK-FORM EFFICIENCY", { x: 9.3, y: 1.35, w: 3.5, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5 });
  text(s, `${D.taWins} OF ${D.taRules.length}`, { x: 9.3, y: 1.7, w: 3.5, h: 0.8, fontSize: 44, bold: true, color: WHITE });
  text(s, "RULES THAT BEAT BUY-AND-HOLD", { x: 9.3, y: 2.5, w: 3.5, h: 0.3, fontSize: 10, bold: true, color: SAND });
  text(s, "The rules cut drawdowns, so they are risk controls, not return engines.", { x: 9.3, y: 2.85, w: 3.5, h: 0.6, fontSize: 12, color: SAND });
  rule(s, 9.3, 3.65, 3.5);
  text(s, "SEMI-STRONG: NEWS IS PRICED FAST", { x: 9.3, y: 3.85, w: 3.5, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5 });
  text(s, `${D.spct(es.mean_car_positive_surprise, 1)} / ${D.spct(es.mean_car_negative_surprise, 1)}`, { x: 9.3, y: 4.2, w: 3.5, h: 0.65, fontSize: 32, bold: true, color: WHITE });
  text(s, "3-DAY ABNORMAL RETURN AFTER EARNINGS BEATS / MISSES", { x: 9.3, y: 4.85, w: 3.5, h: 0.5, fontSize: 10, bold: true, color: SAND });
  text(s, `${es.events} results announcements since 2016; market-model CAR over days \u22121 to +1.`, { x: 9.3, y: 5.4, w: 3.5, h: 0.6, fontSize: 12, color: SAND });
  source(s, "Prices: Yahoo Finance, 2016\u20132026. Earnings surprises: Yahoo Finance earnings dates. Figure: data/submission/figures/ta.png.", 8.1);
  s.addNotes(`[0:45] Is technical analysis possible? We tested two classic rules, a 50/200-day moving-average crossover and RSI mean `
    + `reversion, after a 0.25% trading cost. Buy-and-hold has the higher Sharpe ratio in ${D.taWins ? `${D.taRules.length - D.taWins} of ${D.taRules.length}` : `all ${D.taRules.length}`} cases. `
    + "The rules do cut drawdowns, so they're risk controls, not return engines. That is weak-form efficiency. And prices "
    + `digest news fast: across ${es.events} earnings announcements, stocks rose ${D.pct(es.mean_car_positive_surprise, 1)} in three days after a beat `
    + `and fell ${D.pct(-es.mean_car_negative_surprise, 1)} after a miss.`);

  // ================================================================ 7. portfolio
  pres.addSection({ title: "Portfolio" });
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Portfolio" });
  fill(s, "06 - PORTFOLIO", `${weights}, SIZED TO EACH INVESTOR`,
    `Forward-looking (CAPM) expected returns, 10\u201360% per stock. History alone would put ${D.pct(D.hist.weights["ICICIBANK.NS"])} in last decade's winner.`);
  card(s, M, 2.42, 8.0, 3.62, "frontier-card");
  s.addImage({ path: D.figure("frontier.png"), x: M + 0.12, y: 2.48, w: 7.76, h: 3.46, objectName: "frontier" });
  const profiles = [["Aggressive", ORANGE], ["Balanced", NAVY], ["Conservative", TEAL]];
  profiles.forEach(([p, color], i) => {
    const y = 2.42 + i * 1.24, r = D.prof[p];
    card(s, 8.85, y, 3.88, 1.1, `profile-${p}`);
    text(s, D.pct(r.y), { x: 9.0, y: y + 0.15, w: 1.25, h: 0.6, fontSize: 30, bold: true, color });
    text(s, "IN P", { x: 9.0, y: y + 0.75, w: 1.25, h: 0.25, fontSize: 10, bold: true, color: SLATE });
    text(s, [{ text: `${p.toUpperCase()} \u00B7 A = ${r.risk_aversion}`, options: { fontSize: 12, bold: true, color: NAVY, breakLine: true } },
      { text: `E(r) ${D.pct(r.expected_return, 1)} \u00B7 \u03C3 ${D.pct(r.volatility, 1)}`, options: { fontSize: 12, color: SLATE, breakLine: true } },
      { text: `Certainty equivalent ${D.pct(r.certainty_equivalent, 1)}`, options: { fontSize: 12, color: SLATE } }],
    { x: 10.3, y: y + 0.13, w: 2.35, h: 0.9 });
  });
  card(s, M, 6.18, 12.13, 0.72, "sharpe-callout", NAVY);
  text(s, `SHARPE ${D.P.sharpe.toFixed(2)} vs ${D.fwd.market.sharpe.toFixed(2)}`, { x: M + 0.2, y: 6.18, w: 3.2, h: 0.72, fontSize: 18,
    bold: true, color: GOLD, valign: "middle" });
  const o = D.oos;
  text(s, "Three stocks don't beat the index on risk-adjusted terms, so the SIP pairs them with a Nifty core. Out of sample "
    + `(2023\u201326): forward P ${D.spct(o["Forward-looking P"].portfolio.cagr, 1)}/yr, Nifty ${D.spct(o["Equal weight"].market.cagr, 1)}, `
    + `history-based P ${D.spct(o["History-based P"].portfolio.cagr, 1)}.`,
  { x: 4.0, y: 6.18, w: 8.55, h: 0.72, fontSize: 12, color: WHITE, valign: "middle" });
  s.addNotes(`[1:30] Now the portfolio. On history alone, the optimiser puts the maximum ${D.pct(D.hist.weights["ICICIBANK.NS"])} in ICICI, `
    + "because it was the last decade's winner. That's hindsight. So we use forward-looking CAPM returns and get "
    + `${D.STOCKS.map((t) => `${w100(t)}% ${D.SHORT[t]}`).join(", ")}. Here's the honest part: that portfolio's Sharpe ratio is `
    + `${D.P.sharpe.toFixed(2)}, below the Nifty's ${D.fwd.market.sharpe.toFixed(2)}. Three stocks can't beat the market's diversification, which is `
    + "why the long-term plan keeps a Nifty core. Then each of us sizes it with the utility function: with A of 2 you put "
    + `${D.pct(D.prof.Aggressive.y)} in P; with 4, ${D.pct(D.prof.Balanced.y)}; with 6, ${D.pct(D.prof.Conservative.y)}. The rest goes to T-bills. `
    + `Out of sample, weights fitted on 2016 to 2022 earned ${D.pct(o["Forward-looking P"].portfolio.cagr, 1)} a year from 2023, against `
    + `${D.pct(o["Equal weight"].market.cagr, 1)} for the Nifty and ${D.pct(o["History-based P"].portfolio.cagr, 1)} for the history-based weights, `
    + "with the caveat that we chose Sun Pharma after its run.");

  // ================================================================ 8. SIP + IPS
  s = pres.addSlide({ masterName: "PANEL_LEFT", sectionTitle: "Portfolio" });
  fill(s, "07 - THE LONG GAME", "OVER THE YEARS", "\u20B910,000 a month for 15 years, under our Investment Policy Statement.");
  [["RETURN", "Beat 4% inflation clearly; target \u20B975 lakh"], ["RISK", "Balanced (A = 4) unless the questionnaire says otherwise"],
    ["LIQUIDITY", "6 months of expenses kept outside the portfolio"], ["REBALANCE", "Once a year, with new SIP money first"],
    ["BEHAVIOUR", "No selling in the month after a 20% fall"]].forEach(([h, d], i) => {
    const y = 2.75 + i * 0.82;
    text(s, [{ text: h, options: { fontSize: 13, bold: true, color: GOLD, breakLine: true, charSpacing: 1 } },
      { text: d, options: { fontSize: 12, color: WHITE } }], { x: M, y, w: 3.3, h: 0.75 });
  });
  const stats = [[D.lakh(invested), "INVESTED (10% STEP-UP A YEAR)"], [D.lakh(median), "MEDIAN CORPUS, BALANCED"],
    [`${D.pct(D.goal("Balanced", "Parametric", 7500000))} / ${D.pct(D.goal("Balanced", "Bootstrap", 7500000))}`, "CHANCE OF \u20B975 LAKH (TWO MODELS)"]];
  stats.forEach(([v, l], i) => {
    const x = 4.95 + i * (2.48 + 0.17);
    card(s, x, 1.0, 2.48, 1.1, `sip-stat-${i}`);
    text(s, v, { x: x + 0.15, y: 1.1, w: 2.2, h: 0.55, fontSize: 24, bold: true, color: ORANGE });
    text(s, l, { x: x + 0.15, y: 1.68, w: 2.2, h: 0.35, fontSize: 10, bold: true, color: SLATE });
  });
  card(s, 4.95, 2.3, 7.78, 3.5, "sip-card");
  s.addImage({ path: D.figure("sip.png"), x: 5.07, y: 2.37, w: 7.54, h: 3.32, objectName: "sip-fan" });
  text(s, "50% Nifty 50 index fund + 50% our three stocks, gliding to 40% equity. Parametric and bootstrap Monte Carlo, "
    + `10,000 paths, pre-tax. Aggressive: ${D.pct(D.goal("Aggressive", "Parametric", 7500000))} / `
    + `${D.pct(D.goal("Aggressive", "Bootstrap", 7500000))} chance of \u20B975 lakh.`, { x: 4.95, y: 5.98, w: 7.78, h: 0.6, fontSize: 12, color: SLATE });
  s.addNotes(`[1:00] How do you build this over the years? A ten-thousand-rupee SIP rising 10% a year puts in ${D.lakh(invested)} over 15 years. `
    + "Half goes to a Nifty index fund and half to our three stocks, and equity glides down to 40% as the goal nears. For a "
    + `balanced investor the median outcome is ${D.lakh(median)}. The chance of reaching 75 lakh is ${D.pct(D.goal("Balanced", "Parametric", 7500000))} `
    + `with normal returns and ${D.pct(D.goal("Balanced", "Bootstrap", 7500000))} when we resample real history. Our investment policy statement `
    + "adds the discipline: an emergency fund outside the portfolio, yearly rebalancing with new money, and behavioural rules, "
    + "starting with no selling in the month after a 20% fall.");

  // ================================================================ 9. recommendation
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "PANEL_LEFT", sectionTitle: "Close" });
  fill(s, "08 - RECOMMENDATION", "OUR CALL", "Range: our blended value to the analysts' mean target.");
  D.STOCKS.forEach((t, i) => {
    const r = D.recommendation[t], y = 2.75 + i * 1.32;
    text(s, D.LONG[t].toUpperCase(), { x: M, y, w: 3.3, h: 0.3, fontSize: 12, bold: true, color: SAND, charSpacing: 1 });
    text(s, r.action, { x: M, y: y + 0.3, w: 3.3, h: 0.6, fontSize: 30, bold: true, color: r.action === "BUY" ? GOLD : WHITE });
    text(s, `${D.rupee(r.low)}\u2013${D.rupee(r.high).slice(1)} \u00B7 price ${D.rupee(r.price)}`, { x: M, y: y + 0.88, w: 3.3, h: 0.3, fontSize: 12, color: SAND });
  });
  text(s, "BUY THE PORTFOLIO SLOWLY, THROUGH THE SIP", { x: 4.95, y: 0.95, w: 7.78, h: 0.95, fontSize: 28, bold: true, color: ORANGE });
  text(s, "Good businesses at full prices: own them, but let monthly buying average the entry price.",
    { x: 4.95, y: 1.95, w: 7.78, h: 0.4, fontSize: 14, color: NAVY });
  text(s, "RISKS WE ARE WATCHING", { x: 4.95, y: 2.65, w: 7.78, h: 0.3, fontSize: 10, bold: true, color: ORANGE, charSpacing: 1.5 });
  const growths = D.STOCKS.map((t) => val[t].market_implied_growth);
  [["CONCENTRATION", `ICICI is ${D.pct(D.P.weights["ICICIBANK.NS"])} of the weight but ${D.pct(D.ai.risk.risk_share_latest["ICICI Bank"])} of the risk.`],
    ["VALUATION", `Today's prices assume ${D.pct(Math.min(...growths), 1)} to ${D.pct(Math.max(...growths), 1)} growth a year, for ever.`],
    ["REGULATION", "Proposed caps on trade margins for anti-cancer drugs (Sun Pharma)."]].forEach(([h, d], i) => {
    const y = 3.05 + i * 0.62;
    text(s, `0${i + 1}`, { x: 4.95, y: y + 0.02, w: 0.45, h: 0.3, fontSize: 11, bold: true, color: ORANGE });
    text(s, [{ text: `${h}  `, options: { bold: true, color: NAVY } }, { text: d, options: { color: NAVY } }],
      { x: 5.45, y, w: 7.28, h: 0.5, fontSize: 14 });
  });
  rule(s, 4.95, 5.0, 7.78);
  text(s, "LIMITATIONS", { x: 4.95, y: 5.15, w: 7.78, h: 0.3, fontSize: 10, bold: true, color: ORANGE, charSpacing: 1.5 });
  text(s, "One risk-free rate for 2016\u201326 \u00B7 Nifty total return estimated (+1.22%/yr dividends) \u00B7 Sun Pharma chosen after "
    + "its run \u00B7 pre-tax, no fees \u00B7 coursework, not investment advice.", { x: 4.95, y: 5.5, w: qrData ? 6.4 : 7.78, h: 0.75, fontSize: 12, color: SLATE });
  if (qrData) s.addImage({ data: qrData, x: 11.73, y: 5.2, w: 1.0, h: 1.0, objectName: "qr-dashboard" });
  s.addNotes("[1:00] So, our recommendation. HUL: buy; our models call it fairly valued. Sun Pharma and ICICI Bank: hold. Our models "
    + "say they are expensive and analysts say they are cheap, so add only through the SIP, never as a lump sum. Each range "
    + "runs from our blended value to the analysts' mean target. "
    + `The risks we are watching: ICICI is half the weight but ${D.pct(D.ai.risk.risk_share_latest["ICICI Bank"])} of the risk; drug-price `
    + "regulation for Sun Pharma; and all three prices assume growth for ever. The limitations are on the slide, and every "
    + "number here is live on our dashboard. Thank you.");

  // ================================================================ appendix
  pres.addSection({ title: "Appendix" });
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Appendix" });
  fill(s, "APPENDIX A1 - METHODS", "METHODS AND ASSUMPTIONS", "Every number in this deck is computed from these choices; the code is in our GitHub repository.");
  const a = D.metrics.assumptions, st = D.mc.settings, ss = D.sip.settings;
  const rows = [
    ["Prices", "Daily adjusted closes from 2016; HUL demerger (Dec 2025) adjusted", "Yahoo Finance; NSE special pre-open"],
    ["Risk-free rate", `${D.pct(a.risk_free_rate, 2)}, 91-day T-bill`, `RBI, ${D.date(a.risk_free_as_of)}`],
    ["Equity risk premium", `${D.pct(a.equity_risk_premium, 2)} (India)`, `Damodaran, ${D.date(a.erp_as_of)}`],
    ["Benchmark", "Nifty 50 price index + 1.22%/yr estimated dividends", "Nifty BeES vs index gap, 2016\u20132026"],
    ["Valuation", "Two-stage DDM (HUL); two-stage residual income (Sun Pharma, ICICI); peer multiples; r \u00D7 g grids", "workbook/valuation.xlsx"],
    ["Optimisation", "Maximum Sharpe ratio, 10\u201360% per stock, CAPM expected returns (rf + \u03B2 \u00D7 ERP)", "scipy SLSQP"],
    ["Complete portfolio", "y* = (E[rP] \u2212 rf) / (A\u03C3\u00B2), capped at 100%; A = 2, 4, 6", "BKM Ch 6"],
    ["Monte Carlo", `${st.n_sims.toLocaleString("en-IN")} paths, 1 year; normal (Cholesky), ${st.bootstrap_block_days}-day block bootstrap, EWMA \u03BB = ${st.ewma_lambda}`, `numpy, seed ${st.seed}`],
    ["SIP", `\u20B9${ss.monthly_amount.toLocaleString("en-IN")}/month, +${D.pct(ss.annual_step_up)}/yr, ${ss.years} years; ${D.pct(ss.core_index_share)} Nifty core; glide to ${D.pct(ss.glide_path_end_equity)} equity`, "Pre-tax, no fees"],
    ["AI", "FinBERT sentiment; Claude for extraction, aspects and headline tagging", "docs/ai_prompts.md"],
  ];
  const head = ["Item", "Choice", "Source"].map((h) => ({ text: h, options: { bold: true, color: WHITE, fill: { color: NAVY } } }));
  s.addTable([head, ...rows.map((r) => r.map((c, j) => ({ text: c, options: { bold: j === 0, color: NAVY, fill: { color: WHITE } } })))],
    { x: M, y: 2.5, w: 12.13, colW: [2.2, 6.73, 3.2], fontSize: 12, border: { type: "solid", pt: 0.75, color: HEX.sand },
      rowH: 0.36, margin: [0.04, 0.1, 0.04, 0.1], valign: "middle", objectName: "methods-table" });
  s.addNotes("Backup slide for questions on method.");

  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Appendix" });
  fill(s, "APPENDIX A2 - RISK", "WHERE THE RISK SITS", "Correlations of daily returns, and what happened to the portfolio in four real sell-offs.");
  card(s, M, 2.45, 7.4, 3.25, "heatmap-card");
  s.addImage({ path: D.figure("corr_heatmap.png"), x: M + 0.1, y: 2.52, w: 7.2, h: 3.02, objectName: "corr-heatmap" });
  const share = D.ai.risk.risk_share_latest;
  Object.entries(share).forEach(([nm, v], i) => {
    const x = M + i * (2.4 + 0.1);
    text(s, D.pct(v), { x, y: 5.9, w: 2.4, h: 0.55, fontSize: 26, bold: true, color: ORANGE });
    text(s, [{ text: nm.toUpperCase(), options: { bold: true, color: NAVY, breakLine: true } },
      { text: "SHARE OF PORTFOLIO RISK", options: { color: SLATE } }], { x, y: 6.42, w: 2.4, h: 0.5, fontSize: 10 });
  });
  const stressRows = Object.entries(D.stress).map(([ep, r]) => [ep, D.spct(r["Portfolio P"], 1), D.spct(r["Nifty 50"], 1)]);
  s.addTable([["Episode", "Our P", "Nifty 50"].map((h) => ({ text: h, options: { bold: true, color: WHITE, fill: { color: NAVY } } })),
    ...stressRows.map((r) => r.map((c, j) => ({ text: c, options: { color: NAVY, bold: j === 1, fill: { color: WHITE }, align: j ? "right" : "left" } })))],
  { x: 8.3, y: 2.45, w: 4.43, colW: [2.43, 1.0, 1.0], fontSize: 12, border: { type: "solid", pt: 0.75, color: HEX.sand },
    rowH: 0.62, margin: [0.04, 0.1, 0.04, 0.1], valign: "middle", objectName: "stress-table" });
  text(s, `Our portfolio fell less than the Nifty in ${D.stressBetter} of ${stressRows.length} episodes.`, { x: 8.3, y: 5.9, w: 4.43, h: 0.6, fontSize: 14, bold: true, color: NAVY });
  s.addNotes("Backup slide: correlation, risk contribution and stress tests.");

  s = pres.addSlide({ masterName: "NAVY", sectionTitle: "Appendix" });
  fill(s, "APPENDIX A3 - DEMO BACKUP", "THE DASHBOARD, IF THE DEMO FAILS", "Rung 4 of the backup ladder: the same screens as the live demo.");
  [["dash_overview.png", "OVERVIEW: P, VALUATION, VERDICTS"], ["dash_risk.png", "RISK: HEATMAPS AND STRESS"],
    ["dash_ask.png", "ASK THE PORTFOLIO: SAVED ANSWERS"]].forEach(([f, cap], i) => {
    const x = M + i * (3.93 + 0.17);
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.6, w: 3.93, h: 2.7, fill: { color: WHITE }, line: { color: WHITE, width: 0 } });
    s.addImage({ path: D.asset(f.replace(".png", "_crop.png")), x: x + 0.04, y: 2.64, w: 3.85, h: 2.62, objectName: `backup-${i + 1}` });
    text(s, cap, { x, y: 5.45, w: 3.93, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1 });
  });
  s.addNotes("Use only if the live link, the local copy and the recorded walkthrough all fail.");

  s = pres.addSlide({ masterName: "NAVY", sectionTitle: "Appendix" });
  fill(s, "APPENDIX A4 - SOURCES", "DATA SOURCES AND AI PROMPTS", "Free and public sources only; every AI prompt is saved with its output.");
  const col = (x, h, items) => {
    text(s, h, { x, y: 2.55, w: 5.9, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5 });
    text(s, items.map((it, i) => ({ text: it, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })),
      { x, y: 2.95, w: 5.9, h: 3.8, fontSize: 12, color: WHITE });
  };
  col(M, "DATA", ["Prices, statements, analyst consensus: Yahoo Finance (yfinance)", "Ten-year financials: Screener.in public pages",
    "Annual reports and earnings-call transcripts: BSE filings and company IR sites", "Risk-free rate and repo rate: Reserve Bank of India",
    "GDP and demand mix: MOSPI press note, 31 Aug 2026", "Equity risk premium: Damodaran, India, Jan 2026",
    "Headlines: Google News RSS, 12 months", "Sector momentum: Zerodha Aftermarket Report, 12 Oct 2026"]);
  col(6.83, "AI AND METHOD", ["FinBERT: ProsusAI/finbert (Hugging Face)", "Claude (Anthropic): ratio extraction, concall aspects, headline tagging",
    "Prompts P1\u2013P5 and outputs: docs/ai_prompts.md, data/ai/", "Bodie, Kane & Marcus, Investments: Ch 6, 7, 12, 17, 18, 24",
    "Valuation workbook: workbook/valuation.xlsx (live formulas)", "Code, tests and the nightly refresh: GitHub repository"]);
  s.addNotes("Backup slide: sources.");

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log(`wrote ${OUT} (data as of ${D.asOf}${URL ? ", with QR codes" : ", no dashboard URL yet"})`);
}

build().catch((e) => { console.error(e); process.exit(1); });
