# -*- coding: utf-8 -*-
"""Search results table with select-all / enqueue actions.

v2.8: click a header to sort, and a filename filter hides rows.  Sorting
reorders the VISUAL rows, so every consumer maps a visual row back to the
granule through the check item's UserRole (the source row of the last
populate) — never through the visual row index."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from .. import i18n, search

COL_CHECK, COL_NAME, COL_DATE, COL_TILE, COL_SIZE = range(5)


class _SortItem(QTableWidgetItem):
    """Sorting key: the raw value stored in UserRole (number or ISO date)
    wins over the display text, so 10.0 > 9.0 and dates sort chronologically."""

    def __lt__(self, other):
        a = self.data(Qt.ItemDataRole.UserRole)
        b = other.data(Qt.ItemDataRole.UserRole)
        if a is not None and b is not None:
            try:
                if isinstance(a, str) and isinstance(b, str):
                    return a < b
                return float(a) < float(b)
            except (TypeError, ValueError):
                pass
        # NEVER super().__lt__(): PySide re-enters this Python override and
        # recurses (surfaced the moment the initial sort indicator pointed
        # at the name column) — compare display text ourselves.
        return self.text() < other.text()


class ResultsTable(QWidget):
    enqueue_requested = Signal(list)    # list[dict(url, filename, size_bytes)]
    export_requested = Signal(list)     # same rows: write .txt/.html hand-off
    browse_requested = Signal(list)     # same rows: open the index in a browser

    def __init__(self, parent=None):
        super().__init__(parent)
        self._granules = []

        layout = QVBoxLayout(self)
        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton(i18n.tr("btn_select_all"))
        self.select_none_btn = QPushButton(i18n.tr("btn_select_none"))
        self.clear_btn = QPushButton(i18n.tr("btn_clear_results"))
        self.open_browser_btn = QPushButton(i18n.tr("btn_open_browser"))
        self.export_btn = QPushButton(i18n.tr("btn_export_links"))
        self.enqueue_btn = QPushButton(i18n.tr("btn_enqueue"))
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.select_none_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.open_browser_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.enqueue_btn)
        layout.addLayout(btn_row)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(i18n.tr("results_filter_hint"))
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.table = QTableWidget(0, 5)
        self._set_headers()
        layout.addWidget(self.table)

        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.select_none_btn.clicked.connect(lambda: self._set_all_checked(False))
        self.clear_btn.clicked.connect(self.clear)
        self.enqueue_btn.clicked.connect(self._on_enqueue)
        self.open_browser_btn.clicked.connect(self._open_in_browser)
        self.export_btn.clicked.connect(self._export_selected)

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
        self.table.setColumnWidth(COL_CHECK, 48)
        self.table.setColumnWidth(COL_DATE, 100)
        self.table.setColumnWidth(COL_TILE, 70)
        self.table.setColumnWidth(COL_SIZE, 90)
        from PySide6.QtWidgets import QHeaderView
        self.table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # sorting stays ON between populates: populate() turns it off while
        # filling (rows would reorder mid-fill) and back on afterwards
        self.table.setSortingEnabled(True)
        # v2.8 回归修复：排序指示器默认落在第 0 列（勾选列），36px 列宽里
        # 「选」+箭头互相裁剪成了乱码。初始指示器给到「文件名」列，勾选列
        # 头被点也弹回（勾选状态无排序意义），列宽 36→48。
        header.setSortIndicator(COL_NAME, Qt.SortOrder.AscendingOrder)
        header.sectionClicked.connect(self._keep_check_col_unsorted)

    def _keep_check_col_unsorted(self, section: int) -> None:
        if section == COL_CHECK:
            self.table.horizontalHeader().setSortIndicator(
                COL_NAME, Qt.SortOrder.AscendingOrder)

    def populate(self, granules) -> None:
        self._granules = list(granules)
        self.filter_edit.clear()          # a new result set starts unfiltered
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._granules))
        for row, g in enumerate(self._granules):
            check = QTableWidgetItem()
            check.setCheckState(Qt.CheckState.Checked)
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setData(Qt.ItemDataRole.UserRole, row)
            self.table.setItem(row, COL_CHECK, check)
            name = _SortItem(search.granule_filename(g))
            self.table.setItem(row, COL_NAME, name)
            date = _SortItem(search.granule_date(g))
            date.setData(Qt.ItemDataRole.UserRole, search.granule_date(g))
            self.table.setItem(row, COL_DATE, date)
            self.table.setItem(row, COL_TILE, _SortItem(search.granule_tile(g)))
            size_mb = search.granule_size_mb(g)
            size = _SortItem(f"{size_mb:.1f}" if size_mb else "-")
            size.setData(Qt.ItemDataRole.UserRole, float(size_mb or -1.0))
            self.table.setItem(row, COL_SIZE, size)
        self.table.setSortingEnabled(True)

    def clear(self) -> None:
        self._granules = []
        self.filter_edit.clear()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self.table.setSortingEnabled(True)

    def _apply_filter(self, needle: str) -> None:
        needle = (needle or "").strip().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_NAME)
            name = (item.text() if item is not None else "").lower()
            self.table.setRowHidden(row, bool(needle) and needle not in name)

    def _set_all_checked(self, checked: bool) -> None:
        """全选/全不选只作用于可见行——被过滤隐藏的行保持原状。"""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
            item = self.table.item(row, COL_CHECK)
            if item is not None:
                item.setCheckState(state)

    def _checked_items(self) -> list:
        rows = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_CHECK)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            src = item.data(Qt.ItemDataRole.UserRole)
            src_row = row if src is None else int(src)   # 0 is a valid source row!
            g = self._granules[src_row]
            links = search.granule_links(g)
            if not links:
                continue
            size_mb = search.granule_size_mb(g)
            rows.append({
                "url": links[0],
                "filename": search.granule_filename(g),
                "date": search.granule_date(g),
                "size_bytes": int(size_mb * 1024 * 1024) if size_mb else 0,
            })
        return rows

    def _on_enqueue(self) -> None:
        items = self._checked_items()
        if items:
            self.enqueue_requested.emit(items)

    def _export_selected(self) -> None:
        self.export_requested.emit(self._checked_items())

    def _open_in_browser(self) -> None:
        self.browse_requested.emit(self._checked_items())
