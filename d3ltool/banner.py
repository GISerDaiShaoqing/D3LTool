# -*- coding: utf-8 -*-
"""Startup banner: block-letter ASCII art of D3LTool + version line.

Claude-Code-inspired: a short animated star cycle, then the teal block
logo (echoing the app icon) and the version/tagline.  Pure stdout ANSI —
never touches files or network.  When the stream is not a TTY (MCP
stdio, pipes, CI) it degrades to the same art without color codes so
machine-readable flows stay clean.  Windows: ``os.system("")`` flips on
VT processing in legacy conhost; Windows Terminal has it on already."""

import os
import sys
import time

from . import __version__

_FRAMES = ("✻", "✳", "✼", "✽", "✻", "✳")
_TAGLINE = "search & download NASA data — MODIS / VIIRS / MERRA-2 / GLASS"

# solid pixel glyphs (5 rows) — 实心块风格（贴作者示例图的观感），比描边
# figlet 的"3"好读得多。全名 D3LTool 在版本行。
_GLYPHS = {
    "D": ("██████ ", "█    ██", "█    ██", "█    ██", "██████ "),
    "3": (" ██████", "     ██", " ██████", "     ██", " ██████"),
    "L": ("█      ", "█      ", "█      ", "█      ", "███████"),
}

_LOGO_COLOR = "\x1b[38;5;79m"    # teal — the app icon's green
_RESET = "\x1b[0m"


def _art_lines(colored: bool) -> list:
    rows = ["", "", "", "", ""]
    for ch in "D3L":
        glyph = _GLYPHS[ch]
        for i in range(5):
            rows[i] += glyph[i] + " "
    if colored:
        return [_LOGO_COLOR + r + _RESET for r in rows]
    return rows


def show_banner(stream=None, animate: bool = True, delay: float = 0.12) -> None:
    stream = stream or sys.stdout
    try:
        tty = stream.isatty()
    except Exception:
        tty = False
    colored = tty
    if not tty and os.name == "nt":
        pass                     # pipes/CI: plain text, no ANSI
    elif tty and os.name == "nt":
        os.system("")            # legacy conhost: enable ANSI VT processing
    version = f"D3LTool v{__version__} — {_TAGLINE}"
    lines = _art_lines(colored)
    lines.append(f"✻ {version}" if colored else version)
    if not tty or not animate:
        stream.write("\n".join(lines) + "\n")
        stream.flush()
        return
    try:
        for frame in _FRAMES:
            stream.write(f"\r{frame} {version}   ")
            stream.flush()
            time.sleep(delay)
        stream.write("\r" + "\n".join(lines) + "\n")
        stream.flush()
    except Exception:
        stream.write("\n".join(_art_lines(False)) + "\n" + version + "\n")
        stream.flush()
