# -*- coding: utf-8 -*-
"""Shared fixtures: a local HTTP server that supports HEAD/GET + Range."""

import os

# Headless insurance: must be set before any test imports PySide6. Tests also
# set it per-test, but the default here keeps module-level imports safe on
# display-less CI runners even before fixtures run.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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


# NOTE (Qt teardown): deliberately NOT calling QApplication.quit()/shutdown()
# here. Under PySide6 6.12.0 on CI that teardown crashed the Qt test process
# (SIGSEGV on linux/mac, errors on windows) while 6.11.x is unaffected, and
# the original macOS suite crash was fixed by process isolation instead.

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
