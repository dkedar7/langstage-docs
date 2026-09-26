"""Record the JupyterLab demo: `langstage-jupyter` with the keyless tool demo agent.

Flow (about 25 s): a notebook is open, the LangStage sidebar streams a reply with a
tool call, then the agent pauses for approval and resumes when Approve is clicked.

    python demos/scripts/record_jupyter.py  # writes docs/assets/demos/jupyter.{gif,webm}
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from _common import REPO, VIEWPORT, encode, free_port, start, stop, wait_http, which

AGENT = str(REPO / "demos" / "agents" / "showcase.py") + ":graph"
TYPE_DELAY_MS = 45

NOTEBOOK = {
    "cells": [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Q3 revenue\n", "A quick look at monthly revenue."]},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
         "source": ["revenue = {'Jul': 120, 'Aug': 135, 'Sep': 151}\n", "growth = revenue['Sep'] / revenue['Jul'] - 1\n", "print(f'Q3 growth: {growth:.0%}')"]},
    ],
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python"}},
    "nbformat": 4,
    "nbformat_minor": 5,
}


def lab_settings(root: Path) -> Path:
    """A throwaway JupyterLab settings dir: no news toast, no restored layout."""
    settings = root / "lab-settings"
    notif = settings / "@jupyterlab" / "apputils-extension"
    notif.mkdir(parents=True)
    (notif / "notification.jupyterlab-settings").write_text(
        json.dumps({"fetchNews": "false", "checkForUpdates": False}), encoding="utf-8")
    return settings


def main() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="langstage-jupyter-demo-") as tmp:
        tmp_path = Path(tmp)
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "analysis.ipynb").write_text(json.dumps(NOTEBOOK, indent=1), encoding="utf-8")
        server = start(
            [which("langstage-jupyter"), "-a", AGENT, "--no-browser", "--port", str(port),
             "--IdentityProvider.token=", f"--ServerApp.root_dir={ws}"],
            log=tmp_path / "jupyter.log",
            cwd=ws,
            env={
                "JUPYTERLAB_SETTINGS_DIR": str(lab_settings(tmp_path)),
                "JUPYTERLAB_WORKSPACES_DIR": str(tmp_path / "lab-workspaces"),
            },
        )
        url = f"http://localhost:{port}"
        try:
            wait_http(f"{url}/api/status", timeout=180)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                ctx = browser.new_context(
                    viewport=VIEWPORT,
                    record_video_dir=str(tmp_path / "video"),
                    record_video_size=VIEWPORT,
                )
                t0 = time.monotonic()
                page = ctx.new_page()
                page.goto(f"{url}/lab/tree/analysis.ipynb?reset")
                page.locator(".jp-Notebook .jp-Cell").first.wait_for(timeout=60_000)
                # Collapse the file browser so the notebook and the chat get the room.
                page.locator("li[data-id='filebrowser']").click()
                page.locator("li[data-id='deepagents-chat']").click()
                box = page.locator("#deepagents-chat textarea").first
                box.wait_for()
                # Widen the right sidebar so chat replies wrap less: drag its left edge.
                right = page.locator("#jp-right-stack").bounding_box()
                if right:
                    x, y = right["x"] - 2, VIEWPORT["height"] / 2
                    page.mouse.move(x, y)
                    page.mouse.down()
                    page.mouse.move(x - 150, y, steps=5)
                    page.mouse.up()
                # Start recording only once the kernel is idle and the agent has loaded.
                page.wait_for_function("() => /Idle/.test(document.querySelector('#jp-main-statusbar')?.innerText || '')", timeout=90_000)
                page.locator("#deepagents-chat").get_by_text("Demo Agent").first.wait_for(timeout=90_000)
                page.wait_for_timeout(1000)
                trim = time.monotonic() - t0
                page.wait_for_timeout(800)

                # Run the code cell so the notebook is live.
                page.locator(".jp-Notebook .jp-CodeCell").first.click()
                page.keyboard.press("Shift+Enter")
                page.locator(".jp-OutputArea-output").get_by_text("Q3 growth", exact=False).first.wait_for(timeout=30_000)
                page.wait_for_timeout(1200)

                def ask(text: str, wait_for: str) -> None:
                    box.click()
                    box.press_sequentially(text, delay=TYPE_DELAY_MS)
                    page.wait_for_timeout(300)
                    box.press("Enter")
                    page.locator("#deepagents-chat").get_by_text(wait_for, exact=False).last.wait_for(timeout=30_000)

                ask("Use a tool to look up the answer", "That completes the")
                page.wait_for_timeout(2500)
                ask("Ask me before you act", "Approve")
                page.wait_for_timeout(2000)
                page.locator("#deepagents-chat").get_by_role("button", name="Approve").click()
                page.locator("#deepagents-chat").get_by_text("Resumed", exact=False).last.wait_for(timeout=30_000)
                page.wait_for_timeout(3000)

                video = page.video
                ctx.close()
                browser.close()
                raw = Path(video.path())
        finally:
            stop(server)
        encode(raw, "jupyter", trim_start=trim)


if __name__ == "__main__":
    main()
