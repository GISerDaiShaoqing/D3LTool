# -*- coding: utf-8 -*-
"""MCP stdio server entry for packaged builds (dist/D3LToolMCP.*).

Point MCP clients at this executable instead of `d3ltool-mcp` when using the
release binaries. The GUI build stays windowed; this one must keep console
stdout because the stdio transport writes protocol frames there.
"""

import sys

from d3ltool.mcp_server import run

if __name__ == "__main__":
    sys.exit(run())
