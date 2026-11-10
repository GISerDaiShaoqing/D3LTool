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
# Composite-date tokens for filenames lying directly inside a year folder
# (the archive's real layout for ~50 cadence-less variants — NOT year/DOY/):
# month codes "201801" (NDVI/EVI 0.25°, one per month, never a 3rd digit),
# and bare 7-digit yyyyddd tails ("GLASSxxB01.Q10.2018217.hdf").  Priority
# when both appear: the A-header wins, otherwise the FIRST match in the
# filename — NDVI0.25's trailing "2023068" is the processing date, the
# month code "201801" sits before it in the name and must win.
_MONTH_RE = re.compile(r"(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?![0-9])")
_TAILC_RE = re.compile(r"(?:19|20)\d{2}\d{3}(?![0-9])")
_YEAR_DIR_RE = re.compile(r"(?:18|19|20)\d{2}")   # 4-digit year directory
_DOY_DIR_RE = re.compile(r"\d{3}")               # 3-digit DOY directory

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


class GlassCancelled(RuntimeError):
    """Search aborted by the user (cooperative cancellation flag)."""


# search() installs the caller's cancelled() callable here so the deep
# listing/backoff loops can bail out promptly; None while no search runs.
_CANCELLED = [None]


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


def _parse_composite(filename: str):
    """Composite start carried by a filename lying directly inside a year
    folder: ("doy", year, doy) from the A{yyyy}{ddd} header (FVC/Albedo/
    NPP...), ("month", year, month) from a yyyyMM code (NDVI/EVI 0.25°), or
    ("doy", year, doy) from a bare 7-digit yyyyddd tail.
    A-header wins; otherwise the FIRST match in the name (NDVI0.25 carries
    the processing date "2023068" later in the name — the month code "201801"
    sits before it and must win).  None when no composite token exists."""
    m = _ATOK_RE.search(filename)
    if m:
        tok = m.group(0)
        return "doy", int(tok[1:5]), int(tok[5:8])
    cands = []
    for mm in _MONTH_RE.finditer(filename):
        ym = mm.group(0)
        cands.append((mm.start(), "month", int(ym[0:4]), int(ym[4:6])))
    for tc in _TAILC_RE.finditer(filename):
        tok = tc.group(0)
        cands.append((tc.start(), "doy", int(tok[0:4]), int(tok[4:7])))
    if not cands:
        return None
    return min(cands, key=lambda c: c[0])[1:]


def list_files(v: dict, year: int = None, doy: int = None, tiles=None,
               ext=None, session=None, fetch=None, _folder=None) -> list:
    """One directory listing — port of the R glass_list_files(): the variant
    folder's <a href>s, subdirectories dropped, filtered by extension (an
    hdf match also keeps '.hdf.xml' sidecars), by tile fragment — only for
    tiled products, global CMG filenames carry no h##v## — and, for verified
    variants, by the registry's real GLASS code prefix (GHOSE03G01 for BBE,
    not every family starts with "GLASS").  year_files variants additionally
    filter by the A{yyyy}{ddd} composite token in the filename when a doy is
    given; cadence-less year_doy variants whose files lie directly inside a
    year folder (FVC, Albedo AVHRR/MIX, NPP...) are listed through the
    private ``_folder`` escape hatch — search() resolved that address
    itself, and per-file composite dates come from _parse_composite().
    ext=None uses the variant's registry ext (from the R package's
    verified granule samples: .hdf / .tif / .nc / .dat); a missing folder
    raises FileNotFoundError (the cadence math names composite folders the
    archive never filled).  `fetch` lets search() memoize directory pages —
    a year_files year folder would otherwise be re-listed once per day."""
    session = session or _get_session()
    fetch = fetch or _fetch_hrefs
    root = v["url_root"]
    layout = v.get("layout")
    folder = _folder
    if _folder:
        pass
    elif layout == "flat":
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
        f_year, f_doy, f_month = year, doy, None
        if layout == "year_files":
            tok = _ATOK_RE.search(filename)
            if tok:
                f_year, f_doy = int(tok.group(0)[1:5]), int(tok.group(0)[5:8])
            else:
                f_year, f_doy = int(year), None   # annual file, no composite token
        elif layout == "year_doy" and _folder:
            pt = _parse_composite(filename)   # files lie flat inside {year}/
            if pt:
                kind, f_year, val = pt
                if kind == "doy":
                    f_doy = val
                else:
                    f_month = val
            else:
                f_year, f_doy = int(year), None
        out.append({
            "filename": filename,
            "url": href if href.startswith("http") else folder + href,
            "year": int(f_year) if f_year else None,
            "doy": int(f_doy) if f_doy else None,
            "month": int(f_month) if f_month else None,
            "tile": m.group(0).lower() if m else "",
            "ext": filename.rsplit(".", 1)[-1].lower(),
        })
    return out


