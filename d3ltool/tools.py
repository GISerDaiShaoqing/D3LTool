# -*- coding: utf-8 -*-
"""Shared tool registry for the MCP server and the in-app AI agent.

Every tool is a plain function with type hints that returns a JSON-friendly
dict. JSON schemas are derived from the signatures, so the MCP surface and
OpenAI-style function calling always describe the same thing.

Credentials are never a tool parameter: download-capable tools reuse the
sign-in persisted on this machine (GUI login / `d3ltool login`), so no
password ever flows through chat or MCP messages.
"""

import inspect
import threading
import types
import typing
from pathlib import Path

from . import auth, config, engine, products, search
from .tiles import lonlat_to_tile, parse_tile, tile_bounds_lonlat, tile_name

# ---------------------------------------------------------------- registry


class ToolSpec:
    def __init__(self, name, fn, description, description_zh):
        self.name = name
        self.fn = fn
        self.description = description          # English, read by models
        self.description_zh = description_zh    # shown in the GUI/docs
        self.parameters = _schema_from_signature(fn)


REGISTRY = {}          # name -> ToolSpec, insertion order = display order


def tool(name, description, description_zh=""):
    def deco(fn):
        REGISTRY[name] = ToolSpec(name, fn, description, description_zh)
        return fn
    return deco


def all_specs():
    return list(REGISTRY.values())


def get_spec(name):
    return REGISTRY.get(name)


def openai_tool_specs():
    """Tools in OpenAI function-calling format (used by the in-app agent)."""
    out = []
    for s in REGISTRY.values():
        out.append({
            "type": "function",
            "function": {
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters,
            },
        })
    return out


_PRIMITIVES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def _type_schema(hint):
    if hint is list or hint is dict:
        return {"type": "array" if hint is list else "object"}
    if isinstance(hint, types.UnionType) or typing.get_origin(hint) is typing.Union:
        args = [a for a in typing.get_args(hint) if a is not type(None)]
        hint = args[0] if args else str
    origin = typing.get_origin(hint)
    if origin in (list, tuple):
        args = typing.get_args(hint)
        if args:
            return {"type": "array", "items": _type_schema(args[0])}
        return {"type": "array"}
    if origin in (set, frozenset):
        return {"type": "array"}
    if hint in _PRIMITIVES:
        return {"type": _PRIMITIVES[hint]}
    return {"type": "string"}


def _schema_from_signature(fn):
    """JSON Schema object built from fn's type hints (matching the MCP schema
    that FastMCP derives from the very same signatures)."""
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        hints = {}
    properties, required = {}, []
    for name, param in inspect.signature(fn).parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        prop = _type_schema(hints.get(name, str))
        if param.default is not inspect.Parameter.empty:
            if param.default != "" and param.default is not None \
                    and not isinstance(param.default, (list, tuple)):
                prop["default"] = param.default
            properties[name] = prop
        else:
            required.append(name)
            properties[name] = prop
    return {"type": "object", "properties": properties, "required": required}


# ------------------------------------------------------- engine singleton

_SESSION_FACTORY = auth.new_download_session   # replaced by tests
_SEARCHER = None                               # replaced by tests; None -> earthaccess
_ENGINE = None
_ENGINE_LOCK = threading.Lock()


def _get_engine(dest_dir=""):
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            cfg = config.load_config()
            _ENGINE = engine.DownloadEngine(
                session_factory=_SESSION_FACTORY,
                dest_dir=dest_dir or cfg.get("download_dir") or str(Path.home() / "Downloads"),
                max_workers=int(cfg.get("max_workers", 3)),
            )
        elif dest_dir:
            _ENGINE.dest_dir = Path(dest_dir)
        return _ENGINE


def _reset_engine():
    global _ENGINE
    with _ENGINE_LOCK:
        _ENGINE = None


def attach_engine(engine_obj) -> None:
    """Let the GUI inject its engine so agent-driven downloads surface in the
    task table (bridge already wired). MCP servers keep their own singleton."""
    global _ENGINE
    with _ENGINE_LOCK:
        _ENGINE = engine_obj


# ----------------------------------------------------------------- tools

@tool(
    "check_auth",
    "Check whether this machine is signed in to NASA Earthdata. Search works "
    "anonymously; downloads require a prior sign-in on this machine (GUI login "
    "or `d3ltool login`). Passwords are never accepted through chat tools.",
    "查询本机 Earthdata 登录状态（检索无需登录，下载需要先在 GUI 或 d3ltool login 登录）",
)
def check_auth() -> dict:
    signed_in = auth.is_authenticated()
    return {
        "authenticated": signed_in,
        "user": auth.current_user() if signed_in else "",
        "hint": "" if signed_in else
        "not signed in: searching works, downloads do not; "
        "sign in once in the D3LTool GUI or run `d3ltool login` (interactive)",
    }


@tool(
    "list_products",
    "List the curated product catalog: MODIS Terra/Aqua/Combined, VIIRS "
    "(incl. nighttime lights) and MERRA-2, with short_name, version hint and "
    "a short description. `group` filters by substring (e.g. 'VIIRS', 'MODIS', 'MERRA').",
    "列出内置产品目录（按组筛选，含 short_name/版本/说明）",
)
def list_products(group: str = "") -> dict:
    needle = (group or "").strip().lower()
    out = []
    for gname, items in products.GROUPS:
        if needle and needle not in gname.lower():
            continue
        for short_name, version, desc_zh, desc_en in items:
            out.append({
                "group": gname,
                "short_name": short_name,
                "version": version,
                "description_zh": desc_zh,
                "description_en": desc_en,
            })
    return {"count": len(out), "products": out}


