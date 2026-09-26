"""Track which LangStage releases the committed demos were recorded against.

    python demos/scripts/versions.py write   # record installed versions -> versions.json
    python demos/scripts/versions.py check   # exit 0 and print changed=true|false comparing
                                             # the latest PyPI releases to versions.json

The demos workflow runs `check` after the nightly drift detector and only re-records
when a release moved, so the refresh PR carries a real change instead of re-encoded noise.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from importlib import metadata
from pathlib import Path

PACKAGES = ["langstage-core", "langstage", "langstage-cli", "langstage-jupyter", "langstage-hermes"]
MANIFEST = Path(__file__).resolve().parents[2] / "docs" / "assets" / "demos" / "versions.json"


def latest(pkg: str) -> str:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=20) as r:
        return json.load(r)["info"]["version"]


def write() -> None:
    versions = {pkg: metadata.version(pkg) for pkg in PACKAGES}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"recorded_against": versions}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.name}: {versions}")


def check() -> None:
    recorded = {}
    if MANIFEST.exists():
        recorded = json.loads(MANIFEST.read_text(encoding="utf-8")).get("recorded_against", {})
    now = {pkg: latest(pkg) for pkg in PACKAGES}
    moved = {p: f"{recorded.get(p)} -> {v}" for p, v in now.items() if recorded.get(p) != v}
    for pkg, change in moved.items():
        print(f"{pkg}: {change}")
    changed = "true" if moved else "false"
    print(f"changed={changed}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"changed={changed}\n")


if __name__ == "__main__":
    {"write": write, "check": check}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
