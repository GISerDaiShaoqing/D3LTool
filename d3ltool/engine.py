# -*- coding: utf-8 -*-
"""Thread-pool download engine: chunked transfer, Range resume, retry.

Pure Python (no Qt). The GUI/CLI wrap it and render the callbacks.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

import requests

CHUNK_SIZE = 256 * 1024
MAX_ATTEMPTS = 4

STATES = ("pending", "running", "done", "skipped", "failed", "paused", "canceled")


class _Paused(Exception):
    pass


class _Canceled(Exception):
    pass


@dataclass
class DownloadItem:
    url: str
    filename: str
    dest_dir: Path
    id: int = 0
    state: str = "pending"
    total: int = 0            # bytes, 0 = unknown
    downloaded: int = 0
    speed: float = 0.0        # bytes/sec
    message: str = ""


def filename_from_url(url: str) -> str:
    base = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    name = unquote(base) if base else ""
    return name or f"granule_{abs(hash(url)) % 10**8}.bin"


class DownloadEngine:
    def __init__(self, session_factory, dest_dir, max_workers=3, on_event=None):
        self.session_factory = session_factory
        self.dest_dir = Path(dest_dir)
        self.max_workers = max(1, int(max_workers))
        self.on_event = on_event or (lambda item, event, payload: None)
        self.items = {}
        self._next_id = 1
        self._pool = None
        self._futures = {}
        self._control = {}
        self._known_paths = set()
        self._lock = threading.Lock()
        self._session = None
        self._session_lock = threading.Lock()

    # ------------------------------------------------------------------ public

    def add(self, url, filename=None, size_hint=0) -> DownloadItem:
        filename = filename or filename_from_url(url)
        dest = self.dest_dir / filename
        with self._lock:
            if dest in self._known_paths:
                for it in self.items.values():
                    if self.dest_dir / it.filename == dest:
                        return it
            item = DownloadItem(url=url, filename=filename, dest_dir=self.dest_dir,
                                id=self._next_id, total=int(size_hint or 0))
            self._next_id += 1
            self.items[item.id] = item
            self._known_paths.add(dest)
            self._control[item.id] = {"pause": False, "cancel": False}
        self._set_state(item, "pending", "")
        self._ensure_pool()
        self._futures[item.id] = self._pool.submit(self._run, item)
        return item

    def pause(self, item_id) -> None:
        ctrl = self._control.get(item_id)
        if ctrl:
            ctrl["pause"] = True

    def cancel(self, item_id) -> None:
        ctrl = self._control.get(item_id)
        if ctrl:
            ctrl["cancel"] = True
            ctrl["pause"] = True

    def resume(self, item_id) -> None:
        """Resume a paused/failed/canceled item; Range continues from .part file."""
        item = self.items.get(item_id)
        if item is None:
            return
        with self._lock:
            if item.state not in ("paused", "failed", "canceled"):
                return
            self._control[item_id] = {"pause": False, "cancel": False}
            item.state = "pending"
            item.message = ""
        self._emit(item, "status", {})
        self._ensure_pool()
        self._futures[item.id] = self._pool.submit(self._run, item)

    retry = resume

    def clear_finished(self) -> None:
        with self._lock:
            finished = [i for i, it in list(self.items.items())
                        if it.state in ("done", "skipped", "failed", "canceled")]
            for i in finished:
                it = self.items.pop(i)
                self._control.pop(i, None)
                self._futures.pop(i, None)
                self._known_paths.discard(self.dest_dir / it.filename)
        if finished:
            self.on_event(None, "cleared", {})

    def wait_all(self, timeout=None) -> bool:
        import concurrent.futures

        futures = list(self._futures.values())
        if not futures:
            return True
        try:
            concurrent.futures.wait(futures, timeout=timeout)
            return all(f.done() for f in futures)
        except Exception:
            return False

    # ----------------------------------------------------------------- internal

    def _get_session(self):
        with self._session_lock:
            if self._session is None:
                self._session = self.session_factory()
            return self._session

    def _ensure_pool(self):
        with self._lock:
            if self._pool is None:
                self._pool = ThreadPoolExecutor(max_workers=self.max_workers,
                                                thread_name_prefix="d3ldl")

    def _emit(self, item, event, payload):
        try:
            self.on_event(item, event, payload)
        except Exception:
            pass

    def _set_state(self, item, state, message):
        item.state = state
        item.message = message
        if state in ("done", "skipped", "paused", "canceled", "failed"):
            item.speed = 0.0
        self._emit(item, "status", {})

    def _run(self, item):
        ctrl = self._control[item.id]
        attempt = 0
        while True:
            if ctrl["cancel"]:
                self._set_state(item, "canceled", "")
                return
            try:
                self._download_one(item, ctrl)
                return
            except _Paused:
                self._set_state(item, "paused", "")
                return
            except _Canceled:
                self._set_state(item, "canceled", "")
                return
            except Exception as exc:
                attempt += 1
                if attempt >= MAX_ATTEMPTS:
                    self._set_state(item, "failed", f"{type(exc).__name__}: {exc}")
                    return
                self._set_state(item, "running", f"retry {attempt}/{MAX_ATTEMPTS - 1}: {exc}")
                for _ in range(3 * attempt):   # 3s, 6s, 9s backoff
                    if ctrl["cancel"]:
                        self._set_state(item, "canceled", "")
                        return
                    time.sleep(1)

    def _download_one(self, item, ctrl):
        session = self._get_session()
        dest = item.dest_dir / item.filename
        item.dest_dir.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")

        remote_size = 0
        try:
            head = session.head(item.url, timeout=(20, 40), allow_redirects=True)
            if head.ok:
                remote_size = int(head.headers.get("Content-Length") or 0)
        except requests.RequestException:
            pass
        if not remote_size and item.total:
            remote_size = int(item.total)
        item.total = remote_size

        if dest.exists():
            local = dest.stat().st_size
            if (remote_size and local == remote_size) or (not remote_size and local > 0):
                self._set_state(item, "skipped", "exists")
                return
            dest.unlink()   # incomplete or corrupt: start over

        offset = part.stat().st_size if part.exists() else 0
        if remote_size and offset > remote_size:
            offset = 0
            part.unlink(missing_ok=True)
        elif remote_size and offset == remote_size:
            part.rename(dest)
            self._set_state(item, "done", "")
            return

        headers = {"Range": f"bytes={offset}-"} if offset else {}
        item.downloaded = offset
        with session.get(item.url, stream=True, timeout=(30, 60),
                         headers=headers, allow_redirects=True) as resp:
            if resp.status_code == 416:
                if remote_size and offset == remote_size:
                    part.rename(dest)
                    self._set_state(item, "done", "")
                    return
                part.unlink(missing_ok=True)
                raise RuntimeError("HTTP 416 (range not satisfiable)")
            resp.raise_for_status()
            mode = "ab"
            if resp.status_code == 200 and offset:
                offset = 0            # server ignored Range: restart
                item.downloaded = 0
                mode = "wb"
            elif resp.status_code == 200:
                mode = "wb"
            if not remote_size:
                cl = resp.headers.get("Content-Length")
                if cl:
                    remote_size = item.total = int(cl)

            self._set_state(item, "running", "")
            last_t = time.time()
            last_b = item.downloaded
            with open(part, mode) as fh:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if ctrl["cancel"]:
                        raise _Canceled()
                    if ctrl["pause"]:
                        raise _Paused()
                    if not chunk:
                        continue
                    fh.write(chunk)
                    item.downloaded += len(chunk)
                    now = time.time()
                    if now - last_t >= 0.4:
                        item.speed = (item.downloaded - last_b) / (now - last_t)
                        last_t, last_b = now, item.downloaded
                        self._emit(item, "progress", {})

        if remote_size and item.downloaded != remote_size:
            raise RuntimeError(f"size mismatch: got {item.downloaded}, want {remote_size}")
        part.rename(dest)
        item.speed = 0.0
        self._set_state(item, "done", "")
