# Migrating from `deepagent-*` / `cowork-dash`

The family was renamed to **LangStage** in June 2026. The rename is designed to
be a non-event for existing users: old installs, imports, and commands keep
working through a transition window.

## Name map

| Old package | New package | Old → new version |
|---|---|---|
| `cowork-dash` | **`langstage`** | 0.6.x → 0.7.0 |
| `deepagent-code` | **`langstage-cli`** | 0.3.x → 0.4.0 |
| `deepagent-lab` | **`langstage-jupyter`** | 0.3.x → 0.4.0 |
| `deepagent-vscode` | **`langstage-vscode`** | 0.2.x → 0.3.0 |
| `deepagent-hermes` | **`langstage-hermes`** | 0.1.x → 0.2.x |
| `langgraph-stream-parser` | *(unchanged)* | → 0.3.0 |

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

## Recommended steps

1. `pip install langstage langstage-cli langstage-jupyter langstage-vscode langstage-hermes`
   (only the ones you use).
2. Swap `import` paths and commands to the new names at your leisure.
3. Rename `deepagents.toml` → `langstage.toml` and `DEEPAGENT_*` → `LANGSTAGE_*`
   when convenient; run any stage's `--show-config` to confirm what's resolving.
