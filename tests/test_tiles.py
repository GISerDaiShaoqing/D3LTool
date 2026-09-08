# -*- coding: utf-8 -*-
"""Tile math tests (known MODIS grid references)."""

import pytest

from d3ltool import tiles


def test_prime_meridian_equator():
    # 0-10E / 0-10N is h18v08
    assert tiles.lonlat_to_tile(1, 1) == (18, 8)
    assert tiles.lonlat_to_tile(5, 5) == (18, 8)


def test_beijing_h29v05():
    # Beijing 116.4E 39.9N -> column 110E-120E (h29), row 30N-40N (v05)
    assert tiles.lonlat_to_tile(116.4, 39.9) == (29, 5)


def test_us_west_h04v03():
    # 140W-130W / 50N-60N is h04v03 (as seen in VNP46A1 h04v03 files)
    assert tiles.lonlat_to_tile(-135, 55) == (4, 3)


def test_bounds_and_inverse():
    lon_min, lat_min, lon_max, lat_max = tiles.tile_bounds_lonlat(4, 3)
    assert (lon_min, lat_min, lon_max, lat_max) == (-140, 50, -130, 60)
    # round trip through the box center
    h, v = tiles.lonlat_to_tile((lon_min + lon_max) / 2, (lat_min + lat_max) / 2)
    assert (h, v) == (4, 3)


def test_parse_and_name():
    assert tiles.parse_tile("H04V03") == (4, 3)
    assert tiles.tile_name(4, 3) == "h04v03"
    with pytest.raises(ValueError):
        tiles.parse_tile("h40v03")
    with pytest.raises(ValueError):
        tiles.parse_tile("04v03")


def test_edges_clamped():
    h, v = tiles.lonlat_to_tile(180, -90)
    assert (h, v) == (0, 17)
    h, v = tiles.lonlat_to_tile(-180, 90)
    assert (h, v) == (0, 0)


def test_row_width_fraction_symmetry():
    assert tiles.row_width_fraction(8) == pytest.approx(tiles.row_width_fraction(9))
    assert tiles.row_width_fraction(0) < tiles.row_width_fraction(8)
