# Security Analysis presentation: prep sheet

Marks: Report 15, Presentation 10, Individual presentation 15, Q&A 10. The faculty will probably not ask questions, but each person must understand their part. Marks also go to effective questions asked to other groups. The talk runs 15–20 minutes, and the report goes in before it.

Presenter names are placeholders. Change `SPEAKERS` in `deliverables/data.js`, then run `npm run deck` in `deliverables/`.

Every number below comes from the frozen 13 Oct dataset, except where it says 3 Nov.

## Running order (18:45)

| Slide | Topic | Speaker | Time |
|---|---|---|---|
| 1 | Cover | A | 0:30 |
| 2 | The three picks | A | 1:30 |
| 3 | What these prices require | A | 1:30 |
| 4 | Street check | A | 2:00 |
| 5 | Mosaic | B | 2:00 |
| 6 | Five AI tasks | B | 1:00 |
| 7 | Live demo | B | 2:00 |
| 8 | Market efficiency | B | 1:45 |
| 9 | Sentiment | C | 1:15 |
| 10 | Portfolio | C | 1:30 |
| 11 | Excess return, Sharpe, Treynor, alpha | C | 1:45 |
| 12 | The 15-year plan | C | 1:00 |
| 13 | Recommendation | C | 1:00 |

If you run short of time, cut slide 6 to one sentence and shorten the demo. Slides 14–17 are backup.

## Speaker A: selection, valuation, Street

**You must be able to explain:**

1. **The four selection tests:** a different macro driver, five-year correlation of 0.5 or less (highest pair 0.20), Nifty 50 liquidity with at least six quarters of transcripts, and a business a standard model can value. None of them claims the stocks will beat the market.
2. **Why not Media or Infosys:** Media was the strongest sector, but at A = 4 its certainty equivalents are −8% to −38%, below the T-bill. Sun Pharma keeps the dollar exposure at a lower beta than Infosys (0.65 against 0.82). We chose it partly after its strong run, which flatters the back-test, and we say so.
3. **The cost of equity:**
   ```
   r = rf + beta x ERP
   r(HUL) = 5.52% + 0.602 x 7.08% = 9.78%
   r(Sun) = 5.52% + 0.645 x 7.08% = 10.09%
   r(ICICI) = 5.52% + 1.293 x 7.08% = 14.67%
   ```
4. **Why each model:** HUL pays out 67% of profit, so dividends describe its cash well (two-stage DDM). Sun pays out 34% and ICICI's borrowings are raw material, so both use residual income on book value.
5. **The values:**

   | | Price, 13 Oct | Model | Peers | Blended | Blended vs price | Implied growth |
   |---|---|---|---|---|---|---|
   | HUL | ₹1,862 | ₹1,079 | ₹2,105 | ₹1,592 | −14% | 7.4% |
   | Sun Pharma | ₹1,760 | ₹748 | ₹1,702 | ₹1,225 | −30% | 8.6% |
   | ICICI Bank | ₹1,351 | ₹575 | ₹1,139 | ₹857 | −37% | 13.9% |

6. **Why we don't say "overvalued":** we found no way to beat these prices, so we read the gap as what the price requires. Implied growth is the perpetual growth at which the model equals the price.
7. **The Street check (3 Nov, Yahoo consensus):**

   | | Analysts | Buy share | Mean target | Discount rate the price needs | Our r |
   |---|---|---|---|---|---|
   | HUL | 39 | 69% | ₹2,256 | 7.9% | 9.8% |
   | Sun Pharma | 33 | 85% | ₹2,136 | 7.6% | 10.1% |
   | ICICI Bank | 42 | 100% | ₹1,769 | 9.9% | 14.7% |

8. **The ICICI bridge:** ₹575 on our model, ₹831 with the five-year beta (0.96), ₹1,096 with ₹265 for subsidiaries, ₹1,213 with the Street's ROE (17%, then 16%), against a price of ₹1,402 and a target of ₹1,769.
9. **Why we kept our beta:** switching after seeing the Street's answer would be tuning. With the five-year beta, P would be 39/21/40 and A = 4 would hold 38% in P.
10. **Why HUL is Hold:** "fairly valued" rested on a ±15% band: −14.5% at the freeze, −17.7% at the 3 Nov price. A label that flips on a small price move can't support a Buy. No number in the analysis changed.

**Be careful:** most broker figures are press summaries, not the original PDFs. Say so if asked.

## Speaker B: mosaic, AI, demo, efficiency

**You must be able to explain:**

1. **Mosaic theory:** building a view from many public pieces, plus non-public details that aren't material. Ours is all public, so under semi-strong efficiency it tests a thesis. It does not find alpha.
2. **Q2 FY27 (second-hand sources, so name them if asked):**
   - **HUL:** revenue +15%, volume +7%, EBITDA margin −142 bp to 22.6%. FIIs fell from 10.18% to 9.26% and DIIs rose from 15.99% to 17.05% (Jun 25 to Sep 26).
   - **Sun Pharma:** revenue about +12%, India +17.3%, US −8.2%, reported profit −36% on one-offs. Sources conflict on some figures.
   - **ICICI Bank:** profit +20%, NIM 4.18% (−18 bp), advances +30% (+24% excluding FCNR-B), gross NPA 1.20%.
