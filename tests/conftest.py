# -*- coding: utf-8 -*-
"""Shared fixtures: a local HTTP server that supports HEAD/GET + Range."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _RangeHandler(BaseHTTPRequestHandler):
    payload = b""       # set per test via start_range_server
    log_message = lambda self, *a, **k: None

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()

    def do_GET(self):
        total = len(self.payload)
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            try:
                start = int(rng.split("=", 1)[1].split("-", 1)[0])
            except ValueError:
                start = 0
            if start >= total:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{total}")
                self.end_headers()
                return
            body = self.payload[start:]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{total - 1}/{total}")
        else:
            body = self.payload
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def range_server():
    """Start a local server serving `payload`; yields the base URL."""
    holder = {}

    def _start(payload: bytes) -> str:
        _RangeHandler.payload = payload
        server = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
        holder["server"] = server
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return f"http://127.0.0.1:{server.server_address[1]}/file.bin"

    yield _start
    if "server" in holder:
        holder["server"].shutdown()
        holder["server"].server_close()
