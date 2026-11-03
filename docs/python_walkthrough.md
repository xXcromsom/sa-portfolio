# Python project: code walkthrough and demo script

Course BBAT5E07, Prof. Jinu Sara. Team: Abhay S (246213044), Sankarshana Mulugundam (246213080).

All the code is in one file, `python_project.py`, with tests in `tests/test_python_project.py`. The file imports nothing else from this repository. It reads the frozen data in `data/submission` and `workbook/valuation.xlsx`.

## Run it

```bash
pip install -r requirements-pipeline.txt
```

```bash
python python_project.py
```

```bash
python python_project.py --charts out/
```

```bash
streamlit run python_project.py
```

```bash
python -m pytest tests/test_python_project.py
```

Optional flags: `--fetch` downloads fresh prices with yfinance, `--finbert` scores two sample headlines (the first run downloads the model), and `--pdf FILE` reads a PDF with pypdf.

## Function map

Line numbers are for the current file. The "Owner" column follows the roles in proposal v2.

| Section | Lines | What is there | Course concept | Owner |
|---|---|---|---|---|
| 1 Settings | 50–73 | Paths, constants, `rupees()` for Indian digit grouping | Variables, numbers, strings | Abhay |
| 2 Files | 75–165 | `DataError`, `read_json`, `read_settings`, `read_returns`, `read_metrics_csv`, `read_pdf_text`, `download_prices` | Files and exceptions, pypdf, yfinance | Abhay |
| 3 Risk and return | 166–236 | `cagr`, `sharpe_ratio`, `sortino_ratio`, `max_drawdown`, `beta`, `treynor_ratio`, `jensen_alpha`, `metrics_table` | Functions, Pandas | Abhay |
| 4 Questionnaire | 237–296 | `QUESTIONS`, `score_to_a`, `profile_name`, `risk_aversion_from` | Decisions, loops, dictionaries, lists | Sankarshana |
| 5 Entities | 298–385 | `Security`, `Investor`, `Portfolio` | Classes | Both (Abhay presents) |
| 6 Valuation | 387–569 | `ValuationModel`, `DividendDiscountModel`, `ResidualIncomeModel`, `load_models` | Inheritance, recursion, openpyxl | Abhay |
| 7 Sorting | 570–626 | `merge_sort`, `binary_search`, `percentile`, `grid_search_max_sharpe` | Sorting and searching | Sankarshana |
| 8 Optimisation | 627–656 | `_optimise`, `max_sharpe_weights`, `efficient_frontier` | SciPy | Sankarshana |
| 9 Simulation | 657–745 | `simulate_normal`, `block_bootstrap`, `ewma_covariance`, `wealth_paths`, `risk_summary`, `simulate_sip`, `run_simulations` | NumPy | Sankarshana |
| 10 Efficiency | 746–806 | `rsi`, `trend_signal`, `rsi_signal`, `rule_sharpes`, `event_study` | Decisions, loops, Pandas | Abhay |
| 11 Text | 807–856 | `HEDGE_WORDS`, `hedge_share`, `headline_summary`, `finbert_tone`, `ask_model` | Sets, Transformers, requests | Abhay |
| 12 Charts | 857–907 | `save_charts` | Matplotlib, Seaborn | Sankarshana |
| 13 Tour | 908–1043 | `Project`, `load_project`, `check`, `tour` | Puts it together | Both |
| 14 Demo | 1044–end | `streamlit_view`, `main` | Streamlit, argparse | Both |

## The functions to know cold

Each person should be able to open these and explain them line by line.

### `present_value` (line 404)

The value of a list of cash flows is the first one discounted, plus the value of the rest.

Example with `flows = [10, 11]`, `r = 10%`:
```
present_value([10, 11], t=1) = 10 / 1.1 + present_value([11], t=2)
present_value([11], t=2) = 11 / 1.21 + present_value([], t=3)
present_value([], t=3) = 0
Answer = 9.09 + 9.09 + 0 = 18.18
```
- **Base case:** an empty list is worth 0.
- **Smaller problem:** one fewer flow, one year later.

### `implied_growth` (line 416)

