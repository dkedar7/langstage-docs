"""Track which LangStage releases the committed demos were recorded against.

    python demos/scripts/versions.py write   # record installed versions -> versions.json
    python demos/scripts/versions.py check   # exit 0 and print changed=true|false comparing
                                             # the latest PyPI releases to versions.json

The demos workflow runs `check` after the nightly drift detector and only re-records
when a release moved, so the refresh PR carries a real change instead of re-encoded noise.

Besides the PyPI packages it tracks the VS Code extension's GitHub release tag
(`extension-v*` on dkedar7/langstage-vscode) that the vscode demo was recorded from:
demos/build.sh exports LANGSTAGE_VSCODE_REF when it checks that tag out.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from importlib import metadata
from pathlib import Path

PACKAGES = ["langstage-core", "langstage", "langstage-cli", "langstage-jupyter", "langstage-hermes",
            "langstage-vscode"]
EXTENSION = "langstage-vscode-extension"
EXTENSION_REPO = "https://github.com/dkedar7/langstage-vscode"
MANIFEST = Path(__file__).resolve().parents[2] / "docs" / "assets" / "demos" / "versions.json"


def latest(pkg: str) -> str:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=20) as r:
        return json.load(r)["info"]["version"]


def latest_extension() -> str | None:
    """The newest `extension-v*` release tag of the VS Code extension (None if unreachable)."""
    try:
        out = subprocess.run(["git", "ls-remote", "--tags", "--refs", EXTENSION_REPO, "extension-v*"],
                             capture_output=True, text=True, timeout=30, check=True).stdout
    except Exception as exc:
        print(f"warning: could not list {EXTENSION_REPO} tags: {exc}", file=sys.stderr)
        return None
    tags = [line.rsplit("refs/tags/", 1)[1] for line in out.splitlines() if "refs/tags/" in line]
    return max(tags, key=lambda t: tuple(int(x) for x in re.findall(r"\d+", t)), default=None)


def recorded() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8")).get("recorded_against", {})
    return {}


def write() -> None:
    versions = {}
    for pkg in PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            pass
    # The extension tag the vscode demo came from: this build's, else the previous one.
    ref = os.environ.get("LANGSTAGE_VSCODE_REF") or recorded().get(EXTENSION)
    if ref:
        versions[EXTENSION] = ref
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"recorded_against": versions}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.name}: {versions}")


def check() -> None:
    was = recorded()
    now = {pkg: latest(pkg) for pkg in PACKAGES}
    ext = latest_extension()
    if ext:
        now[EXTENSION] = ext
    moved = {p: f"{was.get(p)} -> {v}" for p, v in now.items() if was.get(p) != v}
    for pkg, change in moved.items():
        print(f"{pkg}: {change}")
    changed = "true" if moved else "false"
    print(f"changed={changed}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"changed={changed}\n")


if __name__ == "__main__":
    {"write": write, "check": check}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
