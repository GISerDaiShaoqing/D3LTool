<!--
JOSS submission draft (target: Journal of Open Source Software, https://joss.theoj.org/)
Notes for the author (delete before submitting):
- Submission is via OpenReview (https://openreview.net). JOSS papers are short
  (250-1000 words of prose) and do NOT describe research results — they describe
  the software itself.
- Fill in your affiliation in the authors line; ORCID 0000-0003-0858-4728 is already
  in CITATION.cff. After the first GitHub release linked to Zenodo, replace the
  DOI placeholder in the header below with the real version DOI and set the
  repository link in OpenReview metadata.
-->

---
title: "D3L Tool of NASA Satellite: a bilingual GUI for searching and downloading NASA MODIS/VIIRS/MERRA-2 data"
tags:
  - remote sensing
  - MODIS
  - VIIRS
  - MERRA-2
  - Earthdata
  - data download
  - Python
authors:
  - name: Shaoqing Dai
    orcid: 0000-0003-0858-4728
    affiliations:
      - "Independent researcher; https://gisersqdai.top/"
date: 16 September 2026
DOI: 10.5281/zenodo.XXXXXXX   <!-- paste the Zenodo DOI of the archived release -->
---

# Summary

Remote-sensing practitioners who do not write Python still need MODIS, VIIRS and
MERRA-2 data, and the network conditions they work in are often not ideal. NASA's
official pathways — the LAADS DAAC website (manual orders or click-by-click
archive browsing), `wget`/`curl` with bearer tokens, or the `earthaccess` Python
library — all assume a certain degree of technical familiarity. D3L Tool of NASA
Satellite ("D3LTool") closes this gap with a bilingual (Chinese/English) desktop
application in which the complete workflow — authentication, product discovery,
selection and download — happens inside one window. It is a full rewrite of the
author's 2018 tool[@dai2018d3l], which automated order downloads through browser
automation and was itself an early answer to the closure of the LAADS FTP servers.

# Statement of need

D3LTool's users are remote-sensing practitioners, students and researchers who
need production-ready Earth observation files but do not maintain a Python
environment, plus any user whose network makes large NASA downloads slow or
unreliable (a very common situation for users in China, which the bilingual
interface targets explicitly). Existing options have specific gaps: the LAADS
website requires manually creating orders or browsing archives;
command-line scripts have no graphical feedback; and `earthaccess` — which
D3LTool builds on — is a script-oriented library with notebook-style progress
handling, no pause/resume control, no tile-map discovery, and no interface in
Chinese. D3LTool fills this niche by providing a single GUI application with:

- **built-in search** by product, date range, sinusoidal tile (a clickable 36×18
  MODIS/VIIRS tile map, text tile ids such as `h04v03`, or a lat/lon bounding
  box for MERRA-2-style data), with a browsable bilingual product catalog that
  frees non-experts from memorising CMR short names;
- **a robust download queue** built on the authenticated `earthaccess`
  session: parallel workers, chunked transfer with per-file progress, HTTP
  `Range` resumption of interrupted transfers, exponential-backoff retries,
  and file-size validation;
- **local credential persistence** in the conventional `~/.netrc` file, silent
  session restore at startup, and configurable proxy support;
- **a CLI** (`d3ltool search/download/login`) sharing the same core library as
  the GUI, so scripted pipelines and the GUI stay in feature parity.

# Software description

D3LTool is a Python package (`d3ltool`, Python ≥ 3.10) distributed via PyPI
installation from source and as standalone builds (Windows exe, macOS .app,
Linux binary) produced by a GitHub Actions matrix build on tagged releases.
It builds on PySide6 [@pyside6] for the interface and on `earthaccess`
[@earthaccess] for Earthdata authentication and CMR search, and is released
under the MIT licence.

The package separates concerns into a GUI-independent core and a thin GUI layer:
`search.py` wraps CMR granule search (temporal, tile-name patterns via
`readable_granule_name`, bounding-box filters, and a client-side tile filter
fallback) over `earthaccess.search_data`; `engine.py` is a pure-Python,
Qt-free download engine providing a thread pool, chunked HTTP transfer,
`Range`-based resume with `.part` files, retry with backoff, and event
callbacks that a thin Qt bridge forwards to the UI; `auth.py` wraps
`earthaccess` login (handling strategy/API differences across library
versions), persists credentials to the platform netrc file, and restores
sessions at startup; `tiles.py` implements the MODIS sinusoidal tile grid
arithmetic; `products.py` holds a curated, bilingual product catalogue.
The GUI (`d3ltool.gui`) is a PySide6 application: a search panel with the
tile map, results and task tables, settings (download directory, worker
count, proxy) and a language switcher; all strings live in a single i18n
module. The test suite (41 pytest tests at submission time) covers the tile
math, configuration handling, search query construction and version
fallbacks, the resume/retry engine against a local Range-capable HTTP
server, GUI smoke tests and login diagnostics.

# Acknowledgements

We thank the NASA EOSDIS community for `earthaccess` and the Common Metadata
Repository, and Tristan Quaife and MorvanZhou whose 2018-era code and
tutorials informed v1.0 of this tool.

# References

1. earthaccess: NASA Earthdata access library.
   <https://earthaccess.readthedocs.io/>
2. Common Metadata Repository (CMR) search API.
   <https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html>
3. LAADS DAAC, NASA: MODIS and VIIRS data products.
   <https://ladsweb.modaps.eosdis.nasa.gov/>
4. GES DISC: MERRA-2 data products.
   <https://disc.gsfc.nasa.gov/datasets?project=MERRA-2>
5. PySide6 (Qt for Python).
   <https://doc.qt.io/qtforpython/>
