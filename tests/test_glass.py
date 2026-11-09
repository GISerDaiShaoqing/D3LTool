# -*- coding: utf-8 -*-
"""GLASS archive search (public glass.hku.hk directory listings, no CMR).

Network-free: listings are faked at glass._fetch_hrefs; the fixture mirrors
a real captured LAI composite folder page (Apache index style)."""

import pytest
import requests

from d3ltool import glass
from d3ltool.glass_registry import VARIANTS

LAI = "LAI_MODIS_250M"

# A trimmed capture of https://glass.hku.hk/archive/LAI/MODIS/250M/2018/217/ —
# the GLASS13D01 file is a deliberately misplaced file (wrong product code),
# exactly the kind the verified-variant prefix filter must drop.
LAI_217_HREFS = [
    "../",
    "GLASS01D01.V60.A2018217.h28v05.2022013.hdf",
    "GLASS01D01.V60.A2018217.h28v05.2022013.hdf.xml",
    "GLASS01D01.V60.A2018217.h29v05.2022013.hdf",
    "GLASS13D01.V10.A2018217.h28v05.2023064.hdf",
    "browse_preview.png",
]


@pytest.fixture
def fake_fetch(monkeypatch):
    """_fetch_hrefs -> canned listings keyed by URL substring."""
    calls = []

    def fake(url, session=None):
        calls.append(url)
        if "2018/217" in url:
            return list(LAI_217_HREFS)
        raise FileNotFoundError(url)

    monkeypatch.setattr(glass, "_fetch_hrefs", fake)
    return calls


# ---------------------------------------------------------------- registry

def test_registry_has_verified_variants():
    assert len(VARIANTS) == 133
    verified = {v["variant_id"] for v in VARIANTS.values() if v["verified"]}
    assert len(verified) == 131
    assert {"LAI_MODIS_250M", "NDVI_MODIS_250M", "EVI_MODIS_250M",
            "FVC_MODIS_500M", "Ta_MODIS"} <= verified
    skeletons = {v["variant_id"] for v in VARIANTS.values() if not v["verified"]}
    assert skeletons == {"LWRT_MODIS_InS", "SH_MODIS"}
    lai = glass.get_variant("lai_modis_250m")      # case-insensitive lookup
    assert lai["cadence_days"] == 8 and lai["layout"] == "year_doy"
    assert lai["code"] == "GLASS01D01" and lai["ext"] == "hdf" and lai["tiled"]
    # the four archive layouts, as measured by the R package's scan
    from collections import Counter
    assert Counter(v["layout"] for v in VARIANTS.values()) == {
        "year_doy": 76, "flat": 51, "year_files": 3, "year_yyyddd": 3}
    # ext/tiled derive from the R verification log's real granule samples:
    # AWGF day folders hold .tif, global CMG filenames carry no h##v##, and
    # BBE's code prefix is GHOSE03G01 — not every family starts with "GLASS"
    awgf = VARIANTS["awgf_lst_abi_cmg_005deg"]
    assert awgf["ext"] == "tif" and not awgf["tiled"]
    assert VARIANTS["bbe_avhrr_0_1d"]["code"] == "GHOSE03G01"
    assert VARIANTS["tpsce_avhrr"]["ext"] == "dat"


def test_is_glass_variant_and_url():
    assert glass.is_glass_variant("LAI_MODIS_250M")
    assert glass.is_glass_variant("  ndvi_modis_250m ")
    assert not glass.is_glass_variant("MOD13Q1")
    assert not glass.is_glass_variant("")
    assert glass.is_glass_url("https://glass.hku.hk/archive/AGB/")
    assert glass.is_glass_url("http://glass.hku.hk/x/y.hdf")
    assert not glass.is_glass_url(
        "https://ladsweb.modaps.eosdis.nasa.gov/allData/61/x.hdf")
    assert not glass.is_glass_url("not a url")


def test_get_variant_unknown_lists_hint():
    with pytest.raises(glass.GlassError, match="list_products"):
        glass.get_variant("MCD43A4")


# ------------------------------------------------------------------- doys

def test_doys_span_vs_start():
    v = glass.get_variant(LAI)
    span = glass.doys(v, "2018-08-01", "2018-12-31")
    assert span[0] == (2018, 209)          # Jul 28 + 8d window covers Aug 1
    assert len(span) == 20
    start = glass.doys(v, "2018-08-01", "2018-12-31", mode="start")
    assert start[0] == (2018, 217)         # first composite beginning in range
    assert len(start) == 19


