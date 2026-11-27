"""Record the board-update gallery clip: Codraft co-authoring a quarterly update.

Flow: a document with the authors' outline (an opening, three headings, the ask) is
open. Ask the agent to draft Results and Returns from the Q3 numbers; its paragraphs
arrive as suggestions, and the author accepts them. Save a checkpoint, "Sent to
finance". Finance corrects the return rate, so the author leaves a comment and clicks
Address all comments; the agent proposes the edit and the author accepts it. End on
the checkpoint's "changes since" view, the word diff a redline export would carry.

    OPENROUTER_API_KEY=... python demos/gallery/record_board_update.py
    # writes docs/assets/gallery/board-update.{webm,png}

Set GALLERY_SHOTS=<dir> to also save a screenshot at each step for review.
"""
from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from importlib import metadata
from pathlib import Path

from playwright.sync_api import sync_playwright

from _gallery import GALLERY, VIEWPORT, Clock, encode, free_port, record_versions, start, stop, wait_http, which

STEM = "board-update"
FAST = float(os.environ.get("GALLERY_FAST", "3"))  # speed while waiting on the model
TYPE_DELAY_MS = 40
MODEL_TIMEOUT_MS = 300_000
SHOTS = Path(os.environ["GALLERY_SHOTS"]) if os.environ.get("GALLERY_SHOTS") else None

TITLE = "Q3 update for the board"
OPENING = ("Q3 was our best quarter for revenue and our worst for returns. This update covers "
           "both, and asks the board to approve one change before the holiday season.")
ASK = ("Approve $120,000 to move Ridgeline tent poles to a second supplier and extend the "
       "Ridgeline warranty to two years.")
PROMPT = "Draft a short paragraph under Results and one under Returns from the Q3 numbers and the ops notes."
COMMENT = "Finance closed the books: the Q3 return rate was 7.1%, not 6.4%. Please update."


def post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def shot(page, name: str) -> None:
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{STEM}-{name}.png"))


def wait_turn(page) -> None:
    """Wait for the agent's turn to finish: the Send button comes back when it does."""
    page.wait_for_timeout(1500)
    page.locator("[data-testid=chat-send]").wait_for(state="visible", timeout=MODEL_TIMEOUT_MS)
    page.wait_for_timeout(1200)


def accept_pending(page) -> None:
    page.click("[data-testid=tab-review]")
    page.wait_for_timeout(1200)
    if page.locator("[data-testid=accept-all]").count():
        page.click("[data-testid=accept-all]")
    else:
        page.locator("[data-testid=review-accept]").first.click()
    page.wait_for_timeout(1800)


def main() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="gallery-board-", ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        server = start(
            # From the example's folder, so the status chip shows "agent.py:graph", as a
            # reader running it would see, not this machine's path.
            [which("langstage-codraft"), "run", "--agent", "agent.py:graph",
             "--no-browser", "--port", str(port), "--data-dir", str(tmp_path / "data")],
            log=tmp_path / "server.log", cwd=GALLERY / STEM,
        )
        url = f"http://localhost:{port}"
        try:
            wait_http(f"{url}/api/health")
            did = post(f"{url}/api/docs", {"title": TITLE})["id"]
            blocks = f"{url}/api/docs/{did}/blocks"
            post(blocks, {"type": "heading", "content": {"text": TITLE, "level": 1}})
            post(blocks, {"type": "text", "content": {"markdown": OPENING}})
            post(blocks, {"type": "heading", "content": {"text": "Results", "level": 2}})
            post(blocks, {"type": "heading", "content": {"text": "Returns", "level": 2}})
            post(blocks, {"type": "heading", "content": {"text": "What we're asking for", "level": 2}})
            post(blocks, {"type": "text", "content": {"markdown": ASK}})

            with sync_playwright() as p:
                browser = p.chromium.launch()
                ctx = browser.new_context(viewport=VIEWPORT, record_video_dir=str(tmp_path / "video"),
                                          record_video_size=VIEWPORT)
                clock = Clock()
                page = ctx.new_page()
                page.goto(f"{url}/d/{did}")
                page.locator("[data-testid=chat-input]").wait_for()
                page.get_by_title("Hide the document list").click()
                page.wait_for_timeout(800)
                trim = clock.now()
                page.wait_for_timeout(1500)

                # 1. Ask for the two sections; they arrive as suggestions to accept.
                chat = page.locator("[data-testid=chat-input]")
                chat.click()
                chat.press_sequentially(PROMPT, delay=TYPE_DELAY_MS)
                page.wait_for_timeout(300)
                page.click("[data-testid=chat-send]")
                t_sent = clock.now()
                wait_turn(page)
                shot(page, "1-drafted")
                t_drafted = clock.now()
                page.wait_for_timeout(4000)   # read the drafted paragraphs
                accept_pending(page)
                shot(page, "2-accepted")

                # 2. A checkpoint: the version that went to finance.
                page.click("[data-testid=tab-document]")
                page.wait_for_timeout(800)
                name = page.locator("[data-testid=checkpoint-name]")
                name.scroll_into_view_if_needed()
                name.click()
                name.press_sequentially("Sent to finance", delay=TYPE_DELAY_MS)
                page.wait_for_timeout(300)
                page.click("[data-testid=checkpoint-save]")
                page.wait_for_timeout(1800)
                shot(page, "3-checkpoint")

                # 3. Finance corrects a figure: a comment on the Returns paragraph.
                returns = page.locator(".ed-item", has_text="6.4%").first
                returns.click()
                page.wait_for_timeout(500)
                page.click("[data-testid=tab-comments]")
                page.wait_for_timeout(500)
                box = page.locator("[data-testid=comment-input]")
                box.click()
                box.press_sequentially(COMMENT, delay=TYPE_DELAY_MS)
                page.wait_for_timeout(300)
                page.click("[data-testid=comment-add]")
                page.wait_for_timeout(1200)
                page.click("[data-testid=address-all]")
                t_addressed = clock.now()
                page.wait_for_selector("[data-testid=suggestion-badge]", timeout=MODEL_TIMEOUT_MS)
                wait_turn(page)
                t_fixed = clock.now()
                page.locator("[data-testid=suggestion-badge]").first.click()
                page.wait_for_timeout(4000)   # read the proposed edit as a diff
                shot(page, "4-suggestion")
                accept_pending(page)

                # 4. What changed since the checkpoint: the redline's content.
                page.click("[data-testid=tab-document]")
                page.wait_for_timeout(800)
                named = page.locator("[data-testid=checkpoint][data-kind=named]").first
                named.scroll_into_view_if_needed()
                page.wait_for_timeout(1200)
                named.locator("[data-testid=checkpoint-changes]").click()
                page.locator("[data-testid=checkpoint-review]").wait_for(timeout=30_000)
                page.wait_for_timeout(5000)
                shot(page, "5-changes")

                video = page.video
                ctx.close()
                browser.close()
                raw = Path(video.path())
        finally:
            stop(server)
            print((tmp_path / "server.log").read_text(encoding="utf-8", errors="replace")[-2000:])
        segments = [
            (trim, t_sent, 1),             # the outline and the request
            (t_sent, t_drafted, FAST),     # the agent reads the numbers and drafts
            (t_drafted, t_addressed, 1),   # read, accept, checkpoint, comment
            (t_addressed, t_fixed, FAST),  # the agent proposes the correction
            (t_fixed, None, 1),            # the diff, accept, changes since
        ]
        encode(raw, STEM, segments)
        record_versions(STEM, segments, packages={
            n: metadata.version(n) for n in ("langstage-codraft", "langstage-core")})


if __name__ == "__main__":
    main()
