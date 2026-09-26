# Configuration

Every stage resolves its settings through one shared chain, so what you learn once
applies everywhere. From lowest to highest precedence:

<!-- snippet: skip -->
```text
defaults  <  ~/.langstage/config.toml  <  langstage.toml  <  LANGSTAGE_* env vars  <  CLI flags / Python args
             (global, per user)           (project)
```

The chain is implemented once, in the [shared core](../core.md) (`HostConfig`), so
the spelling and the precedence are the same in the web app, the terminal,
JupyterLab, the VS Code sidecar and `langstage-agui`. (`langstage-hermes` uses the
same machinery with its own file names; see [below](#langstage-hermes).)

## The two TOML files

Both files are read and deep-merged. The project file wins key by key.

- **Project `langstage.toml`.** The nearest `langstage.toml` at or above the
  directory you run the command from, found by walking up the tree the way `git`
  finds `.git`. A file in a parent directory therefore configures every run beneath
  it. Discovery starts from the working directory, not from `--workspace`.
- **Global `~/.langstage/config.toml`.** Applies to every run for your user. Set
  `LANGSTAGE_CONFIG_HOME` to move the directory it lives in (the file is always
  named `config.toml`).

<!-- snippet: check -->
```toml title="langstage.toml"
debug = false             # top-level keys go ABOVE the first [table]

[agent]
spec = "my_agent.py:graph"

[workspace]
root = "."

[server]
host = "localhost"
port = 8050

[ui]
title = "My Agent"

[configurable]            # passed to your graph as config["configurable"]
model = "claude-sonnet-4-6"
```

!!! warning "`debug` must come before the first table"
    In TOML, a bare key written after `[server]` belongs to `server`. So
    `debug = true` below a table header is read as `server.debug`, which is
    ignored, and a `note:` says so at startup. Put top-level keys first.

Because a parent-directory or global file can set values such as
`auth.password` or `server.host` for every run beneath it, don't assume config
comes only from `./langstage.toml`. Run [`--show-config`](#see-what-resolved) when a
value surprises you.

### Relative paths resolve against the file they're in

A relative path in a TOML file resolves against **that file's directory**, the way
paths in `pyproject.toml` do. This applies to `[agent] spec` (the file form) and
`[workspace] root`:

- In a project `langstage.toml`, `spec = "my_agent.py:graph"` means "next to this
  `langstage.toml`", so the project runs the same from its root and from any
  subdirectory.
- In the global `~/.langstage/config.toml`, a relative path resolves against
  `~/.langstage/`. Write `~/agents/my_agent.py:graph` or an absolute path there.
- Paths from `LANGSTAGE_*` env vars and CLI flags stay relative to the directory
  you run the command from.
- A leading `~` is expanded from every source.

`--show-config` prints the resolved absolute path.

### `[configurable]`

Keys in a `[configurable]` table are forwarded to your graph's
`config["configurable"]` on every turn, by the terminal, the VS Code sidecar and
`langstage-agui` (serving and `-m`). `--show-config` lists them, and they are never
flagged as unknown keys. `thread_id` is set per conversation by the surface; the
terminal honors a pinned `[configurable] thread_id`.

## Environment variables

Every shared key has a `LANGSTAGE_*` env var:

| Setting | Env var | TOML key |
|---|---|---|
| Agent spec | `LANGSTAGE_AGENT_SPEC` | `agent.spec` |
| Workspace root | `LANGSTAGE_WORKSPACE_ROOT` | `workspace.root` |
| Host | `LANGSTAGE_HOST` | `server.host` |
| Port | `LANGSTAGE_PORT` | `server.port` |
| Debug (tracebacks on error frames) | `LANGSTAGE_DEBUG` | `debug` |
| Title | `LANGSTAGE_TITLE` | `ui.title` |

Family-wide switches that aren't config keys:

| Env var | Effect |
|---|---|
| `LANGSTAGE_CONFIG_HOME` | Directory of the global `config.toml` (default `~/.langstage`). The CLI's session store lives under it too. |
| `LANGSTAGE_SUPPRESS_LEGACY_NOTICE=1` | Silence the one-line `note:` printed for each legacy `DEEPAGENT_*` / `deepagents.toml` name. |

Surface-specific keys include:

| Env var | TOML key | Surface |
|---|---|---|
| `LANGSTAGE_CORS_ORIGINS` | `server.cors_origins` | Web: extra origins allowed cross-origin. See [Web](../stages/web.md#cors). |
| `LANGSTAGE_TASK_CONCURRENCY` | `tasks.concurrency` | Web: task-board workers (default 3). |
| `LANGSTAGE_CELL_MEMORY_LIMIT_MB` | — | Web: memory limit for the default agent's `execute_python` (default 512). |
| `LANGSTAGE_PERSIST` | `session.persist` | Terminal: persist sessions (default on). |
| `LANGSTAGE_CLI_SESSIONS_DIR` | — | Terminal: where session stores live. |
| `LANGSTAGE_JUPYTER_TOKEN` | `jupyter.token` | JupyterLab: pin the launcher's token. |

The web app alone has more than 20 keys (theme, auth, branding, workflow prompts,
tab visibility…); its page has [the full table](../stages/web.md#configuration).
For any stage, `--show-config` lists every key it reads.

## See what resolved

Never guess which layer won. Every stage prints each value, its source, and the env
var and TOML key that set it:

<!-- snippet: run each needs=my_agent.py -->
```bash
langstage config                    # web (also: langstage --show-config)
langstage-cli --show-config
langstage-jupyter --show-config
langstage-vscode-sidecar --show-config
langstage-hermes --show-config
langstage-agui --show-config
python -m langstage_core.host       # just the shared keys
```

For the same data as one JSON object, use `langstage config --json`, or add
`--json` to `--show-config` on `langstage-jupyter`, `langstage-vscode-sidecar`,
`langstage-hermes` and `langstage-agui`. (`langstage-cli --show-config` is human-only
today; use `HostConfig.config_dict()` from Python.) The JSON has each field's
`value`, `source`, `env` and `toml`; a `toml` block with the files read (`paths`),
`malformed` and `malformed_files`; and an `issues` list. A surface leaves out keys it doesn't use and says so on a
`(not used by this surface, so not shown: …)` line.

What the diagnostic tells you:

- **Every file that contributed.** `TOML read from:` lists the global and project
  files. Each value is credited to the file that actually set it.
- **A malformed file is reported as malformed, not missing.** A `langstage.toml`
  that doesn't parse is ignored entirely (its keys fall back to env and defaults),
  and the footer says `TOML: <path> is MALFORMED and was ignored entirely
  (<parse error>)`.
- **Unknown keys.** A key that maps to no field (a typo, a wrong table) is listed
  under `unknown TOML keys`.
- **Bad values degrade, with a note.** A malformed or invalid value (`LANGSTAGE_PORT=abc`,
  port `70000`, an unknown theme) never crashes a surface. It is ignored with a
  one-line `note:` on stderr, and the **next layer down** is used: the
  `langstage.toml` value if one is set, else the default.
- **Booleans** accept `true`/`false`, `1`/`0`, `yes`/`no` and `on`/`off` in env vars.
  In TOML, use a real boolean (`true`) or a quoted string with one of those words
  (`"off"`). Anything else is ignored with a note.

### Fail CI on a config problem

The default is "degrade and keep running", which is right for a server but wrong
for a deploy check. Two ways to make a problem fatal:

<!-- snippet: run -->
```bash
langstage config --strict           # exit 1 if anything was ignored or degraded
```

<!-- snippet: run -->
```python
from langstage_core import HostConfig

issues = HostConfig.resolve().config_issues()
assert not issues, issues
```

`config --strict` prints one stderr line per issue and composes with `--json`.
`config_issues()` works for any surface's config class (they all subclass
`HostConfig`).

## Scaffold a config

Pick one; both write `./langstage.toml`:

<!-- snippet: check -->
```bash
langstage init          # a fully commented langstage.toml: every web option, its section and env var
langstage-cli init      # or: a runnable my_agent.py + a langstage.toml pointing at it
```

Neither overwrites an existing file unless you pass `--force`.
`--path` writes elsewhere, and `init` tells you if the file it wrote won't be
discovered from where you are.

## `langstage-hermes`

Hermes reads the family `langstage.toml` too, plus its own `langstage-hermes.toml`
(project) and `$HERMES_HOME/config.toml` (global, default
`~/.langstage-hermes/config.toml`). Its own settings use the `LANGSTAGE_HERMES_*`
env prefix. `langstage-hermes --show-config [--json]` shows the resolved values.
See [Reference agent](../stages/hermes.md#configuration).

## Legacy names still work

!!! note "Coming from `deepagent-*` / `cowork-dash`"
    The pre-rename vocabulary — `DEEPAGENT_*` env vars, `deepagents.toml`,
    `~/.deepagents/config.toml` and `DEEPAGENTS_CONFIG_HOME` — still resolves as a
    deprecated fallback. The canonical `LANGSTAGE_*` name wins when both are set.
    Each legacy name prints one line on stderr per process, for example
    `note: DEEPAGENT_PORT is deprecated; use LANGSTAGE_PORT.` Set
    `LANGSTAGE_SUPPRESS_LEGACY_NOTICE=1` to silence it. Moving off `~/.deepagents/`
    also avoids a collision with LangChain's `dcode`, which now owns that
    directory. See [Migrating](../migrating.md).
