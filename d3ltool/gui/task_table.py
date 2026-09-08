# -*- coding: utf-8 -*-
"""Download task table: per-file progress, pause/resume/retry."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QHBoxLayout, QMessageBox, QProgressBar,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .. import i18n

COL_FILE, COL_STATE, COL_PROGRESS, COL_SPEED, COL_SIZE = range(5)

STATE_COLORS = {
    "done": "#1e7e34",
    "skipped": "#6c757d",
    "failed": "#c0392b",
    "paused": "#e67e22",
    "canceled": "#6c757d",
    "running": "#1e6fd2",
    "pending": "#444444",
}


def _fmt_bytes(n) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


class TaskTable(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._rows = {}       # item_id -> row index

        layout = QVBoxLayout(self)
        btn_row = QHBoxLayout()
        self.pause_btn = QPushButton(i18n.tr("btn_pause"))
        self.resume_btn = QPushButton(i18n.tr("btn_resume"))
        self.retry_btn = QPushButton(i18n.tr("btn_retry"))
        self.clear_btn = QPushButton(i18n.tr("btn_clear_done"))
        self.open_btn = QPushButton(i18n.tr("btn_open_dir"))
        for b in (self.pause_btn, self.resume_btn, self.retry_btn):
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.open_btn)
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            i18n.tr("tasks_col_file"),
            i18n.tr("tasks_col_state"),
            i18n.tr("tasks_col_progress"),
            i18n.tr("tasks_col_speed"),
            i18n.tr("tasks_col_size"),
        ])
        self.table.setColumnWidth(COL_STATE, 110)
        self.table.setColumnWidth(COL_PROGRESS, 160)
        self.table.setColumnWidth(COL_SPEED, 90)
        self.table.setColumnWidth(COL_SIZE, 130)
        from PySide6.QtWidgets import QHeaderView
        self.table.horizontalHeader().setSectionResizeMode(COL_FILE, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.pause_btn.clicked.connect(lambda: self._act("pause"))
        self.resume_btn.clicked.connect(lambda: self._act("resume"))
        self.retry_btn.clicked.connect(lambda: self._act("retry"))
        self.clear_btn.clicked.connect(self._clear_done)
        self.open_btn.clicked.connect(self._open_dir)

    # ------------------------------------------------------------------ public

    def set_engine(self, engine) -> None:
        self.engine = engine

    def on_status(self, item_id: int) -> None:
        item = self.engine.items.get(item_id) if self.engine else None
        if item is None:
            return
        row = self._rows.get(item_id)
        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._rows[item_id] = row
            self.table.setItem(row, COL_FILE, QTableWidgetItem(item.filename))
            state_item = QTableWidgetItem("")
            self.table.setItem(row, COL_STATE, state_item)
            bar = QProgressBar()
            bar.setValue(0)
            self.table.setCellWidget(row, COL_PROGRESS, bar)
            self.table.setItem(row, COL_SPEED, QTableWidgetItem("-"))
            self.table.setItem(row, COL_SIZE, QTableWidgetItem("-"))

        state_item = self.table.item(row, COL_STATE)
        state_item.setText(i18n.tr(f"state_{item.state}"))
        state_item.setForeground(Qt.GlobalColor.white if item.state in ("done", "failed") else Qt.GlobalColor.black)
        color = STATE_COLORS.get(item.state, "#444444")
        from PySide6.QtGui import QColor
        state_item.setForeground(QColor(color))
        if item.message and item.state in ("failed", "running"):
            state_item.setToolTip(item.message)

        bar = self.table.cellWidget(row, COL_PROGRESS)
        if item.state == "running" and not item.total:
            bar.setRange(0, 0)                     # busy indicator
        else:
            bar.setRange(0, 100)
            if item.total:
                bar.setValue(int(item.downloaded * 100 / item.total))
            elif item.state in ("done", "skipped"):
                bar.setValue(100)
            else:
                bar.setValue(0)
        if item.state in ("done", "skipped"):
            bar.setRange(0, 100)
            bar.setValue(100)

        speed_item = self.table.item(row, COL_SPEED)
        speed_item.setText(f"{_fmt_bytes(item.speed)}/s" if item.state == "running" else "-")

        size_item = self.table.item(row, COL_SIZE)
        if item.total:
            size_item.setText(f"{_fmt_bytes(item.downloaded)} / {_fmt_bytes(item.total)}")
        else:
            size_item.setText(_fmt_bytes(item.downloaded))

    def on_progress(self, item_id: int) -> None:
        self.on_status(item_id)

    def on_cleared(self) -> None:
        self.rebuild()

    def rebuild(self) -> None:
        self.table.setRowCount(0)
        self._rows.clear()
        if self.engine:
            for item_id in list(self.engine.items.keys()):
                self.on_status(item_id)

    # ----------------------------------------------------------------- helpers

    def _selected_item_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        for item_id, r in self._rows.items():
            if r == row:
                return item_id
        return None

    def _act(self, action: str) -> None:
        item_id = self._selected_item_id()
        if item_id is None or self.engine is None:
            return
        if action == "pause":
            self.engine.pause(item_id)
        elif action == "resume":
            self.engine.resume(item_id)
        elif action == "retry":
            self.engine.retry(item_id)

    def _clear_done(self) -> None:
        if self.engine:
            self.engine.clear_finished()
            self.rebuild()

    def _open_dir(self) -> None:
        import pathlib

        if self.engine is None:
            return
        path = pathlib.Path(self.engine.dest_dir)
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
