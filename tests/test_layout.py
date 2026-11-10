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


def test_agent_plot_sink_relays_to_gui_thread(tmp_path, monkeypatch):
    """plot_timeseries executes on the agent worker thread (QThread.run ->
    run_agent_loop -> spec.fn); before the plot bridge the sink touched
    drawer widgets from that thread — undefined behaviour that
    intermittently hard-crashes the app. The sink must deliver through a
    queued signal so the drawer is only ever touched on the GUI thread."""
    import threading

    from d3ltool import tools

    app, window = _make_window(tmp_path, monkeypatch)
    try:
        seen = {}

        def fake_render(points, meta):
            seen["render"] = threading.current_thread()

        def fake_toggle(animate=True):
            seen["toggle"] = threading.current_thread()

        monkeypatch.setattr(window.ts_panel, "show_external_series",
                            fake_render)
        monkeypatch.setattr(window, "_toggle_ts_drawer", fake_toggle)

        def fire():
            tools._PLOT_SINK([("2010-08-07", 0.78)],
                             {"product": "MOD13Q1", "layer": "NDVI"})

        t = threading.Thread(target=fire)
        t.start()
        t.join()
        deadline = time.time() + 2
        while "render" not in seen and time.time() < deadline:
            app.processEvents()

        assert seen["render"] is threading.current_thread()
        assert seen["toggle"] is threading.current_thread()
    finally:
        window.close()


def test_results_export_and_browse_requests(tmp_path, monkeypatch):
    """The two browser-handoff buttons emit the checked rows to the main
    window; unchecked rows and none-checks stay out."""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import d3ltool.search as search

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.results_table import ResultsTable

    app = QApplication.instance() or QApplication([])

    granule = object()
    monkeypatch.setattr(
        search, "granule_links",
        lambda g: ["https://ladsweb.modaps.eosdis.nasa.gov/a.hdf"])
    monkeypatch.setattr(search, "granule_filename", lambda g: "a.hdf")
    monkeypatch.setattr(search, "granule_date", lambda g: "2025-01-16")
    monkeypatch.setattr(search, "granule_size_mb", lambda g: 5.0)

    t = ResultsTable()
    t.populate([granule, granule])
    t.table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)   # keep 1 row

    got = []
    t.export_requested.connect(lambda items: got.append(list(items)))
    browsed = []
    t.browse_requested.connect(lambda items: browsed.append(list(items)))
    t.export_btn.click()
    t.open_browser_btn.click()
    assert len(got) == 1 and len(got[0]) == 1
    assert got[0][0]["url"].startswith("https://ladsweb")
    assert got[0][0]["date"] == "2025-01-16"
    assert got[0][0]["size_bytes"] == 5 * 1024 * 1024
    assert len(browsed) == 1 and browsed[0] == got[0]

    t.clear_btn.click()
    assert t.table.rowCount() == 0 and t._granules == []
    got.clear()
    t.export_btn.click()
    assert got == [[]]      # still one empty emission -> main window shows
                            # the generic "nothing to export" status line


def test_task_table_export_requests_engine_rows(tmp_path, monkeypatch):
    """任务表「导出失败清单」：只导失败任务（401/403 救援线，跨检索
    生存）；成功/排队中/运行中永不混入。"""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import types

    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.task_table import TaskTable

    app = QApplication.instance() or QApplication([])
    engine = types.SimpleNamespace(items={
        1: types.SimpleNamespace(url="https://x/1.hdf", filename="1.hdf",
                                 total=1024 * 1024, state="failed"),
        2: types.SimpleNamespace(url="https://x/2.hdf", filename="2.hdf",
                                 total=0, state="pending"),
        3: types.SimpleNamespace(url="https://x/3.hdf", filename="3.hdf",
                                 total=0, state="done"),
    })
    t = TaskTable(engine)
    got = []
    t.export_requested.connect(lambda items: got.append(list(items)))
    t.export_btn.click()
    assert [it["url"] for it in got[0]] == ["https://x/1.hdf"]
    assert got[0][0]["size_bytes"] == 1024 * 1024


def test_tile_clear_button(tmp_path, monkeypatch):
    """「清除瓦片」一键全清：地图选择与瓦片输入框一起复位。"""
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        sp = window.search_panel
        sp.tile_map.set_selected_names(["h29v05", "h35v05"])
        assert sp.tile_edit.text() == "h29v05, h35v05"
        sp.tile_clear_btn.click()
        assert sp.tile_map.selected_tiles() == []
        assert sp.tile_edit.text() == ""
    finally:
        window.close()


def test_tile_map_has_no_stripes_outside_bands(tmp_path, monkeypatch):
    """窄行格线必须随带宽收窄：旧的固定 9px 步距把格线画过行的右缘，
    在球体外面留下一把条纹梳子（用户截图红圈处）。"""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import d3ltool.tiles as tiles_mod

    from d3ltool.gui.tile_map import CANVAS_W, TILE_H, TileMap

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    m = TileMap()
    img = m.grab().toImage()
    cx = CANVAS_W / 2.0
    for v in (0, 17):                       # the two narrowest rows
        edge = cx + tiles_mod.row_width_fraction(v) * CANVAS_W / 2.0
        for x in range(int(edge) + 4, min(int(edge) + 44, CANVAS_W)):
            assert img.pixelColor(x, v * TILE_H + 6).name() == "#f4f7fb", \
                f"stripe pixel outside row {v}'s band at x={x}"


