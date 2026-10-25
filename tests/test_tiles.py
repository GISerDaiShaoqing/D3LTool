# -*- coding: utf-8 -*-
"""Tile math tests (known MODIS grid references)."""

import pytest

from d3ltool import tiles


def test_prime_meridian_equator():
    # 0-10E / 0-10N is h18v08
    assert tiles.lonlat_to_tile(1, 1) == (18, 8)
    assert tiles.lonlat_to_tile(5, 5) == (18, 8)


def test_beijing_h26v05():
    # Ground truth from the C6.1 files themselves (their Latitude/Longitude
    # arrays): h26v05 covers ~104.4E-117.5E at 40N, so Beijing 116.4E/39.9N
    # falls in h26v05 — NOT h29: C6 tiles are sinusoidal squares, not
    # 10-degree lon/lat boxes.
    assert tiles.lonlat_to_tile(116.4, 39.9) == (26, 5)


def test_yucheng_h27v05():
    # The 2017-blog Yucheng station point (36.833N, 116.567E)
    assert tiles.lonlat_to_tile(116.567, 36.833) == (27, 5)


def test_us_west_h10v03():
    # Gulf of Alaska 135W/55N belongs to the sinusoidal square h10v03
    assert tiles.lonlat_to_tile(-135, 55) == (10, 3)


def test_bounds_are_display_boxes_only():
    # tile_bounds_lonlat stays the classic 10-degree box for display text;
    # box centers far from the equator do NOT map back to the same tile.
    lon_min, lat_min, lon_max, lat_max = tiles.tile_bounds_lonlat(4, 3)
    assert (lon_min, lat_min, lon_max, lat_max) == (-140, 50, -130, 60)
    h, v = tiles.lonlat_to_tile((lon_min + lon_max) / 2, 55)
    assert (h, v) == (10, 3)


def test_parse_and_name():
    assert tiles.parse_tile("H04V03") == (4, 3)
    assert tiles.tile_name(4, 3) == "h04v03"
    with pytest.raises(ValueError):
        tiles.parse_tile("h40v03")
    with pytest.raises(ValueError):
        tiles.parse_tile("04v03")


def test_edges_clamped():
    # Longitude is mathematically ambiguous at the poles (every meridian
    # meets); the sinusoidal x collapses, so any h is as good as another.
    h, v = tiles.lonlat_to_tile(180, -90)
    assert v == 17
    h, v = tiles.lonlat_to_tile(-180, 90)
    assert v == 0


def test_row_width_fraction_symmetry():
    assert tiles.row_width_fraction(8) == pytest.approx(tiles.row_width_fraction(9))
    assert tiles.row_width_fraction(0) < tiles.row_width_fraction(8)
