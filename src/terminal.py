"""Terminal look for the dashboard: colours, CSS, HTML blocks, chart styling and number formats.

Black background, amber labels, white values, green/red changes, monospace throughout,
in the spirit of a market-data terminal. The base theme is in .streamlit/config.toml.
"""
from __future__ import annotations

import html

import altair as alt

BG, PANEL, BORDER, GRID = "#000000", "#0B0E11", "#2A2F36", "#1A1F25"
AMBER, YELLOW, WHITE, TEXT, MUTED = "#FF9F1C", "#FFD166", "#FFFFFF", "#E6E6E6", "#8A939C"
CYAN, GREEN, RED, VIOLET, GREY = "#4FC3F7", "#3DDC84", "#FF5252", "#C792EA", "#5C6670"
MINUS = "−"

CSS = f"""
<style>
.block-container {{padding-top: 0.6rem; padding-bottom: 2rem; max-width: 100%;}}
header[data-testid="stHeader"] {{display: none;}}
h1, h2, h3, h4 {{color: {AMBER} !important; text-transform: uppercase; letter-spacing: 0.04em;}}
h3 {{font-size: 0.95rem !important; border-bottom: 1px solid {BORDER}; padding-bottom: 0.25rem;}}
[data-testid="stTab"] {{background: {PANEL}; border: 1px solid {BORDER}; margin-right: 3px; padding: 0.35rem 1rem;}}
[data-testid="stTab"] p {{color: {AMBER}; font-weight: 700; letter-spacing: 0.06em;}}
[data-testid="stTab"][aria-selected="true"] {{background: {AMBER}; border-color: {AMBER};}}
[data-testid="stTab"][aria-selected="true"] p {{color: {BG};}}
[data-testid="stMetricLabel"] p {{color: {AMBER}; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.05em;}}
[data-testid="stMetricValue"] {{color: {WHITE};}}
[data-testid="stWidgetLabel"] p {{color: {AMBER} !important; text-transform: uppercase; font-size: 0.75rem !important;}}
[data-testid="stRadio"] [role="radiogroup"] label p {{color: {TEXT}; font-size: 0.8rem;}}
.term-bar {{display: flex; flex-wrap: wrap; gap: 0 1.4rem; background: {AMBER}; color: {BG}; font-weight: 700;
  padding: 0.3rem 0.7rem; letter-spacing: 0.04em; font-size: 0.85rem;}}
.term-bar .go {{background: {BG}; color: {AMBER}; padding: 0 0.4rem;}}
.term-tape {{display: flex; flex-wrap: wrap; gap: 0 2rem; background: {PANEL}; border: 1px solid {BORDER}; border-top: none;
  padding: 0.3rem 0.7rem; font-size: 0.82rem; margin-bottom: 0.6rem;}}
.term-tape .tk {{color: {AMBER}; font-weight: 700;}} .term-tape .px {{color: {WHITE};}}
.up {{color: {GREEN};}} .down {{color: {RED};}} .mut {{color: {MUTED};}} .amb {{color: {AMBER};}} .cy {{color: {CYAN};}}
.term-head {{background: {PANEL}; border-left: 3px solid {AMBER}; color: {AMBER}; font-weight: 700; letter-spacing: 0.05em;
  padding: 0.25rem 0.6rem; margin: 0.8rem 0 0.4rem 0; text-transform: uppercase; font-size: 0.85rem;}}
.term-head .sub {{color: {MUTED}; font-weight: 400; text-transform: none; margin-left: 0.8rem;}}
.term-hl {{border: 2px solid {AMBER}; background: #120C02; padding: 0.7rem 0.9rem; margin: 0.4rem 0 0.8rem 0;}}
.term-hl .title {{color: {AMBER}; font-weight: 700; letter-spacing: 0.06em; margin-bottom: 0.4rem;}}
.term-kpis {{display: flex; flex-wrap: wrap; gap: 0.6rem 2.2rem;}}
.term-kpi .k {{color: {AMBER}; font-size: 0.7rem; letter-spacing: 0.05em; text-transform: uppercase;}}
.term-kpi .v {{color: {WHITE}; font-size: 1.45rem; font-weight: 700;}}
.term-kpi .v.big {{color: {YELLOW}; font-size: 1.9rem;}}
.term-kpi .s {{color: {MUTED}; font-size: 0.72rem;}}
table.term {{width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-bottom: 0.4rem;}}
table.term th {{background: #14181D; color: {AMBER}; text-align: right; padding: 0.3rem 0.5rem; border-bottom: 1px solid {BORDER};
  font-weight: 700; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.04em;}}
table.term td {{color: {TEXT}; text-align: right; padding: 0.25rem 0.5rem; border-bottom: 1px solid {GRID};}}
table.term th:first-child, table.term td:first-child, table.term.txt th, table.term.txt td {{text-align: left;}}
table.term td:first-child {{color: {WHITE}; font-weight: 700;}}
table.term tr.hl td {{background: #1C1405; color: {YELLOW};}}
table.term tr.tot td {{border-top: 1px solid {AMBER}; font-weight: 700; color: {WHITE};}}
.term-note {{color: {MUTED}; font-size: 0.75rem; margin: 0.2rem 0 0.6rem 0;}}
.term-warn {{border: 1px solid {YELLOW}; color: {YELLOW}; padding: 0.4rem 0.6rem; font-size: 0.8rem; margin: 0.4rem 0;}}
</style>
"""


