# -*- coding: utf-8 -*-
"""Command line interface: login / search / download / gui.

With no arguments, launches the GUI.
"""

import argparse
import getpass
import sys

from . import __version__, auth, config, engine, search


def _setup_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _add_search_args(p):
    p.add_argument("short_name", help="CMR short name, e.g. VNP46A1 / MOD13Q1 / M2T1NXSLV")
    p.add_argument("--start", required=True, help="start date YYYY-MM-DD")
    p.add_argument("--end", required=True, help="end date YYYY-MM-DD")
    p.add_argument("--tile", action="append", default=[],
                   help="MODIS/VIIRS tile like h04v03 (repeatable)")
    p.add_argument("--bbox", nargs="+", default=[],
                   help="bounding box: west,south,east,north (for MERRA-2 etc.); "
                        "spaces or commas both fine, e.g. --bbox 100 20 120 40")
    p.add_argument("--version", default="", help="CMR version, e.g. 6.1 (optional)")
    p.add_argument("--limit", type=int, default=200, help="max granules (default 200)")


def _params_from_args(args):
    tiles = []
    for t in args.tile:
        tiles.extend(search.parse_tiles(t))
    return search.SearchParams(
        short_name=args.short_name,
        start=args.start,
        end=args.end,
        version=args.version,
        tiles=tiles,
        bbox=search.parse_bbox(" ".join(args.bbox)),
        max_results=args.limit,
    )


def _print_results(granules):
    if not granules:
        print("no granules found")
        return
    for g in granules:
        size = search.granule_size_mb(g)
        print(f"{search.granule_date(g)}  {search.granule_tile(g):8s} "
              f"{(f'{size:9.1f} MB' if size else '        -')}  {search.granule_filename(g)}")
    print(f"-- {len(granules)} granule(s)")


def _cmd_login(_args):
    username = input("Earthdata username: ").strip()
    password = getpass.getpass("Earthdata password: ")
    user = auth.login(username, password, persist=True)
    print(f"signed in as {user}; credentials persisted to ~/.netrc")
    return 0


def _cmd_search(args):
    granules = search.run_search(_params_from_args(args))
    _print_results(granules)
    return 0


def _cmd_download(args):
    if not auth.is_authenticated():
        if sys.stdin.isatty():
            print("not signed in; downloading requires Earthdata login")
            return _cmd_login(args)
        print("not signed in (no tty). Run `d3ltool login` first.", file=sys.stderr)
        return 2

    params = _params_from_args(args)
    granules = search.run_search(params)
    if not granules:
        print("no granules found")
        return 0

    cfg = config.load_config()
    dest = args.dest or cfg["download_dir"]
    workers = args.workers or int(cfg.get("max_workers", 3))

    def on_event(item, event, payload):
        if item is None:
            return
        if event == "status" and item.state in ("done", "skipped", "failed", "canceled"):
            mark = {"done": "OK ", "skipped": "SKIP", "failed": "FAIL",
                    "canceled": "CANC"}.get(item.state, "    ")
            print(f"[{mark}] {item.filename} {item.message}")
        elif event == "progress" and item.total:
            sys.stdout.write(f"\r  {item.filename}: {item.downloaded / 1048576:.1f}/"
                             f"{item.total / 1048576:.1f} MB  "
                             f"{item.speed / 1048576:.1f} MB/s   ")
            sys.stdout.flush()

    eng = engine.DownloadEngine(session_factory=auth.new_download_session,
                                dest_dir=dest, max_workers=workers,
                                on_event=on_event)
    print(f"downloading {len(granules)} granule(s) -> {dest} (workers={workers})")
    for g in granules:
        links = search.granule_links(g)
        if not links:
            print(f"[FAIL] {search.granule_filename(g)}: no download link")
            continue
        size_mb = search.granule_size_mb(g)
        eng.add(links[0], filename=search.granule_filename(g),
                size_hint=int(size_mb * 1048576) if size_mb else 0)
    eng.wait_all()
    print("done.")
    return 0


def _cmd_gui(_args):
    from .app import run_gui
    return run_gui()


def main(argv=None) -> int:
    _setup_stdout()
    parser = argparse.ArgumentParser(
        prog="d3ltool",
        description=f"D3L Tool of NASA Satellite v{__version__} — "
                    "search & download MODIS/VIIRS/MERRA-2 data. "
                    "Run without arguments to start the GUI.")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("gui", help="start the GUI").set_defaults(func=_cmd_gui)
    sub.add_parser("login", help="login to NASA Earthdata and persist ~/.netrc") \
       .set_defaults(func=_cmd_login)

    p_search = sub.add_parser("search", help="search granules, print the list")
    _add_search_args(p_search)
    p_search.set_defaults(func=_cmd_search)

    p_dl = sub.add_parser("download", help="search + download")
    _add_search_args(p_dl)
    p_dl.add_argument("--dest", default="", help="destination directory (default: settings)")
    p_dl.add_argument("--workers", type=int, default=0, help="concurrent downloads")
    p_dl.set_defaults(func=_cmd_download)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        return _cmd_gui(args)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
