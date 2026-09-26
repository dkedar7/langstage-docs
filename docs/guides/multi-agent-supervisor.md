# Running a multi-agent supervisor in LangStage

LangStage runs **any** compiled LangGraph graph. A single ReAct agent, a
supervisor that routes between specialists, a swarm, a crew, an arbitrary graph
of subgraphs — they all compile to the same `CompiledStateGraph`, and every
LangStage stage serves that type through the *same* spec string. So "multi-agent"
isn't a separate mode or a different API: if your graph compiles, LangStage runs
it, and supervisor routing and sub-agent hand-offs stream just like a single
agent.

!!! info "LangStage operates your graph — it doesn't author it"
    The orchestration (who calls whom, how state is routed) lives in **your**
    LangGraph graph, using LangGraph's own primitives. LangStage is the operate
    layer: it loads the compiled graph and gives it a web/terminal/notebook/editor
    stage. This page shows you wiring *your* supervisor to LangStage — not a
    LangStage-specific orchestration framework.

## 1. Build a supervisor (standard LangGraph)

This is ordinary LangGraph code — nothing LangStage-specific. Here we use
[`langgraph-supervisor`](https://github.com/langchain-ai/langgraph-supervisor-py),
the prebuilt supervisor, with two worker agents built by LangChain 1.x's
`create_agent` (LangGraph's older `create_react_agent` is deprecated since LangGraph
1.0):

<!-- snippet: run -->
```bash
pip install langstage langgraph-supervisor langchain langchain-anthropic
```

!!! warning "Running it needs an API key"
    The graph builds and loads without a key (so `langstage check` works), but
    every turn calls Anthropic. Set `ANTHROPIC_API_KEY` before you chat.

<!-- snippet: run file=my_supervisor.py -->
```python title="my_supervisor.py"
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph_supervisor import create_supervisor

model = init_chat_model("anthropic:claude-sonnet-4-6")

def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

def web_search(query: str) -> str:
    """Look something up (stub)."""
    return f"results for {query!r}"

math_agent = create_agent(
    model, tools=[add], name="math_expert",
    system_prompt="You are a math expert. Use the tools to compute answers.",
)
research_agent = create_agent(
    model, tools=[web_search], name="researcher",
    system_prompt="You are a researcher. Look things up with the tools.",
)

# create_supervisor returns a StateGraph; .compile() yields the CompiledStateGraph
# LangStage loads — exactly the type a single agent compiles to.
supervisor = create_supervisor(
    agents=[math_agent, research_agent],
    model=model,
    prompt=(
        "You manage a math expert and a researcher. "
        "Delegate to exactly one worker at a time, then synthesize the answer."
    ),
).compile()  # (1)!
```

1. The only requirement LangStage places on your agent is that it is a
   **compiled** LangGraph graph exporting the spec attribute — here
   `supervisor`. Everything above is your code.

## 2. Run it — the same spec string as any agent

The graph is exported as `supervisor` from `my_supervisor.py`, so the spec string
is `my_supervisor.py:supervisor`. Point any stage at it the usual way:

=== "Web"

    <!-- snippet: run server -->

    ```bash
    langstage run --agent my_supervisor.py:supervisor
    ```

=== "Terminal"

    <!-- snippet: run server -->

    ```bash
    langstage-cli -a my_supervisor.py:supervisor
    ```

=== "Env var (any stage)"

    <!-- snippet: run -->

    ```bash
    export LANGSTAGE_AGENT_SPEC=my_supervisor.py:supervisor
    ```

=== "From Python"

    <!-- snippet: run server -->

    ```python
    from langstage import CoworkApp
    from my_supervisor import supervisor

    CoworkApp(agent=supervisor, workspace="./workspace", title="My Crew").run()
    ```

Check that it loads before you chat (keyless; add `--live` to run a real turn):

<!-- snippet: run -->
```bash
langstage check --agent my_supervisor.py:supervisor
```

That `my_supervisor.py:supervisor` spec is understood identically by every stage —
just like a single-agent `my_agent.py:graph` spec. No flags change, no multi-agent
mode is toggled.

## 3. What you see

Every stage streams your graph through the core's AG-UI bridge, which doesn't care
about the graph's internal structure. So a supervisor run looks like a single
agent's, with the hand-offs made visible:

- **Streaming chat** shows the supervisor's routing and each worker's replies, each
  labeled with the node that produced it (turn on `-v` in the terminal to see the
  labels).
- **Tool-call visualization** renders each sub-agent's tool calls inline (args,
  results, duration, status) — including the supervisor's hand-off "tools".
- **The task board, human-in-the-loop review, and the durable checkpointer apply
  unchanged.** A multi-step supervisor run delegated to the background is tracked
  on the board; if any node calls `interrupt()`, you get the same approval gate;
  and on the web stage the auto-attached SQLite checkpointer
  (`<workspace>/.langstage/checkpoints.db`) persists the whole graph's state, so a
  run survives a restart.

## Notes & limits

- **Use a spec string or pass the compiled object** — both work. The spec string
  (`module:attr` / `path/to/file.py:attr`) is what makes the *same* supervisor run
  on every stage; passing the object to `CoworkApp(agent=...)` is the in-process
  shorthand.
- **`--demo` still works** for a keyless first look, but it runs the built-in echo
  agent, not your supervisor — point `--agent` at your graph to see routing.
- **LangStage serves one graph per process.** That graph can contain as many
  agents as you like (a supervisor *is* one compiled graph). Running several
  *independent* top-level agents from one console is a separate idea and is not
  part of this stage today.

## See also

- [Web stage](../stages/web.md) · [Terminal stage](../stages/cli.md) — the surfaces this runs on
- [Configuration](../getting-started/configuration.md) — spec string, `langstage.toml`, `LANGSTAGE_*`
- [Human-in-the-loop](human-in-the-loop.md) — approvals inside any node of the graph
- [`langgraph-supervisor`](https://github.com/langchain-ai/langgraph-supervisor-py) — the prebuilt used above
