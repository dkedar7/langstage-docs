# What changed / migrating

Two changes landed in June and July 2026: the family was **renamed to
LangStage**, and the shared core **adopted the AG-UI protocol** as the one way every
surface streams a turn.
Both are designed to be a non-event for existing users — old installs, imports,
and commands keep working through a transition window.

!!! warning "What can break"
    - **Python ≥ 3.11.** The shared core requires 3.11 (it was 3.10), because
      AG-UI's streaming stack doesn't work on 3.10. The surface packages already
      required 3.11. On 3.10, stay on the pre-1.0 `langgraph-stream-parser` 0.3.x
      or upgrade Python.
    - **Direct use of the old event layer.** If your own code imported
      `StreamParser`, `event_to_dict` or `stream_graph_updates`, it needs the
      small migration [below](#if-you-used-langgraph-stream-parser-directly).

    Everything else (package names, imports, commands, config names) is shimmed or
    falls back.

## Name map

| Old package | New package |
|---|---|
| `cowork-dash` | **`langstage`** |
| `deepagent-code` | **`langstage-cli`** |
| `deepagent-lab` | **`langstage-jupyter`** |
| `deepagent-vscode` | **`langstage-vscode`** |
| `deepagent-hermes` | **`langstage-hermes`** |
| `langgraph-stream-parser` | **`langstage-core`** *(the shared core; the old name still installs as a shim)* |

All are on PyPI — `pip install <new package>` gets the current release. (This table
intentionally lists no version numbers; a hand-maintained "latest" column only goes
stale — check PyPI for the current version of each.)

## What still works

- **`pip install <old-name>`** — each old name has a final "tombstone" release
  that simply depends on the new package, so installing it pulls the rename.
- **`import <old_module>`** — e.g. `import cowork_dash`, `import deepagent_code`,
  and the documented host spec `deepagent_hermes.agent:graph` still import, via a
  deprecated alias package that emits a `DeprecationWarning`.
- **Old console commands** — `cowork-dash`, `deepagent-code`, `deepagent-lab`,
  `deepagent-hermes` remain as aliases of the new commands. (`deepagent-hermes`
  prints a one-line deprecation `note:` on each run.)

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

The legacy names **still resolve** as a deprecated fallback. The canonical name
wins when both are set, and each legacy name prints one `note:` line on stderr per
process (`LANGSTAGE_SUPPRESS_LEGACY_NOTICE=1` silences it). Moving the global config out of
`~/.deepagents/` also avoids a collision with LangChain's `dcode`, which now owns
that directory.

`langstage-hermes` keeps its existing home dir for safety: an existing
`~/.deepagent-hermes` directory keeps being used if present, so no skills,
memories, or session history are orphaned by upgrading. The legacy
`deepagent-hermes.toml` file name is still read, with a deprecation note.

## Every surface now streams over AG-UI

The shared core adopted the **[AG-UI protocol](https://github.com/ag-ui-protocol/ag-ui)**,
the event-based wire for streaming text, tool calls, reasoning, state and
human-in-the-loop to frontends. It started as an opt-in and is now the only
streaming path: every surface drives your graph through the core's in-process
AG-UI bridge, and `langstage-core[agui]` is a regular dependency of each one. You
don't need to change your agent. What you get:

- The same frames on every surface, with the same rules. See the
  [frame reference](reference/frames.md).
- `langstage-agui`, which serves any `CompiledGraph` as an AG-UI HTTP endpoint:

    ```bash
    pip install "langstage-core[agui]"
    langstage-agui --agent my_agent.py:graph     # or --demo
    ```

    See [Serve over AG-UI](reference/agui-server.md).

Notes for AG-UI client authors:

- Graphs compiled **without a checkpointer** work: one is attached for you (AG-UI
  needs threaded state for interrupts and resume).
- Agent failures surface as a terminal **`RUN_ERROR`** event rather than a dropped
  stream.
- **Use a new message id per turn.** The adapter dedupes messages by id, so a reused
  id silently drops the later turn.
- Interrupts arrive as a `CUSTOM` `on_interrupt` event. Resume by starting a new run
  on the same thread with AG-UI's standard **`RunAgentInput.resume`**
  (ag-ui-langgraph 0.0.43 and later). The older `forwardedProps.command.resume`
  still works as a fallback but is deprecated. The decision payload is described in
  [Human-in-the-loop](guides/human-in-the-loop.md).

## If you used `langgraph-stream-parser` directly

`langstage-core` 1.0 is the rename of `langgraph-stream-parser`. `import
langgraph_stream_parser` keeps working **only while the separate
`langgraph-stream-parser` compat package is installed** (upgrading it in place keeps
it; a fresh `pip install langstage-core` doesn't pull it). New code should
`import langstage_core`.

The old event layer was removed in 1.0. If you used it, migrate:

| Removed | Use instead |
|---|---|
| `StreamParser`, `langstage_core.events`, `event_to_dict` | `langstage_core.agui.iter_event_frames` / `iter_chunk_frames` (frame dicts, same vocabulary) |
| `stream_graph_updates`, `resume_graph_from_interrupt` | `iter_chunk_frames(agent, message, thread_id, resume=...)` |
| `adapters.CLIAdapter`, `PrintAdapter`, `FastAPIAdapter`, `JupyterDisplay` | `SessionAdapter` (in-process) or `build_app` / `serve` (HTTP) |
| `from langstage_cli import stream_graph_updates, prepare_agent_input` | the `iter_chunk_frames` snippet on the [Terminal](stages/cli.md#programmatic-use) page |

Kept and unchanged: `load_agent_spec`, `HostConfig`, `prepare_agent_input`,
`create_resume_input`, the task engine and the extractors. The rationale is in
[ADR 0003](https://github.com/dkedar7/langstage-core/blob/main/docs/adr/0003-deprecate-the-event-layer.md).

## Recommended steps

1. `pip install langstage langstage-cli langstage-jupyter langstage-vscode langstage-hermes`
   (only the ones you use).
2. Swap `import` paths and commands to the new names at your leisure.
3. Rename `deepagents.toml` → `langstage.toml` and `DEEPAGENT_*` → `LANGSTAGE_*`
   when convenient; run any stage's `--show-config` to confirm what's resolving.
