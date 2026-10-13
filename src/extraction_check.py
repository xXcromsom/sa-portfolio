"""Score the AI ratio extraction (data/ai/ratio_extraction.json) against Yahoo and Screener.

A field "matches" if it is within 1% of the reference. A larger gap counts as a
"definition difference" only when the two sources are known to define the item
differently (the reason is recorded next to the comparison). Anything else is an
"extraction error", and only those count against the AI.
"""
from __future__ import annotations

import yfinance as yf

TOLERANCE = 0.01

# Yahoo line item, statement, and how to build the comparable AI figure.
# The note explains any known definitional difference.
YAHOO = {
    "nonbank": [
        ("Revenue", "income_stmt", "Total Revenue", lambda a: a["revenue_from_operations"],
         "Yahoo 'Total Revenue' appears to exclude other operating revenue"),
        ("Net profit to owners", "income_stmt", "Net Income Common Stockholders", lambda a: a["net_profit_attributable"], ""),
        ("Basic EPS", "income_stmt", "Basic EPS", lambda a: a["eps_basic_rs"], ""),
        ("Equity to owners", "balance_sheet", "Stockholders Equity", lambda a: a["total_equity_attributable"], ""),
        ("Debt incl. leases", "balance_sheet", "Total Debt", lambda a: a["borrowings"] + a["lease_liabilities"],
         "Yahoo 'Total Debt' includes lease liabilities"),
        ("Cash and equivalents", "balance_sheet", "Cash And Cash Equivalents", lambda a: a["cash_and_equivalents"], ""),
        ("Shares (crore)", "balance_sheet", "Ordinary Shares Number", lambda a: a["shares_crore"], ""),
        ("Operating cash flow", "cashflow", "Operating Cash Flow", lambda a: a["operating_cash_flow"], ""),
        ("Dividends paid", "cashflow", "Cash Dividends Paid", lambda a: -a["dividends_paid"], ""),
    ],
    "bank": [
        ("Interest earned", "income_stmt", "Interest Income", lambda a: a["interest_earned"], ""),
        ("Interest expended", "income_stmt", "Interest Expense", lambda a: a["interest_expended"], ""),
        ("Net interest income", "income_stmt", "Net Interest Income",
         lambda a: a["interest_earned"] - a["interest_expended"], ""),
        ("Net profit to owners", "income_stmt", "Net Income Common Stockholders", lambda a: a["net_profit_attributable"], ""),
        ("Basic EPS", "income_stmt", "Basic EPS", lambda a: a["eps_basic_rs"], ""),
        ("Equity to owners", "balance_sheet", "Stockholders Equity", lambda a: a["total_equity_attributable"],
         "Yahoo includes employee stock options outstanding (Rs 2,682 Cr) in equity"),
        ("Borrowings", "balance_sheet", "Total Debt", lambda a: a["borrowings"],
         "Yahoo 'Total Debt' for banks is defined differently from the borrowings schedule"),
        ("Cash", "balance_sheet", "Cash And Cash Equivalents", lambda a: a["cash_and_equivalents"],
         "Yahoo adds balances with other banks and money at call; we took cash and RBI balances only"),
        ("Shares (crore)", "balance_sheet", "Ordinary Shares Number", lambda a: a["shares_crore"], ""),
        ("Operating cash flow", "cashflow", "Operating Cash Flow", lambda a: a["operating_cash_flow"], ""),
        ("Dividends paid", "cashflow", "Cash Dividends Paid", lambda a: -a["dividends_paid"], ""),
    ],
}

