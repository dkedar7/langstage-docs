"""Shared helpers for the gallery recorders.

Unlike the keyless demos in ``demos/scripts``, the gallery runs real agents on a real
model (Claude Sonnet 5), so these recordings are made once, by hand, with a model key,
and committed. CI never re-records them. Each recorder copies its example's seed
workspace into a temp dir, starts the stage on that copy, and drives it.

The key comes from the environment (OPENROUTER_API_KEY or ANTHROPIC_API_KEY); with
1Password: ``OPENROUTER_API_KEY=op://<vault>/<item>/credential op run -- python ...``.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from _common import REPO, VIEWPORT, ffmpeg, free_port, start, stop, wait_http, which  # noqa: E402,F401

GALLERY = REPO / "gallery"
OUT_DIR = REPO / "docs" / "assets" / "gallery"
MODEL = "Claude Sonnet 5"


def seed(example: str, dest: Path) -> Path:
    """Copy ``gallery/<example>/workspace`` to ``dest`` and return it."""
    shutil.copytree(GALLERY / example / "workspace", dest)
    return dest


class Clock:
    """Seconds since the recording started, for marking segment boundaries."""

    def __init__(self) -> None:
        import time

        self._time = time
        self.t0 = time.monotonic()

    def now(self) -> float:
        return self._time.monotonic() - self.t0


def _segments_filter(segments: list[tuple[float, float | None, float]]) -> str:
    """An ffmpeg filter that cuts ``segments`` (start, end or None, speed) and joins them.

    Waiting on the model plays fast; the moments a viewer should read (a request to
    approve, a finished report) play at real speed. The page says it's sped up.
    """
    parts, labels = [], []
    for i, (start, end, speed) in enumerate(segments):
        rng = f"start={start:.2f}" + (f":end={end:.2f}" if end is not None else "")
        parts.append(f"[0:v]trim={rng},setpts=(PTS-STARTPTS)/{speed}[s{i}]")
        labels.append(f"[s{i}]")
    parts.append(f"{''.join(labels)}concat=n={len(segments)}:v=1:a=0[cut]")
    return ";".join(parts)


def encode(raw: Path, stem: str, segments: list[tuple[float, float | None, float]],
           width: int = 1100, fps: int = 10, gif_width: int = 800) -> list[Path]:
    """Cut ``segments`` from ``raw`` and write ``<stem>.webm`` and a ``<stem>.png`` poster.

    The WebM is what the gallery page plays. A GIF of a 40-90 s clip runs 3-8 MB, too
    big to commit, so it's only written with GALLERY_GIF=1 (for a README or a post).
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    webm, gif = OUT_DIR / f"{stem}.webm", OUT_DIR / f"{stem}.gif"
    cut = _segments_filter(segments)
    subprocess.run(
        [ffmpeg(), "-y", "-loglevel", "error", "-i", str(raw),
         "-filter_complex", f"{cut};[cut]scale={width}:-2[out]", "-map", "[out]",
         "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "36", "-row-mt", "1", "-an", str(webm)],
        check=True,
    )
    written = [webm]
    if os.environ.get("GALLERY_GIF") == "1":
        subprocess.run(
            [ffmpeg(), "-y", "-loglevel", "error", "-i", str(raw),
             "-filter_complex",
             f"{cut};[cut]fps={fps},scale={gif_width}:-1:flags=lanczos,split[a][b];"
             "[a]palettegen=max_colors=96:stats_mode=diff[p];"
             "[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle[out]",
             "-map", "[out]", "-loop", "0", str(gif)],
            check=True,
        )
        written.append(gif)
    poster = OUT_DIR / f"{stem}.png"
    subprocess.run(
        [ffmpeg(), "-y", "-loglevel", "error", "-sseof", "-0.5", "-i", str(webm),
         "-frames:v", "1", "-update", "1", str(poster)],
        check=True,
    )
    written.append(poster)
    for p in written:
        print(f"wrote {p.relative_to(REPO)} ({p.stat().st_size / 1e6:.2f} MB)")
    return written


def record_versions(stem: str, segments: list, extra: dict | None = None,
                    packages: dict | None = None) -> None:
    """Record what a gallery clip was made with in docs/assets/gallery/versions.json.

    ``packages`` defaults to this environment's LangStage versions; a terminal clip
    passes the ones it was recorded with (the cast header), not the renderer's.
    """
    path = OUT_DIR / "versions.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if packages is None:
        packages = {}
        for name in ("langstage", "langstage-core", "langstage-cli", "langstage-jupyter", "langstage-vscode"):
            try:
                packages[name] = metadata.version(name)
            except metadata.PackageNotFoundError:
                pass
    speeds = sorted({s for *_, s in segments})
    data[stem] = {"recorded": date.today().isoformat(), "model": MODEL,
                  "speedup": f"{speeds[-1]:g}x while waiting on the model" if speeds[-1] > 1 else "none",
                  "packages": packages, **(extra or {})}
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
