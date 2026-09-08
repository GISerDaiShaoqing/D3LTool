# -*- coding: utf-8 -*-
"""Earthdata login dialog (performs login in a background thread)."""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QVBoxLayout)

from .. import auth, i18n


class _LoginThread(QThread):
    done = Signal(bool, str)      # ok, username-or-error

    def __init__(self, username, password, parent=None):
        super().__init__(parent)
        self._username = username
        self._password = password

    def run(self):
        try:
            user = auth.login(self._username, self._password, persist=True)
            self.done.emit(True, user)
        except Exception as exc:
            self.done.emit(False, str(exc))


class LoginDialog(QDialog):
    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("login_title"))
        self.setMinimumWidth(360)
        self._thread = None
        self._logged_user = ""

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.user_edit = QLineEdit(username)
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(i18n.tr("login_username"), self.user_edit)
        form.addRow(i18n.tr("login_password"), self.pass_edit)
        layout.addLayout(form)

        self.remember_box = QCheckBox(i18n.tr("login_remember"))
        self.remember_box.setChecked(True)
        layout.addWidget(self.remember_box)

        hint = QLabel(i18n.tr("login_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color:#c0392b;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.ok_btn = QPushButton(i18n.tr("login_ok"))
        self.ok_btn.setDefault(True)
        cancel_btn = QPushButton(i18n.tr("login_cancel"))
        buttons.addWidget(self.ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.ok_btn.clicked.connect(self._start_login)
        cancel_btn.clicked.connect(self.reject)

    def _start_login(self):
        if self._thread is not None:
            return
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        if not username or not password:
            self.error_label.setText(i18n.tr("login_failed", reason="empty username/password"))
            return
        self.ok_btn.setEnabled(False)
        self.ok_btn.setText(i18n.tr("login_running"))
        self.error_label.setText("")
        self._thread = _LoginThread(username, password, self)
        self._thread.done.connect(self._on_login_done)
        self._thread.start()

    def _on_login_done(self, ok, payload):
        self._thread = None
        self.ok_btn.setEnabled(True)
        self.ok_btn.setText(i18n.tr("login_ok"))
        if ok:
            self._logged_user = payload
            self.accept()
        else:
            self.error_label.setText(i18n.tr("login_failed", reason=payload))

    def logged_username(self) -> str:
        return self._logged_user

    def remember_username(self) -> bool:
        return self.remember_box.isChecked()
