# -*- coding: utf-8 -*-
"""Offscreen GUI smoke test: the whole UI can be constructed."""

import pytest


def test_main_window_smoke(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")

    # force offscreen before Qt widgets are created
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    # isolate user config so the test never touches the real ~/.d3ltool
    import d3ltool.config as config

    cfg = dict(config.DEFAULTS)
    cfg["download_dir"] = str(tmp_path / "downloads")
    monkeypatch.setattr(config, "load_config", lambda: cfg)
    monkeypatch.setattr(config, "update_config", lambda **kw: {**cfg, **kw})

    from PySide6.QtWidgets import QApplication

    from d3ltool import APP_NAME
    from d3ltool.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert APP_NAME in window.windowTitle()
    assert window.engine.dest_dir.name == "downloads"
    assert window.search_panel is not None
    assert window.results_table is not None
    assert window.task_table is not None
    window.close()
