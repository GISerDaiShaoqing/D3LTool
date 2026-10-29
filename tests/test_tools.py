# -*- coding: utf-8 -*-
"""Tool registry tests: schema generation + every tool's behaviour.

Network-free: search and downloads use the shared fakes/local range server.
"""

import json
import time

import pytest
import requests

import d3ltool.tools as tools
from d3ltool import auth


class FakeGranule:
    """Mimics the earthaccess DataGranule surface used by search helpers."""

    def __init__(self, name, url=None, size_mb=0.0, date="2020-03-01"):
        self._name = name
        self._size = size_mb
        umm = {"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": date}}}
        if url:
            umm["RelatedUrls"] = [{"URL": url, "Type": "GET DATA"}]
        self._umm = umm

    def __getitem__(self, key):
        if key == "meta":
            return {"native-id": self._name}
        if key == "umm":
            return self._umm
        raise KeyError(key)

    @property
    def size(self):
        return self._size


@pytest.fixture(autouse=True)
def isolated_tools(monkeypatch):
    """No real config, no real netrc, no real network for any tool test."""
    import d3ltool.config as config

    cfg = dict(config.DEFAULTS)
    monkeypatch.setattr(config, "load_config", lambda: cfg)
    monkeypatch.setattr(tools, "_SESSION_FACTORY", requests.Session)
    monkeypatch.setattr(tools, "_SEARCHER", None)
    monkeypatch.setattr(tools, "_PLOT_SINK", None)
    tools._reset_engine()
    yield
    tools._reset_engine()


def _signed_in(monkeypatch, user="tester"):
    monkeypatch.setattr(auth, "is_authenticated", lambda: True)
    monkeypatch.setattr(auth, "current_user", lambda: user)


def _signed_out(monkeypatch):
    monkeypatch.setattr(auth, "is_authenticated", lambda: False)
    monkeypatch.setattr(auth, "current_user", lambda: "")
    # start_download/check_auth fall back to try_restore_session() since the
    # MCP patch; stub it so offline machines never attempt a real URS login.
    monkeypatch.setattr(auth, "try_restore_session", lambda: False)


# ----------------------------------------------------------------- registry

def test_registry_contains_all_tools():
    expected = {
        "check_auth", "list_products", "point_to_tile", "tile_bounds",
        "search_granules", "point_timeseries", "plot_timeseries",
        "start_download", "download_status", "cancel_download",
        "retry_download",
    }
    assert set(tools.REGISTRY) == expected
    for spec in tools.all_specs():
        assert spec.description
        assert spec.description_zh
        assert spec.parameters["type"] == "object"


def test_schemas_match_signatures():
    sg = tools.get_spec("search_granules").parameters
    assert set(sg["required"]) == {"short_name", "start", "end"}
    assert sg["properties"]["tiles"]["type"] == "array"
    assert sg["properties"]["limit"]["default"] == 10
    assert sg["properties"]["version"]["type"] == "string"

    sd = tools.get_spec("start_download").parameters
    assert set(sd["required"]) == {"urls"}
    assert sd["properties"]["urls"]["type"] == "array"

    cb = tools.get_spec("tile_bounds").parameters
    assert set(cb["required"]) == {"h", "v"}
    assert cb["properties"]["h"]["type"] == "integer"

    pt = tools.get_spec("point_to_tile").parameters
    assert pt["properties"]["lon"]["type"] == "number"

    ts = tools.get_spec("point_timeseries").parameters
    assert set(ts["required"]) == {"lon", "lat", "product", "start", "end"}
    assert ts["properties"]["limit"]["default"] == 200
    assert ts["properties"]["layer"]["type"] == "string"


def test_openai_tool_specs_format():
    specs = tools.openai_tool_specs()
    names = [s["function"]["name"] for s in specs]
    assert "search_granules" in names
    for s in specs:
        assert s["type"] == "function"
        assert s["function"]["parameters"]["type"] == "object"


# ------------------------------------------------------------------- tools

def test_check_auth_signed_out(monkeypatch):
    _signed_out(monkeypatch)
    out = tools.check_auth()
    assert out["authenticated"] is False
    assert "sign in" in out["hint"]


def test_check_auth_signed_in(monkeypatch):
    _signed_in(monkeypatch, "alice")
    out = tools.check_auth()
    assert out == {"authenticated": True, "user": "alice", "hint": ""}


