# -*- coding: utf-8 -*-
"""Time-series data layer tests (LAADS OPeNDAP, fully mocked HTTP)."""

import json
import struct

import pytest

from d3ltool import timeseries as tsl


class FakeSession:
    """Route table: [(method, url_contains, responder)] checked in order."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []          # (method, url, body_or_None)
        self.last_kwargs = None

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs.get("data")))
        self.last_kwargs = kwargs
        for m, part, responder in self.routes:
            if m == method and part in url:
                if isinstance(responder, list):
                    if not responder:
                        raise AssertionError(f"exhausted route {part}")
                    return responder.pop(0)
                return responder(kwargs)
        raise AssertionError(f"unrouted request: {method} {url}")

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)


# ===================== LAADS OPeNDAP (AppEEARS-free) path =====================

DMR_FIXTURE = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#" name="x.hdf">
  <Dimension name="YDim" size="4800"/>
  <Dimension name="XDim" size="4800"/>
  <Int16 name="_250m_16_days_NDVI">
    <Dim name="/YDim"/><Dim name="/XDim"/>
    <Attribute name="long_name" type="String"><Value>250m 16 days NDVI</Value></Attribute>
    <Attribute name="valid_range" type="Int16"><Value>-2000</Value><Value>10000</Value></Attribute>
    <Attribute name="_FillValue" type="Int16"><Value>-3000</Value></Attribute>
    <Attribute name="scale_factor" type="Float64"><Value>0.00010000000000000000</Value></Attribute>
    <Attribute name="add_offset" type="Float64"><Value>0.0000000000000000</Value></Attribute>
  </Int16>
  <Int16 name="_250m_16_days_NDVI_QC">
    <Dim name="/YDim"/><Dim name="/XDim"/>
    <Attribute name="long_name" type="String"><Value>quality</Value></Attribute>
  </Int16>
  <Float32 name="Latitude"><Dim name="/YDim"/><Dim name="/XDim"/></Float32>
</Dataset>"""


class TextResp:
    """Plain-text HTTP response (DMR XML / OPeNDAP ascii / DAP4 blob)."""

    def __init__(self, body, status=200):
        self.text = body
        self.status_code = status
        self.headers = {"Content-Type": "text/plain"}

    @property
    def content(self):
        return self.text.encode("latin-1")


def test_point_to_pixel_calibration():
    """Values below are the Latitude/Longitude arrays OF THE REAL FILE
    MOD13Q1.A2009017.h26v05 (sampled live); the formulas map them back to
    their true indices pixel-exactly."""
    # top-left pixel center -> (0, 0)
    assert tsl.point_to_pixel(39.9989583297443, 104.432349805394,
                              26, 5, 4800) == (0, 0)
    # centre pixel -> (2400, 2400)
    assert tsl.point_to_pixel(34.9989583301918, 103.765790736523,
                              26, 5, 4800) == (2400, 2400)
    # bottom-left -> (4799, 0); top-right -> (0, 4799)
    assert tsl.point_to_pixel(30.0010416639725, 92.3782155380262,
                              26, 5, 4800) == (4799, 0)
    assert tsl.point_to_pixel(39.9989583297443, 117.483504001727,
                              26, 5, 4800) == (0, 4799)


def test_point_to_pixel_outside_tile():
    with pytest.raises(tsl.TimeSeriesError, match="outside"):
        tsl.point_to_pixel(50.0, 104.4, 26, 5, 4800)


def test_laads_opendap_url():
    url = tsl.laads_opendap_url(
        "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/"
        "MOD13Q1/2009/017/x.hdf")
    assert "/opendap/RemoteResources/laads/allData/61/" in url
    with pytest.raises(tsl.TimeSeriesError):
        tsl.laads_opendap_url("https://example.com/data/x.hdf")


def test_parse_dmr():
    dims, variables = tsl.parse_dmr(DMR_FIXTURE)
    assert dims == {"YDim": 4800, "XDim": 4800}
    ndvi = variables["_250m_16_days_NDVI"]
    assert ndvi["shape"] == [4800, 4800]
    assert ndvi["long_name"] == "250m 16 days NDVI"
    assert ndvi["fill"] == -3000.0
    assert ndvi["valid"] == [-2000.0, 10000.0]
    assert ndvi["scale"] == 0.0001
    assert ndvi["offset"] == 0.0
    # QC variable parsed too, coordinates kept out of the layer list later
    assert "_250m_16_days_NDVI_QC" in variables


