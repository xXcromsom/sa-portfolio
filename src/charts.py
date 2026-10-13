"""Static report charts (matplotlib). One visual system for every figure.

Tokens follow the dataviz reference palette (light mode). The three stocks keep
the first three categorical slots in every chart (colour follows the entity).
Other series use ink greys, and ordered series (risk profiles, percentile bands)
use one blue ramp.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # render to file; no display needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import quant_utils as qu

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]                 # stocks, fixed order
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE_RAMP = {"light": "#cde2fb", "mid_light": "#86b6ef", "mid": "#2a78d6", "dark": "#184f95"}
PROFILE_COLORS = ["#86b6ef", "#2a78d6", "#184f95"]          # least to most risk-averse


def _style(ax, title: str, xlabel: str, ylabel: str, pct_x=False, pct_y=True, rupee_y=False):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.set_xlabel(xlabel, color=INK_2)
    ax.set_ylabel(ylabel, color=INK_2)
    if pct_x:
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    if rupee_y:
        ax.yaxis.set_major_formatter(lambda v, _: _rupees(v))
    elif pct_y:
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")


def _rupees(v: float) -> str:
    """Indian units: lakh (1e5) and crore (1e7)."""
    if abs(v) >= 1e7:
        return f"₹{v / 1e7:.1f} Cr"
    if abs(v) >= 1e6:
        return f"₹{v / 1e5:.1f} L"
    if abs(v) >= 1e5:
        return f"₹{v / 1e5:.2f} L"  # two decimals so nearby ticks stay distinct
    return f"₹{v:,.0f}"


def _figure(size=(7.5, 4.8)):
    fig, ax = plt.subplots(figsize=size, dpi=200)
    fig.patch.set_facecolor(SURFACE)
    return fig, ax


def _footnote(fig, text: str):
    fig.text(0.01, 0.01, text, color=MUTED, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))


def sml_figure(table: pd.DataFrame, stocks: list[str], benchmark: str,
               labels: dict[str, str], rf: float, periods: int = 252) -> plt.Figure:
    """Ex-post Security Market Line: realised mean return against beta.

    The line runs from the risk-free rate at beta 0 through the benchmark at
    beta 1. The intercept is the per-day risk-free rate times `periods` (the same
    arithmetic scaling as the returns), so each stock's vertical distance from
    the line equals its Jensen's alpha exactly.
    """
    rf_line = qu.periodic_rf(rf, periods) * periods
    mkt = table.loc[benchmark, "mean_return"]
    betas = table.loc[stocks + [benchmark], "beta"]
    x_max = max(1.4, betas.max() + 0.2)
    fig, ax = _figure()
    ax.plot([0, x_max], [rf_line, rf_line + x_max * (mkt - rf_line)],
            color=INK_2, linewidth=2, zorder=1, label="SML (CAPM-implied return)")
    ax.scatter([1.0], [mkt], s=70, color=MUTED, edgecolor=SURFACE, linewidth=2, zorder=3,
               label=labels[benchmark])
    ax.annotate(labels[benchmark], (1.0, mkt), xytext=(8, -14), textcoords="offset points",
                color=INK_2, fontsize=9)
    for color, ticker in zip(SERIES, stocks):
        b, r = table.at[ticker, "beta"], table.at[ticker, "mean_return"]
        alpha = table.at[ticker, "jensen_alpha"]
        on_line = rf_line + b * (mkt - rf_line)
        ax.plot([b, b], [on_line, r], color=color, linewidth=1.2, linestyle=":", zorder=2)
        ax.scatter([b], [r], s=90, color=color, edgecolor=SURFACE, linewidth=2, zorder=4,
                   label=labels[ticker])
        # Label on the left when another stock sits just to the right.
        crowded = any(0 < table.at[t, "beta"] - b < 0.4 for t in stocks if t != ticker)
        ax.annotate(f"{labels[ticker]}\nα = {alpha:+.1%}", (b, r),
                    xytext=(-8, 4) if crowded else (8, 4), ha="right" if crowded else "left",
                    textcoords="offset points", color=INK, fontsize=9)
    ax.set_xlim(0, x_max)
    _style(ax, "Security Market Line (ex-post): points above the line beat CAPM",
           "Beta vs Nifty 50", "Annualised mean return")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="upper left")
    _footnote(fig, "Benchmark: Nifty 50 price index + 1.22%/yr estimated dividend yield. "
                   "Daily returns 2016-2026.")
    return fig


def frontier_figure(panels: list[dict], vol: pd.Series, stocks: list[str], labels: dict[str, str],
                    rf: float, profiles: dict[str, dict]) -> plt.Figure:
    """Efficient frontier, CAL through P and CML through the Nifty, one panel per return view.

    Each panel dict: title, mu (Series), frontier (DataFrame), tangency, market.
    Profiles are drawn on the last panel (the recommended view).
    """
    fig, axes = plt.subplots(1, len(panels), figsize=(11, 4.9), dpi=200, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    x_max = max(vol.max(), max(p["frontier"]["volatility"].max() for p in panels)) * 1.15
    y_lo = min(rf, min(p["mu"].min() for p in panels)) - 0.02
    y_hi = max(max(p["mu"].max(), p["tangency"]["expected_return"]) for p in panels) + 0.03
    xs = np.array([0, x_max])
    for i, (ax, panel) in enumerate(zip(axes, panels)):
        mu, front, tan, mkt = panel["mu"], panel["frontier"], panel["tangency"], panel["market"]
        ax.plot(front["volatility"], front["return"], color=INK_2, linewidth=2, zorder=2,
                label="Efficient frontier (10-60% per stock)")
        cal = (tan["expected_return"] - rf) / tan["volatility"]
        cml = (mkt["expected_return"] - rf) / mkt["volatility"]
        ax.plot(xs, rf + cal * xs, color=INK, linewidth=2, zorder=3, label=f"CAL: T-bills + P (Sharpe {cal:.2f})")
        ax.plot(xs, rf + cml * xs, color=MUTED, linewidth=2, linestyle="--", zorder=1,
                label=f"CML: T-bills + Nifty (Sharpe {cml:.2f})")
        for color, t in zip(SERIES, stocks):
            ax.scatter(vol[t], mu[t], s=80, color=color, edgecolor=SURFACE, linewidth=2, zorder=4)
            # Label on the left when another stock sits just to the right at a similar return
            # (HUL and Sun Pharma: ~5 points of volatility apart, <1 point of return).
            crowded = any(0 < vol[o] - vol[t] < 0.07 and abs(mu[o] - mu[t]) < 0.015 for o in stocks if o != t)
            ax.annotate(labels[t], (vol[t], mu[t]), xytext=(-7, -3) if crowded else (7, -3),
                        ha="right" if crowded else "left", textcoords="offset points", color=INK, fontsize=8)
        ax.scatter(mkt["volatility"], mkt["expected_return"], s=70, color=MUTED, edgecolor=SURFACE,
                   linewidth=2, zorder=4)
        ax.annotate("Nifty 50", (mkt["volatility"], mkt["expected_return"]), xytext=(-6, 8), ha="right",
                    textcoords="offset points", color=INK_2, fontsize=8)
        ax.scatter(tan["volatility"], tan["expected_return"], s=110, marker="D", color=INK,
                   edgecolor=SURFACE, linewidth=2, zorder=5)
        ax.annotate("P", (tan["volatility"], tan["expected_return"]), xytext=(-4, 9), ha="right",
                    textcoords="offset points", color=INK, fontsize=10, fontweight="bold")
        w = "\n".join(f"{labels[t]} {x:.0%}" for t, x in tan["weights"].items())
        ax.text(0.98, 0.04, f"Optimal risky portfolio P\n{w}\nSharpe {cal:.2f}", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=8, color=INK,
                bbox=dict(boxstyle="square,pad=0.4", facecolor=SURFACE, edgecolor=AXIS, linewidth=0.8))
        ax.annotate(f"T-bill {rf:.1%}", (0, rf), xytext=(4, -12), textcoords="offset points",
                    color=INK_2, fontsize=8)
        if i == len(panels) - 1:
            shown = [p for p in profiles.values() if p["y"] < 0.999]  # a capped profile sits on P itself
            ax.scatter([p["volatility"] for p in shown], [p["expected_return"] for p in shown], s=40,
                       color=SURFACE, edgecolor=INK, linewidth=1.5, zorder=5,
                       label="Complete portfolios, A = " + ", ".join(f"{p['risk_aversion']:g}" for p in shown))
        ax.set_xlim(0, x_max)
        ax.set_ylim(y_lo, y_hi)
        _style(ax, panel["title"], "Annualised volatility", "Expected return" if i == 0 else "", pct_x=True)
        ax.legend(frameon=False, fontsize=7, labelcolor=INK_2, loc="upper left")
    fig.suptitle("Efficient frontier and capital allocation: history vs forward-looking expected returns",
                 x=0.01, ha="left", color=INK, fontsize=11)
    _footnote(fig, "Same 2016-2026 covariance in both panels. Left: realised mean returns. Right: CAPM "
                   "required returns (rf + beta x ERP), the recommended view.")
    return fig


def indifference_figure(tangency: dict, rf: float, profiles: dict[str, dict]) -> plt.Figure:
    """Each profile's highest indifference curve touching the CAL (BKM Ch 6)."""
    fig, ax = _figure((7.5, 4.8))
    x_max = tangency["volatility"] * 1.4
    xs = np.linspace(0, x_max, 200)
    slope = (tangency["expected_return"] - rf) / tangency["volatility"]
    ax.plot(xs, rf + slope * xs, color=INK, linewidth=2, label="CAL (T-bills + P)", zorder=3)
    ax.scatter(tangency["volatility"], tangency["expected_return"], s=110, marker="D", color=INK,
               edgecolor=SURFACE, linewidth=2, zorder=5)
    ax.annotate("P", (tangency["volatility"], tangency["expected_return"]), xytext=(-14, 6),
                textcoords="offset points", color=INK, fontsize=10, fontweight="bold")
    for color, (name, p) in zip(PROFILE_COLORS, profiles.items()):
        curve = p["certainty_equivalent"] + 0.5 * p["risk_aversion"] * xs ** 2
        ax.plot(xs, curve, color=color, linewidth=2, zorder=2,
                label=f"{name}, A={p['risk_aversion']:g}: CE {p['certainty_equivalent']:.1%}")
        ax.scatter(p["volatility"], p["expected_return"], s=60, color=color, edgecolor=SURFACE,
                   linewidth=2, zorder=4)
        ax.annotate(f"y = {p['y']:.0%}", (p["volatility"], p["expected_return"]), xytext=(8, -12),
                    textcoords="offset points", color=INK, fontsize=8)
    ax.set_xlim(0, x_max)
    ax.set_ylim(rf - 0.02, tangency["expected_return"] + 0.06)
    _style(ax, "Indifference curves: where each investor stops adding risk",
           "Annualised volatility", "Annualised expected return", pct_x=True)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="upper left")
    _footnote(fig, "Each curve's intercept is the certainty-equivalent return (CE). "
                   "Steeper curves = more risk-averse.")
    return fig


