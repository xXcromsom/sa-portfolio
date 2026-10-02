"""Phase 1 analysis: per-security risk/return, correlation, CAPM beta and the SML."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # render to file; no display needed
import matplotlib.pyplot as plt
import pandas as pd

from src import quant_utils as qu

# Chart tokens (dataviz reference palette, light mode). The first three
# categorical slots are the only ones validated for scatter (all-pairs) use.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"


def metrics_table(returns: pd.DataFrame, market_col: str, rf: float, erp: float,
                  periods: int = 252) -> pd.DataFrame:
    """One row per security (benchmark included) with every Phase 1 metric."""
    market = returns[market_col]
    table = pd.DataFrame({
        "cagr": qu.annualized_return(returns, periods),
        "mean_return": qu.annualized_mean(returns, periods),
        "volatility": qu.annualized_volatility(returns, periods),
        "sharpe": qu.sharpe_ratio(returns, rf, periods),
        "sortino": qu.sortino_ratio(returns, rf, periods),
        "max_drawdown": qu.max_drawdown(returns),
        "beta": qu.beta(returns, market),
        "treynor": qu.treynor_ratio(returns, market, rf, periods),
        "jensen_alpha": qu.jensen_alpha(returns, market, rf, periods),
    })
    # Forward-looking discount rate for valuation, from today's rf and ERP.
    table["capm_required_return"] = qu.capm_required_return(table["beta"], rf, erp)
    return table


def correlation_check(returns: pd.DataFrame, stocks: list[str], years: int,
                      threshold: float = 0.5, periods: int = 252) -> dict:
    """Selection criterion: pairwise correlation of daily returns over the last `years`."""
    recent = returns[stocks].iloc[-years * periods:]
    corr = recent.corr()
    # Plain floats (not numpy scalars) so the result serialises to JSON.
    pairs = {f"{a} / {b}": round(float(corr.at[a, b]), 3)
             for i, a in enumerate(stocks) for b in stocks[i + 1:]}
    return {
        "window_start": recent.index[0].date().isoformat(),
        "window_end": recent.index[-1].date().isoformat(),
        "pairs": pairs,
        "max_pair": max(pairs, key=pairs.get),
        "max_correlation": max(pairs.values()),
        "threshold": threshold,
        "passes": max(pairs.values()) <= threshold,
    }


def sml_figure(table: pd.DataFrame, stocks: list[str], benchmark: str,
               labels: dict[str, str], rf: float, periods: int = 252) -> plt.Figure:
    """Ex-post Security Market Line: realised mean return against beta.

    The line runs from the risk-free rate at beta 0 through the benchmark at
    beta 1. The risk-free intercept is the per-day rate times `periods` (the same
    arithmetic scaling the returns use), so each stock's vertical distance from
    the line equals its Jensen's alpha exactly.
    """
    rf_line = qu.periodic_rf(rf, periods) * periods
    mkt = table.loc[benchmark, "mean_return"]
    betas = table.loc[stocks + [benchmark], "beta"]
    x_max = max(1.4, betas.max() + 0.2)

    fig, ax = plt.subplots(figsize=(7.5, 4.8), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    ax.plot([0, x_max], [rf_line, rf_line + x_max * (mkt - rf_line)],
            color=INK_2, linewidth=2, zorder=1, label="SML (CAPM-implied return)")

    ax.scatter([1.0], [mkt], s=70, color=MUTED, edgecolor=SURFACE, linewidth=2,
               zorder=3, label=labels[benchmark])
    ax.annotate(labels[benchmark], (1.0, mkt), xytext=(8, -14),
                textcoords="offset points", color=INK_2, fontsize=9)

    for color, ticker in zip(SERIES, stocks):
        b, r = table.at[ticker, "beta"], table.at[ticker, "mean_return"]
        alpha = table.at[ticker, "jensen_alpha"]
        on_line = rf_line + b * (mkt - rf_line)
        ax.plot([b, b], [on_line, r], color=color, linewidth=1.2, linestyle=":", zorder=2)
        ax.scatter([b], [r], s=90, color=color, edgecolor=SURFACE, linewidth=2,
                   zorder=4, label=labels[ticker])
        # Label on the left when another stock sits just to the right, so the
        # text doesn't run into that stock's point or alpha line.
        crowded = any(0 < table.at[t, "beta"] - b < 0.4 for t in stocks if t != ticker)
        ax.annotate(f"{labels[ticker]}\nα = {alpha:+.1%}", (b, r),
                    xytext=(-8, 4) if crowded else (8, 4), ha="right" if crowded else "left",
                    textcoords="offset points", color=INK, fontsize=9)

    ax.set_xlim(0, x_max)
    ax.set_xlabel("Beta vs Nifty 50", color=INK_2)
    ax.set_ylabel("Annualised mean return", color=INK_2)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_title("Security Market Line (ex-post): points above the line beat CAPM",
                 loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="upper left")
    fig.text(0.01, 0.01, "Benchmark is the Nifty 50 price index (excludes dividends); "
             "alphas are overstated by roughly its dividend yield, ~1-1.5% a year.",
             color=MUTED, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return fig