def test_parse_ascii_value():
    text = ("Dataset: x.hdf\n"
            "_250m_16_days_NDVI[0], 3470\n")
    assert tsl.parse_ascii_value(text, "_250m_16_days_NDVI") == 3470.0
    assert tsl.parse_ascii_value("Dataset: x.hdf\n", "_x") is None
    assert tsl.parse_ascii_value("_x[0], NaN\n", "_x") is None


def test_pick_layer_fuzzy_hints():
    """Users and the agent say 'NDVI'; files call it _250m_16_days_NDVI."""
    layers = [{"layer": "_250m_16_days_NDVI", "description": "NDVI"},
              {"layer": "_250m_16_days_NDVI_QC", "description": "quality"}]
    assert tsl.pick_layer(layers, "NDVI") == "_250m_16_days_NDVI"
    assert tsl.pick_layer(layers, "ndvi") == "_250m_16_days_NDVI"
    # case / underscores / spaces are all interchangeable
    assert tsl.pick_layer(layers, "250m 16 days NDVI") == "_250m_16_days_NDVI"
    # an exact name — including QC — is honoured as-is
    assert tsl.pick_layer(layers, "_250m_16_days_NDVI_QC") \
        == "_250m_16_days_NDVI_QC"
    # an empty hint keeps the sensible default (QC skipped)
    assert tsl.pick_layer(layers) == "_250m_16_days_NDVI"
    # a hint nothing resembles raises instead of silently picking another
    # science layer, and the message lists the available names
    with pytest.raises(tsl.TimeSeriesError, match="EVI"):
        tsl.pick_layer(layers, "EVI")
    # a one-letter guess must not substring-hit everything: it raises with
    # the available list so the caller can retry with an exact name
    with pytest.raises(tsl.TimeSeriesError, match="available"):
        tsl.pick_layer(layers, "T")


def _fake_granule(date, tile, suffix="061", cloud=True):
    """CMR-style granule: Earthdata-Cloud link by default, classic LAADS
    archive link when cloud=False. Filenames use the real AYYYYDDD day
    numbering (A2009001, not the full date)."""
    import datetime as _dt

    day = _dt.date.fromisoformat(date)
    aday = f"A{day.year}{day.timetuple().tm_yday:03d}"
    name = f"MOD13Q1.{aday}.{tile}.{suffix}.2021.hdf"
    if cloud:
        url = ("https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/"
               f"MOD13Q1.{suffix}/{name[:-4]}/{name}")
    else:
        url = ("https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/"
               f"MOD13Q1/{day.year}/{day.timetuple().tm_yday:03d}/{name}")
    return {"umm": {
        "TemporalExtent": {"RangeDateTime":
                           {"BeginningDateTime": f"{date}T00:00:00Z"}},
        "RelatedUrls": [{
            "URL": "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-public/"
                   f"{name[:-4]}/BROWSE.{name[:-4]}.1.jpg",
            "Type": "GET DATA"},
            {"URL": url, "Type": "GET DATA"}],
    }}


def test_opendap_granule_urls():
    seen_queries = {}

    def searcher(**query):
        seen_queries.update(query)
        return [_fake_granule("2009-01-17", "h27v05"),
                _fake_granule("2009-01-01", "h27v05"),
                _fake_granule("2009-01-01", "h27v05"),   # duplicate
                _fake_granule("2009-02-01", "h27v05", cloud=False)]

    s = tsl.LaadsOpendapSeries(searcher=searcher)
    out = s.granule_urls("MOD13Q1", "2009-01-01", "2009-12-31", "h27v05")
    assert [d for d, _u in out] == ["2009-01-01", "2009-01-17", "2009-02-01"]
    # cloud links rebuilt from the filename into the archive layout ...
    assert out[0][1].endswith(
        "/opendap/RemoteResources/laads/allData/61/MOD13Q1/2009/001/"
        "MOD13Q1.A2009001.h27v05.061.2021.hdf")
    # ... classic /archive/ links rewritten in place
    assert out[2][1].startswith(
        "https://ladsweb.modaps.eosdis.nasa.gov/opendap/RemoteResources/"
        "laads/allData/61/")
    # the tile went into the CMR name pattern
    assert seen_queries["readable_granule_name"] == ["*.h27v05.*"]


