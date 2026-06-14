# What changed / migrating

Two changes landed in June 2026: the family was **renamed to LangStage**, and
the shared core **adopted the AG-UI protocol** for serving agents to frontends.
Both are designed to be a non-event for existing users — old installs, imports,
and commands keep working through a transition window.

!!! warning "One real breaking change"
    **`langgraph-stream-parser` now requires Python ≥ 3.11** (was ≥ 3.10), as of
    0.4.0 — AG-UI's streaming stack doesn't work on 3.10. If you're on Python
    3.10, stay on `langgraph-stream-parser` 0.3.x or upgrade Python. The surface
    packages already required 3.11+, so they're unaffected. **This is the only
    change that can break an existing install** — everything below is shimmed or
    falls back.

## Name map

| Old package | New package | Latest |
|---|---|---|
| `cowork-dash` | **`langstage`** | 0.8.0 |
| `deepagent-code` | **`langstage-cli`** | 0.5.0 |
| `deepagent-lab` | **`langstage-jupyter`** | 0.5.0 |
| `deepagent-vscode` | **`langstage-vscode`** | 0.4.0 |
| `deepagent-hermes` | **`langstage-hermes`** | 0.3.0 |
| `langgraph-stream-parser` | *(unchanged — the shared core)* | 0.4.1 |

## What still works

- **`pip install <old-name>`** — each old name has a final "tombstone" release
  that simply depends on the new package, so installing it pulls the rename.
- **`import <old_module>`** — e.g. `import cowork_dash`, `import deepagent_code`,
  and the documented host spec `deepagent_hermes.agent:graph` still import, via a
  deprecated alias package that emits a `DeprecationWarning`.
- **Old console commands** — `cowork-dash`, `deepagent-code`, `deepagent-lab`,
  `deepagent-hermes` remain as aliases of the new commands.

These shims are kept for a transition window, then removed in a future major.
Update when convenient — nothing breaks today.

## Config vocabulary

The canonical config vocabulary is now `LANGSTAGE_*`:

| Old | New |
|---|---|
| `DEEPAGENT_*` env vars | `LANGSTAGE_*` |
| `deepagents.toml` | `langstage.toml` |
| `~/.deepagents/config.toml` | `~/.langstage/config.toml` |
| `DEEPAGENTS_CONFIG_HOME` | `LANGSTAGE_CONFIG_HOME` |

The legacy names **still resolve** as a deprecated fallback (canonical wins when
both are set; legacy env use warns once). Moving the global config out of
`~/.deepagents/` also avoids a collision with LangChain's `dcode`, which now owns
that directory.

`langstage-hermes` keeps its existing home dir for safety: an existing
`~/.deepagent-hermes` directory keeps being used if present, so no skills,
memories, or session history are orphaned by upgrading.

## New: serve any agent over AG-UI

The shared core now bridges to the **[AG-UI protocol](https://github.com/ag-ui-protocol/ag-ui)** — the event-based wire format for streaming rich agent interactions (text, tool calls, reasoning, state, human-in-the-loop) to frontends. Any LangGraph `CompiledGraph` can be served:

```bash
pip install "langgraph-stream-parser[agui]"
langstage-agui --agent my_agent.py:graph     # or --demo
```

Notes for integrators:

- Works with graphs compiled **without a checkpointer** (one is auto-attached — AG-UI needs threaded state for interrupts/resume).
- Agent failures surface as a terminal **`RUN_ERROR`** event rather than a dropped stream.
- **Use a unique message id per turn** — the adapter dedupes messages by id, so reused ids silently drop later turns.
- Interrupts arrive as a `CUSTOM` `on_interrupt` event; resume by starting a new run with `forwardedProps.command.resume`.

This is additive — it doesn't change how the existing surfaces work. See [Shared core](core.md).

## Recommended steps

1. `pip install langstage langstage-cli langstage-jupyter langstage-vscode langstage-hermes`
   (only the ones you use).
2. Swap `import` paths and commands to the new names at your leisure.
3. Rename `deepagents.toml` → `langstage.toml` and `DEEPAGENT_*` → `LANGSTAGE_*`
   when convenient; run any stage's `--show-config` to confirm what's resolving.
