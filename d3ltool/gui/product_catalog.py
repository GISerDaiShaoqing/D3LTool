# -*- coding: utf-8 -*-
"""Product catalog dialog: browse products per satellite, pick with a double-click.

Keeps the main search panel clean (one button) while giving non-experts a
readable reference of products, versions and descriptions.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from .. import i18n, products

COL_GROUP, COL_SHORT, COL_VERSION, COL_DESC = range(4)


class ProductCatalogDialog(QDialog):
    """Browsable catalog of all curated products; double-click applies one."""

    product_selected = Signal(str, str)      # short_name, version_hint

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("catalog_title"))
        self.resize(700, 480)

        layout = QVBoxLayout(self)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(i18n.tr("catalog_filter")))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(i18n.tr("catalog_filter_hint"))
        self.filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_edit, 1)
        layout.addLayout(filter_row)

        hint = QLabel(i18n.tr("catalog_hint"))
        hint.setStyleSheet("color:#6b7280;")
        layout.addWidget(hint)

        middle = QHBoxLayout()
        self.group_list = QListWidget()
        self.group_list.setMaximumWidth(190)
        self.group_list.addItem(i18n.tr("catalog_all"))
        for name, _items in products.GROUPS:
            self.group_list.addItem(name)
        self.group_list.setCurrentRow(0)
        self.group_list.currentRowChanged.connect(self._populate_table)
        middle.addWidget(self.group_list)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            i18n.tr("col_group"), i18n.tr("col_shortname"),
            i18n.tr("col_version"), i18n.tr("col_desc"),
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(lambda _index: self._apply_selection(self.table.currentRow()))
        middle.addWidget(self.table, 1)
        layout.addLayout(middle)

        buttons = QHBoxLayout()
        use_btn = QPushButton(i18n.tr("btn_use_product"))
        use_btn.setObjectName("accentButton")
        use_btn.clicked.connect(lambda: self._apply_selection(self.table.currentRow()))
        buttons.addStretch(1)
        buttons.addWidget(use_btn)
        layout.addLayout(buttons)

        self._populate_table()

    # ------------------------------------------------------------------ public

    def apply_product(self, short_name: str) -> None:
        """Programmatically apply a product by short_name (tests / convenience)."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_SHORT)
            if item is not None and item.text().upper() == short_name.upper():
                self._apply_selection(row)
                return

    # ------------------------------------------------------------------ slots

    def _all_rows(self) -> list:
        zh = i18n.get_language() == "zh"
        rows = []
        for gname, items in products.GROUPS:
            for short, version, desc_zh, desc_en in items:
                rows.append((gname, short, version, desc_zh if zh else desc_en))
        return rows

    def _populate_table(self, _row=None) -> None:
        needle = self.filter_edit.text().strip().lower()
        if needle:
            rows = []
            for gname, items in products.GROUPS:
                for short, version, desc_zh, desc_en in items:
                    desc = desc_zh if i18n.get_language() == "zh" else desc_en
                    hay = f"{gname} {short} {desc_zh} {desc_en}".lower()
                    if needle in hay:
                        rows.append((gname, short, version, desc))
            self._load_rows(rows)
            return
        group_item = self.group_list.currentItem()
        group_name = group_item.text() if group_item else ""
        if group_name == i18n.tr("catalog_all"):
            self._load_rows(self._all_rows())
            return
        rows = [(g, s, v, d if i18n.get_language() == "zh" else de)
                for g, items in products.GROUPS if g == group_name
                for s, v, d, de in items]
        self._load_rows(rows)

    def _apply_filter(self, _text=None) -> None:
        self._populate_table()

    def _apply_selection(self, row=None) -> None:
        if row is None or row < 0 or row >= self.table.rowCount():
            return
        short_item = self.table.item(row, COL_SHORT)
        version_item = self.table.item(row, COL_VERSION)
        if short_item is None:
            return
        self.product_selected.emit(short_item.text(),
                                   version_item.text() if version_item else "")
        self.accept()

    # ----------------------------------------------------------------- helpers

    def _load_rows(self, rows) -> None:
        self.table.setRowCount(len(rows))
        for row, (gname, short, version, desc) in enumerate(rows):
            self.table.setItem(row, COL_GROUP, QTableWidgetItem(gname))
            self.table.setItem(row, COL_SHORT, QTableWidgetItem(short))
            self.table.setItem(row, COL_VERSION, QTableWidgetItem(version))
            desc_item = QTableWidgetItem(desc)
            desc_item.setToolTip(desc)
            self.table.setItem(row, COL_DESC, desc_item)
