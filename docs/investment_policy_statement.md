# Investment Policy Statement (BKM Ch 24 framework)

**Investor:** a TAPMI BBA student, age about 20, who starts a monthly SIP after graduation and plans to hold it for about 15 years. Figures are from the pipeline (`data/latest/`, forward-looking CAPM returns) and update with the data.

## Objectives

| | Policy |
|---|---|
| **Return** | Grow the corpus faster than inflation (RBI target 4%) by a clear margin. Target: ₹75 lakh nominal after 15 years from a ₹10,000/month SIP that rises 10% a year (₹38 lakh invested in total). |
| **Risk** | Balanced profile by default (A = 4, unless the questionnaire says otherwise). One-year 95% VaR on ₹1 lakh: about ₹5,800 (Monte Carlo, both methods). Accept that the chance of reaching ₹75 lakh is about 20% for Balanced and 38% for Aggressive. |

## Constraints

| | Policy |
|---|---|
| **Time horizon** | About 15 years, in two stages: accumulation, then a glide path from the profile's equity share down to 40% as the goal nears. |
| **Liquidity** | Keep 6 months of expenses in a liquid fund *outside* this portfolio, so a market fall never forces a sale. |
| **Tax** | Pre-tax in our models. Holding equity for more than 12 months keeps gains long-term (LTCG: 12.5% above ₹1.25 lakh a year; STCG 20%, per Budget July 2024; *check the current rates*). Rebalance with new SIP money where possible rather than selling. |
| **Legal / regulatory** | A SEBI-registered broker or mutual fund platform only, with KYC completed. No derivatives, leverage or margin (y is capped at 100%). |
| **Unique** | Three stocks are too concentrated for a lifetime portfolio: the CML (T-bills + Nifty) has a higher Sharpe ratio (0.44) than our CAL (0.36). So the equity sleeve is **core-satellite: 50% Nifty 50 index fund + 50% the three stocks**. The satellite share should shrink as more companies are researched. |

## Strategic allocation

| Sleeve | Weight | Holds |
|---|---|---|
| Equity (starts at the profile's y, glides to 40%) | Aggressive 91% · Balanced 46% · Conservative 30% to start | 50% Nifty 50 index fund; 50% HUL 26% / Infosys 28% / ICICI 46% |
| Debt | The rest | T-bills, or a liquid / gilt fund |

## Rebalancing and review

- **Rebalance** once a year, or sooner if any sleeve drifts more than 5 percentage points from target. New SIP money goes to the underweight sleeve first.
- **Review** after each set of quarterly results:
  - Re-run the valuation workbook.
  - Check the dashboard's sentiment and earnings-surprise signals.
  - If a stock's thesis (`docs/macro_industry.md`) no longer holds, replace it, not because the price fell.
- **Re-take** the risk questionnaire every year, and after any major life change.
- **Behavioural rules (BKM Ch 12):**
  - no selling in the month after a 20% fall (loss aversion and panic)
  - no buying a stock because it rose recently (recency and herding)
  - write down the reason for every trade before placing it (overconfidence check)
