# -*- coding: utf-8 -*-
"""GLASS multi-variant batch search dialog (v2.8).

One checkbox list of the archive's variants (verified first, exactly like
the GLASS product group), a quick-filter box, and shared date/area/limit
settings that come from the main search panel.  OK emits the checked
variant ids; the actual search runs through the same worker thread /
progress / cancel machinery as a single search."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout)

from .. import glass, i18n, products


class BatchVariantDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("batch_title"))

        layout = QVBoxLayout(self)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(i18n.tr("batch_filter_hint"))
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.listw = QListWidget(self)
        glass_items = []
        for name, items in products.GROUPS:
            if name == "GLASS":
                glass_items = items
                break
        for short, _version, desc_zh, desc_en in glass_items:
            verified = bool(glass.get_variant(short).get("verified"))
            mark = i18n.tr("batch_verified_mark") if verified else ""
            desc = (desc_zh if i18n.get_language() == "zh" else desc_en) or ""
            label = f"{short}{mark}  ·  {desc}" if desc else f"{short}{mark}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, short)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.listw.addItem(item)
        layout.addWidget(self.listw, 1)

        sel_row = QHBoxLayout()
        self.all_btn = QPushButton(i18n.tr("batch_select_all"))
        self.none_btn = QPushButton(i18n.tr("batch_select_none"))
        self.all_btn.clicked.connect(lambda: self._set_all(True))
        self.none_btn.clicked.connect(lambda: self._set_all(False))
        sel_row.addWidget(self.all_btn)
        sel_row.addWidget(self.none_btn)
        sel_row.addStretch(1)
        self.count_label = QLabel("")
        sel_row.addWidget(self.count_label)
        layout.addLayout(sel_row)

        go_row = QHBoxLayout()
        go_row.addStretch(1)
        self.cancel_btn = QPushButton(i18n.tr("batch_cancel"))
        self.ok_btn = QPushButton(i18n.tr("batch_go"))
        self.ok_btn.setObjectName("accentButton")
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self._on_ok)
        go_row.addWidget(self.cancel_btn)
        go_row.addWidget(self.ok_btn)
        layout.addLayout(go_row)

        self.listw.itemChanged.connect(self._update_count)
        self._update_count()

    def _apply_filter(self, needle: str) -> None:
        needle = (needle or "").strip().lower()
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            short = str(item.data(Qt.ItemDataRole.UserRole)).lower()
            item.setHidden(bool(needle) and needle not in short)

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            if not item.isHidden():
                item.setCheckState(state)

    def _update_count(self, *_a) -> None:
        n = sum(1 for i in range(self.listw.count())
                if self.listw.item(i).checkState() == Qt.CheckState.Checked)
        self.count_label.setText(i18n.tr("batch_count", n=n))
        self.ok_btn.setEnabled(n > 0)

    def _on_ok(self) -> None:
        ids = []
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(str(item.data(Qt.ItemDataRole.UserRole)))
        self.accept()
        self.batch_confirmed = ids

    def selected_variants(self) -> list:
        """Checked variant ids in registry order; [] if the dialog was
        rejected."""
        return list(getattr(self, "batch_confirmed", []))
