"""Text analysis for earnings calls and headlines (Phase 3).

- Sentiment: FinBERT (Araci 2019; ProsusAI/finbert), a BERT model fine-tuned on
  financial news. Each sentence gets P(positive), P(negative), P(neutral);
  tone = P(positive) - P(negative), from -1 to +1.
- Hedging: the share of words that signal uncertainty. The short list below is
  of the kind in Loughran & McDonald's (2011) Uncertainty category; it is a
  hand-picked subset, not their full dictionary.
- Speakers: transcripts are split into management and analyst turns, so tone
  can be compared between the people selling the story and the people
  questioning it.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pypdf

HEDGE_WORDS = frozenset("""
approximately assume assumed assumption believe believes could depend depends depending doubt
estimate estimated expect hopefully indicate likely may maybe might perhaps possible possibly
probably risk risks roughly seem seems somewhat suggest tentative uncertain uncertainty unclear
unknown unpredictable variable volatile volatility
""".split())

SPEAKER = re.compile(r"^\s*([A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+){0,4})\s*:\s*(.*)$")
# Keywords are matched case-insensitively, but a name must be capitalised words;
# otherwise "the line" in "question from the line of X" would count as a name.
_NAME = r"([A-Z][a-zA-Z.'\-]+(?:\s+[A-Z][a-zA-Z.'\-]+){0,3})"
_TITLE = r"(?:(?i:mr|ms|mrs|dr)\.?\s+)?"
ANALYST_INTRO = re.compile(r"(?i:question|line)\s+(?i:is\s+|comes\s+)?(?i:from|of)\s+(?i:the\s+line\s+of\s+)?"
                           + _TITLE + _NAME + r"\s+(?i:from|of|with)\b")
HANDOVER = re.compile(r"(?i:over\s+to|hand\s+(?:the\s+\w+\s+)?over\s+to|invite|pass\s+(?:on\s+)?the\s+call\s+to|"
                      r"request)\s+" + _TITLE + _NAME)
NOT_NAMES = {"yes", "no", "okay", "ok", "sure", "right", "thank you", "thanks", "correct", "so"}
PAGE_FURNITURE = re.compile(r"^\s*(?:Corporate Office|Registered Office|Regd\.? Office|CIN\b|Tel\.?:|Website|"
                            r"Page \d+|External Document)", re.I)
REMARKS = re.compile(r"^\s*(?:Mr|Ms|Mrs|Dr)\.?\s+([A-Z][A-Za-z\-]+)['’]s\s+(?:opening\s+|closing\s+)?remarks\b")


def _clean_name(name: str) -> str:
    return re.sub(r"^(?:Mr|Ms|Mrs|Dr)\.?\s+", "", name.strip()).rstrip(".")


def _text_quality(text: str) -> float:
    """Share of tokens that look like ordinary words; scanned PDFs with bad OCR score low."""
    tokens = re.findall(r"[A-Za-z]{2,}", text)
    common = sum(t.lower() in _COMMON for t in tokens)
    return common / len(tokens) if tokens else 0.0


_COMMON = frozenset("""the and of to in is we that for on this it as are with be our you have at
will from by an or not which but so all can has there their they was what about growth quarter
year business market thank question""".split())
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")


def pdf_text(path: Path, cache_dir: Path) -> str:
    """Text of a PDF, cached as .txt next to the other raw files."""
    cache = cache_dir / (path.parent.name + "_" + path.stem + ".txt")
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(path).pages)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


NAME_LINE = re.compile(r"^\s*([A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+){0,4})\s*$")


def speaker_turns(text: str) -> pd.DataFrame:
    """Split a transcript into (speaker, role, text) turns.

    Handles both layouts seen in Indian transcripts: "Name: words" (HUL, ICICI)
    and a name alone on its own line (Infosys). Parsing starts at the first
    "Moderator" line, which skips cover letters and participant lists. A name
    counts as a speaker only if it speaks at least twice or is an analyst the
    moderator introduced; this keeps headings such as "On Costs" out.
    Analysts are the people the moderator introduces ("the next question is
    from the line of X from Y"). Everyone else, apart from the moderator, is
    treated as management.
    """
    start = re.search(r"^\s*Moderator\b", text, re.M | re.I)
    body = text[start.start():] if start else text
    flat = " ".join(body.split())
    analysts = {_clean_name(m.group(1)).lower() for m in ANALYST_INTRO.finditer(flat)}
    # Infosys lists analysts in a participants block ("ANALYSTS ... ") before the call starts.
    header = text[: start.start()] if start else ""
    block = re.search(r"\bANALYSTS\b(.*?)(?:CORPORATE PARTICIPANTS|MANAGEMENT|JOURNALISTS|$)", header, re.S)
    roster = " ".join(block.group(1).split()) if block else ""
    handed = {_clean_name(m.group(1)).lower() for m in HANDOVER.finditer(flat)}
    lines = body.splitlines()

    def candidate(line: str) -> tuple[str, str] | None:
        # ICICI marks speeches with headings such as "Mr. Bakhshi's opening remarks".
        r = REMARKS.match(line)
        if r:
            surname = r.group(1).lower()
            full = next((h for h in handed if h.split()[-1] == surname), surname)
            return full.title(), ""
        m = SPEAKER.match(line) or NAME_LINE.match(line)
        if not m or len(m.group(1)) > 40:
            return None
        name = _clean_name(m.group(1))
        if name.lower() in NOT_NAMES or len(name) < 3:
            return None
        return name, (m.group(2) if m.re is SPEAKER else "")

    counts = pd.Series([c[0] for line in lines if (c := candidate(line))], dtype=object).value_counts()

    def is_speaker(name: str) -> bool:
        n = name.lower()
        return n in ("moderator", "operator") or counts.get(name, 0) >= 2 or n in handed or n in analysts

    turns, speaker, buf = [], None, []
    for line in lines:
        if PAGE_FURNITURE.match(line):  # repeated page headers, not speech
            continue
        c = candidate(line)
        if c and is_speaker(c[0]):
            if speaker:
                turns.append((speaker, " ".join(buf)))
            speaker, buf = c[0], [c[1]]
        elif speaker:
            buf.append(line.strip())
    if speaker:
        turns.append((speaker, " ".join(buf)))

    # Structural rule (robust to names that PDF extraction breaks, e.g. "A bneesh Roy"):
    # whoever speaks right after the moderator announces a question is an analyst.
    # The cue must be an actual introduction, not the opening "you may ask questions".
    intro_cue = re.compile(r"question\s+(?:is\s+|comes\s+)?from|from\s+the\s+line\s+of", re.I)
    for (prev, prev_text), (name, _) in zip(turns, turns[1:]):
        if prev.lower() in ("moderator", "operator") and intro_cue.search(prev_text) \
                and name.lower() not in ("moderator", "operator"):
            analysts.add(name.lower())

    def same_person(a: str, b: str) -> bool:
        # Exact match, or every word of a two-word-plus name appears in the other.
        ta_, tb = set(a.split()), set(b.split())
        return a == b or (min(len(ta_), len(tb)) >= 2 and (ta_ <= tb or tb <= ta_))

    roster_names = {_clean_name(m.group(1)).lower() for m in re.finditer(_NAME, roster)}

    def role(name: str) -> str:
        n = name.lower()
        if n in ("moderator", "operator"):
            return "moderator"
        # Anyone the call is handed to ("over to Mr. X", "pass the call to X") is
        # management, unless the moderator also introduced them by name as a questioner.
        named_analyst = any(same_person(n, a) for a in
                            {_clean_name(m.group(1)).lower() for m in ANALYST_INTRO.finditer(flat)})
        if any(same_person(n, h) for h in handed) and not named_analyst:
            return "management"
        if any(same_person(n, a) for a in analysts | roster_names):
            return "analyst"
        return "management"

    df = pd.DataFrame(turns, columns=["speaker", "text"])
    df["role"] = df["speaker"].map(role)
    return df


def harmonise_roles(transcripts: list[pd.DataFrame]) -> list[pd.DataFrame]:
    """Give each person the role they hold in most of one company's calls.

    The same executives and analysts appear quarter after quarter, so a majority
    vote across transcripts fixes one-off mistakes, e.g. a CFO marked as an
    analyst because the preceding analyst's name was garbled in the PDF.
    """
    votes = pd.concat([t.loc[t["role"] != "moderator", ["speaker", "role"]].drop_duplicates()
                       for t in transcripts])
    tally = votes.groupby(["speaker", "role"]).size().unstack(fill_value=0)
    majority = {name: ("management" if row.get("management", 0) > row.get("analyst", 0) else "analyst")
                for name, row in tally.iterrows() if row.get("management", 0) != row.get("analyst", 0)}
    out = []
    for t in transcripts:
        t = t.copy()
        mask = t["role"] != "moderator"
        t.loc[mask, "role"] = t.loc[mask, "speaker"].map(majority).fillna(t.loc[mask, "role"])
        out.append(t)
    return out


def usable(turns: pd.DataFrame) -> bool:
    """A transcript we can analyse has a moderator and at least one analyst question.

    Scanned PDFs with a garbled OCR layer (e.g. "Modarcdor") fail this test.
    """
    roles = set(turns["role"])
    return "moderator" in roles and "analyst" in roles


def sentences(text: str, min_words: int = 6, max_words: int = 80) -> list[str]:
    """Sentences of a sensible length (drops fragments and run-on page junk)."""
    out = []
    for s in SENTENCE.split(" ".join(text.split())):
        n = len(s.split())
        if min_words <= n <= max_words:
            out.append(s)
    return out


def hedge_share(text: str) -> float:
    words = re.findall(r"[a-z]+", text.lower())
    return sum(w in HEDGE_WORDS for w in words) / len(words) if words else np.nan


@lru_cache(maxsize=1)
def _finbert():
    from transformers import pipeline  # heavy import, only when scoring
    return pipeline("text-classification", model="ProsusAI/finbert", top_k=None, truncation=True,
                    max_length=128, device=-1)


def finbert_scores(texts: list[str], batch_size: int = 32) -> pd.DataFrame:
    """P(positive), P(negative), P(neutral) and tone = pos - neg for each text."""
    if not texts:
        return pd.DataFrame(columns=["positive", "negative", "neutral", "tone"])
    raw = _finbert()(texts, batch_size=batch_size)
    df = pd.DataFrame([{d["label"]: d["score"] for d in row} for row in raw])
    df["tone"] = df["positive"] - df["negative"]
    df["label"] = df[["positive", "negative", "neutral"]].idxmax(axis=1)
    return df


def transcript_tone(turns: pd.DataFrame) -> pd.DataFrame:
    """Sentence-level FinBERT scores for management and analyst turns."""
    rows = [(r.role, s) for r in turns.itertuples() if r.role != "moderator" for s in sentences(r.text)]
    if not rows:
        return pd.DataFrame(columns=["role", "sentence", "positive", "negative", "neutral", "tone", "label"])
    scored = finbert_scores([s for _, s in rows])
    scored.insert(0, "sentence", [s for _, s in rows])
    scored.insert(0, "role", [r for r, _ in rows])
    return scored


def summarize_tone(scored: pd.DataFrame, turns: pd.DataFrame) -> dict:
    """One row per transcript: tone and hedging by speaker role."""
    out = {"sentences": len(scored)}
    for role in ("management", "analyst"):
        s = scored[scored["role"] == role]
        text = " ".join(turns.loc[turns["role"] == role, "text"])
        out[f"{role}_sentences"] = len(s)
        out[f"{role}_tone"] = float(s["tone"].mean()) if len(s) else np.nan
        out[f"{role}_pct_positive"] = float((s["label"] == "positive").mean()) if len(s) else np.nan
        out[f"{role}_pct_negative"] = float((s["label"] == "negative").mean()) if len(s) else np.nan
        out[f"{role}_hedge_share"] = hedge_share(text)
    out["tone_gap"] = out["management_tone"] - out["analyst_tone"]
    return out
