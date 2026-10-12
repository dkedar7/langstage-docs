"""Sales analyst: answers questions about a sales CSV with code, charts and a report.

It runs Python in a persistent session (pandas, Plotly), shows each chart inline in
the chat, and builds a short written report on LangStage's Canvas. The notebook
session, the inline display and the Canvas come from the `langstage` package; the
agent is a plain LangChain agent.

Run it (from this folder):

    pip install langstage langchain-anthropic pandas plotly
    export ANTHROPIC_API_KEY=...        # or OPENROUTER_API_KEY=... (pip install langchain-openai)
    langstage run --agent agent.py:graph --workspace workspace

Then ask: "What drove Q3? Anything I should worry about? Put the findings on the canvas."
"""

from __future__ import annotations

import os

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langstage.middleware import CanvasMiddleware
from langstage.tools import create_cell, display_inline, execute_cell


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


@tool
def run_python(code: str) -> dict:
    """Run Python in the analysis session and return its output.

    The session persists like a notebook: imports, variables and DataFrames from
    earlier calls stay defined. pandas and plotly are installed. Returns stdout, the
    value of the last expression, and the traceback if it failed.
    """
    cell = create_cell(code)  # LangStage's notebook session: one cell per call
    out = execute_cell(cell["index"])
    return {k: out[k] for k in ("status", "stdout", "result", "error") if out.get(k)}


SYSTEM_PROMPT = """You are a senior data analyst at Northwind Outfitters, an outdoor gear retailer.
The workspace holds `sales.csv`: one row per week x region x channel x category, with
`units`, `revenue` and `returned_units`. `week` is the Monday the week starts. The data
runs from October 2025 to September 2026. Quarters are calendar quarters: Q3 is
July to September 2026, compared with Q2 (April to June).

Analyze with run_python. Load the data once and reuse the DataFrame; do several
computations per call rather than one per call, and print compact tables.

Charts: build them with Plotly (plotly.express), use a clean template ("simple_white"),
title them with the finding, not the metric, and save each one with
`fig.write_json("charts/<name>.json")` (make the folder first; don't export images).
Show it in the chat with display_inline("charts/<name>.json"), and add it to the
canvas with add_to_canvas("charts/<name>.json", ...).

When a metric moves, find where before you explain why: break it down by region,
channel and week, and say whether the change is broad or concentrated. Don't claim a
pattern holds everywhere without checking each slice.

Be quantitative and brief. Lead with the answer. Quote numbers with units and the
comparison period ("+12% vs Q2"). Flag anything that looks wrong and say what you'd
check next. Two to four charts is plenty; don't chart what one sentence can say."""

graph = create_agent(
    make_model(),
    tools=[run_python, display_inline],
    middleware=[CanvasMiddleware()],
    system_prompt=SYSTEM_PROMPT,
    name="Northwind Analyst",
).with_config(recursion_limit=80)  # an analysis plus a report takes more than LangGraph's default 25 steps
