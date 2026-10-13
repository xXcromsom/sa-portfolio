"""Phase 3 text step: headlines and earnings calls -> FinBERT sentiment, hedging, tone gap.

Run from the project root (slow the first time: FinBERT scores ~15k sentences on CPU;
results are cached per document, so later runs only score new files):
    python -m pipeline.text_step            # use cached headlines if fetched today
    python -m pipeline.text_step --refresh  # re-fetch headlines

Sentence-level scores (which contain transcript text) stay in data/raw/derived/,
outside git. Only the aggregates go to data/latest/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date

import pandas as pd

from src import news
from src import text_analysis as ta
from src.config import load_config, project_path


def _verify():
    ca = os.getenv("CA_BUNDLE")
    return str(project_path(ca)) if ca else True


def headlines(cfg: dict, refresh: bool) -> pd.DataFrame:
    path = project_path(cfg["data"]["latest_dir"]) / "news.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    companies = {t: v["news_query"] for t, v in cfg["universe"]["stocks"].items()}
    df = news.fetch_headlines(companies, date.today(), cfg["text"]["news_months"], _verify())
    if path.exists():  # keep older headlines that have scrolled out of the feed
        df = pd.concat([pd.read_parquet(path)[df.columns], df]).drop_duplicates(["ticker", "title"])
    df = df[df["ticker"].isin(companies)].reset_index(drop=True)  # drop stocks no longer in the config
    df.to_parquet(path)
    return df


def score_headlines(df: pd.DataFrame, out_path) -> pd.DataFrame:
    """FinBERT scores for headlines, reusing earlier scores for titles already seen."""
    old = pd.read_parquet(out_path) if out_path.exists() else pd.DataFrame(columns=["title"])
    new_titles = sorted(set(df["title"]) - set(old["title"]))
    if new_titles:
        scored = ta.finbert_scores(new_titles)
        scored.insert(0, "title", new_titles)
        old = pd.concat([old, scored], ignore_index=True)
        old.to_parquet(out_path)
    return df.merge(old, on="title", how="left")


def transcripts(cfg: dict) -> pd.DataFrame:
    raw = project_path("data/raw")
    text_cache, derived = raw / "text", raw / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    rows = []
    for ticker in cfg["universe"]["stocks"]:
        files = sorted((raw / ticker).glob("transcripts_*.pdf"))
        parsed = {f.stem.split("_")[-1]: ta.speaker_turns(ta.pdf_text(f, text_cache)) for f in files}
        skipped = [q for q, t in parsed.items() if not ta.usable(t)]
        good = {q: t for q, t in parsed.items() if q not in skipped}
        for (quarter, turns) in zip(good, ta.harmonise_roles(list(good.values()))):
            digest = hashlib.sha256(" ".join(turns["role"] + turns["text"]).encode()).hexdigest()[:12]
            cache = derived / f"{ticker}_{quarter}_{digest}.parquet"
            scored = pd.read_parquet(cache) if cache.exists() else ta.transcript_tone(turns)
            if not cache.exists():
                scored.to_parquet(cache)
            rows.append({"ticker": ticker, "quarter": quarter, **ta.summarize_tone(scored, turns)})
        for q in skipped:
            rows.append({"ticker": ticker, "quarter": q, "skipped": "scanned PDF; unreadable text layer"})
    return pd.DataFrame(rows).sort_values(["ticker", "quarter"]).reset_index(drop=True)


def main(refresh: bool = False, news_only: bool = False) -> None:
    """news_only: rescore headlines but keep the earlier transcript results. Used on GitHub Actions,
    where the transcript PDFs (data/raw/, never committed) are not available."""
    cfg = load_config()
    out = project_path(cfg["data"]["latest_dir"])
    news_df = score_headlines(headlines(cfg, refresh), out / "news_scores.parquet")
    news_df.to_parquet(out / "news_scored.parquet")
    monthly = (news_df.assign(month=news_df["published"].dt.to_period("M").astype(str))
               .groupby(["ticker", "month"])
               .agg(headlines=("title", "size"), tone=("tone", "mean"),
                    pct_negative=("label", lambda s: (s == "negative").mean()))
               .reset_index())
    if news_only:
        calls = pd.read_csv(out / "transcript_tone.csv")
    else:
        calls = transcripts(cfg)
        calls.to_csv(out / "transcript_tone.csv", index=False)
    summary = {
        "headlines": {t: {"count": int(len(g)), "first": str(g["published"].min().date()),
                          "last": str(g["published"].max().date()), "mean_tone": float(g["tone"].mean()),
                          "pct_positive": float((g["label"] == "positive").mean()),
                          "pct_negative": float((g["label"] == "negative").mean())}
                      for t, g in news_df.groupby("ticker")},
        "monthly_headline_tone": monthly.round(4).to_dict(orient="records"),
        "transcripts": json.loads(calls.round(4).to_json(orient="records")),
        "method": "FinBERT (ProsusAI/finbert) sentence scores; tone = P(pos) - P(neg); hedge share = "
                  "uncertainty words / all words (subset of Loughran-McDonald-style terms)",
    }
    (out / "sentiment.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(calls.drop(columns=[c for c in calls.columns if c.endswith("_sentences")], errors="ignore")
          .round(3).to_string())
    print(json.dumps(summary["headlines"], indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="re-fetch headlines")
    parser.add_argument("--news-only", action="store_true", help="keep the existing transcript results")
    args = parser.parse_args()
    main(args.refresh, args.news_only)