def test_search_panel_has_glass_group(tmp_path, monkeypatch):
    """GLASS 组出现在组下拉里：切换后产品下拉是变体 id（已核验排前），
    组名经 products.GROUPS 自动带出，无需专门 UI 代码。"""
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        sp = window.search_panel
        idx = sp.group_combo.findText("GLASS")
        assert idx >= 0
        sp.group_combo.setCurrentIndex(idx)
        assert sp.product_combo.currentText() == "AGB_0.01D_V02"
        names = [sp.product_combo.itemText(i)
                 for i in range(sp.product_combo.count())]
        assert "LAI_MODIS_250M" in names and "AGB_0.05D" in names
    finally:
        window.close()


def test_search_panel_glass_hints(tmp_path, monkeypatch):
    """GLASS 布局联动：flat 静态集禁用日期并提示，全球 CMG 提示免瓦片，
    分瓦片变体与 NASA 产品无提示。"""
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        sp = window.search_panel

        def pick(short_name):
            # 可编辑 QComboBox 的 setCurrentText 只改行编辑文本、不触发
            # currentIndexChanged——走 findData/setCurrentIndex 才是真实联动
            idx = sp.product_combo.findData(short_name)
            assert idx >= 0, short_name
            sp.product_combo.setCurrentIndex(idx)
            sp._update_glass_hint()

        gidx = sp.group_combo.findText("GLASS")
        assert gidx >= 0
        sp.group_combo.setCurrentIndex(gidx)

        pick("LAI_MODIS_250M")
        assert sp.glass_hint.isHidden()
        assert sp.start_edit.isEnabled() and sp.end_edit.isEnabled()

        pick("KGClim_KGClim_V1_historical_1981_2010")
        assert not sp.glass_hint.isHidden()
        assert not sp.start_edit.isEnabled() and not sp.end_edit.isEnabled()

        pick("AWGF_LST_ABI_CMG_005deg")
        assert not sp.glass_hint.isHidden()
        assert sp.start_edit.isEnabled()

        midx = sp.group_combo.findText("MODIS Terra")
        sp.group_combo.setCurrentIndex(midx)
        pick("MOD13Q1")
        assert sp.glass_hint.isHidden()
        assert sp.start_edit.isEnabled() and sp.end_edit.isEnabled()
    finally:
        window.close()


def test_search_panel_busy_button_fires_cancel(tmp_path, monkeypatch):
    """busy 时"检索"按钮不禁用、文字变"取消检索"，再点一次发出
    cancel_requested——v2.7 前按钮 busy 即禁用，多年日级 GLASS 查询根本
    无法停下（AWGF_LST_ABI_2km 四年 ≈1410 次目录是实坑）。"""
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        sp = window.search_panel
        sp.set_searching(True)
        assert sp.search_btn.isEnabled()
        assert sp.search_btn.text()
        fired = []
        sp.cancel_requested.connect(lambda: fired.append(True))
        sp._on_search_clicked()
        assert fired == [True]
        sp.set_searching(False)
        assert sp.search_prog.isHidden()
    finally:
        window.close()


def test_search_panel_progress_bar(tmp_path, monkeypatch):
    """GLASS 目录进度回调驱动进度条：n/m 与文件夹标签可见，结束后隐藏。"""
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        sp = window.search_panel
        sp.set_searching(True)
        sp.on_search_progress({"done": 3, "total": 10, "label": "2018/217"})
        assert not sp.search_prog.isHidden()
        assert sp.search_prog.value() == 3
        assert sp.search_prog.maximum() == 10
        assert "2018/217" in sp.search_prog.format()
        sp.on_search_finished()
        assert sp.search_prog.isHidden()
    finally:
        window.close()


def test_glass_batch_enqueues_without_login(tmp_path, monkeypatch):
    """全 GLASS 批次跳过 Earthdata 闸门直接入队；混入 NASA 条目则照旧
    先过登录闸（公开档案不需要凭据，NASA 数据需要）。"""
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        gate_calls = []
        monkeypatch.setattr(window, "_ensure_logged_in",
                            lambda: gate_calls.append(1) or False)
        added = []
        monkeypatch.setattr(
            window.engine, "add",
            lambda url, filename=None, size_hint=0: added.append(url))

        glass_row = {
            "url": "https://glass.hku.hk/archive/AGB/0.05D/"
                   "GLASS_AGB_5km_Y1992.tif",
            "filename": "GLASS_AGB_5km_Y1992.tif", "size_bytes": 0}
        nasa_row = {"url": "https://ladsweb.modaps.eosdis.nasa.gov/a.hdf",
                    "filename": "a.hdf", "size_bytes": 0}

        window._enqueue([glass_row])
        assert not gate_calls and added == [glass_row["url"]]

        window._enqueue([glass_row, nasa_row])
        assert len(gate_calls) == 1          # mixed batch asks for login once
        assert len(added) == 1               # gate said no -> nothing queued
    finally:
        window.close()
