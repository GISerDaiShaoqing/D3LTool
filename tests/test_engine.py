# -*- coding: utf-8 -*-
"""Download engine tests against a local Range-capable HTTP server."""

import time

import pytest
import requests

from d3ltool.engine import DownloadEngine

PAYLOAD = bytes(range(256)) * 4096     # 1 MiB deterministic body


def _make_engine(dest_dir, events, max_workers=1):
    def on_event(item, event, payload):
        events.append((event, item.state, item.id) if item is not None else (event, None, None))

    return DownloadEngine(
        session_factory=requests.Session,
        dest_dir=dest_dir,
        max_workers=max_workers,
        on_event=on_event,
    )


def _wait_state(item, states, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if item.state in states:
            return item.state
        time.sleep(0.02)
    raise AssertionError(f"timeout waiting for {states}, last={item.state} ({item.message})")


def test_fresh_download(tmp_path, range_server):
    url = range_server(PAYLOAD)
    events = []
    eng = _make_engine(tmp_path, events)
    item = eng.add(url, filename="a.bin")
    assert _wait_state(item, {"done"}) == "done"
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD
    assert not (tmp_path / "a.bin.part").exists()


def test_resume_from_partial(tmp_path, range_server):
    url = range_server(PAYLOAD)
    events = []
    eng = _make_engine(tmp_path, events)
    part = tmp_path / "b.bin.part"
    cut = 400 * 1024
    part.write_bytes(PAYLOAD[:cut])

    item = eng.add(url, filename="b.bin")
    assert _wait_state(item, {"done"}) == "done"
    assert (tmp_path / "b.bin").read_bytes() == PAYLOAD


def test_skip_existing_complete_file(tmp_path, range_server):
    url = range_server(PAYLOAD)
    events = []
    eng = _make_engine(tmp_path, events)
    (tmp_path / "c.bin").write_bytes(PAYLOAD)

    item = eng.add(url, filename="c.bin")
    assert _wait_state(item, {"skipped"}) == "skipped"
    assert (tmp_path / "c.bin").read_bytes() == PAYLOAD


def test_corrupt_file_redownloaded(tmp_path, range_server):
    url = range_server(PAYLOAD)
    events = []
    eng = _make_engine(tmp_path, events)
    (tmp_path / "d.bin").write_bytes(PAYLOAD[:123])   # wrong size

    item = eng.add(url, filename="d.bin")
    assert _wait_state(item, {"done"}) == "done"
    assert (tmp_path / "d.bin").read_bytes() == PAYLOAD


def test_duplicate_add_returns_same_item(tmp_path, range_server):
    url = range_server(PAYLOAD)
    events = []
    eng = _make_engine(tmp_path, events)
    it1 = eng.add(url, filename="e.bin")
    it2 = eng.add(url, filename="e.bin")
    assert it1 is it2
    _wait_state(it1, {"done"})


def test_failed_download_marks_failed(tmp_path):
    # nothing listens on port 1: connection refused -> retries -> failed
    events = []
    eng = _make_engine(tmp_path, events)
    bad_url = "http://127.0.0.1:1/file.bin"
    item = eng.add(bad_url, filename="f.bin")
    # with retries + backoff this takes a few seconds; states may include running
    assert _wait_state(item, {"failed"}, timeout=60) == "failed"


def test_clear_finished(tmp_path, range_server):
    url = range_server(PAYLOAD)
    events = []
    eng = _make_engine(tmp_path, events)
    item = eng.add(url, filename="g.bin")
    _wait_state(item, {"done"})
    eng.clear_finished()
    assert item.id not in eng.items
    # re-adding the same name after clear creates a NEW item (skipped quickly)
    item2 = eng.add(url, filename="g.bin")
    assert item2.id != item.id
    assert _wait_state(item2, {"skipped"}) == "skipped"
