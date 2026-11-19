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
    # 检索历史等 update_config 写盘路径也必须隔离——测试不得碰真实 ~/.d3ltool
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".d3ltool")
    monkeypatch.setattr(config, "CONFIG_FILE",
                        tmp_path / ".d3ltool" / "config.json")

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


def test_main_window_cancel_discards_late_results(tmp_path, monkeypatch):
    """取消=立即恢复+丢弃：点"取消检索"按钮立刻回到"检索"、busy 复位，
    迟到完成的 worker 结果不得再碰结果表（CMR 单请求无法中断，只能丢弃；
    GLASS 则由协作标志在 ≤1 次列表内真正停机）。"""
    import threading

    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        from d3ltool.search import SearchParams

        from d3ltool.gui import main_window as mw
        from d3ltool.i18n import tr as _tr

        gate = threading.Event()

        def fake_run(p, searcher=None, progress=None, cancelled=None):
            gate.wait(5)               # block like a slow CMR request
            return []

        monkeypatch.setattr(mw.search, "run_search", fake_run)
        window._do_search(SearchParams(short_name="MOD13Q1",
                                       start="2018-01-01", end="2018-01-02"))
        t = window._search_thread
        assert t is not None and t.isRunning()
        window._cancel_search()
        assert window._search_thread is None
        assert window.search_panel._busy is False
        assert window.search_panel.search_btn.text() == _tr("btn_search")
        gate.set()                     # the abandoned worker finishes late
        assert t.wait(5000)
        assert window.results_table.table.rowCount() == 0
        assert window._search_thread is None
    finally:
        window.close()


def test_search_panel_busy_pulse_for_cmr(tmp_path, monkeypatch):
    """CMR 检索的进度条复用：total<=0 是 busy 脉冲——条转不定式动画，
    提示行显示"正在查询 CMR：产品"；结束后条隐藏、提示行复位。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        sp = window.search_panel
        sp.on_search_progress({"done": 0, "total": 0, "label": "MOD13Q1"})
        assert not sp.search_prog.isHidden()
        assert (sp.search_prog.minimum(), sp.search_prog.maximum()) == (0, 0)
        assert "MOD13Q1" in sp.glass_hint.text()
        sp.set_searching(False)
        assert sp.search_prog.isHidden()
        assert sp.glass_hint.isHidden()
    finally:
        window.close()


def test_search_history_roundtrip(tmp_path, monkeypatch):
    """检索历史：发起即记录（失败重试也走历史）、去重连续相同、菜单重建
    与表单回填；持久化进 tmp 隔离的 config.json。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        import d3ltool.config as config

        from d3ltool.search import SearchParams

        sp = window.search_panel
        p1 = SearchParams(short_name="MOD13Q1", start="2018-01-01",
                          end="2018-01-02", tiles=["h28v05"], max_results=50)
        p2 = SearchParams(short_name="LAI_MODIS_250M", start="2018-08-01",
                          end="2018-08-31", tiles=["h28v05"], max_results=200)
        sp.record_history(p1)
        sp.record_history(p1)          # 与最新一条相同 → 不重复
        sp.record_history(p2)
        sp.record_history(p1)          # 再查 p1 → 回到最前
        hist = sp._load_history()
        assert [e["short_name"] for e in hist] == ["MOD13Q1", "LAI_MODIS_250M", "MOD13Q1"]
        assert config.load_config()["search_history"] == hist
        sp._rebuild_history_menu()
        texts = [a.text() for a in sp._history_menu.actions() if a.text()]
        # 3 条历史 + 底部「清除历史」（分隔符无文本被滤掉）
        assert len(texts) == 4 and "MOD13Q1" in texts[0]
        # 回填（不自动检索）：产品（含自定义补入）、日期、瓦片、上限
        sp._restore_history(hist[1])
        assert sp.current_short_name() == "LAI_MODIS_250M"
        assert sp.start_edit.date().toString("yyyy-MM-dd") == "2018-08-01"
        assert sp.end_edit.date().toString("yyyy-MM-dd") == "2018-08-31"
        assert sp.tile_edit.text() == "h28v05"
        assert sp.limit_spin.value() == 200
        # 空历史占位
        import d3ltool.gui.search_panel as spp

        monkeypatch.setattr(config, "load_config",
                            lambda: {**config.DEFAULTS, "search_history": []})
        sp._rebuild_history_menu()
        acts = sp._history_menu.actions()
        assert len(acts) == 1 and not acts[0].isEnabled()
        del spp
    finally:
        window.close()


