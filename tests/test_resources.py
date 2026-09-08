# -*- coding: utf-8 -*-
"""Bundled resources: icon files, donation QR, menus kept from v1.0."""

from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "d3ltool" / "resources"


def test_icon_files_exist():
    assert (RES / "D3L.ico").exists()
    assert (RES / "D3L_original.jpg").exists()
    assert (RES / "alipay.gif").exists()
    # optimized ico must carry modern sizes, not just 32x32 like v1
    try:
        from PIL import Image
    except ImportError:
        return
    ico = Image.open(RES / "D3L.ico")
    sizes = ico.info.get("sizes", set())
    assert (256, 256) in sizes and (16, 16) in sizes and (32, 32) in sizes


def test_window_icon_loads_offscreen(monkeypatch):
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])

    icon = QIcon(str(RES / "D3L.ico"))
    assert not icon.isNull()
    assert not icon.pixmap(32, 32).isNull()


def test_legacy_menu_links_present():
    from d3ltool.gui.main_window import RS_URLS, SITE_URLS

    # personal sites: custom domain (verified 2026-09)
    assert SITE_URLS["site_home"] == "https://gisersqdai.top/D3LTool/"
    assert SITE_URLS["site_blog"] == "https://gisersqdai.top/"
    assert "pan.baidu.com" in SITE_URLS["site_baidupan"]
    # all seven resource links kept, on their current (2026-09) domains
    assert len(RS_URLS) == 7
    urls = " ".join(url for _, url in RS_URLS)
    assert "cnblogs.com/enviidl" in urls          # ENVI blog moved from sina
    assert "cpeos.org.cn" in urls                 # replaces hijacked rscloudmart.com
    assert "chinageoss.cn" in urls
    assert "gscloud.cn" in urls
    assert "nrscc.most.cn" in urls                # moved from nrscc.gov.cn
    assert "usgs.gov/landsat-missions" in urls    # landsat.usgs.gov 301s here
    assert "cresda.cn" in urls                    # moved from cresda.com
    # the hijacked domain must never come back
    assert "rscloudmart.com" not in urls


def test_about_text_mentions_glm_and_earthaccess():
    from d3ltool import i18n

    i18n.set_language("zh")
    zh = i18n.tr("about_text")
    assert "GLM-5.3-Flash" in zh
    assert "v2.0" in zh
    assert "earthaccess" in zh
    # GLM-5.3-Flash comes right after v2.0
    assert zh.index("v2.0") < zh.index("GLM-5.3-Flash")
    assert "earthaccess" in zh[:zh.index("v2.0")]
    i18n.set_language("en")
    en = i18n.tr("about_text")
    assert "GLM-5.3-Flash" in en and "earthaccess" in en
    i18n.set_language("zh")