# Screener.in public pages (consolidated), read 2 Oct (HUL, ICICI) and 13 Oct 2026 (Sun Pharma).
SCREENER = {
    "HINDUNILVR.NS": [("Revenue", 64468, lambda a: a["revenue_from_operations"], ""),
                      ("Net profit", 15059, lambda a: a["net_profit_attributable"],
                       "Screener's net profit includes the minority share (Rs 19 Cr)"),
                      ("EPS", 64.01, lambda a: a["eps_basic_rs"], ""),
                      ("Equity (capital + reserves)", 48739, lambda a: a["total_equity_attributable"], ""),
                      ("Borrowings incl. leases", 1478, lambda a: a["borrowings"] + a["lease_liabilities"], ""),
                      ("Operating cash flow", 10999, lambda a: a["operating_cash_flow"], "")],
    "SUNPHARMA.NS": [("Revenue", 58462, lambda a: a["revenue_from_operations"], ""),
                     ("Net profit", 11509, lambda a: a["net_profit_attributable"],
                      "Screener's net profit includes the minority share (Rs 29 Cr)"),
                     ("EPS", 47.84, lambda a: a["eps_basic_rs"], ""),
                     ("Equity (capital + reserves)", 83570, lambda a: a["total_equity_attributable"], ""),
                     ("Borrowings incl. leases", 4627, lambda a: a["borrowings"] + a["lease_liabilities"], "")],
    "ICICIBANK.NS": [("Interest earned", 195218, lambda a: a["interest_earned"], ""),
                     ("Net profit (before minority)", 57936, lambda a: a["net_profit_before_minority"], ""),
                     ("EPS", 75.71, lambda a: a["eps_basic_rs"], "Screener computes EPS from profit / shares"),
                     ("Equity (capital + reserves)", 363060, lambda a: a["total_equity_attributable"],
                      "Screener's reserves include employee stock options outstanding"),
                     ("Deposits", 1830020, lambda a: a["deposits"], ""),
                     ("Borrowings", 220264, lambda a: a["borrowings"], ""),
                     ("Operating cash flow", 67325, lambda a: a["operating_cash_flow"], "")],
}


def _classify(ai: float, ref: float, note: str) -> tuple[float, str]:
    gap = (ai - ref) / abs(ref) if ref else float("inf")
    if abs(gap) <= TOLERANCE:
        return gap, "match"
    return gap, "definition difference" if note else "extraction error"


def yahoo_reference(ticker: str, session=None) -> dict[str, dict[str, float]]:
    """FY26 (31 Mar 2026) statement values from Yahoo, in Rs crore (EPS in Rs)."""
    t = yf.Ticker(ticker, session=session)
    out = {}
    for stmt in ("income_stmt", "balance_sheet", "cashflow"):
        df = getattr(t, stmt)
        col = next((c for c in df.columns if str(c.date()) == "2026-03-31"), None)
        if col is None:
            raise ValueError(f"Yahoo has no FY26 {stmt} for {ticker}")
        out[stmt] = {k: float(v) / (1 if k == "Basic EPS" else 1e7) for k, v in df[col].dropna().items()}
    return out


def score(extraction: dict, yahoo: dict[str, dict], banks: set[str]) -> dict:
    rows = []
    for ticker, ai in extraction["companies"].items():
        spec = YAHOO["bank" if ticker in banks else "nonbank"]
        for field, stmt, line, build, note in spec:
            ref = yahoo[ticker][stmt].get(line)
            if ref is None:
                continue
            gap, status = _classify(build(ai), ref, note)
            rows.append({"ticker": ticker, "field": field, "reference": "Yahoo", "ai": build(ai), "ref": ref,
                         "gap": gap, "status": status, "note": note if status != "match" else ""})
        for field, ref, build, note in SCREENER.get(ticker, []):
            gap, status = _classify(build(ai), ref, note)
            rows.append({"ticker": ticker, "field": field, "reference": "Screener", "ai": build(ai), "ref": ref,
                         "gap": gap, "status": status, "note": note if status != "match" else ""})
    counts = {s: sum(r["status"] == s for r in rows) for s in ("match", "definition difference", "extraction error")}
    return {"tolerance": TOLERANCE, "comparisons": len(rows), "counts": counts, "rows": rows}


def ratios(extraction: dict, banks: set[str]) -> dict:
    """Key ratios computed from the AI-extracted figures (Python does the arithmetic, not the AI)."""
    out = {}
    for ticker, a in extraction["companies"].items():
        np_, eq = a["net_profit_attributable"], a["total_equity_attributable"]
        r = {"roe": np_ / eq, "payout": a["dividends_paid"] / np_, "bvps": eq / a["shares_crore"],
             "eps_check": np_ / a["shares_crore"], "cfo_to_profit": a["operating_cash_flow"] / np_}
        if ticker in banks:
            nii = a["interest_earned"] - a["interest_expended"]
            r.update({"net_interest_income": nii, "credit_deposit_ratio": a["advances"] / a["deposits"],
                      "cost_to_income": a["operating_expenses"] / (nii + a["other_income"])})
        else:
            r.update({"net_margin": np_ / a["revenue_from_operations"],
                      "debt_to_equity": (a["borrowings"] + a["lease_liabilities"]) / eq})
            if "net_profit_continuing_operations" in a:
                r["roe_continuing"] = a["net_profit_continuing_operations"] / eq
        out[ticker] = r
    return out
