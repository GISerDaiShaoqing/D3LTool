# -*- coding: utf-8 -*-
"""Left search panel: product / time / area + search button.

The panel content lives inside a QScrollArea: on short screens (e.g. a
maximized 125%-DPI laptop) the panel's natural minimum height exceeds the
available space, and without scrolling the box layouts overflow and widgets
overlap each other.
"""

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDateEdit, QFormLayout, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QProgressBar, QPushButton, QScrollArea,
                               QSpinBox, QVBoxLayout, QWidget)

from .. import glass, i18n, products, search
from .tile_map import TileMap

CUSTOM_LABEL_ZH = "自定义产品 / Custom"
BIG_QUERY_DIR_LIMIT = 200   # beyond this the hint warns about listing time


def _search_cost_estimate(v: dict, start_q, end_q):
    """Approximate directory-listing count for a GLASS date range — one
    listing per composite (or per year for cadence-less adaptive variants).
    Daily cadences over multiple years easily top thousands of listings
    (e.g. AWGF_LST_ABI_2km 2017-01-01..2020-11-10 = 1410), so the hint
    warns the user up front and they can cancel mid-search."""
    from datetime import date as _date

    s0 = _date(start_q.year(), start_q.month(), start_q.day())
    s1 = _date(end_q.year(), end_q.month(), end_q.day())
    sy, ey = v.get("start_year"), v.get("end_year")
    if sy and ey and not (sy <= s1.year and ey >= s0.year):
        return None    # entirely outside coverage — let search() report it
    try:
        if v.get("cadence_days"):
            n = len(glass.doys(v, s0.isoformat(), s1.isoformat()))
        else:
            n = sum(1 for y in range(s0.year, s1.year + 1))
    except glass.GlassError:
        return None
    if n <= BIG_QUERY_DIR_LIMIT:
        return None
    mins = max(int(n * 2 / 60 + 0.5), 1)   # ~1.2 s spacing + request time
    return i18n.tr("glass_hint_bigquery", n=n, mins=mins)