3. **Organon:** about $11.75bn in cash, of which $9.25–9.75bn is debt. Sun goes from net cash to about 2.3× net debt/EBITDA, closing in Q4 FY27. Our beta was measured on the old balance sheet. A rough Hamada estimate says about 14% higher. Some broker targets exclude the deal.
4. **The AI rule:** AI reads and labels, and Python computes. Claude's extraction: 44 of 47 within 1% of Yahoo and Screener, the other 3 are definition differences. FinBERT: 2,428 headlines and 9,133 call sentences. Bias tags: 120 headlines, 41% with a cue, 14% not about the company, 70% agreement with FinBERT.
5. **The demo steps:** the slide's speaker notes have the script. Backup order: hosted app, local `streamlit run app.py`, recording, slide 16. If a step takes more than 10 seconds, move down without apologising.
6. **Weak form:** past prices can't predict returns. 0 of 8 rules beat buy-and-hold on Sharpe after a 0.25% round-trip cost. Largest z on lag-1 autocorrelation and variance ratios is 1.9 (HUL, lag 1), below 1.96. A variance ratio below 1 hints at mean reversion, but none is significant.
7. **Semi-strong form:** prices react fast and nothing is left afterwards. A reaction alone doesn't show this; you also need no drift. Over 72 results:

   | Window | Beat minus miss | 95% range | p |
   |---|---|---|---|
   | Days −1 to +1 | +2.79% | +1.04% to +4.54% | 0.003 |
   | Days +2 to +20 | −0.53% | −2.80% to +1.74% | 0.649 |
   | Days +2 to +60 | +1.64% | −2.21% to +5.49% | 0.409 |

8. **The careful sentence:** "no drift we can detect", not "no drift". The ranges are wide, and Harshita, Singh & Yadav (2018) did find drift in the Nifty 500.
9. **Strong form:** not tested, because it needs inside information.
10. **Data problems we caught:** five surprises of 30% or more are flagged. HUL on 12 Feb 2026 (estimate 51.08, actual 30.08) looks like a bad Yahoo row. The link between surprise and reaction holds without them (67 events, p = 0.009).

## Speaker C: sentiment, portfolio, performance, plan

**You must be able to explain:**

1. **Fear and greed:** CNN's index is American. Tickertape's MMI read 63 (Greed) on 3 Nov, but that's one reading, so we can't test it. Our stock score ranks four price signals over three years: 13 Oct HUL 17, Sun 18, ICICI 36; 3 Nov 39, 37, 58. It uses prices, so it describes the mood rather than measuring it independently.
2. **Does sentiment predict?** At stock level, no: FinBERT tone against the next five days has p-values of 0.95, 0.80, 0.62. At market level, higher India VIX was followed by higher Nifty returns (r = 0.24, p = 0.005; without COVID r = 0.20, p = 0.024), but the top band carries it, and that may simply be a risk premium.
3. **Choosing P:** the history-based optimiser puts the 60% maximum in ICICI, which is hindsight. On CAPM returns: 31/19/50, E[rP] 12.29%, σ 19.70%, Sharpe 0.34. The Nifty's forward Sharpe is 0.44, so three stocks can't beat the index's diversification. That is why the plan keeps a Nifty core.
4. **Sizing:**
   ```
   U = E(r) - 1/2 x A x sigma^2
   y* = (E[rP] - rf) / (A x sigma^2)
   y*(A = 4) = (12.29% - 5.52%) / (4 x 19.70%^2) = 43.6%
   ```
   A = 2 gives 87%, A = 6 gives 29%. Everyone holds the same P; only y changes. That is the separation property.
5. **The performance measures:**
   ```
   Excess return = Rp - Rf
   Sharpe = (Rp - Rf) / sigma
   Treynor = (Rp - Rf) / beta
   Jensen's alpha = (Rp - Rf) - beta x (Rm - Rf)
   ```
   So excess = Sharpe × σ = Treynor × β.
6. **Out-of-sample results, Jan 2023 to Oct 2026 (weights fitted on 2016–2022):**

   | | Excess over T-bills | Excess over Nifty | σ | β | Sharpe | Treynor | Alpha | t(alpha) |
   |---|---|---|---|---|---|---|---|---|
   | Forward-looking P | +3.0% | +0.5% | 12.8% | 0.71 | 0.24 | 4.3% | +1.2% | 0.27 |
   | Equal weight | +3.8% | +1.2% | 12.3% | 0.65 | 0.31 | 5.8% | +2.1% | 0.47 |
   | History-based P | −1.3% | −3.8% | 13.7% | 0.65 | −0.09 | −2.0% | −3.0% | −0.56 |
   | Nifty 50 | +2.5% | | 12.7% | 1.00 | 0.20 | 2.5% | 0 | |

