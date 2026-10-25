# -*- coding: utf-8 -*-
"""Point time series for MODIS/VIIRS products via LAADS OPeNDAP (pure Python).

LAADS — the same servers d3ltool downloads granules from — runs a Hyrax
OPeNDAP service: one authenticated GET returns a single pixel of a remote
HDF file, e.g.

    FILE.hdf.ascii?_250m_16_days_NDVI[2400][2400]
    -> "_250m_16_days_NDVI[0], 3470"   (NDVI = 3470 * 0.0001)

so a whole-year series costs a handful of ~100-byte requests and no
third-party service. Pure Python (no Qt); the GUI worker thread drives it
exactly like d3ltool.agent. LAADS is reachable directly from mainland
networks (it never needed a proxy), and the configured app proxy is still
honoured for users behind one.
"""

import math
import re
import struct
import time

import requests

from . import i18n


class TimeSeriesError(RuntimeError):
    pass


class StopRequested(TimeSeriesError):
    """The user pressed stop; abort the sampling loop quietly."""


def proxies():
    """Proxy from the app settings ("" = none); None keeps requests' own
    env/system proxy detection intact."""
    try:
        from . import config

        proxy = (config.load_config() or {}).get("proxy_url") or ""
        if proxy:
            return {"http": proxy, "https": proxy}
    except Exception:
        pass
    return None


# ============================== LAADS OPeNDAP =================================

OPENDAP_BASE = "https://ladsweb.modaps.eosdis.nasa.gov"
ARCHIVE_MARK = "/archive/"
OPENDAP_MARK = "/opendap/RemoteResources/laads/"
MERRA_GATEWAY = "https://opendap.earthdata.nasa.gov"
_COORD_LAYERS = {"Latitude", "Longitude", "lat", "lon", "time"}
_NUM_TYPES = {"Int8", "UInt8", "Int16", "UInt16", "Int32", "UInt32",
              "Int64", "UInt64", "Float32", "Float64", "Array"}
# PRODUCT.AYYYYDDD.hHHvVV.VERSION.<proc>.hdf — everything needed to rebuild
# the deterministic LAADS archive layout allData/<coll>/<P>/<Y>/<DDD>/file
_LAADS_FNAME_RE = re.compile(
    r"^((?:MOD|MYD|MCD|VNP|VJ1|VJ2)\w+)\.A(\d{4})(\d{3})\.h\d{2}v\d{2}\."
    r"(\d+)\..+\.hdf$", re.IGNORECASE)
QC_TOKENS = ("QC", "Quality", "quality", "uncert", "Confidence",
             "NumSamples", "Day_of_year")
# when no specific layer is requested, prefer these science layers over an
# alphabetical accident like CLDPRS
PREFERRED_LAYERS = ("T2M", "NDVI", "EVI", "LST_Day_1km", "Lai_500m",
                    "GPP", "Npp_1km", "Albedo", "Snow_Cover_Daily_Percent",
                    "FireMask", "Radiance_DNB")


def pick_layer(layers, hint=""):
    """Choose a sensible default layer: the hint, a preferred science
    layer, else the first non-QC one."""
    if hint:
        for entry in layers:
            if entry.get("layer") == hint:
                return hint
    names = [entry.get("layer", "") for entry in layers]
    for want in PREFERRED_LAYERS:
        if want in names:
            return want
    for name in names:
        if name and not any(tok in name for tok in QC_TOKENS):
            return name
    return names[0] if names else ""


def laads_opendap_url(archive_url: str) -> str:
    if ARCHIVE_MARK not in archive_url:
        raise TimeSeriesError(f"not a LAADS archive URL: {archive_url}")
    return archive_url.replace(ARCHIVE_MARK, OPENDAP_MARK, 1)