def test_doys_cap_at_365_like_the_r_package():
    v = glass.get_variant(LAI)
    doys = glass.doys(v, "2020-12-01", "2020-12-31")   # leap year
    assert max(d for _, d in doys) == 361              # folder DOYs cap at 365


def test_doys_rejects_bad_input():
    v = glass.get_variant(LAI)
    with pytest.raises(glass.GlassError, match="later than end"):
        glass.doys(v, "2020-02-01", "2020-01-01")
    with pytest.raises(glass.GlassError, match="cadence unknown"):
        glass.doys(glass.get_variant("AGB_1KM_V01"), "2020-01-01", "2020-02-01")


# ------------------------------------------------------------------ tiles

def test_tiles_for_bbox_shanghai_matches_r_package_and_point_math():
    # the R package README example: Greater Shanghai -> h28v05
    assert glass.tiles_for_bbox(120.8, 30.6, 122.2, 31.9) == [(28, 5)]

    from d3ltool import tiles

    for lon, lat in [(121.5, 31.2), (116.4, 39.9), (102.7, 25.0),
                     (-58.4, -34.6), (20.5, 62.2)]:
        want = tiles.lonlat_to_tile(lon, lat)
        got = glass.tiles_for_bbox(lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5)
        assert want in got, f"{(lon, lat)} -> {want} missing from {got}"


def test_tiles_for_bbox_meridian_straddle():
    # a bbox crossing lon 0 just north of the equator (row v08 = 0-10N)
    # touches both h17 (x<0) and h18 (x>0)
    assert set(glass.tiles_for_bbox(-0.1, 0.4, 1.0, 0.6)) == {(17, 8), (18, 8)}
    assert glass.tiles_for_bbox(-1.0, 0.4, -0.05, 0.6) == [(17, 8)]
    assert glass.tiles_for_bbox(0.05, 0.4, 1.0, 0.6) == [(18, 8)]


def test_tiles_for_bbox_polar_rows_go_whole_row():
    got = glass.tiles_for_bbox(-180, 85, 180, 90)
    assert got == [(h, 0) for h in range(36)]      # safe over-inclusion
    assert glass.tiles_for_bbox(120, 30, 100, 40) == []   # inverted -> none


# ---------------------------------------------------------------- listing

def test_list_files_filters_like_the_r_package(fake_fetch):
    v = glass.get_variant(LAI)
    files = glass.list_files(v, year=2018, doy=217)
    # verified prefix drops the misplaced GLASS13D01 file and the png;
    # ext=hdf keeps .hdf and its .hdf.xml sidecar
    assert [f["filename"] for f in files] == [
        "GLASS01D01.V60.A2018217.h28v05.2022013.hdf",
        "GLASS01D01.V60.A2018217.h28v05.2022013.hdf.xml",
        "GLASS01D01.V60.A2018217.h29v05.2022013.hdf",
    ]
    assert files[0]["url"].endswith("/2018/217/GLASS01D01.V60.A2018217.h28v05.2022013.hdf")
    assert files[0]["year"] == 2018 and files[0]["doy"] == 217
    assert {f["tile"] for f in files} == {"h28v05", "h29v05"}

    h28 = glass.list_files(v, year=2018, doy=217, tiles=["H28V05"])
    assert [f["tile"] for f in h28] == ["h28v05", "h28v05"]
    assert fake_fetch[0].endswith("/2018/217/")


def test_list_files_flat_variant_uses_registry_ext(monkeypatch):
    """flat 布局：ext 来自登记表（台账实测样本），不再无差别全收。"""
    monkeypatch.setattr(
        glass, "_fetch_hrefs",
        lambda url, session=None: ["GLASS_AGB_5km_Y1992.tif",
                                   "GLASS_AGB_5km_Y1993.tif"])
    files = glass.list_files(glass.get_variant("AGB_0.05D"))
    assert [f["filename"] for f in files] == ["GLASS_AGB_5km_Y1992.tif",
                                              "GLASS_AGB_5km_Y1993.tif"]
    assert all(f["year"] is None and f["doy"] is None for f in files)


