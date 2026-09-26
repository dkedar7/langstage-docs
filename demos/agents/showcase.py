"""The keyless rich-frame demo agent, tidied for recordings.

This is ``langstage_core.demo.tools:graph`` (tool call, reasoning, interrupt; no API
key, no network) with one cosmetic change: the web app and the JupyterLab sidebar
add host context to every message (the web app prepends ``[Current time: ...]`` /
``[Working directory: ...]`` lines; JupyterLab appends a ``Currently focused: ...``
paragraph), and the stock demo tool echoes the whole message back as its query. In
a recording that prints the runner's temp path into the reply. Here the demo agent
sees only what was typed: leading bracketed lines are dropped and only the first
paragraph is kept.

If a future langstage-core renames the private helper this patches, the recorder
still works: it falls back to the stock demo agent unchanged.

Spec: ``demos/agents/showcase.py:graph``
"""
from __future__ import annotations

import re

import langstage_core.demo.tools as _tools

_CONTEXT_LINE = re.compile(r"^\s*\[[^\]]*\]\s*$")
_original = getattr(_tools, "_last_human_text", None)

if _original is not None:

    def _without_host_context(messages):
        lines = _original(messages).splitlines()
        while lines and (not lines[0].strip() or _CONTEXT_LINE.match(lines[0])):
            lines.pop(0)
        return "\n".join(lines).split("\n\n", 1)[0].strip()

    _tools._last_human_text = _without_host_context

graph = _tools.create_tool_demo_agent(name="Demo Agent")
