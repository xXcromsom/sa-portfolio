// Builds out/Python_Project_Deck.pptx for the Python course (BBAT5E07), in the same style as the
// Security Analysis deck. Code on the slides is read from python_project.py, so it cannot drift.
// Numbers come from data/submission (through data.js) and from the saved tour output. Refresh those with:
//   python python_project.py --charts deliverables/assets/python > deliverables/assets/python/tour_output.txt
const path = require("path");
process.env.NODE_PATH = path.join(__dirname, "node_modules");
require("module").Module._initPaths(); // lets the skill's apply_theme.js find this folder's pptxgenjs

const fs = require("fs");
const pptxgen = require("pptxgenjs");
const D = require("./data");

const SKILL = process.env.PPTX_SKILL || "C:/Users/abhay.ABHAYSLAPTOP/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/603515dc-4b72-4f9a-b223-f734b83beecd/b2a81119-0cca-429f-b56c-4b6607e72c29/skills/pptx";
const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));

const OUT = path.join(__dirname, "out", "Python_Project_Deck.pptx");
const CHARTS = path.join(__dirname, "assets", "python");
const SOURCE = fs.readFileSync(path.join(D.ROOT, "python_project.py"), "utf8").trimEnd().split(/\r?\n/);
const TESTS = fs.readFileSync(path.join(D.ROOT, "tests", "test_python_project.py"), "utf8");
const TOUR = fs.readFileSync(path.join(CHARTS, "tour_output.txt"), "utf8");
const SPEAKERS = { A: "Abhay", S: "Sankarshana", B: "Both" };

const HEX = { navy: "1D2C62", cream: "FFFAED", slate: "5A6590", gold: "EBB24D", orange: "C84D00",
  teal: "3A7C74", brick: "B95142", tan: "D9CBB0", sand: "EADFC8", white: "FFFFFF" };
const THEME = { name: "Python Project", headFontFace: "Century Gothic", bodyFontFace: "Calibri",
  colors: { dk1: HEX.navy, lt1: HEX.white, dk2: HEX.slate, lt2: HEX.cream, accent1: HEX.orange, accent2: HEX.gold,
    accent3: HEX.teal, accent4: HEX.brick, accent5: HEX.tan, accent6: HEX.sand, hlink: HEX.orange, folHlink: HEX.slate } };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Behaviour-aware portfolio construction: Python project";
pres.subject = "Python course project (BBAT5E07)";
pres.author = "Abhay S, Sankarshana Mulugundam";
pres.company = "TAPMI";
const C = pres.SchemeColor;
const NAVY = C.text1, SLATE = C.text2, WHITE = C.background1, CREAM = C.background2;
const ORANGE = C.accent1, GOLD = C.accent2, TEAL = C.accent3, BRICK = C.accent4, TAN = C.accent5, SAND = C.accent6;

const W = 13.333, M = 0.6;
const STRAP = "PYTHON PROJECT \u00B7 BBAT5E07";
const PANEL_R = 8.9;

// ------------------------------------------------------------------ layouts
const strap = (color, x, w) => ({ text: { text: STRAP, options: { x, y: 0.42, w, h: 0.3, fontSize: 9, bold: true,
  color, align: "right", charSpacing: 1.5, margin: 0, isTextBox: true } } });
const ph = (name, type, o) => ({ placeholder: { options: { name, type, margin: 0, valign: "top", align: "left", ...o }, text: "" } });
const label = (color, w) => ph("label", "body", { x: M, y: 0.42, w, h: 0.3, fontSize: 10, bold: true, color });
const title = (color, w) => ph("title", "title", { x: M, y: 0.8, w, h: 1.05, fontSize: 28, bold: true, color });
const sub = (color, w, y = 1.95) => ph("sub", "body", { x: M, y, w, h: 0.5, fontSize: 14, color });
const slideNo = (color) => ({ x: W - 1.1, y: 6.98, w: 0.5, h: 0.3, fontSize: 9, color, align: "right" });

pres.defineSlideMaster({ title: "COVER", background: { color: CREAM }, objects: [
  { rect: { x: 8.43, y: 0, w: W - 8.43, h: 7.5, fill: { color: NAVY } } }, strap(WHITE, 9.0, 3.73),
  label(NAVY, 7.4),
  ph("title", "title", { x: M, y: 1.05, w: 7.4, h: 2.3, fontSize: 40, bold: true, color: ORANGE }),
  ph("sub", "body", { x: M, y: 3.5, w: 7.0, h: 1.1, fontSize: 18, color: NAVY }),
] });
pres.defineSlideMaster({ title: "CREAM", background: { color: CREAM }, slideNumber: slideNo(SLATE), objects: [
  strap(SLATE, 8.4, 4.33), label(ORANGE, 7.4), title(ORANGE, 12.1), sub(NAVY, 12.1)] });
pres.defineSlideMaster({ title: "NAVY", background: { color: NAVY }, slideNumber: slideNo(TAN), objects: [
  strap(WHITE, 8.4, 4.33), label(GOLD, 7.4), title(WHITE, 12.1), sub(CREAM, 12.1)] });
pres.defineSlideMaster({ title: "PANEL_RIGHT", background: { color: CREAM }, slideNumber: slideNo(TAN), objects: [
  { rect: { x: PANEL_R, y: 0, w: W - PANEL_R, h: 7.5, fill: { color: NAVY } } }, strap(WHITE, 9.3, 3.43),
  label(ORANGE, 7.9), title(ORANGE, 7.9), sub(NAVY, 7.9)] });

// ------------------------------------------------------------------ helpers
const text = (slide, value, o) => slide.addText(value, { isTextBox: true, margin: 0, valign: "top",
  ...(o.fontSize >= 20 && o.bold ? { fontFace: THEME.headFontFace } : {}), ...o });