def test_ext_pattern_hdf_keeps_xml_sidecar():
    pat = glass._ext_pattern("hdf")
    assert pat.search("A2018217.h28v05.hdf")
    assert pat.search("A2018217.h28v05.hdf.xml")
    assert not pat.search("A2018217.h28v05.tif")
    assert glass._ext_pattern("hdf.xml").search("x.hdf.xml")
    assert not glass._ext_pattern("hdf.xml").search("x.hdf")
    # the pattern itself is case-sensitive — list_files lowercases the
    # filename before matching, so ".HDF" still gets through there
    assert glass._ext_pattern("hdf").search("x.HDF".lower())


# ----------------------------------------------------------------- search

def test_search_returns_accessor_compatible_rows(fake_fetch):
    rows = glass.search(LAI, "2018-08-01", "2018-08-31", tiles=["h28v05"])
    assert len(rows) == 2                          # hdf + xml of the h28v05 pair
    row = rows[0]
    assert row["product"] == LAI
    assert row["tile"] == "h28v05"
    assert row["date"] == "2018-08-05"             # doy 217 -> ISO date
    assert row["size_mb"] == 0.0 and row["size_bytes"] == 0
    assert row["url"].startswith("https://glass.hku.hk/archive/LAI/MODIS/250M/")
    # the CMR-path accessors must read these rows unchanged
    from d3ltool import search

    assert search.granule_filename(row) == row["filename"]
    assert search.granule_date(row) == "2018-08-05"
    assert search.granule_tile(row) == "h28v05"
    assert search.granule_links(row) == [row["url"]]


def test_search_respects_max_results(fake_fetch):
    rows = glass.search(LAI, "2018-08-01", "2018-08-31", tiles=["h28v05"],
                        max_results=1)
    assert len(rows) == 1


def test_search_flat_variant_rows_carry_no_date(monkeypatch):
    """Flat (static) variants ignore the date range: every listed file comes
    back with an empty date and the variant id as product."""
    monkeypatch.setattr(
        glass, "_fetch_hrefs",
        lambda url, session=None: ["GLASS_AGB_5km_Y1992.tif"])
    rows = glass.search("AGB_0.05D", "2020-01-01", "2020-12-31")
    assert len(rows) == 1
    assert rows[0]["date"] == "" and rows[0]["product"] == "AGB_0.05D"
    assert rows[0]["url"].endswith("GLASS_AGB_5km_Y1992.tif")


def test_search_all_folders_missing_raises(fake_fetch):
    with pytest.raises(glass.GlassError, match="404"):
        glass.search(LAI, "2019-01-01", "2019-02-01", tiles=["h28v05"])


def test_search_beyond_coverage_says_so(fake_fetch):
    """Verified variant + a range entirely beyond the archive's observed
    coverage (the GUI defaults to recent dates; GLASS archives lag years):
    the error must name the coverage window, not blame the layout."""
    with pytest.raises(glass.GlassError, match="2000-2025"):
        glass.search(LAI, "2026-10-23", "2026-11-07", tiles=["h28v05"])


def test_search_skeleton_variant_derives_folders(monkeypatch):
    """Cadence-unknown year_doy variants (SH_MODIS is the registry's real
    skeleton): derive year/DOY folders from the archive itself (the R
    package's legacy "start" mode)."""
    def fake(url, session=None):
        if url.endswith("/archive/SH/MODIS/"):
            return ["2018/", "2019/", "readme.txt"]
        if url.endswith("/2018/"):
            return ["001/", "193/"]
        if url.endswith("/2019/"):
            return ["001/"]
        if url.endswith("/2018/001/"):
            return ["GLASS09A01.V01.A2018001.h28v05.2020001.hdf"]
        if url.endswith("/2018/193/"):
            return ["GLASS09A01.V01.A2018193.h28v05.2020001.hdf"]
        if url.endswith("/2019/001/"):
            return ["GLASS09A01.V01.A2019001.h28v05.2021001.hdf"]
        raise FileNotFoundError(url)

    monkeypatch.setattr(glass, "_fetch_hrefs", fake)
    rows = glass.search("SH_MODIS", "2018-07-01", "2019-01-10",
                        tiles=["h28v05"])
    # legacy "start" mode keeps folders beginning inside the range:
    # 2018/193 (Jul 12) and 2019/001 (Jan 1); 2018/001 began before the range
    assert [r["date"] for r in rows] == ["2018-07-12", "2019-01-01"]
    assert all(r["product"] == "SH_MODIS" for r in rows)


