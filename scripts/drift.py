#!/usr/bin/env python3
"""Detect when the six LangStage packages have moved past what the docs cover.

versions.json records the package versions the docs were last verified against.

    python scripts/drift.py check [--out drift.json] [--constraints c.txt]
        Query PyPI. Print what moved; write drift.json and a pip constraints
        file pinning the latest releases. Sets `drift=true|false` in
        $GITHUB_OUTPUT when run in Actions.

    python scripts/drift.py issue --drift drift.json [--snippets results.json]
                                  [--run-url URL] [--dry-run]
        Open, or update in place, the single open "Docs sync needed" issue in
        this repo (label: docs-sync). Uses `gh` with GITHUB_TOKEN; never opens a
        second issue while one is open. With no drift, closes that issue.

    python scripts/drift.py bump [pkg=version ...]
        After syncing the docs: record the latest PyPI releases (or the given
        versions) in versions.json. Commit it with the doc changes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = ROOT / "versions.json"
OWNER = "dkedar7"
LABEL = "docs-sync"
TITLE_PREFIX = "Docs sync needed"


def http_get(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "langstage-docs-drift"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except Exception as exc:  # network errors are reported, not fatal, for changelogs
        print(f"warning: GET {url} failed: {exc}", file=sys.stderr)
        return None


def vkey(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def is_final(v: str) -> bool:
    return re.fullmatch(r"\d+(\.\d+)*", v) is not None


def pypi(pkg: str) -> dict:
    raw = http_get(f"https://pypi.org/pypi/{pkg}/json")
    if raw is None:
        raise SystemExit(f"error: could not reach PyPI for {pkg}")
    return json.loads(raw)


def load_versions() -> dict:
    return json.loads(VERSIONS.read_text(encoding="utf-8"))


def save_versions(data: dict) -> None:
    VERSIONS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def github_slug(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def changelog_links(pkg: str, versions: list[str]) -> list[str]:
    """Markdown links to each version's section of the repo's CHANGELOG.md."""
    base = f"https://github.com/{OWNER}/{pkg}/blob/main/CHANGELOG.md"
    raw = http_get(f"https://raw.githubusercontent.com/{OWNER}/{pkg}/main/CHANGELOG.md")
    headings = []
    if raw:
        headings = [m.group(1) for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", raw.decode("utf-8", "replace"))]
    out = []
    for v in versions:
        h = next((h for h in headings if re.search(rf"(?<![\d.]){re.escape(v)}(?![\d.])", h)), None)
        out.append(f"[{v}]({base}#{github_slug(h)})" if h else f"{v} ([CHANGELOG]({base}), no section found)")
    return out


def cmd_check(args) -> int:
    pinned = load_versions()["packages"]
    drift, latest_all = [], {}
    for pkg, old in pinned.items():
        info = pypi(pkg)
        latest = info["info"]["version"]
        latest_all[pkg] = latest
        if vkey(latest) > vkey(old):
            between = sorted((v for v in info["releases"] if is_final(v) and vkey(old) < vkey(v) <= vkey(latest)),
                             key=vkey)
            drift.append({"package": pkg, "old": old, "new": latest, "releases": between,
                          "changelog": changelog_links(pkg, list(reversed(between)))})
            print(f"{pkg}: {old} -> {latest}  ({len(between)} release(s))")
        else:
            print(f"{pkg}: {old} (current)")
    result = {"drift": drift, "latest": latest_all}
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.constraints:
        Path(args.constraints).write_text("".join(f"{p}=={v}\n" for p, v in latest_all.items()),
                                          encoding="utf-8")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"drift={'true' if drift else 'false'}\n")
    print("drift detected" if drift else "no drift: the docs cover the latest releases")
    return 0


def issue_title(drift: list[dict]) -> str:
    return f"{TITLE_PREFIX}: " + ", ".join(f"{d['package']} {d['old']}→{d['new']}" for d in drift)


def issue_body(drift: list[dict], snippets: dict | None, run_url: str | None, repo: str) -> str:
    lines = [
        "The docs were last verified against the versions in "
        f"[`versions.json`](https://github.com/{repo}/blob/main/versions.json). PyPI has moved on:",
        "",
        "| Package | Docs verified | Latest | Changelog |",
        "|---|---|---|---|",
    ]
    for d in drift:
        lines.append(f"| [`{d['package']}`](https://pypi.org/project/{d['package']}/) | {d['old']} | "
                     f"**{d['new']}** | {', '.join(d['changelog'])} |")
    lines += ["", "### Snippets against the new releases", ""]
    if snippets is None:
        lines.append("_The snippet run did not produce results; see the workflow run._")
    else:
        c = snippets["counts"]
        lines.append(f"{c['run']} run, {c['check']} check, {c['skip']} skip: "
                     f"**{snippets['failing']} failing**.")
        for f in snippets["failures"]:
            detail = f["detail"].strip()[-2500:]
            lines += ["", f"<details><summary><code>{f['where']}</code> ({f['mode']}, {f['lang']})</summary>",
                      "", "```text", detail, "```", "</details>"]
    if run_url:
        lines += ["", f"Workflow run: {run_url}"]
    lines += [
        "",
        "### To close this",
        "",
        "1. Read the changelog sections above; update the pages they affect "
        "(new flags, renamed APIs, changed output, changed exit codes).",
        "2. Fix or re-mark any failing snippet (see *How the docs stay current* in the README).",
        "3. `python scripts/drift.py bump` and commit `versions.json` in the same PR.",
        "4. Merge. The next nightly run finds no drift and closes this issue.",
        "",
        "<!-- docs-sync-bot: this issue is updated in place by .github/workflows/drift.yml -->",
    ]
    return "\n".join(lines) + "\n"


def gh(*args: str, input: str | None = None) -> str:
    cp = subprocess.run(["gh", *args], capture_output=True, text=True, input=input,
                        encoding="utf-8")
    if cp.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout


def open_sync_issues(repo: list[str]) -> list[dict]:
    found = json.loads(gh("issue", "list", "--state", "open", "--label", LABEL,
                          "--json", "number,title", "--limit", "20", *repo))
    found += [i for i in json.loads(gh("issue", "list", "--state", "open", "--search",
                                       f'"{TITLE_PREFIX}" in:title', "--json", "number,title",
                                       "--limit", "20", *repo))
              if i["title"].startswith(TITLE_PREFIX) and i not in found]
    return found


def cmd_issue(args) -> int:
    drift = json.loads(Path(args.drift).read_text(encoding="utf-8"))["drift"]
    repo_name = args.repo or os.environ.get("GITHUB_REPOSITORY") or f"{OWNER}/langstage-docs"
    repo = ["--repo", repo_name]
    if not drift:
        if args.dry_run:
            print("no drift; would close any open docs-sync issue")
            return 0
        for i in open_sync_issues(repo):
            gh("issue", "close", str(i["number"]), "--comment",
               "`versions.json` now matches the latest PyPI releases. Closing.", *repo)
            print(f"closed issue #{i['number']}")
        print("no drift; nothing to file")
        return 0
    snippets = None
    if args.snippets and Path(args.snippets).exists():
        snippets = json.loads(Path(args.snippets).read_text(encoding="utf-8"))
    title, body = issue_title(drift), issue_body(drift, snippets, args.run_url, repo_name)
    if args.dry_run:
        print(f"TITLE: {title}\n\n{body}")
        return 0
    gh("label", "create", LABEL, "--color", "D93F0B", "--force",
       "--description", "The docs need a sync with new package releases", *repo)
    existing = open_sync_issues(repo)
    if existing:
        num = str(min(i["number"] for i in existing))
        old_title = next(i["title"] for i in existing if str(i["number"]) == num)
        gh("issue", "edit", num, "--title", title, "--body-file", "-", "--add-label", LABEL, *repo,
           input=body)
        if old_title != title:
            gh("issue", "comment", num, "--body",
               f"New releases since the last update: now **{title[len(TITLE_PREFIX) + 2:]}**. "
               "The issue body is updated.", *repo)
        print(f"updated issue #{num}")
    else:
        url = gh("issue", "create", "--title", title, "--body-file", "-", "--label", LABEL, *repo,
                 input=body).strip()
        print(f"opened {url}")
    return 0


def cmd_bump(args) -> int:
    data = load_versions()
    pkgs = data["packages"]
    explicit = dict(a.split("=", 1) for a in args.pins)
    for name in explicit:
        if name not in pkgs:
            raise SystemExit(f"error: unknown package {name!r}; known: {', '.join(pkgs)}")
    for pkg in pkgs:
        new = explicit.get(pkg) or (None if explicit else pypi(pkg)["info"]["version"])
        if new and new != pkgs[pkg]:
            print(f"{pkg}: {pkgs[pkg]} -> {new}")
            pkgs[pkg] = new
    save_versions(data)
    print(f"wrote {VERSIONS.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--out")
    c.add_argument("--constraints")
    i = sub.add_parser("issue")
    i.add_argument("--drift", required=True)
    i.add_argument("--snippets")
    i.add_argument("--run-url")
    i.add_argument("--repo", help="owner/name (default: the current repo)")
    i.add_argument("--dry-run", action="store_true")
    b = sub.add_parser("bump")
    b.add_argument("pins", nargs="*", metavar="pkg=version")
    args = ap.parse_args()
    return {"check": cmd_check, "issue": cmd_issue, "bump": cmd_bump}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