@tool(
    "point_to_tile",
    "Given longitude/latitude in degrees, return the MODIS/VIIRS sinusoidal "
    "tile (h,v) that contains the point, plus its geographic bounds.",
    "经纬度 -> 所在的 MODIS/VIIRS 正弦瓦片及范围",
)
def point_to_tile(lon: float, lat: float) -> dict:
    h, v = lonlat_to_tile(lon, lat)
    west, south, east, north = tile_bounds_lonlat(h, v)
    return {
        "tile": tile_name(h, v),
        "h": h,
        "v": v,
        "bounds": {"west": west, "south": south, "east": east, "north": north},
    }


@tool(
    "tile_bounds",
    "Geographic bounds (degrees) of a MODIS/VIIRS sinusoidal tile. "
    "h is the column (0-35, west->east from 180W), v is the row (0-17, north->south from 90N).",
    "给定 h/v 返回瓦片地理范围（网格 36x18）",
)
def tile_bounds(h: int, v: int) -> dict:
    west, south, east, north = tile_bounds_lonlat(int(h), int(v))
    return {
        "tile": tile_name(int(h), int(v)),
        "bounds": {"west": west, "south": south, "east": east, "north": north},
    }


@tool(
    "search_granules",
    "Search CMR for data granules of one product by short_name and time range "
    "(YYYY-MM-DD, inclusive). tiles (e.g. 'h04v03') filter MODIS/VIIRS "
    "sinusoidal products only; bbox (west,south,east,north degrees) suits "
    "MERRA-2 and global products. Returns each granule's filename, date, tile, "
    "size and HTTPS download URL. Anonymous access is allowed.",
    "按产品与时间检索 granule（可按瓦片/范围过滤），返回文件名、日期、大小与下载地址",
)
def search_granules(short_name: str, start: str, end: str, version: str = "",
                    tiles: list = None, bbox: list = None, limit: int = 10) -> dict:
    tile_names = []
    for t in (tiles or []):
        h, v = parse_tile(str(t).strip().lower())
        tile_names.append(tile_name(h, v))
    box = tuple(float(x) for x in bbox) if bbox else None
    if box and not (-180 <= box[0] < box[2] <= 180 and -90 <= box[1] < box[3] <= 90):
        raise ValueError("bbox must satisfy west<east, south<north in degrees")

    params = search.SearchParams(
        short_name=short_name,
        start=start,
        end=end,
        version=version or "",
        tiles=tile_names,
        bbox=box,
        max_results=max(1, min(int(limit or 10), 200)),
    )
    granules = search.run_search(params, searcher=_SEARCHER)
    out = []
    for g in granules[:params.max_results]:
        links = search.granule_links(g)
        out.append({
            "filename": search.granule_filename(g),
            "date": search.granule_date(g),
            "tile": search.granule_tile(g),
            "size_mb": search.granule_size_mb(g),
            "url": links[0] if links else "",
        })
    return {"count": len(out), "granules": out}


@tool(
    "start_download",
    "Queue HTTPS file URLs (as returned by search_granules) for download with "
    "resume support. Requires a previous Earthdata sign-in on this machine. "
    "Returns immediately with task ids; poll download_status for progress. "
    "dest = target folder (default: the app's configured download folder).",
    "把文件 URL 加入下载队列（支持断点续传），立即返回任务 id；用 download_status 查询进度",
)
def start_download(urls: list, dest: str = "") -> dict:
    urls = [str(u).strip() for u in (urls or []) if str(u).strip()]
    if not urls:
        return {"error": "no urls given"}
    if not auth.is_authenticated():
        return {
            "error": "not_authenticated",
            "hint": "downloads need Earthdata sign-in; the user must sign in "
                    "once in the D3LTool GUI or run `d3ltool login` first",
        }
    eng = _get_engine(dest)
    items = []
    for url in urls:
        it = eng.add(url)
        items.append({"id": it.id, "filename": it.filename})
    return {"dest": str(eng.dest_dir), "count": len(items), "items": items}


@tool(
    "download_status",
    "Current state of download tasks started in this session: per file the "
    "state (pending/running/done/skipped/failed/paused/canceled), progress in "
    "MB and speed. Poll this after start_download until all files are done.",
    "查询下载任务进度（状态/大小/速度/失败原因）",
)
def download_status() -> dict:
    eng = _peek_engine()
    items = []
    if eng is not None:
        for it in list(eng.items.values()):
            items.append({
                "id": it.id,
                "filename": it.filename,
                "state": it.state,
                "downloaded_mb": round(it.downloaded / 1048576, 1),
                "total_mb": round(it.total / 1048576, 1),
                "speed_mbs": round(it.speed / 1048576, 1),
                "message": it.message,
            })
    return {"count": len(items), "items": items}


def _peek_engine():
    return _ENGINE


@tool(
    "cancel_download",
    "Cancel a queued or running download task by its id (from start_download/download_status).",
    "按 id 取消下载任务",
)
def cancel_download(id: int) -> dict:
    eng = _peek_engine()
    if eng is None or int(id) not in eng.items:
        return {"error": f"unknown task id: {id}"}
    eng.cancel(int(id))
    return {"ok": True, "id": int(id)}


@tool(
    "retry_download",
    "Retry a failed/paused/canceled download task by its id; Range resume "
    "continues from the partial file.",
    "按 id 重试/继续下载任务（断点续传）",
)
def retry_download(id: int) -> dict:
    eng = _peek_engine()
    if eng is None or int(id) not in eng.items:
        return {"error": f"unknown task id: {id}"}
    eng.retry(int(id))
    return {"ok": True, "id": int(id)}
