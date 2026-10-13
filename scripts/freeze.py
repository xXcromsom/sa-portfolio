"""Freeze the numbers that go in the report: copy data/latest to data/submission.

The dashboard's default dataset is the frozen copy, so what the professor opens matches
the report even after the nightly refresh moves data/latest on.
    python scripts/freeze.py                 # refuses if a frozen copy already exists
    python scripts/freeze.py --force         # replace it (e.g. a corrected resubmission)
Then commit and tag, as the script prints.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEST, FROZEN = ROOT / "data" / "latest", ROOT / "data" / "submission"


def main(force: bool) -> int:
    if FROZEN.exists() and not force:
        print(f"{FROZEN} already exists. Pass --force to replace it.")
        return 1
    as_of = json.loads((LATEST / "metrics.json").read_text(encoding="utf-8"))["as_of"]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip() or None
    if FROZEN.exists():
        shutil.rmtree(FROZEN)
    shutil.copytree(LATEST, FROZEN)
    manifest = {"frozen_at": datetime.now().isoformat(timespec="seconds"), "data_as_of": as_of,
                "code_commit": commit, "files": sorted(str(p.relative_to(FROZEN)).replace("\\", "/")
                                                      for p in FROZEN.rglob("*") if p.is_file())}
    (FROZEN / "FROZEN.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Froze data as of {as_of} ({len(manifest['files'])} files) into {FROZEN.relative_to(ROOT)}.")
    print("Next:\n  python scripts/check_dashboard.py\n  git add data/submission && "
          f'git commit -m "Freeze submission data ({as_of})"\n  git tag submission-v1 && git push --tags')
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="replace an existing frozen copy")
    sys.exit(main(parser.parse_args().force))
