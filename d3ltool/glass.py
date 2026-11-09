# -*- coding: utf-8 -*-
"""GLASS archive search — the Python port of the author's glass.sqdaitools
R package listing logic.

The GLASS product archive (https://glass.hku.hk/archive/) is a plain public
HTML directory tree: no API, no credentials, no CMR. This module mirrors the
R package's semantics — the variant registry (glass_registry, generated from
the R dataset), composite-DOY expansion (glass_doys "span" mode), directory
listing + filename filters (glass_list_files), bbox -> sinusoidal tiles
(glass_tiles_for_bbox) — so D3LTool can search GLASS with the same row-dict
shape the CMR path's accessor functions understand; downloads then flow
through the shared engine. Post-processing (mosaic / crop / scaling) stays
in the R package on purpose: two packages, one lifecycle.
"""

import math
import re
import time
from datetime import date, timedelta
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

import requests

from . import tiles as _tiles
from . import __version__
from .glass_registry import VARIANTS

GLASS_HOST = "glass.hku.hk"
USER_AGENT = (f"D3LTool/{__version__} (GLASS archive search; "
              "+https://github.com/GISerDaiShaoqing/D3LTool)")

_TILE_FN_RE = re.compile(r"h[0-9]{2}v[0-9]{2}", re.IGNORECASE)
_ATOK_RE = re.compile(r"A[0-9]{7}")   # A{yyyy}{ddd} composite token (year_files)

# glass.hku.hk rate-limits bursts of directory listings (requests fail or
# time out).  Measured politeness policy from the glass.sqdaitools engine:
# exponential backoff retries (8/24/72s) plus a final attempt after a 15s
# cooldown, and at least ~1.2s between any two directory fetches.
# Tests shrink these to zero — patch the module constants, not time.sleep.
LISTING_BACKOFFS = (8.0, 24.0, 72.0)
LISTING_COOLDOWN = 15.0
LISTING_MIN_INTERVAL = 1.2
_LAST_LISTING = [0.0]   # monotonic timestamp of the last listing fetch


class GlassError(ValueError):
    """Unknown GLASS variant / unusable date range (user-fixable)."""


# --------------------------------------------------------------- registry

def is_glass_variant(short_name: str) -> bool:
    """True if the name is a GLASS variant id (case-insensitive)."""
    return (short_name or "").strip().lower() in VARIANTS


def is_glass_url(url: str) -> bool:
    """True for URLs on the public GLASS archive host (no Earthdata needed)."""
    try:
        host = urlsplit(str(url)).hostname or ""
    except ValueError:
        return False
    return host == GLASS_HOST or host.endswith("." + GLASS_HOST)


def get_variant(short_name: str) -> dict:
    vid = (short_name or "").strip().lower()
    v = VARIANTS.get(vid)
    if v is None:
        raise GlassError(
            f"unknown GLASS variant: {short_name!r} — see "
            "list_products(group='GLASS') for the catalog")
    return v


# ------------------------------------------------------------------- doys

def doys(v: dict, start: str, end: str, mode: str = "span") -> list:
    """Port of the R glass_doys(): expand a date range into composite
    (year, doy) folder keys with the variant's cadence.  "span" (default)
    keeps every composite whose interval [begin, begin+cadence-1] intersects
    the range; "start" keeps composites beginning inside the range.  Folder
    start DOYs cap at 365 like the R original (leap years keep folder 365).
    Unknown cadence raises GlassError — search() falls back to a
    listing-derived expansion for those skeleton variants."""
    cad = v.get("cadence_days")
    if not cad:
        raise GlassError(f"cadence unknown for variant {v['variant_id']}; "
                         "composite folders are derived from the archive "
                         "instead")
    d0, d1 = _date_range(start, end)
    out = []
    for year in range(d0.year, d1.year + 1):
        for doy in range(1, 366, cad):
            begin = date(year, 1, 1) + timedelta(days=doy - 1)
            last = begin + timedelta(days=cad - 1)
            if (begin <= d1 and last >= d0) if mode == "span" \
                    else (d0 <= begin <= d1):
                out.append((year, doy))
    return out


