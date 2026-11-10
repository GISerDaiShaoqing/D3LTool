# -*- coding: utf-8 -*-
"""Search query construction & fallbacks (earthaccess mocked out)."""

import pytest

from d3ltool import search
from d3ltool.search import SearchParams


class FakeGranule:
    """Mimics earthaccess DataGranule surface used by d3ltool.search."""

    def __init__(self, name, url=None, size_mb=0.0, date="2020-03-01"):
        self._name = name
        self._size = size_mb
        umm = {"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": date}}}
        if url:
            umm["RelatedUrls"] = [
                {"URL": url, "Type": "GET DATA"},
                {"URL": url.replace("https://data.", "s3://prod-"), "Type": "GET DATA VIA DIRECT ACCESS"},
                {"URL": "https://example.com/opendap/x", "Type": "USE SERVICE API"},
            ]
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

    def data_links(self, access=None):
        return [r["URL"] for r in self._umm.get("RelatedUrls", [])]


def make_granule(name, url=None, size_mb=0.0):
    return FakeGranule(name, url=url, size_mb=size_mb)


def test_query_basics():
    p = SearchParams(short_name="vnp46a1", start="2020-03-01", end="2020-03-31")
    q = search.build_query(p)
    assert q["short_name"] == "VNP46A1"
    assert q["temporal"] == ("2020-03-01", "2020-03-31")
    assert q["count"] == 200
    assert "readable_granule_name" not in q


def test_query_with_tiles_and_bbox_and_version():
    p = SearchParams(short_name="MOD13Q1", start="2020-01-01", end="2020-01-31",
                     version="6.1", tiles=["H04V03", "h26v05"],
                     bbox=(100, 20, 120, 40), max_results=50)
    q = search.build_query(p)
    assert q["version"] == "6.1"
    assert q["readable_granule_name"] == ["*.h04v03.*", "*.h26v05.*"]
    assert q["bounding_box"] == (100, 20, 120, 40)
    assert q["count"] == 50


def test_run_search_client_side_tile_filter():
    captured = {}

    def fake_searcher(**kwargs):
        captured.update(kwargs)
        return [
            make_granule("LAADS:1", url="https://data.example/VNP46A1.A2020060.h04v03.002.1.h5"),
            make_granule("LAADS:2", url="https://data.example/VNP46A1.A2020061.h26v05.002.2.h5"),
            make_granule("LAADS:3", url="https://data.example/VNP46A1.A2020062.h31v10.002.3.h5"),
        ]

    p = SearchParams(short_name="VNP46A1", start="2020-03-01", end="2020-03-31",
                     tiles=["h04v03"])
    result = search.run_search(p, searcher=fake_searcher)
    assert captured["readable_granule_name"] == ["*.h04v03.*"]
    assert len(result) == 1
    assert search.granule_filename(result[0]).endswith("h04v03.002.1.h5")


def test_run_search_retries_when_version_returns_empty():
    calls = []

    def searcher(**kwargs):
        calls.append(dict(kwargs))
        if "version" in kwargs:
            return []          # e.g. retired version on CMR
        return [make_granule("M2T1NXSLV.1")]

    p = SearchParams(short_name="M2T1NXSLV", start="2019-08-01", end="2019-08-31",
                     version="9.9.9")
    result = search.run_search(p, searcher=searcher)
    assert len(calls) == 2
    assert "version" not in calls[1]
    assert len(result) == 1


def test_run_search_retries_when_version_raises():
    calls = []

    def searcher(**kwargs):
        calls.append(dict(kwargs))
        if "version" in kwargs:
            raise RuntimeError("no such version")
        return [make_granule("M2T1NXSLV.1")]

    p = SearchParams(short_name="M2T1NXSLV", start="2019-08-01", end="2019-08-31",
                     version="9.9.9")
    result = search.run_search(p, searcher=searcher)
    assert len(calls) == 2
    assert len(result) == 1


def test_links_prefer_https_get_data():
    g = make_granule("LAADS:9", url="https://data.example/VNP46A1.A2020061.h04v03.002.9.h5")
    links = search.granule_links(g)
    assert links == ["https://data.example/VNP46A1.A2020061.h04v03.002.9.h5"]
    assert not any(l.startswith("s3://") for l in links)
    assert "opendap" not in links[0]


def test_size_mb_property_and_method_compat():
    assert search.granule_size_mb(make_granule("x", size_mb=51.38)) == 51.4

    class MethodStyle:
        def size(self):
            return 12.34

    assert search.granule_size_mb(MethodStyle()) == 12.3


def test_tile_from_filename_when_native_id_has_none():
    g = make_granule("LAADS:8464904857",
                     url="https://data.example/VNP46A1.A2020061.h04v03.002.9.h5")
    assert search.granule_tile(g) == "h04v03"


def test_parse_tiles_and_bbox():
    assert search.parse_tiles("h04v03, H26V05 h04v03") == ["h04v03", "h26v05"]
    assert search.parse_bbox("100, 20, 120, 40") == (100.0, 20.0, 120.0, 40.0)
    assert search.parse_bbox("100 20 120 40") == (100.0, 20.0, 120.0, 40.0)
    assert search.parse_bbox("") is None
    with pytest.raises(ValueError):
        search.parse_bbox("1,2,3")
    with pytest.raises(ValueError):
        search.parse_bbox("120, 20, 100, 40")   # west >= east
    with pytest.raises(ValueError):
        search.parse_tiles("h99v99")


# ----------------------------------------------------- GLASS row dicts (v2.5)

GLASS_ROW = {
    "url": "https://glass.hku.hk/archive/LAI/MODIS/250M/2018/217/"
           "GLASS01D01.V60.A2018217.h28v05.2022013.hdf",
    "filename": "GLASS01D01.V60.A2018217.h28v05.2022013.hdf",
    "date": "2018-08-05",
    "tile": "h28v05",
    "size_mb": 0.0,
    "product": "LAI_MODIS_250M",
}


def test_glass_row_dicts_flow_through_accessors():
    """GLASS search returns plain row dicts; the same accessors that read
    earthaccess granules must read them unchanged (results table & tools
    never learn the difference)."""
    assert search.granule_filename(GLASS_ROW) == GLASS_ROW["filename"]
    assert search.granule_date(GLASS_ROW) == "2018-08-05"
    assert search.granule_tile(GLASS_ROW) == "h28v05"
    assert search.granule_links(GLASS_ROW) == [GLASS_ROW["url"]]
    assert search.granule_size_mb(GLASS_ROW) == 0.0
    assert search.granule_name(GLASS_ROW) == GLASS_ROW["filename"]


def test_run_search_routes_glass_variants(monkeypatch):
    import d3ltool.glass as glass

    seen = {}

    def fake_glass_search(short_name, start, end, tiles=None, bbox=None,
                          max_results=200, progress=None, cancelled=None):
        seen.update(short_name=short_name, start=start, tiles=tiles,
                    bbox=bbox, max_results=max_results)
        return [dict(GLASS_ROW)]

    monkeypatch.setattr(glass, "search", fake_glass_search)
    p = SearchParams(short_name="lai_modis_250m", start="2018-08-01",
                     end="2018-08-31", tiles=["h28v05"], max_results=5)
    rows = search.run_search(p)
    assert seen == {"short_name": "lai_modis_250m", "start": "2018-08-01",
                    "tiles": ["h28v05"], "bbox": None, "max_results": 5}
    assert rows[0]["filename"] == GLASS_ROW["filename"]
    assert search.granule_tile(rows[0]) == "h28v05"
