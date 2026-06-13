# Configuration

Every stage resolves its settings through one shared chain, so what you learn
once applies everywhere. The chain, lowest precedence first:

```text
defaults  <  langstage.toml  <  LANGSTAGE_* env vars  <  CLI flags / explicit args
```

This is implemented once in the [shared core](../core.md) (`HostConfig`), so
the spelling and precedence are identical across the web app, CLI, JupyterLab,
and VS Code sidecar.

## `langstage.toml`

Drop a `langstage.toml` in your project (or any ancestor directory — the
nearest one wins) and a global `~/.langstage/config.toml` for machine-wide
defaults. Project values override global.

```toml title="langstage.toml"
[agent]
spec = "my_agent.py:graph"

[workspace]
root = "."

[server]
host = "localhost"
port = 8050

[ui]
title = "My Agent"
```

## Environment variables

Every shared key has a `LANGSTAGE_*` env var:

| Setting | Env var | TOML key |
|---|---|---|
| Agent spec | `LANGSTAGE_AGENT_SPEC` | `agent.spec` |
| Workspace root | `LANGSTAGE_WORKSPACE_ROOT` | `workspace.root` |
| Host | `LANGSTAGE_HOST` | `server.host` |
| Port | `LANGSTAGE_PORT` | `server.port` |
| Debug | `LANGSTAGE_DEBUG` | `debug` |
| Title | `LANGSTAGE_TITLE` | `ui.title` |

Individual stages add their own keys (e.g. `langstage-hermes` has a large
`LANGSTAGE_HERMES_*` surface) — run that stage's `--show-config` to see them all.

## `--show-config`

Never guess which layer won. Every stage prints the resolved value, its source,
and the names that set it:

```bash
langstage --show-config
```

You can also dump just the shared core:

```bash
python -m langgraph_stream_parser.host
```

## Legacy names still work

!!! note "Coming from `deepagent-*` / `cowork-dash`"
    The pre-rename vocabulary — `DEEPAGENT_*` env vars, `deepagents.toml`, and
    `~/.deepagents/config.toml` — is still resolved as a **deprecated fallback**.
    The canonical `LANGSTAGE_*` name wins when both are set, and using a legacy
    env var emits a one-time `DeprecationWarning`. Moving off `~/.deepagents/`
    also avoids a collision with LangChain's `dcode`, which now owns that
    directory. See [Migrating](../migrating.md).
