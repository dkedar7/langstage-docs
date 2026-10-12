#!/usr/bin/env python3
"""Check that links into this repository point at files that exist.

A page often links to a file in this repo on GitHub (an example agent, a recorder):
``https://github.com/dkedar7/langstage-docs/blob/main/<path>`` or ``/tree/main/<path>``.
The link checker (lychee) can't check those on a pull request that adds the file,
because the file isn't on ``main`` until the PR merges, so lychee.toml skips them and
this script checks them against the checkout instead.

    python scripts/self_links.py        # exit 1 and list any link to a missing path
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LINK = re.compile(
    r"https://(?:github\.com/dkedar7/langstage-docs/(?:blob|tree)|"
    r"raw\.githubusercontent\.com/dkedar7/langstage-docs)/main/([^\s)\"'#>]+)"
)


def main() -> int:
    missing = []
    checked = 0
    for page in sorted((REPO / "docs").rglob("*.md")):
        for n, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            for match in LINK.finditer(line):
                checked += 1
                target = match.group(1).rstrip("/.,")
                if not (REPO / target).exists():
                    missing.append(f"{page.relative_to(REPO)}:{n}: {target}")
    for m in missing:
        print(f"missing: {m}")
    print(f"{checked} links into this repo checked, {len(missing)} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
