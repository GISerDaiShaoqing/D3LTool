# -*- coding: utf-8 -*-
"""Product catalog dialog: grouping, filtering, and applying a product."""

import pytest


def _make_app_and_panel(tmp_path, monkeypatch):
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
    return app, window, window.search_panel


def test_catalog_lists_all_groups_and_products(tmp_path, monkeypatch):
    _app, _window, sp = _make_app_and_panel(tmp_path, monkeypatch)

    from d3ltool import products
    from d3ltool.gui.product_catalog import ProductCatalogDialog

    dlg = ProductCatalogDialog(sp)
    # "All" group selected by default: every curated product visible
    assert dlg.table.rowCount() == sum(len(items) for _g, items in products.GROUPS)
    # switch to the VIIRS group: only VIIRS rows
    names = [dlg.group_list.item(i).text() for i in range(dlg.group_list.count())]
    viirs_idx = next(i for i, t in enumerate(names) if "VIIRS" in t)
    dlg.group_list.setCurrentRow(viirs_idx)
    texts = {dlg.table.item(r, 0).text() for r in range(dlg.table.rowCount())}
    assert texts == {"VIIRS"}
    dlg.close()


def test_filter_and_apply_product_to_panel(tmp_path, monkeypatch):
    _app, _window, sp = _make_app_and_panel(tmp_path, monkeypatch)

    from d3ltool.gui.product_catalog import ProductCatalogDialog

    dlg = ProductCatalogDialog(sp)
    dlg.product_selected.connect(sp._apply_catalog_choice)   # wired like the real app
    dlg.filter_edit.setText("夜光")
    assert dlg.table.rowCount() >= 1            # VNP46A1/A2 mention 夜光

    dlg.apply_product("VNP46A1")
    # the dialog accepted itself and the panel got the product + version hint
    assert sp.product_combo.currentText() == "VNP46A1"
    assert sp.version_edit.text() == "2"

    # a product from another group can also be applied the same way
    dlg2 = ProductCatalogDialog(sp)
    dlg2.product_selected.connect(sp._apply_catalog_choice)
    dlg2.apply_product("M2T1NXSLV")
    assert sp.product_combo.currentText() == "M2T1NXSLV"
    assert sp.version_edit.text() == "5.12.4"
    dlg2.close()
