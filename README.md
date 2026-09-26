# langstage-docs

Source for the **LangStage** documentation site — *every stage for your
LangGraph agent*.

**Live:** https://dkedar7.github.io/langstage-docs/

Built with [MkDocs](https://www.mkdocs.org/) +
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) (the same
stack FastAPI's docs use). Covers the whole family: `langstage` (web),
`langstage-cli`, `langstage-jupyter`, `langstage-vscode`, `langstage-hermes`,
and the shared `langstage-core` core.

## Local development

```bash
pip install -r requirements.txt
mkdocs serve              # http://127.0.0.1:8000
mkdocs build --strict     # full build; fails on broken internal links / missing images
```

CI runs the same strict build on every PR (see below), so a broken internal link
or a missing `#anchor` fails the PR.

## Deploy

Pushing to `main` triggers `.github/workflows/docs.yml`: a `mkdocs build --strict`
job, then (only if it passes) `mkdocs gh-deploy --strict` publishes the site to
the `gh-pages` branch.

## How the docs stay current

The docs describe six packages that release often (`langstage-core`,
`langstage`, `langstage-cli`, `langstage-hermes`, `langstage-jupyter`,
`langstage-vscode`). Three automated guards keep the site from drifting.

| Workflow | When | What it does |
|---|---|---|
| `checks.yml` | every PR, every push to `main` | `snippets.py lint`; `mkdocs build --strict`; [lychee](https://lychee.cli.rs/) over the built site (internal links, anchors, **external** links, with retries; config in `lychee.toml`); every doc snippet run against the **latest PyPI releases** in a fresh venv |
| `drift.yml` | nightly 09:17 UTC, or on demand (*Actions → Run workflow*) | compares [`versions.json`](versions.json) with PyPI (and with the VS Code extension's `extension-v*` GitHub releases, since the `.vsix` isn't on PyPI), runs the snippets against the latest releases, and opens or updates **one** `Docs sync needed: <pkg> <old>→<new>` issue (label `docs-sync`) with changelog links and any snippet failures. It closes that issue once `versions.json` matches PyPI again. The run goes red if a snippet breaks. |
| `docs.yml` | push to `main` | strict build, then deploy to GitHub Pages |

All three use only the repo's own `GITHUB_TOKEN`.

### Snippet markers

Every fenced code block in `docs/` needs a marker comment directly above it
(invisible on the site). `python scripts/snippets.py lint` fails on an unmarked block,
so a new example can't skip the decision.

````markdown
<!-- snippet: run needs=my_agent.py -->
```bash
langstage-cli --verify -a my_agent.py:graph
```
````

| Mode | Use it for | What CI does |
|---|---|---|
| `run` | anything that works **without an API key** | executes it; it must succeed |
| `check` | needs a key, a placeholder (`<name>`), or has side effects (daemons, installs outside pip) | Python: compiles and runs its imports. Bash: `bash -n`, and every `langstage*` command must exist and list each `--flag`/subcommand used in its `--help`. TOML/JSON: parses. |
| `skip` | illustrative fragments, other shells, CSS, sample output | nothing |

Options (after the mode): `file=NAME` writes the block to that file so later blocks
on the page can use it; `needs=my_agent.py,prompt.md` copies fixtures from
`tests/snippets/fixtures/`; `server[=SEC]` runs each line as its own process and
counts one still running after SEC seconds (default 12) as a healthy server or
interactive session, then kills it; `each` runs each line separately; `exit=0,2`
sets the accepted exit codes; `timeout=SEC`; `no-errexit`. Inside tabs or
admonitions, leave a blank line between the marker and the fence. The full
reference is the docstring of `scripts/snippets.py`.

Blocks on one page run in order in a fresh temp directory with a throwaway
`HOME`. Provider API keys are removed from the environment, so `run` really
means keyless.

Run them locally:

```bash
python -m venv .venv-snippets
.venv-snippets/bin/pip install -r tests/snippets/requirements.txt   # Scripts\ on Windows
python scripts/snippets.py run --python .venv-snippets/bin/python   # all pages
python scripts/snippets.py run --python .venv-snippets/bin/python --page stages/cli.md
```

### When a "Docs sync needed" issue opens

1. Read the linked CHANGELOG sections for each new version, and update the pages
   they affect: new or renamed flags, API changes, output, exit codes.
2. Fix any snippet the issue lists as failing. If an example now legitimately
   needs a key, change its marker to `check`. Don't use `skip` to silence a real
   break.
3. Record the versions you verified against:
   ```bash
   python scripts/drift.py bump                        # latest PyPI for all six
   python scripts/drift.py bump langstage-cli=0.6.37   # or specific versions
   ```
4. Commit `versions.json` together with the doc changes. After merge, the next
   nightly run finds no drift and closes the issue. Dispatch `drift.yml` by hand
   if you want it closed sooner.

A red nightly run with no issue means a snippet broke without a release of the
six packages, usually a dependency (LangGraph, LangChain) moving underneath. The
run summary shows the failing block.
