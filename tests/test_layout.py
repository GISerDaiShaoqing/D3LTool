# -*- coding: utf-8 -*-
"""Regression test: on short windows the search panel must scroll, never
overlap (the tile map used to collide with the locate row / search button)."""

import time

import pytest


def test_search_panel_structure(tmp_path, monkeypatch):
    """The pinned action bar must live outside the scroll area, by design."""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import d3ltool.config as config

    cfg = dict(config.DEFAULTS)
    cfg["download_dir"] = str(tmp_path / "downloads")
    monkeypatch.setattr(config, "load_config", lambda: cfg)

    from PySide6.QtWidgets import QApplication, QScrollArea

    from d3ltool.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    sp = window.search_panel

    scrolls = sp.findChildren(QScrollArea)
    assert len(scrolls) == 1
    sa = scrolls[0]
    assert sa.widgetResizable()

    def is_descendant(widget, ancestor):
        p = widget.parentWidget()
        while p is not None:
            if p is ancestor:
                return True
            p = p.parentWidget()
        return False

    # the three cards scroll; the search button does not
    body = sa.widget()
    assert is_descendant(sp.tile_map, body)
    assert not is_descendant(sp.search_btn, body)
    assert sp.search_btn.parent() is sp
    window.close()


def test_no_overlap_on_short_window(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import d3ltool.config as config

    cfg = dict(config.DEFAULTS)
    cfg["download_dir"] = str(tmp_path / "downloads")
    monkeypatch.setattr(config, "load_config", lambda: cfg)

    from PySide6.QtWidgets import QApplication, QScrollArea

    from d3ltool.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.processEvents()
    app.processEvents()

    # a maximized 125%-DPI laptop offers far less height than the panel's
    # natural minimum; the panel must scroll instead of overlapping
    window.resize(1200, 700)
    app.processEvents()
    app.processEvents()

    sp = window.search_panel

    def mapped(widget):
        r = widget.geometry()
        r.moveTo(widget.mapTo(window, r.topLeft()))
        return r

    # widgets inside the scroll area can only paint within its viewport, so
    # clip their rects before checking intersections
    sa = sp.findChildren(QScrollArea)[0]
    viewport_rect = mapped(sa.viewport())

    widgets = {"tile_map": sp.tile_map, "search_btn": sp.search_btn,
               "lon_edit": sp.lon_edit, "bbox_edit": sp.bbox_edit,
               "limit_spin": sp.limit_spin}
    rects = {}
    for name, wd in widgets.items():
        r = mapped(wd)
        parent = wd.parentWidget()
        while parent is not None:
            if parent is sa.viewport():
                r = r.intersected(viewport_rect)
                break
            parent = parent.parentWidget()
        rects[name] = r

    names = list(rects)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if rects[a].width() <= 0 or rects[b].width() <= 0:
                continue     # fully scrolled out of view
            inter = rects[a].intersected(rects[b])
            assert inter.width() <= 0 or inter.height() <= 0, \
                f"{a} overlaps {b}: {inter.getRect()}"

    # on a real windowing system the pinned button is always on screen
    # (offscreen platforms activate layouts lazily, so skip there)
    if app.platformName() != "offscreen":
        btn = rects["search_btn"]
        assert 0 <= btn.top() <= btn.bottom() <= window.height()
    window.close()


def _make_window(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import d3ltool.config as config

    cfg = dict(config.DEFAULTS)
    cfg["download_dir"] = str(tmp_path / "downloads")
    monkeypatch.setattr(config, "load_config", lambda: cfg)

    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.processEvents()
    app.processEvents()
    return app, window


def _drawer_span(window):
    """The drawer hangs below the menu bar and stops above the status bar."""
    top = window.menuBar().height()
    bottom = window.height() - window.statusBar().height()
    return top, bottom


def test_agent_drawer_overlay_leaves_data_layout_alone(tmp_path, monkeypatch):
    """The drawer floats over the data page: opening/closing must not
    reflow the search panel, and it must sit flush at the right edge,
    hanging below the menu bar."""
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        before = window.search_panel.geometry()
        assert not window.agent_drawer.isVisible()
        assert window.agent_tab_btn.isVisible()

        window._toggle_agent_drawer(animate=False)
        app.processEvents()
        assert window.agent_drawer.isVisible()
        assert not window.agent_tab_btn.isVisible()
        top, bottom = _drawer_span(window)
        assert window.agent_drawer.geometry().top() == top
        assert window.agent_drawer.geometry().bottom() == bottom - 1
        assert window.agent_drawer.x() + window.agent_drawer.width() \
            == window.width()
        assert window.search_panel.geometry() == before

        window._toggle_agent_drawer(animate=False)
        app.processEvents()
        assert not window.agent_drawer.isVisible()
        assert window.agent_tab_btn.isVisible()
        assert window.search_panel.geometry() == before
    finally:
        window.close()


def test_agent_drawer_repins_on_resize(tmp_path, monkeypatch):
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        window._toggle_agent_drawer(animate=False)
        app.processEvents()
        window.resize(1300, 720)
        app.processEvents()
        top, bottom = _drawer_span(window)
        assert window.agent_drawer.geometry().top() == top
        assert window.agent_drawer.geometry().bottom() == bottom - 1
        assert window.agent_drawer.x() + window.agent_drawer.width() \
            == window.width()
    finally:
        window.close()


def test_two_drawers_are_mutually_exclusive(tmp_path, monkeypatch):
    """AI and time series live in separate right-edge drawers with their
    own edge tabs; opening one closes the other, both keep the data page
    untouched, and both sit flush at the right edge."""
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        window._agent_ctl.anim.setDuration(0)
        window._ts_ctl.anim.setDuration(0)
        cw = window.centralWidget()
        before = window.search_panel.geometry()
        assert not window.agent_drawer.isVisible()
        assert not window.ts_drawer.isVisible()
        assert window.agent_tab_btn.isVisible()
        assert window.ts_tab_btn.isVisible()

        window._toggle_agent_drawer(animate=False)
        app.processEvents()
        assert window.agent_drawer.isVisible()
        assert not window.ts_drawer.isVisible()
        assert not window.agent_tab_btn.isVisible()
        assert window.ts_tab_btn.isVisible()
        assert window.agent_drawer.geometry().right() == cw.rect().right()
        assert window.search_panel.geometry() == before

        # opening the time-series drawer closes the AI drawer
        window._focus_timeseries()
        app.processEvents()
        assert window.ts_drawer.isVisible()
        assert not window.agent_drawer.isVisible()
        assert not window.ts_tab_btn.isVisible()
        assert window.agent_tab_btn.isVisible()
        assert window.ts_drawer.geometry().right() == cw.rect().right()
        assert window.search_panel.geometry() == before

        # the ✕ of the time-series panel closes its own drawer only
        window.ts_panel.hide_requested.emit()
        app.processEvents()
        assert not window.ts_drawer.isVisible()
        assert window.ts_tab_btn.isVisible()
        assert not window.agent_drawer.isVisible()

        window._focus_agent()
        app.processEvents()
        assert window.agent_drawer.isVisible()
        assert not window.ts_drawer.isVisible()
    finally:
        window.close()


def test_time_series_csv_export(tmp_path, monkeypatch):
    """The export writes a utf-8-sig CSV with a commented metadata header
    and date,value rows; exporting with no series never opens a dialog."""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.timeseries_panel import TimeSeriesPanel

    app = QApplication.instance() or QApplication([])
    panel = TimeSeriesPanel()
    panel.render_points([])
    monkeypatch.setattr(panel, "_ask_save_path",
                        lambda: pytest.fail("dialog opened with no series"))
    panel._export()                       # -> inline error, no dialog
    assert "error" == panel.status_label.property("state")

    panel.render_points([("2009-01-01", 0.7), ("2009-01-17", 1.3)])
    panel._meta = {"product": "MOD13Q1", "layer": "_250m_16_days_NDVI",
                   "lat": "36.833", "lon": "116.567",
                   "start": "2009-01-01", "end": "2009-12-31",
                   "source": "MOD13Q1 (LAADS OPeNDAP)"}
    out = tmp_path / "series.csv"
    monkeypatch.setattr(panel, "_ask_save_path", lambda: str(out))
    panel._export()
    text = out.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    assert lines[0] == "# product: MOD13Q1"
    assert "# layer: _250m_16_days_NDVI" in lines
    assert "# lat: 36.833" in lines
    assert "date,value" in lines
    assert "2009-01-17,1.3" in lines
    assert "已导出" in panel.status_label.text() \
        or "Exported" in panel.status_label.text()


def test_time_series_panel_renders_points(tmp_path, monkeypatch):
    """QtCharts line series gets the points; nulls already filtered upstream."""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCharts import QLineSeries
    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.timeseries_panel import TimeSeriesPanel

    app = QApplication.instance() or QApplication([])
    panel = TimeSeriesPanel()
    points = [("2009-01-01", 0.7), ("2009-01-17", 1.3),
              ("2009-01-25", 0.9)]
    panel.render_points(points)
    series = panel.chart.series()
    assert len(series) == 1
    assert series[0].count() == 3
    assert panel.last_points == [list(p) for p in points]

    panel.render_points([])
    assert panel.chart.series() == []
    assert panel.last_points == []


def test_time_series_panel_clear_button(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.timeseries_panel import TimeSeriesPanel

    app = QApplication.instance() or QApplication([])
    panel = TimeSeriesPanel()
    panel.render_points([("2009-01-01", 0.7), ("2009-01-17", 1.3)])
    panel._meta = {"product": "MOD13Q1"}
    panel.clear_btn.click()
    assert panel.chart.series() == []
    assert panel.chart.axes() == []
    assert panel.last_points == []
    assert panel._meta is None


def test_time_series_panel_hourly_stamps_and_fresh_axes(monkeypatch):
    """MERRA-2 hourly stamps parse, and re-plotting must not stack the
    previous run's axes beside the new ones."""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.timeseries_panel import TimeSeriesPanel

    app = QApplication.instance() or QApplication([])
    panel = TimeSeriesPanel()
    panel.render_points([("2025-10-25T01:30", 270.0),
                         ("2025-10-25T02:30", 271.0),
                         ("2025-10-25T03:30", 269.5)])
    series = panel.chart.series()
    assert len(series) == 1
    assert series[0].count() == 3
    assert len(panel.chart.axes()) == 2           # one x + one y

    panel.render_points([("2009-01-01", 0.7), ("2009-01-17", 1.3)])
    assert panel.chart.series()[0].count() == 2
    assert len(panel.chart.axes()) == 2           # old axes gone, not piled up


def test_agent_plot_sink_opens_ts_drawer(tmp_path, monkeypatch):
    """The AI assistant's plot_timeseries tool lands in the app's own
    time-series drawer and pops it open."""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        window._plot_agent_series(
            [("2010-01-01", 0.18), ("2010-01-17", 0.22)],
            {"product": "MOD13Q1", "layer": "_250m_16_days_NDVI",
             "lat": "36.833", "lon": "116.567",
             "start": "2010-01-01", "end": "2010-12-31",
             "source": "MOD13Q1 (LAADS OPeNDAP)"})
        app.processEvents()
        assert window.ts_drawer.isVisible()
        assert window.ts_panel.chart.series()[0].count() == 2
        assert window.ts_panel._meta["product"] == "MOD13Q1"
        assert window.ts_panel.last_points == [["2010-01-01", 0.18],
                                               ["2010-01-17", 0.22]]
    finally:
        window.close()


def test_time_series_panel_validation(tmp_path, monkeypatch):
    """Bad coordinates are reported inline; no worker thread is started."""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.timeseries_panel import TimeSeriesPanel

    app = QApplication.instance() or QApplication([])
    panel = TimeSeriesPanel()
    panel.lat_edit.setText("120")          # out of range
    panel.lon_edit.setText("116.5")
    panel.product_combo.setCurrentText("MOD13Q1")
    panel._plot()
    assert panel._thread is None
    assert panel.plot_btn.isEnabled()
    assert "error" == panel.status_label.property("state")

    panel.lat_edit.setText("36.833")
    panel.product_combo.setCurrentText("   ")
    panel._plot()                          # missing product
    assert panel._thread is None
    assert "error" == panel.status_label.property("state")
