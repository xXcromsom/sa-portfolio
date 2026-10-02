"""Scaffold workbook/valuation.xlsx with live formulas (run once).

After this, the workbook is the source of truth: edit inputs in Excel, save, and
the pipeline reads its Summary sheet. Re-running this script would overwrite
those edits, so it refuses to run if the file exists unless --force is passed.

Starting values for price and beta come from data/latest (run the pipeline
first). Fundamentals were read from Screener.in public company pages on
2 Oct 2026 and dividends from Yahoo Finance; each cell cites its source.

Run from the project root, then recalculate in Excel:
    python scripts/build_valuation_workbook.py
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
SCREENER = "Screener.in public page, read 2 Oct 2026 (consolidated)"

# Formatting conventions (stated in the README sheet).
FONT = "Arial"
BLUE, GREEN, BLACK, GREY = "0000FF", "008000", "000000", "666666"
YELLOW = PatternFill("solid", fgColor="FFFF00")
HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
THIN = Side(style="thin", color="999999")
RUPEE, PCT, MULT, NUM = '"₹"#,##0.00', "0.0%", '0.0"x"', "0.00"

STOCKS = ["HINDUNILVR.NS", "INFY.NS", "ICICIBANK.NS"]
COLS = {"HINDUNILVR.NS": "B", "INFY.NS": "C", "ICICIBANK.NS": "D"}


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


def build_readme(wb):
    ws = wb.active
    ws.title = "README"
    lines = [
        ("Valuation workbook: Hindustan Unilever, Infosys, ICICI Bank", True),
        ("", False),
        ("Colour code", True),
        ("Blue text = hardcoded input (each cites its source in the notes column)", False),
        ("Black text = formula", False),
        ("Green text = link pulled from another sheet", False),
        ("Yellow fill = key assumption the group should review", False),
        ("", False),
        ("Sheets", True),
        ("Inputs: market rates, company data and model assumptions. The only sheet you need to edit.", False),
        ("DDM: two-stage dividend discount model for HUL and Infosys (BKM Ch 18).", False),
        ("Bank: two-stage P/B (residual income) model for ICICI Bank; terminal value = book x justified P/B.", False),
        ("Comps: peer multiples. Banks use P/B scaled by ROE because justified P/B rises with ROE.", False),
        ("Sensitivity: intrinsic value across cost of equity (rows) and terminal growth (columns).", False),
        ("Summary: one row per stock. The Python pipeline reads this sheet; keep its layout.", False),
        ("", False),
        ("How to update", True),
        ("1. Change blue/yellow cells on Inputs.  2. Save in Excel (this stores the computed values).", False),
        ("3. Run `python -m pipeline.run_all` to refresh valuation.json.", False),
        ("", False),
        ("Method notes and caveats", True),
        ("Cost of equity r = rf + beta x ERP. rf = 91-day T-bill (RBI); ERP = Damodaran India total ERP; "
         "beta = daily-return beta vs Nifty 50, 2016-2026 (pipeline).", False),
        ("Terminal growth is kept at or below rf (Damodaran's stable-growth rule: no firm outgrows the economy forever).", False),
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
    put(ws, "A1", "Valuation inputs", bold=True).font = Font(name=FONT, size=14, bold=True)
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

    header_row(ws, 10, ["Company inputs", "Hindustan Unilever", "Infosys", "ICICI Bank", "Source / note"])
    names = [cfg["universe"]["stocks"][t]["name"] for t in STOCKS]
    for t, name in zip(STOCKS, names):
        ws[f"{COLS[t]}10"].value = name

    # (row, label, {ticker: value or formula template}, fmt, note, kind)
    # kind: "input" (blue), "formula" (black), "assumption" (blue + yellow)
    company_rows = [
        (11, "Ticker", {t: t for t in STOCKS}, None, "Yahoo Finance symbol", "input"),
        (12, "Valuation model", {"HINDUNILVR.NS": "Two-stage DDM", "INFY.NS": "Two-stage DDM",
                                 "ICICIBANK.NS": "Two-stage P/B (residual income)"}, None,
         "Banks: free cash flow is not meaningful, so value book value x justified P/B", "input"),
        (13, "Price (Rs)", {t: round(float(prices[t].iloc[-1]), 2) for t in STOCKS}, RUPEE,
         "Pipeline data/latest/prices.parquet, last close", "input"),
        (14, "Beta vs Nifty 50", {t: round(float(betas[t]), 4) for t in STOCKS}, NUM,
         "Pipeline metrics.json: daily returns 2016 to price date", "input"),
        (15, "Cost of equity r = rf + beta x ERP", {t: "=$B$5+{c}14*$B$6" for t in STOCKS}, PCT,
         "CAPM (BKM Ch 9)", "formula"),
        (16, "Screener P/E (TTM, excl. exceptional items)",
         {"HINDUNILVR.NS": 39.1, "INFY.NS": 13.5, "ICICIBANK.NS": 16.8}, NUM, SCREENER, "input"),
        (17, "EPS, TTM (Rs) = price / Screener P/E", {t: "={c}13/{c}16" for t in STOCKS}, RUPEE,
         "Same earnings basis as the peer P/Es on the Comps sheet", "formula"),
        (18, "EPS FY21 (Rs)", {"HINDUNILVR.NS": 34.03, "INFY.NS": 45.42, "ICICIBANK.NS": 26.58}, RUPEE,
         SCREENER + ", P&L table", "input"),
        (19, "EPS growth, ~5-yr CAGR", {t: "=({c}17/{c}18)^(1/5)-1" for t in STOCKS}, PCT,
         "FY21 to TTM; a reference point for g1, not used directly", "formula"),
        (20, "Dividend per share FY26 = D0 (Rs)", {"HINDUNILVR.NS": 41, "INFY.NS": 48, "ICICIBANK.NS": 12},
         RUPEE, "Yahoo Finance dividends: HUL 19 (Nov-25) + 22 (Jun-26); INFY 23 (Oct-25) + 25 (Jun-26); "
         "ICICI 12 (Aug-26)", "input"),
        (21, "Payout ratio (DPS / EPS TTM)", {t: "={c}20/{c}17" for t in STOCKS}, PCT, "", "formula"),
        (22, "Book value per share (Rs)", {"HINDUNILVR.NS": 207, "INFY.NS": 225, "ICICIBANK.NS": 527},
         RUPEE, SCREENER, "input"),
        (23, "ROE, latest FY", {"HINDUNILVR.NS": 0.310, "INFY.NS": 0.319, "ICICIBANK.NS": 0.159}, PCT,
         SCREENER + " (HUL's figure includes the FY26 one-off gain)", "input"),
    ]
    assumption_rows = [
        (26, "High-growth years N (1 to 10)", {t: 5 for t in STOCKS}, "0",
         "Assumption: same horizon for all three for comparability", "assumption"),
        (27, "Dividend growth in high-growth phase g1 (DDM)",
         {"HINDUNILVR.NS": 0.07, "INFY.NS": 0.08, "ICICIBANK.NS": "n/a"}, PCT,
         "Assumption. HUL: ~5-yr sales CAGR 6.5-7% with flat margins. INFY: between 5-yr EPS CAGR "
         "(~10%) and 3-yr profit growth (8%)", "assumption"),
        (28, "ROE in high-growth phase (bank)", {"HINDUNILVR.NS": "n/a", "INFY.NS": "n/a",
                                                 "ICICIBANK.NS": 0.16}, PCT,
         "Assumption: FY26 ROE held for N years (3-yr average was 17%)", "assumption"),
        (29, "Payout in high-growth phase (bank)", {"HINDUNILVR.NS": "n/a", "INFY.NS": "n/a",
                                                    "ICICIBANK.NS": 0.16}, PCT,
         "Assumption: FY26 payout per Screener (16%)", "assumption"),
        (30, "Stable ROE after year N (bank)", {"HINDUNILVR.NS": "n/a", "INFY.NS": "n/a",
                                                "ICICIBANK.NS": 0.15}, PCT,
         "Assumption: ROE fades toward the peer range (11-14%) but stays above it", "assumption"),
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
            c = COLS[t]
            v = values[t]
            if isinstance(v, str) and v.startswith("="):
                put(ws, f"{c}{r}", v.format(c=c), fmt=fmt)
            elif v == "n/a":
                put(ws, f"{c}{r}", v, color=GREY)
            else:
                put(ws, f"{c}{r}", v, color=BLUE, fmt=fmt,
                    fill=YELLOW if kind == "assumption" else None)
    widths(ws, {"A": 44, "B": 20, "C": 20, "D": 30, "E": 95})
    ws.freeze_panes = "B11"


def build_ddm(wb):
    ws = wb.create_sheet("DDM")
    put(ws, "A1", "Two-stage dividend discount model: Hindustan Unilever and Infosys").font = \
        Font(name=FONT, size=14, bold=True)
    put(ws, "A2", "Dividends grow at g1 for N years, then at g2 for ever. Value = PV of dividends in years "
                  "1-10 + PV of the terminal value at year 10. Years after N already grow at g2, so any N "
                  "from 1 to 10 gives the textbook two-stage value.", color=GREY, italic=True)
    header_row(ws, 4, ["Inputs (linked)", "Hindustan Unilever", "Infosys"])
    links = [(5, "D0, dividend just paid (Rs)", 20, RUPEE), (6, "Cost of equity r", 15, PCT),
             (7, "High-growth rate g1", 27, PCT), (8, "High-growth years N", 26, "0"),
             (9, "Terminal growth g2", 31, PCT), (10, "Market price (Rs)", 13, RUPEE)]
    for r, label, src_row, fmt in links:
        put(ws, f"A{r}", label)
        put(ws, f"B{r}", f"=Inputs!B{src_row}", color=GREEN, fmt=fmt)
        put(ws, f"C{r}", f"=Inputs!C{src_row}", color=GREEN, fmt=fmt)

    header_row(ws, 12, ["Year", "HUL growth", "HUL dividend (Rs)", "HUL PV (Rs)",
                        "INFY growth", "INFY dividend (Rs)", "INFY PV (Rs)"])
    put(ws, "A13", 0)
    put(ws, "C13", "=B5", fmt=RUPEE)
    put(ws, "F13", "=C5", fmt=RUPEE)
    for t in range(1, 11):
        r = 13 + t
        put(ws, f"A{r}", t)
        put(ws, f"B{r}", f"=IF(A{r}<=$B$8,$B$7,$B$9)", fmt=PCT)
        put(ws, f"C{r}", f"=C{r-1}*(1+B{r})", fmt=RUPEE)
        put(ws, f"D{r}", f"=C{r}/(1+$B$6)^A{r}", fmt=RUPEE)
        put(ws, f"E{r}", f"=IF(A{r}<=$C$8,$C$7,$C$9)", fmt=PCT)
        put(ws, f"F{r}", f"=F{r-1}*(1+E{r})", fmt=RUPEE)
        put(ws, f"G{r}", f"=F{r}/(1+$C$6)^A{r}", fmt=RUPEE)

    header_row(ws, 25, ["Results", "Hindustan Unilever", "Infosys"])
    results = [
        (26, "PV of dividends, years 1-10 (Rs)", "=SUM(D14:D23)", "=SUM(G14:G23)", RUPEE),
        (27, "Terminal value at year 10 (Rs)", "=C23*(1+B9)/(B6-B9)", "=F23*(1+C9)/(C6-C9)", RUPEE),
        (28, "PV of terminal value (Rs)", "=B27/(1+B6)^10", "=C27/(1+C6)^10", RUPEE),
        (29, "Intrinsic value per share (Rs)", "=B26+B28", "=C26+C28", RUPEE),
        (30, "Market price (Rs)", "=B10", "=C10", RUPEE),
        (31, "Upside (intrinsic / price - 1)", "=B29/B30-1", "=C29/C30-1", PCT),
        (32, "Share of value from terminal value", "=B28/B29", "=C28/C29", PCT),
        (33, "Market-implied perpetual growth (reverse DDM)", "=(B6*B30-B5)/(B30+B5)",
         "=(C6*C30-C5)/(C30+C5)", PCT),
        (34, "Check: closed-form two-stage value (Rs)",
         "=B5*(1+B7)/(B6-B7)*(1-((1+B7)/(1+B6))^B8)+B5*(1+B7)^B8*(1+B9)/((B6-B9)*(1+B6)^B8)",
         "=C5*(1+C7)/(C6-C7)*(1-((1+C7)/(1+C6))^C8)+C5*(1+C7)^C8*(1+C9)/((C6-C9)*(1+C6)^C8)", RUPEE),
        (35, "Check: table minus closed form (should be 0)", "=ROUND(B29-B34,6)", "=ROUND(C29-C34,6)", NUM),
    ]
    for r, label, f_hul, f_infy, fmt in results:
        put(ws, f"A{r}", label, bold=(r == 29))
        put(ws, f"B{r}", f_hul, fmt=fmt, bold=(r == 29))
        put(ws, f"C{r}", f_infy, fmt=fmt, bold=(r == 29))
    put(ws, "A36", "Reverse DDM: the constant growth g at which Gordon's formula D0(1+g)/(r-g) equals "
                   "today's price, i.e. g = (r x P - D0) / (P + D0).", color=GREY, italic=True)
    widths(ws, {"A": 46, "B": 20, "C": 20, "D": 14, "E": 12, "F": 18, "G": 14})


def build_bank(wb):
    ws = wb.create_sheet("Bank")
    put(ws, "A1", "ICICI Bank: two-stage P/B (residual income) model").font = Font(name=FONT, size=14, bold=True)
    put(ws, "A2", "Book value compounds at ROE x retention. For N years the bank keeps its current ROE and "
                  "payout; afterwards payout = 1 - g2/ROE, just enough retention to grow book at g2. Terminal "
                  "value = book value x justified P/B, where justified P/B = (ROE - g) / (r - g).",
        color=GREY, italic=True)
    header_row(ws, 4, ["Inputs (linked)", "ICICI Bank"])
    links = [(5, "Book value per share now (Rs)", "=Inputs!D22", RUPEE),
             (6, "Cost of equity r", "=Inputs!D15", PCT),
             (7, "High-growth years N", "=Inputs!D26", "0"),
             (8, "ROE in high-growth phase", "=Inputs!D28", PCT),
             (9, "Payout in high-growth phase", "=Inputs!D29", PCT),
             (10, "Stable ROE after year N", "=Inputs!D30", PCT),
             (11, "Terminal growth g2", "=Inputs!D31", PCT),
             (12, "Market price (Rs)", "=Inputs!D13", RUPEE)]
    for r, label, f, fmt in links:
        put(ws, f"A{r}", label)
        put(ws, f"B{r}", f, color=GREEN, fmt=fmt)
    put(ws, "A13", "Stable payout = 1 - g2 / stable ROE")
    put(ws, "B13", "=1-B11/B10", fmt=PCT)

    header_row(ws, 15, ["Year", "Opening book (Rs)", "ROE", "EPS (Rs)", "Payout", "DPS (Rs)",
                        "Closing book (Rs)", "PV of DPS (Rs)"])
    for t in range(1, 11):
        r = 15 + t
        put(ws, f"A{r}", t)
        put(ws, f"B{r}", "=$B$5" if t == 1 else f"=G{r-1}", fmt=RUPEE)
        put(ws, f"C{r}", f"=IF(A{r}<=$B$7,$B$8,$B$10)", fmt=PCT)
        put(ws, f"D{r}", f"=B{r}*C{r}", fmt=RUPEE)
        put(ws, f"E{r}", f"=IF(A{r}<=$B$7,$B$9,$B$13)", fmt=PCT)
        put(ws, f"F{r}", f"=D{r}*E{r}", fmt=RUPEE)
        put(ws, f"G{r}", f"=B{r}+D{r}-F{r}", fmt=RUPEE)
        put(ws, f"H{r}", f"=F{r}/(1+$B$6)^A{r}", fmt=RUPEE)

    header_row(ws, 27, ["Results", "ICICI Bank"])
    results = [
        (28, "PV of dividends, years 1-10 (Rs)", "=SUM(H16:H25)", RUPEE),
        (29, "Justified P/B at year 10 = (ROE - g2) / (r - g2)", "=(B10-B11)/(B6-B11)", MULT),
        (30, "Terminal value = book at year 10 x justified P/B (Rs)", "=G25*B29", RUPEE),
        (31, "PV of terminal value (Rs)", "=B30/(1+B6)^10", RUPEE),
        (32, "Intrinsic value per share (Rs)", "=B28+B31", RUPEE),
        (33, "Market price (Rs)", "=B12", RUPEE),
        (34, "Upside (intrinsic / price - 1)", "=B32/B33-1", PCT),
        (35, "Intrinsic P/B (intrinsic / book now)", "=B32/B5", MULT),
        (36, "Market P/B (price / book now)", "=B33/B5", MULT),
        (37, "Market-implied perpetual growth at today's ROE", "=(B6*B36-Inputs!D23)/(B36-1)", PCT),
        (38, "Check: closed-form value (Rs)",
         "=B9*B8*B5/(B6-B8*(1-B9))*(1-((1+B8*(1-B9))/(1+B6))^B7)"
         "+B5*(1+B8*(1-B9))^B7*(B10-B11)/(B6-B11)/(1+B6)^B7", RUPEE),
        (39, "Check: table minus closed form (should be 0)", "=ROUND(B32-B38,6)", NUM),
    ]
    for r, label, f, fmt in results:
        put(ws, f"A{r}", label, bold=(r == 32))
        put(ws, f"B{r}", f, fmt=fmt, bold=(r == 32))
    put(ws, "A40", "Implied growth solves single-stage P/B = (ROE - g) / (r - g) for g: "
                   "g = (r x P/B - ROE) / (P/B - 1).", color=GREY, italic=True)
    widths(ws, {"A": 50, "B": 18, "C": 10, "D": 12, "E": 10, "F": 12, "G": 18, "H": 16})


def build_comps(wb):
    ws = wb.create_sheet("Comps")
    put(ws, "A1", "Peer multiples").font = Font(name=FONT, size=14, bold=True)
    put(ws, "A2", "Peer figures: " + SCREENER + ". P/E is Screener's TTM P/E.", color=GREY, italic=True)

    def pe_block(top, title, peers, target_col, target_name):
        put(ws, f"A{top}", title, bold=True)
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
                        ("Dabur India", 33.5, 374)], "B", "HUL")
    infy_val = pe_block(hul_val + 2, "IT services peers for Infosys",
                        [("TCS", 14.0, 2075), ("HCL Technologies", 18.6, 1243), ("Wipro", 11.9, 159)],
                        "C", "Infosys")

    top = infy_val + 2
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
    put(ws, f"B{r+1}", "=Inputs!D23", color=GREEN, fmt=PCT)
    put(ws, f"A{r+2}", "ICICI Bank book value per share (Rs)")
    put(ws, f"B{r+2}", "=Inputs!D22", color=GREEN, fmt=RUPEE)
    put(ws, f"A{r+3}", "ICICI value at median P/B (Rs), for reference")
    put(ws, f"B{r+3}", f"=F{r}*B{r+2}", fmt=RUPEE)
    put(ws, f"A{r+4}", "ICICI value at ROE-adjusted median P/B (Rs)", bold=True)
    put(ws, f"B{r+4}", f"=G{r}*B{r+1}*B{r+2}", fmt=RUPEE, bold=True)
    put(ws, f"A{r+5}", "ROE-adjusted because justified P/B = (ROE - g)/(r - g) rises with ROE, and ICICI's "
                       "ROE is above all three peers.", color=GREY, italic=True)
    widths(ws, {"A": 44, "B": 14, "C": 14, "D": 16, "E": 10, "F": 10, "G": 18})
    return {"HINDUNILVR.NS": f"Comps!B{hul_val}", "INFY.NS": f"Comps!B{infy_val}",
            "ICICIBANK.NS": f"Comps!B{r+4}"}


def build_sensitivity(wb):
    ws = wb.create_sheet("Sensitivity")
    put(ws, "A1", "Intrinsic value (Rs) vs cost of equity and terminal growth").font = \
        Font(name=FONT, size=14, bold=True)
    put(ws, "A2", "Rows shift r from its CAPM base; columns shift g2 from its base. Other inputs as on "
                  "Inputs. Bold cell = base case. Blank where g2 >= r (formula invalid).",
        color=GREY, italic=True)
    r_shifts = [-0.02, -0.01, 0.0, 0.01, 0.02]
    g_shifts = [-0.015, -0.01, -0.005, 0.0, 0.005]

    ddm = ("{D0}*(1+{g1})/({r}-{g1})*(1-((1+{g1})/(1+{r}))^{N})"
           "+{D0}*(1+{g1})^{N}*(1+{g})/(({r}-{g})*(1+{r})^{N})")
    bank = ("{p}*{roe}*{bv}/({r}-{roe}*(1-{p}))*(1-((1+{roe}*(1-{p}))/(1+{r}))^{N})"
            "+{bv}*(1+{roe}*(1-{p}))^{N}*({roes}-{g})/({r}-{g})/(1+{r})^{N}")
    blocks = [
        ("Hindustan Unilever (two-stage DDM)", "B", ddm,
         {"D0": "Inputs!$B$20", "g1": "Inputs!$B$27", "N": "Inputs!$B$26"}),
        ("Infosys (two-stage DDM)", "C", ddm,
         {"D0": "Inputs!$C$20", "g1": "Inputs!$C$27", "N": "Inputs!$C$26"}),
        ("ICICI Bank (two-stage P/B)", "D", bank,
         {"p": "Inputs!$D$29", "roe": "Inputs!$D$28", "bv": "Inputs!$D$22", "roes": "Inputs!$D$30",
          "N": "Inputs!$D$26"}),
    ]
    top = 4
    for title, col, template, refs in blocks:
        put(ws, f"A{top}", title, bold=True)
        put(ws, f"A{top+1}", "r  \\  g2", bold=True)
        for j, gs in enumerate(g_shifts):
            c = get_column_letter(2 + j)
            put(ws, f"{c}{top+1}", f"=Inputs!${col}$31+({gs})", fmt=PCT, bold=True)
        for i, rs in enumerate(r_shifts):
            row = top + 2 + i
            put(ws, f"A{row}", f"=Inputs!${col}$15+({rs})", fmt=PCT, bold=True)
            for j in range(len(g_shifts)):
                c = get_column_letter(2 + j)
                formula = template.format(r=f"$A{row}", g=f"{c}${top+1}", **refs)
                put(ws, f"{c}{row}", f'=IF({c}${top+1}<$A{row},{formula},"")', fmt='"₹"#,##0',
                    bold=(rs == 0.0 and g_shifts[j] == 0.0))
        put(ws, f"A{top+7}", "Market price (Rs)")
        put(ws, f"B{top+7}", f"=Inputs!{col}13", color=GREEN, fmt=RUPEE)
        top += 10
    widths(ws, {"A": 34, "B": 12, "C": 12, "D": 12, "E": 12, "F": 12})


def build_summary(wb, comps_refs):
    ws = wb.create_sheet("Summary")
    headers = ["ticker", "name", "model", "price", "cost_of_equity", "intrinsic_value", "model_upside",
               "comps_value", "comps_upside", "blended_value", "blended_upside",
               "market_implied_growth", "verdict"]
    header_row(ws, 1, headers)
    model_cells = {"HINDUNILVR.NS": ("DDM!B29", "DDM!B33"), "INFY.NS": ("DDM!C29", "DDM!C33"),
                   "ICICIBANK.NS": ("Bank!B32", "Bank!B37")}
    for i, t in enumerate(STOCKS):
        r, c = 2 + i, COLS[t]
        intrinsic, implied_g = model_cells[t]
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
                enumerate([16, 20, 30, 12, 14, 14, 13, 13, 13, 13, 14, 20, 14])})
    ws.freeze_panes = "A2"


def main(force: bool) -> None:
    if OUT.exists() and not force:
        sys.exit(f"{OUT} exists and may hold manual edits. Use --force to overwrite it.")
    cfg = load_config()
    latest = project_path(cfg["data"]["latest_dir"])
    prices = pd.read_parquet(latest / "prices.parquet")
    metrics = json.loads((latest / "metrics.json").read_text(encoding="utf-8"))
    betas = {t: metrics["securities"][t]["beta"] for t in STOCKS}

    wb = Workbook()
    build_readme(wb)
    build_inputs(wb, cfg, prices, betas)
    build_ddm(wb)
    build_bank(wb)
    comps_refs = build_comps(wb)
    build_sensitivity(wb)
    build_summary(wb, comps_refs)
    OUT.parent.mkdir(exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT}. Now recalculate: python scripts/recalc_excel.py {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold the valuation workbook")
    parser.add_argument("--force", action="store_true", help="overwrite an existing workbook")
    main(parser.parse_args().force)
