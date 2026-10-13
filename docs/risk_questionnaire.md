# Risk questionnaire: estimating your own risk aversion A

The Class 8–10 deck (BKM Ch 6) gives three ways to estimate risk aversion. The first is "use questionnaires". This one turns eight answers into a risk profile and its coefficient A, the A in U = E(r) − ½Aσ². Each group member answers on their own. Their A then decides their y\*, the share of money that goes into the optimal risky portfolio P instead of T-bills.

The questions are modelled on standard risk-tolerance surveys of the kind banks and fund houses use (e.g. Grable & Lytton, 1999). The scoring is ours: it is transparent and rule-based, not a validated psychometric instrument.

## Questions (score each answer 1–5)

| # | Question | 1 | 3 | 5 |
|---|---|---|---|---|
| 1 | When will you need most of this money? | Within 2 years | 5–7 years | 10+ years |
| 2 | Your portfolio falls 20% in three months. You… | Sell everything | Hold and wait | Buy more |
| 3 | Which yearly range of outcomes would you pick? | +4% to +7% | −8% to +18% | −25% to +40% |
| 4 | How much investing experience do you have? | None | Mutual funds / SIPs | Direct stocks for 2+ years |
| 5 | Without this money, how many months could you cover your expenses? | Under 1 month | 3–6 months | 12+ months |
| 6 | How stable is your expected income? | Uncertain | Fairly stable | Very stable, with room to save |
| 7 | "I would accept a 1-in-10 chance of losing a quarter of my investment for a chance to double it." | Strongly disagree | Neutral | Strongly agree |
| 8 | How do you feel when an investment you hold falls sharply? | I lose sleep | Uneasy, but I stay put | I see an opportunity |

Use 2 and 4 for answers between the columns.

## Score → profile → A

| Total score | Profile | A | y\* on our P (forward-looking) | Share in T-bills |
|---|---|---|---|---|
| 8–18 | Conservative | 6 | 30% | 70% |
| 19–29 | Balanced | 4 | 46% | 54% |
| 30–40 | Aggressive | 2 | 91% | 9% |

The y\* values come from `data/latest/portfolio.json` and change when the data does. y\* = (E[r_P] − r_f) / (A·σ_P²), capped at 100% because a student can't borrow at the T-bill rate.

## Group results (fill in)

| Member | Score | Profile | A | Notes |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

## Caveats

- Questionnaires measure *stated* risk tolerance. Behavioural finance (BKM Ch 12) warns that stated tolerance shifts with recent market moves, which is recency bias. Re-take it once a year.
- Questions 1, 5 and 6 measure *capacity* to take risk (horizon, liquidity, income); the rest measure *willingness*. If the two disagree, use the lower one.
