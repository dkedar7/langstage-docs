# Shared core — `langstage-core`

Every stage is thin because the hard parts live in one shared package:
`langstage-core`. It's the dependency that visibly ties LangStage to LangGraph, and
it's useful on its own — you can load an agent, resolve config, and stream a turn
without any surface.

!!! note "Formerly `langgraph-stream-parser`"
    The core was renamed to `langstage-core` in 1.0. `langgraph-stream-parser` still
    installs as a thin compatibility shim that re-exports `langstage_core` with a
    deprecation warning, so old pins keep working — but new code should use
    `langstage-core` / `import langstage_core`.

[:material-github: dkedar7/langstage-core](https://github.com/dkedar7/langstage-core){ .md-button }
[:material-package: PyPI](https://pypi.org/project/langstage-core/){ .md-button }

## What it provides

- **`load_agent_spec()`** — the `module:attr` / `path/to/file.py:attr` loader behind
  every stage's agent spec.
- **`HostConfig`** — the layered config resolver
  (`defaults < langstage.toml < LANGSTAGE_* env < overrides`) with per-field source
  tracking. Each stage subclasses it to add its own keys.
- **`apply_workspace()` / `workspace_root()`** — one source of truth for the agent's
  working directory, resolved once and read by every surface's tools and file
  browser.
- **The AG-UI bridge** — `build_agent()` wraps any compiled graph, and
  `iter_event_frames()` / `iter_chunk_frames()` stream one turn as the typed frames
  (`content`, `tool_start`/`tool_end`, `reasoning`, `interrupt`, `extraction`,
  `complete`, `error`) that every surface renders. Built on the official
  `ag-ui-langgraph` adapter.
- **`verify()`** — a live preflight: run one real turn and return whether the agent
  actually completed it (the shared primitive behind each stage's health check).
- **The keyless stub agent** — `langstage_core.demo.stub:graph`, the deterministic
  echo agent behind every stage's `--demo` mode.

## Stream a turn yourself

Given any compiled LangGraph graph, drive one turn in-process and consume the same
typed frames the surfaces render:

```python
import asyncio
from langstage_core.agui import build_agent, iter_event_frames

agent = build_agent(graph)  # any CompiledStateGraph

async def main():
    async for frame in iter_event_frames(agent, "hello", thread_id="t1"):
        if frame["type"] == "content":
            print(frame["content"], end="")
        elif frame["type"] == "tool_start":
            print(f"\nCalling {frame['name']}…")
        elif frame["type"] == "interrupt":
            ...  # human-in-the-loop; resume via iter_event_frames(..., resume=...)

asyncio.run(main())
```

`iter_chunk_frames()` is the same, shaped for a chunk-style renderer
(`{"status": "streaming", "chunk": …}`). The AG-UI bridge needs the `[agui]` extra:
`pip install "langstage-core[agui]"`.

## Inspect the shared config

```bash
python -m langstage_core.host
```

prints every shared `LANGSTAGE_*` value, where it resolved from, and the env var /
TOML key that sets it — the same machinery behind each stage's `--show-config`.

See [Configuration](getting-started/configuration.md) for the resolution chain.