def doys_from_listing(v: dict, start: str, end: str, session=None) -> list:
    """Variants without a verified cadence: derive the folders from the
    archive itself and keep those starting inside the range — the R
    package's legacy "start" mode, layout-aware:

    - year_doy: ``{root}/{year}/{ddd}/`` folders (3-digit DOY dirs),
    - year_yyyddd: ``{root}/{year}/{YYYYDDD}/`` folders (7-digit dirs),
    - year_files: granules sit directly under ``{year}/`` — cadence-less
      annual collections have no DOY semantics, so one (year, None) pair
      per year in range; the year folder is listed whole.

    Variants whose root holds no year folders at all (climatology files,
    nested resolutions, retired dirs) raise GlassError."""
    d0, d1 = _date_range(start, end)
    session = session or _get_session()
    root = v["url_root"]
    try:
        years = _dir_names(root, r"^\d{4}$", session)
    except FileNotFoundError:
        raise GlassError(
            f"archive folder not found (404): {root} — the variant "
            "exists in the registry but not on the archive") from None
    if not years:
        raise GlassError(
            f"no year folders under {root} — the archive layout of "
            f"{v['variant_id']} is not year/composite based; browse it "
            "directly or use the glass.sqdaitools R package")
    out = []
    layout = v.get("layout")
    if layout == "year_files":
        for yname in years:
            year = int(yname)
            if d0.year <= year <= d1.year:
                out.append((year, None))
        return out
    doy_pat = r"^\d{7}$" if layout == "year_yyyddd" else r"^\d{3}$"
    for yname in years:
        year = int(yname)
        if year < d0.year or year > d1.year:
            continue
        for dname in _dir_names(f"{root}{year}/", doy_pat, session):
            if layout == "year_yyyddd":
                if int(dname[:4]) != year:
                    continue
                doy = int(dname[4:])
            else:
                doy = int(dname)
            begin = date(year, 1, 1) + timedelta(days=doy - 1)
            if d0 <= begin <= d1:
                out.append((year, doy))
    return out


def _date_range(start: str, end: str):
    d0 = date.fromisoformat(str(start).strip())
    d1 = date.fromisoformat(str(end).strip())
    if d0 > d1:
        raise GlassError(f"start must not be later than end: {start} > {end}")
    return d0, d1


def _dir_names(url: str, pattern: str, session) -> list:
    pat = re.compile(pattern)
    names = []
    for href in _fetch_hrefs(url, session):
        name = href.rstrip("/")
        if name != href and pat.fullmatch(name):
            names.append(name)
    return sorted(names)


# ------------------------------------------------------------------ tiles

def tiles_for_bbox(west: float, south: float, east: float, north: float) -> list:
    """Exact bbox -> [(h, v)] on the sinusoidal grid — the Python twin of the
    R package's glass_tiles_for_bbox().  Tiles are exact rectangles in
    sinusoidal space, so the bbox intersects a tile iff their latitude bands
    overlap and the bbox longitude interval overlaps the tile's longitude
    interval at some latitude inside that overlap.  Both inequalities are
    monotone in |lat| (a tile's edges move outward as cos(lat) shrinks), so
    evaluating each at its analytically hardest latitude inside the overlap
    is exact — no polygon library needed.  Rows reaching into the polar caps
    (|lat| >= 80, where a tile's longitude interval exceeds the row's own
    width and wraps the antimeridian) degrade to whole-row inclusion:
    over-inclusion merely lists tiles with no matching files, under-inclusion
    loses data."""
    west, south, east, north = (float(x) for x in (west, south, east, north))
    if west > east or south > north:
        return []
    out = []
    for v in range(_tiles.N_ROWS):
        lat_max = 90.0 - 10.0 * v
        lat_min = lat_max - 10.0
        lo, hi = max(south, lat_min), min(north, lat_max)
        if lo > hi:
            continue
        if max(abs(lo), abs(hi)) >= 80.0:
            out.extend((h, v) for h in range(_tiles.N_COLS))
            continue
        # |lat| extremes within the overlapping band
        if lo <= 0.0 <= hi:
            m = 0.0
        else:
            m = lo if abs(lo) < abs(hi) else hi
        M = lo if abs(lo) >= abs(hi) else hi
        c_m = max(math.cos(math.radians(m)), 1e-9)
        c_M = max(math.cos(math.radians(M)), 1e-9)
        for h in range(_tiles.N_COLS):
            x0 = (h - 18) * _tiles.TILE_SIZE
            x1 = x0 + _tiles.TILE_SIZE
            if x1 <= 0.0:      # west of the 0 meridian: edges move west with |lat|
                right = math.degrees(x1 / (_tiles.R_SIN * c_M))
                left = math.degrees(x0 / (_tiles.R_SIN * c_m))
            elif x0 >= 0.0:    # east of the 0 meridian: edges move east with |lat|
                right = math.degrees(x1 / (_tiles.R_SIN * c_m))
                left = math.degrees(x0 / (_tiles.R_SIN * c_M))
            else:              # straddles the 0 meridian (h == 17)
                right = math.degrees(x1 / (_tiles.R_SIN * c_m))
                left = math.degrees(x0 / (_tiles.R_SIN * c_m))
            if west <= right and left <= east:
                out.append((h, v))
    return out


# ---------------------------------------------------------------- listing

class _HrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for key, val in attrs:
                if key == "href" and val:
                    self.hrefs.append(val)


