# -*- coding: utf-8 -*-
"""MCP server tests: registration surface + real stdio round trip.

The stdio smoke test launches `python -m d3ltool.mcp_server` as a subprocess
and exchanges JSON-RPC messages over pipes, exactly like an MCP client does.
Network-free; needs the `mcp` package (dev extra).
"""

import json
import queue
import subprocess
import sys
import threading

import pytest

import d3ltool.tools as tools

EXPECTED_TOOLS = sorted(tools.REGISTRY)


def test_mcp_server_registers_all_tools():
    pytest.importorskip("mcp")
    from d3ltool import mcp_server

    server = mcp_server._build_server()
    tm = getattr(server, "_tool_manager", None)
    if tm is None:
        pytest.skip("SDK internal tool manager moved")
    names = sorted(t.name for t in tm.list_tools())
    assert names == EXPECTED_TOOLS


def test_mcp_missing_sdk_exit_code(monkeypatch):
    from d3ltool import mcp_server

    def _no_sdk():
        raise ImportError("No module named 'mcp'")

    monkeypatch.setattr(mcp_server, "_build_server", _no_sdk)
    assert mcp_server.run() == 2


def test_mcp_stdio_roundtrip(tmp_path):
    pytest.importorskip("mcp")
    env_cmd = [sys.executable, "-m", "d3ltool.mcp_server"]
    try:
        proc = subprocess.Popen(env_cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8")
    except OSError:
        pytest.skip("cannot spawn subprocess")
    assert proc.stdin and proc.stdout

    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(l) for l in proc.stdout],
                     daemon=True).start()

    def send(msg):
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def recv(timeout=30):
        return json.loads(lines.get(timeout=timeout))

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "d3ltool-test", "version": "0"}}})
        init = recv()
        assert init["result"]["serverInfo"]["name"] == "d3ltool"

        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = recv()
        names = sorted(t["name"] for t in listed["result"]["tools"])
        assert names == EXPECTED_TOOLS

        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "list_products", "arguments": {"group": "VIIRS"}}})
        call = recv()
        payload = json.loads(call["result"]["content"][0]["text"])
        assert payload["count"] == 4
        assert payload["products"][0]["group"] == "VIIRS"
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.terminate()
        proc.wait(timeout=15)