7. **What to say about it:** a small lead, but no alpha we can tell from zero. Equal weights did better, so this shows no weighting skill. No t-statistic reaches 2, including ICICI's +7.1% over ten years (t = 1.17).
8. **Which measure when:** Sharpe suits a whole portfolio. Treynor and alpha suit a piece of a diversified one, which is how the three stocks sit around a Nifty core.
9. **What changes with A:** Sharpe and Treynor don't. Excess return, β and alpha scale with y. At A = 4, alpha on your money is 0.53%. Going forward with CAPM inputs, every asset has alpha 0 and Treynor 7.08% by construction, so the measures only mean something on realised returns.
10. **The plan:** ₹10,000 a month rising 10% a year puts in ₹38.1 lakh over 15 years. Median ₹64.8 lakh for A = 4. Half Nifty, half the three stocks, gliding down to 40% equity. Chance of ₹75 lakh: 19% normal, 11% resampling history.
11. **The call:** Hold at these weights, add only through the SIP. ICICI is 50% of the weight and 57% of the risk. This is coursework, not investment advice.

## Questions another group may ask us

| Question | Short answer |
|---|---|
| Your values are far below the price. Why own these stocks? | The portfolio takes prices as efficient and the valuation asks what they require. We don't claim mispricing, and the call is Hold. |
| Isn't it a contradiction to overweight the stock with the widest gap? | The same 1.29 beta gives ICICI the highest CAPM return and the highest discount rate. It is consistent once the two are read separately. |
| Why not switch to the five-year beta? | It would look tuned after seeing the Street. We show its effect openly (Table 4 and the bridge). |
| Isn't a 10.8-year beta stale for ICICI? | Possibly. It is 1.29 on the full sample and about 0.96 over five years. That is the largest single step in the bridge. |
| Your alpha is positive. Why not claim it? | The t-statistic is 0.27. It can't be told from zero, and equal weights did better. |
| You chose Sun Pharma after its run. Isn't that biased? | Yes, and the report says so. It flatters the 2023–26 test. |
| You found no drift, but the literature does. Who's right? | We can't rule it out. Our ranges are wide, with 72 events on three stocks; the study used the Nifty 500. |
| Does Organon break your selection? | It weakens test (iv), the model fit, and its beta understates future risk. The diversification case is unchanged. |
| How reliable are your broker numbers? | Mostly press summaries, dated and marked as second-hand. The original PDFs would be better. |
| What did the AI get wrong? | 3 of 47 extractions differed from Yahoo or Screener, all on definitions (such as Yahoo's bank cash including money at call). FinBERT agrees with the LLM tags 70% of the time, so the tags are not gospel. |
| Why is the Sharpe of P below the Nifty's? | Three stocks carry stock-specific risk. That is why they are a satellite around an index core. |

## Questions to ask other groups (Q&A marks)

Marks go to effective questions, so:
- Name the slide or number you're asking about.
- Ask one thing, and ask what it changes.
- Plan two per group, and have one person note what each group says about valuation and alpha.

**Valuation inputs**
- What share of your intrinsic value comes from the terminal value? How much does it move if terminal growth falls by 1 point?
- Which beta window did you use, and what happens to your value on a shorter one?
- What growth rate does the current price imply, and is that believable for this company?
- Why is that model right for this business? What would break it (a bank, a low payout, heavy buybacks)?
- Does your terminal growth stay below long-run nominal GDP?
- Are your peers comparable in leverage and growth, or just in the same sector?
- Your value differs from the analysts' targets by a wide margin. Which input explains most of the gap?

**Efficiency claims**
- You call this stock undervalued. Which form of efficiency does that reject, and what's your evidence?
- Did you test only the reaction to earnings, or also whether returns drift afterwards?
- Do your technical rules beat buy-and-hold after costs, and on which risk measure?
- How many strategies or rules did you try before showing this one?

**Performance measures**
- What is the t-statistic on your alpha?
- Were your weights fitted on the same period you report returns for?
- Is your benchmark the price index or total return? What does that do to your alpha?
- Why did you use Sharpe rather than Treynor for this portfolio, or the reverse?
- Did you choose these stocks after a strong run? How does that affect your back-test?

**AI verification**
- How did you check the AI's output, and what was the error rate?
- Did any number in your deck come straight from a model rather than a calculation?
- What did the AI get wrong, and how did you find out?
- Did you save your prompts, so someone else could repeat this?

**Portfolio and behaviour**
- What happens to your correlations in a sell-off?
- How did you choose your risk-aversion number, and how much does your allocation change with it?
- Which single stock contributes the most risk, compared with its weight?
- What would make you sell, and how does that rule avoid a behavioural bias?

## Before the day

- [ ] Replace Speaker A/B/C with real names and rebuild the deck
- [ ] Submit the report before the talk
- [ ] Make the hosted app public, test it logged out, and rebuild with `DASHBOARD_URL` so the QR codes appear
- [ ] Record the backup video
- [ ] Rehearse once with a timer; the target is under 19 minutes
- [ ] Have each person read the other two sections, in case someone is asked
- [ ] Check the latest numbers: Street and mood data are dated 3 Nov, so update them if the talk is much later
