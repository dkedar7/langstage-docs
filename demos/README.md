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
| VS Code panel: tool call, reasoning, Approve | [langstage-vscode](https://github.com/dkedar7/langstage-vscode) `extension/test/record/record-demo.ts` (`npm run record`) | Playwright video + ffmpeg | `vscode.gif` / `vscode.webm` |

Every demo uses `langstage_core.demo.tools:graph` directly (the VS Code panel uses the
sidecar's `--demo=tools`, the same agent).

The VS Code demo is recorded by the extension repo's own recorder, so it stays in step
with the panel's UI: `build.sh vscode` clones dkedar7/langstage-vscode at its latest
`extension-v*` release tag (override with `VSCODE_REF=main`, or reuse a clone with
`VSCODE_REPO_DIR=<path>`), runs `npm ci`, `npm run compile` and `npm run record`
against the `langstage-vscode` sidecar installed from PyPI, and copies
`docs/assets/panel-demo.gif|.webm` here. It records the panel's real webview bundle in
the Playwright harness page (styled like VS Code's Dark Modern theme), not a full
editor window. `versions.json` records the tag as `langstage-vscode-extension`, and a
new extension release triggers a re-record like a PyPI release does. Since langstage-core
1.0.39 (#192) the demo agents echo only what was typed, so host context lines
(`[Current time: …]`, `Currently focused: …`) don't leak a runner's temp paths into
the recordings.

## Regenerate

**In CI (the source of truth).** Run the **Demos** workflow
(Actions > Demos > Run workflow, or `gh workflow run demos.yml`; the `targets` input
records a subset, e.g. `-f targets=vscode`). It records on `ubuntu-latest` and, when
run on `main`, opens a PR from `demos/refresh` with the new assets; on any other
branch it only uploads the `demos` artifact. It never commits to `main`. It also runs:

- after each nightly drift-detector run (`drift.yml`), re-recording only when a
  LangStage release has moved past `docs/assets/demos/versions.json`;
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
bash demos/build.sh web jupyter    # or a subset: cli agui hermes web jupyter vscode
```

The `vscode` target also needs git and Node 22.

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
