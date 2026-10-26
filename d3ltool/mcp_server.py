# -*- coding: utf-8 -*-
"""MCP server exposing D3LTool capabilities over stdio.

Entry points: `d3ltool-mcp` (console script) or `python -m d3ltool.mcp_server`.
Point any MCP client (Claude Desktop, Cursor, ZCode, ...) at this process.
Requires the MCP SDK: pip install 'd3ltool[mcp]'.

Search works anonymously; downloads reuse the Earthdata sign-in persisted on
this machine, so no password ever flows through MCP messages.
"""

import sys

INSTRUCTIONS = (
    "D3L Tool of NASA Satellite: search & download NASA MODIS / VIIRS / "
    "MERRA-2 data from LAADS DAAC and GES DISC via CMR, plus point time "
    "series sampled straight over NASA OPeNDAP. Search works anonymously; "
    "downloads and point_timeseries reuse the Earthdata sign-in persisted "
    "on this machine (passwords are never accepted through tools). "
    "Routing: for 'time series / trend / plotting' requests call "
    "point_timeseries (inside the D3LTool desktop app follow with "
    "plot_timeseries to draw it; plain MCP clients chart the returned "
    "points themselves) — do NOT search or download granules for that. "
    "The flow check_auth -> list_products / point_to_tile -> "
    "search_granules -> start_download -> download_status is for file "
    "requests only."
)


def _build_server():
    from . import tools

    # mcp 1.x keeps the high-level server in fastmcp; 2.x renamed it MCPServer.
    # Signatures of (name, instructions), add_tool(fn, name, description) and
    # run("stdio") are the same, so one alias covers both. The [mcp] extra is
    # capped below 3 in pyproject to block a future breaking major release.
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        from mcp.server.mcpserver import MCPServer as FastMCP

    server = FastMCP("d3ltool", instructions=INSTRUCTIONS)
    for spec in tools.all_specs():
        server.add_tool(spec.fn, name=spec.name, description=spec.description)
    return server


def run() -> int:
    try:
        server = _build_server()
    except ImportError:
        print("The MCP SDK is not installed. Install it with:\n"
              "  pip install 'd3ltool[mcp]'\n"
              "then run `d3ltool-mcp` again.", file=sys.stderr)
        return 2
    server.run()        # stdio transport; blocks until the client disconnects
    return 0


if __name__ == "__main__":
    sys.exit(run())