def _bands(ax, fan: pd.DataFrame, x: np.ndarray):
    ax.fill_between(x, fan["p5"], fan["p95"], color=BLUE_RAMP["light"], linewidth=0, label="5th-95th pct")
    ax.fill_between(x, fan["p25"], fan["p75"], color=BLUE_RAMP["mid_light"], linewidth=0,
                    label="25th-75th pct")
    ax.plot(x, fan["p50"], color=BLUE_RAMP["dark"], linewidth=2, label="Median")


def mc_fan_figure(fans: dict[str, pd.DataFrame], initial_value: float, profile: str) -> plt.Figure:
    """Side-by-side fan charts for the parametric and bootstrap simulations (same y-axis)."""
    fig, axes = plt.subplots(1, len(fans), figsize=(9, 4.4), dpi=200, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    for ax, (mode, f) in zip(axes, fans.items()):
        x = np.arange(len(f))
        _bands(ax, f, x)
        ax.axhline(initial_value, color=MUTED, linewidth=1, linestyle=":")
        for p in ("p5", "p95"):
            ax.annotate(_rupees(f[p].iloc[-1]), (x[-1], f[p].iloc[-1]), xytext=(-4, 4 if p == "p95" else -12),
                        ha="right", textcoords="offset points", color=INK, fontsize=8)
        _style(ax, mode, "Trading days ahead", "Portfolio value" if ax is axes[0] else "", rupee_y=True)
    axes[0].legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="upper left")
    fig.suptitle(f"One-year Monte Carlo, {profile} profile, {_rupees(initial_value)} invested",
                 x=0.01, ha="left", color=INK, fontsize=11)
    _footnote(fig, "10,000 paths each, CAPM expected returns, 2016-2026 covariance. Parametric = correlated "
                   "normal draws; bootstrap = 10-day blocks of actual days, re-centred on the same means.")
    return fig


