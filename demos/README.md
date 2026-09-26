# Demo animations

The GIFs and WebMs in `docs/assets/demos/` are generated, not hand-made. Every one
runs a keyless demo agent (no API key, no network) against the **latest PyPI
releases**, so what they show is what `pip install` gives a new user today.
`docs/assets/demos/versions.json` records the exact versions.

| Demo | Source | Tool | Output |
|---|---|---|---|
| `langstage-cli`: tool call, reasoning, approval menu | `tapes/cli.tape` | VHS | `cli.gif` / `cli.webm` |
| `langstage-agui`: `--verify`, `-m`, `--json`, exit 2 on a pause | `tapes/agui.tape` | VHS | `agui.gif` / `agui.webm` |
| `langstage-hermes`: `demo`, `search`, `skills list` | `tapes/hermes.tape` | VHS | `hermes.gif` / `hermes.webm` |
| Web app: tool call, reasoning, Files, Board task | `scripts/record_web.py` | Playwright video + ffmpeg | `web.gif` / `web.webm` |
| JupyterLab: notebook, tool call, Approve | `scripts/record_jupyter.py` | Playwright video + ffmpeg | `jupyter.gif` / `jupyter.webm` |
| VS Code | `vscode/README.md` (manual) | a screen recorder | `vscode.svg` placeholder for now |

The terminal demos use `langstage_core.demo.tools:graph` directly. The browser
demos use `agents/showcase.py`, which is the same agent with host context lines
(`[Current time: …]`, `Currently focused: …`) dropped before it echoes the prompt,
so the recordings don't print a runner's temp paths.

## Regenerate

**In CI (the source of truth).** Run the **Demos** workflow
(Actions > Demos > Run workflow, or `gh workflow run demos.yml`). It records on
`ubuntu-latest` and opens a PR from `demos/refresh` with the new assets. It never
commits to `main`. It also runs:

- weekly, re-recording only when a LangStage release has moved past `versions.json`;
- on a `repository_dispatch` of type `langstage-release`, which a package's release
  workflow can send;
- on PRs that touch `demos/`, where it records and uploads the result as the `demos`
  artifact without opening a PR.

Opening the refresh PR needs either *Allow GitHub Actions to create and approve pull
requests* (Settings > Actions > General) or a `DEMOS_PR_TOKEN` secret.

**Locally (Linux or macOS).** You need Python 3.11+, ffmpeg, and
[VHS](https://github.com/charmbracelet/vhs) with ttyd for the tapes. Then:

```bash
pip install -U -r demos/requirements.txt
python -m playwright install chromium
bash demos/build.sh                # everything
bash demos/build.sh web jupyter    # or a subset: cli agui hermes web jupyter
```

The Playwright recorders also run on Windows (`python demos/scripts/record_web.py`).
VHS needs a Linux-style terminal, so on Windows let CI render the tapes.

## Editing a demo

- Keep each one 10 to 30 seconds, with the GIF under about 2 MB. The build prints
  sizes, and CI warns over 3 MiB.
- The tapes' `Sleep` and `Wait` lines set the pacing. The recorders wait on visible
  text (for example "That completes the"), not on fixed delays, so a slower runner
  gives a longer pause rather than a broken demo.
- The demo agent's trigger phrases are `use a tool`, `think`, and `ask me`
  (`langstage_core.demo.tools`). Anything else is echoed back.
