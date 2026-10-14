"""Render the dashboard headlessly and fail if anything raises or a data file is missing.

Drives the real flow: the questionnaire (skipped, and answered in full), then every tab of the
terminal for each dataset, at several risk-aversion levels including A <= 0.
Run before committing refreshed data (the nightly workflow does) and after freezing:
    python scripts/check_dashboard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import questionnaire as quiz  # noqa: E402

FILES = ["metrics.json", "valuation.json", "portfolio.json", "mc.json", "sip.json", "ai_analysis.json",
         "sentiment.json", "extraction_accuracy.json", "prices.parquet", "returns_daily.parquet",
         "returns_monthly.parquet"]


def problems_of(at: AppTest) -> list[str]:
    return [f"exception: {e.message}" for e in at.exception]


def check(dataset: str) -> list[str]:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180).run()
    problems = problems_of(at)
    at.button(key="skip").click().run()                 # SKIP: Balanced, A = 4
    problems += problems_of(at)
    if at.radio(key="dataset").value != dataset:
        at.radio(key="dataset").set_value(dataset).run()
    for a in (4.0, 0.0, -1.0, 1.0, 10.0):               # every tab renders at each A
        at.slider(key="A").set_value(a).run()
        problems += [f"A={a}: {p}" for p in problems_of(at)]
    at.toggle(key="borrow").set_value(True).run()       # leverage branch
    problems += problems_of(at)
    return problems


def check_questionnaire() -> list[str]:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180).run()
    for key, _, _, options in quiz.QUESTIONS:
        at.radio(key=f"q_{key}").set_value(options[1])
    at.button(key="build").click().run()                # BUILD MY PORTFOLIO (form submit)
    problems = problems_of(at)
    expected = quiz.score({k: 2 for k, *_ in quiz.QUESTIONS}).risk_aversion
    if at.session_state["A"] != expected:
        problems.append(f"questionnaire set A = {at.session_state['A']}, expected {expected}")
    return problems


def main() -> int:
    datasets = [name for name, folder in (("SUBMISSION", "submission"), ("LATEST", "latest"))
                if (ROOT / "data" / folder / "metrics.json").exists()]
    failed = False
    q = check_questionnaire()
    print(f"Questionnaire: {'OK' if not q else 'FAILED'}")
    for p in q:
        print("   ", p)
    failed |= bool(q)
    for name in datasets:
        folder = ROOT / "data" / name.lower()
        problems = [f"missing file: {f}" for f in FILES if not (folder / f).exists()]
        problems += check(name) if not problems else []
        print(f"{name}: {'OK' if not problems else 'FAILED'}")
        for p in problems:
            print("   ", p)
        failed |= bool(problems)
    return 1 if failed or not datasets else 0


if __name__ == "__main__":
    sys.exit(main())