def _ext_pattern(ext: str) -> "re.Pattern":
    e = (ext or "hdf").strip().lstrip(".").lower()
    alts = [re.escape(e)]
    if not e.endswith(".xml"):
        alts.append(re.escape(e) + r"\.xml")
    return re.compile(r"(?:\." + r"|\.".join(alts) + r")$")


def list_files(v: dict, year: int = None, doy: int = None, tiles=None,
               ext=None, session=None, fetch=None) -> list:
    """One directory listing — port of the R glass_list_files(): the variant
    folder's <a href>s, subdirectories dropped, filtered by extension (an
    hdf match also keeps '.hdf.xml' sidecars), by tile fragment — only for
    tiled products, global CMG filenames carry no h##v## — and, for verified
    variants, by the registry's real GLASS code prefix (GHOSE03G01 for BBE,
    not every family starts with "GLASS").  year_files variants additionally
    filter by the A{yyyy}{ddd} composite token in the filename when a doy is
    given.  ext=None uses the variant's registry ext (from the R package's
    verified granule samples: .hdf / .tif / .nc / .dat); a missing folder
    raises FileNotFoundError (the cadence math names composite folders the
    archive never filled).  `fetch` lets search() memoize directory pages —
    a year_files year folder would otherwise be re-listed once per day."""
    session = session or _get_session()
    fetch = fetch or _fetch_hrefs
    root = v["url_root"]
    layout = v.get("layout")
    if layout == "flat":
        folder = root
    elif layout == "year_doy":
        if not year or not doy:
            raise GlassError(f"{v['variant_id']} is a year_doy variant: "
                             "year and doy are required")
        folder = f"{root}{int(year)}/{int(doy):03d}/"
    elif layout == "year_files":
        if not year:
            raise GlassError(f"{v['variant_id']} is a year_files variant: "
                             "year is required")
        folder = f"{root}{int(year)}/"
    elif layout == "year_yyyddd":
        if not year or not doy:
            raise GlassError(f"{v['variant_id']} is a year_yyyddd variant: "
                             "year and doy are required")
        folder = f"{root}{int(year)}/{int(year)}{int(doy):03d}/"
    else:
        raise GlassError(f"unknown layout {layout!r} for {v['variant_id']}")

    if ext is None:
        ext = v.get("ext") or "hdf"
    pat = _ext_pattern(ext) if ext else None
    want = {str(t).lower() for t in (tiles or [])}
    if want and not v.get("tiled", True):
        want = set()    # global CMG products: tile filtering must not apply
    code = v.get("code")
    out = []
    for href in fetch(folder, session):
        if href.endswith("/"):
            continue
        filename = unquote(href.split("?")[0].rsplit("/", 1)[-1])
        m = _TILE_FN_RE.search(filename)
        if pat and not pat.search(filename.lower()):
            continue
        if want and (not m or m.group(0).lower() not in want):
            continue
        if layout == "year_files" and doy and \
                f"A{int(year)}{int(doy):03d}" not in filename:
            continue
        if v.get("verified") and code and not filename.startswith(code):
            continue
        f_year, f_doy = year, doy
        if layout == "year_files":
            tok = _ATOK_RE.search(filename)
            if tok:
                f_year, f_doy = int(tok.group(0)[1:5]), int(tok.group(0)[5:8])
            else:
                f_year, f_doy = int(year), None   # annual file, no composite token
        out.append({
            "filename": filename,
            "url": href if href.startswith("http") else folder + href,
            "year": int(f_year) if f_year else None,
            "doy": int(f_doy) if f_doy else None,
            "tile": m.group(0).lower() if m else "",
            "ext": filename.rsplit(".", 1)[-1].lower(),
        })
    return out


# ----------------------------------------------------------------- search