It finds the growth at which the one-stage value equals the price. The gap between value and price changes sign somewhere in the range, so we look at the middle and keep the half where the sign still changes. Each call halves the range, so about 35 calls take it from about 0.6 to 1e-10.

The opening check raises `ValueError` if no answer exists in the range, which stops a pointless search.

### `ValuationModel` and its subclasses (lines 388, 454, 483)

- The base class is abstract, so it can't be created by itself. It holds the validation, discounting and bisection.
- Each subclass must define `cash_flows`, `terminal_value`, `single_stage_value`, `closed_form_value` and `implied_growth_closed_form`.
- `load_models` picks the class from the workbook's "Valuation model" row: a DDM for HUL, residual income for Sun Pharma and ICICI.
- Inheritance is justified here because the logic is really shared. Only the cash flows differ.

### `Portfolio.complete` (line 354)

```
y* = (E[rP] - rf) / (A x sigma^2)
```
- `y` is `y*` capped between 0 and 1, or up to 2 if borrowing is allowed.
- At A ≤ 0, risk never lowers utility, so `y*` is infinite and the cap applies.
- `allocation` turns `y` into rupees. `Investor.from_answers` is the class method that builds an investor from the questionnaire.

### `risk_aversion_from` (line 281)

Ten answers are scored 1–5 and grouped into capacity and willingness in a dictionary of lists. Each group is scaled to 0–1 and mapped to A by `score_to_a`. The higher A of the two wins, because a willing investor who can't afford a loss should not take it. Answering 3 everywhere gives A = 4.

### `simulate_normal` and `wealth_paths` (lines 658, 680)

- `rng.standard_normal((n_sims, horizon, assets))` gives independent draws. `@ chol.T` gives them the right correlations. `+ mu` adds the mean.
- `np.cumprod(..., axis=1)` compounds along time for each path.
- The array shape is paths × days × stocks, so one line handles all 10,000 paths. That is vectorisation.
- `seed` 42 is in `config.yaml`, so results repeat exactly and match `mc.json`.

### `merge_sort` and `binary_search` (lines 571, 588)

- **Merge sort:** split in half, sort each half recursively, merge by always taking the smaller front item. O(n log n).
- **Binary search:** it keeps a range where the answer lies and halves it. It needs a sorted list. O(log n), about 14 steps for 10,000 items.
- The tour runs our merge sort on 2,000 paths, checked against `sorted`, and uses `sorted` for all 10,000.

### `max_sharpe_weights` and `grid_search_max_sharpe` (lines 639, 608)

