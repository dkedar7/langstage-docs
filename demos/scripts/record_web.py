"""Record the web-stage demo: `langstage run` with the keyless tool demo agent.

Flow (about 25 s): a streamed reply with a tool call, a reasoning turn, a glance at
the file browser, then a task delegated from the Board tab running to completion.

    python demos/scripts/record_web.py      # writes docs/assets/demos/web.{gif,webm}
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from _common import REPO, VIEWPORT, encode, free_port, start, stop, wait_http, which

AGENT = "langstage_core.demo.tools:graph"
TYPE_DELAY_MS = 45


def seed_workspace(ws: Path) -> None:
    (ws / "README.md").write_text("# Q3 planning\n\nNotes for the demo workspace.\n", encoding="utf-8")
    (ws / "data").mkdir()
    (ws / "data" / "sales.csv").write_text("month,revenue\nJul,120\nAug,135\nSep,151\n", encoding="utf-8")
    (ws / "report.py").write_text("print('hello from the workspace')\n", encoding="utf-8")


def main() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="langstage-web-demo-") as tmp:
        tmp_path = Path(tmp)
        ws = tmp_path / "workspace"
        ws.mkdir()
        seed_workspace(ws)
        server = start(
            [which("langstage"), "run", "-a", AGENT, "--workspace", str(ws), "--port", str(port),
             "--no-browser", "--theme", "light", "--title", "LangStage"],
            log=tmp_path / "server.log",
        )
        url = f"http://localhost:{port}"
        try:
            wait_http(f"{url}/api/health")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                ctx = browser.new_context(
                    viewport=VIEWPORT,
                    record_video_dir=str(tmp_path / "video"),
                    record_video_size=VIEWPORT,
                )
                t0 = time.monotonic()
                page = ctx.new_page()
                page.goto(url)
                box = page.locator("textarea").first
                box.wait_for()
                page.wait_for_timeout(600)
                trim = time.monotonic() - t0
                page.wait_for_timeout(900)

                def ask(text: str, wait_for: str) -> None:
                    box.click()
                    box.press_sequentially(text, delay=TYPE_DELAY_MS)
                    page.wait_for_timeout(300)
                    box.press("Enter")
                    page.get_by_text(wait_for, exact=False).last.wait_for(timeout=30_000)
                    page.wait_for_timeout(2200)

                ask("Use a tool to look up the answer", "That completes the")
                ask("Think it through first", "Done reasoning")

                page.get_by_role("button", name="Files").click()
                page.wait_for_timeout(2200)

                page.get_by_role("button", name="Board").click()
                page.wait_for_timeout(600)
                # Widen the side pane (drag the splitter) so all four board columns fit.
                sash = page.locator(".sash-vertical").first.bounding_box()
                if sash:
                    x, y = sash["x"] + sash["width"] / 2, VIEWPORT["height"] / 2
                    page.mouse.move(x, y)
                    page.mouse.down()
                    page.mouse.move(VIEWPORT["width"] * 0.4, y, steps=20)
                    page.mouse.up()
                page.wait_for_timeout(700)
                task_box = page.get_by_placeholder("Describe a task", exact=False)
                task_box.click()
                task_box.press_sequentially("Use a tool to check the sales numbers", delay=TYPE_DELAY_MS)
                page.wait_for_timeout(300)
                page.get_by_role("button", name="Run").click()
                page.wait_for_timeout(1500)
                # Let the card leave "running" (it lands in Review), then hold a beat.
                try:
                    page.get_by_text("running", exact=True).wait_for(state="detached", timeout=15_000)
                except Exception:
                    pass
                page.wait_for_timeout(3000)

                video = page.video
                ctx.close()
                browser.close()
                raw = Path(video.path())
        finally:
            stop(server)
        encode(raw, "web", trim_start=trim)


if __name__ == "__main__":
    main()
