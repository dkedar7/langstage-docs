# VS Code demo: manual recording checklist

The VS Code demo is the one stage the demos workflow cannot record. Driving the
`@langstage` chat participant needs a real VS Code (1.95 or newer, for the chat API),
a signed-in chat view, and the extension installed, and none of that runs headless
on a CI runner. Until someone records it, `docs/assets/demos/vscode.svg` is a
labeled placeholder, and the VS Code page says so.

The shot to get is the **in-chat approval buttons**: an `@langstage` turn pauses on
a human-in-the-loop interrupt and is answered by clicking **Approve**.

## Setup (once)

1. VS Code **1.95 or newer**, with the chat view available.
2. A fresh venv with the latest sidecar:
   `pip install -U langstage-vscode`
3. The latest extension `.vsix`: from the newest
   [langstage-vscode CI run on `main`](https://github.com/dkedar7/langstage-vscode/actions/workflows/ci.yml?query=branch%3Amain),
   download the `langstage-vscode-vsix` artifact, unzip it, then
   `code --install-extension langstage-vscode-<version>.vsix`.
4. In a scratch folder, set VS Code's workspace settings:
   ```json
   {
     "langstage.pythonPath": "<path to the venv's python>",
     "langstage.agentSpec": "langstage_core.demo.tools:graph"
   }
   ```
   This is the keyless rich-frame demo agent, so no API key is involved and the
   run is repeatable.
5. Sanity check from a terminal in that venv:
   `langstage-vscode-sidecar --demo=tools --message "ask me first"` should print the
   interrupt and exit `2`.

## Recording

- Window about **1280x760**, light theme, zoom level 1 (`Ctrl+0`), editor font
  size 14 or more. Close the explorer and the minimap so the chat has room.
- Use a screen recorder that writes MP4 or WebM (OBS, ShareX, or the macOS
  screenshot toolbar). Aim for **15 to 25 seconds**.

Script, typed in the chat view:

1. `@langstage use a tool to look up the answer`: shows a streamed reply with the
   `demo_lookup` tool call.
2. `@langstage ask me before you act`: the turn pauses and shows the
   **Approve / Reject / Respond… / Edit…** buttons.
3. Hover **Approve** for a beat, then click it. The reply resumes with
   `Resumed. Your decision was: ...`.

## Converting and committing

From the repo root, with the raw recording at `raw.mp4` and the start trimmed to
the first keystroke at `SS` seconds:

```bash
ffmpeg -ss SS -i raw.mp4 -vf "fps=10,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -loop 0 docs/assets/demos/vscode.gif
ffmpeg -ss SS -i raw.mp4 -vf "scale=960:-2" -c:v libvpx-vp9 -b:v 0 -crf 40 -an docs/assets/demos/vscode.webm
```

These are the same settings the automated recorders use
(`demos/scripts/_common.py`). Keep the GIF under about 2 MB. Then change the image
in `docs/stages/vscode.md` from `vscode.svg` to `vscode.gif`, drop the placeholder
note there, and update the `langstage-vscode` README image to the GIF URL.