SciPy minimises the negative Sharpe ratio using SLSQP, with weights summing to 1 and each between 10% and 60%. The grid search tries every mix at 1% steps with two loops (the third weight is what's left). It is slow but easy to trust, and it finds the same portfolio.

## Likely questions from the faculty

| Question | Answer |
|---|---|
| Why recursion here rather than a loop? | The course asks for it, and it suits both problems: each has a clear base case and a smaller version of itself. A loop would work too, and we check the results against closed forms. |
| What is the recursion limit, and could this hit it? | Python's default is about 1,000 calls. `present_value` goes about 11 deep and bisection about 35. Merge sort goes about 11 deep on 2,000 items. |
| What does `flows[1:]` cost? | Each slice copies the list, so it's O(n²) overall. For 10 flows that doesn't matter. |
| Why an abstract base class? | It forces each model to define its cash flows, and it can't be created by itself. A missing method fails immediately. |
| `@staticmethod`, `@classmethod`, `@property`? | `present_value` needs no instance (static). `from_answers` builds an instance, so it takes the class. `volatility` reads like a value but is computed each time (property). |
| Why a `dataclass`? | `Security` and `Investor` mostly hold data, so it writes `__init__` for us. |
| What does `@` do? | Matrix multiplication. `w @ cov @ w` is wᵀΣw, the portfolio variance. |
| Why Cholesky? | Covariance = L Lᵀ. Multiplying independent normal draws by L gives draws with that covariance. |
| What is a lambda? | A small unnamed function, such as the objective passed to `minimize` or the key in `ranked`. |
| Why a set for hedge words? | Membership lookup is about constant time; in a list it scans every item. |
| Why your own `DataError`? | So callers can catch data problems separately, and the message names the file. `from err` keeps the original cause. |
| Why import heavy libraries inside functions? | The file still starts on a machine without Transformers or Seaborn. Only that feature fails. |
| Why not fill missing data? | A guess would silently change every number. The program stops and says what's wrong. |
| Is SLSQP guaranteed to find the best? | It finds a local optimum, and this problem is well behaved. The grid search is our independent check. |
| How is VaR calculated? | The amount invested minus the 5th percentile of ending wealth across paths. At A = 4 on ₹1 lakh it is ₹5,582. |
| Is the simulation a forecast? | No. It assumes CAPM mean returns and stable risk. The bootstrap keeps fat tails, but neither models regime shifts. |
| How do Streamlit reruns work? | Each widget change reruns the script from the top, so the numbers recompute from the new value of A. |
| What did you do yourselves, and what did AI do? | Answer honestly, from your own experience. See the next section. |

## AI disclosure

Say this plainly, and adjust it to what you actually did:

> We used Claude to help write and review this code. We checked it by running it, by testing it against our Excel workbook and our pipeline's outputs, and by reading it until we could explain each function. The tests and the checks in the tour are how we know it's right, rather than because an AI said so.

Before you present, make sure this is true for you: each of you should be able to open any function above and explain it without notes. If your course has an AI-use policy, follow its wording.

## Differences from proposal v2

Disclose these. Slide 15 of the deck lists them.

| Proposal said | The project does | Why |
|---|---|---|
| FINRA NCFS microdata | A 10-question questionnaire | It sets A for one investor directly. We did not calibrate it on NCFS. |
| Loughran–McDonald word lists | A small hedge-word set of that kind | Keeps the file self-contained. It is not the full list. |
| NSE total-return index | Nifty 50 price plus an estimated 1.22% a year | Measured from the gap between Nifty BeES and the index. |
| Anthropic SDK (optional) | A free model through OpenRouter (optional) | No cost for a live demo. Every number still comes from our files. |

If the professor would rather see any of these implemented as promised, ask early. The NCFS calibration is the largest of the four.

## Demo script (about 1:30 in the deck; up to 5 minutes if asked for more)

Before starting, open a terminal in the repository and open `python_project.py` in an editor. Increase the font size in both.

1. **Tour (30 s).** Run `python python_project.py`. Scroll to section 3: "Each value matches Excel and a closed form, and each line says OK." Show section 4 for SciPy against the grid, then section 7 for sorting.
2. **Charts (15 s).** Run with `--charts out/` and open `out/frontier.png`.
3. **Streamlit (30 s).** Run `streamlit run python_project.py`. Move A from 4 to 2: the share in P goes from 44% to 87%, the rupee split from ₹13,382 HUL to about ₹26,764, and the VaR from ₹5,582 to ₹16,138. Then open `Portfolio.complete` in the editor and point at the y* line.
4. **Tests (15 s).** Run `python -m pytest tests/test_python_project.py`: 21 passed.

**Longer version, if asked:**
- Open a function the professor names.
- Show a bad input failing, by changing `r` below `g2` in a Python prompt:
  ```python
  from python_project import DividendDiscountModel
  DividendDiscountModel("Test", 100, 0.05, 0.06, 5, 1.0, 0.1)
  ```
- Run `--pdf` on a report you've copied in, or `--finbert` if the model is already downloaded.

**Backup plan:**
- The tour output and charts are saved in `deliverables/assets/python/` (`tour_output.txt` and three PNGs).
- If Streamlit won't start, show the same change in a Python prompt with `Investor` and `Portfolio.allocation`.
- If the laptop fails, use the PDF of the deck. The code on the slides comes straight from the file.

## Before the day

- [ ] Run all four commands on the laptop you'll present from
- [ ] Run `--finbert` once beforehand if you plan to show it; the first run downloads the model
- [ ] Don't rely on `--fetch` in the demo. It needs the network, and on a machine with Avast it needs the CA bundle (see the README)
- [ ] Rehearse the handover between Abhay and Sankarshana
- [ ] Each read the other's sections of this file
