# D3L Tool of NASA Satellite

|Author|Shaoqing Dai|
|---|---|
|E-mail|dsq1993qingge@163.com|
|Website|https://gisersqdai.top/D3LTool/|

[中文说明](READMEcn.md)

[![GLASS engine: glass.sqdaitools](https://img.shields.io/badge/GLASS%20engine-glass.sqdaitools%20v0.1.0-2ea44f)](https://github.com/GISerDaiShaoqing/glass.sqdaitools)

D3L Tool v2 is a free & open-source tool to **search and download** NASA Earth science data —
the whole workflow (login → search → download) inside one app, built on NASA's official
[earthaccess](https://earthaccess.readthedocs.io/) library and the CMR search service —
and, since v2.3, to sample a pixel's time series over OPeNDAP and plot it in-app.
**GLASS support (v2.5.0)**: the public **GLASS** (Global Land Surface Satellite)
archive joins the same workflow — no sign-in — with the GLASS engine ported from
the author's R package
[glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools)
([docs](https://giserdaishaoqing.github.io/glass.sqdaitools/), v0.1.0):
D3LTool finds & downloads, the R package does the post-processing — use the
two as a matched pair. No more manual order creation, no more browser automation.

## Features

- **Built-in search**: by product, date range, MODIS/VIIRS sinusoidal tile (clickable 36×18 tile map)
  or bounding box — search works without an Earthdata login
- **Coverage**: MODIS, VIIRS (LAADS DAAC), MERRA-2 (GES DISC) — any CMR short_name works too
- **GLASS data source** (new in v2.5.0): search & download the GLASS (Global Land
  Surface Satellite) suite — 130+ variants from the public
  [glass.hku.hk](https://glass.hku.hk) archive, no Earthdata sign-in. The engine
  is ported from the author's R package
  [glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools/tree/v0.1.0)
  v0.1.0 (archive-scan variant registry, tile mapping, composite-DOY listing,
  verified-product filters); fill-value handling, mosaicking, reprojection and
  temporal compositing stay in R — see [GLASS support in 2.5.0](#glass-support-in-250)
- **Robust downloads**: multi-threaded queue, chunked progress, HTTP Range resume,
  automatic retry, size validation
- **MCP server** (new in v2.1): `d3ltool-mcp` exposes search / tile math / downloads
  as [MCP tools](docs/mcp.md) for Claude Desktop, Claude Code, Codex, Cursor,
  OpenCode, Qoder, ZCode and other AI clients
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
d3ltool search LAI_MODIS_250M --start 2018-08-01 --end 2018-12-31 --tile h28v05   # GLASS, no login
```

### GLASS support in 2.5.0

The GLASS module is ported from the author's R package
[glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools/tree/v0.1.0)
([docs](https://giserdaishaoqing.github.io/glass.sqdaitools/), v0.1.0):
the archive-scan variant registry (130+ product × source × resolution
variants, five of them verified against real granules), the sinusoidal tile
mapping, the composite-DOY expansion and the verified-product filters all
come from it. The two projects are a **matched pair** with a clear split:

| | does |
|---|---|
| **D3LTool** (GUI / CLI / MCP) | GLASS product discovery & batch download — resumable, size-validated, no sign-in (the archive is public) |
| **R: glass.sqdaitools** | fill-value & scale-factor handling, multi-tile mosaicking, reprojection & ROI cropping, temporal compositing (`terra`-based) |

Post-process in R whatever D3LTool downloaded:

```r
# R >= 4.1; heavy deps terra / sf
devtools::install_github("GISerDaiShaoqing/glass.sqdaitools")
glass.sqdaitools::glass_process(files, roi = my_roi,
                                product = "LAI_MODIS_250M",
                                fun = "mean", outfile = "lai_2023_mean.tif")
```

![One sentence to the built-in AI assistant — "download GLASS EVI for Xiamen,
2024-10-23" — resolves the variant via `list_products`, searches by bbox via
`search_granules` and queues the files via `start_download`, no sign-in
anywhere; post-process the files in R with glass.sqdaitools](images/GlassDownload.png)

Compatibility: D3L Tool **2.5.0** ↔ glass.sqdaitools **≥ 0.1.0** — breaking
API changes will be announced in both projects' release notes.
GLASS data are produced by the GLASS product team
([glass.hku.hk](https://glass.hku.hk)); please follow their citation policy
when using the data.

### MCP / AI Assistant

Both channels share one tool set — `check_auth`, `list_products`, `point_to_tile`,
`tile_bounds`, `search_granules`, `start_download`, `download_status`,
`cancel_download`, `retry_download`, plus `point_timeseries` / `plot_timeseries`
(v2.3) and the browser-handoff pair `export_download_urls` / `open_download_page`
(v2.4). Passwords are never tool parameters:
downloads reuse the Earthdata sign-in persisted on this machine (GLASS archive
URLs are public and need no sign-in).

```bash
python -m pip install "d3ltool[mcp]"   # then point your MCP client at `d3ltool-mcp`
```

Client wiring (Claude Desktop / Claude Code / Codex / Cursor / OpenCode /
Qoder / ZCode) and the in-app AI Assistant
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
  version = {2.5.0},
  year    = {2026},
  url     = {https://github.com/GISerDaiShaoqing/D3LTool},
}
```

## Changelog

- **2026-11 v2.5.0** — new **GLASS** data source: D3LTool now also searches &
  downloads the GLASS product suite — 130+ product × source × resolution
  variants served as plain HTML directory listings from the public
  [glass.hku.hk](https://glass.hku.hk) archive (no CMR, no Earthdata
  sign-in). A **GLASS** group joins the product catalog with the full
  variant registry (the five verified variants first: LAI/NDVI/EVI MODIS
  250m, FVC 500m, Ta daily); GLASS variant ids route to a new archive
  search that expands date ranges into composite DOY folders, reuses the
  same sinusoidal tile map / tile math, and intersects bboxes with the
  sinusoidal grid analytically (exact like the author's
  [glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools)
  R package; polar caps degrade to whole-row inclusion). Downloads ride the
  existing engine — public URLs need no login, so the GUI and
  `start_download` skip the Earthdata gate for all-GLASS batches — and the
  v2.4 export / browser-handoff surfaces work unchanged. Skeleton variants
  without a verified cadence get their year/DOY folders derived from the
  archive itself; layouts the registry skeleton cannot model (climatology
  roots, retired directories) fail with a clear message instead of a
  silently empty table. MCP/AI: the same 13 tools cover GLASS automatically
  (`list_products(group='GLASS')`, results capped at 80 rows), and the
  in-app agent system prompt mentions the no-sign-in route. The GLASS engine
  is ported from the author's R package
  [glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools/tree/v0.1.0)
  v0.1.0 ([docs](https://giserdaishaoqing.github.io/glass.sqdaitools/)) — the
  Python registry is generated from its dataset (`tools_gen_glass_registry.py`);
  compatibility D3L Tool 2.5.0 ↔ glass.sqdaitools ≥ 0.1.0 (API changes are
  announced in both release notes). Search & download live in D3LTool, the
  R package keeps post-processing (fill values / mosaic / crop / compositing) —
  see [GLASS support in 2.5.0](#glass-support-in-250); GLASS data are courtesy
  of the GLASS product team (glass.hku.hk), please follow their citation policy
- **2026-11 v2.4.0** — new **browser-assisted download** hand-off (the modern,
  dependency-free successor of v1.0's 2018 browser automation): the results
  table gains **Export download list** (a `.txt` of the checked granule URLs — one URL
  per line for `wget -i` / `aria2c -i` / download managers — plus a
  self-contained `.html` index page) and **Open in browser** (that index page
  in your default browser, where you can click files or batch-select them
  with a Download-It-All-style extension); the task table gains **Export
  failed links** (failed tasks only — the next search overwrites the results
  table, but failed URLs live on in the queue, so the rescue line survives
  across searches): files stuck on 401/403 get fetched by your browser's own
  Earthdata session instead. The results table also gained a one-click
  **"Clear results"** button. The same surface is exposed
  to MCP/AI via two new tools, `export_download_urls` and `open_download_page`
  (13 tools now; no Earthdata password ever enters chat or MCP — the browser
  session carries the login). The tile row also gained a one-click
  **"Clear tiles"** button (until now deselecting meant re-clicking each tile).
  The tile map's narrow rows now draw their cell grid at the band's own pitch —
  the old fixed 9px pitch spilled its lines past the band edge, leaving a comb
  of vertical stripes outside the globe (painted cells now match click zones)
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
- **2026-09 v2.0.0** — full rewrite: earthaccess/CMR search, tile map, resumable downloads,
  PySide6 bilingual UI, cross-platform
- **2018-04-27 v1.0** — first release (browser automation order downloads)

## Credits & License

- v1.0 (2018) created by Dai Shaoqing; v2.0 rewritten on top of
  [earthaccess](https://earthaccess.readthedocs.io/) / CMR
- GLASS data are produced by the GLASS product team
  ([glass.hku.hk](https://glass.hku.hk)) — please follow their citation
  policy; the GLASS module (v2.5) is ported from the author's
  [glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools) R package
- Released under the [MIT license](https://mit-license.org/)
- Questions? [Submit an issue](https://github.com/GISerDaiShaoqing/D3LTool/issues)
  or contact dsq1993qingge@163.com
