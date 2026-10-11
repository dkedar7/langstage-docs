"""Incident investigator: an on-call assistant that finds a root cause in the logs.

It searches the service and database logs, lines the failures up with the deploy
history and the release diff, proposes the smallest safe fix, and writes an incident
note. Reading is free; changing production config pauses for your approval with
LangGraph's ``interrupt()``, which the terminal shows as an approval menu.

Run it in the terminal (from this folder):

    pip install langstage-cli langchain-anthropic
    export ANTHROPIC_API_KEY=...        # or OPENROUTER_API_KEY=... (pip install langchain-openai)
    cd workspace && langstage-cli --agent ../agent.py:graph

Then ask: "The API started throwing 503s around 2pm. Find the root cause and fix it."
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.types import interrupt


def make_model():
    """Claude Sonnet 5: through OpenRouter when OPENROUTER_API_KEY is set, else directly."""
    if os.environ.get("OPENROUTER_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model="anthropic/claude-sonnet-5",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    return init_chat_model("anthropic:claude-sonnet-5")


ROOT = Path.cwd()  # the on-call workspace: logs/, config/, releases/, deploys.log


def _path(rel: str) -> Path:
    p = (ROOT / rel).resolve()
    if ROOT.resolve() not in p.parents and p != ROOT.resolve():
        raise ValueError(f"{rel} is outside the workspace")
    return p


@tool
def list_files() -> str:
    """List the files in the on-call workspace, with their sizes in lines."""
    out = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(ROOT).parts):
            n = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
            out.append(f"{p.relative_to(ROOT).as_posix()}  ({n} lines)")
    return "\n".join(out)


@tool
def search(pattern: str, path: str, max_matches: int = 15) -> str:
    """Search a file with a regular expression (case-insensitive).

    Returns the total number of matching lines, the first and last match, and up to
    ``max_matches`` matching lines with their line numbers.
    """
    lines = _path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    rx = re.compile(pattern, re.IGNORECASE)
    hits = [(i + 1, line) for i, line in enumerate(lines) if rx.search(line)]
    if not hits:
        return f"0 matches for /{pattern}/ in {path}."
    shown = hits[:max_matches]
    head = f"{len(hits)} matches for /{pattern}/ in {path}. First: line {hits[0][0]}. Last: line {hits[-1][0]}."
    return head + "\n" + "\n".join(f"{n}: {line}" for n, line in shown)


@tool
def read_file(path: str, start_line: int = 1, end_line: int | None = None) -> str:
    """Read a file, or a range of its lines (at most 120 lines at a time)."""
    lines = _path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    end = min(end_line or len(lines), start_line + 119, len(lines))
    return "\n".join(f"{n}: {lines[n - 1]}" for n in range(start_line, end + 1))


def _set_yaml_value(text: str, dotted: str, value: object) -> str:
    """Set ``section.key`` in a simple two-level YAML file, keeping comments."""
    section, key = dotted.split(".", 1)
    out, in_section, done = [], False, False
    for line in text.splitlines():
        if re.match(rf"^{re.escape(section)}:\s*$", line):
            in_section = True
        elif re.match(r"^\S", line):
            in_section = False
        m = re.match(rf"^(\s+){re.escape(key)}:\s*\S.*$", line)
        if in_section and m and not done:
            line, done = f"{m.group(1)}{key}: {value}", True
        out.append(line)
    if not done:
        raise KeyError(dotted)
    return "\n".join(out) + "\n"


@tool
def apply_config_change(path: str, changes: dict[str, int | float | str], reason: str) -> str:
    """Change production config values, e.g. {"db.pool_size": 20}. Needs approval.

    Keys are ``section.key``. The change pauses for the on-call engineer's approval
    and is applied only if they approve (or edit) it.
    """
    target = _path(path)
    text = target.read_text(encoding="utf-8")
    answer = interrupt({
        "action_requests": [{
            "name": "apply_config_change",
            "args": {"path": path, "changes": changes, "reason": reason},
            "description": f"Change production config {path}: "
                           + ", ".join(f"{k} -> {v}" for k, v in changes.items()),
        }],
        "review_configs": [
            {"action_name": "apply_config_change", "allowed_decisions": ["approve", "edit", "reject"]}
        ],
    })
    decisions = answer.get("decisions", []) if isinstance(answer, dict) else answer or []
    decision = decisions[0] if decisions else {}
    if decision.get("type") == "reject":
        return f"The on-call engineer rejected the change ({decision.get('message') or 'no reason given'})."
    if decision.get("type") == "edit":
        changes = decision["edited_action"]["args"].get("changes", changes)
    elif decision.get("type") != "approve":
        return f"Not applied: unexpected decision {decision!r}."
    for dotted, value in changes.items():
        text = _set_yaml_value(text, dotted, value)
    target.write_text(text, encoding="utf-8")
    with (ROOT / "deploys.log").open("a", encoding="utf-8") as fh:
        fh.write(f'2026-10-11 14:41:07 config api {path} by=on-call "{reason}"\n')
    return f"Applied to {path}: " + ", ".join(f"{k}={v}" for k, v in changes.items()) + ". Rolling restart started."


@tool
def write_incident_note(title: str, body: str) -> str:
    """Write the incident note (markdown) to incidents/."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    out = ROOT / "incidents" / f"2026-10-11-{slug}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")
    return f"Wrote {out.relative_to(ROOT).as_posix()}."


SYSTEM_PROMPT = """You are the on-call assistant for the orders API. It is October 11, 2026,
about 14:40. You have the service logs, the database logs, the deploy history, the
release diffs and the production config in the workspace.

Investigate before you act: find when the errors started and what they say, line them
up with the deploy history and the release diff, and confirm the cause with evidence
(timestamps, counts, the exact config lines). Search the logs; don't read them whole.

Then fix it with the smallest safe change, through apply_config_change (it asks the
on-call engineer to approve), and write a short incident note with the timeline, the
root cause, the fix and one follow-up.

You're talking in a terminal: keep messages short and plain. Narrate in one line
before each step. End with three or four lines: cause, fix, follow-up."""

graph = create_agent(
    make_model(),
    tools=[list_files, search, read_file, apply_config_change, write_incident_note],
    system_prompt=SYSTEM_PROMPT,
    name="On-call",
).with_config(recursion_limit=60)
