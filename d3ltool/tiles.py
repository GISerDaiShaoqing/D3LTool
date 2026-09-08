# -*- coding: utf-8 -*-
"""MODIS/VIIRS sinusoidal tile grid helpers.

The operational tile grid is the 36x18 Integerized Sinusoidal grid:
tile (h, v) covers 10 deg of longitude and 10 deg of latitude,
h counted west->east from 180W, v counted north->south from 90N
(v00 = 80N-90N ... v17 = 90S-80S).
"""

import math
import re

N_COLS = 36
N_ROWS = 18
R_SIN = 6371007.181            # MODIS sinusoidal sphere radius (m)
TILE_SIZE = 1111950.5196666666  # tile edge length (m), = 2*pi*R/72

_TILE_RE = re.compile(r"^h(\d{1,2})v(\d{1,2})$", re.IGNORECASE)


def tile_name(h: int, v: int) -> str:
    return f"h{h:02d}v{v:02d}"


def parse_tile(text: str):
    """Parse 'h04v03' -> (4, 3). Raises ValueError on bad input."""
    m = _TILE_RE.match(text.strip())
    if not m:
        raise ValueError(f"bad tile id: {text!r} (expected like h04v03)")
    h, v = int(m.group(1)), int(m.group(2))
    if not (0 <= h < N_COLS and 0 <= v < N_ROWS):
        raise ValueError(f"tile out of range: {text!r}")
    return h, v


def lonlat_to_tile(lon: float, lat: float):
    """Return (h, v) for a longitude/latitude degree pair."""
    lon = ((float(lon) + 180.0) % 360.0 + 360.0) % 360.0 - 180.0
    lat = max(-90.0, min(90.0, float(lat)))
    h = int((lon + 180.0) // 10.0)
    v = int((90.0 - lat) // 10.0)
    return min(N_COLS - 1, max(0, h)), min(N_ROWS - 1, max(0, v))


def tile_bounds_lonlat(h: int, v: int):
    """Return (lon_min, lat_min, lon_max, lat_max) of a tile, degrees."""
    if not (0 <= h < N_COLS and 0 <= v < N_ROWS):
        raise ValueError(f"tile index out of range: h={h}, v={v}")
    lon_min = -180.0 + 10.0 * h
    lon_max = lon_min + 10.0
    lat_max = 90.0 - 10.0 * v
    lat_min = lat_max - 10.0
    return lon_min, lat_min, lon_max, lat_max


def tile_center_lonlat(h: int, v: int):
    lon_min, lat_min, lon_max, lat_max = tile_bounds_lonlat(h, v)
    return (lon_min + lon_max) / 2.0, (lat_min + lat_max) / 2.0


def row_width_fraction(v: int) -> float:
    """Relative half-width of tile row v on a sinusoidal globe drawing (0..1]."""
    _, lat_min, _, lat_max = tile_bounds_lonlat(0, v)
    center = math.radians((lat_min + lat_max) / 2.0)
    return max(0.0, math.cos(center))