def test_list_products_all_and_filtered():
    out = tools.list_products()
    assert out["count"] == 27          # 8 Terra + 4 Aqua + 4 Combined + 4 VIIRS + 7 MERRA-2
    assert all(p["short_name"] and p["version"] for p in out["products"])

    viirs = tools.list_products(group="VIIRS")
    assert viirs["count"] == 4
    assert {p["short_name"] for p in viirs["products"]} >= {"VNP46A1", "VNP46A2"}

    assert tools.list_products(group="no-such-group")["count"] == 0


def test_point_to_tile_beijing():
    # Ground truth from C6.1 files (their own lat/lon arrays): Beijing is
    # in the sinusoidal square h26v05; the old 10-degree box rule said h29.
    out = tools.point_to_tile(116.4, 39.9)          # Beijing -> h26v05
    assert out["tile"] == "h26v05"
    assert out["bounds"]["north"] == 40.0           # v05 row: 30-40N


def test_tile_bounds_and_range_check():
    out = tools.tile_bounds(0, 0)
    assert out["bounds"] == {"west": -180.0, "south": 80.0,
                             "east": -170.0, "north": 90.0}
    with pytest.raises(ValueError):
        tools.tile_bounds(36, 0)
    with pytest.raises(ValueError):
        tools.tile_bounds(0, 18)


def test_search_granules_maps_results(monkeypatch):
    captured = {}

    def searcher(**kwargs):
        captured.update(kwargs)
        return [
            FakeGranule("LAADS:1",
                        url="https://data.example/VNP46A1.A2020060.h04v03.002.1.h5",
                        size_mb=51.4, date="2020-03-01"),
            FakeGranule("LAADS:2",
                        url="https://data.example/VNP46A1.A2020061.h04v03.002.2.h5",
                        size_mb=52.0, date="2020-03-02"),
        ]

    monkeypatch.setattr(tools, "_SEARCHER", searcher)
    out = tools.search_granules(
        short_name="vnp46a1", start="2020-03-01", end="2020-03-31",
        tiles=["H04V03"], limit=10)

    assert captured["short_name"] == "VNP46A1"
    assert captured["readable_granule_name"] == ["*.h04v03.*"]
    assert out["count"] == 2
    g = out["granules"][0]
    assert g["filename"].endswith("h04v03.002.1.h5")
    assert g["date"] == "2020-03-01"
    assert g["tile"] == "h04v03"
    assert g["size_mb"] == 51.4
    assert g["url"].startswith("https://")


def test_search_granules_bbox_validation(monkeypatch):
    monkeypatch.setattr(tools, "_SEARCHER", lambda **kw: [])
    with pytest.raises(ValueError):
        tools.search_granules(short_name="M2T1NXSLV", start="2019-08-01",
                              end="2019-08-31", bbox=[120, 20, 100, 40])
    with pytest.raises(ValueError):
        tools.search_granules(short_name="x", start="2020-01-01",
                              end="2020-01-31", tiles=["h99v99"])


# --------------------------------------------------------- point_timeseries

def test_point_timeseries_tool_laads(monkeypatch):
    """Full chain through the tool: CMR search -> LAADS OPeNDAP pixel."""
    from d3ltool import auth
    from test_timeseries import FakeSession, _fake_granule, _opendap_routes

    monkeypatch.setattr(tools, "_SEARCHER",
                        lambda **query: [_fake_granule("2009-01-17", "h27v05")])
    session = FakeSession(_opendap_routes(["_250m_16_days_NDVI[0], 3470"]))
    monkeypatch.setattr(auth, "new_download_session", lambda: session)

    out = tools.point_timeseries(lon=116.567, lat=36.833, product="MOD13Q1",
                                 start="2009-01-01", end="2009-12-31")
    assert out["source"] == "MOD13Q1 (LAADS OPeNDAP)"
    assert out["layer"] == "_250m_16_days_NDVI"
    assert out["stats"] == {"count": 1, "min": 0.347, "max": 0.347,
                            "mean": 0.347}
    assert out["truncated"] is False
    assert out["points"] == [["2009-01-17", 0.347]]
    assert out["series_id"]


