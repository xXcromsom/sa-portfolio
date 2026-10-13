"""Scaffold workbook/valuation.xlsx with live formulas (run once).

After this, the workbook is the source of truth: edit inputs in Excel, save, and
the pipeline reads its Summary sheet. Re-running this script would overwrite
those edits, so it refuses to run if the file exists unless --force is passed.

Models, chosen to fit each business (BKM Ch 18):
- HUL pays out most of its earnings, so a two-stage dividend discount model works.
- Sun Pharma pays out only about a third (it reinvests in R&D and acquisitions),
  so a DDM would badly undervalue it; ICICI is a bank, where free cash flow is
  not meaningful. Both use a two-stage residual-income (book value) model whose
  terminal value is book x justified P/B = (ROE - g) / (r - g).

Starting values for price and beta come from data/latest (run the pipeline
first). Fundamentals were read from Screener.in public company pages (2 and 13
Oct 2026) and dividends from Yahoo Finance; each cell cites its source.

Run from the project root, then recalculate in Excel:
    python scripts/build_valuation_workbook.py --force
    python scripts/recalc_excel.py workbook/valuation.xlsx
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import load_config, project_path  # noqa: E402

OUT = ROOT / "workbook" / "valuation.xlsx"
SCREENER = "Screener.in public page (consolidated)"

# Formatting conventions (stated in the README sheet).
FONT = "Arial"
BLUE, GREEN, BLACK, GREY = "0000FF", "008000", "000000", "666666"
YELLOW = PatternFill("solid", fgColor="FFFF00")
HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
THIN = Side(style="thin", color="999999")
RUPEE, PCT, MULT, NUM = '"₹"#,##0.00', "0.0%", '0.0"x"', "0.00"

HUL, SUN, ICICI = "HINDUNILVR.NS", "SUNPHARMA.NS", "ICICIBANK.NS"
STOCKS = [HUL, SUN, ICICI]
COLS = {HUL: "B", SUN: "C", ICICI: "D"}
RI_STOCKS = [SUN, ICICI]          # valued with the residual-income model


def put(ws, ref, value, color=BLACK, fmt=None, bold=False, fill=None, italic=False):
    cell = ws[ref]
    cell.value = value
    cell.font = Font(name=FONT, size=10, color=color, bold=bold, italic=italic)
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill
    return cell


def header_row(ws, row, labels, start_col=1):
    for i, label in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=label)
        c.font = Font(name=FONT, size=10, bold=True)
        c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = Border(bottom=THIN)


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


def title(ws, text):
    put(ws, "A1", text).font = Font(name=FONT, size=14, bold=True)


def build_readme(wb):
    ws = wb.active
    ws.title = "README"
    lines = [
        ("Valuation workbook: Hindustan Unilever, Sun Pharma, ICICI Bank", True),
        ("", False),
        ("Colour code", True),
        ("Blue text = hardcoded input (each cites its source in the notes column)", False),
        ("Black text = formula", False),
        ("Green text = link pulled from another sheet", False),
        ("Yellow fill = key assumption the group should review", False),
        ("", False),
        ("Sheets", True),
        ("Inputs: market rates, company data and model assumptions. The only sheet you need to edit.", False),
        ("DDM: two-stage dividend discount model for HUL, which pays out most of its earnings (BKM Ch 18).", False),
        ("ResidualIncome: two-stage residual-income model for Sun Pharma (low payout) and ICICI Bank (a bank); "
         "terminal value = book x justified P/B.", False),
        ("Comps: peer multiples. Banks use P/B scaled by ROE because justified P/B rises with ROE.", False),
        ("Sensitivity: intrinsic value across cost of equity (rows) and terminal growth (columns).", False),
        ("Summary: one row per stock. The Python pipeline reads this sheet; keep its layout.", False),
        ("", False),
        ("Why different models", True),
        ("A DDM values only the dividends paid. For a company that reinvests two-thirds of its earnings "
         "(Sun Pharma), it misses most of the value; residual income values the book equity the company keeps "
         "building instead. Both models agree when payout is high.", False),
        ("", False),
        ("How to update", True),
        ("1. Change blue/yellow cells on Inputs.  2. Save in Excel (this stores the computed values).", False),
        ("3. Run `python -m pipeline.run_all` to refresh valuation.json.", False),
        ("", False),
        ("Method notes and caveats", True),
        ("Cost of equity r = rf + beta x ERP. rf = 91-day T-bill (RBI); ERP = Damodaran India total ERP; "
         "beta = daily-return beta vs Nifty 50, 2016-2026 (pipeline).", False),
        ("Terminal growth is kept at or below rf (Damodaran's stable-growth rule: no firm outgrows the economy forever).",
         False),
        ("HUL's FY26 EPS (Rs 64.0) includes a ~Rs 3,900 Cr one-off gain in Q3 FY26. EPS here is price / "
         "Screener P/E, which excludes it (~Rs 47).", False),
        ("Blended value = simple average of the model value and the comps value (a judgement call).", False),
        ("Verdict: blended upside beyond +/- the band on Inputs = Undervalued / Overvalued.", False),
        ("These models are very sensitive to r and g; read the Sensitivity sheet before quoting a single number.", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        put(ws, f"A{i}", text, bold=bold)
    ws["A1"].font = Font(name=FONT, size=14, bold=True)
    widths(ws, {"A": 120})


def build_inputs(wb, cfg, prices, betas):
    ws = wb.create_sheet("Inputs")
    m = cfg["market"]
    title(ws, "Valuation inputs")
    put(ws, "A2", "Edit blue cells and yellow assumptions only. Everything else is a formula.",
        color=GREY, italic=True)
    put(ws, "A4", "Market", bold=True)
    rows = [
        (5, "Risk-free rate (91-day T-bill)", m["risk_free_rate"], PCT,
         f"{m['risk_free_source']}; RBI homepage, as of {m['risk_free_as_of']}"),
        (6, "Equity risk premium (India, total)", m["equity_risk_premium"], PCT,
         f"{m['erp_source']}, updated {m['erp_as_of']}"),
        (7, "Verdict band (+/- upside)", 0.15, PCT, "Assumption: blended upside beyond this = Under/Overvalued"),
        (8, "Price date", str(prices.index[-1].date()), None, "NSE close via Yahoo Finance (pipeline data/latest)"),
    ]
    for r, label, val, fmt, note in rows:
        put(ws, f"A{r}", label)
        put(ws, f"B{r}", val, color=BLUE, fmt=fmt, fill=YELLOW if r == 7 else None)
        put(ws, f"E{r}", note, color=GREY)

    header_row(ws, 10, ["Company inputs", "", "", "", "Source / note"])
    for t in STOCKS:
        ws[f"{COLS[t]}10"].value = cfg["universe"]["stocks"][t]["name"]

    na = "n/a"
    company_rows = [
        (11, "Ticker", {t: t for t in STOCKS}, None, "Yahoo Finance symbol", "input"),
        (12, "Valuation model", {HUL: "Two-stage DDM", SUN: "Two-stage residual income",
                                 ICICI: "Two-stage residual income (bank)"}, None,
         "DDM needs a high payout (HUL). Low payout (Sun) or a bank (ICICI) -> residual income", "input"),
        (13, "Price (Rs)", {t: round(float(prices[t].iloc[-1]), 2) for t in STOCKS}, RUPEE,
         "Pipeline data/latest/prices.parquet, last close", "input"),
        (14, "Beta vs Nifty 50", {t: round(float(betas[t]), 4) for t in STOCKS}, NUM,
         "Pipeline metrics.json: daily returns 2016 to price date", "input"),
        (15, "Cost of equity r = rf + beta x ERP", {t: "=$B$5+{c}14*$B$6" for t in STOCKS}, PCT,
         "CAPM (BKM Ch 9)", "formula"),
        (16, "Screener P/E (TTM, excl. exceptional items)", {HUL: 39.1, SUN: 33.4, ICICI: 16.8}, NUM,
         SCREENER + "; HUL and ICICI read 2 Oct, Sun 13 Oct 2026", "input"),
        (17, "EPS, TTM (Rs) = price / Screener P/E", {t: "={c}13/{c}16" for t in STOCKS}, RUPEE,
         "Same earnings basis as the peer P/Es on the Comps sheet", "formula"),
        (18, "EPS FY21 (Rs)", {HUL: 34.03, SUN: 12.10, ICICI: 26.58}, RUPEE,
         SCREENER + ", P&L table. Sun's FY21 EPS was depressed by a Rs 3,449 Cr exceptional charge, "
                    "so its 5-yr CAGR overstates growth (3-yr profit CAGR: 13%)", "input"),
        (19, "EPS growth, ~5-yr CAGR", {t: "=({c}17/{c}18)^(1/5)-1" for t in STOCKS}, PCT,
         "FY21 to TTM; a reference point for growth assumptions, not used directly", "formula"),
        (20, "Dividend per share FY26 = D0 (Rs)", {HUL: 41, SUN: 16, ICICI: 12}, RUPEE,
         "Yahoo Finance dividends: HUL 19 (Nov-25) + 22 (Jun-26); Sun 11 (Feb-26) + 5 (Jul-26); "
         "ICICI 12 (Aug-26)", "input"),
        (21, "Payout ratio (DPS / EPS TTM)", {t: "={c}20/{c}17" for t in STOCKS}, PCT, "", "formula"),
        (22, "Book value per share (Rs)", {HUL: 207, SUN: 348, ICICI: 527}, RUPEE, SCREENER, "input"),
        (23, "ROE, latest FY", {HUL: 0.310, SUN: 0.160, ICICI: 0.159}, PCT,
         SCREENER + " (HUL's figure includes the FY26 one-off gain)", "input"),
    ]
    assumption_rows = [
        (26, "High-growth years N (1 to 10)", {t: 5 for t in STOCKS}, "0",
         "Assumption: same horizon for all three for comparability", "assumption"),
        (27, "Dividend growth in high-growth phase g1 (DDM)", {HUL: 0.07, SUN: na, ICICI: na}, PCT,
         "Assumption. HUL: ~5-yr sales CAGR 6.5-7% with flat margins", "assumption"),
        (28, "ROE in high-growth phase (residual income)", {HUL: na, SUN: 0.16, ICICI: 0.16}, PCT,
         "Assumption. Sun: 5-yr average ROE 16%. ICICI: FY26 ROE (3-yr average 17%)", "assumption"),
        (29, "Payout in high-growth phase (residual income)", {HUL: na, SUN: 0.33, ICICI: 0.16}, PCT,
         "Assumption: FY26 payout per Screener (Sun 33%, ICICI 16%)", "assumption"),
        (30, "Stable ROE after year N (residual income)", {HUL: na, SUN: 0.14, ICICI: 0.15}, PCT,
         "Assumption. Sun: 10-yr average ROE 14%. ICICI: fades toward peers (11-14%) but stays above",
         "assumption"),
        (31, "Terminal growth g2 (keep at or below rf)", {t: 0.055 for t in STOCKS}, PCT,
         "Assumption: capped at rf, a proxy for long-run nominal growth", "assumption"),
        (32, "Check: g2 at or below rf", {t: '=IF({c}31<=$B$5,"OK","g2 above rf")' for t in STOCKS}, None,
         "", "formula"),
        (33, "Check: g2 below r", {t: '=IF({c}31<{c}15,"OK","g2 must be below r")' for t in STOCKS}, None,
         "", "formula"),
    ]
    put(ws, "A25", "Model assumptions (review these)", bold=True)
    for r, label, values, fmt, note, kind in company_rows + assumption_rows:
        put(ws, f"A{r}", label)
        put(ws, f"E{r}", note, color=GREY)
        for t in STOCKS:
            c, v = COLS[t], values[t]
            if isinstance(v, str) and v.startswith("="):
                put(ws, f"{c}{r}", v.format(c=c), fmt=fmt)
            elif v == na:
                put(ws, f"{c}{r}", v, color=GREY)
            else:
                put(ws, f"{c}{r}", v, color=BLUE, fmt=fmt, fill=YELLOW if kind == "assumption" else None)
    widths(ws, {"A": 46, "B": 20, "C": 20, "D": 30, "E": 100})
    ws.freeze_panes = "B11"


def build_ddm(wb) -> dict:
    """Two-stage DDM for HUL. Returns cell references for the Summary sheet."""
    ws = wb.create_sheet("DDM")
    title(ws, "Two-stage dividend discount model: Hindustan Unilever")
    put(ws, "A2", "Dividends grow at g1 for N years, then at g2 for ever. Value = PV of dividends in years "
                  "1-10 + PV of the terminal value at year 10. Years after N already grow at g2, so any N "
                  "from 1 to 10 gives the textbook two-stage value.", color=GREY, italic=True)
    c = COLS[HUL]
    header_row(ws, 4, ["Inputs (linked)", "Hindustan Unilever"])
    for r, label, src, fmt in [(5, "D0, dividend just paid (Rs)", 20, RUPEE), (6, "Cost of equity r", 15, PCT),
                               (7, "High-growth rate g1", 27, PCT), (8, "High-growth years N", 26, "0"),
                               (9, "Terminal growth g2", 31, PCT), (10, "Market price (Rs)", 13, RUPEE)]:
        put(ws, f"A{r}", label)
        put(ws, f"B{r}", f"=Inputs!{c}{src}", color=GREEN, fmt=fmt)
    header_row(ws, 12, ["Year", "Growth", "Dividend (Rs)", "PV (Rs)"])
    put(ws, "A13", 0)
    put(ws, "C13", "=B5", fmt=RUPEE)
    for t in range(1, 11):
        r = 13 + t
        put(ws, f"A{r}", t)
        put(ws, f"B{r}", f"=IF(A{r}<=$B$8,$B$7,$B$9)", fmt=PCT)
        put(ws, f"C{r}", f"=C{r-1}*(1+B{r})", fmt=RUPEE)
        put(ws, f"D{r}", f"=C{r}/(1+$B$6)^A{r}", fmt=RUPEE)
    header_row(ws, 25, ["Results", "Hindustan Unilever"])
    results = [
        (26, "PV of dividends, years 1-10 (Rs)", "=SUM(D14:D23)", RUPEE),
        (27, "Terminal value at year 10 (Rs)", "=C23*(1+B9)/(B6-B9)", RUPEE),
        (28, "PV of terminal value (Rs)", "=B27/(1+B6)^10", RUPEE),
        (29, "Intrinsic value per share (Rs)", "=B26+B28", RUPEE),
        (30, "Market price (Rs)", "=B10", RUPEE),
        (31, "Upside (intrinsic / price - 1)", "=B29/B30-1", PCT),
        (32, "Share of value from terminal value", "=B28/B29", PCT),
        (33, "Market-implied perpetual growth (reverse DDM)", "=(B6*B30-B5)/(B30+B5)", PCT),
        (34, "Check: closed-form two-stage value (Rs)",
         "=B5*(1+B7)/(B6-B7)*(1-((1+B7)/(1+B6))^B8)+B5*(1+B7)^B8*(1+B9)/((B6-B9)*(1+B6)^B8)", RUPEE),
        (35, "Check: table minus closed form (should be 0)", "=ROUND(B29-B34,6)", NUM),
    ]
    for r, label, f, fmt in results:
        put(ws, f"A{r}", label, bold=(r == 29))
        put(ws, f"B{r}", f, fmt=fmt, bold=(r == 29))
    put(ws, "A36", "Reverse DDM: the constant growth g at which Gordon's formula D0(1+g)/(r-g) equals "
                   "today's price, i.e. g = (r x P - D0) / (P + D0).", color=GREY, italic=True)
    widths(ws, {"A": 46, "B": 20, "C": 16, "D": 14})
    return {HUL: ("DDM!B29", "DDM!B33")}


def _ri_block(ws, top: int, ticker: str, name: str) -> tuple[str, str]:
    """One residual-income block starting at row `top`. Returns (intrinsic, implied-growth) cells."""
    c = COLS[ticker]
    put(ws, f"A{top}", name, bold=True).font = Font(name=FONT, size=12, bold=True)
    links = [("Book value per share now (Rs)", 22, RUPEE), ("Cost of equity r", 15, PCT),
             ("High-growth years N", 26, "0"), ("ROE in high-growth phase", 28, PCT),
             ("Payout in high-growth phase", 29, PCT), ("Stable ROE after year N", 30, PCT),
             ("Terminal growth g2", 31, PCT), ("Market price (Rs)", 13, RUPEE), ("ROE, latest FY", 23, PCT)]
    rows = {}
    for i, (label, src, fmt) in enumerate(links):
        r = top + 1 + i
        rows[src] = r
        put(ws, f"A{r}", label)
        put(ws, f"B{r}", f"=Inputs!{c}{src}", color=GREEN, fmt=fmt)
    bv, rr, n, roe_h, pay_h, roe_s, g2, price, roe_now = (f"$B${rows[k]}" for k in (22, 15, 26, 28, 29, 30, 31, 13, 23))
    sp = top + 10
    put(ws, f"A{sp}", "Stable payout = 1 - g2 / stable ROE")
    put(ws, f"B{sp}", f"=1-{g2}/{roe_s}", fmt=PCT)
    hdr = top + 12
    header_row(ws, hdr, ["Year", "Opening book (Rs)", "ROE", "EPS (Rs)", "Payout", "DPS (Rs)",
                         "Closing book (Rs)", "PV of DPS (Rs)"])
    first = hdr + 1
    for t in range(1, 11):
        r = hdr + t
        put(ws, f"A{r}", t)
        put(ws, f"B{r}", f"={bv}" if t == 1 else f"=G{r-1}", fmt=RUPEE)
        put(ws, f"C{r}", f"=IF(A{r}<={n},{roe_h},{roe_s})", fmt=PCT)
        put(ws, f"D{r}", f"=B{r}*C{r}", fmt=RUPEE)
        put(ws, f"E{r}", f"=IF(A{r}<={n},{pay_h},$B${sp})", fmt=PCT)
        put(ws, f"F{r}", f"=D{r}*E{r}", fmt=RUPEE)
        put(ws, f"G{r}", f"=B{r}+D{r}-F{r}", fmt=RUPEE)
        put(ws, f"H{r}", f"=F{r}/(1+{rr})^A{r}", fmt=RUPEE)
    last = hdr + 10
    res = last + 2
    header_row(ws, res, ["Results", name])
    gb = f"{roe_h}*(1-{pay_h})"   # book growth in the high-growth phase
    lines = [
        ("PV of dividends, years 1-10 (Rs)", f"=SUM(H{first}:H{last})", RUPEE),
        ("Justified P/B at year 10 = (ROE - g2) / (r - g2)", f"=({roe_s}-{g2})/({rr}-{g2})", MULT),
        ("Terminal value = book at year 10 x justified P/B (Rs)", f"=G{last}*B{res + 2}", RUPEE),
        ("PV of terminal value (Rs)", f"=B{res + 3}/(1+{rr})^10", RUPEE),
        ("Intrinsic value per share (Rs)", f"=B{res + 1}+B{res + 4}", RUPEE),
        ("Market price (Rs)", f"={price}", RUPEE),
        ("Upside (intrinsic / price - 1)", f"=B{res + 5}/B{res + 6}-1", PCT),
        ("Intrinsic P/B (intrinsic / book now)", f"=B{res + 5}/{bv}", MULT),
        ("Market P/B (price / book now)", f"=B{res + 6}/{bv}", MULT),
        ("Market-implied perpetual growth at today's ROE", f"=({rr}*B{res + 9}-{roe_now})/(B{res + 9}-1)", PCT),
        ("Check: closed-form value (Rs)",
         f"={pay_h}*{roe_h}*{bv}/({rr}-{gb})*(1-((1+{gb})/(1+{rr}))^{n})"
         f"+{bv}*(1+{gb})^{n}*({roe_s}-{g2})/({rr}-{g2})/(1+{rr})^{n}", RUPEE),
        ("Check: table minus closed form (should be 0)", f"=ROUND(B{res + 5}-B{res + 11},6)", NUM),
    ]
    for i, (label, f, fmt) in enumerate(lines, start=1):
        r = res + i
        put(ws, f"A{r}", label, bold=(i == 5))
        put(ws, f"B{r}", f, fmt=fmt, bold=(i == 5))
    return f"ResidualIncome!B{res + 5}", f"ResidualIncome!B{res + 10}"


def build_residual_income(wb, cfg) -> dict:
    ws = wb.create_sheet("ResidualIncome")
    title(ws, "Two-stage residual-income (P/B) model: Sun Pharma and ICICI Bank")
    put(ws, "A2", "Book value compounds at ROE x retention. For N years the company keeps its current ROE and "
                  "payout; afterwards payout = 1 - g2/ROE, just enough retention to grow book at g2. Terminal "
                  "value = book value x justified P/B, where justified P/B = (ROE - g) / (r - g). Implied growth "
                  "solves single-stage P/B = (ROE - g)/(r - g): g = (r x P/B - ROE) / (P/B - 1).",
        color=GREY, italic=True)
    refs, top = {}, 4
    for t in RI_STOCKS:
        refs[t] = _ri_block(ws, top, t, cfg["universe"]["stocks"][t]["name"])
        top += 40
    widths(ws, {"A": 50, "B": 18, "C": 10, "D": 12, "E": 10, "F": 12, "G": 18, "H": 16})
    return refs


def build_comps(wb):
    ws = wb.create_sheet("Comps")
    title(ws, "Peer multiples")
    put(ws, "A2", "Peer figures: " + SCREENER + ", read 2 Oct (FMCG, banks) and 13 Oct 2026 (pharma). "
                  "P/E is Screener's TTM P/E.", color=GREY, italic=True)

    def pe_block(top, heading, peers, target_col, target_name):
        put(ws, f"A{top}", heading, bold=True)
        header_row(ws, top + 1, ["Peer", "P/E (TTM)", "Price (Rs)"])
        for i, (name, pe, price) in enumerate(peers):
            r = top + 2 + i
            put(ws, f"A{r}", name)
            put(ws, f"B{r}", pe, color=BLUE, fmt=NUM)
            put(ws, f"C{r}", price, color=BLUE, fmt=RUPEE)
        first, last = top + 2, top + 1 + len(peers)
        med, eps, val = last + 1, last + 2, last + 3
        put(ws, f"A{med}", "Median peer P/E", bold=True)
        put(ws, f"B{med}", f"=MEDIAN(B{first}:B{last})", fmt=NUM, bold=True)
        put(ws, f"A{eps}", f"{target_name} EPS, TTM (Rs)")
        put(ws, f"B{eps}", f"=Inputs!{target_col}17", color=GREEN, fmt=RUPEE)
        put(ws, f"A{val}", f"{target_name} value at median P/E (Rs)", bold=True)
        put(ws, f"B{val}", f"=B{med}*B{eps}", fmt=RUPEE, bold=True)
        return val

    hul_val = pe_block(4, "FMCG peers for Hindustan Unilever",
                       [("Nestle India", 68.0, 1308), ("Britannia Industries", 44.2, 4778),
                        ("Dabur India", 33.5, 374)], COLS[HUL], "HUL")
    sun_val = pe_block(hul_val + 2, "Pharma peers for Sun Pharma",
                       [("Cipla", 29.9, 1325), ("Dr Reddy's Laboratories", 32.3, 1244),
                        ("Divi's Laboratories", 82.2, 9224)], COLS[SUN], "Sun Pharma")

    top = sun_val + 2
    put(ws, f"A{top}", "Private bank peers for ICICI Bank", bold=True)
    header_row(ws, top + 1, ["Peer", "P/E (TTM)", "Price (Rs)", "Book value (Rs)", "ROE",
                             "P/B", "P/B per unit of ROE"])
    banks = [("HDFC Bank", 14.1, 721, 390, 0.136), ("Kotak Mahindra Bank", 20.8, 418, 182, 0.114),
             ("Axis Bank", 13.6, 1217, 712, 0.131)]
    for i, (name, pe, price, bv, roe) in enumerate(banks):
        r = top + 2 + i
        put(ws, f"A{r}", name)
        put(ws, f"B{r}", pe, color=BLUE, fmt=NUM)
        put(ws, f"C{r}", price, color=BLUE, fmt=RUPEE)
        put(ws, f"D{r}", bv, color=BLUE, fmt=RUPEE)
        put(ws, f"E{r}", roe, color=BLUE, fmt=PCT)
        put(ws, f"F{r}", f"=C{r}/D{r}", fmt=MULT)
        put(ws, f"G{r}", f"=F{r}/E{r}", fmt=NUM)
    first, last = top + 2, top + 1 + len(banks)
    r = last + 1
    put(ws, f"A{r}", "Median", bold=True)
    for col, fmt in (("B", NUM), ("F", MULT), ("G", NUM)):
        put(ws, f"{col}{r}", f"=MEDIAN({col}{first}:{col}{last})", fmt=fmt, bold=True)
    put(ws, f"A{r+1}", "ICICI Bank ROE (latest FY)")
    put(ws, f"B{r+1}", f"=Inputs!{COLS[ICICI]}23", color=GREEN, fmt=PCT)
    put(ws, f"A{r+2}", "ICICI Bank book value per share (Rs)")
    put(ws, f"B{r+2}", f"=Inputs!{COLS[ICICI]}22", color=GREEN, fmt=RUPEE)
    put(ws, f"A{r+3}", "ICICI value at median P/B (Rs), for reference")
    put(ws, f"B{r+3}", f"=F{r}*B{r+2}", fmt=RUPEE)
    put(ws, f"A{r+4}", "ICICI value at ROE-adjusted median P/B (Rs)", bold=True)
    put(ws, f"B{r+4}", f"=G{r}*B{r+1}*B{r+2}", fmt=RUPEE, bold=True)
    put(ws, f"A{r+5}", "ROE-adjusted because justified P/B = (ROE - g)/(r - g) rises with ROE, and ICICI's "
                       "ROE is above all three peers.", color=GREY, italic=True)
    widths(ws, {"A": 44, "B": 14, "C": 14, "D": 16, "E": 10, "F": 10, "G": 18})
    return {HUL: f"Comps!B{hul_val}", SUN: f"Comps!B{sun_val}", ICICI: f"Comps!B{r+4}"}


def build_sensitivity(wb, cfg):
    ws = wb.create_sheet("Sensitivity")
    title(ws, "Intrinsic value (Rs) vs cost of equity and terminal growth")
    put(ws, "A2", "Rows shift r from its CAPM base; columns shift g2 from its base. Other inputs as on "
                  "Inputs. Bold cell = base case. Blank where g2 >= r (formula invalid).",
        color=GREY, italic=True)
    r_shifts = [-0.02, -0.01, 0.0, 0.01, 0.02]
    g_shifts = [-0.015, -0.01, -0.005, 0.0, 0.005]
    ddm = ("{D0}*(1+{g1})/({r}-{g1})*(1-((1+{g1})/(1+{r}))^{N})"
           "+{D0}*(1+{g1})^{N}*(1+{g})/(({r}-{g})*(1+{r})^{N})")
    ri = ("{p}*{roe}*{bv}/({r}-{roe}*(1-{p}))*(1-((1+{roe}*(1-{p}))/(1+{r}))^{N})"
          "+{bv}*(1+{roe}*(1-{p}))^{N}*({roes}-{g})/({r}-{g})/(1+{r})^{N}")

    def refs(col, kind):
        if kind == "ddm":
            return {"D0": f"Inputs!${col}$20", "g1": f"Inputs!${col}$27", "N": f"Inputs!${col}$26"}
        return {"p": f"Inputs!${col}$29", "roe": f"Inputs!${col}$28", "bv": f"Inputs!${col}$22",
                "roes": f"Inputs!${col}$30", "N": f"Inputs!${col}$26"}

    blocks = [(HUL, "two-stage DDM", ddm, "ddm"), (SUN, "two-stage residual income", ri, "ri"),
              (ICICI, "two-stage residual income", ri, "ri")]
    top = 4
    for ticker, model, template, kind in blocks:
        col = COLS[ticker]
        put(ws, f"A{top}", f"{cfg['universe']['stocks'][ticker]['name']} ({model})", bold=True)
        put(ws, f"A{top+1}", "r  \\  g2", bold=True)
        for j, gs in enumerate(g_shifts):
            c = get_column_letter(2 + j)
            put(ws, f"{c}{top+1}", f"=Inputs!${col}$31+({gs})", fmt=PCT, bold=True)
        for i, rs in enumerate(r_shifts):
            row = top + 2 + i
            put(ws, f"A{row}", f"=Inputs!${col}$15+({rs})", fmt=PCT, bold=True)
            for j in range(len(g_shifts)):
                c = get_column_letter(2 + j)
                formula = template.format(r=f"$A{row}", g=f"{c}${top+1}", **refs(col, kind))
                put(ws, f"{c}{row}", f'=IF({c}${top+1}<$A{row},{formula},"")', fmt='"₹"#,##0',
                    bold=(rs == 0.0 and g_shifts[j] == 0.0))
        put(ws, f"A{top+7}", "Market price (Rs)")
        put(ws, f"B{top+7}", f"=Inputs!{col}13", color=GREEN, fmt=RUPEE)
        top += 10
    widths(ws, {"A": 40, "B": 12, "C": 12, "D": 12, "E": 12, "F": 12})


def build_summary(wb, model_refs, comps_refs):
    ws = wb.create_sheet("Summary")
    headers = ["ticker", "name", "model", "price", "cost_of_equity", "intrinsic_value", "model_upside",
               "comps_value", "comps_upside", "blended_value", "blended_upside",
               "market_implied_growth", "verdict"]
    header_row(ws, 1, headers)
    for i, t in enumerate(STOCKS):
        r, c = 2 + i, COLS[t]
        intrinsic, implied_g = model_refs[t]
        row = [
            (f"=Inputs!{c}11", None, GREEN), (f"=Inputs!{c}10", None, GREEN),
            (f"=Inputs!{c}12", None, GREEN), (f"=Inputs!{c}13", RUPEE, GREEN),
            (f"=Inputs!{c}15", PCT, GREEN), (f"={intrinsic}", RUPEE, GREEN),
            (f"=F{r}/D{r}-1", PCT, BLACK), (f"={comps_refs[t]}", RUPEE, GREEN),
            (f"=H{r}/D{r}-1", PCT, BLACK), (f"=AVERAGE(F{r},H{r})", RUPEE, BLACK),
            (f"=J{r}/D{r}-1", PCT, BLACK), (f"={implied_g}", PCT, GREEN),
            (f'=IF(K{r}>Inputs!$B$7,"Undervalued",IF(K{r}<-Inputs!$B$7,"Overvalued","Fairly valued"))',
             None, BLACK),
        ]
        for j, (f, fmt, color) in enumerate(row):
            put(ws, f"{get_column_letter(1 + j)}{r}", f, color=color, fmt=fmt)
    widths(ws, {get_column_letter(i + 1): w for i, w in
                enumerate([16, 20, 32, 12, 14, 14, 13, 13, 13, 13, 14, 20, 14])})
    ws.freeze_panes = "A2"


def main(force: bool) -> None:
    if OUT.exists() and not force:
        sys.exit(f"{OUT} exists and may hold manual edits. Use --force to overwrite it.")
    cfg = load_config()
    if list(cfg["universe"]["stocks"]) != STOCKS:
        sys.exit(f"config.yaml lists {list(cfg['universe']['stocks'])}; this script is written for {STOCKS}")
    latest = project_path(cfg["data"]["latest_dir"])
    prices = pd.read_parquet(latest / "prices.parquet")
    metrics = json.loads((latest / "metrics.json").read_text(encoding="utf-8"))
    betas = {t: metrics["securities"][t]["beta"] for t in STOCKS}

    wb = Workbook()
    build_readme(wb)
    build_inputs(wb, cfg, prices, betas)
    model_refs = {**build_ddm(wb), **build_residual_income(wb, cfg)}
    comps_refs = build_comps(wb)
    build_sensitivity(wb, cfg)
    build_summary(wb, model_refs, comps_refs)
    OUT.parent.mkdir(exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT}. Now recalculate: python scripts/recalc_excel.py {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold the valuation workbook")
    parser.add_argument("--force", action="store_true", help="overwrite an existing workbook")
    main(parser.parse_args().force)