# ----------------------------------------------------------------- search

def search(short_name: str, start: str, end: str, tiles=None, bbox=None,
           max_results: int = 200, progress=None, cancelled=None) -> list:
    """GLASS archive search.  Returns the row dicts the CMR path's accessor
    functions understand: {url, filename, date, tile, size_mb, size_bytes,
    product}.  size is 0 — directory listings carry no sizes; the download
    engine HEADs every file anyway.  All four archive layouts are handled:
    year_doy (composite folders), flat (static file collections — dates
    ignored), year_files (granules under {year}/, cadence ones filtered by
    the A{yyyy}{ddd} token) and year_yyyddd (7-digit YYYYDDD day folders).
    Variants without a verified cadence self-adapt to the real archive
    layout (_search_year_doy_adaptive).  Tile filtering only applies to
    tiled products; global CMG variants ignore tiles/bbox entirely.

    progress(done, total, label) is called once per directory listing the
    search performs — daily cadences spanning years mean thousands of
    listings, so the caller should surface this.  cancelled() returning
    truthy aborts cooperatively (GlassCancelled), checked between listings
    and inside the politeness backoff waits."""
    _CANCELLED[0] = cancelled
    try:
        return _search_impl(short_name, start, end, tiles, bbox, max_results,
                            progress, cancelled)
    finally:
        _CANCELLED[0] = None


def _search_impl(short_name, start, end, tiles, bbox, max_results,
                 progress, cancelled) -> list:
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
    elif layout == "year_doy" and not v.get("cadence_days"):
        # ~50 verified variants (FVC, Albedo AVHRR/MIX, PAR, RN, SM, NDVI/EVI
        # 0.25°, NPP…): the label says year_doy, the archive often does not
        # (files flat in the year folder, month codes, version wrappers) —
        # self-adapt from real listings instead of a cadence guess.
        return _search_year_doy_adaptive(v, start, end, want, session,
                                         max_results, progress=progress,
                                         cancelled=cancelled)
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

    total = max(len(pairs), 1)
    done = 0
    for year, doy in pairs:
        if cancelled and cancelled():
            raise GlassCancelled("GLASS search cancelled")
        done += 1
        if progress:
            label = f"{year}/{doy:03d}" if doy else \
                (str(year) if year else v["url_root"])
            try:
                progress(done, total, label)
            except Exception:
                pass
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
    if not rows and not missing and not errors and layout == "flat":
        # listing succeeded but every entry was a subdirectory — never a
        # silent empty table.  Two measured shapes sit behind this: ABI
        # climatology roots in 365 day folders; HiGLASS 20m (HR) files live
        # one level deeper in 1-degree band folders like n018e108/.
        raise GlassError(
            f"no data files under {v['url_root']} — the collection root "
            "holds only subdirectories (ABI's 365 day folders, or HiGLASS "
            "20m's 1-degree band folders like n018e108/); browse it "
            "directly or use the glass.sqdaitools R package")
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


