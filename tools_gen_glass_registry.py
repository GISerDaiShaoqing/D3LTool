# -*- coding: utf-8 -*-
"""Regenerate d3ltool/glass_registry.py from the glass.sqdaitools R package.

The R package (https://github.com/GISerDaiShaoqing/glass.sqdaitools) owns the
GLASS product registry: its data-raw/build_registry.R derives 130+ variants
(product x source x resolution) from a directory scan of glass.hku.hk, and
131 of 133 variants are verified against real granules (naming + cadence).
D3LTool only searches & downloads, so band metadata (fill/scale/valid range)
stays in the R package — this generator keeps the variant skeleton plus two
search/download-only fields derived from the verification log:

- ``ext``   — the data-file extension, taken from the log's real
  ``file_sample`` (AWGF is .tif, ABI_2km is .nc, TPSCE is .dat; hardcoding
  ``hdf`` would find zero files).  Falls back to ``hdf``.
- ``tiled`` — whether filenames carry ``h##v##`` sinusoidal tile fragments
  (global CMG products don't: tile filtering must not apply to them).
  Falls back to True for the seven variants absent from the log (the five
  originally verified MODIS products and two MODIS skeletons — all tiled).

Export the R dataset + verification log once, then run this script:

    Rscript -e "e <- new.env(); load('<pkg>/data/glass_products.rda', \
        envir=e); write.csv(e$glass_products, 'glass_products.csv', \
        row.names=FALSE, na='')"
    python tools_gen_glass_registry.py glass_products.csv \
        <pkg>/data-raw/verify_batch_log.csv
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "d3ltool" / "glass_registry.py"

# Columns kept for search/download (band metadata intentionally left to R).
KEEP = ("variant_id", "product", "long_name", "source", "res", "layout",
        "start_year", "end_year", "cadence_days", "temporal_res", "version",
        "code", "verified", "url_root")
_INT_COLS = ("start_year", "end_year", "cadence_days")

_TILE_RE = re.compile(r"h[0-9]{2}v[0-9]{2}", re.IGNORECASE)


def _verify_facts(log_path):
    """variant_id -> (ext, tiled) from the R package's verification log.

    Rows without a real file_sample (the skeletons) carry no fact and are
    skipped, so they fall through to the MODIS/VIIRS heuristic below."""
    facts = {}
    with Path(log_path).open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            sample = (row.get("file_sample") or "").strip()
            if not sample or "." not in sample:
                continue
            ext = sample.rsplit(".", 1)[-1].lower()
            facts[(row.get("variant_id") or "").strip()] = \
                (ext, bool(_TILE_RE.search(sample)))
    return facts


def _cell(col: str, raw: str):
    raw = (raw or "").strip()
    if col == "verified":
        return raw.upper() == "TRUE"
    if col in _INT_COLS:
        return int(float(raw)) if raw else None
    return raw or None


def main(argv: list) -> int:
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    src = Path(argv[1])
    facts = _verify_facts(argv[2]) if len(argv) == 3 else {}
    with src.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    # Keys are lowercased variant ids (is_glass_variant matches case-
    # insensitively); each dict keeps the canonical id in "variant_id".
    data = {}
    for row in rows:
        vid = (row.get("variant_id") or "").strip()
        if not vid:
            continue
        key = vid.lower()
        if key in data:
            raise SystemExit(f"duplicate variant id: {vid}")
        v = {col: _cell(col, row.get(col, "")) for col in KEEP}
        ext, tiled = facts.get(vid, (None, None))
        if ext is None:
            ext = "hdf"      # the five pre-log MODIS products are all .hdf
        if tiled is None:
            # no log row: the five originally verified MODIS products and
            # the two MODIS skeletons — all tiled families
            tiled = "MODIS" in vid.upper() or "VIIRS" in vid.upper()
        v["ext"] = ext
        v["tiled"] = bool(tiled)
        data[key] = v

    out = [
        "# -*- coding: utf-8 -*-",
        '"""GLASS product registry — generated data, do not edit by hand.',
        "",
        "Source: the glass.sqdaitools R package (same author), whose",
        "data-raw/build_registry.R derives the variants from a directory scan",
        "of https://glass.hku.hk/archive/ ; 131 of 133 variants carry",
        "verified naming/cadence metadata.  ``ext``/``tiled`` are derived",
        "from the package's data-raw/verify_batch_log.csv (real granule",
        "samples: AWGF is .tif, BBE is .hdf, TPSCE is .dat; global CMG",
        "products carry no h##v## tile fragment).",
        "Regenerate: python tools_gen_glass_registry.py <glass_products.csv>",
        "[<verify_batch_log.csv>]",
        "(that script has the Rscript export one-liner in its docstring).",
        "",
        "Band metadata (fill/scale/valid range) deliberately stays in the R",
        "package — D3LTool searches & downloads, the R package processes.",
        '"""',
        "",
        "VARIANTS = {",
    ]
    for key, v in data.items():
        out.append(f'    "{key}": {{')
        for col in KEEP + ("ext", "tiled"):
            val = v[col]
            if col == "verified":
                out.append(f'        "{col}": {val},')
            elif col == "tiled":
                out.append(f'        "{col}": {val},')
            elif val is None:
                out.append(f'        "{col}": None,')
            else:
                out.append(f'        "{col}": {val!r},')
        out.append("    },")
    out.append("}")
    out.append("")
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"{len(data)} variants -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
