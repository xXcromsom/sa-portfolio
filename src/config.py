"""Load config.yaml and resolve project paths."""
from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    """Return the parsed config. Paths inside it are relative to the project root."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def project_path(relative: str) -> Path:
    """Absolute path for a project-relative path taken from the config."""
    return ROOT / relative
