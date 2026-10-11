"""Record the sales-analyst gallery clip: code, inline charts and a Canvas report.

Flow: ask what drove Q3 with the Canvas open beside the chat. The agent writes and
runs pandas in cells, shows Plotly charts inline, and builds the report on the Canvas;
the clip ends scrolling through the finished report.

    OPENROUTER_API_KEY=... python demos/gallery/record_sales_analyst.py
    # writes docs/assets/gallery/sales-analyst.{webm,gif,png}

Set GALLERY_SHOTS=<dir> to also save a screenshot at each step for review.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from _gallery import GALLERY, VIEWPORT, Clock, encode, free_port, record_versions, seed, start, stop, wait_http, which

STEM = "sales-analyst"
FAST = float(os.environ.get("GALLERY_FAST", "3"))
TYPE_DELAY_MS = 35
MODEL_TIMEOUT_MS = 420_000
QUESTION = "What drove Q3 revenue, and is there anything I should worry about? Put the findings on the canvas."
SHOTS = Path(os.environ["GALLERY_SHOTS"]) if os.environ.get("GALLERY_SHOTS") else None


def shot(page, name: str) -> None:
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{STEM}-{name}.png"))


def main() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="gallery-analyst-", ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        ws = seed(STEM, tmp_path / "workspace")
        server = start(
            [which("langstage"), "run", "--agent", f"{GALLERY / STEM / 'agent.py'}:graph",
             "--workspace", str(ws), "--port", str(port), "--no-browser", "--theme", "light"],
            log=tmp_path / "server.log",
        )
        url = f"http://localhost:{port}"
        try:
            wait_http(f"{url}/api/health")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                ctx = browser.new_context(viewport=VIEWPORT, record_video_dir=str(tmp_path / "video"),
                                          record_video_size=VIEWPORT)
                clock = Clock()
                page = ctx.new_page()
                page.goto(url)
                box = page.locator("textarea").first
                box.wait_for()

                # The Canvas beside the chat, at about half the width.
                page.get_by_role("button", name="Canvas").click()
                sash = page.locator(".sash-vertical").first.bounding_box()
                if sash:
                    x, y = sash["x"] + sash["width"] / 2, VIEWPORT["height"] / 2
                    page.mouse.move(x, y)
                    page.mouse.down()
                    page.mouse.move(VIEWPORT["width"] * 0.5, y, steps=10)
                    page.mouse.up()
                page.wait_for_timeout(500)
                trim = clock.now()
                page.wait_for_timeout(1000)

                box.click()
                box.press_sequentially(QUESTION, delay=TYPE_DELAY_MS)
                page.wait_for_timeout(300)
                box.press("Enter")
                t_sent = clock.now()

                # The turn is running while the Stop button shows.
                stop_btn = page.locator("button[title='Stop']")
                stop_btn.wait_for(timeout=30_000)
                try:
                    stop_btn.wait_for(state="detached", timeout=MODEL_TIMEOUT_MS)
                except Exception:
                    shot(page, "error")
                    raise
                t_done = clock.now()
                page.wait_for_timeout(2500)
                shot(page, "2-done")

                # Read the report: scroll the Canvas (its scroll pane is the right half).
                page.mouse.move(VIEWPORT["width"] * 0.75, VIEWPORT["height"] * 0.55)
                for _ in range(16):
                    page.mouse.wheel(0, 240)
                    page.wait_for_timeout(650)
                shot(page, "3-report")
                page.wait_for_timeout(1500)

                video = page.video
                ctx.close()
                browser.close()
                raw = Path(video.path())
        finally:
            stop(server)
        segments = [
            (trim, t_sent, 1),        # the question
            (t_sent, t_done, FAST),   # code, charts, report
            (t_done, None, 1),        # read the finished report
        ]
        encode(raw, STEM, segments)
        record_versions(STEM, segments)


if __name__ == "__main__":
    main()
