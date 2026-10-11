"""Record the support-triage gallery clip: the web app's Board working a ticket queue.

Flow: ask the agent to work the queue; it starts one background task per ticket and
the Board fills up. Three tickets resolve on their own; the $189 refund lands in
Review. Open it, read the request, approve it, and watch the task finish. End on the
reply it sent.

    OPENROUTER_API_KEY=... python demos/gallery/record_support_triage.py
    # writes docs/assets/gallery/support-triage.{webm,gif,png}

Set GALLERY_SHOTS=<dir> to also save a screenshot at each step for review.
"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from _gallery import GALLERY, VIEWPORT, Clock, encode, free_port, record_versions, seed, start, stop, wait_http, which

STEM = "support-triage"
FAST = float(os.environ.get("GALLERY_FAST", "3"))  # speed while waiting on the model
TYPE_DELAY_MS = 40
MODEL_TIMEOUT_MS = 240_000
SHOTS = Path(os.environ["GALLERY_SHOTS"]) if os.environ.get("GALLERY_SHOTS") else None


def shot(page, name: str) -> None:
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{STEM}-{name}.png"))


def main() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="gallery-triage-", ignore_cleanup_errors=True) as tmp:
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

                # Open the Board beside the chat and widen it so all columns fit.
                page.get_by_role("button", name="Board").click()
                sash = page.locator(".sash-vertical").first.bounding_box()
                if sash:
                    x, y = sash["x"] + sash["width"] / 2, VIEWPORT["height"] / 2
                    page.mouse.move(x, y)
                    page.mouse.down()
                    page.mouse.move(VIEWPORT["width"] * 0.36, y, steps=10)
                    page.mouse.up()
                page.wait_for_timeout(500)
                trim = clock.now()
                page.wait_for_timeout(1000)

                box.click()
                box.press_sequentially("Work through the open support tickets.", delay=TYPE_DELAY_MS)
                page.wait_for_timeout(300)
                box.press("Enter")
                t_sent = clock.now()

                # The agent delegates one task per ticket; wait for the refund to need review.
                review_card = page.get_by_text("T-301", exact=False).last
                review_card.wait_for(timeout=MODEL_TIMEOUT_MS)
                shot(page, "1-delegated")
                page.get_by_text("review", exact=True).first.wait_for(timeout=MODEL_TIMEOUT_MS)
                # Let the other tickets finish too, so the Board tells the whole story.
                deadline = time.monotonic() + MODEL_TIMEOUT_MS / 1000
                while time.monotonic() < deadline:
                    busy = page.get_by_text("running", exact=True).count() + page.get_by_text("queued", exact=True).count()
                    if busy == 0:
                        break
                    page.wait_for_timeout(1000)
                page.wait_for_timeout(1500)
                shot(page, "2-review")

                # Open the paused task: the request, its arguments, and the controls.
                t_open = clock.now()
                page.get_by_text("T-301", exact=False).last.click()
                approve = page.get_by_role("button", name="Approve")
                approve.wait_for(timeout=30_000)
                page.get_by_text("issue_refund", exact=False).last.scroll_into_view_if_needed()
                page.wait_for_timeout(3500)
                shot(page, "3-approval")
                approve.click()
                t_approved = clock.now()

                # The task resumes, refunds, replies, and lands in Done (the detail
                # view's header shows the state; other cards are already done).
                modal = page.locator("div.fixed.inset-0").last
                modal.get_by_text("done", exact=True).wait_for(timeout=MODEL_TIMEOUT_MS)
                t_done = clock.now()
                page.wait_for_timeout(2500)
                shot(page, "4-done")
                page.keyboard.press("Escape")
                page.locator("body").click(position={"x": 10, "y": VIEWPORT["height"] - 10})
                page.wait_for_timeout(1500)
                shot(page, "5-board")

                video = page.video
                ctx.close()
                browser.close()
                raw = Path(video.path())
        finally:
            stop(server)
            print((tmp_path / "server.log").read_text(encoding="utf-8", errors="replace")[-2000:])
        segments = [
            (trim, t_sent, 1),            # the question
            (t_sent, t_open, FAST),       # delegation; the Board fills and settles
            (t_open, t_approved, 1),      # read the refund request, approve it
            (t_approved, t_done, FAST),   # the task resumes and finishes
            (t_done, None, 1),            # the finished task, then the Board
        ]
        encode(raw, STEM, segments)
        record_versions(STEM, segments)


if __name__ == "__main__":
    main()
