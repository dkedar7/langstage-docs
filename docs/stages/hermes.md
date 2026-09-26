# Reference agent — `langstage-hermes`

Not a surface but an **agent**: the family's reference implementation, a faithful
reproduction of Nous Research's Hermes Agent on top of LangGraph and deepagents.
Drop it into any stage to see a rich, real-world agent at work.

[:material-github: dkedar7/langstage-hermes](https://github.com/dkedar7/langstage-hermes){ .md-button }
[:material-package: PyPI](https://pypi.org/project/langstage-hermes/){ .md-button }

## What it is

A deepagents-built agent with a **closed reflection → skill-creation loop**:

- After about 10 tool-using iterations, a review subagent writes or patches a
  `SKILL.md` capturing the pattern it just used, and adds it to a skill library.
- Next session, the agent sees the library's skill descriptions at startup and can
  `skill_view(name)` to load a skill's body on demand.
- A **curator** ages out skills that aren't used and archives stale ones.
- **Frozen-snapshot memory** (`MEMORY.md` and `USER.md`) keeps prompt-cache hits for
  the whole session, and **FTS5 session search** indexes every past conversation
  locally.

## Try it without a key

<!-- snippet: run -->
```bash
pip install langstage-hermes
langstage-hermes demo
```

`demo` runs the real reflection loop (the review subagent, `skill_manage`, the
skill library, the audit log and the FTS5 store) against a scripted model: no
network, no key. It prints the skill the loop wrote. The loop runs in a throwaway
home that is removed afterwards (`--keep-workspace` keeps it), so nothing lands in
your real skill library. If `HERMES_HOME` is set, only the demo session is copied
into `<HERMES_HOME>/state.db`, so `search` can find it.

## Demo

<!-- TODO(demo): embed the animated hermes demo here (`langstage-hermes demo` closing the loop, then `search` finding the session). -->

## Run it standalone

!!! warning "Needs a model key"
    `chat` and the live part of `verify` call the model. The default is
    `anthropic:claude-sonnet-4-6` with `ANTHROPIC_API_KEY`.

<!-- snippet: check -->
```bash
langstage-hermes doctor                 # Python, packages, keys, HERMES_HOME; keyless
langstage-hermes verify                 # offline checks, then one live round-trip
langstage-hermes chat                   # interactive REPL
langstage-hermes chat -a my_agent.py:graph   # chat with a different agent
```

`verify` runs its offline checks first (bundled prompts and skills, a writable
`HERMES_HOME`, the FTS5 store), so a keyless run still tells you the install is
sound. `verify --json` and `doctor --json` print a top-level `ok` plus a per-check
list, and `.ok` matches the exit code, so `langstage-hermes doctor --json | jq -e .ok`
is a one-line gate. Without a key, `verify --json` reports the live round-trip as
`skipped`, so a keyless CI check never makes a paid call. `doctor` also checks the
provider package for the auxiliary (reflection) model when it differs from the main
one.

In `chat`: `/skills`, `/model <id>`, `/memory`, `/compress`, `/quit`.

## Run it on any stage

It's a `CompiledGraph`, so any surface can run it:

<!-- snippet: run server -->
```bash
langstage-cli -a langstage_hermes.agent:graph           # terminal
langstage run --agent langstage_hermes.agent:graph      # web
langstage-jupyter -a langstage_hermes.agent:graph       # JupyterLab
langstage-agui --agent langstage_hermes.agent:graph     # AG-UI endpoint
```

## Look inside, offline

These read local state only: keyless, no model call. Each takes `--json`.

<!-- snippet: check -->
```bash
langstage-hermes search "profile slow python"                 # BM25 matches with highlighted snippets
langstage-hermes search --session <id> --around <msg> --window 5   # a window around one message
langstage-hermes search --browse --limit 20                   # recent sessions
langstage-hermes memory show                                  # USER.md + MEMORY.md, with size vs budget
langstage-hermes memory notes "rollback"                      # what MarkdownProvider would recall
langstage-hermes tools --implemented-only                     # the toolsets and their tools
```

- `search` understands FTS5 syntax: multi-word queries are AND, and `OR`, quoted
  phrases and prefix `wildcards*` work. `--json` snippets are plain text with
  `match_ranges` offsets.
- `memory show` prints each layer's size against its budget. An over-budget layer is
  still injected in full; the agent's `memory` tool just refuses new entries until
  it's trimmed.

## Skills

<!-- snippet: check -->
```bash
langstage-hermes skills list                  # bundled + user skills (--json)
langstage-hermes skills show <name>
langstage-hermes skills validate ./my-skill   # check a SKILL.md without installing; exit 0/1
langstage-hermes skills install ./my-skill    # install a skill directory
langstage-hermes skills audit                 # validate every installed skill
langstage-hermes skills remove <name>         # archive it; prints the exact rollback command
```

**What `install` copies.** Installing a **file** (`SKILL.md`, or a draft with another
name) copies only that file. Installing a **directory** copies the skill's contents
but never hidden entries (`.git`, `.env*`, `.venv`), symlinks, `node_modules`,
`__pycache__`, virtualenvs, `*.egg-info` or compiled Python files, and lists what it
skipped. So pointing it at a messy working directory can't leak secrets into the
agent's context. To ship support files (`references/`, `templates/`, `scripts/`),
install the directory.

A skill needs a `description` and a non-empty body. `validate`, `install` and
`audit` reject one without, and the loader skips it with a warning rather than list
it to the model. Bundled skills can't be removed (hide one with
`skills.disabled` / `LANGSTAGE_HERMES_SKILLS_DISABLED`); when the agent edits a
bundled skill, it edits a copy in your skills directory.

**Plugins.** `langstage-hermes plugins list` shows the plugins discovered from all
four sources.

**Audit log.** Every skill change the agent or the CLI makes is recorded:
`langstage-hermes audit log`, `audit show <id> --diff`, `audit diff`, and
`audit rollback <name> <id>`.

## Curator

The curator marks a skill `stale` after 30 days without use and archives it after
90 (`curator.stale_after_days` / `curator.archive_after_days`). "Use" means the agent actually loaded or edited the skill, not the file's
modification time. Pinned skills and bundled skills are never touched.

<!-- snippet: check -->
```bash
langstage-hermes curator status
langstage-hermes curator run            # a lifecycle pass now
langstage-hermes curator pin <name>     # never archive this one (unpin to undo)
langstage-hermes curator pause          # stop scheduled runs (resume to restart)
```

## Scheduled runs (cron)

<!-- snippet: check -->
```bash
langstage-hermes cron create --prompt "summarize today's notes" --schedule "0 18 * * MON-FRI"
langstage-hermes cron list
langstage-hermes cron run-due           # one tick: run every due job, then exit
langstage-hermes cron daemon            # run forever
```

- `--schedule` takes an interval (`30m`, `every 2h`), a standard cron expression
  (including `MON-FRI`, `JAN`, and `@daily` / `@hourly` / `@weekly`), or a one-shot
  `once at 2026-10-01T09:00`. A one-shot time in the past is refused.
- `pause`, `resume` and `delete` manage jobs. A one-shot job whose run failed stays
  in the list, disabled, with its error.
- A failed run logs one line; set `LANGSTAGE_DEBUG=1` for the traceback. The daemon
  recovers from a lock file left by a crash.

## Picking a model

Any `init_chat_model` string works, via `--model` or `model.default` in
`langstage-hermes.toml`. For OpenAI or OpenRouter:

<!-- snippet: check -->
```bash
pip install "langstage-hermes[openai]"
export OPENAI_API_KEY=sk-…            # or OPENROUTER_API_KEY=sk-or-v1-…
export OPENAI_BASE_URL=https://openrouter.ai/api/v1   # OpenRouter only
langstage-hermes chat --model openai:openai/gpt-4o-mini
```

Set `LANGSTAGE_HERMES_MODEL_AUX` too, so the reflection subagent uses the same
provider. Other extras: `[daytona]`, `[modal]` and `[ssh]` terminal backends.

## Configuration

- **Home.** Skills, memory, `state.db` and cron jobs live in the hermes home:
  `LANGSTAGE_HERMES_HOME`, else `HERMES_HOME`, else `~/.langstage-hermes`. An
  existing `~/.deepagent-hermes` from before the rename keeps being used.
- **Files.** `langstage-hermes.toml` (project) and `$HERMES_HOME/config.toml`
  (global) layer over the defaults, then `LANGSTAGE_HERMES_*` env vars, then CLI
  flags. Relative paths in a TOML file resolve against that file's directory.
- **Inspect.** `langstage-hermes --show-config` prints each value and its source;
  `--show-config --json` prints the same as JSON, with an `issues` list. A malformed
  file is reported as MALFORMED.
- **Legacy names.** `deepagent-hermes.toml`, `DEEPAGENT_HERMES_*` and the
  `deepagent-hermes` command still work and print a one-line deprecation `note:`
  (silence with `LANGSTAGE_SUPPRESS_LEGACY_NOTICE=1`).

The full field list is in
[SPEC §2](https://github.com/dkedar7/langstage-hermes/blob/main/SPEC.md#2-configuration).
