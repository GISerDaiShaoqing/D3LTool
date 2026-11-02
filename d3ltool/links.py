# -*- coding: utf-8 -*-
"""Download-link handoffs: a plain URL text list and a self-contained HTML
index page.

Both artifacts let the user's own tools do the fetching — a logged-in
browser (plus "Download It All"/DownThemAll-style extensions) for the
HTML page, `wget -i` / `aria2c -i` / download managers for the text
list. This is the modern successor of the v1.0 (2018) browser-automation
path: instead of driving the user's Chrome itself, the program hands
over the list and lets the already-authenticated browser take it — so
no Earthdata password ever passes through the program, chat or MCP."""

import html
import re
from datetime import datetime
from pathlib import Path

from . import i18n

FORMATS = ("txt", "html", "both")


def sanitize_stem(stem) -> str:
    """File-name-safe stem for user/model-supplied names (no separators,
    no traversal, bounded length)."""
    name = re.sub(r'[\\/:*?"<>|\s]+', "_", str(stem or "").strip()).strip("_")
    return name[:120] or "d3ltool_links"


def _fmt_size(n) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def prepare_items(entries):
    """Normalize GUI/tool payloads into display rows. `entries` may be a
    list (or a single dict) of URL strings or dicts (url / filename /
    date / size_bytes / product; a granule dict's first `links` entry
    also counts). Only http(s) URLs survive — anything else is counted
    in `skipped` and never written; duplicate URLs keep their first
    occurrence. Returns (items, skipped); zero usable items raises
    ValueError."""
    if isinstance(entries, dict):
        entries = [entries]
    items = []
    skipped = 0
    seen = set()
    for entry in entries or []:
        if isinstance(entry, dict):
            url = entry.get("url") or (entry.get("links") or [None])[0]
            if isinstance(url, dict):
                url = url.get("url")
            filename = str(entry.get("filename") or "")
            date = str(entry.get("date") or "")
            size = entry.get("size_bytes") or 0
            product = str(entry.get("product") or "")
        else:
            url, filename, date, size, product = str(entry), "", "", 0, ""
        url = str(url).strip() if url else ""
        if not url.lower().startswith(("http://", "https://")):
            skipped += 1
            continue
        if url in seen:
            continue
        seen.add(url)
        if not filename:
            filename = url.rstrip("/").rsplit("/", 1)[-1]
        items.append({"url": url, "filename": filename, "date": date,
                      "size_bytes": size, "product": product})
    if not items:
        raise ValueError("no usable http(s) urls in the list")
    return items, skipped


def write_txt(items, path) -> str:
    """One URL per line, no comments or headers, so the file works as-is
    as `wget -i urls.txt` / `aria2c -i urls.txt` input."""
    text = "\n".join(it["url"] for it in items) + "\n"
    Path(path).write_text(text, encoding="utf-8")
    return str(path)


def write_html(items, path, stem="") -> str:
    """Self-contained page (no external resources): each row links the
    granule file directly, so the browser's own Earthdata session fetches
    it; rows can be selected inline by Download-It-All-style extensions."""
    groups = {}                      # product or "" -> row list, insertion order
    for it in items:
        groups.setdefault(it.get("product", ""), []).append(it)
    note = html.escape(i18n.tr("links_page_note"))
    parts = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8">',
        f"<title>D3LTool · {html.escape(stem or 'links')}</title>",
        "<style>",
        "body{font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,"
        "sans-serif;margin:2em;color:#1f2328}",
        "h1{font-size:1.4em}h2{font-size:1.15em;margin-top:1.8em}",
        "table{border-collapse:collapse;width:100%}",
        "th,td{border:1px solid #d0d7de;padding:4px 10px;text-align:left;"
        "font-size:14px;white-space:nowrap}",
        "td.file{white-space:normal;max-width:460px;word-break:break-all}",
        "a{color:#0969da}a:visited{color:#8250df}",
        ".note{color:#57606a;font-size:13px;max-width:70em}",
        "</style></head><body>",
        f"<h1>{html.escape(i18n.tr('links_page_title'))}</h1>",
        f'<p class="note">{note} · {len(items)} · '
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
    ]
    heads = (html.escape(i18n.tr("links_col_file")),
             html.escape(i18n.tr("links_col_date")),
             html.escape(i18n.tr("links_col_size")))
    shown_rows = []                  # numbered sequentially across all groups
    for product, rows_ in groups.items():
        if len(set(groups)) > 1 and product:
            parts.append(f"<h2>{html.escape(str(product))}</h2>")
        lines = [f"<table><tr><th>#</th><th>{heads[0]}</th>"
                 f"<th>{heads[1]}</th><th>{heads[2]}</th></tr>"]
        for it in rows_:
            n = len(shown_rows) + 1
            shown_rows.append(it["url"])
            lines.append(
                "<tr><td>{}</td><td class=\"file\"><a href=\"{}\">{}</a></td>"
                "<td>{}</td><td>{}</td></tr>".format(
                    n, html.escape(it["url"], quote=True),
                    html.escape(it["filename"]), html.escape(it["date"]),
                    html.escape(_fmt_size(it["size_bytes"])
                                if it["size_bytes"] else "-")))
        lines.append("</table>")
        parts.extend(lines)
    parts.append("</body></html>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")
    return str(path)


def export_links(entries, out_dir, stem="", fmt="both") -> dict:
    """Write the link artifacts and return what was produced.

    entries  — see prepare_items(); str URLs or granule-ish dicts
    out_dir  — target folder (created if missing)
    stem     — filename base (sanitized; default d3ltool_links)
    fmt      — "txt" | "html" | "both"

    Returns {"txt": path|None, "html": path|None, "count": n_kept,
    "skipped": n_bad}. Raises ValueError when nothing survives."""
    if fmt not in FORMATS:
        raise ValueError(
            f"fmt must be one of {FORMATS}, got {fmt!r}")
    items, skipped = prepare_items(entries)
    out_dir = Path(out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = sanitize_stem(stem)
    got = {"txt": None, "html": None}
    if fmt in ("txt", "both"):
        got["txt"] = write_txt(items, out_dir / f"{stem}.txt")
    if fmt in ("html", "both"):
        got["html"] = write_html(items, out_dir / f"{stem}.html", stem)
    got["count"] = len(items)
    got["skipped"] = skipped
    return got