def _opendap_routes(ascii_responses):
    return [
        ("GET", ".dmr.xml", lambda kw: TextResp(DMR_FIXTURE)),
        ("GET", ".ascii?", [TextResp(t) for t in ascii_responses]),
    ]


def test_opendap_series_full():
    granules = [("2009-01-01", "https://ladsweb.example/opendap/a.hdf"),
                ("2009-01-17", "https://ladsweb.example/opendap/b.hdf")]
    session = FakeSession(_opendap_routes([
        "_250m_16_days_NDVI[0], 3470",       # valid
        "_250m_16_days_NDVI[0], -3000",      # fill -> dropped
    ]))
    s = tsl.LaadsOpendapSeries(session=session)
    progress_log = []
    layers_seen = []

    source, layer, points, layer_meta = s.series(
        36.833, 116.567, "MOD13Q1", "2009-01-01", "2009-12-31",
        granules=granules,
        progress=lambda i, n, d: progress_log.append((i, n, d)),
        on_layers=layers_seen.append)
    assert source == "MOD13Q1 (LAADS OPeNDAP)"
    assert layer == "_250m_16_days_NDVI"     # QC skipped as default
    assert points == [("2009-01-01", 0.347)]
    assert layers_seen and layers_seen[0][0]["layer"] == "_250m_16_days_NDVI"
    assert progress_log == [(1, 2, "2009-01-01"), (2, 2, "2009-01-17")]
    # the exact pixel indices rode along in the request URL
    row, col = tsl.point_to_pixel(36.833, 116.567, 27, 5, 4800)
    ascii_calls = [u for m, u, _b in session.calls if ".ascii?" in u]
    assert ascii_calls[0].endswith(
        f".ascii?_250m_16_days_NDVI[{row}][{col}]")


def test_opendap_series_fuzzy_layer_hint():
    """'NDVI' — what the user or the agent actually says — samples the
    file's _250m_16_days_NDVI instead of dying with 'layer not found'."""
    granules = [("2009-01-01", "https://ladsweb.example/opendap/a.hdf")]
    session = FakeSession(_opendap_routes(["_250m_16_days_NDVI[0], 3470"]))
    s = tsl.LaadsOpendapSeries(session=session)
    _source, layer, points, layer_meta = s.series(
        36.833, 116.567, "MOD13Q1", "2009-01-01", "2009-12-31",
        layer="NDVI", granules=granules)
    assert layer == "_250m_16_days_NDVI"
    assert points == [("2009-01-01", 0.347)]


def test_opendap_series_stop():
    granules = [("2009-01-01", "https://ladsweb.example/opendap/a.hdf"),
                ("2009-01-17", "https://ladsweb.example/opendap/b.hdf")]
    session = FakeSession(_opendap_routes(["_250m_16_days_NDVI[0], 100"]))
    s = tsl.LaadsOpendapSeries(session=session)
    with pytest.raises(tsl.StopRequested):
        s.series(36.833, 116.567, "MOD13Q1", "2009-01-01", "2009-12-31",
                 granules=granules, should_stop=lambda: True)


def test_run_point_series_prefers_opendap():
    def searcher(**query):
        return [_fake_granule("2009-01-17", "h27v05")]

    session = FakeSession(_opendap_routes(["_250m_16_days_NDVI[0], 5000"]))
    stages = []

    class Adapter:
        def stage(self, key, **kw):
            stages.append(key)

        def layers(self, layers):
            pass

    source, layer, points, layer_meta = tsl.run_point_series(
        36.833, 116.567, "MOD13Q1", "2009-01-01", "2009-12-31",
        adapter=Adapter(), session=session, searcher=searcher)
    assert "LAADS OPeNDAP" in source
    assert points == [("2009-01-17", 0.5)]
    assert "ts_odap_sample" in stages
    assert "ts_stage_search" in stages


