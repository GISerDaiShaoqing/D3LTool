# -*- coding: utf-8 -*-
"""Search results table with select-all / enqueue actions."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from .. import i18n, search

COL_CHECK, COL_NAME, COL_DATE, COL_TILE, COL_SIZE = range(5)


class ResultsTable(QWidget):
    enqueue_requested = Signal(list)    # list[dict(url, filename, size_bytes)]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._granules = []

        layout = QVBoxLayout(self)
        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton(i18n.tr("btn_select_all"))
        self.select_none_btn = QPushButton(i18n.tr("btn_select_none"))
        self.enqueue_btn = QPushButton(i18n.tr("btn_enqueue"))
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.select_none_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.enqueue_btn)
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, 5)
        self._set_headers()
        layout.addWidget(self.table)

        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.select_none_btn.clicked.connect(lambda: self._set_all_checked(False))
        self.enqueue_btn.clicked.connect(self._on_enqueue)

    def _set_headers(self):
        self.table.setHorizontalHeaderLabels([
            i18n.tr("results_col_check"),
            i18n.tr("results_col_name"),
            i18n.tr("results_col_date"),
            i18n.tr("results_col_tile"),
            i18n.tr("results_col_size"),
        ])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        self.table.setColumnWidth(COL_CHECK, 36)
        self.table.setColumnWidth(COL_DATE, 100)
        self.table.setColumnWidth(COL_TILE, 70)
        self.table.setColumnWidth(COL_SIZE, 90)
        from PySide6.QtWidgets import QHeaderView
        self.table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    def populate(self, granules) -> None:
        self._granules = list(granules)
        self.table.setRowCount(len(self._granules))
        for row, g in enumerate(self._granules):
            check = QTableWidgetItem()
            check.setCheckState(Qt.CheckState.Checked)
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setData(Qt.ItemDataRole.UserRole, row)
            self.table.setItem(row, COL_CHECK, check)
            self.table.setItem(row, COL_NAME, QTableWidgetItem(search.granule_filename(g)))
            self.table.setItem(row, COL_DATE, QTableWidgetItem(search.granule_date(g)))
            self.table.setItem(row, COL_TILE, QTableWidgetItem(search.granule_tile(g)))
            size_mb = search.granule_size_mb(g)
            self.table.setItem(row, COL_SIZE,
                               QTableWidgetItem(f"{size_mb:.1f}" if size_mb else "-"))

    def clear(self) -> None:
        self._granules = []
        self.table.setRowCount(0)

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_CHECK)
            if item is not None:
                item.setCheckState(state)

    def _on_enqueue(self) -> None:
        items = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_CHECK)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            g = self._granules[row]
            links = search.granule_links(g)
            if not links:
                continue
            size_mb = search.granule_size_mb(g)
            items.append({
                "url": links[0],
                "filename": search.granule_filename(g),
                "size_bytes": int(size_mb * 1024 * 1024) if size_mb else 0,
            })
        if items:
            self.enqueue_requested.emit(items)