def esc(x) -> str:
    return html.escape(str(x))


def inr(x: float, decimals: int = 0) -> str:
    """Indian digit grouping: 1,00,000 and 12,34,567."""
    s = f"{abs(x):.{decimals}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail, groups = whole[:-3], whole[-3:], []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        whole = ",".join(([head] if head else []) + groups) + "," + tail
    return (MINUS if x < 0 else "") + "₹" + whole + (f".{frac}" if frac else "")


def loss(x: float) -> str:
    """VaR/CVaR as a rupee loss; a negative value means even the bad tail is a gain."""
    return inr(x) if x > 0 else "no loss"


def lakh(x: float) -> str:
    return f"₹{x / 1e7:.2f} Cr" if abs(x) >= 1e7 else f"₹{x / 1e5:.1f} L"


def pct(x: float, d: int = 1, sign: bool = False) -> str:
    s = f"{x:+.{d}%}" if sign else f"{x:.{d}%}"
    return s.replace("-", MINUS)


def chg(x: float, d: int = 1) -> str:
    """A change in green or red, with an arrow."""
    cls, arrow = ("up", "▲") if x >= 0 else ("down", "▼")
    return f'<span class="{cls}">{arrow}{pct(abs(x), d)}</span>'


def bar(items: list[str]) -> str:
    """The amber command bar across the top."""
    return '<div class="term-bar">' + "".join(f"<span>{i}</span>" for i in items) + "</div>"


def tape(rows: list[tuple[str, float, float, float]]) -> str:
    """Ticker tape: (ticker, last price, 1-day change, 1-year change)."""
    cells = [f'<span><span class="tk">{esc(t)}</span> <span class="px">{px:,.2f}</span> {chg(d1, 2)} '
             f'<span class="mut">1Y</span> {chg(y1)}</span>' for t, px, d1, y1 in rows]
    return '<div class="term-tape">' + "".join(cells) + "</div>"


def head(title: str, sub: str = "") -> str:
    return f'<div class="term-head">{esc(title)}' + (f'<span class="sub">{esc(sub)}</span>' if sub else "") + "</div>"


def kpis(items: list[tuple[str, str, str]], big: int | None = None) -> str:
    """Key figures: (label, value, small note). `big` = index of the headline figure."""
    out = []
    for i, (k, v, s) in enumerate(items):
        out.append(f'<div class="term-kpi"><div class="k">{esc(k)}</div><div class="v{" big" if i == big else ""}">{v}</div>'
                   + (f'<div class="s">{s}</div>' if s else "") + "</div>")
    return '<div class="term-kpis">' + "".join(out) + "</div>"


def highlight(title: str, body: str) -> str:
    return f'<div class="term-hl"><div class="title">{esc(title)}</div>{body}</div>'


def table(header: list[str], rows: list[list[str]], hl: set[int] = frozenset(), total: set[int] = frozenset(),
          text: bool = False) -> str:
    """An HTML table; cells are inserted as given, so escape any untrusted text first. text=True left-aligns."""
    th = "".join(f"<th>{esc(h)}</th>" for h in header)
    body = "".join(f'<tr class="{"hl" if i in hl else "tot" if i in total else ""}">' + "".join(f"<td>{c}</td>" for c in r)
                   + "</tr>" for i, r in enumerate(rows))
    return f'<table class="term{" txt" if text else ""}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


def note(text: str) -> str:
    return f'<div class="term-note">{esc(text)}</div>'


def warn(text: str) -> str:
    return f'<div class="term-warn">{esc(text)}</div>'


def style(chart: alt.Chart, height: int = 300) -> alt.Chart:
    """Dark terminal styling for an Altair chart (render with theme=None)."""
    font = "Source Code Pro, monospace"
    return (chart.properties(height=height, background=BG)
            .configure_view(stroke=BORDER, fill=BG)
            .configure_axis(labelColor=MUTED, titleColor=AMBER, gridColor=GRID, domainColor=BORDER, tickColor=BORDER,
                            labelFont=font, titleFont=font, labelFontSize=11, titleFontSize=11, titleFontWeight="normal")
            .configure_legend(labelColor=TEXT, titleColor=AMBER, labelFont=font, titleFont=font, orient="top",
                              labelFontSize=11, titleFontSize=11, labelLimit=0)
            .configure_title(color=AMBER, font=font, anchor="start", fontSize=12, fontWeight="bold")
            .configure_text(font=font))