def test_run_point_series_rejects_non_laads_product():
    """AppEEARS was removed: non-LAADS products (e.g. MERRA-2) get a clear
    'not supported' error instead of a connection error."""

    def searcher(**query):        # MERRA-2 granules: GES DISC, not LAADS
        return [{"umm": {
            "TemporalExtent": {"RangeDateTime":
                               {"BeginningDateTime": "2020-01-01T00:00:00Z"}},
            "RelatedUrls": [{
                "URL": "https://goldsmr4.gesdisc.eosdis.nasa.gov/data/x.nc4",
                "Type": "GET DATA"}],
        }}]

    session = FakeSession([])     # no routes: nothing may be fetched
    with pytest.raises(tsl.TimeSeriesError, match=r"M2T1NXSLV"):
        tsl.run_point_series(36.833, 116.567, "M2T1NXSLV",
                             "2020-01-01", "2020-01-31",
                             session=session, searcher=searcher)


def test_run_point_series_no_granules(monkeypatch):
    monkeypatch.setattr(tsl, "cmr_product_exists", lambda name: True)

    def searcher(**query):
        return []

    session = FakeSession([])
    with pytest.raises(tsl.TimeSeriesError, match="h27v05"):
        tsl.run_point_series(36.833, 116.567, "MOD13Q1",
                             "2099-01-01", "2099-01-31",
                             session=session, searcher=searcher)


def test_run_point_series_unknown_product(monkeypatch):
    """An invented product name (models guess 'MCD13Q1'; CMR has no such
    short_name — the real VI family is MOD13/MYD13) is called out as such
    instead of blaming the date range."""
    monkeypatch.setattr(tsl, "cmr_product_exists", lambda name: False)

    def searcher(**query):
        return []

    session = FakeSession([])
    with pytest.raises(tsl.TimeSeriesError, match="MCD13Q1"):
        tsl.run_point_series(36.833, 116.567, "MCD13Q1",
                             "2010-01-01", "2010-12-31",
                             session=session, searcher=searcher)


# ===================== MERRA-2 via the cloud OPeNDAP gateway =====================

MERRA_DMR = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#" name="x.nc4">
  <Dimension name="time" size="24"/>
  <Dimension name="lat" size="361"/>
  <Dimension name="lon" size="576"/>
  <Float32 name="T2M">
    <Dim name="/time"/><Dim name="/lat"/><Dim name="/lon"/>
    <Attribute name="long_name" type="String"><Value>2-meter_air_temperature</Value></Attribute>
    <Attribute name="units" type="String"><Value>K</Value></Attribute>
    <Attribute name="_FillValue" type="Float32"><Value>9.99999987e+14</Value></Attribute>
    <Attribute name="scale_factor" type="Float64"><Value>1.</Value></Attribute>
  </Float32>
