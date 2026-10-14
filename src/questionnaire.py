"""Risk questionnaire: ten answers -> risk aversion A in U = E(r) - 1/2 A sigma^2 (BKM Ch 6).

Modelled on standard risk-tolerance surveys (e.g. Grable & Lytton, 1999). The scoring is
ours: transparent and rule-based, not a validated psychometric instrument.

Capacity questions (horizon, cushion, income, share of savings) measure how much risk the
investor can afford; willingness questions measure how much they want. Each group is scored
0-1 and mapped to A, and the more conservative (higher) A wins, because a willing investor who
can't afford a loss shouldn't take it. docs/risk_questionnaire.md mirrors this file.
"""
from __future__ import annotations

from dataclasses import dataclass

# (key, kind, question, five options from most cautious to most risk-tolerant)
QUESTIONS: list[tuple[str, str, str, tuple[str, str, str, str, str]]] = [
    ("horizon", "capacity", "When will you need most of this money?",
     ("Within 1 year", "In 1-3 years", "In 3-5 years", "In 5-10 years", "In more than 10 years")),
    ("drawdown", "willingness", "Your portfolio falls 20% in three months. What do you do?",
     ("Sell everything", "Sell some", "Hold and wait", "Buy a little more", "Buy a lot more")),
    ("range", "willingness", "Which one-year range of outcomes would you pick?",
     ("+4% to +7%", "0% to +12%", "-8% to +18%", "-15% to +28%", "-25% to +40%")),
    ("experience", "willingness", "How much investing experience do you have?",
     ("None", "Fixed deposits and savings only", "Mutual funds or SIPs", "Some direct stocks",
      "Direct stocks for 2+ years")),
    ("cushion", "capacity", "Without this money, how many months of expenses could you cover?",
     ("Under 1 month", "1-3 months", "3-6 months", "6-12 months", "More than 12 months")),
    ("income", "capacity", "How stable is your expected income?",
     ("Uncertain", "Somewhat uncertain", "Fairly stable", "Stable", "Very stable, with room to save")),
    ("gamble", "willingness",
     "\"I would accept a 1-in-10 chance of losing a quarter of my investment for a chance to double it.\"",
     ("Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree")),
    ("feeling", "willingness", "How do you feel when an investment you hold falls sharply?",
     ("I lose sleep", "Very anxious", "Uneasy, but I stay put", "Calm", "I see an opportunity")),
    ("goal", "willingness", "What is the main goal for this money?",
     ("Protect what I have", "Steady income", "Balanced growth", "Growth", "Maximum growth")),
    ("share", "capacity", "What share of your total savings is this money?",
     ("Almost all of it", "More than half", "About half", "About a quarter", "Under 10%")),
]

A_MOST_CAUTIOUS, A_MIDDLE, A_MOST_TOLERANT = 8.0, 4.0, 1.5


@dataclass(frozen=True)
class Result:
    capacity: float      # 0 (no capacity for risk) to 1
    willingness: float   # 0 to 1
    a_capacity: float
    a_willingness: float
    risk_aversion: float
    profile: str


def score_to_a(s: float) -> float:
    """0 -> 8, 0.5 -> 4, 1 -> 1.5, piecewise linear (finer steps where most investors sit)."""
    if not 0.0 <= s <= 1.0:
        raise ValueError(f"score must be in [0, 1], got {s}")
    if s <= 0.5:
        return A_MOST_CAUTIOUS - (A_MOST_CAUTIOUS - A_MIDDLE) * s / 0.5
    return A_MIDDLE - (A_MIDDLE - A_MOST_TOLERANT) * (s - 0.5) / 0.5


def profile_name(risk_aversion: float) -> str:
    if risk_aversion < 3:
        return "Aggressive"
    return "Balanced" if risk_aversion < 5.5 else "Conservative"


def score(answers: dict[str, int]) -> Result:
    """`answers` maps each question key to the chosen option, 1 (most cautious) to 5."""
    missing = [k for k, *_ in QUESTIONS if k not in answers]
    if missing:
        raise ValueError(f"unanswered questions: {missing}")
    groups: dict[str, list[int]] = {"capacity": [], "willingness": []}
    for key, kind, *_ in QUESTIONS:
        if answers[key] not in (1, 2, 3, 4, 5):
            raise ValueError(f"answer to {key!r} must be 1-5, got {answers[key]!r}")
        groups[kind].append(answers[key])
    cap, will = ((sum(v) / len(v) - 1) / 4 for v in (groups["capacity"], groups["willingness"]))
    a_cap, a_will = score_to_a(cap), score_to_a(will)
    a = round(max(a_cap, a_will) * 4) / 4   # nearest 0.25; the more conservative answer wins
    return Result(cap, will, a_cap, a_will, a, profile_name(a))
