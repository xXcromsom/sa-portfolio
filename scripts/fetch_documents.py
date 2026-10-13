"""Download the PDFs listed in documents.yaml into data/raw/<ticker>/.

Skips files already on disk. A download is accepted only if it really is a PDF,
and data/raw/manifest.json records its size and SHA-256.

    python scripts/fetch_documents.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import project_path  # noqa: E402  (also loads .env)

RAW = ROOT / "data" / "raw"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.bseindia.com/"}


def verify_path() -> str | bool:
    ca = os.getenv("CA_BUNDLE")
    return str(project_path(ca)) if ca else True


def fetch(url: str, dest: Path) -> dict:
    r = requests.get(url, headers=HEADERS, verify=verify_path(), timeout=120)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise ValueError(f"{url} did not return a PDF (got {r.headers.get('content-type')})")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return {"url": url, "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest()}


def main() -> None:
    docs = yaml.safe_load((ROOT / "documents.yaml").read_text(encoding="utf-8"))
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    failures = []
    for ticker, kinds in docs.items():
        for kind, items in kinds.items():
            for label, url in items.items():
                dest = RAW / ticker / f"{kind}_{label}.pdf"
                key = str(dest.relative_to(RAW)).replace("\\", "/")
                if dest.exists():
                    continue
                try:
                    manifest[key] = fetch(url, dest)
                    print(f"ok   {key} ({manifest[key]['bytes'] / 1e6:.1f} MB)")
                except Exception as e:  # report every failure, then exit non-zero
                    failures.append(key)
                    print(f"FAIL {key}: {type(e).__name__}: {str(e)[:120]}")
                time.sleep(1.5)  # be polite to BSE
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if failures:
        sys.exit(f"{len(failures)} downloads failed: {failures}")
    print("all documents present")


if __name__ == "__main__":
    main()
