# Shared core — `langstage-core`

Every stage is thin because the hard parts live in one shared package,
`langstage-core`. It is useful on its own: you can load an agent, resolve config,
stream a turn, run one turn for a test, or delegate work to a background worker,
all without a surface.

!!! note "Formerly `langgraph-stream-parser`"
    The core was renamed to `langstage-core` in 1.0, and its old event layer
    (`StreamParser`, `event_to_dict`, `stream_graph_updates`, …) was replaced by the
    AG-UI bridge. See [Migrating](migrating.md#if-you-used-langgraph-stream-parser-directly).

[:material-github: dkedar7/langstage-core](https://github.com/dkedar7/langstage-core){ .md-button }
[:material-package: PyPI](https://pypi.org/project/langstage-core/){ .md-button }

## Install

```bash
pip install "langstage-core[agui]"          # what every surface uses
pip install "langstage-core[agui,stub]"     # + the keyless echo agent, for trying things
pip install "langstage-core[agui,real]"     # + langchain-openai, for "connect a real model" below
```

A bare `pip install langstage-core` covers the host and config layer only
(`load_agent_spec`, `HostConfig`, the resume helpers). Streaming, one-shot turns,
`langstage-agui` and the task engine all need `[agui]`.

## What it provides

- **The host layer.** `load_agent_spec()` loads the `module:attr` /
  `path/to/file.py:attr` spec every stage understands. `HostConfig` resolves the
  layered [configuration](getting-started/configuration.md) with per-field source
  tracking; each stage subclasses it.
- **The AG-UI bridge** (`langstage_core.agui`). `build_agent()` wraps any compiled
  graph in the official `ag-ui-langgraph` adapter. `iter_event_frames()` /
  `iter_chunk_frames()` stream a turn as typed frames (see the
  [frame reference](reference/frames.md)). `run_turn()` and the `collect_*`
  functions run one turn and return a `TurnResult`. `build_app()` / `serve()`
  expose the agent over HTTP (see [Serve over AG-UI](reference/agui-server.md)).
- **`verify()`**, a live preflight: run one real turn and report whether the agent
  works. It is the primitive behind every stage's `--verify` / `check --live`.
- **The task engine**: `TaskRunner`, `TaskStore`, `InMemoryTaskStore` and the
  agent-facing `TASK_TOOLS`. It powers the web app's task board.
- **`SessionAdapter`**, a session-scoped driver with a typed terminal outcome. It
  streams the web app's chat and the task board.
- **Human-in-the-loop helpers**: `create_resume_input`, `normalize_decision`,
  `is_allowed_decision`, `DECISION_VERBS`, `DECISION_ALIASES`. See
  [Human-in-the-loop](guides/human-in-the-loop.md).
- **Extractors** (`ToolExtractor` and built-ins such as `TodoExtractor`) that turn a
  tool result into a structured `extraction` frame.
- **Console-safe output**: `langstage_core.console.safe_print` / `safe_write`. See
  [Windows and console output](reference/windows.md).
- **Keyless demo agents**: `langstage_core.demo.stub:graph` (the echo agent behind
  every `--demo`) and `langstage_core.demo.tools:graph` (tool calls, reasoning and
  an interrupt, all offline).

## Stream a turn

```python
import asyncio
from langstage_core import load_agent_spec
from langstage_core.agui import build_agent, iter_event_frames

graph = load_agent_spec("langstage_core.demo.stub:graph")   # or any CompiledGraph of yours
agent = build_agent(graph)

async def main():
    async for frame in iter_event_frames(agent, "hello", thread_id="t1"):
        if frame["type"] == "content":
            print(frame["content"], end="")
        elif frame["type"] == "tool_start":
            print(f"\nCalling {frame['name']}…")
        elif frame["type"] == "complete":
            print()

asyncio.run(main())
```

`build_agent` attaches an in-memory checkpointer when the graph has none (on a
copy; your graph isn't changed), so multi-turn memory and interrupts work. Build
the agent once, reuse it, and pass a `thread_id` per conversation.
`iter_chunk_frames()` takes the same arguments and yields the chunk-style frames the
terminal and JupyterLab use.

## Run one turn and get the result

For a test, an eval harness, a batch job or a script, you usually want the answer,
not a stream. `run_turn` (sync) returns a typed `TurnResult`:

```python
from langstage_core.agui import run_turn
from langstage_core.demo.tools import create_tool_demo_agent, demo_extractors

result = run_turn(create_tool_demo_agent(), "use a tool", extractors=demo_extractors())
print(result.outcome)      # complete   ('interrupted' on "ask me", 'error' on a failing turn)
print(result.tool_calls)   # [{'name': 'demo_lookup', 'args': {'query': 'use a tool'}, 'id': 'demo_lookup_1'}]
print(result.text)
```

`TurnResult` has `text`, `tool_calls`, `extractions`, `reasoning`, `outcome`,
`interrupt`, `error`, `traceback` (set on an error when `LANGSTAGE_DEBUG` is on) and
`frames` (a count, not the list).

- Each `run_turn` call is isolated: a fresh `thread_id`, and your graph isn't
  changed. So `for prompt in dataset: run_turn(graph, prompt)` never leaks one turn
  into the next. To carry state across calls, pass the same `build_agent(...)` agent
  and an explicit `thread_id`.
- `run_turn` accepts a compiled graph, a prebuilt agent, or a spec string.
- Inside a running event loop (a Jupyter cell, an async app), use
  `await collect_event_frames(agent, message, thread_id)` instead;
  `run_turn` raises a clear error there. `collect_chunk_frames` is the chunk-wire twin.

## Connect a real model

The demos are keyless. To stream a real model, bring any LangGraph `CompiledGraph`.
This one uses LangChain 1.x's `create_agent` and any OpenAI-compatible endpoint.

!!! warning "Needs an API key"
    Set `OPENAI_API_KEY` (and `OPENAI_BASE_URL` for OpenRouter or another
    compatible endpoint). Without a key the model call fails.

```python
import asyncio, os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langstage_core.agui import build_agent, iter_event_frames

model = ChatOpenAI(
    model="gpt-4o-mini",
    base_url=os.environ.get("OPENAI_BASE_URL"),   # e.g. https://openrouter.ai/api/v1
    api_key=os.environ["OPENAI_API_KEY"],
)
agent = build_agent(create_agent(model, tools=[]))

async def main():
    async for frame in iter_event_frames(agent, "Say hi in one word.", thread_id="s1"):
        if frame["type"] == "content":
            print(frame["content"], end="")

asyncio.run(main())
```

Prefer Anthropic and the deepagents stack? `pip install deepagents langchain-anthropic`
and build a deepagents graph instead; the core only ever sees a `CompiledGraph`.
LangGraph's `create_react_agent` is deprecated since LangGraph 1.0, so new code
should use `langchain.agents.create_agent`.

## Delegate work to a background task

The task engine is a single-process worker pool: enqueue a prompt, keep working,
and read the result when it's done.

```python
import asyncio
from langstage_core import SessionAdapter
from langstage_core.demo.tools import create_tool_demo_agent
from langstage_core.tasks import REVIEW_NEEDED, TERMINAL_STATES, InMemoryTaskStore, TaskRunner

async def main():
    adapter = SessionAdapter(graph=create_tool_demo_agent())   # keyless; "ask me" interrupts
    runner = TaskRunner(adapter, InMemoryTaskStore(), concurrency=3)
    await runner.start()

    task_id = await runner.enqueue(title="research", prompt="ask me first")

    # review_needed is NOT terminal: a HITL task waits there until someone resumes it.
    while (task := await runner.store.get(task_id))["state"] not in TERMINAL_STATES:
        if task["state"] == REVIEW_NEEDED:
            print(task["interrupt"]["allowed_decisions"])        # ['respond', 'approve']
            await runner.resume(task_id, [{"type": "approve"}])
        await asyncio.sleep(0.1)

    print(task["state"], "-", task["result"])
    await runner.shutdown()

asyncio.run(main())
```

A task is a `TypedDict`: read `task["state"]`, `task["result"]`, `task["error"]` and
`task["interrupt"]`. States flow `queued → ongoing → review_needed → done | failed |
cancelled`. Besides `resume`, you can `followup(task_id, message)` a finished task,
`retry(task_id)` a failed or cancelled one, and `cancel(task_id)` a queued or
running one. Each returns `False` when the task isn't in a state that allows it.
Give your agent `TASK_TOOLS` and it can delegate to copies of itself.

## Configuration helpers

`HostConfig` is the resolver behind every `--show-config`.

```bash
python -m langstage_core.host        # every shared key, its value and where it came from
```

From Python:

```python
from langstage_core import HostConfig

cfg = HostConfig.resolve()
print(cfg.agent_spec, cfg.port)
print(cfg.config_issues())   # [] when nothing was ignored or degraded
```

| Method | Returns |
|---|---|
| `resolve(**overrides)` | The resolved config; overrides are the highest layer. |
| `describe()` | The human `--show-config` table. |
| `config_dict()` | The same as data: each field's `value`, `source`, `env`, `legacy_env`, `toml`, plus `toml` (`found`, `paths`, `malformed`, `malformed_files`, `unknown_keys`) and `issues`. |
| `config_issues()` | Everything that was ignored or degraded: a malformed file, a wrong-type or invalid value, an unknown key. Empty means clean. |
| `malformed_toml()` | The config files that exist but don't parse. |
| `unknown_toml_keys()` | Keys that map to no field (typos). |
| `configurable()` | The `[configurable]` table, for `config["configurable"]`. |
| `toml_dir_for(field)` | The directory of the TOML file a value came from, to pass as `base_dir=`. |

### Agent specs

A spec is `path/to/file.py:attr` or `package.module:attr`.

- The `:attr` suffix is required. A spec without a colon is an error, never a
  silent fallback to some default agent.
- Surrounding whitespace is ignored and a leading `~` is expanded.
- The attribute must be the agent itself. A `str` attribute is rejected, not
  followed as another spec.
- `file.py:attr` puts the file's directory first on `sys.path`, so the agent can
  import its sibling modules, just like `python file.py`.
- `package.module:attr` falls back to the current directory (or `base_dir=`) when
  the package isn't otherwise importable.
- `load_agent_spec(spec, stdout_to_stderr=True)` sends the agent's import-time
  `print`s to stderr. Use it when stdout has to stay machine-readable.

## `verify()`

`verify(agent_or_graph)` (and the async `averify`) runs one probe turn and returns a
`VerifyResult` with `ok` and a reason. It passes a turn that produces content, a
tool call or reasoning. It fails a graph that won't load or isn't compiled, a turn
that errors, and a turn that completes with no output at all. A turn that pauses
on an interrupt counts as healthy, since the agent ran and the approval gate
worked. It never raises for a bad agent; you get `ok=False` with the reason.