def search(short_name: str, start: str, end: str, tiles=None, bbox=None,
           max_results: int = 200) -> list:
    """GLASS archive search.  Returns the row dicts the CMR path's accessor
    functions understand: {url, filename, date, tile, size_mb, size_bytes,
    product}.  size is 0 — directory listings carry no sizes; the download
    engine HEADs every file anyway.  All four archive layouts are handled:
    year_doy (composite folders), flat (static file collections — dates
    ignored), year_files (granules under {year}/, cadence ones filtered by
    the A{yyyy}{ddd} token) and year_yyyddd (7-digit YYYYDDD day folders).
    Variants without a verified cadence get their folders derived from the
    archive itself (doys_from_listing).  Tile filtering only applies to
    tiled products; global CMG variants ignore tiles/bbox entirely."""
    v = get_variant(short_name)
    layout = v.get("layout")
    want = {str(t).lower() for t in (tiles or [])}
    if bbox:
        west, south, east, north = (float(x) for x in bbox)
        for h, vv in tiles_for_bbox(west, south, east, north):
            want.add(_tiles.tile_name(h, vv))

    session = _get_session()
    if layout == "flat":
        pairs = [(None, None)]   # static collection: dates play no role
    elif layout == "year_files" and not v.get("cadence_days"):
        # cadence-less annual collections (TPSCE, AWGF_LST_GHA-LST): one
        # listing per year inside the range, no composite filter
        d0, d1 = _date_range(start, end)
        pairs = [(y, None) for y in range(d0.year, d1.year + 1)]
    else:
        try:
            pairs = doys(v, start, end)
        except GlassError:
            pairs = doys_from_listing(v, start, end, session=session)

    rows = []
    errors = []
    missing = 0
    # Memoized directory fetches: a year_files year folder holds every
    # composite of the year, so a multi-day range would re-list the same
    # page once per day — the server politely declines that kind of burst.
    memo = {}

    def _memo_fetch(url, _session):
        if url not in memo:
            try:
                memo[url] = _fetch_hrefs(url, _session)
            except Exception as exc:
                memo[url] = exc
                raise
        val = memo[url]
        if isinstance(val, Exception):
            raise val
        return val

    for year, doy in pairs:
        try:
            files = list_files(v, year=year, doy=doy, tiles=want,
                               session=session, fetch=_memo_fetch)
        except FileNotFoundError:
            missing += 1   # sparse composite: the cadence math names folders the archive never filled
            continue
        except requests.RequestException as exc:
            errors.append(f"{year or ''}/{doy or ''}: {exc}")
            continue
        for f in files:
            fy, fd = f["year"], f["doy"]
            if fy and fd:
                date_s = _doy_date(fy, fd).isoformat()
            elif fy:
                date_s = str(fy)   # annual file without a composite token
            else:
                date_s = ""        # flat static layer: no date at all
            rows.append({
                "url": f["url"],
                "filename": f["filename"],
                "date": date_s,
                "tile": f["tile"],
                "size_mb": 0.0,
                "size_bytes": 0,
                "product": v["variant_id"],
            })
            if len(rows) >= max_results:
                return rows
    if not rows and missing and missing == len(pairs):
        # Two very different causes share this symptom: the requested range
        # sits beyond the archive's observed coverage (the GUI default dates
        # are "recent" — GLASS archives lag years behind), or the archive
        # layout really does differ from the registry. The registry carries
        # observed start/end years, so tell them apart.
        if layout == "flat":
            raise GlassError(
                f"GLASS archive folder not found (404): {v['url_root']} — "
                "the variant exists in the registry but not on the archive")
        sy, ey = v.get("start_year"), v.get("end_year")
        if sy and ey and all(y is not None and not (sy <= y <= ey)
                             for y, _ in pairs):
            raise GlassError(
                f"GLASS archive coverage for {v['variant_id']} observed "
                f"{sy}-{ey}; the requested range {start}..{end} has no "
                "composite folders yet — pick an earlier period")
        raise GlassError(
            f"no archive folder found for {v['variant_id']} (all {missing} "
            "listing URLs returned 404 — the archive layout may differ from "
            "the registry)")
    if not rows and errors:
        raise RuntimeError("GLASS archive unreachable: " + errors[0])
    return rows


def _doy_date(year: int, doy: int) -> date:
    return date(year, 1, 1) + timedelta(days=doy - 1)


# ---------------------------------------------------------------- session

_SESSION = None


def _get_session():
    """A plain anonymous session (the archive is public); the configured
    proxy from the settings dialog still applies."""
    global _SESSION
    if _SESSION is None:
        from . import auth

        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT
        auth._apply_configured_proxy(s)
        _SESSION = s
    return _SESSION


def _fetch_hrefs(url: str, session) -> list:
    """All <a href> values of a directory page, with the glass.hku.hk
    politeness policy: consecutive directory fetches are spaced at least
    LISTING_MIN_INTERVAL apart, and transient failures (timeouts, HTTP
    429/5xx — the server's way of rate-limiting) retry on the measured
    exponential backoff 8/24/72s plus one final attempt after a 15s
    cooldown.  404 is never retried: it becomes FileNotFoundError, a normal
    sparse-folder condition for the search loop."""
    waits = (0.0,) + tuple(LISTING_BACKOFFS) + (LISTING_COOLDOWN,)
    last_exc = None
    for wait in waits:
        if wait:
            time.sleep(wait)
        gap = LISTING_MIN_INTERVAL - (time.monotonic() - _LAST_LISTING[0])
        if gap > 0:
            time.sleep(gap)
        try:
            resp = session.get(url, timeout=30)
            _LAST_LISTING[0] = time.monotonic()
            if resp.status_code == 404:
                raise FileNotFoundError(url)
            resp.raise_for_status()
            parser = _HrefParser()
            parser.feed(resp.text)
            parser.close()
            return parser.hrefs
        except requests.RequestException as exc:
            _LAST_LISTING[0] = time.monotonic()
            last_exc = exc
    raise last_exc