</Dataset>"""


def _dap_body(values):
    """A DAP4 data response: DMR tail + chunk header + LE float32 + checksum."""
    data = struct.pack(f"<{len(values)}f", *values)
    return (b"<?xml version=\"1.0\"?><Dataset>...attrs...</Dataset>"
            b"\n\r\n\x04\x00\x00d" + data + b"\x00" * 8)


def test_decode_dap4_floats_structural():
    body = _dap_body([270.5, 271.0, 269.5] + [265.0] * 21)
    out = tsl.decode_dap4_floats(body, 24)
    assert [round(v, 1) for v in out[:3]] == [270.5, 271.0, 269.5]


def test_decode_dap4_floats_fallback_and_fill():
    # degenerate zeros at the structural offset: the scan finds real data
    data = struct.pack("<24f", *([0.0] * 4 + [260.0] * 20))
    body = b"<Dataset>x</Dataset>\n\r\n\x04\x00\x00d" + data + b"\x00" * 8
    out = tsl.decode_dap4_floats(body, 24)
    assert 260.0 in [round(v, 1) for v in out]


def test_merra_grid_index():
    # 0.5-deg lat rows / 0.625-deg lon cols: Yucheng lands on (254, 475)
    n_lat, n_lon = 361, 576
    row = min(n_lat - 1, max(0, int(round((36.833 + 90.0) / (180.0 / (n_lat - 1))))))
    col = min(n_lon - 1, max(0, int(round((116.567 + 180.0) / (360.0 / n_lon)))))
    assert (row, col) == (254, 475)


def _fake_merra_granule(date):
    ur = f"M2T1NXSLV.5.12.4%3AMERRA2_400.tavg1_2d_slv_Nx.{date.replace('-', '')}.nc4"
    return {"umm": {
        "TemporalExtent": {"RangeDateTime":
                           {"BeginningDateTime": f"{date}T00:00:00Z"}},
        "RelatedUrls": [
            {"URL": "https://data.gesdisc.earthdata.nasa.gov/data/x.nc4",
             "Type": "GET DATA"},
            {"URL": f"https://opendap.earthdata.nasa.gov/collections/"
                    f"C1276812863-GES_DISC/granules/{ur}",
             "Type": "USE SERVICE API"}],
    }}


def test_merra_collect():
    def searcher(**query):
        return [_fake_merra_granule("2020-01-02"),
                _fake_merra_granule("2020-01-01")]

    s = tsl.MerraOpendapSeries(searcher=searcher)
    urls, saw = s.collect("M2T1NXSLV", "2020-01-01", "2020-01-02")
    assert saw and len(urls) == 2
    assert urls[0][0] == "2020-01-01"
    assert "opendap.earthdata.nasa.gov" in urls[0][1]


def test_run_point_series_merra(monkeypatch):
    def searcher(**query):
        return [_fake_merra_granule("2020-01-01")]

    session = FakeSession([
        ("GET", ".dmr.xml", lambda kw: TextResp(MERRA_DMR)),
        ("GET", ".dap", lambda kw: TextResp("")),
    ])
    # the .dap route must answer with BYTES: patch the session for it
    class BinarySession(FakeSession):
        def get(self, url, **kwargs):
            if ".dap" in url and not url.endswith(".dmr.xml"):
                self.calls.append(("GET", url, None))
                return TextResp(_dap_body([270.0] * 24).decode(
                    "latin-1"))
            return super().get(url, **kwargs)

    session = BinarySession([
        ("GET", ".dmr.xml", lambda kw: TextResp(MERRA_DMR)),
    ])
    source, layer, points, layer_meta = tsl.run_point_series(
        36.833, 116.567, "M2T1NXSLV", "2020-01-01", "2020-01-01",
        session=session, searcher=searcher)
    assert layer_meta["units"] == "K"
    assert layer_meta["long_name"] == "2-meter_air_temperature"
    assert source == "M2T1NXSLV (GES DISC OPeNDAP)"
    assert layer == "T2M"
    assert len(points) == 24
    stamps = [t for t, _v in points]
    assert stamps == sorted(stamps)          # native labels keep day order
    assert points[0][0] == "2020-01-01T00:30"
    assert points[0][1] == 270.0


def test_is_fill_float32_roundtrip():
    """The gateway sends float32; MERRA-2's 1e15 fill loses ~9e3 in the
    round trip, so exact equality misses every filled hour."""
    fill = 9.9999987e14
    wire = struct.unpack("<f", struct.pack("<f", fill))[0]
    assert wire != fill                       # exact == provably fails
    assert wire < fill                        # inside the (useless) valid range
    assert tsl.is_fill(wire, fill)
    assert tsl.is_fill(fill, fill)
    assert not tsl.is_fill(270.0, fill)
    assert not tsl.is_fill(98158.0, fill)
    assert not tsl.is_fill(100.0, None)


def test_merra_series_drops_float32_fill():
    """End to end: the float32-rounded fill hours are dropped, the real
    one kept (CLDPRS arrives filled for every clear-sky hour)."""
    fill = 9.9999987e14
    wire = struct.unpack("<f", struct.pack("<f", fill))[0]
    values = [wire, 270.0] + [wire] * 22

    class _BytesSession(FakeSession):
        def get(self, url, **kwargs):
            if ".dap" in url and not url.endswith(".dmr.xml"):
                self.calls.append(("GET", url, None))
                return TextResp(_dap_body(values).decode("latin-1"))
            return super().get(url, **kwargs)

    session = _BytesSession(
        [("GET", ".dmr.xml", lambda kw: TextResp(MERRA_DMR))])
    s = tsl.MerraOpendapSeries(session=session)
    _source, _layer, points, _meta = s.series(
        36.833, 116.567, "M2T1NXSLV", "2020-01-01", "2020-01-01",
        granules=[("2020-01-01", "https://opendap.example/g")])
    assert points == [("2020-01-01T01:30", 270.0)]