def test_results_table_sort_and_filter(tmp_path, monkeypatch):
    """v2.8 结果表：列头排序（视觉行序 ≠ 源行序，UserRole 源行号保正确性）
    + 文件名过滤（隐藏行不进全选，入队/导出走源行映射）。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        from PySide6.QtCore import Qt

        rt = window.results_table
        granules = [{
            "url": f"https://x/{i}.hdf", "filename": f"G{i:02d}.hdf",
            "date": f"2018-01-{i:02d}", "tile": "h28v05",
            "size_mb": 20.0 - i, "size_bytes": 0, "product": "T",
        } for i in range(1, 4)]
        rt.populate(granules)
        # size 升序（18,19,20）→ 视觉第 0 行是 G03（源行 2）
        rt.table.sortItems(4)   # AscendingOrder by default indicator
        assert rt.table.item(0, 1).text() == "G03.hdf"
        check = rt.table.item(0, 0)
        assert check.data(Qt.ItemDataRole.UserRole) == 2
        # 先全不选清掉 populate 的默认全勾；过滤只留 G01（升序后视觉行 2）
        # → 行 0/1 隐藏；全选不碰隐藏行
        rt.select_none_btn.click()
        rt.filter_edit.setText("G01")
        assert rt.table.isRowHidden(0) and not rt.table.isRowHidden(2)
        rt.select_all_btn.click()
        assert rt.table.item(0, 0).checkState() != Qt.CheckState.Checked
        assert rt.table.item(2, 0).checkState() == Qt.CheckState.Checked
        # 入队走源行映射（直接取，不发信号）：勾上 G03 后源 granules[2]
        rt.filter_edit.setText("")
        rt.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        items = rt._checked_items()
        assert [it["filename"] for it in items] == ["G03.hdf", "G01.hdf"]
        assert items[0]["url"] == "https://x/3.hdf"
    finally:
        window.close()


def test_batch_dialog_and_wiring(tmp_path, monkeypatch):
    """GLASS 批量检索：批量按钮仅 GLASS 组显示；对话框勾选→确认带出 ids；
    线程走 glass.search_batch，部分失败进状态栏、结果照常入表。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        from PySide6.QtCore import Qt

        sp = window.search_panel
        assert sp.batch_btn.isHidden()          # 默认 MODIS 组 → 隐藏
        gidx = next(i for i in range(sp.group_combo.count())
                    if sp.group_combo.itemText(i) == "GLASS")
        sp.group_combo.setCurrentIndex(gidx)
        assert not sp.batch_btn.isHidden()
        # 对话框：勾选前两个变体（登记表序，核验排前）
        from d3ltool.gui.batch_dialog import BatchVariantDialog

        dlg = BatchVariantDialog(window)
        assert dlg.listw.count() >= 2
        dlg.listw.item(0).setCheckState(Qt.CheckState.Checked)
        dlg.listw.item(1).setCheckState(Qt.CheckState.Checked)
        ids = [str(dlg.listw.item(i).data(Qt.ItemDataRole.UserRole))
               for i in (0, 1)]
        dlg.batch_confirmed = ids
        assert dlg.selected_variants() == ids
        # 信号接线 + 线程批量执行（mock 引擎）
        import d3ltool.glass as glassmod

        seen = {}

        def fake_batch(vids, start, end, tiles=None, bbox=None,
                       max_results=200, progress=None, cancelled=None):
            seen.update(vids=vids, max_results=max_results)
            return ([{"url": "https://x/a.hdf", "filename": "a.hdf",
                      "date": "2018-08-05", "tile": "h28v05", "size_mb": 0.0,
                      "size_bytes": 0, "product": vids[0]}],
                    {vids[1]: "GlassError: boom"})

        monkeypatch.setattr(glassmod, "search_batch", fake_batch)
        window._do_batch_search(ids)
        t = window._search_thread
        assert t is not None and t.wait(8000)
        app.processEvents()                     # 送达排队信号
        assert seen["vids"] == ids
        assert window.results_table.table.rowCount() == 1
        assert "1 个变体失败" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_band_variant_hint(tmp_path, monkeypatch):
    """HiGLASS 带状变体的提示行：告诉用户需要 bbox/瓦片，日期可用。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        sp = window.search_panel
        sp._apply_catalog_choice("LAI_HR_LAI_V01", "")
        assert not sp.glass_hint.isHidden()
        assert "1°" in sp.glass_hint.text()
        assert sp.start_edit.isEnabled()
        assert sp.end_edit.isEnabled()
    finally:
        window.close()


def test_search_history_clear(tmp_path, monkeypatch):
    """「历史」菜单底部有「清除历史」：置空并落盘，下次弹出显示占位。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        import d3ltool.config as config

        from d3ltool.search import SearchParams

        from d3ltool.i18n import tr as _tr

        sp = window.search_panel
        sp.record_history(SearchParams(short_name="MOD13Q1",
                                       start="2018-01-01", end="2018-01-02"))
        sp._rebuild_history_menu()
        acts = sp._history_menu.actions()
        assert acts[-1].text() == _tr("history_clear")
        acts[-1].trigger()
        assert config.load_config()["search_history"] == []
        sp._rebuild_history_menu()
        acts = sp._history_menu.actions()
        assert len(acts) == 1 and not acts[0].isEnabled()
    finally:
        window.close()


