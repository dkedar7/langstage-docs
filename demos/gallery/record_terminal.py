"""Record a real terminal session with langstage-cli as an asciinema v2 cast.

Drives the CLI in a pseudo-terminal with pexpect (so Linux or macOS, or WSL on
Windows), types like a person, answers the approval menu, and writes every byte the
CLI prints, with its timestamp, to a ``.cast`` file. ``render_cast.py`` turns the cast
into the gallery's video.

    OPENROUTER_API_KEY=... python demos/gallery/record_terminal.py incident-investigator out.cast
"""
from __future__ import annotations

import json
import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pexpect

REPO = Path(__file__).resolve().parents[2]
COLS, ROWS = 108, 30
SCRIPTS = {
    "incident-investigator": {
        "question": "The API started throwing 503s around 2pm. Find the root cause and fix it.",
        "after": "grep -n pool config/api.yaml && ls incidents",
    },
}


class Cast:
    """Collects (time, data) output events into an asciinema v2 file."""

    def __init__(self) -> None:
        self.t0 = time.monotonic()
        self.events: list[tuple[float, str]] = []

    def write(self, data: str) -> None:
        self.events.append((time.monotonic() - self.t0, data))

    def flush(self) -> None:  # pexpect logfile protocol
        pass

    def save(self, path: Path, title: str) -> None:
        from importlib import metadata

        versions = {}
        for name in ("langstage-cli", "langstage-core"):
            try:
                versions[name] = metadata.version(name)
            except metadata.PackageNotFoundError:
                pass
        header = {"version": 2, "width": COLS, "height": ROWS, "title": title,
                  "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
                  "langstage_versions": versions}  # what recorded it, for versions.json
        with path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(header) + "\n")
            for t, data in self.events:
                fh.write(json.dumps([round(t, 4), "o", data]) + "\n")


def type_slowly(child: pexpect.spawn, text: str) -> None:
    for ch in text:
        child.send(ch)
        time.sleep(random.uniform(0.03, 0.07))


def main() -> None:
    example, out = sys.argv[1], Path(sys.argv[2])
    script = SCRIPTS[example]
    # The example's own layout, the one its page tells readers to run: agent.py next to
    # workspace/, started from inside workspace/ (so no local paths show on screen).
    tmp = Path(tempfile.gettempdir()) / example
    shutil.rmtree(tmp, ignore_errors=True)
    ws = tmp / "workspace"
    shutil.copytree(REPO / "gallery" / example / "workspace", ws)
    shutil.copy(REPO / "gallery" / example / "agent.py", tmp / "agent.py")
    env = {**os.environ, "TERM": "xterm-256color", "COLUMNS": str(COLS), "LINES": str(ROWS),
           "PYTHONIOENCODING": "utf-8", "LANGSTAGE_SUPPRESS_LEGACY_NOTICE": "1",
           "PS1": "\\[\\e[38;5;111m\\]on-call\\[\\e[0m\\] $ "}
    cast = Cast()
    child = pexpect.spawn("bash", ["--norc", "--noprofile"], cwd=str(ws), env=env, encoding="utf-8",
                          dimensions=(ROWS, COLS), timeout=600)
    child.logfile_read = cast
    try:
        run(child, script)
    except Exception:
        cast.save(out.with_suffix(".partial.cast"), f"langstage-cli: {example} (failed)")
        print("FAILED; last output:", repr((child.before or "")[-1500:]))
        raise
    cast.save(out, f"langstage-cli: {example}")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {out} ({len(cast.events)} events, {cast.events[-1][0]:.0f}s)")


def run(child: pexpect.spawn, script: dict) -> None:
    child.expect(r"\$ ")
    time.sleep(0.8)
    type_slowly(child, "langstage-cli --agent ../agent.py:graph")
    time.sleep(0.4)
    child.send("\r")
    child.expect("❯", timeout=120)  # the REPL prompt
    time.sleep(1.2)
    type_slowly(child, script["question"])
    time.sleep(0.6)
    child.send("\r")
    child.expect("How would you like to proceed", timeout=300)
    child.expect("Exit")  # the whole menu is drawn (its cursor is a ❯ too)
    time.sleep(5.0)  # read the request
    child.send("\r")  # the first option: approve all
    # The turn ends with its duration ("41.2s" / "1m 3.5s") and then the prompt.
    child.expect(r"\n\S*(\d+m )?\d+(\.\d)?m?s\S*\s*\r?\n", timeout=600)
    child.expect("❯", timeout=60)
    time.sleep(3.0)
    type_slowly(child, "/q")
    child.send("\r")
    child.expect(r"\$ ", timeout=60)
    time.sleep(0.8)
    type_slowly(child, script["after"])
    child.send("\r")
    child.expect(r"\$ ", timeout=30)
    time.sleep(3.0)
    child.logfile_read = None  # the recording ends on the result, not on `exit`
    child.sendline("exit")
    child.expect(pexpect.EOF, timeout=30)


if __name__ == "__main__":
    main()