def mc_hist_figure(terminals: dict[str, np.ndarray], var95: dict[str, float], initial_value: float,
                   profile: str) -> plt.Figure:
    """Terminal-value distributions of both modes with each 95% VaR marked."""
    fig, ax = _figure((7.5, 4.4))
    styles = {"Parametric": dict(color=BLUE_RAMP["mid_light"], histtype="stepfilled", alpha=0.9),
              "Bootstrap": dict(color=INK, histtype="step", linewidth=1.5)}
    lo = min(np.percentile(v, 0.5) for v in terminals.values())
    hi = max(np.percentile(v, 99.5) for v in terminals.values())
    bins = np.linspace(lo, hi, 70)
    for mode, values in terminals.items():
        ax.hist(values, bins=bins, label=mode, **styles[mode])
        cut = initial_value - var95[mode]
        ax.axvline(cut, color=styles[mode]["color"] if mode == "Bootstrap" else BLUE_RAMP["dark"],
                   linestyle="--", linewidth=1.2)
        ax.annotate(f"{mode} 95% VaR\n{_rupees(var95[mode])}", (cut, ax.get_ylim()[1] * 0.9),
                    xytext=(-6 if mode == "Parametric" else 6, 0), textcoords="offset points",
                    ha="right" if mode == "Parametric" else "left", color=INK, fontsize=8)
    _style(ax, f"Value after one year, {profile} profile", "Portfolio value", "Number of paths",
           pct_y=False)
    ax.xaxis.set_major_formatter(lambda v, _: _rupees(v))
    ax.legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="upper right")
    _footnote(fig, f"VaR = loss not exceeded in 95% of paths, from {_rupees(initial_value)}.")
    return fig