def test_point_timeseries_progress_and_stop(monkeypatch):
    """The in-app agent path: stage progress flows to the GUI sink and the
    panel's stop checker aborts sampling between granules (a temperature
    turn used to grind silently for minutes on the slow GES DISC gateway
    with no way to cancel it)."""
    from d3ltool import auth
    from test_timeseries import FakeSession, _fake_granule, _opendap_routes

    monkeypatch.setattr(tools, "_SEARCHER",
                        lambda **query: [_fake_granule("2009-01-17", "h27v05")])
    monkeypatch.setattr(auth, "new_download_session", lambda: FakeSession(
        _opendap_routes(["_250m_16_days_NDVI[0], 3470"])))
    seen = []
    monkeypatch.setattr(tools, "_PROGRESS_SINK",
                        lambda key, **kw: seen.append((key, kw)))
    monkeypatch.setattr(tools, "_PLOT_SINK", object())   # in-app environment
    monkeypatch.setattr(tools, "_TS_STOP", lambda: False)
    out = tools.point_timeseries(lon=116.567, lat=36.833, product="MOD13Q1",
                                 start="2009-01-01", end="2009-12-31")
    assert out["series_id"]
    assert f"plot_timeseries(series_id='{out['series_id']}')" in out["hint"]
    assert [k for k, _kw in seen] == ["ts_stage_search", "ts_odap_sample"]
    assert seen[1][1] == {"i": 1, "n": 1, "date": "2009-01-17"}

    # the stop button aborts the loop; the tool reports it as a quiet error
    monkeypatch.setattr(tools, "_SEARCHER",
                        lambda **query: [_fake_granule("2009-01-17", "h27v05"),
                                         _fake_granule("2009-02-01", "h27v05")])
    monkeypatch.setattr(tools, "_TS_STOP", lambda: True)
    stopped = tools.point_timeseries(lon=116.567, lat=36.833,
                                     product="MOD13Q1",
                                     start="2009-01-01", end="2009-12-31")
    assert stopped["error"] == "timeseries_failed"
    assert "stop" in stopped["hint"].lower()


def test_plot_timeseries_tool(monkeypatch):
    """point_timeseries caches the full series under a series_id;
    plot_timeseries hands it to the GUI sink, and reports honestly
    when there is no GUI to draw in."""
    from d3ltool import auth
    from test_timeseries import FakeSession, _fake_granule, _opendap_routes

    monkeypatch.setattr(tools, "_SEARCHER",
                        lambda **query: [_fake_granule("2009-01-17", "h27v05")])
    session = FakeSession(_opendap_routes(["_250m_16_days_NDVI[0], 3470"]))
    monkeypatch.setattr(auth, "new_download_session", lambda: session)

    out = tools.point_timeseries(lon=116.567, lat=36.833, product="MOD13Q1",
                                 start="2009-01-01", end="2009-12-31")

    seen = {}
    monkeypatch.setattr(tools, "_PLOT_SINK",
                        lambda points, meta: seen.update(points=points,
                                                         meta=meta))
    plotted = tools.plot_timeseries(out["series_id"])
    assert plotted["plotted"] is True
    assert plotted["count"] == 1
    assert seen["points"] == [("2009-01-17", 0.347)]
    assert seen["meta"]["product"] == "MOD13Q1"
    assert seen["meta"]["layer"] == "_250m_16_days_NDVI"

    monkeypatch.setattr(tools, "_PLOT_SINK", None)   # e.g. plain MCP server
    assert tools.plot_timeseries(out["series_id"])["error"] == "not_in_gui"
    assert tools.plot_timeseries("ts999")["error"] == "unknown series_id"


def test_point_timeseries_budget_compaction(monkeypatch):
    """Long series are compacted to fit the tool-result budget with
    series_id and hint kept at the head — the loop could otherwise chop
    both off mid-points-array (DeepSeek diagnosed exactly the missing
    series_id on a 15-day hourly fetch)."""
    from d3ltool import auth
    from d3ltool.agent import loop as loop_mod
    from test_timeseries import (FakeSession, MERRA_DMR, TextResp,
                                 _dap_body, _fake_merra_granule)

    class _BytesSession(FakeSession):
        def get(self, url, **kwargs):
            if ".dap" in url and not url.endswith(".dmr.xml"):
                self.calls.append(("GET", url, None))
                body = _dap_body([270.0 + h * 0.2 for h in range(24)])
                return TextResp(body.decode("latin-1"))
            return super().get(url, **kwargs)

    monkeypatch.setattr(loop_mod, "TOOL_RESULT_LIMIT", 1180)
    monkeypatch.setattr(tools, "_SEARCHER",
                        lambda **query: [_fake_merra_granule("2020-01-01")])
    monkeypatch.setattr(auth, "new_download_session", lambda: _BytesSession(
        [("GET", ".dmr.xml", lambda kw: TextResp(MERRA_DMR))]))

    out = tools.point_timeseries(lon=116.567, lat=36.833,
                                 product="M2T1NXSLV",
                                 start="2020-01-01", end="2020-01-01")
    assert out["stats"]["count"] == 24          # stats cover the FULL series
    assert out["truncated"] is True
    assert len(out["points"]) == 12
    assert "tool budget" in out["hint"]
    assert out["series_id"].startswith("ts")
    assert out["layer_long_name"] == "2-meter_air_temperature"
    assert out["units"] == "K"
    # the compacted result itself stays within the loop's budget
    assert len(json.dumps(out, ensure_ascii=False, default=str)) \
        <= loop_mod.TOOL_RESULT_LIMIT + 200     # worst-case trim headroom
    # and the id still resolves in the plot cache
    assert tools.plot_timeseries(out["series_id"])["error"] == "not_in_gui"


