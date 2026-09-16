# D3L Tool of NASA Satellite

|Author|Shaoqing Dai|
|---|---|
|E-mail|dsq1993qingge@163.com|
|Website|https://gisersqdai.top/D3LTool/|

[中文说明](READMEcn.md)

D3L Tool v2 is a free & open-source tool to **search and download** NASA Earth science data —
the whole workflow (login → search → download) inside one app, built on NASA's official
[earthaccess](https://earthaccess.readthedocs.io/) library and the CMR search service.
No more manual order creation, no more browser automation.

## Features

- **Built-in search**: by product, date range, MODIS/VIIRS sinusoidal tile (clickable 36×18 tile map)
  or bounding box — search works without an Earthdata login
- **Coverage**: MODIS, VIIRS (LAADS DAAC), MERRA-2 (GES DISC); any CMR short_name works too
- **Robust downloads**: multi-threaded queue, chunked progress, HTTP Range resume,
  automatic retry, size validation
- **Bilingual UI**: one-click 中文 / English switch (PySide6)
- **Cross-platform**: Windows exe / macOS .app / Linux binary (CI builds), or `pip install d3ltool`
- **Proxy support** for complex network environments

## Install

Requires Python 3.10+.

```bash
python -m pip install -e .
```

Development (incl. pytest): `python -m pip install -e ".[dev]"`

## Usage

### GUI

```bash
d3ltool-gui     # or: python -m d3ltool
```

1. **Settings → Sign in to Earthdata** with your free
   [NASA Earthdata](https://urs.earthdata.nasa.gov/) account
   (search works without login; downloads need it; credentials stay in the local `~/.netrc`)
2. Pick a product, date range, and click tiles on the map (or type `h04v03`, or enter a bbox)
3. Hit **Search**, tick files, **Add to download queue**

### CLI

```bash
d3ltool login
d3ltool search VNP46A1 --start 2020-03-01 --end 2020-03-31 --tile h04v03
d3ltool download VNP46A1 --start 2020-03-01 --end 2020-03-31 --tile h04v03 --dest D:/data
d3ltool search M2T1NXSLV --start 2019-08-01 --end 2019-08-31 --bbox 100 20 120 40
```

## Standalone builds / Release

Download prebuilt packages from
[GitHub Releases](https://github.com/GISerDaiShaoqing/D3LTool/releases/latest):
Windows exe, macOS .app (Apple Silicon & Intel) and Linux binary are built
automatically by CI when a `v*` tag is pushed.

Build locally:

```bash
pyinstaller D3LToolNASA.spec --noconfirm   # -> dist/D3LToolNASA(.exe/.app)
```

## Documentation

- Project website: <https://gisersqdai.top/D3LTool/>
- [Documentation (EN)](https://gisersqdai.top/D3LTool/documentation.html) /
  [文档（中文）](https://gisersqdai.top/D3LTool/documentationcn.html)
- Legacy v1.0 (2018, browser automation) READMEs live in [docs/legacy/](docs/legacy/)

## Changelog

- **2026-09 v2.0.2** — reliable Earthdata login: adapts to the earthaccess 0.19 auth
  singleton, session auto-restored from the local netrc file at startup, precise
  login diagnostics (401 / network / blocked account)
- 2026-09 v2.0.0 — full rewrite: earthaccess/CMR search, tile map, resumable downloads,
  PySide6 bilingual UI, cross-platform
- 2018-04-27 v1.0 — first release (browser automation order downloads)

## Credits & License

- v1.0 (2018) created by Dai Shaoqing; v2.0 rewritten on top of
  [earthaccess](https://earthaccess.readthedocs.io/) / CMR
- Released under the [MIT license](https://mit-license.org/)
- Questions? [Submit an issue](https://github.com/GISerDaiShaoqing/D3LTool/issues)
  or contact dsq1993qingge@163.com
