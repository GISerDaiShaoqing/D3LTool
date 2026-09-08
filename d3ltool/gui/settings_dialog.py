# -*- coding: utf-8 -*-
"""Settings dialog: download dir / workers / proxy."""

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QVBoxLayout)

from .. import i18n


class SettingsDialog(QDialog):
    def __init__(self, parent=None, config=None, on_save=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("settings_title"))
        self._config = config or {}
        self._on_save = on_save
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        dir_row = QHBoxLayout()
        self.dir_edit = QLineEdit(self._config.get("download_dir", ""))
        browse = QPushButton(i18n.tr("settings_browse"))
        browse.clicked.connect(self._browse)
        dir_row.addWidget(self.dir_edit)
        dir_row.addWidget(browse)
        form.addRow(i18n.tr("settings_download_dir"), dir_row)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 8)
        self.workers_spin.setValue(int(self._config.get("max_workers", 3)))
        form.addRow(i18n.tr("settings_workers"), self.workers_spin)

        self.proxy_edit = QLineEdit(self._config.get("proxy_url", ""))
        self.proxy_edit.setPlaceholderText("http://127.0.0.1:7890 / socks5://...")
        form.addRow(i18n.tr("settings_proxy"), self.proxy_edit)

        layout.addLayout(form)
        layout.addLayout(self._buttons())

    def _buttons(self):
        from PySide6.QtWidgets import QHBoxLayout

        row = QHBoxLayout()
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                               | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self._save)
        box.rejected.connect(self.reject)
        row.addStretch(1)
        row.addWidget(box)
        return row

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, i18n.tr("settings_download_dir"),
                                                self.dir_edit.text() or "")
        if path:
            self.dir_edit.setText(path)

    def _save(self):
        values = {
            "download_dir": self.dir_edit.text().strip() or self._config.get("download_dir", ""),
            "max_workers": self.workers_spin.value(),
            "proxy_url": self.proxy_edit.text().strip(),
        }
        if self._on_save is not None:
            self._on_save(values)
        self.accept()
