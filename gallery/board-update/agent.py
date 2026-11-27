"""Board update co-author: drafts a quarterly update from the numbers, in Codraft.

You write the outline and the ask; the agent drafts the sections from the quarter's
metrics and the operations notes. Everything it writes arrives as a suggestion on the
page, which you accept or reject. When finance corrects a figure, leave a comment and
the agent proposes the edit. A checkpoint ("Sent to finance") lets you see, and export
as a Word redline, exactly what changed since.

Run it in Codraft (from this folder):

    pip install langstage-codraft langchain-anthropic
    export ANTHROPIC_API_KEY=...        # or OPENROUTER_API_KEY=... (pip install langchain-openai)
    langstage-codraft run --agent agent.py:graph

Then make a document with headings for Results and Returns, and ask: "Draft a short
paragraph under Results and one under Returns from the Q3 numbers and the ops notes."
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langstage_codraft import CodraftMiddleware


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


# The source material sits next to this file, so it works from any directory.
DATA = Path(__file__).resolve().parent / "workspace"


@tool
def read_metrics() -> str:
    """The quarter's metrics as JSON: revenue, orders, returns, NPS, top categories.

    Each figure is given for this quarter and a comparison quarter. A ``note`` on a
    figure says when it is preliminary.
    """
    return (DATA / "metrics.json").read_text(encoding="utf-8")


@tool
def read_ops_notes() -> str:
    """The operations team's notes for this update: what drove the numbers and the fix
    they want the board to approve."""
    return (DATA / "ops-notes.md").read_text(encoding="utf-8")


@tool
def percent_change(old: float, new: float) -> str:
    """The change from ``old`` to ``new`` in percent, rounded to one decimal place."""
    if old == 0:
        return "undefined (old value is 0)"
    return f"{(new - old) / old * 100:+.1f}%"


INSTRUCTIONS = f"""\
You help the founders of {json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))["company"]}
write their quarterly update for the board.

- Take every figure from read_metrics or read_ops_notes, and every percentage change
  from percent_change. Never estimate a number. If a figure is marked preliminary,
  say so in the text.
- The board reads this in five minutes. Short paragraphs, the number first, then what
  it means. No headings of your own, no bullet lists unless asked.
- The authors wrote the outline, the opening and the ask. Draft only the sections you
  are asked for, under the heading they belong to, and leave the authors' paragraphs
  alone unless a comment asks you to change one.
- When a comment corrects a figure, change that figure and any sentence that depends on
  it, and nothing else.
"""

graph = create_agent(
    make_model(),
    tools=[read_metrics, read_ops_notes, percent_change],
    middleware=[CodraftMiddleware(extra_prompt=INSTRUCTIONS)],
    name="Juniper",
)
