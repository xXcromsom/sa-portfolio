import pytest

from src import questionnaire as q

KEYS = [k for k, *_ in q.QUESTIONS]
CAPACITY = [k for k, kind, *_ in q.QUESTIONS if kind == "capacity"]


def answers(default: int, **overrides) -> dict[str, int]:
    return {k: overrides.get(k, default) for k in KEYS}


def test_ten_questions_with_five_options():
    assert len(q.QUESTIONS) == 10
    assert all(len(options) == 5 for *_, options in q.QUESTIONS)
    assert len(set(KEYS)) == 10


def test_extremes_and_middle():
    assert q.score(answers(1)).risk_aversion == 8.0
    assert q.score(answers(1)).profile == "Conservative"
    assert q.score(answers(5)).risk_aversion == 1.5
    assert q.score(answers(5)).profile == "Aggressive"
    assert q.score(answers(3)).risk_aversion == 4.0
    assert q.score(answers(3)).profile == "Balanced"


def test_low_capacity_overrides_high_willingness():
    r = q.score(answers(5, **{k: 1 for k in CAPACITY}))
    assert r.willingness == 1.0 and r.capacity == 0.0
    assert r.risk_aversion == 8.0  # can't afford the risk, so the cautious A wins


def test_a_is_rounded_to_quarters_and_monotonic():
    previous = 9.0
    for level in range(1, 6):
        a = q.score(answers(level)).risk_aversion
        assert a * 4 == int(a * 4)
        assert a < previous
        previous = a


def test_score_to_a_bounds():
    assert q.score_to_a(0.0) == 8.0 and q.score_to_a(0.5) == 4.0 and q.score_to_a(1.0) == 1.5
    with pytest.raises(ValueError):
        q.score_to_a(1.2)


def test_rejects_missing_or_invalid_answers():
    with pytest.raises(ValueError, match="unanswered"):
        q.score({"horizon": 3})
    with pytest.raises(ValueError, match="must be 1-5"):
        q.score(answers(3, goal=6))
