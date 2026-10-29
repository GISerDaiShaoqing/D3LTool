# -*- coding: utf-8 -*-
"""AI Assistant panel tests (offscreen Qt, scripted fake transports)."""

import json
import time

import pytest


def _pump(app, panel, timeout=10.0):
    """Process Qt events until the agent turn finishes."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if panel._agent_thread is None and panel.send_btn.isEnabled():
            return True
        time.sleep(0.01)
    return False


def _make_panel(monkeypatch, tmp_path):
    """An offscreen AgentPanel with isolated config; returns (app, panel, saved)."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    import d3ltool.config as config
    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.agent_panel import AgentPanel

    cfg = dict(config.DEFAULTS)
    saved = {}
    monkeypatch.setattr(config, "load_config", lambda: cfg)
    monkeypatch.setattr(
        config, "update_config",
        lambda **kw: (saved.update(kw), cfg.update(kw), cfg)[2])

    app = QApplication.instance() or QApplication([])
    return app, AgentPanel(), saved


def _apply_valid_settings(panel):
    panel._apply_settings(base_url="https://api.test/v1", model="m",
                          api_key="sk-test")


def _scripted_transport(*final_text):
    def transport(messages, tool_specs):
        if not any(m.get("role") == "tool" for m in messages):
            return [
                {"type": "text", "text": "好的，我来查询 "},
                {"type": "tool_calls", "calls": [
                    {"id": "c1", "name": "list_products",
                     "arguments": {"group": "VIIRS"}}]},
                {"type": "done", "finish_reason": "tool_calls"},
            ]
        return [{"type": "text", "text": "".join(final_text)},
                {"type": "done", "finish_reason": "stop"}]
    return transport


def test_agent_panel_flow_shows_tool_and_answer(monkeypatch, tmp_path):
    app, panel, _saved = _make_panel(monkeypatch, tmp_path)
    monkeypatch.setattr(panel, "_make_transport",
                        lambda: _scripted_transport("VIIRS 有 4 个产品。"))

    _apply_valid_settings(panel)
    panel.input.setPlainText("列出 VIIRS 产品")
    panel._send()

    assert _pump(app, panel)
    text = panel.chat.toPlainText()
    assert "列出 VIIRS 产品" in text            # user message echoed
    assert "list_products" in text             # tool call line
    assert "VIIRS 有 4 个产品。" in text         # final answer
    assert panel.send_btn.isEnabled()


def test_agent_panel_saves_api_key(monkeypatch, tmp_path):
    app, panel, saved = _make_panel(monkeypatch, tmp_path)
    monkeypatch.setattr(panel, "_make_transport", lambda: _scripted_transport("ok"))

    _apply_valid_settings(panel)
    panel.input.setPlainText("hi")
    panel._send()
    _pump(app, panel)

    assert saved.get("ai_api_key") == "sk-test"
    assert saved.get("ai_base_url") == "https://api.test/v1"
    assert saved.get("ai_model") == "m"
    assert panel.current_settings()["api_key"] == "sk-test"


def test_agent_panel_requires_setup(monkeypatch, tmp_path):
    app, panel, _saved = _make_panel(monkeypatch, tmp_path)
    warnings = []
    monkeypatch.setattr(panel, "_warn", lambda msg: warnings.append(msg))

    panel.input.setPlainText("hi")
    panel._send()

    assert len(warnings) == 1
    assert "base_url" in warnings[0]
    assert panel._agent_thread is None         # nothing started


def test_agent_panel_ollama_needs_no_api_key(monkeypatch, tmp_path):
    app, panel, _saved = _make_panel(monkeypatch, tmp_path)
    monkeypatch.setattr(panel, "_make_transport",
                        lambda: _scripted_transport("done"))

    from d3ltool.agent.llm import PROVIDER_PRESETS

    ollama_index = next(i for i, (label, _u, _m) in enumerate(PROVIDER_PRESETS)
                        if label.startswith("Ollama"))
    panel.provider_combo.setCurrentIndex(ollama_index)
    panel.base_url_edit.setText("http://125.220.139.185:11434/v1")
    panel.model_edit.setText("qwen2.5:7b")
    panel.api_key_edit.setText("")             # Ollama: no key

    warnings = []
    monkeypatch.setattr(panel, "_warn", lambda msg: warnings.append(msg))
    panel.input.setPlainText("hi")
    panel._send()

    assert warnings == []
    assert panel._agent_thread is not None
    _pump(app, panel)


def test_agent_panel_confirm_decline(monkeypatch, tmp_path):
    app, panel, _saved = _make_panel(monkeypatch, tmp_path)

    def transport(messages, tool_specs):
        if not any(m.get("role") == "tool" for m in messages):
            return [{"type": "tool_calls", "calls": [
                {"id": "t1", "name": "start_download",
                 "arguments": {"urls": ["https://x/1.h5"]}}]},
                {"type": "done", "finish_reason": "tool_calls"}]
        return [{"type": "text", "text": "好的，已按你的要求取消"},
                {"type": "done", "finish_reason": "stop"}]

    monkeypatch.setattr(panel, "_make_transport", lambda: transport)
    asked = {}

    def record_confirm(name, arguments_json):
        asked["name"] = name
        asked["arguments"] = json.loads(arguments_json)
        return False                            # decline

    monkeypatch.setattr(panel, "_confirm_download", record_confirm)

    _apply_valid_settings(panel)
    panel.input.setPlainText("下载 x")
    panel._send()
    assert _pump(app, panel)

    text = panel.chat.toPlainText()
    assert asked["name"] == "start_download"
    assert asked["arguments"] == {"urls": ["https://x/1.h5"]}
    assert "user declined this download" in text
    assert "已按你的要求取消" in text