def test_search_skeleton_without_year_folders_raises(monkeypatch):
    """Climatology-style roots (no year dirs) get a clear error, not a
    silently empty table."""
    monkeypatch.setattr(glass, "_fetch_hrefs",
                        lambda url, session=None: ["lwrt_2010.hdf"])
    with pytest.raises(glass.GlassError, match="not year/composite"):
        glass.search("LWRT_MODIS_InS", "2020-01-01", "2020-02-01")


def test_search_root_404_raises(monkeypatch):
    def fail(url, session=None):
        raise FileNotFoundError(url)

    monkeypatch.setattr(glass, "_fetch_hrefs", fail)
    with pytest.raises(glass.GlassError, match="404"):
        glass.search("AGB_1KM_V01", "2020-01-01", "2020-02-01")


# ------------------------------------------------- layouts 2/3/4 (verified)

BBE_2020_HREFS = [
    "../",
    "GHOSE03G01.V10.A2020001.2022006.hdf",
    "GHOSE03G01.V10.A2020002.2022006.hdf",
    "GHOSE03G01.V10.A2020003.2022006.hdf",
    "GLASS03G02.V40.A2020001.2021020.hdf",   # 0.5D-code file — prefix filter drops
    "notes.txt",
]

AWGF_2021181_HREFS = [
    "../",
    "all_sky_diurnal_lst_2021181_conus_goes16_lst_00.tif",
    "all_sky_diurnal_lst_2021181_conus_goes16_lst_01.tif",
]

TPSCE_2016_HREFS = [
    "../",
    "Combined_TPSCE_2016001.dat",
    "Combined_TPSCE_2016002.dat",
    "readme.pdf",
]


def test_search_year_files_layout(monkeypatch):
    """year_files（BBE AVHRR 逐日）：granule 直接放在 {year}/ 下，按文件名中的
    A{yyyy}{ddd} 片段过滤；同一年份的目录在一次检索里只列一次（memo）。"""
    calls = []

    def fake(url, session=None):
        calls.append(url)
        if url.endswith("/archive/BBE/AVHRR/0.1D/2020/"):
            return list(BBE_2020_HREFS)
        raise FileNotFoundError(url)

    monkeypatch.setattr(glass, "_fetch_hrefs", fake)
    rows = glass.search("BBE_AVHRR_0_1D", "2020-01-01", "2020-01-02")
    assert [r["date"] for r in rows] == ["2020-01-01", "2020-01-02"]
    assert all(r["filename"].startswith("GHOSE03G01") for r in rows)
    assert all(r["tile"] == "" for r in rows)      # 全球 CMG：无瓦片号
    assert sum(1 for c in calls if c.endswith("/2020/")) == 1


def test_search_year_files_annual_collection(monkeypatch):
    """cadence 为空的 year_files（TPSCE）：按年列出、无合成期过滤；
    文件名无 A-token，日期退化为年份字符串。"""
    def fake(url, session=None):
        if url.endswith("/archive/TPSCE/AVHRR/2016/"):
            return list(TPSCE_2016_HREFS)
        raise FileNotFoundError(url)

    monkeypatch.setattr(glass, "_fetch_hrefs", fake)
    rows = glass.search("TPSCE_AVHRR", "2016-01-01", "2016-12-31")
    assert [r["filename"] for r in rows] == ["Combined_TPSCE_2016001.dat",
                                             "Combined_TPSCE_2016002.dat"]
    assert all(r["date"] == "2016" for r in rows)


def test_search_year_yyyddd_layout(monkeypatch):
    """year_yyyddd（AWGF_LST）：日目录是 7 位 YYYYDDD（不是 8 位）；全球 CMG
    连 tiles 都给了也照样忽略。"""

    def fake(url, session=None):
        if url.endswith("/AWGF_LST/ABI/CMG_005deg/2021/2021181/"):
            return list(AWGF_2021181_HREFS)
        raise FileNotFoundError(url)

    monkeypatch.setattr(glass, "_fetch_hrefs", fake)
    rows = glass.search("AWGF_LST_ABI_CMG_005deg", "2021-06-30",
                        "2021-06-30", tiles=["h25v05"])
    assert len(rows) == 2
    assert all(r["filename"].endswith(".tif") for r in rows)
    assert all(r["date"] == "2021-06-30" for r in rows)
    assert all(r["tile"] == "" for r in rows)


