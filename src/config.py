"""Load config.yaml and resolve project paths."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")

# If a custom CA bundle is configured (antivirus HTTPS scanning, see README), point
# the standard variables at it too, so requests/httpx-based libraries such as
# huggingface_hub verify against the same roots.
if os.getenv("CA_BUNDLE"):
    _ca = Path(os.environ["CA_BUNDLE"])
    _ca = _ca if _ca.is_absolute() else ROOT / _ca
    for _var in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
        os.environ.setdefault(_var, str(_ca))


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    """Return the parsed config. Paths inside it are relative to the project root."""
    import yaml  # here, so the dashboard can import this module (for .env) without PyYAML

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def project_path(relative: str) -> Path:
    """Absolute path for a project-relative path taken from the config."""
    return ROOT / relative
