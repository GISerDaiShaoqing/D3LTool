# -*- coding: utf-8 -*-
"""AI Assistant drawer panel: chat with any OpenAI-compatible provider.

The panel is the content of a right-edge drawer owned by the main window
(see main_window._build_agent_drawer). API settings live in a popup dialog
(AgentSettingsDialog) and the whole panel can paint a user-chosen
background image under chat and input. The agent logic itself stays in
d3ltool.agent (pure Python); this module is Qt only.
"""

import json
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QKeySequence, QPainter, QPixmap, QTextCursor
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton,
                               QTextBrowser, QTextEdit, QVBoxLayout, QWidget)

from .. import config, i18n
from ..agent import llm, loop
from .. import tools


class AgentThread(QThread):
    text_delta = Signal(str)
    tool_started = Signal(str, str)       # name, arguments-json
    tool_result = Signal(str, str)        # name, payload-json (truncated)
    failed = Signal(str)
    finished_turn = Signal()
    # object (NOT dict): PySide6 copies dict payloads across queued
    # connections, and the confirm answer must round-trip to the worker
    confirm_needed = Signal(object)       # {name, arguments, holder, event}

    def __init__(self, messages, settings, transport=None, parent=None):
        super().__init__(parent)
        self._messages = messages
        self._settings = settings
        self._transport = transport     # None -> build from settings
        self._stop_event = threading.Event()
        self._confirm_event = threading.Event()
        self._confirm_holder = {}

    def stop(self):
        self._stop_event.set()

    def run(self):
        if self._transport is None:
            transport = loop.default_transport(
                base_url=self._settings["base_url"],
                api_key=self._settings["api_key"],
                model=self._settings["model"],
                should_stop=self._stop_event.is_set,
            )
        else:
            transport = self._transport
        try:
            loop.run_agent_loop(
                self._messages, transport, tools,
                on_event=self._dispatch,
                confirm_cb=self._ask_confirm,
            )
        except Exception as exc:      # noqa: BLE001 — the panel must not die
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished_turn.emit()

    def _dispatch(self, event):
        kind = event["type"]
        if kind == "text":
            self.text_delta.emit(event["text"])
        elif kind == "assistant_text":
            pass                      # already shown as streamed deltas
        elif kind == "tool_start":
            self.tool_started.emit(event["name"],
                                   json.dumps(event["arguments"],
                                              ensure_ascii=False))
        elif kind == "tool_result":
            self.tool_result.emit(event["name"], event["result"])
        elif kind == "error":
            self.failed.emit(event["message"])

    # Runs in the worker thread: block on an Event until the GUI thread
    # answers the confirm_needed signal.
    def _ask_confirm(self, name, arguments):
        self._confirm_event.clear()
        self._confirm_holder = {"answer": False}
        self.confirm_needed.emit({
            "name": name,
            "arguments": arguments,
            "holder": self._confirm_holder,
            "event": self._confirm_event,
        })
        self._confirm_event.wait(timeout=600)
        return self._confirm_holder.get("answer", False)


class _InputEdit(QTextEdit):
    send_requested = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.send_requested.emit()
            return
        super().keyPressEvent(event)