def sip_figure(fans: dict[str, pd.DataFrame], goal: float, years: int) -> plt.Figure:
    """Corpus fan for each risk profile (same y-axis), with money invested and the goal."""
    fig, axes = plt.subplots(1, len(fans), figsize=(10, 4.4), dpi=200, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    for ax, (name, f) in zip(axes, fans.items()):
        x = np.arange(len(f)) / 12
        _bands(ax, f, x)
        ax.plot(x, f["invested"], color=INK_2, linewidth=1.5, linestyle="--", label="Money invested")
        ax.axhline(goal, color=MUTED, linewidth=1, linestyle=":")
        ax.annotate(f"Median {_rupees(f['p50'].iloc[-1])}", (x[-1], f["p50"].iloc[-1]), xytext=(-6, -16),
                    ha="right", textcoords="offset points", color=INK, fontsize=8)
        _style(ax, name, "Years", "Corpus" if ax is axes[0] else "", rupee_y=True)
    axes[0].annotate(f"Goal {_rupees(goal)}", (0, goal), xytext=(2, 4), textcoords="offset points",
                     color=MUTED, fontsize=8)
    axes[0].legend(frameon=False, fontsize=7, labelcolor=INK_2, loc="upper left")
    fig.suptitle(f"Building the portfolio over {years} years: monthly SIP with a 10% yearly step-up",
                 x=0.01, ha="left", color=INK, fontsize=11)
    _footnote(fig, "Parametric, 10,000 paths, CAPM expected returns. Equity = 50% Nifty index fund + 50% the "
                   "three stocks; equity share glides to 40%; debt earns the T-bill rate; nominal, pre-tax.")
    return fig
