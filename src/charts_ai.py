"""Phase 3 charts: technical-analysis test, risk heatmaps, sentiment, earnings surprises.

Same visual system as src/charts.py. Diverging scales (correlation, returns) run
red -> grey -> blue around zero; magnitude scales use one blue ramp.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from src.charts import (AXIS, BLUE_RAMP, INK, INK_2, MUTED, SERIES, SURFACE, _figure, _footnote, _style, plt)

DIVERGING = LinearSegmentedColormap.from_list(
    "div", ["#a32626", "#e34948", "#f4a7a6", "#f0efec", "#86b6ef", "#2a78d6", "#184f95"])
SEQUENTIAL = LinearSegmentedColormap.from_list(
    "seq", ["#f0f5fc", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"])
RULE_STYLES = {"Buy and hold": dict(color=INK, linewidth=2),
               "Trend (50/200 DMA)": dict(color=BLUE_RAMP["mid"], linewidth=1.8),
               "RSI mean reversion": dict(color=MUTED, linewidth=1.6, linestyle="--")}


def ta_figure(curves: dict[str, pd.DataFrame], labels: dict[str, str]) -> plt.Figure:
    """Growth of Rs 1 under buy-and-hold vs the two trading rules, one panel per security (log scale)."""
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.4), dpi=200, sharex=True)
    fig.patch.set_facecolor(SURFACE)
    for ax, (t, df) in zip(axes.flat, curves.items()):
        for rule, style in RULE_STYLES.items():
            ax.plot(df.index, df[rule], label=rule, **style)
            ax.annotate(f"₹{df[rule].iloc[-1]:.1f}", (df.index[-1], df[rule].iloc[-1]), xytext=(4, 0),
                        textcoords="offset points", color=INK_2, fontsize=7, va="center")
        ax.set_yscale("log")
        _style(ax, labels[t], "", "Growth of ₹1", pct_y=False)
        ax.yaxis.set_major_formatter(lambda v, _: f"₹{v:g}")
        ax.yaxis.set_minor_formatter(lambda v, _: "")
    axes[0, 0].legend(frameon=False, fontsize=7, labelcolor=INK_2, loc="upper left")
    fig.suptitle("Is technical analysis possible? Trading rules vs buy-and-hold, after 0.25% round-trip costs",
                 x=0.01, ha="left", color=INK, fontsize=11)
    _footnote(fig, "Signals use the previous close; T-bills earn the risk-free rate when out of the market. "
                   "Rules start once the 200-day average exists (Oct 2016).")
    return fig


def _heat(ax, df: pd.DataFrame, cmap, vmin, vmax, fmt="{:.2f}", strong_above=0.6):
    ax.imshow(df.to_numpy(dtype=float), cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(df.shape[1]), df.columns, fontsize=8, color=INK_2)
    ax.set_yticks(range(df.shape[0]), df.index, fontsize=8, color=INK_2)
    span = max(abs(vmin), abs(vmax))
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            v = df.iat[i, j]
            if pd.notna(v):
                ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=8,
                        color=SURFACE if abs(v) / span > strong_above else INK)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(length=0)


def corr_heatmap_figure(full: pd.DataFrame, recent: pd.DataFrame, recent_label: str) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    for ax, (title, df) in zip(axes, (("2016-2026", full), (recent_label, recent))):
        _heat(ax, df, DIVERGING, -1, 1)
        ax.set_title(title, loc="left", color=INK, fontsize=10)
    fig.suptitle("Correlation of daily returns: low between the three stocks, higher with the index",
                 x=0.01, ha="left", color=INK, fontsize=11)
    _footnote(fig, "Blue = positive, red = negative, grey = zero. Nifty 50 includes the estimated dividend yield.")
    return fig


def rolling_corr_figure(roll: pd.DataFrame, window: int) -> plt.Figure:
    fig, ax = _figure((9, 4.2))
    styles = [dict(color=INK, linewidth=1.6), dict(color=BLUE_RAMP["mid"], linewidth=1.6),
              dict(color=MUTED, linewidth=1.6, linestyle="--")]
    for style, col in zip(styles, roll.columns):
        ax.plot(roll.index, roll[col], label=col, **style)
    ax.axhline(0, color=AXIS, linewidth=1)
    _style(ax, f"Correlations move: {window}-day rolling correlation between pairs", "", "Correlation", pct_y=False)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="upper left")
    _footnote(fig, "Diversification is weakest in crashes (March 2020), when correlations jump together.")
    return fig


def risk_contrib_figure(contrib: pd.DataFrame) -> plt.Figure:
    """Share of portfolio variance from each stock over time (rows = stocks)."""
    fig, ax = _figure((10, 3.2))
    data = contrib.T
    im = ax.imshow(data.to_numpy(dtype=float), cmap=SEQUENTIAL, vmin=0, vmax=1, aspect="auto")
    ax.set_yticks(range(data.shape[0]), data.index, fontsize=8, color=INK_2)
    step = max(1, data.shape[1] // 10)
    ax.set_xticks(range(0, data.shape[1], step), [c.strftime("%b %Y") for c in data.columns[::step]],
                  fontsize=7, color=INK_2)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    cb.ax.tick_params(labelsize=7, colors=MUTED)
    cb.outline.set_visible(False)
    ax.set_title("Where the portfolio's risk comes from: share of variance by stock (rolling 1-year)",
                 loc="left", color=INK, fontsize=11)
    _footnote(fig, "Recommended weights held fixed; risk share = w_i x (Σw)_i / (w'Σw). Darker = larger share.")
    return fig


def stress_figure(table: pd.DataFrame) -> plt.Figure:
    fig, ax = _figure((9, 0.6 * len(table) + 1.6))
    lim = float(np.nanmax(np.abs(table.to_numpy(dtype=float))))
    _heat(ax, table, DIVERGING, -lim, lim, fmt="{:+.1%}", strong_above=0.55)
    ax.set_title("Stress test: total return in past shocks", loc="left", color=INK, fontsize=11)
    _footnote(fig, "Portfolio P = recommended weights, rebalanced daily. Red = loss.")
    return fig


def sentiment_figure(monthly: pd.DataFrame, calls: pd.DataFrame, stocks: list[str], labels: dict[str, str]) -> plt.Figure:
    from matplotlib.lines import Line2D
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax = axes[0]
    for color, t in zip(SERIES, stocks):
        m = monthly[monthly["ticker"] == t]
        ax.plot(pd.PeriodIndex(m["month"], freq="M").to_timestamp(), m["tone"], color=color, linewidth=1.8,
                marker="o", markersize=3)
    ax.axhline(0, color=AXIS, linewidth=1)
    _style(ax, "News headlines: average FinBERT tone by month", "", "Tone (P(pos) − P(neg))", pct_y=False)
    ax = axes[1]
    quarters = sorted(calls.loc[calls["management_tone"].notna(), "quarter"].unique())  # FY25Q3 < FY25Q4 < ...
    pos = {q: i for i, q in enumerate(quarters)}
    for color, t in zip(SERIES, stocks):
        c = calls[(calls["ticker"] == t) & calls["management_tone"].notna()].sort_values("quarter")
        x = c["quarter"].map(pos)
        ax.plot(x, c["management_tone"], color=color, linewidth=1.8, marker="o", markersize=5)
        ax.plot(x, c["analyst_tone"], color=color, linewidth=1.2, linestyle=":", marker="s", markersize=3)
    ax.set_xticks(range(len(quarters)), quarters)
    ax.axhline(0, color=AXIS, linewidth=1)
    _style(ax, "Earnings calls: management vs analyst tone", "", "Tone", pct_y=False)
    ax.tick_params(axis="x", labelsize=8)
    handles = [Line2D([], [], color=c, linewidth=2, label=labels[t]) for c, t in zip(SERIES, stocks)]
    handles += [Line2D([], [], color=INK_2, linewidth=1.8, marker="o", label="Management (right)"),
                Line2D([], [], color=INK_2, linewidth=1.2, linestyle=":", marker="s", label="Analysts (right)")]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=8, labelcolor=INK_2,
               bbox_to_anchor=(0.5, 0.04))
    fig.text(0.01, 0.01, "FinBERT (ProsusAI/finbert) sentence scores. Analysts' questions are usually less upbeat "
                         "than management's answers (the tone gap). HUL FY25Q4 skipped: scanned PDF.",
             color=MUTED, fontsize=7)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    return fig


def event_figure(events: pd.DataFrame, stocks: list[str], labels: dict[str, str]) -> plt.Figure:
    fig, ax = _figure((7.5, 4.6))
    for color, t in zip(SERIES, stocks):
        e = events[events["ticker"] == t]
        ax.scatter(e["surprise_pct"] / 100, e["car"], s=45, color=color, edgecolor=SURFACE, linewidth=1.5,
                   label=labels[t], zorder=3)
    if len(events) > 2:
        x, y = events["surprise_pct"] / 100, events["car"]
        b, a = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs, a + b * xs, color=INK_2, linewidth=1.5, label=f"Fit: slope {b:.2f}")
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.axvline(0, color=AXIS, linewidth=1)
    _style(ax, "Earnings surprise vs 3-day abnormal return", "EPS surprise vs consensus",
           "Abnormal return, day −1 to +1", pct_x=True)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="upper left")
    _footnote(fig, "Market model vs Nifty 50 TR, estimated over the prior 250 days. Surprises from Yahoo Finance.")
    return fig