class AgentSettingsDialog(QDialog):
    """Popup holding provider/API settings + the chat background choice.

    Owns all settings widgets; AgentPanel forwards the widget attributes so
    callers/tests keep the original names.
    """

    def __init__(self, panel, parent=None):
        super().__init__(parent or panel)
        self.panel = panel
        self.setWindowTitle(i18n.tr("agent_settings"))
        self.setMinimumWidth(460)

        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.provider_combo = QComboBox(self)
        self._presets = llm.PROVIDER_PRESETS
        for label, _url, _model in self._presets:
            self.provider_combo.addItem(label)
        self.provider_combo.currentIndexChanged.connect(self._on_preset)

        self.base_url_edit = QLineEdit(self)
        self.base_url_edit.setPlaceholderText("https://api.deepseek.com/v1")
        self.model_edit = QLineEdit(self)
        self.model_edit.setPlaceholderText("deepseek-chat / gpt-4o-mini / ...")
        self.api_key_edit = QLineEdit(self)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText(i18n.tr("agent_key_placeholder"))

        self.test_btn = QPushButton(i18n.tr("agent_test"), self)
        self.test_btn.clicked.connect(self.panel._test_connection)
        self.test_result = QLabel("", self)
        self.test_result.setWordWrap(True)

        # chat background image (optional; empty = default surface)
        self.bg_edit = QLineEdit(self)
        self.bg_pick = QPushButton(i18n.tr("agent_bg_pick"), self)
        self.bg_pick.clicked.connect(self._pick_bg)
        self.bg_clear = QPushButton(i18n.tr("agent_bg_clear"), self)
        self.bg_clear.clicked.connect(lambda: self.bg_edit.clear())
        bg_row = QHBoxLayout()
        bg_row.addWidget(self.bg_edit, 1)
        bg_row.addWidget(self.bg_pick)
        bg_row.addWidget(self.bg_clear)

        note = QLabel(i18n.tr("agent_key_note"), self)
        note.setWordWrap(True)

        form.addRow(self.provider_combo)
        form.addRow(i18n.tr("agent_base_url"), self.base_url_edit)
        form.addRow(i18n.tr("agent_model"), self.model_edit)
        form.addRow(i18n.tr("agent_api_key"), self.api_key_edit)
        form.addRow(self.test_btn, self.test_result)
        form.addRow(i18n.tr("agent_bg"), bg_row)
        form.addRow(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self._load_current()

    def _load_current(self):
        """Seed the fields from persisted config (Cancel keeps them intact)."""
        cfg = config.load_config()
        self.base_url_edit.setText(cfg.get("ai_base_url", ""))
        self.model_edit.setText(cfg.get("ai_model", ""))
        self.api_key_edit.setText(cfg.get("ai_api_key", ""))
        self.bg_edit.setText(cfg.get("ai_chat_bg", ""))

    def _on_preset(self, index):
        label, url, model = self._presets[index]
        if url:                      # keep the user's Custom values untouched
            self.base_url_edit.setText(url)
            if model:
                self.model_edit.setText(model)

    def _pick_bg(self):
        start = self.bg_edit.text() or str(Path.home())
        path, _filter = QFileDialog.getOpenFileName(
            self, i18n.tr("agent_bg_pick"), start,
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if path:
            self.bg_edit.setText(path)

    def apply(self):
        """Called after Accept: persist and reflect onto the panel."""
        base_url = self.base_url_edit.text().strip()
        model = self.model_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        bg = self.bg_edit.text().strip()
        config.update_config(ai_base_url=base_url, ai_model=model,
                             ai_api_key=api_key, ai_chat_bg=bg)
        self.panel._apply_settings(base_url=base_url, model=model,
                                   api_key=api_key)
        self.panel.apply_background(bg)


class AgentPanel(QWidget):
    """Content of the right-edge 'AI 助手' drawer."""

    hide_requested = Signal()         # the ✕ button; the drawer decides

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("agentPanel")
        self.messages = [{"role": "system", "content": self._system_prompt()}]
        self._agent_thread = None
        self._streaming_assistant = False
        self._bg = None               # QPixmap or None
        self._bg_path = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(6)

        # ---------------- header row
        header = QHBoxLayout()
        title = QLabel(i18n.tr("tab_agent"))
        title.setObjectName("agentTitle")
        self.gear_btn = QPushButton("⚙")
        self.gear_btn.setObjectName("agentHeaderBtn")
        self.gear_btn.setToolTip(i18n.tr("agent_settings"))
        self.gear_btn.clicked.connect(self._open_settings)
        self.hide_btn = QPushButton("✕")
        self.hide_btn.setObjectName("agentHeaderBtn")
        self.hide_btn.setToolTip(i18n.tr("agent_hide"))
        self.hide_btn.clicked.connect(self.hide_requested.emit)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.gear_btn)
        header.addWidget(self.hide_btn)
        root.addLayout(header)

        # ---------------- chat area (transparent over the panel background)
        self.chat = QTextBrowser()
        self.chat.setObjectName("agentChat")
        self.chat.setOpenExternalLinks(True)
        self.chat.setStyleSheet("QTextBrowser { background: transparent; }")
        root.addWidget(self.chat, 1)

        # ---------------- input row
        input_row = QHBoxLayout()
        self.input = _InputEdit()
        self.input.setObjectName("agentInput")
        self.input.setFixedHeight(64)
        self.input.setPlaceholderText(i18n.tr("agent_input_hint"))
        self.input.send_requested.connect(self._send)
        input_row.addWidget(self.input, 1)

        btn_col = QVBoxLayout()
        self.send_btn = QPushButton(i18n.tr("agent_send"))
        self.send_btn.setObjectName("accentButton")
        self.send_btn.setShortcut(QKeySequence("Ctrl+Return"))
        self.send_btn.clicked.connect(self._send)
        self.stop_btn = QPushButton(i18n.tr("agent_stop"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        self.clear_btn = QPushButton(i18n.tr("agent_clear"))
        self.clear_btn.clicked.connect(self._clear_chat)
        btn_col.addWidget(self.send_btn)
        btn_col.addWidget(self.stop_btn)
        btn_col.addWidget(self.clear_btn)
        input_row.addLayout(btn_col)
        root.addLayout(input_row)

        self._settings_dialog = AgentSettingsDialog(self)
        self.apply_background(config.load_config().get("ai_chat_bg", ""))
        self._append_html(self._welcome_html())

    # ------------------------------------------------- settings (popup dlg)

    # The settings widgets live in the popup dialog; forwarding the names
    # keeps the pre-2.2 attribute API for tests and external callers.
    @property
    def provider_combo(self):
        return self._settings_dialog.provider_combo

    @property
    def base_url_edit(self):
        return self._settings_dialog.base_url_edit

    @property
    def model_edit(self):
        return self._settings_dialog.model_edit

    @property
    def api_key_edit(self):
        return self._settings_dialog.api_key_edit

    @property
    def test_result(self):
        return self._settings_dialog.test_result

    def _open_settings(self):
        if self._settings_dialog.exec() == QDialog.DialogCode.Accepted:
            self._settings_dialog.apply()

    def _apply_settings(self, base_url: str, model: str, api_key: str):
        dlg = self._settings_dialog
        dlg.base_url_edit.setText(base_url)
        dlg.model_edit.setText(model)
        dlg.api_key_edit.setText(api_key)

    def current_settings(self) -> dict:
        dlg = self._settings_dialog
        return {
            "base_url": dlg.base_url_edit.text().strip(),
            "model": dlg.model_edit.text().strip(),
            "api_key": dlg.api_key_edit.text().strip(),
        }

    def _save_settings(self):
        s = self.current_settings()
        config.update_config(ai_base_url=s["base_url"],
                             ai_model=s["model"],
                             ai_api_key=s["api_key"])

    def _test_connection(self):
        s = self.current_settings()
        if not self._settings_valid(s):
            return
        self.test_result.setText(i18n.tr("agent_testing"))
        ok, message = llm.test_connection(s["base_url"], s["api_key"], s["model"])
        if ok:
            self.test_result.setStyleSheet("color: #1a7f37;")
            self.test_result.setText(i18n.tr("agent_test_ok"))
        else:
            self.test_result.setStyleSheet("color: #d6372a;")
            self.test_result.setText(i18n.tr("agent_test_fail", reason=message))

    def _settings_valid(self, s) -> bool:
        # Ollama needs no API key; other OpenAI-compatible providers do
        # (an empty key would otherwise fail later with a bare 401).
        local = self.provider_combo.currentText().strip().lower().startswith("ollama")
        required = [("base_url", s["base_url"]), ("model", s["model"])]
        if not local:
            required.append(("api_key", s["api_key"]))
        missing = [k for k, v in required if not v]
        if missing:
            self._warn(i18n.tr("agent_need_setup", fields=", ".join(missing)))
            return False
        return True

    def _warn(self, message: str) -> None:
        """Dialog seam (tests replace this)."""
        QMessageBox.warning(self, i18n.tr("err_title"), message)

    # ------------------------------------------------- background painting

    def apply_background(self, path: str):
        """Set (or clear with "") the image painted under the whole panel."""
        path = (path or "").strip()
        self._bg = QPixmap(path) if path else None
        self._bg_path = path if (path and self._bg is not None
                                 and not self._bg.isNull()) else ""
        # translucent input plate keeps text readable over a busy image
        self.input.setStyleSheet(
            "QTextEdit#agentInput { background: rgba(255, 255, 255, 205); }"
            if self._bg_path else "")
        self.update()

    def background_path(self) -> str:
        return self._bg_path

    def paintEvent(self, event):
        if self._bg is not None:
            painter = QPainter(self)
            r = self.rect()
            pm = self._bg.scaled(
                r.width(), r.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((r.width() - pm.width()) // 2,
                               (r.height() - pm.height()) // 2, pm)
            painter.end()
        super().paintEvent(event)

    # ------------------------------------------------------------- chat

    def _system_prompt(self) -> str:
        return i18n.tr("agent_system_prompt")

    def _welcome_html(self) -> str:
        return f"<p style='color:#666'>{i18n.tr('agent_welcome')}</p>"

    def _append_html(self, html: str):
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html + "<br>")
        self.chat.setTextCursor(cursor)
        self.chat.verticalScrollBar().setValue(
            self.chat.verticalScrollBar().maximum())

    def _append_text_delta(self, text: str):
        if not self._streaming_assistant:
            self._streaming_assistant = True
            cursor = self.chat.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml(f"<br><b style='color:#d6372a'>"
                              f"{i18n.tr('agent_ai_label')}</b> ")
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.chat.verticalScrollBar().setValue(
            self.chat.verticalScrollBar().maximum())

    def _end_stream_block(self):
        self._streaming_assistant = False

    # ------------------------------------------------------------ send flow

    def _send(self):
        if self._agent_thread is not None and self._agent_thread.isRunning():
            return
        s = self.current_settings()
        if not self._settings_valid(s):
            return
        self._save_settings()

        user_text = self.input.toPlainText().strip()
        if not user_text:
            return
        self.input.clear()
        self._append_html(f"<b style='color:#24292e'>{i18n.tr('agent_you_label')}"
                          f"</b> {self._escape(user_text)}")
        self.messages.append({"role": "user", "content": user_text})

        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._agent_thread = AgentThread(self.messages, s,
                                         transport=self._make_transport(),
                                         parent=self)
        self._agent_thread.text_delta.connect(self._on_text_delta)
        self._agent_thread.tool_started.connect(self._on_tool_started)
        self._agent_thread.tool_result.connect(self._on_tool_result)
        self._agent_thread.failed.connect(self._on_failed)
        self._agent_thread.finished_turn.connect(self._on_turn_finished)
        self._agent_thread.confirm_needed.connect(self._on_confirm_needed)
        self._agent_thread.start()

    def _make_transport(self):
        """Test seam: None lets the thread build the real provider transport;
        tests replace this method to script a fake one."""
        return None

    def _stop(self):
        if self._agent_thread is not None:
            self._agent_thread.stop()

    def _clear_chat(self):
        self.messages = [{"role": "system", "content": self._system_prompt()}]
        self.chat.clear()
        self._append_html(self._welcome_html())

    # ------------------------------------------------------- thread signals

    def _on_text_delta(self, text):
        self._append_text_delta(text)

    def _on_tool_started(self, name, arguments_json):
        self._end_stream_block()
        summary = arguments_json if len(arguments_json) <= 160 \
            else arguments_json[:157] + "..."
        self._append_html(f"<br><span style='color:#8250df'>🔧 "
                          f"{i18n.tr('agent_tool_run', name=name)} "
                          f"<code>{self._escape(summary)}</code></span>")

    def _on_tool_result(self, name, payload_json):
        summary = self._summarize_result(payload_json)
        color = "#1a7f37" if '"error"' not in payload_json else "#d6372a"
        self._append_html(f"<span style='color:{color}'>   ↳ {summary}</span>")

    def _on_failed(self, message):
        self._end_stream_block()
        self._append_html(f"<br><span style='color:#d6372a'>✗ "
                          f"{self._escape(message)}</span>")

    def _on_turn_finished(self):
        self._end_stream_block()
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        thread = self._agent_thread
        if thread is not None:
            thread.wait(2000)
        self._agent_thread = None

    # runs on the GUI thread; answers the worker's blocked confirm callback
    def _on_confirm_needed(self, info):
        args = json.dumps(info["arguments"], ensure_ascii=False)
        answer = self._confirm_download(info["name"], args)
        info["holder"]["answer"] = answer
        info["event"].set()

    def _confirm_download(self, name: str, arguments_json: str) -> bool:
        """Dialog seam (tests replace this): ask before the AI downloads."""
        box = QMessageBox(self)
        box.setWindowTitle(i18n.tr("agent_confirm_title"))
        box.setText(i18n.tr("agent_confirm_text", name=name))
        box.setDetailedText(arguments_json)
        box.setStandardButtons(QMessageBox.StandardButton.Yes
                               | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec() == QMessageBox.StandardButton.Yes

    # -------------------------------------------------------------- helpers

    @staticmethod
    def _escape(text: str) -> str:
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;"))

    @staticmethod
    def _summarize_result(payload_json: str) -> str:
        try:
            data = json.loads(payload_json)
        except ValueError:
            return payload_json[:120]
        if isinstance(data, dict) and data.get("error"):
            return str(data["error"])[:120]
        if isinstance(data, dict) and "count" in data:
            extra = ""
            items = data.get("granules") or data.get("items") or data.get("products")
            if items:
                first = items[0]
                name = first.get("filename") or first.get("short_name") or ""
                extra = f" · {name}"
            return f"{data['count']} 项{extra}"
        return payload_json[:120]