def point_to_pixel(lat, lon, h, v, n_pixels):
    """(row, col) of the point inside the granule grid.

    C6 MODIS/VIIRS granules are squares of the true sinusoidal grid
    (validated pixel-exact against the Latitude/Longitude arrays of real
    files; see tests/test_timeseries.py)."""
    from . import tiles

    phi = math.radians(float(lat))
    x = tiles.R_SIN * math.radians(float(lon)) * math.cos(phi)
    y = tiles.R_SIN * phi
    res = tiles.TILE_SIZE / float(n_pixels)
    col = int((x - (h - 18) * tiles.TILE_SIZE) // res)
    row = int(((9 - v) * tiles.TILE_SIZE - y) // res)
    if not (0 <= row < n_pixels and 0 <= col < n_pixels):
        raise TimeSeriesError(
            "point falls outside the sinusoidal tile grid")
    return row, col


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def decode_dap4_floats(body: bytes, count: int, valid=None):
    """Decode the single-variable data blob of a DAP4 .dap response.

    The Hyrax gateway answers with the DMR XML, then one chunk:
    4-byte chunk header + count×float32 (little endian) + 8-byte trailing
    checksum. The data therefore sits right after the 4-byte header; a
    short plausibility scan over nearby offsets only serves as a fallback
    when the structural read looks degenerate (e.g. all zeros)."""
    marker = body.rindex(b"</Dataset>") + len(b"</Dataset>")
    blob = body[marker:].lstrip(b"\r\n \t")
    need = 4 * count

    def plausible(values):
        return all(v == v for v in values) and any(v != 0.0 for v in values)

    if len(blob) >= 4 + need:
        values = struct.unpack(f"<{count}f", blob[4:4 + need])
        if plausible(values):
            return list(values)

    # fallback: scan a few offsets for the most plausible alignment
    best = None
    for off in range(0, min(32, max(1, len(blob) - need))):
        chunk = blob[off:off + need]
        if len(chunk) < need:
            break
        values = struct.unpack(f"<{count}f", chunk)
        if any(v != v for v in values):          # NaN
            continue
        if valid is not None:
            inside = [valid[0] <= v <= valid[1] for v in values]
        else:
            inside = [1e-9 < abs(v) < 1e12 for v in values]
        score = sum(inside) + sum(1 for v, ok in zip(values, inside)
                                  if ok and v != 0.0)
        if best is None or score > best[0]:
            best = (score, list(values))
    if best is None or best[0] == 0:
        raise TimeSeriesError("could not decode the DAP4 data response")
    return best[1]


def _grid_index(value, lo, step, n):
    return min(n - 1, max(0, int(round((float(value) - lo) / step))))


def parse_dmr(xml_text: str):
    """Hyrax DAP4 DMR -> (dims, variables).

    dims: {name: size}. variables: {name: {long_name, units, fill, valid,
    scale, offset, dims, shape}} for every 2-D grid variable."""
    import xml.etree.ElementTree as ET

    def tag(el):
        return el.tag.rsplit("}", 1)[-1]

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise TimeSeriesError(f"bad DMR XML: {exc}") from exc

    dims = {}
    for node in root:
        if tag(node) == "Dimension":
            try:
                dims[node.get("name", "")] = int(node.get("size", 0))
            except ValueError:
                pass

    variables = {}
    for node in root:
        if tag(node) not in _NUM_TYPES:
            continue
        name = node.get("name", "")
        dim_names = [c.get("name", "").lstrip("/")
                     for c in node if tag(c) == "Dim"]
        attrs = {}
        for c in node:
            if tag(c) == "Attribute":
                attrs[c.get("name", "")] = [v.text for v in c
                                            if tag(v) == "Value"]
        if not name or not dim_names:
            continue
        valid = [_to_float(x) for x in attrs.get("valid_range", [])]
        variables[name] = {
            "dims": dim_names,
            "shape": [dims.get(d, 0) for d in dim_names],
            "long_name": (attrs.get("long_name") or [""])[0] or "",
            "units": (attrs.get("units") or [""])[0] or "",
            "fill": _to_float((attrs.get("_FillValue") or [None])[0]),
            "valid": valid if len(valid) == 2 and None not in valid else None,
            "scale": _to_float((attrs.get("scale_factor") or [None])[0]),
            "offset": _to_float((attrs.get("add_offset") or [None])[0]),
        }
    return dims, variables


def parse_ascii_value(text: str, layer: str):
    """'_250m_16_days_NDVI[0], 3470' -> 3470.0; None when absent/bad/NaN."""
    prefix = layer + "["
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(prefix) and "," in line:
            try:
                value = float(line.split(",", 1)[1].strip())
            except ValueError:
                return None
            return None if value != value else value   # NaN -> nodata
    return None


def is_fill(raw, fill):
    """Fill match with a relative tolerance. The DAP4 wire format carries
    float32 while the DMR _FillValue is parsed as float64 — MERRA-2's
    1e15-scale fill loses ~9e3 in the round trip, so exact equality misses
    every filled hour (CLDPRS is filled whenever the sky is clear)."""
    if fill is None or raw != raw:
        return False
    if raw == fill:
        return True
    return fill != 0 and abs(raw - fill) <= abs(fill) * 1e-6


class LaadsOpendapSeries:
    """Point time series sampled straight from the LAADS OPeNDAP service."""

    def __init__(self, session=None, searcher=None):
        self._session = session      # None -> authenticated lazily (auth)
        self._searcher = searcher    # None -> search.run_search default
        self._variables = None       # DMR cache of the probe granule

    def _get_text(self, url):
        if self._session is None:
            from . import auth

            self._session = auth.new_download_session()
        try:
            resp = self._session.get(url, timeout=(30, 180))
        except requests.RequestException as exc:
            if "SSL" in str(exc):
                raise TimeSeriesError(i18n.tr("ts_err_tls")) from exc
            raise TimeSeriesError(
                f"network error reaching LAADS OPeNDAP: {exc}") from exc
        if resp.status_code != 200:
            raise TimeSeriesError(
                f"LAADS OPeNDAP HTTP {resp.status_code}: "
                f"{(resp.text or '')[:200]}")
        return resp.text

    def collect(self, product, start, end, tile):
        """(urls, saw_granules) for one tile, urls sorted by date.

        CMR serves Earthdata-Cloud URLs these days, but the LAADS archive
        layout is deterministic, so the OPeNDAP URL is rebuilt from the
        granule filename: allData/<coll>/<P>/<Y>/<DDD>/<file>.hdf (classic
        /archive/ links are still rewritten when present)."""
        from . import search as search_mod

        params = search_mod.SearchParams(
            short_name=product, start=start, end=end,
            tiles=[tile], max_results=400)
        granules = search_mod.run_search(params, searcher=self._searcher)
        out, seen = [], set()
        for g in granules:
            date = search_mod.granule_date(g)
            url = None
            for link in search_mod.granule_links(g):
                base = link.split("?")[0]
                fname = base.rsplit("/", 1)[-1]
                if ARCHIVE_MARK in base and fname.lower().endswith(".hdf"):
                    url = laads_opendap_url(base)   # classic direct link
                    break
                m = _LAADS_FNAME_RE.match(fname)
                if m:
                    prod, yyyy, doy, version = m.groups()
                    url = (f"{OPENDAP_BASE}{OPENDAP_MARK}allData/"
                           f"{int(version)}/{prod}/{yyyy}/{doy}/{fname}")
                    break
            if not url:
                continue                       # browse/metadata-only entry
            key = (date, url.rsplit("/", 1)[-1])
            if key not in seen:
                seen.add(key)
                out.append((date, url))
        out.sort(key=lambda item: (item[0], item[1]))
        return out, bool(granules)

    def granule_urls(self, product, start, end, tile):
        return self.collect(product, start, end, tile)[0]

    def layers(self, granule_url):
        """Grid variables of the probe granule as [{layer, description}]."""
        _, variables = parse_dmr(self._get_text(granule_url + ".dmr.xml"))
        self._variables = variables
        return [{"layer": name, "description": meta["long_name"]}
                for name, meta in variables.items()
                if name not in _COORD_LAYERS]

    def series(self, lat, lon, product, start, end, layer="",
               granules=None, should_stop=None, progress=None,
               on_layers=None):
        """-> (source_label, layer, [(iso_date, value), ...])."""
        from . import tiles as tiles_mod

        h, v = tiles_mod.lonlat_to_tile(lon, lat)
        if granules is None:
            granules = self.granule_urls(product, start, end,
                                         tiles_mod.tile_name(h, v))
        if not granules:
            raise TimeSeriesError(
                f"no granules found for {product} at tile "
                f"{tiles_mod.tile_name(h, v)} in {start}..{end}")
        if self._variables is None or layer not in (self._variables or {}):
            found = self.layers(granules[0][1])
            if on_layers is not None:
                on_layers(found)
            if not layer:
                layer = pick_layer(found)
        meta = (self._variables or {}).get(layer)
        if not meta:
            raise TimeSeriesError(
                f"layer {layer!r} not found in the granule")
        n_pixels = meta["shape"][-1]
        if not n_pixels:
            raise TimeSeriesError(f"layer {layer!r} has no grid size in DMR")
        row, col = point_to_pixel(lat, lon, h, v, n_pixels)

        points = []
        for i, (date, url) in enumerate(granules):
            if should_stop is not None and should_stop():
                raise StopRequested("stopped by user")
            if progress is not None:
                progress(i + 1, len(granules), date)
            text = self._get_text(f"{url}.ascii?{layer}[{row}][{col}]")
            raw = parse_ascii_value(text, layer)
            if raw is None:
                continue
            if is_fill(raw, meta["fill"]):
                continue                      # cloud / nodata pixel
            if meta["valid"] is not None \
                    and not meta["valid"][0] <= raw <= meta["valid"][1]:
                continue
            value = raw * (meta["scale"] if meta["scale"] is not None else 1.0) \
                + (meta["offset"] if meta["offset"] is not None else 0.0)
            if date:
                points.append((date, round(value, 6)))
        return f"{product} (LAADS OPeNDAP)", layer, points


class MerraOpendapSeries:
    """Hourly MERRA-2 point series via NASA's cloud OPeNDAP gateway
    (opendap.earthdata.nasa.gov, DAP4 over the GES DISC netcdf-4 files).

    One authenticated GET per day returns that day's 24 hourly values for
    one pixel; values are decoded straight out of the DAP4 data blob (see
    decode_dap4_floats) so no netCDF4 dependency is needed."""

    def __init__(self, session=None, searcher=None):
        self._session = session
        self._searcher = searcher
        self._variables = None
        self._n_hours = 24

    def _get(self, url):
        if self._session is None:
            from . import auth

            self._session = auth.new_download_session()
        try:
            resp = self._session.get(url, timeout=(30, 180))
        except requests.RequestException as exc:
            raise TimeSeriesError(
                f"network error reaching the OPeNDAP gateway: {exc}") from exc
        if resp.status_code != 200:
            raise TimeSeriesError(
                f"OPeNDAP gateway HTTP {resp.status_code}: "
                f"{(resp.text or '')[:200]}")
        return resp.content

    def collect(self, product, start, end):
        """(urls, saw_granules): per-day OPeNDAP URLs from CMR search."""
        from . import search as search_mod

        params = search_mod.SearchParams(
            short_name=product, start=start, end=end, max_results=800)
        granules = search_mod.run_search(params, searcher=self._searcher)
        out, seen = [], set()
        for g in granules:
            date = search_mod.granule_date(g)
            url = None
            try:
                related = g["umm"].get("RelatedUrls", [])
            except AttributeError:
                related = []
            for r in related:
                link = r.get("URL", "")
                if r.get("Type") == "USE SERVICE API" \
                        and "opendap.earthdata.nasa.gov" in link:
                    url = link.split("?")[0]
                    break
            if not url:
                continue
            if url not in seen:
                seen.add(url)
                out.append((date, url))
        out.sort(key=lambda item: (item[0], item[1]))
        return out, bool(granules)

    def layers(self, granule_url):
        """(time,lat,lon) grid variables of the probe granule."""
        _, variables = parse_dmr(
            self._get(granule_url + ".dmr.xml").decode("utf-8", "replace"))
        self._variables = variables
        grid = [meta for name, meta in variables.items()
                if name not in _COORD_LAYERS and meta["dims"][:1] == ["time"]]
        return [{"layer": name, "description": meta["long_name"]}
                for name, meta in
                sorted((n, m) for n, m in variables.items()
                       if n not in _COORD_LAYERS and m["dims"][:1] == ["time"])]

    def series(self, lat, lon, product, start, end, layer="",
               granules=None, should_stop=None, progress=None,
               on_layers=None):
        """-> (source_label, layer, [(iso_datetime, value), ...])."""
        if granules is None:
            granules = self.granule_urls(product, start, end)
        if not granules:
            raise TimeSeriesError(
                f"no granules found for {product} in {start}..{end}")
        if self._variables is None or layer not in (self._variables or {}):
            found = self.layers(granules[0][1])
            if on_layers is not None:
                on_layers(found)
            if not layer:
                layer = pick_layer(found)
        meta = (self._variables or {}).get(layer)
        if not meta:
            raise TimeSeriesError(f"layer {layer!r} not found in the granule")
        if len(meta["shape"]) != 3:
            raise TimeSeriesError(
                f"layer {layer!r} is not a (time, lat, lon) grid")
        n_lat, n_lon = meta["shape"][1], meta["shape"][2]
        if not n_lat or not n_lon:
            raise TimeSeriesError(f"layer {layer!r} has no grid size in DMR")
        # MERRA-2 grids are fixed regular lat/lon: 0.5° x 0.625°
        d_lat = 180.0 / (n_lat - 1)
        d_lon = 360.0 / n_lon
        row = _grid_index(lat, -90.0, d_lat, n_lat)
        col = _grid_index(lon, -180.0, d_lon, n_lon)
        n_hours = meta["shape"][0] or 24
        valid = meta["valid"]

        points = []
        for i, (date, url) in enumerate(granules):
            if should_stop is not None and should_stop():
                raise StopRequested("stopped by user")
            if progress is not None:
                progress(i + 1, len(granules), date)
            body = self._get(f"{url}.dap?dap4.ce=/{layer}"
                             f"[0:{n_hours - 1}][{row}][{col}]")
            values = decode_dap4_floats(body, n_hours, valid)
            for hour, raw in enumerate(values):
                if raw is None:
                    continue
                if is_fill(raw, meta["fill"]):
                    continue
                value = raw * (meta["scale"] if meta["scale"] is not None
                               else 1.0) \
                    + (meta["offset"] if meta["offset"] is not None else 0.0)
                stamp = f"{date}T{(hour + 1) % 24:02d}:30"
                points.append((stamp, round(value, 4)))
        return f"{product} (GES DISC OPeNDAP)", layer, points

    def granule_urls(self, product, start, end):
        return self.collect(product, start, end)[0]


def run_point_series(lat, lon, product, start, end, layer_hint="",
                     should_stop=None, adapter=None, session=None,
                     searcher=None):
    """Sample one pixel's series, dispatching on the product family:
    MODIS/VIIRS -> LAADS OPeNDAP direct sampling; MERRA-2 -> the NASA cloud
    OPeNDAP gateway. adapter.stage(key, **kw) / adapter.layers(list) report
    progress. Returns (source_label, layer, points)."""
    if adapter is None:
        adapter = _NullAdapter()

    name = str(product).strip().upper()
    if name.startswith("M2") or name.startswith("MERRA2"):
        merra = MerraOpendapSeries(session=session, searcher=searcher)
        adapter.stage("ts_stage_search")
        urls, saw_granules = merra.collect(name, start, end)
        if not urls:
            if saw_granules:
                raise TimeSeriesError(i18n.tr(
                    "ts_no_granules_url", product=name))
            raise TimeSeriesError(i18n.tr(
                "ts_no_granules", product=name, tile="—",
                start=start, end=end))

        def _progress(i, n, date):
            adapter.stage("ts_odap_sample", i=i, n=n, date=date)

        return merra.series(lat, lon, name, start, end, layer_hint,
                            granules=urls, should_stop=should_stop,
                            progress=_progress, on_layers=adapter.layers)

    opendap = LaadsOpendapSeries(session=session, searcher=searcher)
    from . import tiles as tiles_mod

    h, v = tiles_mod.lonlat_to_tile(lon, lat)
    tile = tiles_mod.tile_name(h, v)
    adapter.stage("ts_stage_search")
    urls, saw_granules = opendap.collect(product, start, end, tile)
    if not urls:
        if saw_granules:
            # CMR knows the product but its files are not on LAADS
            raise TimeSeriesError(i18n.tr(
                "ts_unsupported", product=name))
        raise TimeSeriesError(i18n.tr(
            "ts_no_granules", product=name, tile=tile,
            start=start, end=end))

    def _progress(i, n, date):
        adapter.stage("ts_odap_sample", i=i, n=n, date=date)

    return opendap.series(lat, lon, product, start, end, layer_hint,
                          granules=urls, should_stop=should_stop,
                          progress=_progress, on_layers=adapter.layers)


class _NullAdapter:
    def stage(self, key, **kw):
        pass

    def layers(self, layers):
        pass


def now_stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")
