"""Shared helpers for the browser demo recorders (web + JupyterLab).

Every recorder follows the same shape: start a LangStage surface against a keyless
demo agent on a free port, drive it with Playwright while `recordVideo` captures the
page, then trim the warm-up and convert the WebM to a small GIF with ffmpeg.
"""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "assets" / "demos"

# One viewport for every browser demo: wide enough for the web app's two panes,
# small enough that the GIF stays legible when the docs theme scales it down.
VIEWPORT = {"width": 1280, "height": 760}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_http(url: str, timeout: float = 90.0) -> None:
    """Poll ``url`` until it answers (any status below 500) or ``timeout`` passes."""
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status < 500:
                    return
        except urllib.error.HTTPError as e:
            if e.code < 500:
                return
            last = e
        except Exception as e:  # connection refused while the server boots
            last = e
        time.sleep(0.5)
    raise TimeoutError(f"{url} did not come up in {timeout}s (last error: {last})")


def start(cmd: list[str], log: Path, cwd: Path | None = None, env: dict | None = None) -> subprocess.Popen:
    """Start a server process in its own process group, logging to ``log``."""
    full_env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    fh = open(log, "w", encoding="utf-8")
    print("$", " ".join(cmd), flush=True)
    return subprocess.Popen(cmd, cwd=cwd, env=full_env, stdout=fh, stderr=subprocess.STDOUT, **kwargs)


def stop(proc: subprocess.Popen) -> None:
    """Stop ``proc`` and everything it spawned (jupyter kernels, uvicorn workers)."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=10)
        except Exception:
            os.killpg(proc.pid, signal.SIGKILL)


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg not found on PATH")
    return exe


def encode(raw_video: Path, stem: str, trim_start: float, width: int = 960, fps: int = 10) -> list[Path]:
    """Trim the warm-up off ``raw_video`` and write ``<stem>.gif`` + ``<stem>.webm``.

    The GIF uses a two-pass palette (palettegen/paletteuse) so UI text stays crisp;
    the WebM is a small, sharper copy for pages that prefer <video>.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gif = OUT_DIR / f"{stem}.gif"
    webm = OUT_DIR / f"{stem}.webm"
    ss = f"{max(trim_start, 0):.2f}"
    scale = f"fps={fps},scale={width}:-1:flags=lanczos"
    subprocess.run(
        [ffmpeg(), "-y", "-loglevel", "error", "-ss", ss, "-i", str(raw_video),
         "-vf", f"{scale},split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];"
                "[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
         "-loop", "0", str(gif)],
        check=True,
    )
    subprocess.run(
        [ffmpeg(), "-y", "-loglevel", "error", "-ss", ss, "-i", str(raw_video),
         "-vf", f"scale={width}:-2", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "40",
         "-row-mt", "1", "-an", str(webm)],
        check=True,
    )
    for p in (gif, webm):
        print(f"wrote {p.relative_to(REPO)} ({p.stat().st_size / 1e6:.2f} MB)")
    return [gif, webm]


def which(name: str) -> str:
    """Resolve a console script, preferring the one next to this interpreter."""
    here = Path(sys.executable).parent
    for cand in (here / name, here / f"{name}.exe"):
        if cand.exists():
            return str(cand)
    exe = shutil.which(name)
    if not exe:
        sys.exit(f"{name} not found; install the LangStage packages first (see demos/README.md)")
    return exe