const card = (slide, x, y, w, h, name, fill = WHITE) =>
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: SAND, width: 0.75 }, objectName: name });
const rule = (slide, x, y, w, color = TAN) => slide.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color, width: 0.75 } });
const source = (slide, value, w = 11.4, color = SLATE) => text(slide, value, { x: M, y: 6.98, w, h: 0.3, fontSize: 10, color });
const fill = (slide, l, t, s) => {
  slide.addText(l, { placeholder: "label", charSpacing: 1.5 });
  slide.addText(t, { placeholder: "title" });
  if (s) slide.addText(s, { placeholder: "sub" });
};
const say = (who, time) => `[${SPEAKERS[who]} \u00B7 ${time}] `;
const head = (h, align = "left") => ({ text: h, options: { bold: true, color: WHITE, fill: { color: NAVY }, align } });
const cell = (c, j, o = {}) => ({ text: c, options: { color: NAVY, bold: j === 0, fill: { color: WHITE }, align: o.align && o.align[j] || "left" } });
const tableStyle = { fontSize: 12, border: { type: "solid", pt: 0.75, color: HEX.sand }, margin: [0.03, 0.08, 0.03, 0.08], valign: "middle" };
const pngSize = (file) => { const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; };
const fit = (file, x, y, w, h) => {
  const { w: pw, h: ph_ } = pngSize(file);
  const scale = Math.min(w / pw, h / ph_);
  return { x: x + (w - pw * scale) / 2, y: y + (h - ph_ * scale) / 2, w: pw * scale, h: ph_ * scale };
};
const picture = (slide, name, x, y, w, h) => {
  const file = path.join(CHARTS, name);
  card(slide, x, y, w, h, `${name}-card`);
  slide.addImage({ path: file, ...fit(file, x + 0.08, y + 0.08, w - 0.16, h - 0.16), objectName: name });
};
// Real source lines, so a slide cannot drift from the file. A part is ["start of a line", how many lines]
// or a literal string. One-line docstrings are dropped and the common indent removed.
function code(...parts) {
  const lines = parts.flatMap((part) => {
    if (typeof part === "string") return [part];
    const [marker, n] = part;
    const at = SOURCE.findIndex((l) => l.startsWith(marker));
    if (at < 0) throw new Error(`python_project.py has no line starting "${marker}"`);
    return SOURCE.slice(at, at + n).filter((l) => !/^\s*""".*"""$/.test(l));
  });
  const indent = Math.min(...lines.filter((l) => l.trim()).map((l) => l.length - l.trimStart().length));
  return lines.map((l) => l.slice(indent));
}
// Takes the type hints off def lines that would not fit on a slide.
const plain = (lines) => lines.map((l) => (l.trimStart().startsWith("def ")
  ? l.replace(/: [A-Za-z_][\w.\[\]]*(?=[,)])/g, "").replace(/ -> [\w.\[\]]+(?=:$)/, "") : l));
const codeBox = (slide, lines, x, y, w, h, fontSize = 12) => {
  card(slide, x, y, w, h, "code-card", NAVY);
  text(slide, lines.join("\n"), { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: h - 0.2, fontFace: "Consolas", fontSize, color: WHITE, wrap: false });
};
const tourLine = (start) => {
  const line = TOUR.split(/\r?\n/).find((l) => l.trim().startsWith(start));
  if (!line) throw new Error(`the saved tour output has no line starting "${start}"`);
  return line.trim().slice(start.length).trim();
};

