"""Record the documents-stage demo: `langstage-codraft run --demo` (keyless).

Flow (about 25 s): a one-page brief opens in the editor. The author leaves a comment
("make it shorter") on a paragraph and clicks Address all comments. The scripted
co-author proposes an edit, which waits on the block until the author accepts it.
Then the author asks in chat for a new paragraph, and accepts the drafted block.

    python demos/scripts/record_codraft.py   # writes docs/assets/demos/codraft.{gif,webm}
"""
from __future__ import annotations

import json
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

from _common import VIEWPORT, encode, free_port, start, stop, wait_http, which

TYPE_DELAY_MS = 45

TITLE = "Tidal energy brief"
INTRO = ("Tidal power is predictable months ahead, which sets it apart from wind and solar. "
         "The barrier is cost: turbines must survive salt water and strong currents for decades. "
         "Two pilot sites in the region have run for three years without a major failure. "
         "This brief asks whether a third site is worth funding now.")


def post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="langstage-codraft-demo-") as tmp:
        tmp_path = Path(tmp)
        server = start(
            [which("langstage-codraft"), "run", "--demo", "--no-browser", "--port", str(port),
             "--data-dir", str(tmp_path / "data")],
            log=tmp_path / "server.log",
        )
        url = f"http://localhost:{port}"
        try:
            wait_http(f"{url}/api/health")
            did = post(f"{url}/api/docs", {"title": TITLE})["id"]
            post(f"{url}/api/docs/{did}/blocks", {"type": "heading", "content": {"text": TITLE, "level": 1}})
            para = post(f"{url}/api/docs/{did}/blocks", {"type": "text", "content": {"markdown": INTRO}})["id"]

            with sync_playwright() as p:
                browser = p.chromium.launch()
                ctx = browser.new_context(
                    viewport=VIEWPORT,
                    record_video_dir=str(tmp_path / "video"),
                    record_video_size=VIEWPORT,
                )
                t0 = time.monotonic()
                page = ctx.new_page()
                page.goto(f"{url}/d/{did}")
                page.locator(f"[data-block-id={para}]").first.wait_for()
                # More room for the page: hide the document list (the page re-fits its zoom).
                page.get_by_title("Hide the document list").click()
                page.wait_for_timeout(800)
                trim = time.monotonic() - t0
                page.wait_for_timeout(1200)

                # 1. A comment for the agent, then "Address all comments".
                page.locator(f"[data-block-id={para}]").first.click()
                page.wait_for_timeout(500)
                page.click("[data-testid=tab-comments]")
                page.wait_for_timeout(400)
                box = page.locator("[data-testid=comment-input]")
                box.click()
                box.press_sequentially("make it shorter", delay=TYPE_DELAY_MS)
                page.wait_for_timeout(300)
                page.click("[data-testid=comment-add]")
                page.wait_for_timeout(900)
                page.click("[data-testid=address-all]")

                # 2. The suggestion waits on the block; the author reviews and accepts it.
                page.wait_for_selector("[data-testid=suggestion-badge]", timeout=30_000)
                page.wait_for_timeout(1800)
                page.click("[data-testid=suggestion-badge]")
                page.wait_for_timeout(2200)
                page.click("[data-testid=accept-suggestion]")
                page.wait_for_timeout(2000)

                # 3. Ask in chat for a new paragraph; it arrives as a draft block to accept.
                chat = page.locator("[data-testid=chat-input]")
                chat.click()
                chat.press_sequentially("write a paragraph about the funding decision", delay=TYPE_DELAY_MS)
                page.wait_for_timeout(300)
                page.click("[data-testid=chat-send]")
                page.wait_for_selector(".ed-item.virtual", timeout=30_000)
                page.wait_for_timeout(2200)
                page.click("[data-testid=accept-insert]")
                page.wait_for_timeout(3000)

                video = page.video
                ctx.close()
                browser.close()
                raw = Path(video.path())
        finally:
            stop(server)
        encode(raw, "codraft", trim_start=trim, width=820, fps=8)


if __name__ == "__main__":
    main()
