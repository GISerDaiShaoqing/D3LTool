# -*- coding: utf-8 -*-
"""Regenerate d3ltool/glass_registry.py from the glass.sqdaitools R package.

The R package (https://github.com/GISerDaiShaoqing/glass.sqdaitools) owns the
GLASS product registry: its data-raw/build_registry.R derives 130+ variants
(product x source x resolution) from a directory scan of glass.hku.hk, and
five variants are verified against real granules (naming + cadence). D3LTool
only searches & downloads, so band metadata (fill/scale/valid range) stays in
the R package — this generator keeps the variant skeleton only.

Export the R dataset once, then run this script:

    Rscript -e "e <- new.env(); load('<pkg>/data/glass_products.rda', \
        envir=e); write.csv(e$glass_products, 'glass_products.csv', \
        row.names=FALSE, na='')"
    python tools_gen_glass_registry.py glass_products.csv
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "d3ltool" / "glass_registry.py"

# Columns kept for search/download (band metadata intentionally left to R).
KEEP = ("variant_id", "product", "long_name", "source", "res", "layout",
        "start_year", "end_year", "cadence_days", "temporal_res", "version",
        "code", "verified", "url_root")
_INT_COLS = ("start_year", "end_year", "cadence_days")


def _cell(col: str, raw: str):
    raw = (raw or "").strip()
    if col == "verified":
        return raw.upper() == "TRUE"
    if col in _INT_COLS:
        return int(float(raw)) if raw else None
    return raw or None


def main(argv: list) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    src = Path(argv[1])
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
        data[key] = {col: _cell(col, row.get(col, "")) for col in KEEP}

    out = [
        "# -*- coding: utf-8 -*-",
        '"""GLASS product registry — generated data, do not edit by hand.',
        "",
        "Source: the glass.sqdaitools R package (same author), whose",
        "data-raw/build_registry.R derives the variants from a directory scan",
        "of https://glass.hku.hk/archive/ ; five variants carry verified",
        "naming/cadence metadata, the rest are unverified skeletons.",
        "Regenerate: python tools_gen_glass_registry.py <glass_products.csv>",
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
        for col in KEEP:
            val = v[col]
            if col == "verified":
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
