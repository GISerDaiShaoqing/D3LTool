# -*- coding: utf-8 -*-
"""links.py: the browser-assisted download hand-offs — a pure-URL .txt
list for `wget -i` / `aria2c -i` and a self-contained .html index page
for a logged-in browser (no plugin, no extension required to click)."""

import pytest

from d3ltool import links


URLS = [
    "https://ladsweb.modaps.eosdis.nasa.gov/a.hdf",
    "https://files.gesdisc.eosdis.nasa.gov/b.nc",
]


def test_sanitize_stem_is_filename_safe():
    assert links.sanitize_stem("my batch/2025") == "my_batch_2025"
    assert links.sanitize_stem("../../evil") == ".._.._evil"
    assert links.sanitize_stem('a"b:c') == "a_b_c"
    assert len(links.sanitize_stem("x" * 400)) == 120
    assert links.sanitize_stem("") == "d3ltool_links"


def test_export_txt_is_pure_url_list(tmp_path):
    res = links.export_links(URLS, tmp_path, "urls", fmt="txt")
    text = (tmp_path / "urls.txt").read_text(encoding="utf-8")
    assert text.splitlines() == URLS           # byte-exact, no headers
    assert res["txt"].endswith("urls.txt")
    assert res["html"] is None
    assert res["count"] == 2 and res["skipped"] == 0


def test_export_html_is_self_contained(tmp_path):
    links.export_links({"url": URLS[0], "filename": "A.hdf"},
                       tmp_path, stem="x", fmt="html")
    page = (tmp_path / "x.html").read_text(encoding="utf-8")
    assert "A.hdf" in page and 'href="' in page
    # self-contained means no external css/js/images — the granule hrefs
    # themselves are the point, but no other resource is fetched
    for forbidden in ("<script", "<img", "<link", "@import"):
        assert forbidden not in page


def test_export_both_dedups_and_keeps_order(tmp_path):
    res = links.export_links(URLS + [URLS[0]], tmp_path, stem="d", fmt="both")
    txt = (tmp_path / "d.txt").read_text(encoding="utf-8")
    assert txt.splitlines() == URLS
    assert res["count"] == 2 and res["skipped"] == 0


def test_bad_schemes_are_skipped(tmp_path):
    res = links.export_links(
        URLS + ["ftp://x/y", "file:///c/z", {"not": "url"}],
        tmp_path, stem="s", fmt="txt")
    assert res["count"] == 2 and res["skipped"] == 3
    with pytest.raises(ValueError):          # nothing survivable at all
        links.export_links(["ftp://x/y"], tmp_path, stem="n", fmt="both")


def test_bad_fmt_raises(tmp_path):
    with pytest.raises(ValueError, match="fmt"):
        links.export_links(URLS, tmp_path, fmt="rss")


def test_prepare_accepts_granule_shapes():
    items, skipped = links.prepare_items([
        {"links": [URLS[0]], "filename": "a.hdf"},
        {"links": [{"url": URLS[1]}]},           # nested umm-style row
        URLS[0],                                 # plain string dup -> deduped
        "https://ladsweb.modaps.eosdis.nasa.gov/c.h5",
    ])
    assert skipped == 0
    assert [it["filename"] for it in items] == ["a.hdf", "b.nc", "c.h5"]
    assert all(it["url"].startswith("https://") for it in items)
