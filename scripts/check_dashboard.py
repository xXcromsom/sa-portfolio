"""Render every dashboard tab headlessly and fail if anything raises or a figure is missing.

Run before committing refreshed data (the nightly workflow does) and after freezing:
    python scripts/check_dashboard.py            # each dataset that exists
"""
from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ["sml", "frontier", "indifference", "mc_fan", "mc_hist", "sip", "ta", "corr_heatmap", "rolling_corr",
           "risk_contrib", "stress", "sentiment", "event_study"]


def check(dataset: str | None) -> list[str]:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    if dataset and at.sidebar.radio[0].value != dataset:
        at.sidebar.radio[0].set_value(dataset).run()
    problems = [f"exception: {e.message}" for e in at.exception]
    problems += [f"info box: {i.value}" for i in at.info if "not available" in i.value]
    return problems


def main() -> int:
    datasets = [name for name, folder in (("Submission (frozen)", "submission"), ("Latest", "latest"))
                if (ROOT / "data" / folder / "metrics.json").exists()]
    failed = False
    for name in datasets:
        folder = ROOT / "data" / ("submission" if name.startswith("Submission") else "latest")
        missing = [f for f in FIGURES if not (folder / "figures" / f"{f}.png").exists()]
        problems = check(name) + [f"missing figure: {f}.png" for f in missing]
        print(f"{name}: {'OK' if not problems else 'FAILED'}")
        for p in problems:
            print("   ", p)
        failed |= bool(problems)
    return 1 if failed or not datasets else 0


if __name__ == "__main__":
    sys.exit(main())
