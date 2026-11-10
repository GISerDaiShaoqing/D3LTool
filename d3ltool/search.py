# -*- coding: utf-8 -*-
"""CMR granule search on top of earthaccess."""

import re
from dataclasses import dataclass, field
from urllib.parse import unquote


@dataclass
class SearchParams:
    short_name: str
    start: str                 # YYYY-MM-DD (inclusive)
    end: str                   # YYYY-MM-DD (inclusive)
    version: str = ""          # CMR version, e.g. "6.1"; empty = latest
    tiles: list = field(default_factory=list)   # ["h04v03", ...]
    bbox: tuple = None         # (west, south, east, north) degrees
    max_results: int = 200


def build_query(p: SearchParams) -> dict:
    q = {
        "short_name": p.short_name.strip().upper(),
        "temporal": (p.start, p.end),
        "count": int(p.max_results),
    }
    if p.version:
        q["version"] = str(p.version).strip()
    if p.tiles:
        q["readable_granule_name"] = [f"*.{t.lower()}.*" for t in p.tiles]
    if p.bbox:
        q["bounding_box"] = tuple(p.bbox)
    return q


def run_search(p: SearchParams, searcher=None, progress=None,
               cancelled=None) -> list:
    """Execute the search. `searcher` is injectable for tests; `progress`
    (done, total, label) and `cancelled` are cooperative-search hooks used
    by the GUI for GLASS archive queries (which list real directories and
    can take minutes over multi-year daily data).

    GLASS variants route to the public glass.hku.hk directory search
    (d3ltool.glass) instead of CMR — same row dicts downstream, but plain
    dicts rather than earthaccess granules."""
    if is_glass_variant(p.short_name):
        from . import glass

        return glass.search(p.short_name, p.start, p.end, tiles=p.tiles,
                            bbox=p.bbox, max_results=p.max_results,
                            progress=progress, cancelled=cancelled)
    if searcher is None:
        import earthaccess
        searcher = earthaccess.search_data

    query = build_query(p)
    try:
        granules = searcher(**query) or []
    except Exception:
        if not query.get("version"):
            raise
        granules = None
    if not granules and query.get("version"):
        # CMR may not carry the requested version (e.g. retired collections):
        # retry against the latest version.
        query.pop("version")
        granules = searcher(**query) or []

    if p.tiles:
        # belt & braces in case the name pattern was ignored server-side
        pats = tuple(t.lower() for t in p.tiles)

        def _has_tile(g):
            haystack = (granule_filename(g) + " " + granule_name(g)).lower()
            return any(pt in haystack for pt in pats)

        granules = [g for g in granules if _has_tile(g)]
    return granules


def parse_tiles(text: str) -> list:
    """Parse 'h04v03, h26v05' (comma/space separated) -> ['h04v03', 'h26v05']."""
    from . import tiles

    out = []
    for token in re.split(r"[,\s;]+", (text or "").strip()):
        if not token:
            continue
        h, v = tiles.parse_tile(token)
        name = tiles.tile_name(h, v)
        if name not in out:
            out.append(name)
    return out


def parse_bbox(text: str):
    """Parse 'west,south,east,north' -> (west, south, east, north) or None."""
    text = (text or "").strip()
    if not text:
        return None
    parts = [x for x in re.split(r"[,\s]+", text) if x]
    if len(parts) != 4:
        raise ValueError(f"bbox needs 4 values west,south,east,north: {text!r}")
    w, s, e, n = (float(x) for x in parts)
    if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s <= 90 and -90 <= n <= 90):
        raise ValueError(f"bbox out of range: {text!r}")
    if w >= e or s >= n:
        raise ValueError(f"bbox must be west<east, south<north: {text!r}")
    return (w, s, e, n)


def is_glass_variant(short_name: str) -> bool:
    """GLASS variant ids route to the public glass.hku.hk search, not CMR."""
    from . import glass

    return glass.is_glass_variant(short_name)


def _is_row(g) -> bool:
    """GLASS search results are plain row dicts {url, filename, ...};
    CMR granules are earthaccess objects or UMM dicts carrying umm/meta."""
    return isinstance(g, dict) and "url" in g \
        and "umm" not in g and "meta" not in g


def granule_name(g) -> str:
    if _is_row(g):
        return str(g.get("filename") or "")
    try:
        return g["meta"]["native-id"]
    except (KeyError, TypeError, IndexError):
        return ""


def granule_date(g) -> str:
    if _is_row(g):
        return str(g.get("date") or "")
    try:
        return str(g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"])[:10]
    except (KeyError, TypeError, IndexError):
        return ""


def granule_size_mb(g) -> float:
    """Size in MB. earthaccess <0.19 exposes size() as a method, >=0.19 as property."""
    if _is_row(g):
        try:
            return round(float(g.get("size_mb") or 0), 1)
        except (TypeError, ValueError):
            return 0.0
    val = None
    try:
        val = g.size()
    except TypeError:
        try:
            val = g.size
        except Exception:
            val = None
    except Exception:
        return 0.0
    try:
        return round(float(val), 1)
    except (TypeError, ValueError):
        return 0.0


def granule_links(g) -> list:
    """HTTPS GET DATA links (never s3:// or OPeNDAP), in metadata order."""
    if _is_row(g):
        return [g["url"]] if g.get("url") else []
    out = []
    try:
        for r in g["umm"].get("RelatedUrls", []):
            url = r.get("URL", "")
            if url.startswith("http") and r.get("Type") == "GET DATA":
                out.append(url)
    except (KeyError, TypeError, AttributeError):
        pass
    if not out:
        try:
            out = [l for l in g.data_links() if isinstance(l, str) and l.startswith("http")]
        except Exception:
            out = []
    return out


def granule_filename(g) -> str:
    if _is_row(g):
        return str(g.get("filename") or "granule")
    links = granule_links(g)
    if links:
        base = links[0].split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        if base:
            return unquote(base)
    name = granule_name(g)
    return (name.rsplit(":", 1)[-1] if name else "granule") + ".bin"


def granule_tile(g) -> str:
    if _is_row(g):
        return str(g.get("tile") or "")
    for source in (granule_filename(g), granule_name(g)):
        m = re.search(r"[hH]\d{2}[vV]\d{2}", source)
        if m:
            return m.group(0).lower()
    return ""
