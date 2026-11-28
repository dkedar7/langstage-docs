# Test your agent in CI

A pull request can break an agent in ways a unit test of your tools won't catch: a
renamed variable breaks the spec, a new import is missing from the requirements, or
someone removes the approval on a tool that moves money. LangStage's preflights catch
these, and with a scripted model they run in CI with no API key and no network.

This page builds one GitHub Actions job that checks, on every pull request, that:

1. the agent loads (`langstage check --json`),
2. one turn runs end to end (`langstage-cli --verify`),
3. a gated tool still stops for approval (exit code `2`),
4. your own assertions hold (`pytest`).

## A model that needs no key

The only part of an agent that needs a key is the model, so swap it for a scripted one
when an environment variable says so. The rest of the agent, its tools, middleware and
prompt, is the real thing.

The scripted model replays fixed replies, tool calls included. Each script is one turn:
`lookup` calls `lookup_order` and answers, `refund` calls `issue_refund`.

<!-- snippet: check file=tests/fake_model.py -->
```python title="tests/fake_model.py"
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage


class ScriptedModel(FakeMessagesListChatModel):
    """Replays a fixed list of replies, tool calls included, in order."""

    def bind_tools(self, tools, **kwargs):
        return self


def call(name, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{name}"}])


SCRIPTS = {
    "lookup": [call("lookup_order", order_id="A-1"), AIMessage(content="Order A-1 shipped on Nov 3.")],
    "refund": [call("issue_refund", order_id="A-1", amount=40.0), AIMessage(content="Refunded $40.00.")],
}


def scripted_model(script: str):
    return ScriptedModel(responses=SCRIPTS[script])
```

`bind_tools` returning the model itself is what lets `create_agent` use it. Add an
empty `tests/__init__.py` so pytest finds `agent.py` from the tests. The agent picks
the scripted model when `AGENT_FAKE_MODEL` names a script:

<!-- snippet: check file=agent.py -->
```python title="agent.py"
import os

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import tool


@tool
def lookup_order(order_id: str) -> str:
    """Look up an order's status."""
    return f"Order {order_id} shipped on Nov 3."


@tool
def issue_refund(order_id: str, amount: float) -> str:
    """Refund part or all of an order."""
    return f"Refunded ${amount:.2f} on {order_id}."


def make_model():
    script = os.environ.get("AGENT_FAKE_MODEL")   # set in CI: no key, no network
    if script:
        from tests.fake_model import scripted_model
        return scripted_model(script)
    return "anthropic:claude-sonnet-5"


graph = create_agent(
    make_model(),
    tools=[lookup_order, issue_refund],
    middleware=[HumanInTheLoopMiddleware(interrupt_on={"issue_refund": True})],
)
```

LangStage puts the agent file's folder on the import path, as `python agent.py` would,
so `tests.fake_model` imports from there.

## The workflow

<!-- snippet: skip -->
```yaml title=".github/workflows/agent.yml"
name: Agent
on: [pull_request]

jobs:
  preflight:
    runs-on: ubuntu-latest
    env:
      AGENT_FAKE_MODEL: lookup
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install langstage langstage-cli langchain pytest

      - name: The agent loads
        run: langstage check --agent agent.py:graph --json | jq -e .ok

      - name: One turn runs
        run: langstage-cli --agent agent.py:graph --verify

      - name: The refund still needs approval
        run: |
          set +e
          AGENT_FAKE_MODEL=refund langstage-cli --agent agent.py:graph 'Refund $40 on A-1'
          test $? -eq 2

      - run: pytest -q
```

What each step tells you:

- **The agent loads.** `langstage check` imports the spec and inspects the graph without
  running a turn. It fails on a bad path, a missing variable or an import error, and
  its JSON has `"ok": true` when the agent loads. The other entries under `checks`
  (Canvas, the Board's task tools) only report which web-app features the agent uses;
  `ok` doesn't depend on them.
- **One turn runs.** `--verify` runs one real turn through the agent and prints
  `✓ agent verified: one turn completed cleanly`. It catches what loading alone
  can't: a tool that raises, a middleware that breaks the message flow, a turn that
  ends with no output.
- **The refund still needs approval.** In CI nothing can answer an approval, so
  `langstage-cli` stops and exits `2`, printing
  `Error: approval required but stdin is not a terminal.` If someone drops
  `issue_refund` from `interrupt_on`, the refund runs, the command exits `0`, and the
  step fails. Don't add `--no-interactive` here: it approves every pending action.
  The `set +e` is needed because GitHub runs each step with `bash -e`.

Use the preflight for the stage you deploy to; they all read the same spec. The
[Installation page](../getting-started/installation.md#preflight-your-own-agent)
lists them, and [Exit codes](../reference/exit-codes.md#what-each-command-returns)
has what each returns. Install only the stages you check: `langstage` for the web
app's `check`, `langstage-cli` for the terminal's `--verify`.

## Your own assertions

For checks on what the agent does, test the graph directly. `verify()` is the same
preflight `--verify` runs, as a function:

<!-- snippet: check file=tests/test_agent.py -->
```python title="tests/test_agent.py"
import importlib

from langstage_core.agui import verify


def fresh_graph(monkeypatch, script):
    """Build the agent again with a scripted model (each script plays once)."""
    monkeypatch.setenv("AGENT_FAKE_MODEL", script)
    import agent
    return importlib.reload(agent).graph


def test_preflight(monkeypatch):
    result = verify(fresh_graph(monkeypatch, "lookup"))
    assert result.ok, result.reason


def test_lookup_answers(monkeypatch):
    out = fresh_graph(monkeypatch, "lookup").invoke({"messages": [("user", "Where is A-1?")]})
    assert "shipped" in out["messages"][-1].content


def test_refund_waits_for_approval(monkeypatch):
    out = fresh_graph(monkeypatch, "refund").invoke({"messages": [("user", "Refund $40 on A-1")]})
    (pause,) = out["__interrupt__"]
    assert pause.value["action_requests"][0]["name"] == "issue_refund"
```

Build a fresh graph for each test. The scripted model keeps its place in the script,
so a second turn on the same graph picks up where the first left off and plays the
wrong replies. Without a checkpointer, `invoke` returns a paused turn's request under
`__interrupt__`, which is the easiest way to assert on it.
[Human-in-the-loop](human-in-the-loop.md) covers the request's shape and how to
answer it.

## A real model, less often

The scripted model proves the wiring, not the prompts. To check that a real model
still uses your tools sensibly, run one live turn on pushes to `main` rather than on
every pull request, with the key from your repository's secrets:

<!-- snippet: skip -->
```yaml
  live:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install langstage langchain langchain-anthropic
      - run: langstage check --agent agent.py:graph --live
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

Add `push: {branches: [main]}` to the workflow's `on:` for this job to run. A missing
or wrong key fails the step with the provider's error; see
[Troubleshooting](../getting-started/troubleshooting.md#no-api-key-it-may-say-connection-error).