def _search_year_doy_adaptive(v: dict, start: str, end: str, want: set,
                              session, max_results: int, progress=None,
                              cancelled=None) -> list:
    """Search the ~50 verified variants labelled year_doy without a verified
    cadence (FVC, Albedo AVHRR/MIX/0.5D, PAR, RN, SM, NDVI/EVI 0.25°,
    NPP, …).  The 2026-06 skeleton scan trusted the res-directory for the
    year/DOY layout, but live listings show the archive really organizes
    these products four different ways:

    1. composite files flat inside ``{year}/`` — FVC "GLASS10G02.V40.
       A2018001.2021040.hdf" (8-day), PAR/RN/SM/DSR daily,
    2. month codes inside ``{year}/`` — NDVI/EVI 0.25° "GLASS13J01.
       201801.V10.2023068.hdf" (12 per year; the trailing 7-digit token is
       the processing date, the month code sits first),
    3. DOY subdirectories under ``{year}/`` — the layout the label assumed
       (a few MODIS families),
    4. a version wrapper between root and years — NPP roots hold
       GLASS_NPP_0.05D_V40/ beside GLASS_NPP_0.05D_YEARLY_V40/.

    Instead of trusting the registry's cadence, every year folder in the
    range is listed ONCE (memoized), per-file composite dates come from
    _parse_composite(), and the stride is the smallest gap between
    consecutive composite starts in any year — the measured cadence.  Span
    semantics like the registered variants: [begin, begin+stride-1] must
    intersect the range; month files span their calendar month; a year that
    yields a single composite (or one undated file — an annual product)
    keeps it for the whole year.  A 404 year folder triggers a one-level
    wrapper probe (root subdirectory whose name contains the root path's
    resolution segment, "YEARLY" wrappers demoted); sparse 404 years and
    missing composite folders are the archive's normal gaps, never retried.
    Registered-cadence variants never reach this path."""
    d0, d1 = _date_range(start, end)
    root = v["url_root"]
    memo = {}

    def _memo(url, _session=None):
        if url in memo:
            val = memo[url]
            if isinstance(val, Exception):
                raise val
            return val
        try:
            val = _fetch_hrefs(url, session)
        except Exception as exc:
            memo[url] = exc
            raise
        memo[url] = val
        return val

    def _listed_dirs(folder) -> list:
        return sorted(n.rstrip("/") for n in _memo(folder) if n.endswith("/"))

    wrap = [None, False]   # [wrapper name or None, probe attempted]

    def _wrapper_dir():
        """First tier under root whose name echoes the root path's resolution
        segment — NPP's GLASS_NPP_0.05D_V40 inside NPP/AVHRR/0.05D/."""
        if wrap[0] is not None:
            return wrap[0]
        seg = urlsplit(root).path.rstrip("/").rsplit("/", 1)[-1].lower()
        try:
            dirs = _listed_dirs(root)
        except Exception:
            dirs = []
        cands = [d for d in dirs if not _YEAR_DIR_RE.fullmatch(d)
                 and seg and seg in d.lower()]
        keep = [c for c in cands if "YEARLY" not in c.upper()] or cands
        wrap[0], wrap[1] = (keep[0] if keep else None), True
        return wrap[0]

    def _year_folder(year: int) -> str:
        if wrap[1] and wrap[0]:
            return f"{root}{wrap[0]}/{year}/"
        if not wrap[1]:
            folder = f"{root}{year}/"
            try:
                _memo(folder)
                return folder
            except FileNotFoundError:
                _wrapper_dir()   # resolve once; later years skip the probe
        if wrap[0]:
            return f"{root}{wrap[0]}/{year}/"   # 404 propagates → sparse year
        raise FileNotFoundError(f"{root}{year}/")

    try:
        year_list = _listed_dirs(root)
    except FileNotFoundError:
        raise GlassError(
            f"archive folder not found (404): {root} — the variant exists "
            "in the registry but not on the archive") from None
    typed = sorted(int(n) for n in year_list if _YEAR_DIR_RE.fullmatch(n))
    if not typed:
        w = _wrapper_dir()
        if w:
            try:
                typed = sorted(int(n) for n in _listed_dirs(f"{root}{w}/")
                               if _YEAR_DIR_RE.fullmatch(n))
            except FileNotFoundError:
                typed = []
    if not typed:
        raise GlassError(
            f"no year folders under {root} — the archive layout of "
            f"{v['variant_id']} is not year/composite based; browse it "
            "directly or use the glass.sqdaitools R package")
    years = [y for y in typed if d0.year <= y <= d1.year]
    if not years:
        raise GlassError(
            f"GLASS archive coverage for {v['variant_id']} observed "
            f"{typed[0]}-{typed[-1]}; the requested range {start}..{end} "
            "has no year folders — pick a period inside it")

    # pass 1 — one listing per year folder: composite subdirectories, or the
    # year folder holds the files itself (ext/code/tile filters still apply)
    plans = {}    # year -> (folder, 3-digit DOY subdirs)
    file_rows = {}
    missing = 0
    errors = []
    for year in years:
        if cancelled and cancelled():
            raise GlassCancelled("GLASS search cancelled")
        if progress:
            try:
                progress(years.index(year) + 1, len(years), f"{year}/")
            except Exception:
                pass
        try:
            folder = _year_folder(year)
            hrefs = _memo(folder)
        except FileNotFoundError:
            missing += 1
            continue
        except requests.RequestException as exc:
            errors.append(f"{year}: {exc}")
            continue
        dirs3 = sorted(int(n.rstrip("/")) for n in hrefs
                       if n.endswith("/") and _DOY_DIR_RE.fullmatch(n.rstrip("/")))
        plans[year] = (folder, dirs3)
        if not dirs3:
            try:
                file_rows[year] = list_files(v, year=year, tiles=want,
                                             session=session, fetch=_memo,
                                             _folder=folder)
            except requests.RequestException as exc:
                errors.append(f"{year}: {exc}")
    per_year_doy = {}
    for year, (_, dirs3) in plans.items():
        if dirs3:
            per_year_doy[year] = set(dirs3)
    for year, rows in file_rows.items():
        pts = {r["doy"] for r in rows if r["doy"]}
        if pts:
            per_year_doy.setdefault(year, set()).update(pts)
    diffs = sorted({b - a for lst in per_year_doy.values()
                    for a, b in zip(sorted(lst), sorted(lst)[1:]) if b > a})
    stride = diffs[0] if diffs else None   # measured cadence, not the registry's

    # pass 2 — span-filter and assemble rows (memo serves every listing)
    out = []

    def _emit(r, date_s):
        out.append({
            "url": r["url"],
            "filename": r["filename"],
            "date": date_s,
            "tile": r["tile"],
            "size_mb": 0.0,
            "size_bytes": 0,
            "product": v["variant_id"],
        })

    for year in sorted(plans):
        if cancelled and cancelled():
            raise GlassCancelled("GLASS search cancelled")
        _, dirs3 = plans[year]
        if dirs3:
            for doy in sorted(dirs3):
                begin = _doy_date(year, doy)
                if stride is not None and not (
                        begin <= d1 and
                        begin + timedelta(days=stride - 1) >= d0):
                    continue
                try:
                    files = list_files(v, year=year, doy=doy, tiles=want,
                                       session=session, fetch=_memo)
                except FileNotFoundError:
                    continue
                except requests.RequestException as exc:
                    errors.append(f"{year}/{doy:03d}: {exc}")
                    continue
                for r in files:
                    _emit(r, begin.isoformat())
                    if len(out) >= max_results:
                        return out
        else:
            rows = file_rows.get(year, [])
            dated = any(r["doy"] or r["month"] for r in rows)
            if rows and not dated and len(rows) == 1:
                _emit(rows[0], str(year))  # annual single file keeps the year
            else:
                for r in rows:
                    if r["doy"]:
                        begin = _doy_date(year, r["doy"])
                        if stride is None or (
                                begin <= d1 and
                                begin + timedelta(days=stride - 1) >= d0):
                            _emit(r, begin.isoformat())
                    elif r["month"]:
                        ms = date(year, r["month"], 1)
                        me = ((date(year + 1, 1, 1) if r["month"] == 12
                               else date(year, r["month"] + 1, 1))
                              - timedelta(days=1))
                        if ms <= d1 and me >= d0:
                            _emit(r, f"{year}-{r['month']:02d}")
                    # undated files next to dated ones: unparseable, dropped
            if len(out) >= max_results:
                return out
    if not out and missing and missing == len(years):
        raise GlassError(
            f"no archive folder found for {v['variant_id']} (all {missing} "
            "year folders returned 404 — the archive layout may differ from "
            "the registry)")
    if not out and errors and not missing:
        raise RuntimeError("GLASS archive unreachable: " + errors[0])
    if not out:
        raise GlassError(
            f"no composite files could be parsed from the year folders of "
            f"{v['variant_id']} under {root} — browse the archive directly "
            "or use the glass.sqdaitools R package")
    return out


def _doy_date(year: int, doy: int) -> date:
    return date(year, 1, 1) + timedelta(days=doy - 1)


# ---------------------------------------------------------------- session

def _maybe_cancel():
    """Hit the caller's cooperative-cancel flag while stuck in the
    politeness sleeps (backoff 8/24/72 s + cooldown) — without this a
    cancelled search would still wait out the full backoff ladder."""
    chk = _CANCELLED[0]
    if chk is not None and chk():
        raise GlassCancelled("GLASS search cancelled during listing wait")


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
            _maybe_cancel()
            time.sleep(wait)
        gap = LISTING_MIN_INTERVAL - (time.monotonic() - _LAST_LISTING[0])
        if gap > 0:
            _maybe_cancel()
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
