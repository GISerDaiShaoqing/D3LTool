# -*- coding: utf-8 -*-
"""Bridge from DownloadEngine callbacks (worker threads) to Qt signals."""

from PySide6.QtCore import QObject, Signal


class EngineBridge(QObject):
    status = Signal(int)      # item id
    progress = Signal(int)    # item id
    cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = None

    def attach(self, engine) -> None:
        self.engine = engine
        engine.on_event = self._on_event

    def _on_event(self, item, event, payload):
        if item is None and event == "cleared":
            self.cleared.emit()
            return
        if item is None:
            return
        if event == "status":
            self.status.emit(item.id)
        elif event == "progress":
            self.progress.emit(item.id)