class SearchPanel(QWidget):
    search_requested = Signal(object)   # SearchParams
    cancel_requested = Signal()         # user wants the running search stopped

    def __init__(self, parent=None):
        super().__init__(parent)
        self._custom_mode = False
        self._busy = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        body.setObjectName("searchPanelBody")
        root = QVBoxLayout(body)
        root.setContentsMargins(9, 9, 9, 9)

        scroll = QScrollArea()
        scroll.setObjectName("searchPanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        outer.addWidget(scroll)

        # ---- product group
        prod_box = QGroupBox(i18n.tr("group_product"))
        form = QFormLayout(prod_box)
        self.group_combo = QComboBox()
        for name, _items in products.GROUPS:
            self.group_combo.addItem(name)
        self.group_combo.addItem(CUSTOM_LABEL_ZH)
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)

        self.product_combo = QComboBox()
        self.product_combo.setEditable(True)
        self.product_combo.currentIndexChanged.connect(self._on_product_changed)
        self.product_combo.lineEdit().textEdited.connect(
            lambda _t: self._update_glass_hint())

        product_row = QHBoxLayout()
        product_row.addWidget(self.product_combo, 1)
        self.catalog_btn = QPushButton(i18n.tr("btn_catalog"))
        self.catalog_btn.setToolTip(i18n.tr("catalog_hint"))
        self.catalog_btn.clicked.connect(self._open_catalog)
        self._catalog_dialog = None   # created on demand
        product_row.addWidget(self.catalog_btn)

        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText(i18n.tr("label_version_hint"))

        form.addRow(i18n.tr("label_product_group"), self.group_combo)
        form.addRow(i18n.tr("label_product"), product_row)
        form.addRow(i18n.tr("label_version"), self.version_edit)
        root.addWidget(prod_box)

        # ---- time group
        time_box = QGroupBox(i18n.tr("group_time"))
        tform = QFormLayout(time_box)
        today = QDate.currentDate()
        self.start_edit = QDateEdit(today.addDays(-15))
        self.end_edit = QDateEdit(today)
        for w in (self.start_edit, self.end_edit):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
        tform.addRow(i18n.tr("label_start"), self.start_edit)
        tform.addRow(i18n.tr("label_end"), self.end_edit)
        root.addWidget(time_box)

        # GLASS layout hint (static collection / global CMG) — hidden for
        # non-GLASS products; flat variants also disable the date fields.
        self.glass_hint = QLabel("")
        self.glass_hint.setWordWrap(True)
        self.glass_hint.setObjectName("glassHint")
        self.glass_hint.setStyleSheet("color: #888;")
        self.glass_hint.hide()
        root.addWidget(self.glass_hint)

        # per-directory progress for GLASS archive searches (they list real
        # folders — multi-year daily cadences mean thousands of listings)
        self.search_prog = QProgressBar()
        self.search_prog.hide()
        root.addWidget(self.search_prog)

        # ---- area group
        area_box = QGroupBox(i18n.tr("group_area"))
        agrid = QGridLayout(area_box)

        self.tile_edit = QLineEdit()
        self.tile_edit.setPlaceholderText("h04v03, h26v05")
        self.tile_clear_btn = QPushButton(i18n.tr("btn_clear_tiles"))
        agrid.addWidget(QLabel(i18n.tr("label_tile")), 0, 0)
        agrid.addWidget(self.tile_edit, 0, 1)
        agrid.addWidget(self.tile_clear_btn, 0, 2)
        self.tile_clear_btn.clicked.connect(self._clear_tiles)

        self.tile_map = TileMap()
        self.tile_map.tiles_changed.connect(self._on_map_changed)
        agrid.addWidget(self.tile_map, 1, 0, 1, 3, Qt.AlignmentFlag.AlignHCenter)

        locate_row = QHBoxLayout()
        self.lon_edit = QLineEdit()
        self.lon_edit.setPlaceholderText("116.4")
        self.lat_edit = QLineEdit()
        self.lat_edit.setPlaceholderText("39.9")
        locate_btn = QPushButton(i18n.tr("locate_btn"))
        locate_btn.clicked.connect(self._on_locate)
        locate_row.addWidget(QLabel("Lon"))
        locate_row.addWidget(self.lon_edit)
        locate_row.addWidget(QLabel("Lat"))
        locate_row.addWidget(self.lat_edit)
        locate_row.addWidget(locate_btn)
        agrid.addLayout(locate_row, 2, 0, 1, 3)

        self.bbox_edit = QLineEdit()
        self.bbox_edit.setPlaceholderText("100, 20, 120, 40")
        bbox_label = QLabel(i18n.tr("label_bbox"))
        bbox_label.setToolTip(i18n.tr("label_bbox_tip"))
        agrid.addWidget(bbox_label, 3, 0, 1, 3)
        agrid.addWidget(self.bbox_edit, 4, 0, 1, 3)
        root.addWidget(area_box)
        root.addStretch(1)

        # ---- options + search button: pinned below the scroll area so the
        # primary action stays visible even when the cards need scrolling
        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel(i18n.tr("label_limit")))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 2000)
        self.limit_spin.setValue(200)
        opt_row.addWidget(self.limit_spin)
        opt_row.addStretch(1)
        outer.addLayout(opt_row)

        self.search_btn = QPushButton(i18n.tr("btn_search"))
        self.search_btn.setObjectName("accentButton")
        self.search_btn.setMinimumHeight(44)
        self.search_btn.clicked.connect(self._on_search_clicked)
        outer.addWidget(self.search_btn)

        self._on_group_changed(0)

    # ------------------------------------------------------------------ slots

    def _open_catalog(self):
        from .product_catalog import ProductCatalogDialog

        if self._catalog_dialog is None:
            self._catalog_dialog = ProductCatalogDialog(self)
            self._catalog_dialog.product_selected.connect(self._apply_catalog_choice)
        self._catalog_dialog.show()
        self._catalog_dialog.raise_()
        self._catalog_dialog.activateWindow()

    def _apply_catalog_choice(self, short_name: str, version: str) -> None:
        """Fill product + version from the catalog (also used programmatically)."""
        idx = self.product_combo.findData(short_name)
        if idx < 0:
            self.product_combo.blockSignals(True)
            self.product_combo.addItem(short_name, userData=short_name)
            self.product_combo.blockSignals(False)
            idx = self.product_combo.findData(short_name)
        self.product_combo.setCurrentIndex(idx)
        self._on_product_changed(idx)
        if version:
            self.version_edit.setText(version)

    def _on_group_changed(self, index):
        text = self.group_combo.currentText()
        self._custom_mode = text == CUSTOM_LABEL_ZH
        self.product_combo.clear()
        if self._custom_mode:
            self.version_edit.clear()
            return
        for name, items in products.GROUPS:
            if name == text:
                for short, version, desc_zh, desc_en in items:
                    self.product_combo.addItem(short, userData=short)
                break

    def _on_product_changed(self, index):
        short = self.current_short_name()
        self.version_edit.setText(products.version_hint(short))
        self._update_glass_hint()

    def _update_glass_hint(self):
        """GLASS variant-dependent affordances: static collections (flat)
        have no time dimension — disable the date fields and say so; global
        CMG products never carry tile fragments — tell the user tiles are
        pointless there."""
        hint = ""
        flat = False
        try:
            if glass.is_glass_variant(self.current_short_name()):
                v = glass.get_variant(self.current_short_name())
                if v.get("layout") == "flat":
                    flat = True
                    hint = i18n.tr("glass_hint_flat")
                elif not v.get("tiled", True):
                    hint = i18n.tr("glass_hint_cmg")
                est = _search_cost_estimate(v, self.start_edit.date(),
                                            self.end_edit.date())
                if est:
                    hint = (hint + "\n" if hint else "") + est
        except glass.GlassError:
            pass   # not a GLASS id (or malformed) — no hint, dates stay on
        self.glass_hint.setText(hint)
        self.glass_hint.setVisible(bool(hint))
        for w in (self.start_edit, self.end_edit):
            w.setEnabled(not flat)

    def _on_map_changed(self):
        self.tile_edit.setText(", ".join(self.tile_map.selected_tiles()))

    def _clear_tiles(self):
        """「清除瓦片」一键清空：地图选择与手输的瓦片列表一起复位
        （原来只能逐个点击已选瓦片取消——能取消但不可见）。"""
        self.tile_map.clear_selection()
        self.tile_edit.clear()

    def _on_locate(self):
        try:
            lon = float(self.lon_edit.text())
            lat = float(self.lat_edit.text())
        except ValueError:
            return
        self.tile_map.select_lonlat(lon, lat)
        self.tile_edit.setText(", ".join(self.tile_map.selected_tiles()))

    def _on_search_clicked(self):
        if self._busy:                       # the button doubles as "取消检索"
            self.cancel_requested.emit()
            return
        params = self.build_params()
        if params is None:
            return
        self.search_requested.emit(params)

    # ----------------------------------------------------------------- helpers

    def current_short_name(self) -> str:
        data = self.product_combo.currentData()
        if data:
            return str(data)
        return self.product_combo.currentText().strip().upper()

    def set_searching(self, busy: bool) -> None:
        """While busy the button stays ENABLED and reads "取消检索" — a second
        click emits cancel_requested (before v2.7 it was disabled, so a
        multi-year GLASS query could not be stopped at all)."""
        self._busy = busy
        self.search_btn.setText(i18n.tr("btn_cancel_search") if busy
                                else i18n.tr("btn_search"))
        if not busy:
            self.search_prog.hide()

    def on_search_progress(self, payload: dict) -> None:
        """GLASS directory-listing progress: n/m with the folder label on the
        hint line."""
        total = int(payload.get("total") or 0)
        self.search_prog.setRange(0, max(total, 1))
        self.search_prog.setValue(int(payload.get("done") or 0))
        self.search_prog.setFormat(
            f"{payload.get('label', '')}  ·  %v / %m " +
            i18n.tr("glass_prog_dirs"))
        self.search_prog.show()

    def on_search_finished(self) -> None:
        """Hide the GLASS directory-listing progress bar (also auto-hidden
        by set_searching(False))."""
        self.search_prog.hide()

    def build_params(self):
        try:
            tiles = search.parse_tiles(self.tile_edit.text())
            bbox = search.parse_bbox(self.bbox_edit.text())
        except ValueError as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, i18n.tr("err_title"), str(exc))
            return None
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")
        return search.SearchParams(
            short_name=self.current_short_name(),
            start=start,
            end=end,
            version=self.version_edit.text().strip(),
            tiles=tiles,
            bbox=bbox,
            max_results=self.limit_spin.value(),
        )
