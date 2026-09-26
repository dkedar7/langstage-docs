# Serve over AG-UI — `langstage-agui`

`langstage-agui` ships with `langstage-core`. It serves any LangGraph
`CompiledGraph` as an [AG-UI](https://github.com/ag-ui-protocol/ag-ui) HTTP endpoint,
so AG-UI clients (CopilotKit, React/Vue/Angular components, your own frontend) can
talk to it. It also runs one turn from the terminal, which makes it a handy
preflight for any agent.

<!-- snippet: run -->
```bash
pip install "langstage-core[agui]"
```

## Three questions, three flags

<!-- snippet: run each needs=my_agent.py -->
```bash
langstage-agui --agent my_agent.py:graph --show-config   # does the config resolve an agent?
langstage-agui --agent my_agent.py:graph --verify        # does it load and run a turn?
langstage-agui --agent my_agent.py:graph -m "hi there"   # what does it say?
```

No agent yet? Each works keyless with `--demo` (the echo agent) or `--demo=tools`
(the rich demo: tool calls, reasoning and an interrupt):

<!-- snippet: run each exit=0,2 -->
```bash
langstage-agui --demo --verify                           # ok: one turn completed cleanly
langstage-agui --demo=tools -m "use a tool"              # prints the demo tool's answer
langstage-agui --demo=tools -m "use a tool" --json       # the typed TurnResult as JSON
langstage-agui --demo=tools -m "ask me"                  # pauses on an interrupt: exit 2
langstage-agui --show-config --json                      # resolved config as JSON
```

| Flag | What it does |
|---|---|
| `-a`, `--agent SPEC` | The agent (`module:attr` or `path/to/file.py:attr`). Falls back to `LANGSTAGE_AGENT_SPEC` / `[agent] spec`. |
| `--demo`, `--demo=tools` | A keyless demo agent: the echo stub, or the rich-frame tool demo. |
| `--host`, `--port`, `--path`, `--name` | Where to serve, and the agent name AG-UI clients see. |
| `--cors [ORIGIN,…]` | Allow browser frontends on other origins. Off by default; see below. |
| `--show-config` | Print the resolved config and exit. Add `--json` for JSON. |
| `--verify` | Run one keyless probe turn and report whether the agent works. |
| `-m`, `--message TEXT` | Run one turn with your prompt, print the reply, exit. |
| `--json` | With `-m`, print the `TurnResult` as JSON. With `--show-config`, print the config as JSON. |
| `--version` | Print the `langstage-core` version. |

What each one checks:

- **`--verify`** fails an agent that won't load, a graph that isn't runnable (for
  example a `StateGraph` you forgot to `.compile()`), a turn that errors, and a
  turn that completes with no output at all. It's keyless, so it fits a CI or
  deploy gate.
- **`-m` / `--message`** runs your prompt and prints the answer to stdout. With
  `--json` you get the typed `TurnResult` (`text`, `tool_calls`, `extractions`,
  `reasoning`, `outcome`, `interrupt`, `error`, `traceback`).
- `--verify`, `-m` and `--json` keep the agent's import-time `print`s off stdout,
  so the output stays machine-readable.

Exit codes follow the family contract: `0` success, `1` failure, `2` paused on an
interrupt, `64` usage error. See [Exit codes](exit-codes.md).

## Serving

<!-- snippet: run server needs=my_agent.py -->
```bash
langstage-agui --agent my_agent.py:graph                 # http://localhost:8050/
```

- The port is bound **before** the `Serving … at <url>` banner prints, so a busy
  port is a clean one-line `error: cannot serve at <url>: …`, not a success banner
  followed by a crash.
- A graph compiled **without a checkpointer** gets an in-memory one attached (on a
  copy; your graph object isn't changed). AG-UI needs threaded state for
  interrupts and resume.
- Keys in a `[configurable]` table in `langstage.toml` are passed to the graph's
  `config["configurable"]`, when serving and under `-m`. `thread_id` is always set
  per run.

From Python:

<!-- snippet: run -->
```python
from langstage_core import load_agent_spec
from langstage_core.agui import build_app

graph = load_agent_spec("langstage_core.demo.stub:graph")   # or your own CompiledGraph
app = build_app(graph)   # an ASGI (FastAPI) app; run it with uvicorn
```

`serve(graph, host=..., port=...)` builds and runs the app in one call. It binds
first, and raises `OSError` for a busy port.

## Browser frontends on another origin (CORS)

By default the server sends no CORS headers, so only same-origin pages and
non-browser clients can call it. A frontend dev server on another port (say
`http://localhost:5173` calling `http://localhost:8050`) needs an opt-in:

<!-- snippet: run server -->
```bash
langstage-agui --demo=tools --cors                          # any localhost / 127.0.0.1 / [::1] origin
langstage-agui --demo=tools --cors http://localhost:5173    # exactly these origins (comma-separated)
```

<!-- snippet: check -->
```python
app = build_app(graph, cors_origins=["https://app.example.com"])   # or "loopback"
```

`"*"` is honored only if you pass it explicitly. It is never a default.
Credentials (cookies) are never allowed cross-origin.

!!! note "The web app's CORS is different"
    `langstage run` has its own setting, `LANGSTAGE_CORS_ORIGINS`. It allows
    loopback origins by default, and origins you list get *credentialed* access,
    because the web app supports HTTP Basic Auth. `langstage-agui` has no auth and
    never allows credentials. See [Web](../stages/web.md#cors).

## Notes for AG-UI client authors

- Use a new message id for every turn. The adapter dedupes messages by id, so a
  reused id silently drops the later turn.
- An agent failure is a terminal `RUN_ERROR` event.
- An interrupt arrives as a `CUSTOM` `on_interrupt` event. Resume by starting a new
  run on the same thread with `RunAgentInput.resume` (ag-ui-langgraph 0.0.43 and
  later). The older `forwardedProps.command.resume` wire still works but is
  deprecated. The decision payload is described in
  [Human-in-the-loop](../guides/human-in-the-loop.md).
- The in-process frames that the surfaces use are built from the same events. See
  the [frame reference](frames.md).