async function build() {
  const val = D.valuation.securities, A4 = D.prof.Balanced, P = D.P;
  const lines = SOURCE.length, tests = (TESTS.match(/^def test_/gm) || []).length;
  const sections = SOURCE.filter((l) => /^# -+ \d+\. /.test(l)).length;
  const weights = D.STOCKS.map((t) => Math.round(P.weights[t] * 100)).join(" / ");

  // ================================================================ 1. cover
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "COVER", sectionTitle: "Opening" });
  fill(s, "PYTHON PROJECT (BBAT5E07) \u00B7 TAPMI \u00B7 PROF. JINU SARA", "BEHAVIOUR-AWARE PORTFOLIO CONSTRUCTION",
    "How much of an investor's money should go into HUL, Sun Pharma and ICICI Bank, given how much risk that investor can bear?");
  text(s, [{ text: "Abhay S (246213044)", options: { breakLine: true } }, { text: "Sankarshana Mulugundam (246213080)" }],
    { x: M, y: 5.0, w: 7.0, h: 0.8, fontSize: 16, bold: true, color: NAVY });
  text(s, `DATA FROZEN ON ${D.date(D.asOf).toUpperCase()}`, { x: M, y: 6.75, w: 6.2, h: 0.3, fontSize: 10, bold: true, color: SLATE, charSpacing: 1.5 });
  text(s, "ONE FILE: PYTHON_PROJECT.PY", { x: 9.0, y: 1.3, w: 3.8, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5 });
  [[lines.toLocaleString("en-IN"), "LINES OF PYTHON"], [String(sections), "NUMBERED SECTIONS"], [String(tests), "AUTOMATED TESTS AGAINST THE REAL PIPELINE AND EXCEL"]].forEach(([v, l], i) => {
    const y = 1.8 + i * 1.5;
    if (i) rule(s, 9.0, y - 0.15, 3.85);
    text(s, v, { x: 9.0, y, w: 3.85, h: 0.75, fontSize: 40, bold: true, color: WHITE });
    text(s, l, { x: 9.0, y: y + 0.76, w: 3.85, h: 0.4, fontSize: 10, bold: true, color: SAND });
  });
  s.addNotes(say("A", "0:20") + "Our project answers one business question: how much money should an investor put into a portfolio of three Indian stocks, given how much risk they can bear? All of the code is in one Python file. Our tests check that it reproduces the numbers from our Excel workbook and our larger pipeline.");

  // ================================================================ 2. problem and data
  s = pres.addSlide({ masterName: "PANEL_RIGHT", sectionTitle: "Opening" });
  fill(s, "01 - PROBLEM AND DATA", "FROM ANSWERS AND PRICES TO RUPEES",
    "The input is ten questionnaire answers and an amount. The output is a rupee split and a measure of risk.");
  [["PRICES AND RETURNS", `Daily, Jan 2016 to ${D.date(D.asOf)}: Parquet files built with yfinance`, TEAL],
    ["VALUATION INPUTS", "workbook/valuation.xlsx, read cell by cell with openpyxl", GOLD],
    ["SETTINGS", "config.yaml: risk-free rate, simulation sizes, SIP terms", ORANGE],
    ["TEXT", `${D.headlineCount.toLocaleString("en-IN")} headlines scored by FinBERT; PDFs read with pypdf`, BRICK]].forEach(([h, d, color], i) => {
    const y = 2.6 + i * 1.08;
    card(s, M, y, 7.95, 0.95, `data-${i}`);
    s.addShape(pres.shapes.RECTANGLE, { x: M, y, w: 0.14, h: 0.95, fill: { color }, line: { color, width: 0 } });
    text(s, [{ text: h, options: { fontSize: 11, bold: true, color: SLATE, breakLine: true } }, { text: d, options: { fontSize: 15, color: NAVY } }],
      { x: M + 0.32, y, w: 7.45, h: 0.95, valign: "middle" });
  });
  text(s, "EXAMPLE OUTPUT", { x: 9.3, y: 1.35, w: 3.5, h: 0.3, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5 });
  text(s, `A = ${A4.risk_aversion}`, { x: 9.3, y: 1.7, w: 3.5, h: 0.7, fontSize: 36, bold: true, color: WHITE });
  text(s, "BALANCED INVESTOR, \u20B91,00,000", { x: 9.3, y: 2.4, w: 3.5, h: 0.3, fontSize: 10, bold: true, color: SAND });
  rule(s, 9.3, 2.85, 3.5);
  [...D.STOCKS.map((t) => [D.SHORT[t], D.rupee(A4.y * P.weights[t] * 100000)]), ["T-bills", D.rupee((1 - A4.y) * 100000)]].forEach(([n, v], i) => {
    const y = 3.0 + i * 0.5;
    text(s, n, { x: 9.3, y, w: 2.0, h: 0.4, fontSize: 15, color: SAND });
    text(s, v, { x: 11.2, y, w: 1.6, h: 0.4, fontSize: 15, bold: true, color: WHITE, align: "right" });
  });
  rule(s, 9.3, 5.05, 3.5);
  text(s, `One-year 95% VaR: ${D.rupee(D.mcB.par.var_95)}`, { x: 9.3, y: 5.2, w: 3.5, h: 0.4, fontSize: 15, bold: true, color: GOLD });
  s.addNotes(say("A", "0:40") + `The program reads four kinds of data: price and return files, the inputs from our Excel valuation workbook, a settings file, and text. It takes an investor's ten questionnaire answers and an amount, and gives back a rupee split. A balanced investor with one lakh holds ${D.rupee(A4.y * P.weights["ICICIBANK.NS"] * 100000)} of ICICI, for example, and the rest as shown, with a one-year 95% Value at Risk of ${D.rupee(D.mcB.par.var_95)}.`);

  // ================================================================ 3. computational thinking
  s = pres.addSlide({ masterName: "NAVY", sectionTitle: "Opening" });
  fill(s, "02 - COMPUTATIONAL THINKING", "FOUR STAGES, AS PLANNED IN OUR PROPOSAL", "Each stage shaped how the file is organised.");
  [["DECOMPOSITION", TEAL, WHITE, "Split one question into smaller ones: load and validate data; measure risk; value each stock; score the investor; optimise; simulate; report.", "14 sections, each one job"],
    ["PATTERN RECOGNITION", GOLD, NAVY, "Volatility, correlation and beta in returns. Every valuation model has the same shape: cash flows plus a terminal value.", "The shared base class"],
    ["ABSTRACTION", ORANGE, WHITE, "Keep only what the decision needs. An Investor is a name, A, an amount and a SIP. A Security is a beta, a return and a volatility.", "Three small classes"],
    ["ALGORITHM DESIGN", BRICK, WHITE, "Recursive bisection for implied growth; merge sort and binary search for outcomes; Cholesky for correlated simulation.", "Each checked another way"]].forEach(([h, color, ink, d, result], i) => {
    const x = M + i * (2.9 + 0.177), y = 2.55;
    card(s, x, y, 2.9, 4.25, `stage-${i}`);
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.9, h: 0.72, fill: { color }, line: { color, width: 0 } });
    text(s, h, { x: x + 0.15, y, w: 2.6, h: 0.72, fontSize: 14, bold: true, color: ink, valign: "middle" });
    text(s, d, { x: x + 0.15, y: y + 0.88, w: 2.6, h: 2.25, fontSize: 15, color: NAVY });
    rule(s, x + 0.15, y + 3.2, 2.6, SAND);
    text(s, [{ text: "IN THE CODE", options: { fontSize: 10, bold: true, color: SLATE, breakLine: true } }, { text: result, options: { fontSize: 15, bold: true, color: ORANGE } }], { x: x + 0.15, y: y + 3.3, w: 2.6, h: 0.8 });
  });
  s.addNotes(say("A", "0:45") + "We followed the four computational-thinking stages from our proposal. Decomposition: one large question became smaller ones, which is why the file has fourteen sections. Pattern recognition: every valuation model is cash flows plus a terminal value, and that repeated shape became a base class. Abstraction: an investor needs only a name, a risk-aversion number, an amount and a SIP. And algorithm design: each algorithm is checked against a second method, which you will see next.");

  // ================================================================ 4. map
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Opening" });
  fill(s, "03 - WHERE EACH CONCEPT LIVES", "EVERY COURSE CONCEPT, MAPPED TO THE FILE", "The same map sits at the top of python_project.py. Each concept does real work in the project.");
  const concepts = [
    ["Variables, numbers, strings", "1", "Settings; Indian-style rupee formatting"], ["Files and exceptions", "2", "JSON, YAML, CSV, Parquet, PDF; a clear DataError"],
    ["Functions, Pandas", "3", "Returns, Sharpe, beta, Treynor, Jensen's alpha"], ["Decisions, loops, dictionaries", "4, 10", "Questionnaire scoring; trading-rule signals"],
    ["Classes", "5", "Security, Investor, Portfolio"], ["Inheritance, recursion", "6", "ValuationModel and two subclasses; recursive PV, bisection"],
    ["Sorting and searching", "7", "Merge sort, binary search, grid search"], ["SciPy", "8", "Maximum Sharpe weights, efficient frontier"],
    ["NumPy", "9, 10", "Cholesky Monte Carlo, block bootstrap, EWMA, SIP"], ["Sets, Transformers, pypdf, yfinance", "2, 11", "Hedge words, FinBERT, PDF text, price download"],
    ["Matplotlib, Seaborn", "12", "Frontier, fan chart, correlation heatmap"], ["Streamlit", "14", "A small interactive demo in the same file"],
  ];
  s.addTable([["Concept", "Section", "What it does in the project"].map((h, j) => head(h, j === 1 ? "center" : "left")),
    ...concepts.map((r) => r.map((c, j) => cell(c, j, { align: ["left", "center", "left"] })))],
  { x: M, y: 2.5, w: 12.13, colW: [4.2, 1.03, 6.9], rowH: 0.335, objectName: "concept-map", ...tableStyle });
  s.addNotes(say("A", "0:40") + "This is the map of the file, and it's the same list at the top of the code. Every topic in the course outline appears here, and each one does real work rather than being a separate exercise. Sections 5, 6 and 7 are the ones we'll show you in code, because they are the core of the course.");

  // ================================================================ 5. classes and inheritance
  pres.addSection({ title: "The code" });
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "The code" });
  fill(s, "04 - CLASSES AND INHERITANCE", "ONE BASE MODEL, TWO SUBCLASSES", "The base class holds discounting and the reverse solve. A subclass only says what its cash flows are.");
  codeBox(s, code(["class DividendDiscountModel", 16]).map((l) => l.replace(/\s+# Gordon growth$/, "")), M, 2.5, 7.75, 3.6, 13);
  card(s, M, 6.22, 7.75, 0.58, "inherited", WHITE);
  text(s, "present_value and implied_growth are not written here: both come from the base class.", { x: M + 0.15, y: 6.22, w: 7.45, h: 0.58, fontSize: 14, bold: true, color: ORANGE, valign: "middle" });
  // The class family, drawn rather than listed.
  card(s, 8.6, 2.5, 4.13, 0.85, "base-class", NAVY);
  text(s, [{ text: "ValuationModel (ABC)", options: { fontSize: 14, bold: true, color: WHITE, breakLine: true } }, { text: "present_value, implied_growth", options: { fontSize: 12, color: SAND } }], { x: 8.75, y: 2.58, w: 3.85, h: 0.7 });
  [["DividendDiscountModel", "HUL: pays out most of its profit", 8.6], ["ResidualIncomeModel", "Sun Pharma, ICICI Bank", 10.75]].forEach(([n, d, x]) => {
    s.addShape(pres.shapes.LINE, { x: x + 0.99, y: 3.35, w: 0, h: 0.3, line: { color: HEX.tan, width: 1.5 } });
    card(s, x, 3.65, 1.98, 1.15, `sub-${n}`);
    text(s, [{ text: n, options: { fontSize: 11, bold: true, color: NAVY, breakLine: true } }, { text: d, options: { fontSize: 11, color: SLATE } }], { x: x + 0.08, y: 3.72, w: 1.84, h: 1.0 });
  });
  text(s, "BUSINESS ENTITIES", { x: 8.6, y: 4.98, w: 4.13, h: 0.28, fontSize: 10, bold: true, color: ORANGE, charSpacing: 1.5 });
  text(s, [{ text: "Security", options: { bold: true } }, { text: " (dataclass): ticker, beta, return, volatility", options: { breakLine: true } },
    { text: "Investor", options: { bold: true } }, { text: ": A, amount, SIP; from_answers classmethod", options: { breakLine: true } },
    { text: "Portfolio", options: { bold: true } }, { text: ": checks weights sum to 1; complete, allocation, ranked" }], { x: 8.6, y: 5.28, w: 4.13, h: 1.5, fontSize: 13, color: NAVY });
  s.addNotes(say("A", "1:00") + "Inheritance is justified here because the models really do share logic. The base class, ValuationModel, is abstract: it discounts cash flows and solves for implied growth, and it refuses bad inputs such as a discount rate below growth. Each subclass only says what its cash flows are. Here is the dividend model: dividends grow at g1 for the first n years, then at g2, and the terminal value uses Gordon growth. HUL uses this one, because it pays out most of its profit. Sun Pharma and ICICI use residual income. We also have three business classes: a Security, an Investor that can be built from questionnaire answers with a class method, and a Portfolio that checks its weights sum to one.");

  // ================================================================ 6. recursion
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "The code" });
  fill(s, "05 - RECURSION", "TWO RECURSIVE FUNCTIONS, EACH CHECKED BY ALGEBRA", "Each has a base case and a smaller problem. Each result is compared with a closed-form formula and the Excel workbook.");
  codeBox(s, [...code(["    def present_value", 1], ["        if not flows:", 3]), "", "def implied_growth(self, low, high, tol):",
    ...code(["        gap_low = self.single_stage_value(low)", 1], ["        middle = (low + high) / 2", 6]).map((l) => "    " + l)], M, 2.5, 7.75, 2.9, 11);
  s.addTable([["Stock", "Class", "Value", "Implied growth"].map((h, j) => head(h, j > 1 ? "right" : "left")),
    ...D.STOCKS.map((t) => [D.SHORT[t], t === "HINDUNILVR.NS" ? "Dividend" : "Residual income", `\u20B9${val[t].intrinsic_value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, D.pct(val[t].market_implied_growth, 2)].map((c, j) => cell(c, j, { align: ["left", "left", "right", "right"] })))],
  { x: M, y: 5.55, w: 7.75, colW: [1.9, 2.25, 1.8, 1.8], rowH: 0.31, objectName: "recursion-results", ...tableStyle });
  [["BASE CASE", "An empty list of cash flows is worth 0. For bisection, a range narrower than 1e-10 is the answer."],
    ["SMALLER PROBLEM", "One fewer cash flow, one year later. Bisection halves its range on every call."],
    ["PROOF", "A test asserts recursive value = closed form = Excel, and bisection = algebra."]].forEach(([h, d], i) => {
    const y = 2.5 + i * 1.5;
    card(s, 8.6, y, 4.13, 1.3, `recursion-${i}`);
    text(s, [{ text: h, options: { fontSize: 11, bold: true, color: ORANGE, breakLine: true } }, { text: d, options: { fontSize: 14, color: NAVY } }], { x: 8.75, y: y + 0.1, w: 3.85, h: 1.12 });
  });
  s.addNotes(say("A", "1:00") + "Recursion appears twice. The present value of a list of cash flows is the first flow discounted, plus the present value of the rest. The base case is an empty list. Then bisection: what growth rate makes the model equal the market price? We take the middle of a range, see which half contains the answer, and call the function again on that half. About 35 calls reach a width of one in ten billion. A loop would work too, so why trust it? Because we check each one: the recursive value equals the closed-form formula and our Excel workbook, and bisection equals the algebra. The results for all three stocks are in the table.");

  // ================================================================ 7. data structures, files, exceptions
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "The code" });
  fill(s, "06 - DATA STRUCTURES, FILES, EXCEPTIONS", "BAD DATA STOPS THE PROGRAM, WITH A CLEAR MESSAGE", "We never fill a gap with a guess. A missing file or column raises DataError, which names the file and the fix.");
  codeBox(s, code(["def read_returns", 13]), M, 2.5, 7.75, 3.2, 12);
  [["DICTIONARY", "QUESTIONS maps each question to its kind, text and five options"], ["LIST", "The answers for capacity and for willingness, kept separately"], ["SET", "HEDGE_WORDS: fast lookup of cautious words like may, might, could"]].forEach(([h, d], i) => {
    const y = 2.5 + i * 1.09;
    card(s, 8.6, y, 4.13, 0.98, `structure-${i}`);
    text(s, [{ text: h, options: { fontSize: 11, bold: true, color: ORANGE, breakLine: true } }, { text: d, options: { fontSize: 13, color: NAVY } }], { x: 8.75, y: y + 0.08, w: 3.85, h: 0.85 });
  });
  card(s, M, 5.85, 12.13, 0.95, "exception-output", NAVY);
  text(s, [{ text: "A missing file is caught, not ignored: ", options: { color: GOLD, bold: true } }, { text: tourLine("A missing file is caught, not ignored:").replace(/^.*[\\/]/, "..."), options: { color: WHITE, fontFace: "Consolas", breakLine: true } },
    { text: "Bad inputs are refused: ", options: { color: GOLD, bold: true } }, { text: tourLine("Bad inputs are refused:"), options: { color: WHITE, fontFace: "Consolas" } }],
  { x: M + 0.2, y: 5.92, w: 11.7, h: 0.8, fontSize: 13, valign: "middle" });
  s.addNotes(say("A", "0:40") + "Financial data is messy, so we decided that bad data should stop the program rather than be filled with a guess. This function reads a returns file and raises our own DataError if the file is missing, a column is missing, or there are gaps. The file reads JSON, YAML, CSV, Parquet, Excel and PDF, each with its own error handling. The data structures are chosen for a reason: a dictionary for the questionnaire, lists for the answers, and a set for hedge words because lookup in a set is fast. The two messages at the bottom are real output.");

  // ================================================================ 8. numpy
  pres.addSection({ title: "Numbers" });
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Numbers" });
  fill(s, "07 - NUMPY", `10,000 SIMULATED YEARS, WITHOUT A PYTHON LOOP`, "Monte Carlo: Cholesky keeps the correlation between the stocks; arrays do the work on every path at once.");
  codeBox(s, plain(code(["def simulate_normal", 1], ["    chol = np.linalg.cholesky(cov)", 2], "", ["def wealth_paths", 1], ["    growth = np.cumprod", 2])), M, 2.5, 7.3, 1.85, 12);
  [[D.rupee(D.mcB.par.terminal_percentiles.p50), "MEDIAN AFTER ONE YEAR, \u20B91 LAKH, A = 4"], [D.rupee(D.mcB.par.var_95), "95% VaR, NORMAL RETURNS"], [D.rupee(D.mcB.boot.var_95), "95% VaR, BLOCK BOOTSTRAP"]].forEach(([v, l], i) => {
    const x = M + i * (2.35 + 0.125);
    card(s, x, 4.5, 2.35, 1.3, `mc-stat-${i}`);
    text(s, v, { x: x + 0.12, y: 4.58, w: 2.1, h: 0.55, fontSize: 24, bold: true, color: ORANGE });
    text(s, l, { x: x + 0.12, y: 5.15, w: 2.1, h: 0.55, fontSize: 10, bold: true, color: SLATE });
  });
  card(s, M, 5.95, 7.3, 0.85, "cholesky", NAVY);
  text(s, "Cholesky: split the covariance matrix so that cov = L L\u1D40. Independent draws multiplied by L have the correlations we measured.", { x: M + 0.2, y: 5.95, w: 6.9, h: 0.85, fontSize: 14, color: WHITE, valign: "middle" });
  picture(s, "fan.png", 8.05, 2.5, 4.68, 3.1);
  card(s, 8.05, 5.75, 4.68, 1.05, "fan-note");
  text(s, `Half of all paths end between ${D.rupee(D.mcB.par.terminal_percentiles.p25)} and ${D.rupee(D.mcB.par.terminal_percentiles.p75)}.`, { x: 8.2, y: 5.75, w: 4.38, h: 1.05, fontSize: 15, bold: true, color: NAVY, valign: "middle" });
  source(s, "Type hints trimmed to fit the slide.");
  s.addNotes(say("S", "1:00") + "Now the simulation. We need thousands of possible futures in which the three stocks move together realistically. Independent random numbers wouldn't do that, so the Cholesky factor of the covariance matrix turns them into correlated returns. Because these are NumPy arrays of shape paths by days by stocks, one line handles all 10,000 paths at once. The wealth function compounds each path, with a share y in the portfolio and the rest in T-bills. We also resample real history in blocks, which keeps fat tails. On one lakh, the 95% Value at Risk is " + D.rupee(D.mcB.par.var_95) + " with normal returns and " + D.rupee(D.mcB.boot.var_95) + " with the bootstrap.");

  // ================================================================ 9. scipy
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Numbers" });
  fill(s, "08 - SCIPY", "THE OPTIMISER, CHECKED BY BRUTE FORCE", "SciPy finds the maximum-Sharpe weights within 10\u201360% limits. A separate grid search on every 1% mix finds the same portfolio.");
  codeBox(s, code(["def max_sharpe_weights", 4], "", ["def _optimise", 1], ["    all_constraints = [", 1], ["    result = minimize(objective", 2]), M, 2.5, 12.13, 1.82, 12);
  [["SciPy SLSQP", weights, `Sharpe ${P.sharpe.toFixed(4)}`], ["1% grid search", tourLine("Grid search best:").match(/\d+(?=%)/g).join(" / "), "Same portfolio, found by trying every mix"]].forEach(([h, v, d], i) => {
    const x = M + i * (3.9 + 0.15);
    card(s, x, 4.45, 3.9, 1.25, `optimiser-${i}`);
    text(s, h.toUpperCase(), { x: x + 0.15, y: 4.52, w: 3.6, h: 0.25, fontSize: 10, bold: true, color: SLATE });
    text(s, v, { x: x + 0.15, y: 4.76, w: 3.6, h: 0.5, fontSize: 24, bold: true, color: ORANGE });
    text(s, d, { x: x + 0.15, y: 5.3, w: 3.6, h: 0.32, fontSize: 13, color: NAVY });
  });
  card(s, M, 5.82, 7.95, 0.98, "optimiser-note", NAVY);
  text(s, `Then y* = (E[rP] \u2212 rf) / (A\u03C3\u00B2) sizes it for each investor: ${D.pct(D.prof.Aggressive.y)} at A = 2, ${D.pct(A4.y)} at A = 4, ${D.pct(D.prof.Conservative.y)} at A = 6. The rest goes to T-bills.`, { x: M + 0.2, y: 5.82, w: 7.55, h: 0.98, fontSize: 14, color: WHITE, valign: "middle" });
  picture(s, "frontier.png", 8.7, 4.45, 4.03, 2.35);
  s.addNotes(say("S", "0:40") + `SciPy's minimize function solves the constrained problem: maximise the Sharpe ratio, with weights that sum to one and stay between 10 and 60 percent. It gives ${weights.replace(/ \/ /g, ", ")}. How do we know it worked? We wrote a plain grid search that tries every mix at 1% steps. It's slow, but it's easy to trust, and it finds the same portfolio. Then the formula on the slide sizes it for each investor using their risk aversion.`);

  // ================================================================ 10. sorting and searching
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Numbers" });
  fill(s, "09 - SORTING AND SEARCHING", "RANKING 10,000 OUTCOMES, FINDING WHAT MATTERS", "Merge sort ranks the outcomes. Binary search then finds how many end below \u20B91 lakh.");
  codeBox(s, code(["def merge_sort", 15]), M, 2.5, 7.85, 3.0, 12);
  codeBox(s, plain(code(["def binary_search", 10])), 8.6, 2.5, 4.13, 2.05, 12);
  card(s, 8.6, 4.65, 4.13, 0.85, "binary-note");
  text(s, "Each step halves the list: about 14 steps. Scanning it could take 10,000.", { x: 8.75, y: 4.65, w: 3.83, h: 0.85, fontSize: 14, bold: true, color: NAVY, valign: "middle" });
  [["WORST THREE", tourLine("Worst three:")], ["BEST THREE", tourLine("Best three:")], ["BELOW \u20B91 LAKH", tourLine("Binary search:").split(" of paths")[0] + " of paths"]].forEach(([h, v], i) => {
    const x = M + i * (3.93 + 0.17);
    card(s, x, 5.6, 3.93, 1.2, `sort-${i}`);
    text(s, h, { x: x + 0.15, y: 5.68, w: 3.65, h: 0.28, fontSize: 10, bold: true, color: ORANGE });
    text(s, v.replace(/Rs /g, "\u20B9"), { x: x + 0.15, y: 5.98, w: 3.65, h: 0.72, fontSize: i === 2 ? 26 : 15, bold: true, color: NAVY });
  });
  source(s, "Merge sort checked against sorted() on 2,000 paths; sorted() ranks all 10,000. A = 4, \u20B91 lakh, one year. Type hints trimmed.");
  s.addNotes(say("S", "0:40") + "A risk manager cares about the tails, so we sort the simulated outcomes. Merge sort is recursive: sort each half, then merge them. We wrote it ourselves and check it against Python's sorted on 2,000 paths, then use Python's sorted for all 10,000, since a pure-Python recursive sort is slower. On the sorted list, binary search halves the range each step, so it finds how many of the 10,000 paths end below one lakh in about fourteen steps. The answer is the figure on the right. We also use sorted with a key to rank securities by Sharpe ratio.");

  // ================================================================ 11. libraries
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Numbers" });
  fill(s, "10 - LIBRARIES", "EACH LIBRARY HAS ONE JOB", "Heavy libraries are imported inside the function that needs them, so the file still starts on a machine that lacks one.");
  const libs = [["Pandas", "Load, align and summarise returns; metrics tables"], ["Matplotlib", "Efficient frontier and Monte Carlo fan chart"], ["Seaborn", "Correlation heatmap"], ["yfinance", "Fresh prices (--fetch)"],
    ["Transformers (FinBERT)", "Financial tone of a sentence (--finbert)"], ["pypdf", "Text from annual reports and transcripts (--pdf)"], ["openpyxl", "Excel valuation inputs, cell by cell"], ["Streamlit", "Interactive demo on one screen"], ["requests", "Optional live answers through OpenRouter"]];
  s.addTable([["Library", "Job"].map((h) => head(h)), ...libs.map((r) => r.map((c, j) => cell(c, j)))], { x: M, y: 2.5, w: 7.3, colW: [2.6, 4.7], rowH: 0.42, objectName: "libraries", ...tableStyle });
  picture(s, "correlation_heatmap.png", 8.1, 2.5, 4.63, 4.2);
  s.addNotes(say("S", "0:30") + "Each library has one clear job. Pandas handles the tables, Matplotlib and Seaborn draw the charts, like this heatmap, yfinance downloads prices, FinBERT reads tone, pypdf reads reports and Streamlit gives us the demo. One design choice: the heavy libraries are imported inside the function that needs them, so the file still runs on a machine that doesn't have them all.");

  // ================================================================ 12. results
  s = pres.addSlide({ masterName: "NAVY", sectionTitle: "Numbers" });
  fill(s, "11 - RESULTS", "THE SAME PORTFOLIO, SIZED THREE WAYS", "On \u20B91 lakh for one year, then a \u20B910,000 monthly SIP rising 10% a year for 15 years. Simulated; not investment advice.");
  ["Aggressive", "Balanced", "Conservative"].forEach((p, i) => {
    const r = D.prof[p], par = D.mc.results.Parametric[p], x = M + i * (3.93 + 0.17), y = 2.55;
    card(s, x, y, 3.93, 4.25, `result-${p}`);
    text(s, `${p.toUpperCase()} \u00B7 A = ${r.risk_aversion}`, { x: x + 0.2, y: y + 0.15, w: 3.5, h: 0.3, fontSize: 12, bold: true, color: SLATE });
    text(s, D.pct(r.y), { x: x + 0.2, y: y + 0.45, w: 3.5, h: 0.8, fontSize: 44, bold: true, color: ORANGE });
    text(s, "IN THE THREE STOCKS", { x: x + 0.2, y: y + 1.25, w: 3.5, h: 0.28, fontSize: 10, bold: true, color: SLATE });
    rule(s, x + 0.2, y + 1.65, 3.5, SAND);
    [["Expected return", D.pct(r.expected_return, 1)], ["Volatility", D.pct(r.volatility, 1)], ["95% VaR on \u20B91 lakh", D.rupee(par.var_95)], ["Chance of loss", D.pct(par.prob_loss)], ["15-year SIP median", D.lakh(D.sipRes[p].Parametric.terminal_percentiles.p50)]].forEach(([k, v], j) => {
      const yy = y + 1.78 + j * 0.46;
      text(s, k, { x: x + 0.2, y: yy, w: 2.2, h: 0.4, fontSize: 14, color: NAVY });
      text(s, v, { x: x + 2.3, y: yy, w: 1.43, h: 0.4, fontSize: 14, bold: true, color: NAVY, align: "right" });
    });
  });
  s.addNotes(say("S", "0:40") + `Here is what the program tells three different investors. They all hold the same mix of stocks, ${weights.replace(/ \/ /g, ", ")}, because that is the best risky portfolio for everyone. What changes is how much of it they hold: ${D.pct(D.prof.Aggressive.y)}, ${D.pct(A4.y)} or ${D.pct(D.prof.Conservative.y)}. This is the separation property from finance, and it's also a nice software result: one Portfolio object, three Investor objects.`);

  // ================================================================ 13. testing
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Numbers" });
  fill(s, "12 - TESTING", `${tests} TESTS: HOW WE KNOW THE CODE IS RIGHT`, "Because this file is self-contained, it could quietly drift from the rest of the project. The tests stop that.");
  [["SAME ANSWERS", ["Valuations equal the Excel workbook", "Metrics and weights equal the pipeline's files", "Simulations reproduce mc.json and sip.json exactly", "Trading rules match the pipeline's"]],
    ["SECOND METHODS", ["Recursion and bisection equal closed forms", "Grid search finds SciPy's optimum", "Own merge sort equals Python's sorted", "Questionnaire equals the dashboard's"]],
    ["BAD INPUTS", ["Discount rate below growth is refused", "Weights not summing to 1 are refused", "A blank Excel cell gives a clear error", "Missing and broken files raise DataError"]]].forEach(([h, items], i) => {
    const x = M + i * (3.93 + 0.17);
    card(s, x, 2.5, 3.93, 3.4, `test-group-${i}`);
    text(s, h, { x: x + 0.18, y: 2.62, w: 3.6, h: 0.3, fontSize: 11, bold: true, color: ORANGE, charSpacing: 1 });
    text(s, items.map((it, k) => ({ text: it, options: { bullet: { indent: 14 }, breakLine: k < items.length - 1, paraSpaceAfter: 6 } })), { x: x + 0.18, y: 2.98, w: 3.6, h: 2.85, fontSize: 16, color: NAVY });
  });
  card(s, M, 6.05, 12.13, 0.75, "test-command", NAVY);
  text(s, `python -m pytest tests/test_python_project.py    ${tests} passed`, { x: M + 0.25, y: 6.05, w: 11.6, h: 0.75, fontFace: "Consolas", fontSize: 16, color: WHITE, valign: "middle" });
  s.addNotes(say("S", "0:30") + `We have ${tests} automated tests in three groups. First, the file must give the same answers as our Excel workbook and our main pipeline, down to the rupee. Second, each algorithm is checked by a different method. Third, bad inputs must fail with a clear message. We'll run them live in the demo.`);

  // ================================================================ 14. demo
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "NAVY", sectionTitle: "Close" });
  fill(s, "13 - LIVE DEMO", "FOUR COMMANDS", "Everything runs on the frozen data, so the screen matches these slides.");
  [["python python_project.py", "The full tour: each section prints its result next to the pipeline's, marked OK"], ["python python_project.py --charts out/", "Saves the Matplotlib and Seaborn charts"],
    ["streamlit run python_project.py", "Move A from 4 to 2: the share in P goes from " + D.pct(A4.y) + " to " + D.pct(D.prof.Aggressive.y)], ["python -m pytest tests/test_python_project.py", `${tests} tests, in a few seconds`]].forEach(([c, d], i) => {
    const y = 2.6 + i * 0.86;
    card(s, M, y, 12.13, 0.76, `demo-${i}`);
    text(s, `0${i + 1}`, { x: M + 0.15, y, w: 0.5, h: 0.76, fontSize: 14, bold: true, color: ORANGE, valign: "middle" });
    text(s, c, { x: M + 0.7, y, w: 5.6, h: 0.76, fontFace: "Consolas", fontSize: 14, color: NAVY, valign: "middle" });
    text(s, d, { x: 6.95, y, w: 5.65, h: 0.76, fontSize: 13, color: SLATE, valign: "middle" });
  });
  text(s, [{ text: "IF A COMMAND FAILS  ", options: { bold: true, color: GOLD } }, { text: "Show the saved output and charts in deliverables/assets/python, and keep going.", options: { color: WHITE } }], { x: M, y: 6.1, w: 12.13, h: 0.5, fontSize: 14 });
  s.addNotes(say("B", "1:30") + "DEMO: Abhay drives the terminal; Sankarshana explains. (1) Run the tour and point at the OK marks against Excel and the pipeline. (2) Save the charts and open one. (3) Start Streamlit, move A from 4 to 2, and show the rupee split and VaR changing, then open Portfolio.complete in the editor to show the formula. (4) Run pytest. If asked to explain any function, open it in the editor; docs/python_walkthrough.md has the function map and likely questions.");

  // ================================================================ 15. disclosure
  s = pres.addSlide({ masterName: "CREAM", sectionTitle: "Close" });
  fill(s, "14 - HONEST NOTES", "AI ASSISTANCE, AND WHAT CHANGED FROM THE PROPOSAL", "We list what differs from the approved proposal, and why, so nothing is hidden.");
  s.addTable([["Proposal said", "The project does", "Why"].map((h) => head(h)),
    ...[["FINRA NCFS investor microdata", "A 10-question questionnaire (capacity and willingness)", "It sets A for one investor directly; we did not calibrate it on NCFS"],
      ["Loughran\u2013McDonald word lists", "A small hedge-word set of the same kind", "Keeps the file self-contained; it is not the full list"],
      ["NSE total-return index", "Nifty 50 price plus an estimated 1.22% a year", "Estimated from the gap between Nifty BeES and the index"],
      ["Anthropic SDK (optional)", "A free model through OpenRouter (optional)", "No cost for a live demo; every number still comes from our files"]].map((r) => r.map((c, j) => cell(c, j)))],
  { x: M, y: 2.5, w: 12.13, colW: [3.4, 4.3, 4.43], rowH: 0.54, objectName: "proposal-gaps", ...tableStyle });
  card(s, M, 5.4, 12.13, 1.4, "ai-disclosure", NAVY);
  text(s, [{ text: "AI ASSISTANCE", options: { fontSize: 11, bold: true, color: GOLD, charSpacing: 1.5, breakLine: true } },
    { text: "Claude helped write and review this code. We checked it by running it, by testing it against Excel and the pipeline, and by reading it until we could explain each function; docs/python_walkthrough.md is our map. "
      + "This is coursework, not investment advice.", options: { fontSize: 15, color: WHITE } }], { x: M + 0.25, y: 5.5, w: 11.6, h: 1.2 });
  s.addNotes(say("A", "0:30") + "Two honest notes before we finish. First, four things differ from our proposal, and the table says what and why. Second, we used AI to help write and review this code. That is why we built so many independent checks, and why we made sure each of us can explain each function. Thank you, and we'd welcome your questions.");

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log(`wrote ${OUT} (${lines} lines, ${sections} sections, ${tests} tests)`);
}

build().catch((e) => { console.error(e); process.exit(1); });