def test_terminal_launcher(tmp_path, monkeypatch):
    """帮助菜单终端启动器：菜单项存在；Windows 分支参数正确
    （wt 优先 + cmd 回退，命令经 cmd /k 携带）；opencode 缺失时只提示。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        import sys as _sys
        import subprocess as _subprocess

        # 终端启动器测试在 CI 三平台都要跑：显式钉到 win32 分支，
        # 并补上 Linux/macOS subprocess 缺失的 CREATE_NEW_CONSOLE
        monkeypatch.setattr(_sys, "platform", "win32")
        monkeypatch.setattr(_subprocess, "CREATE_NEW_CONSOLE", 0,
                            raising=False)
        import shutil as _shutil

        from d3ltool.i18n import tr as _tr

        menu = [a for a in window.menuBar().actions()
                if a.text() == _tr("menu_help")][0].menu()
        texts = [a.text() for a in menu.actions()]
        assert _tr("act_open_terminal") in texts
        assert _tr("act_open_opencode") in texts

        spawned = []
        monkeypatch.setattr(_subprocess, "Popen",
                            lambda args, **kw: spawned.append(args))
        monkeypatch.setattr(_shutil, "which",
                            lambda name: r"C:\wt.exe" if name == "wt" else None)
        window._open_terminal()
        assert spawned and spawned[0][0] == r"C:\wt.exe"
        assert str(tmp_path / "downloads") in " ".join(spawned[0])
        assert spawned[0][-1] == "cmd"
        spawned.clear()
        monkeypatch.setattr(_shutil, "which",
                            lambda name: (r"C:\wt.exe" if name == "wt" else
                                          r"C:\oc\opencode.exe"
                                          if name == "opencode" else None))
        window._open_terminal(True)
        assert spawned[0][0] == r"C:\wt.exe"
        assert spawned[0][-3:] == ["cmd", "/k", "opencode"]
        # 项目级 skill 随启动自动安装（下载目录/.agents/skills/，非全局）
        assert (tmp_path / "downloads" / ".agents" / "skills" / "d3ltool"
                / "SKILL.md").is_file()
        # wt 不存在 → cmd /k 回退（opencode 需在场，否则触发防呆提示）
        monkeypatch.setattr(_shutil, "which",
                            lambda name: (r"C:\oc\opencode.exe"
                                          if name == "opencode" else None))
        spawned.clear()
        window._open_terminal(True)
        assert spawned[0][:2] == ["cmd", "/k"]
        assert spawned[0][2].endswith("&& opencode")
        # opencode 未安装 → 状态栏提示、不弹窗
        monkeypatch.setattr(_shutil, "which", lambda name: None)
        spawned.clear()
        window.statusBar().clearMessage()
        window._open_terminal(True)
        assert "opencode" in window.statusBar().currentMessage()
        assert not spawned
    finally:
        window.close()


def test_terminal_shell_choices(tmp_path, monkeypatch):
    """设置对话框的「终端」选项：pwsh/powershell 分支生成对应命令行
    （Set-Location + -NoExit），wt 存在时包进 Windows Terminal。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        import sys as _sys
        import subprocess as _subprocess

        # 终端启动器测试在 CI 三平台都要跑：显式钉到 win32 分支，
        # 并补上 Linux/macOS subprocess 缺失的 CREATE_NEW_CONSOLE
        monkeypatch.setattr(_sys, "platform", "win32")
        monkeypatch.setattr(_subprocess, "CREATE_NEW_CONSOLE", 0,
                            raising=False)
        import shutil as _shutil

        from d3ltool.gui.settings_dialog import SettingsDialog

        spawned = []
        monkeypatch.setattr(_subprocess, "Popen",
                            lambda args, **kw: spawned.append(args))
        monkeypatch.setattr(_shutil, "which",
                            lambda name: (r"C:\wt.exe" if name == "wt" else
                                          r"C:\oc\opencode.exe"
                                          if name == "opencode" else None))
        # pwsh（LTS）：wt 路径无分号——cd 由 wt -d 承担，命令单 token
        window.config["terminal_shell"] = "pwsh"
        window._open_terminal(True)
        assert spawned[-1][0] == r"C:\wt.exe"
        assert spawned[-1][3] == "pwsh" and "-NoExit" in spawned[-1]
        assert spawned[-1][-1] == "opencode"
        # wt 分号坑：链里不得出现分号（banner 已撤出启动器，链即单命令）
        assert not any(";" in str(a) for a in spawned[-1])
        # Windows PowerShell 5.1：exe 为 powershell
        window.config["terminal_shell"] = "powershell"
        window._open_terminal(False)
        assert spawned[-1][3] == "powershell"
        # 无 wt → 直接起 shell 进程（重置回 pwsh）
        monkeypatch.setattr(_shutil, "which", lambda name: None)
        window.config["terminal_shell"] = "pwsh"
        window._open_terminal(False)
        assert spawned[-1][0] == "pwsh" and spawned[-1][1] == "-NoExit"
        assert spawned[-1][-1].endswith("'")   # Set-Location 定位，无命令
        # 设置对话框保存 terminal_shell
        dlg = SettingsDialog(window, config=dict(window.config), on_save=None)
        idx = next(i for i in range(dlg.term_combo.count())
                   if dlg.term_combo.itemData(i) == "pwsh")
        dlg.term_combo.setCurrentIndex(idx)
        values = {}
        dlg._on_save = lambda v: values.update(v)
        dlg._save()
        assert values["terminal_shell"] == "pwsh"
    finally:
        window.close()