def test_agent_panel_confirm_accept_runs_download(monkeypatch, tmp_path):
    """Yes on the real dialog must reach the worker and run the tool.

    Regression: Signal(dict) got copied across the queued connection, so the
    worker read answer=False even after the user clicked Yes and reported
    "user declined this download".
    """
    app, panel, _saved = _make_panel(monkeypatch, tmp_path)

    def transport(messages, tool_specs):
        if not any(m.get("role") == "tool" for m in messages):
            return [{"type": "tool_calls", "calls": [
                {"id": "t1", "name": "start_download",
                 "arguments": {"urls": ["https://x/1.h5"]}}]},
                {"type": "done", "finish_reason": "tool_calls"}]
        return [{"type": "text", "text": "已提交下载"},
                {"type": "done", "finish_reason": "stop"}]

    monkeypatch.setattr(panel, "_make_transport", lambda: transport)

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "exec",
                        lambda self: int(QMessageBox.StandardButton.Yes))

    import d3ltool.tools as tools
    from types import SimpleNamespace
    ran = []
    fake = SimpleNamespace(
        fn=lambda urls, dest="": (ran.append(urls), {"queued": urls})[1])
    monkeypatch.setattr(tools, "get_spec",
                        lambda name: fake if name == "start_download" else None)

    _apply_valid_settings(panel)
    panel.input.setPlainText("下载 x")
    panel._send()
    assert _pump(app, panel)

    text = panel.chat.toPlainText()
    assert ran == [["https://x/1.h5"]]          # the tool executed after Yes
    assert "已提交下载" in text                   # final answer after the tool
    assert "user declined this download" not in text


def test_agent_panel_background_image(monkeypatch, tmp_path):
    """A chosen image paints under the panel; clearing restores default."""
    app, panel, _saved = _make_panel(monkeypatch, tmp_path)

    from PySide6.QtGui import QColor, QImage

    bg = tmp_path / "bg.png"
    img = QImage(10, 10, QImage.Format.Format_RGB32)
    img.fill(QColor(0x33, 0x66, 0xCC))
    assert img.save(str(bg), "PNG")

    panel.apply_background(str(bg))
    assert panel.background_path() == str(bg)
    color = panel.grab().toImage().pixelColor(5, 5)   # top-left margin pixel
    assert (color.red(), color.green(), color.blue()) == (0x33, 0x66, 0xCC)

    panel.apply_background("")
    assert panel.background_path() == ""
    assert panel._bg is None


def test_agent_panel_clear_resets_history(monkeypatch, tmp_path):
    app, panel, _saved = _make_panel(monkeypatch, tmp_path)
    monkeypatch.setattr(panel, "_make_transport", lambda: _scripted_transport("done"))

    _apply_valid_settings(panel)
    panel.input.setPlainText("hi")
    panel._send()
    _pump(app, panel)

    panel._clear_chat()
    assert len(panel.messages) == 1            # system prompt only
    assert panel.chat.toPlainText().strip() != ""   # welcome note shown


def test_agent_panel_preset_fills_fields(monkeypatch, tmp_path):
    _app, panel, _saved = _make_panel(monkeypatch, tmp_path)
    from d3ltool.agent.llm import PROVIDER_PRESETS

    # start on Custom so that switching to every preset fires the signal
    panel.provider_combo.setCurrentIndex(len(PROVIDER_PRESETS) - 1)
    for index, (_label, url, model) in enumerate(PROVIDER_PRESETS):
        panel.provider_combo.setCurrentIndex(index)
        if url:     # the Custom preset leaves the user's values untouched
            assert panel.base_url_edit.text() == url
            if model:
                assert panel.model_edit.text() == model


def test_agent_tool_result_summary():
    from d3ltool.gui.agent_panel import AgentPanel

    ok = AgentPanel._summarize_result(
        json.dumps({"count": 4, "granules": [{"filename": "a.h5"}]}))
    assert "4" in ok and "a.h5" in ok

    err = AgentPanel._summarize_result(json.dumps({"error": "boom"}))
    assert "boom" in err

    hint = AgentPanel._summarize_result(json.dumps({
        "error": "timeseries_failed",
        "hint": "layer 'NDVI' not found in the granule"}))
    assert "timeseries_failed" in hint and "not found" in hint

    ts = AgentPanel._summarize_result(json.dumps({
        "source": "M2T1NXSLV (GES DISC OPeNDAP)", "layer": "T2M",
        "units": "K",
        "stats": {"count": 24}, "truncated": False,
        "points": [["2019-12-01T01:30", 267.2]]}))
    assert "24 个点" in ts and "T2M" in ts and "K" in ts

    login = AgentPanel._summarize_result(json.dumps(
        {"authenticated": True, "user": "giser.d", "hint": ""}))
    assert "已登录" in login and "giser.d" in login
    assert AgentPanel._summarize_result(
        json.dumps({"authenticated": False})) == "未登录"
