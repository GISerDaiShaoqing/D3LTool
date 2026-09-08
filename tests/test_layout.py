# -*- coding: utf-8 -*-
"""Regression test: on short windows the search panel must scroll, never
overlap (the tile map used to collide with the locate row / search button)."""

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
