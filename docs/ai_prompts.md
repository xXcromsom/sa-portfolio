# AI prompts and methods (for the report's appendix)

The brief asks us to *use* AI tools. This file records every AI step, so a reader can repeat it or check it:
- which model ran it
- what it was asked
- how its output was checked

| ID | Task | Tool | Output | Checked against |
|---|---|---|---|---|
| P1 | Pull key financials from annual-report PDFs | Claude (claude-opus-5-5) in Claude Code | `data/ai/ratio_extraction.json` | Yahoo Finance and Screener (`data/latest/extraction_accuracy.json`) |
| P2 | Earnings-call sentiment, sentence by sentence | FinBERT (ProsusAI/finbert), a Python NLP model | `data/latest/sentiment.json`, `transcript_tone.csv` | A hand-labelled sample, and the LLM labels in P4 |
| P3 | Headline sentiment | FinBERT | `data/latest/news_scored.parquet` | Same as P2 |
| P4 | Aspect sentiment and guidance from earnings calls | Claude in Claude Code | `data/ai/concall_aspects.json` | Quotes with page references; compared with FinBERT tone |
| P5 | News framing and behavioural-bias tags | Claude in Claude Code | `data/ai/headline_framing.json` | FinBERT labels; a hand-labelled sample |

## P1: ratio extraction (13 Oct 2026)

**Input:** text of each company's FY26 consolidated balance sheet, statement of profit and loss and cash-flow statement. It was extracted with pypdf from the pages listed in the output file.

**Instruction followed:**

> From these consolidated financial statements for the year ended 31 March 2026, extract the figures below exactly as printed, then convert them to ₹ crore. For a bank, extract the bank-specific items instead.
> - For non-banks: revenue from operations; profit attributable to owners; basic EPS; equity attributable to owners (share capital + other equity, excluding non-controlling interests); borrowings (current + non-current, excluding leases); lease liabilities; cash and cash equivalents; net cash from operating activities; dividends paid; number of shares (share capital ÷ face value).
> - For a bank: interest earned, other income, interest expended, operating expenses, provisions, deposits and advances.
>
> Record any one-off items. Do not estimate: if a figure is not clearly legible in the text, leave it out and say why. Note every definitional choice (what is included in or excluded from equity, debt and cash).

**Result:** 44 of 47 field comparisons are within 1%, with 0 extraction errors. The other 3 are documented definition differences (Yahoo's revenue for HUL; ICICI's borrowings and cash).

## P4: earnings-call aspects and guidance (13 Oct 2026)

**Input:** Q1 FY27 transcripts. For HUL and ICICI, the management prepared remarks (about 2,000 words each). For Sun Pharma, the short opening remarks plus every management Q&A sentence mentioning guidance, growth, margins, R&D, launches or M&A (98 sentences).

**Instruction followed:**

> Summarise this earnings call for an equity analyst.
> 1. Record the headline numbers exactly as stated.
> 2. List every piece of forward guidance, marking whether it is quantified.
> 3. For each business aspect (demand, pricing, costs, margins, segments, funding, asset quality, capital, M&A and so on), give one sentiment (positive, negative or neutral) for a shareholder, with the evidence in a few words.
> 4. Give an overall tone and the items to watch next quarter.
>
> Use only what management said. Don't add outside knowledge or opinions.

## P5: headline framing and behavioural-bias tags (13 Oct 2026)

**Input:** 120 headlines, 40 per company, stratified by month (`data/ai/headline_sample.csv`).

**Instruction followed:**

> For each headline:
> - say whether it is really about this company (not a name collision or a generic market story)
> - give its sentiment for a shareholder
> - say whether it frames the news as a gain, a loss or neither
> - tag any behavioural cue: a price-target anchor, an appeal to authority, a herding or FOMO prompt, hype, fear, or recency extrapolation (BKM Ch 12)
>
> Note anything misleading.

**Result:**
- 14% of headlines are irrelevant: name collisions such as ICICI Securities, ICICI Direct and SPARC, plus generic market stories.
- On the 103 relevant ones, FinBERT agrees with these labels 70% of the time. The usual disagreement is FinBERT calling mild good news "neutral".
- 41% carry at least one bias cue. Authority (22) and herding (20) are the most common.
- Sun Pharma's coverage is 60% gain-framed and 3% loss-framed, against HUL's 49% and 23%.

**Why this is a fair test of AI extraction (P1):** the output gives exact page numbers and original units, so every figure can be traced back to the PDF. It is then scored field by field against two independent sources. Differences are classified as either an *extraction error* or a *definition difference*, e.g. Screener's borrowings include lease liabilities. Only the first counts against the AI.