def test_search_flat_ignores_dates_and_tiles(monkeypatch):
    """flat（KGClim）：静态文件集与日期/瓦片无关，登记表 ext（.tif）生效。"""

    def fake(url, session=None):
        if url.endswith("/KGClim/KGClim_V1_historical/1981_2010/"):
            return ["kc_1981_2010_lst.tif", "kc_1981_2010_ndvi.tif",
                    "readme.pdf"]
        raise FileNotFoundError(url)

    monkeypatch.setattr(glass, "_fetch_hrefs", fake)
    rows = glass.search("KGClim_KGClim_V1_historical_1981_2010",
                        "2026-10-01", "2026-11-01", tiles=["h25v05"])
    assert len(rows) == 2
    assert all(r["date"] == "" and r["tile"] == "" for r in rows)


def test_search_flat_404_names_the_folder(monkeypatch):
    def fail(url, session=None):
        raise FileNotFoundError(url)

    monkeypatch.setattr(glass, "_fetch_hrefs", fail)
    with pytest.raises(glass.GlassError, match="404"):
        glass.search("KGClim_KGClim_V1_historical_1981_2010",
                     "2020-01-01", "2020-02-01")


# --------------------------------------------------- politeness (measured)

class _OkResp:
    status_code = 200
    text = '<a href="GLASS01D01.V60.A2018217.h28v05.hdf">f</a>'

    def raise_for_status(self):
        pass


def _quiet_politeness(monkeypatch):
    monkeypatch.setattr(glass, "LISTING_BACKOFFS", (0.0, 0.0))
    monkeypatch.setattr(glass, "LISTING_COOLDOWN", 0.0)
    monkeypatch.setattr(glass, "LISTING_MIN_INTERVAL", 0.0)
    glass._LAST_LISTING[0] = 0.0


def test_fetch_hrefs_backs_off_and_succeeds(monkeypatch):
    """glass.hku.hk 对连续目录请求间歇限速：瞬时失败按 8/24/72s 退避重试。"""
    _quiet_politeness(monkeypatch)
    attempts = []

    class _Sess:
        def get(self, url, timeout=None):
            attempts.append(url)
            if len(attempts) < 3:
                raise requests.Timeout("rate limited")
            return _OkResp()

    hrefs = glass._fetch_hrefs("https://glass.hku.hk/archive/X/", _Sess())
    assert hrefs == ["GLASS01D01.V60.A2018217.h28v05.hdf"]
    assert len(attempts) == 3


def test_fetch_hrefs_gives_up_after_cooldown(monkeypatch):
    """退避穷尽后冷却 15s 再试最后一次，仍失败才上抛。"""
    _quiet_politeness(monkeypatch)
    attempts = []

    class _Sess:
        def get(self, url, timeout=None):
            attempts.append(url)
            raise requests.ConnectionError("still limited")

    with pytest.raises(requests.ConnectionError):
        glass._fetch_hrefs("https://glass.hku.hk/x/", _Sess())
    assert len(attempts) == 4     # 初次 + 2 次退避 + 冷却后末次


def test_fetch_hrefs_404_is_not_retried(monkeypatch):
    """404 是稀疏合成的正常形态，绝不重试。"""
    _quiet_politeness(monkeypatch)
    attempts = []

    class _Resp404:
        status_code = 404

        def raise_for_status(self):
            pass

    class _Sess:
        def get(self, url, timeout=None):
            attempts.append(url)
            return _Resp404()

    with pytest.raises(FileNotFoundError):
        glass._fetch_hrefs("https://glass.hku.hk/x/2018/999/", _Sess())
    assert len(attempts) == 1


def test_fetch_hrefs_spaces_requests(monkeypatch):
    """任意两次目录抓取之间至少间隔 LISTING_MIN_INTERVAL。"""
    monkeypatch.setattr(glass, "LISTING_BACKOFFS", (0.0,))
    monkeypatch.setattr(glass, "LISTING_COOLDOWN", 0.0)
    monkeypatch.setattr(glass, "LISTING_MIN_INTERVAL", 0.05)
    glass._LAST_LISTING[0] = 0.0
    sleeps = []
    monkeypatch.setattr(glass.time, "sleep", lambda s: sleeps.append(s))

    class _Sess:
        def get(self, url, timeout=None):
            return _OkResp()

    glass._fetch_hrefs("https://glass.hku.hk/a/", _Sess())
    glass._fetch_hrefs("https://glass.hku.hk/b/", _Sess())
    assert any(0.04 <= s <= 0.2 for s in sleeps)
