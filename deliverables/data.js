// Every number in the deck and report comes from here: the frozen dataset (data/submission),
// plus the AI outputs in data/ai. Nothing is typed in by hand except the macro table, which
// cites docs/macro_industry.md.
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATASET = path.join(ROOT, "data", process.env.DATASET || "submission");
const read = (f) => JSON.parse(fs.readFileSync(path.join(DATASET, f), "utf8"));
const readAi = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "data", "ai", f), "utf8"));

const STOCKS = ["HINDUNILVR.NS", "SUNPHARMA.NS", "ICICIBANK.NS"];
const SHORT = { "HINDUNILVR.NS": "HUL", "SUNPHARMA.NS": "Sun Pharma", "ICICIBANK.NS": "ICICI Bank", "^NSEI": "Nifty 50" };
const LONG = { "HINDUNILVR.NS": "Hindustan Unilever", "SUNPHARMA.NS": "Sun Pharma", "ICICIBANK.NS": "ICICI Bank" };

const metrics = read("metrics.json");
const valuation = read("valuation.json");
const portfolio = read("portfolio.json");
const mc = read("mc.json");
const sip = read("sip.json");
const ai = read("ai_analysis.json");
const sentiment = read("sentiment.json");
const extraction = read("extraction_accuracy.json");
const aspects = readAi("concall_aspects.json").companies;

const MINUS = "−";
const pct = (x, d = 0) => `${(x * 100).toFixed(d).replace("-", MINUS)}%`;
const spct = (x, d = 0) => (x >= 0 ? "+" : "") + pct(x, d);
const num = (x, d = 2) => x.toFixed(d).replace("-", MINUS);
const rupee = (x) => "₹" + Math.round(x).toLocaleString("en-IN");
const lakh = (x) => `₹${(x / 1e5).toFixed(1)} lakh`;
const date = (iso) => new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

const fwd = portfolio.views.forward;
const P = fwd.tangency;
const hist = portfolio.views.history.tangency;
const oos = portfolio.out_of_sample;
const prof = portfolio.profiles;
const mcB = { par: mc.results.Parametric.Balanced, boot: mc.results.Bootstrap.Balanced };
const sipRes = sip.results;
const goal = (profile, mode, g) => sipRes[profile][mode].prob_reach_goal[String(g)];

// Technical analysis: how many rule/series pairs beat buy-and-hold on Sharpe?
const ta = ai.technical_analysis;
const taBH = Object.fromEntries(ta.filter((r) => r.rule === "Buy and hold").map((r) => [r.ticker, r.sharpe]));
const taRules = ta.filter((r) => r.rule !== "Buy and hold");
const taWins = taRules.filter((r) => r.sharpe > taBH[r.ticker]).length;

// Stress: did P fall less than the Nifty in every episode?
// The pipeline labels the latest window "... to now"; a frozen document names the date instead.
const asOfLabel = new Date(metrics.as_of + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const stress = Object.fromEntries(Object.entries(ai.risk.stress).map(([k, v]) => [k.replace("to now", `to ${asOfLabel}`), v]));
const stressBetter = Object.values(stress).filter((s) => s["Portfolio P"] > s["Nifty 50"]).length;

// P4 cross-check: Claude's overall tone for each latest call vs the sign of FinBERT's management tone
// for the same quarter (|tone| < 0.05 counts as neutral).
const quarterOf = (call) => { const [q, fy] = call.split(",")[0].split(" "); return `${fy}${q}`; }; // "Q1 FY27" -> "FY27Q1"
const toneAgreement = STOCKS.map((t) => {
  const label = { positive: 1, neutral: 0, negative: -1 }[aspects[t].overall_tone];
  const row = sentiment.transcripts.find((r) => r.ticker === t && r.quarter === quarterOf(aspects[t].call));
  const finbert = row.management_tone > 0.05 ? 1 : row.management_tone < -0.05 ? -1 : 0;
  return label === finbert;
});
const callToneAgreement = { agree: toneAgreement.filter(Boolean).length, of: toneAgreement.length };

const headlineCount = Object.values(sentiment.headlines).reduce((a, h) => a + h.count, 0);
const callSentences = sentiment.transcripts.reduce((a, t) => a + (t.sentences || 0), 0);
const calls = ai.sentiment.calls_mean;

// Recommendation: the workbook verdict decides the action; the range runs from our blended
// value to the analysts' mean target.
const recommendation = Object.fromEntries(STOCKS.map((t) => {
  const v = valuation.securities[t];
  const f = ai.forecasts[t];
  const action = v.workbook_verdict === "Fairly valued" ? "BUY" : v.workbook_verdict === "Undervalued" ? "BUY" : "HOLD";
  return [t, { action, verdict: v.workbook_verdict, low: v.blended_value, high: f.analyst_target_mean, price: v.latest_price }];
}));

module.exports = {
  ROOT, DATASET, STOCKS, SHORT, LONG, pct, spct, num, rupee, lakh, date, MINUS,
  metrics, valuation, portfolio, mc, sip, ai, sentiment, extraction, aspects,
  fwd, P, hist, oos, prof, mcB, sipRes, goal, ta, taBH, taRules, taWins, stress, stressBetter,
  headlineCount, callSentences, calls, recommendation, callToneAgreement,
  asOf: metrics.as_of,
  figure: (name) => path.join(DATASET, "figures", name),
  asset: (name) => path.join(__dirname, "assets", name),
  // Macro table: docs/macro_industry.md §1 (MOSPI press note 31 Aug 2026; RBI 1 Oct 2026).
  macro: [
    { value: "7.8%", label: "REAL GDP GROWTH, Q1 FY27", source: "MOSPI" },
    { value: "+11.9%", label: "INVESTMENT (GFCF) GROWTH", source: "MOSPI" },
    { value: "5.25%", label: "RBI REPO RATE", source: "RBI" },
    { value: pct(portfolio.risk_free_rate, 2), label: "91-DAY T-BILL RATE", source: "RBI" },
  ],
};
