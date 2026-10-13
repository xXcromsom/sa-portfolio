"""Build data/latest/ from scratch.

Phase 1: prices -> per-security metrics, correlation, SML, valuation.
Phase 2: frontier, CAL/CML, risk profiles, out-of-sample test, Monte Carlo, SIP.

Run from the project root:
    python -m pipeline.run_all            # use cached prices if present
    python -m pipeline.run_all --refresh  # re-download prices first
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from src import charts
from src import monte_carlo as mc
from src import portfolio as pf
from src import quant_utils as qu
from src import sip
from src.config import load_config, project_path
from src.data_ingest import load_prices
from src.metrics import add_dividend_yield, correlation_check, metrics_table
from src.valuation import read_summary, valuation_record


def _frame_to_dict(df: pd.DataFrame) -> dict:
    return json.loads(df.round(6).to_json(orient="index"))


def _dump(obj, path) -> None:
    path.write_text(json.dumps(obj, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                    encoding="utf-8")


class Context:
    """Everything later steps need, loaded once."""

    def __init__(self, refresh: bool):
        self.cfg = cfg = load_config()
        self.stocks = list(cfg["universe"]["stocks"])
        self.bench = cfg["universe"]["benchmark"]
        m = cfg["market"]
        self.periods, self.rf, self.erp = m["trading_days"], m["risk_free_rate"], m["equity_risk_premium"]
        self.labels = {t: v["name"] for t, v in cfg["universe"]["stocks"].items()}
        self.labels[self.bench] = cfg["universe"]["benchmark_name"]
        self.out = project_path(cfg["data"]["latest_dir"])
        (self.out / "figures").mkdir(parents=True, exist_ok=True)
        self.prices, self.meta = load_prices(cfg, refresh=refresh)
        returns = qu.to_returns(self.prices)
        # Estimated total return for the benchmark (see config).
        returns[self.bench] = add_dividend_yield(returns[self.bench],
                                                 cfg["universe"]["benchmark_dividend_yield"], self.periods)
        self.returns = returns

    def fig(self, figure, name: str) -> None:
        figure.savefig(self.out / "figures" / name)
        charts.plt.close(figure)


# ---------------------------------------------------------------- Phase 1
def run_phase1(ctx: Context) -> None:
    cfg, r = ctx.cfg, ctx.returns
    table = metrics_table(r, ctx.bench, ctx.rf, ctx.erp, ctx.periods)
    ctx.table = table  # CAPM required returns feed Phase 2
    corr_check = correlation_check(r, ctx.stocks, cfg["data"]["correlation_window_years"], periods=ctx.periods)
    m = cfg["market"]
    metrics = {
        "as_of": ctx.meta["last_date"],
        "assumptions": {
            "periods_per_year": ctx.periods,
            "risk_free_rate": ctx.rf, "risk_free_source": m["risk_free_source"],
            "risk_free_as_of": str(m["risk_free_as_of"]),
            "equity_risk_premium": ctx.erp, "erp_source": m["erp_source"], "erp_as_of": str(m["erp_as_of"]),
            "benchmark": f"{ctx.labels[ctx.bench]}: Nifty 50 price index + "
                         f"{cfg['universe']['benchmark_dividend_yield']:.2%}/yr estimated dividend yield",
            "ratio_convention": "arithmetic mean excess return x periods; cagr is geometric",
            "tail_measures": "historical, daily, 95%; VaR and ES are positive losses",
        },
        "data": ctx.meta,
        "names": ctx.labels,
        "securities": _frame_to_dict(table),
        "correlation_full_sample": _frame_to_dict(r[ctx.stocks].corr()),
        "correlation_check": corr_check,
        "covariance_annualized": _frame_to_dict(r[ctx.stocks].cov() * ctx.periods),
    }
    _dump(metrics, ctx.out / "metrics.json")
    table.rename(index=ctx.labels).to_csv(ctx.out / "metrics_table.csv", float_format="%.6f")
    ctx.fig(charts.sml_figure(table, ctx.stocks, ctx.bench, ctx.labels, ctx.rf, ctx.periods), "sml.png")
    _print_phase1(table.rename(index=ctx.labels), ctx.meta, corr_check, ctx.labels)

    workbook = project_path("workbook/valuation.xlsx")
    if workbook.exists():
        record = valuation_record(read_summary(workbook), ctx.prices.iloc[-1], ctx.meta["last_date"], ctx.stocks)
        _dump(record, ctx.out / "valuation.json")
        _print_valuation(record)


# ---------------------------------------------------------------- Phase 2
def run_phase2(ctx: Context) -> None:
    cfg, r, rf, erp, periods = ctx.cfg, ctx.returns, ctx.rf, ctx.erp, ctx.periods
    pc, mcc, sc = cfg["portfolio"], cfg["monte_carlo"], cfg["sip"]
    bounds, n_stocks = tuple(pc["weight_bounds"]), len(ctx.stocks)
    stock_r = r[ctx.stocks]
    mu_hist, cov = pf.annual_inputs(stock_r, periods)
    capm = ctx.table.loc[ctx.stocks, "capm_required_return"]
    vol = pd.Series(np.sqrt(np.diag(cov)), index=ctx.stocks)
    mkt_vol = float(r[ctx.bench].std() * np.sqrt(periods))

    def describe(w, mu) -> dict:
        er, sd = pf.portfolio_return(w, mu), pf.portfolio_vol(w, cov)
        return {"weights": dict(zip(ctx.stocks, map(float, w))), "expected_return": er,
                "volatility": sd, "sharpe": (er - rf) / sd}

    # Two views of expected returns, same covariance (see config).
    views = {}
    for key, mu, mkt_er in (("history", mu_hist, float(r[ctx.bench].mean() * periods)),
                            ("forward", capm, rf + erp)):
        market = {"expected_return": mkt_er, "volatility": mkt_vol, "sharpe": (mkt_er - rf) / mkt_vol}
        views[key] = {"expected_returns": mu.to_dict(),
                      "tangency": describe(pf.max_sharpe_weights(mu, cov, rf, bounds), mu),
                      "min_variance": describe(pf.min_variance_weights(cov, bounds), mu),
                      "equal_weight": describe(np.full(n_stocks, 1 / n_stocks), mu),
                      "market": market,
                      "frontier": pf.efficient_frontier(mu, cov, bounds, pc["frontier_points"])}
    P = views["forward"]["tangency"]  # the recommended risky portfolio
    profiles = {name: pf.complete_portfolio(P["expected_return"], P["volatility"], rf, a, pc["allow_borrowing"])
                for name, a in pc["profiles"].items()}
    # Certainty-equivalent return of holding each asset alone, by risk aversion (forward view).
    assets = {**{ctx.labels[t]: (capm[t], vol[t]) for t in ctx.stocks},
              "Optimal risky P": (P["expected_return"], P["volatility"]),
              "Nifty 50": (rf + erp, mkt_vol)}
    ce_table = {name: {asset: pf.utility(er, sd, a) for asset, (er, sd) in assets.items()}
                for name, a in pc["profiles"].items()}

    # Out-of-sample: estimate each rule on 2016-2022, test it on 2023 onward.
    split = pd.Timestamp(pc["in_sample_end"])
    ins, oos = r[r.index <= split], r[r.index > split]
    mu_in, cov_in = pf.annual_inputs(ins[ctx.stocks], periods)
    capm_in = rf + qu.beta(ins[ctx.stocks], ins[ctx.bench]) * erp
    rules = {"History-based P": pf.max_sharpe_weights(mu_in, cov_in, rf, bounds),
             "Forward-looking P": pf.max_sharpe_weights(capm_in, cov_in, rf, bounds),
             "Equal weight": np.full(n_stocks, 1 / n_stocks)}
    out_of_sample = {"in_sample": f"{ins.index[0].date()} to {ins.index[-1].date()}",
                     "test": f"{oos.index[0].date()} to {oos.index[-1].date()}"}
    for name, w in rules.items():
        weights = dict(zip(ctx.stocks, map(float, w)))
        out_of_sample[name] = {"weights": weights, **pf.backtest(oos, weights, oos[ctx.bench], rf, periods)}

    _dump({"as_of": ctx.meta["last_date"], "weight_bounds": bounds, "risk_free_rate": rf,
           "covariance": _frame_to_dict(cov), "volatility": vol.to_dict(),
           "views": {k: {**v, "frontier": v["frontier"].round(6).to_dict(orient="records")}
                     for k, v in views.items()},
           "recommended": "forward", "profiles": profiles, "certainty_equivalents": ce_table,
           "out_of_sample": out_of_sample}, ctx.out / "portfolio.json")
    panels = [{"title": "History: 2016-2026 mean returns", "mu": mu_hist, **views["history"]},
              {"title": "Forward-looking: CAPM expected returns (recommended)", "mu": capm, **views["forward"]}]
    ctx.fig(charts.frontier_figure(panels, vol, ctx.stocks, ctx.labels, rf, profiles), "frontier.png")
    ctx.fig(charts.indifference_figure(P, rf, profiles), "indifference.png")

    # One-year Monte Carlo. Same draws for every profile, so differences come from y alone.
    rng = np.random.default_rng(mcc["seed"])
    n, horizon, v0 = mcc["n_sims"], mcc["horizon_days"], mcc["initial_value"]
    target = (capm if mcc["expected_returns"] == "capm" else mu_hist).to_numpy() / periods
    hist = stock_r.to_numpy()
    ewma = mc.ewma_cov(stock_r, mcc["ewma_lambda"]).to_numpy()
    draws = {
        "Parametric": mc.simulate_parametric(target, stock_r.cov().to_numpy(), n, horizon, rng),
        "Bootstrap": mc.simulate_bootstrap(mc.shift_means(hist, target), n, horizon,
                                           mcc["bootstrap_block_days"], rng),
        "Parametric, current volatility (EWMA)": mc.simulate_parametric(target, ewma, n, horizon, rng),
    }
    w_p = np.array([P["weights"][t] for t in ctx.stocks])
    rf_d = qu.periodic_rf(rf, periods)
    mc_out, fans, terminals, var95 = {}, {}, {}, {}
    focus = "Balanced"
    for mode, x in draws.items():
        mc_out[mode] = {}
        for name, p in profiles.items():
            wealth = mc.wealth_paths(x, w_p, p["y"], rf_d, mcc["rebalance"])
            mc_out[mode][name] = mc.summarize(wealth, v0)
            if name == focus and mode in ("Parametric", "Bootstrap"):
                fans[mode] = mc.fan(wealth, v0)
                terminals[mode] = wealth[:, -1] * v0
                var95[mode] = mc_out[mode][name]["var_95"]
    del draws
    _dump({"as_of": ctx.meta["last_date"],
           "settings": {**mcc, "risky_portfolio": P["weights"],
                        "annual_vol_ewma_vs_sample": {t: [float(np.sqrt(ewma[i, i] * periods)), float(vol[t])]
                                                      for i, t in enumerate(ctx.stocks)}},
           "results": mc_out}, ctx.out / "mc.json")
    ctx.fig(charts.mc_fan_figure(fans, v0, focus), "mc_fan.png")
    ctx.fig(charts.mc_hist_figure(terminals, var95, v0, focus), "mc_hist.png")

    # SIP over the years: equity = Nifty index core + the three stocks as satellite.
    months, core = sc["years"] * 12, sc["core_index_share"]
    amounts = sip.contributions(sc["monthly_amount"], sc["annual_step_up"], months)
    rf_m = qu.periodic_rf(rf, 12)
    four = ctx.stocks + [ctx.bench]
    w_sleeve = np.append((1 - core) * w_p, core)
    cov_m = r[four].cov().to_numpy() * periods / 12
    monthly_hist = ctx.prices[four].resample("ME").last().pct_change().dropna()
    monthly_hist[ctx.bench] += qu.periodic_rf(cfg["universe"]["benchmark_dividend_yield"], 12)

    def sleeve_draws(mu_annual: np.ndarray) -> dict:
        mu_m = mu_annual / 12
        boot_hist = mc.shift_means(monthly_hist.to_numpy(), mu_m) @ w_sleeve
        return {"Parametric": mc.simulate_parametric(mu_m, cov_m, n, months, rng) @ w_sleeve,
                "Bootstrap": sip.monthly_bootstrap(boot_hist, n, months, sc["bootstrap_block_months"], rng)}

    forward = sleeve_draws(np.append(capm.to_numpy(), rf + erp))
    sip_out, sip_fans = {}, {}
    for name, p in profiles.items():
        glide = sip.glide_path(p["y"], sc["glide_path_end_equity"], months)
        sip_out[name] = {"equity_start": p["y"], "equity_end": float(glide[-1])}
        for mode, risky in forward.items():
            corpus = sip.simulate_sip(risky, glide, rf_m, amounts, sc["rebalance_every_months"])
            sip_out[name][mode] = sip.summarize_sip(corpus, amounts, sc["goals"], sc["inflation"], sc["years"])
            if mode == "Parametric":
                sip_fans[name] = sip.sip_fan(corpus, amounts)
    # Sensitivity: what if the last decade's returns simply repeat?
    hist_mu = np.append(mu_hist.to_numpy(), float(r[ctx.bench].mean() * periods))
    glide = sip.glide_path(profiles[focus]["y"], sc["glide_path_end_equity"], months)
    corpus = sip.simulate_sip(sleeve_draws(hist_mu)["Parametric"], glide, rf_m, amounts,
                              sc["rebalance_every_months"])
    sensitivity = {f"{focus}, historical means": sip.summarize_sip(corpus, amounts, sc["goals"],
                                                                   sc["inflation"], sc["years"])}
    _dump({"as_of": ctx.meta["last_date"],
           "settings": {**sc, "equity_sleeve": dict(zip(four, map(float, w_sleeve)))},
           "results": sip_out, "sensitivity": sensitivity}, ctx.out / "sip.json")
    ctx.fig(charts.sip_figure(sip_fans, sc["goals"][len(sc["goals"]) // 2], sc["years"]), "sip.png")

    _print_phase2(ctx, views, profiles, out_of_sample, mc_out, sip_out, sensitivity)


# ---------------------------------------------------------------- printing
def _print_phase1(table: pd.DataFrame, meta: dict, corr_check: dict, labels: dict) -> None:
    pct = ["cagr", "mean_return", "volatility", "max_drawdown", "var_95_daily", "es_95_daily",
           "treynor", "jensen_alpha", "capm_required_return"]
    shown = table.copy()
    for col in pct:
        shown[col] = shown[col].map("{:.1%}".format)
    for col in ["sharpe", "sortino", "beta", "skewness", "excess_kurtosis"]:
        shown[col] = shown[col].map("{:.2f}".format)
    print(f"\nPrices {meta['first_date']} to {meta['last_date']} "
          f"({meta['observations']} days; {len(meta['dropped_incomplete_dates'])} incomplete dates dropped)\n")
    print(shown.T.to_string())
    print(f"\nCorrelation check ({corr_check['window_start']} to {corr_check['window_end']}):")
    for pair, value in corr_check["pairs"].items():
        a, b = pair.split(" / ")
        print(f"  {labels[a]} / {labels[b]}: {value:.2f}")
    verdict = "PASS" if corr_check["passes"] else "FAIL"
    print(f"  max {corr_check['max_correlation']:.2f} vs threshold {corr_check['threshold']:.2f} -> {verdict}")


def _print_valuation(record: dict) -> None:
    print(f"\nValuation vs latest close ({record['latest_price_date']}):")
    for v in record["securities"].values():
        up = v["upside_vs_latest"]
        print(f"  {v['name']:<20} price {v['latest_price']:>8,.0f} | model {v['intrinsic_value']:>8,.0f} "
              f"({up['intrinsic']:+.0%}) | comps {v['comps_value']:>8,.0f} ({up['comps']:+.0%}) | "
              f"blended {up['blended']:+.0%} | market-implied g {v['market_implied_growth']:.1%}")


def _print_phase2(ctx, views, profiles, oos, mc_out, sip_out, sensitivity) -> None:
    lab = ctx.labels

    def w(d):
        return ", ".join(f"{lab[t]} {x:.0%}" for t, x in d["weights"].items())

    for key, v in views.items():
        print(f"\nPortfolios, {key} view (expected return / volatility / Sharpe):")
        for name in ("tangency", "min_variance", "equal_weight"):
            d = v[name]
            print(f"  {name:<13} {d['expected_return']:.1%} / {d['volatility']:.1%} / {d['sharpe']:.2f}  [{w(d)}]")
        m = v["market"]
        print(f"  {'Nifty (CML)':<13} {m['expected_return']:.1%} / {m['volatility']:.1%} / {m['sharpe']:.2f}")
    print("\nComplete portfolios on the forward-looking P (y = share in P, rest in T-bills):")
    for name, p in profiles.items():
        print(f"  {name:<12} A={p['risk_aversion']:g}: y*={p['y_star']:.0%} -> y={p['y']:.0%}, "
              f"E(r) {p['expected_return']:.1%}, vol {p['volatility']:.1%}, CE {p['certainty_equivalent']:.1%}")
    print(f"\nOut-of-sample {oos['test']} (rules estimated on {oos['in_sample']}):")
    for name in ("History-based P", "Forward-looking P", "Equal weight"):
        d, ws = oos[name]["portfolio"], oos[name]["weights"]
        print(f"  {name:<18} CAGR {d['cagr']:.1%}, vol {d['volatility']:.1%}, Sharpe {d['sharpe']:.2f}, "
              f"alpha {d['jensen_alpha']:+.1%}, maxDD {d['max_drawdown']:.1%}  ["
              + ", ".join(f"{lab[k].split()[0]} {v:.0%}" for k, v in ws.items()) + "]")
    m = oos["Equal weight"]["market"]
    print(f"  {'Nifty 50 TR':<18} CAGR {m['cagr']:.1%}, vol {m['volatility']:.1%}, Sharpe {m['sharpe']:.2f}, "
          f"maxDD {m['max_drawdown']:.1%}")
    print("\nOne-year Monte Carlo, Rs 1 lakh (median / 5th pct / 95% VaR / P(loss)):")
    for mode, res in mc_out.items():
        for name, s in res.items():
            print(f"  {mode[:22]:<22} {name:<12} {s['terminal_percentiles']['p50']:>9,.0f} / "
                  f"{s['terminal_percentiles']['p5']:>9,.0f} / {s['var_95']:>8,.0f} / {s['prob_loss']:.0%}")
    print("\n15-year SIP (median corpus / 5th pct / P(goal)):")
    rows = [(f"{n} {m}", s[m]) for n, s in sip_out.items() for m in ("Parametric", "Bootstrap")]
    rows += list(sensitivity.items())
    for name, d in rows:
        print(f"  {name:<34} {d['terminal_percentiles']['p50']:>12,.0f} / {d['terminal_percentiles']['p5']:>12,.0f}"
              " / P(goal) " + ", ".join(f"{float(g) / 1e5:.0f}L {p:.0%}" for g, p in d["prob_reach_goal"].items())
              + f"  (invested {d['total_invested']:,.0f})")


def main(refresh: bool = False) -> None:
    ctx = Context(refresh)
    run_phase1(ctx)
    run_phase2(ctx)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="re-download prices")
    main(parser.parse_args().refresh)
