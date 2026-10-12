"""Render an asciinema v2 cast (from record_terminal.py) to the gallery's video.

Plays the cast in xterm.js inside Playwright's Chromium, records it, and encodes it
with the same pipeline as the browser clips. Typing and the output play at real speed;
two kinds of waiting are shortened, and the gallery page says so: idle gaps are capped
(asciinema's "idle time limit"), and each stretch of the CLI's "Thinking..." spinner
plays for at most a moment.

    python demos/gallery/render_cast.py incident.cast incident-investigator
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from _gallery import Clock, encode, record_versions

IDLE_MAX = 2.5  # longest pause kept, in seconds
SPIN_MAX = 1.2  # longest spinner stretch kept, in seconds
FONT_SIZE = 15
SPINNER = re.compile(r"(?:\x1b\[[0-9;?]*[A-Za-z]|\r|[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]|\s|(?:Thinking|Loading agent)\.\.\.|\d+s)*")

# Catppuccin Mocha, the theme the docs' other terminal demos use.
THEME = {
    "background": "#1e1e2e", "foreground": "#cdd6f4", "cursor": "#f5e0dc",
    "black": "#45475a", "red": "#f38ba8", "green": "#a6e3a1", "yellow": "#f9e2af",
    "blue": "#89b4fa", "magenta": "#f5c2e7", "cyan": "#94e2d5", "white": "#bac2de",
    "brightBlack": "#585b70", "brightRed": "#f38ba8", "brightGreen": "#a6e3a1",
    "brightYellow": "#f9e2af", "brightBlue": "#89b4fa", "brightMagenta": "#f5c2e7",
    "brightCyan": "#94e2d5", "brightWhite": "#a6adc8",
}

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap">
<script src="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.js"></script>
<style>
  html, body { margin: 0; background: #11111b; }
  #win { display: inline-block; margin: 18px; border-radius: 10px; overflow: hidden;
         box-shadow: 0 10px 30px rgba(0,0,0,.45); background: __BG__; }
  #bar { height: 30px; background: #181825; display: flex; align-items: center; padding: 0 12px;
         font: 12px -apple-system, Segoe UI, sans-serif; color: #a6adc8; }
  .dot { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
  #title { flex: 1; text-align: center; margin-right: 60px; }
  #term { padding: 12px 14px 14px; }
</style></head><body>
<div id="win"><div id="bar"><span class="dot" style="background:#f38ba8"></span>
<span class="dot" style="background:#f9e2af"></span><span class="dot" style="background:#a6e3a1"></span>
<span id="title">__TITLE__</span></div><div id="term"></div></div>
<script>
const CAST = __CAST__;
window.__ready = false; window.__done = false;
document.fonts.load('__SIZE__px "JetBrains Mono"').then(() => {
  const term = new Terminal({cols: CAST.cols, rows: CAST.rows, fontSize: __SIZE__,
    fontFamily: '"JetBrains Mono", Consolas, monospace', theme: __THEME__,
    cursorBlink: false, allowProposedApi: true, scrollback: 0});
  term.open(document.getElementById('term'));
  window.__ready = true;
  window.__play = () => {
    const t0 = performance.now();
    let i = 0;
    const tick = () => {
      const now = (performance.now() - t0) / 1000;
      while (i < CAST.events.length && CAST.events[i][0] <= now) term.write(CAST.events[i++][1]);
      if (i < CAST.events.length) requestAnimationFrame(tick); else setTimeout(() => window.__done = true, 2500);
    };
    tick();
  };
});
</script></body></html>"""


def load(cast_path: Path) -> tuple[dict, list[tuple[float, str]]]:
    lines = cast_path.read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    events = [(e[0], e[2]) for e in map(json.loads, lines[1:]) if e[1] == "o"]
    return header, events


def compress(events: list[tuple[float, str]]) -> list[tuple[float, str]]:
    """Cap idle gaps at IDLE_MAX and each spinner stretch at SPIN_MAX seconds."""
    spin = [bool(SPINNER.fullmatch(data)) and data.strip() != "" for _, data in events]
    out, t, prev = [], 0.0, None
    i = 0
    while i < len(events):
        if spin[i]:
            j = i
            while j < len(events) and spin[j]:
                j += 1
            start = events[i][0]
            end = events[j][0] if j < len(events) else events[j - 1][0]
            scale = min(1.0, SPIN_MAX / (end - start)) if end > start else 1.0
            if prev is not None:
                t += min(start - prev, IDLE_MAX)
            for k in range(i, j):
                out.append((t + (events[k][0] - start) * scale, events[k][1]))
            t += (end - start) * scale
            prev = end
            i = j
            continue
        ts, data = events[i]
        if prev is not None:
            t += min(ts - prev, IDLE_MAX)
        out.append((t, data))
        prev = ts
        i += 1
    return out


def main() -> None:
    cast_path, stem = Path(sys.argv[1]), sys.argv[2]
    header, events = load(cast_path)
    events = compress(events)
    cast = {"cols": header["width"], "rows": header["height"], "events": events}
    html = (PAGE.replace("__CAST__", json.dumps(cast))
                .replace("__THEME__", json.dumps(THEME))
                .replace("__BG__", THEME["background"])
                .replace("__SIZE__", str(FONT_SIZE))
                .replace("__TITLE__", "on-call — langstage-cli"))
    with tempfile.TemporaryDirectory(prefix="gallery-cast-", ignore_cleanup_errors=True) as tmp:
        page_file = Path(tmp) / "play.html"
        page_file.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Measure the framed terminal first, then record at exactly that size.
            probe = browser.new_page(viewport={"width": 1600, "height": 1000})
            probe.goto(page_file.as_uri())
            probe.wait_for_function("window.__ready", timeout=30_000)
            box = probe.locator("#win").bounding_box()
            probe.close()
            size = {"width": int(box["width"] + 36) // 2 * 2, "height": int(box["height"] + 36) // 2 * 2}
            ctx = browser.new_context(viewport=size, record_video_dir=tmp, record_video_size=size)
            clock = Clock()  # the video starts with the page
            page = ctx.new_page()
            page.goto(page_file.as_uri())
            page.wait_for_function("window.__ready", timeout=30_000)
            page.wait_for_timeout(400)
            trim = max(0.0, clock.now() - 0.3)  # start a beat before playback
            page.evaluate("window.__play()")
            page.wait_for_function("window.__done", timeout=600_000, polling=500)
            video = page.video
            ctx.close()
            browser.close()
            raw = Path(video.path())
            segments = [(trim, None, 1)]
            encode(raw, stem, segments, width=size["width"], gif_width=min(900, size["width"]))
    record_versions(stem, [(0, None, 1)], {"waits": f"idle gaps capped at {IDLE_MAX}s, spinner at {SPIN_MAX}s"},
                    packages=header.get("langstage_versions"))



if __name__ == "__main__":
    main()
