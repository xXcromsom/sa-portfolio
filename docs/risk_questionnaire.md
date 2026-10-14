# Risk questionnaire: estimating your own risk aversion A

The Class 8–10 deck (BKM Ch 6) gives three ways to estimate risk aversion. The first is "use questionnaires". This one turns ten answers into a risk profile and its coefficient A, the A in U = E(r) − ½Aσ². The dashboard opens with it (step 1 of 2), and the answers then set the portfolio automatically: y\*, the share of money that goes into the optimal risky portfolio P instead of T-bills.

The questions are modelled on standard risk-tolerance surveys of the kind banks and fund houses use (e.g. Grable & Lytton, 1999). The scoring is ours: it is transparent and rule-based, not a validated psychometric instrument. The code is `src/questionnaire.py`; this file mirrors it.

## Questions (each answer scores 1–5, most cautious first)

| # | Kind | Question | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|---|
| 1 | Capacity | When will you need most of this money? | Within 1 year | 1–3 years | 3–5 years | 5–10 years | 10+ years |
| 2 | Willingness | Your portfolio falls 20% in three months. You… | Sell everything | Sell some | Hold and wait | Buy a little more | Buy a lot more |
| 3 | Willingness | Which one-year range of outcomes would you pick? | +4% to +7% | 0% to +12% | −8% to +18% | −15% to +28% | −25% to +40% |
| 4 | Willingness | How much investing experience do you have? | None | FDs and savings only | Mutual funds or SIPs | Some direct stocks | Direct stocks for 2+ years |
| 5 | Capacity | Without this money, how many months of expenses could you cover? | Under 1 | 1–3 | 3–6 | 6–12 | 12+ |
| 6 | Capacity | How stable is your expected income? | Uncertain | Somewhat uncertain | Fairly stable | Stable | Very stable, with room to save |
| 7 | Willingness | "I would accept a 1-in-10 chance of losing a quarter of my investment for a chance to double it." | Strongly disagree | Disagree | Neutral | Agree | Strongly agree |
| 8 | Willingness | How do you feel when an investment you hold falls sharply? | I lose sleep | Very anxious | Uneasy, but I stay put | Calm | I see an opportunity |
| 9 | Willingness | What is the main goal for this money? | Protect what I have | Steady income | Balanced growth | Growth | Maximum growth |
| 10 | Capacity | What share of your total savings is this money? | Almost all | More than half | About half | About a quarter | Under 10% |

## Score → A → portfolio

1. **Two scores.** Capacity (questions 1, 5, 6, 10: can you afford risk?) and willingness (the other six: do you want it?). Each is the average answer rescaled to 0–1: (average − 1) / 4.
2. **Each score maps to an A**, piecewise linear: 0 → 8, 0.5 → 4, 1 → 1.5.
3. **The more cautious A wins** (the higher one), rounded to 0.25. A willing investor who can't afford a loss shouldn't take it.
4. **Profile:** A < 3 Aggressive · 3 ≤ A < 5.5 Balanced · A ≥ 5.5 Conservative.
5. **Portfolio:** y\* = (E[r_P] − r_f) / (A·σ_P²), capped at 100% because a student can't borrow at the T-bill rate (the dashboard's "Allow borrowing" switch lifts the cap to 200%). The stock mix inside P is the same for everyone (the separation property); A only sets y.

| Answers | A | Profile | y\* on our P (forward-looking) |
|---|---|---|---|
| All middle options (3) | 4.00 | Balanced | 44% |
| All 2s | 6.00 | Conservative | 29% |
| All 4s | 2.75 | Aggressive | 63% |
| Willing (5s) but no capacity (1s) | 8.00 | Conservative | 22% |

The y\* values come from `data/submission/portfolio.json` and change when the data does.

## Reading A beyond the questionnaire

The questionnaire's range is 1.5–8, typical of real investors (2–6). The dashboard's slider also covers the theory's other cases:
- **A > 0, risk-averse:** risk lowers utility.
- **A ≤ (E[r_P] − r_f) / σ_P² ≈ 1.74:** y\* is 100% or more, so without borrowing every such A gives the same portfolio. This is why very low A looks "stuck".
- **A = 0, risk-neutral:** only expected return matters.
- **A < 0, risk-seeking:** risk adds utility.

With A ≤ 0 utility never penalises risk, so the investor holds the most P allowed: 100%, or 200% with borrowing.

## Group results (fill in)

| Member | Capacity | Willingness | A | Profile | Notes |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

## Caveats

- Questionnaires measure *stated* risk tolerance. Behavioural finance (BKM Ch 12) warns that stated tolerance shifts with recent market moves, which is recency bias. Re-take it once a year.
- Capacity questions measure the *ability* to take risk (horizon, liquidity, income, concentration); the rest measure *willingness*. When they disagree, the lower tolerance wins.
