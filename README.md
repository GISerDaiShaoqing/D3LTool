# D3L Tool of NASA Satellite

|Author|Shaoqing Dai|
|---|---|
|E-mail|dsq1993qingge@163.com|
|Website|https://gisersqdai.top/D3LTool/|

[中文说明](READMEcn.md)

D3L Tool v2 is a free & open-source tool to **search and download** NASA Earth science data —
the whole workflow (login → search → download) inside one app, built on NASA's official
[earthaccess](https://earthaccess.readthedocs.io/) library and the CMR search service —
and, since v2.3, to sample a pixel's time series over OPeNDAP and plot it in-app.
No more manual order creation, no more browser automation.

## Features

- **Built-in search**: by product, date range, MODIS/VIIRS sinusoidal tile (clickable 36×18 tile map)
  or bounding box — search works without an Earthdata login
- **Coverage**: MODIS, VIIRS (LAADS DAAC), MERRA-2 (GES DISC); any CMR short_name works too
- **Robust downloads**: multi-threaded queue, chunked progress, HTTP Range resume,
  automatic retry, size validation
- **MCP server** (new in v2.1): `d3ltool-mcp` exposes search / tile math / downloads
  as [MCP tools](docs/mcp.md) for Claude Desktop, Cursor, ZCode and other AI clients
- **AI Assistant drawer** (new in v2.1, redesigned in v2.2): a right-edge
  slide-out panel over the main window — plug any OpenAI-compatible API key
  into the ⚙ popup settings and drive search & download with plain language
  (DeepSeek / Qwen / Kimi / GLM / OpenAI / Ollama…); user background image
  supported; downloads ask for confirmation first — see [docs/mcp.md](docs/mcp.md)
- **Time series** (new in v2.3): its own right-edge drawer plots a pixel's
  changing values for MODIS/VIIRS and MERRA-2 products over a date range
  (latitude/longitude in, line chart out, one-click CSV export) — sampled
  directly via NASA OPeNDAP, no third-party subset service; the modern
  revival of the 2017 MODIS Web Service experiment, in-app
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

### MCP / AI Assistant

Both channels share one tool set — `check_auth`, `list_products`, `point_to_tile`,
`tile_bounds`, `search_granules`, `start_download`, `download_status`,
`cancel_download`, `retry_download`. Passwords are never tool parameters:
downloads reuse the Earthdata sign-in persisted on this machine.

```bash
python -m pip install "d3ltool[mcp]"   # then point your MCP client at `d3ltool-mcp`
```

Client wiring (Claude Desktop / Cursor / ZCode) and the in-app AI Assistant
guide live in [docs/mcp.md](docs/mcp.md).

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

## Citing

If you use D3LTool in your research, please cite it — see [CITATION.cff](CITATION.cff):

```bibtex
@software{Dai_D3LTool_NASA_Satellite_2026,
  author  = {Dai, Shaoqing},
  orcid   = {0000-0003-0858-4728},
  title   = {D3L Tool of NASA Satellite: a bilingual GUI for searching and downloading NASA MODIS/VIIRS/MERRA-2 data},
  version = {2.3.0},
  year    = {2026},
  url     = {https://github.com/GISerDaiShaoqing/D3LTool},
}
```

## Changelog

- **2026-10 v2.3.0** — new **Time Series** drawer (its own right-edge drawer
  with an "TS" edge tab next to the AI one; opening one closes the other):
  type any MODIS/VIIRS product + layer, a latitude/longitude point and a
  date range, and the in-app line chart (QtCharts) shows how that pixel
  changed — the modern, in-app revival of the 2017 MODIS Web Service
  experiment. Pixel values are sampled **directly via NASA OPeNDAP** —
  MODIS/VIIRS from LAADS, hourly **MERRA-2** from the GES DISC cloud
  gateway (the same servers and credentials as the downloader: no
  AppEEARS, no proxy, mainland-network friendly) — with one-click **CSV
  export**. The same sampling is also exposed to MCP clients and the
  in-app AI assistant as `point_timeseries` + `plot_timeseries` — the
  assistant fetches the series and draws it straight into the app's
  time-series drawer. Bonus fix: point→tile math now uses the true sinusoidal grid (pixel-exact against
  real files) instead of the old 10° box approximation, making the
  lat/lon locator and the AI's point_to_tile accurate again. Layer names
  now match loosely — plain 'NDVI' resolves to _250m_16_days_NDVI
  (case/underscore-insensitive) — and the agent chat shows the reason
  behind a failed tool call instead of just its error key; a product
  name CMR doesn't know (a model's guess like MCD13Q1) is called out as
  such instead of blaming the date range. Assistant-side
  plotting now relays through a queued signal: charting runs on the GUI
  thread, fixing the intermittent hard crash when plot_timeseries touched
  the drawer from the agent worker thread. Sampling itself now reports
  live progress in the chat (one updating line) and the stop button
  aborts it between granule requests — a temperature turn used to grind
  silently for minutes on the slow GES DISC gateway. Tool results now
  carry the layer's long name and native units (T2M is Kelvin, °C = K −
  273.15), so a bare series of 264–277 no longer reads as "crypto
  prices" to the model — and a dead-air empty reply is now retried
  (then reported visibly) instead of silently ending the turn, which
  used to look like a frozen drawer. Layer hints under 3 characters no
  longer substring-match everything — a lone 'T' once grabbed CLDTMP
  (the cloud temperature) instead of T2M — they raise with the available
  layer names instead, and a successful fetch tells the in-app agent to
  call plot_timeseries for the user. A fetch longer than the 6 000-char
  tool budget is compacted adaptively with series_id kept at the head —
  the loop used to slice mid-points-array and chop exactly the fields
  the model needed (DeepSeek caught it). Hourly stamps now follow the
  file's native 00:30–23:30 order — the old (h+1)%24 mapping wrapped
  each day's last hour to 00:30 and drew backward diagonals across the
  chart — and the assistant welcome text now notes how the chart treats
  masked pixels and native units
- **2026-10 v2.2.0** — AI Assistant redesigned as a floating right-edge
  drawer: the data page keeps its own layout, API settings moved into a
  popup dialog, user background image supported
- **2026-10 v2.1.1** — fix: AI-assistant download confirmation (a Yes click
  was reported as declined — PySide6 `Signal(dict)` copies payloads across
  the queued connection, now `Signal(object)`); MCP server lazily restores
  the saved Earthdata session from ~/.netrc
- **2026-10 v2.1.0** — MCP server (`d3ltool-mcp`: 9 tools over stdio for Claude
  Desktop / Cursor / ZCode, credential-reuse design) and a built-in AI Assistant
  chat page (any OpenAI-compatible provider, agent tool calls, download
  confirmation, shared task table)
- **2026-09 v2.0.3** — product catalog dialog (browse per satellite, bilingual
  descriptions, filter, double-click to apply); CI switched to Apple Silicon
  only (GitHub retired the macos-13 Intel runner)
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