def test_point_timeseries_tool_merra_truncates(monkeypatch):
    """Hourly MERRA-2 series: stats cover all 24 points while `limit`
    keeps the returned list small."""
    from d3ltool import auth
    from test_timeseries import (FakeSession, MERRA_DMR, TextResp,
                                 _dap_body, _fake_merra_granule)

    class _BytesSession(FakeSession):
        def get(self, url, **kwargs):
            if ".dap" in url and not url.endswith(".dmr.xml"):
                self.calls.append(("GET", url, None))
                body = _dap_body([270.0 + h for h in range(24)])
                return TextResp(body.decode("latin-1"))
            return super().get(url, **kwargs)

    monkeypatch.setattr(tools, "_SEARCHER",
                        lambda **query: [_fake_merra_granule("2020-01-01")])
    session = _BytesSession(
        [("GET", ".dmr.xml", lambda kw: TextResp(MERRA_DMR))])
    monkeypatch.setattr(auth, "new_download_session", lambda: session)

    out = tools.point_timeseries(lon=116.567, lat=36.833,
                                 product="M2T1NXSLV",
                                 start="2020-01-01", end="2020-01-01",
                                 limit=5)
    assert out["layer"] == "T2M"
    assert out["truncated"] is True
    assert len(out["points"]) == 5
    assert out["stats"]["count"] == 24
    assert out["stats"]["min"] == pytest.approx(270.0)
    assert out["stats"]["max"] == pytest.approx(293.0)
    assert "narrow start..end" in out["hint"]


def test_point_timeseries_tool_error(monkeypatch):
    from d3ltool import auth
    from test_timeseries import FakeSession

    monkeypatch.setattr(tools, "_SEARCHER", lambda **query: [])
    monkeypatch.setattr(auth, "new_download_session",
                        lambda: FakeSession([]))      # never reached
    out = tools.point_timeseries(lon=116.567, lat=36.833, product="MOD13Q1",
                                 start="2099-01-01", end="2099-01-31")
    assert out["error"] == "timeseries_failed"
    assert out["hint"]


def test_start_download_requires_auth(monkeypatch):
    _signed_out(monkeypatch)
    out = tools.start_download(urls=["https://example.com/a.h5"])
    assert out["error"] == "not_authenticated"
    assert "hint" in out

    assert tools.start_download(urls=[])["error"] == "no urls given"


def test_start_download_queues_and_completes(tmp_path, monkeypatch, range_server):
    payload = b"d3ltool-tool-test" * 1024
    url = range_server(payload)
    _signed_in(monkeypatch)

    out = tools.start_download(urls=[url], dest=str(tmp_path))
    assert out["count"] == 1
    item_id = out["items"][0]["id"]

    deadline = time.time() + 10
    while time.time() < deadline:
        status = tools.download_status()
        if status["items"] and status["items"][0]["state"] == "done":
            break
        time.sleep(0.02)
    status = tools.download_status()
    assert status["count"] == 1
    row = status["items"][0]
    assert row["state"] == "done"
    assert row["filename"] == "file.bin"
    assert (tmp_path / "file.bin").read_bytes() == payload


def test_duplicate_start_download_returns_same_id(tmp_path, monkeypatch, range_server):
    payload = b"x" * 4096
    url = range_server(payload)
    _signed_in(monkeypatch)
    dest = str(tmp_path / "dl")
    out1 = tools.start_download(urls=[url], dest=dest)
    out2 = tools.start_download(urls=[url], dest=dest)
    assert out1["items"] == out2["items"]     # engine dedupes by dest path


def test_cancel_and_retry_unknown_id():
    assert "error" in tools.cancel_download(999)
    assert "error" in tools.retry_download(999)


def test_download_status_without_engine():
    tools._reset_engine()
    out = tools.download_status()
    assert out == {"count": 0, "items": []}