def test_terminal_auto_prefers_powershell(tmp_path, monkeypatch):
    """auto 解析顺序：pwsh（LTS）→ Windows PowerShell → CMD——默认即为
    PowerShell，没装 pwsh 的机器自动退 5.1。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        import sys as _sys
        import subprocess as _subprocess

        # 终端启动器测试在 CI 三平台都要跑：显式钉到 win32 分支，
        # 并补上 Linux/macOS subprocess 缺失的 CREATE_NEW_CONSOLE
        monkeypatch.setattr(_sys, "platform", "win32")
        monkeypatch.setattr(_subprocess, "CREATE_NEW_CONSOLE", 0,
                            raising=False)
        import shutil as _shutil

        spawned = []
        monkeypatch.setattr(_subprocess, "Popen",
                            lambda args, **kw: spawned.append(args))
        # 装了 pwsh → auto 用 pwsh
        monkeypatch.setattr(_shutil, "which",
                            lambda name: (r"C:\wt.exe" if name == "wt" else
                                          r"C:\ps7\pwsh.exe"
                                          if name == "pwsh" else None))
        window.config["terminal_shell"] = "auto"
        window._open_terminal(False)
        assert spawned[-1][3] == "pwsh"
        # 没装 pwsh → 退 Windows PowerShell 5.1
        monkeypatch.setattr(_shutil, "which",
                            lambda name: (r"C:\wt.exe" if name == "wt" else
                                          r"C:\ps5\powershell.exe"
                                          if name == "powershell" else None))
        window._open_terminal(False)
        assert spawned[-1][3] == "powershell"
        # PowerShell 系也没有 → CMD
        monkeypatch.setattr(_shutil, "which",
                            lambda name: (r"C:\wt.exe" if name == "wt" else None))
        window._open_terminal(False)
        assert spawned[-1][3] == "cmd"
    finally:
        window.close()


def test_results_check_header_indicator(tmp_path, monkeypatch):
    """排序指示器不落在勾选列（v2.8 回归：36px 列里「选」+箭头裁成乱码）：
    初始给文件名列；点勾选列头弹回文件名列。"""
    pytest.importorskip("PySide6")
    app, window = _make_window(tmp_path, monkeypatch)
    try:
        from PySide6.QtCore import Qt

        rt = window.results_table
        rt.populate([])
        header = rt.table.horizontalHeader()
        assert header.sortIndicatorSection() == 1          # COL_NAME
        header.sectionClicked.emit(0)                      # COL_CHECK
        assert header.sortIndicatorSection() == 1
        assert rt.table.columnWidth(0) == 48
    finally:
        window.close()
