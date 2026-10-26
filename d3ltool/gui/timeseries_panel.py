# -*- coding: utf-8 -*-
"""Time-series drawer panel: pixel values of any LAADS product layer.

The data logic lives in d3ltool.timeseries (pure Python): pixel values are
sampled straight from LAADS' own OPeNDAP service — the same servers as the
downloader, no third-party subset service involved. This module is Qt only:
a form (product / layer / dates / latitude / longitude), a QtCharts line
chart, CSV export, and one worker thread at a time.
"""

import csv
import threading

from PySide6.QtCharts import (QChart, QChartView, QDateTimeAxis, QLineSeries,
                              QValueAxis)
from PySide6.QtCore import QDate, QDateTime, QMargins, Qt, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QCompleter, QDateEdit, QFileDialog,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

from .. import i18n
from .. import timeseries as tsl

# popular starting points; any LAADS product short_name can be typed too
SEED_PRODUCTS = ["MOD13Q1", "MOD13A2", "MYD13Q1", "MOD11A2", "MYD11A2",
                 "MOD15A2H", "MCD43A4", "MOD09GA", "MOD17A2H",
                 "MCD64A1", "MOD10A2", "VNP46A1", "VNP46A2", "VJ102IMG",
                 "M2T1NXSLV", "M2TMNXSLV"]


class _ThreadAdapter:
    """Bridges data-layer progress calls to the thread's Qt signals."""

    def __init__(self, thread):
        self._thread = thread

    def stage(self, key, **kw):
        self._thread.stage.emit(i18n.tr(key, **kw))

    def layers(self, layers):
        self._thread.layers_ready.emit(layers)


class TimeSeriesThread(QThread):
    """The LAADS OPeNDAP pipeline (search -> probe -> sample) off the GUI
    thread; one job at a time, stoppable between granules."""

    layers_ready = Signal(list)          # [{layer, description, ...}]
    series_ready = Signal(list)          # [source_label, layer, points]
    stage = Signal(str)                  # human-readable progress text
    failed = Signal(str)
    finished_turn = Signal()

    def __init__(self, args, parent=None):
        super().__init__(parent)
        self._args = args
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            source, layer, points = tsl.run_point_series(
                lat=self._args["lat"], lon=self._args["lon"],
                product=self._args["product"],
                start=self._args["start"], end=self._args["end"],
                layer_hint=self._args.get("layer_hint", ""),
                should_stop=self._stop_event.is_set,
                adapter=_ThreadAdapter(self))
            if self._stop_event.is_set():
                raise tsl.StopRequested("stopped by user")
            self.series_ready.emit([source, layer, points])
        except tsl.StopRequested:
            pass
        except Exception as exc:      # noqa: BLE001 — the panel must not die
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished_turn.emit()


class TimeSeriesPanel(QWidget):
    """Content of the right-edge '时间序列' drawer."""

    hide_requested = Signal()         # the ✕ button; the drawer decides

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tsPanel")
        self._thread = None
        self.last_points = None       # [(iso_date, value)] after a plot
        self._meta = None             # context of the last plot (for export)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(6)

        # ---------------- header row (same chrome style as AgentPanel)
        header = QHBoxLayout()
        title = QLabel(i18n.tr("tab_ts"))
        title.setObjectName("agentTitle")
        self.hide_btn = QPushButton("✕")
        self.hide_btn.setObjectName("agentHeaderBtn")
        self.hide_btn.setToolTip(i18n.tr("agent_hide"))
        self.hide_btn.clicked.connect(self.hide_requested.emit)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.hide_btn)
        root.addLayout(header)

        # ---------------- form
        self.product_combo = QComboBox()
        self.product_combo.setObjectName("tsProduct")
        self.product_combo.setEditable(True)
        self.product_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = QCompleter(SEED_PRODUCTS, self.product_combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.product_combo.setCompleter(completer)
        for name in SEED_PRODUCTS:
            self.product_combo.addItem(name)
        self.product_combo.setCurrentText("")
        self.product_combo.lineEdit().setPlaceholderText(
            i18n.tr("ts_product_ph"))
        root.addWidget(self.product_combo)

        layer_row = QHBoxLayout()
        layer_label = QLabel(i18n.tr("ts_layer"))
        self.layer_combo = QComboBox()
        self.layer_combo.setObjectName("tsLayer")
        layer_row.addWidget(layer_label)
        layer_row.addWidget(self.layer_combo, 1)
        root.addLayout(layer_row)

        dates_row = QHBoxLayout()
        dates_row.addWidget(QLabel(i18n.tr("label_start")))
        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_edit.setDate(QDate.currentDate().addDays(-365))
        dates_row.addWidget(self.start_edit, 1)
        dates_row.addWidget(QLabel(i18n.tr("label_end")))
        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_edit.setDate(QDate.currentDate())
        dates_row.addWidget(self.end_edit, 1)
        root.addLayout(dates_row)

        coord_row = QHBoxLayout()
        self.lat_edit = QLineEdit()
        self.lat_edit.setPlaceholderText(i18n.tr("ts_lat_ph"))
        self.lon_edit = QLineEdit()
        self.lon_edit.setPlaceholderText(i18n.tr("ts_lon_ph"))
        coord_row.addWidget(QLabel(i18n.tr("ts_lat")))
        coord_row.addWidget(self.lat_edit, 1)
        coord_row.addWidget(QLabel(i18n.tr("ts_lon")))
        coord_row.addWidget(self.lon_edit, 1)
        root.addLayout(coord_row)

        btn_row = QHBoxLayout()
        self.plot_btn = QPushButton(i18n.tr("ts_plot"))
        self.plot_btn.setObjectName("accentButton")
        self.plot_btn.clicked.connect(self._plot)
        self.stop_btn = QPushButton(i18n.tr("agent_stop"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        self.export_btn = QPushButton(i18n.tr("ts_export"))
        self.export_btn.clicked.connect(self._export)
        self.clear_btn = QPushButton(i18n.tr("ts_clear"))
        self.clear_btn.clicked.connect(self._clear_chart)
        btn_row.addWidget(self.plot_btn, 1)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.clear_btn)
        root.addLayout(btn_row)

        self.status_label = QLabel(i18n.tr("ts_api_note"))
        self.status_label.setObjectName("tsStatus")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        # ---------------- chart
        self.chart = QChart()
        self.chart.legend().hide()
        self.chart.setBackgroundVisible(False)
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        self.chart_view = QChartView(self.chart)
        self.chart_view.setObjectName("tsChart")
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(160)
        root.addWidget(self.chart_view, 1)

    # ------------------------------------------------------------- helpers

    def _status(self, text, error=False):
        self.status_label.setProperty("state", "error" if error else "ok")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.setText(text)

    # ---------------------------------------------------------------- plot

    def _plot(self):
        if self._thread is not None and self._thread.isRunning():
            return
        try:
            lat = float(self.lat_edit.text().strip())
            lon = float(self.lon_edit.text().strip())
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                raise ValueError("lat/lon out of range")
        except ValueError:
            self._status(i18n.tr("ts_bad_coords"), error=True)
            return
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")
        if start > end:
            self._status(i18n.tr("ts_bad_dates"), error=True)
            return
        product = self._typed_product()
        if not product:
            self._status(i18n.tr("ts_need_fields",
                                 fields=i18n.tr("ts_field_product")),
                         error=True)
            return
        layer_hint = self.layer_combo.currentData() or \
            self.layer_combo.currentText()

        self.plot_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._status(i18n.tr("ts_stage_search"))
        self._thread = TimeSeriesThread({
            "lat": lat, "lon": lon, "product": product,
            "layer_hint": layer_hint, "start": start, "end": end,
        }, parent=self)
        self._thread.layers_ready.connect(self._apply_layers)
        self._thread.series_ready.connect(self._on_series_ready)
        self._thread.stage.connect(self._status)
        self._thread.failed.connect(self._on_failed)
        self._thread.finished_turn.connect(self._on_finished)
        self._thread.start()

    def _typed_product(self):
        text = self.product_combo.currentText().strip()
        if not text:
            return ""
        return text.split()[0]        # drop any decoration the user typed

    def _stop(self):
        if self._thread is not None:
            self._thread.stop()

    # ------------------------------------------------------- thread slots

    def _apply_layers(self, layers):
        current = self.layer_combo.currentData()
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for entry in layers:
            name = str(entry.get("layer", ""))
            if not name:
                continue
            desc = str(entry.get("description", "") or "")
            label = f"{name} — {desc}" if desc else name
            self.layer_combo.addItem(label, name)
        self.layer_combo.blockSignals(False)
        if current:
            index = self.layer_combo.findData(current)
            if index >= 0:
                self.layer_combo.setCurrentIndex(index)

    def _on_series_ready(self, payload):
        source, layer, points = payload
        self.render_points(points)
        self._meta = {
            "source": source, "layer": layer,
            "product": self._typed_product(),
            "lat": self.lat_edit.text().strip(),
            "lon": self.lon_edit.text().strip(),
            "start": self.start_edit.date().toString("yyyy-MM-dd"),
            "end": self.end_edit.date().toString("yyyy-MM-dd"),
        }
        if points:
            self._status(i18n.tr(
                "ts_done", n=len(points), source=source, layer=layer,
                start=points[0][0], end=points[-1][0]))
        else:
            self._status(i18n.tr("ts_no_data"), error=True)

    def show_external_series(self, points, meta):
        """Render a series produced elsewhere (the AI assistant's
        point_timeseries/plot_timeseries tools) and record its context
        for the status line and CSV export."""
        self.render_points(points)
        self._meta = dict(meta)
        if points:
            self._status(i18n.tr(
                "ts_done", n=len(points), source=meta.get("source", ""),
                layer=meta.get("layer", ""),
                start=points[0][0], end=points[-1][0]))
        else:
            self._status(i18n.tr("ts_no_data"), error=True)

    def _on_failed(self, message):
        self._status(i18n.tr("ts_failed", reason=message), error=True)

    def _on_finished(self):
        if self._thread is not None:
            self._thread.wait(2000)
        self._thread = None
        self.plot_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # -------------------------------------------------------------- export

    def _ask_save_path(self):
        """Dialog seam (tests replace this)."""
        meta = self._meta or {}
        suggested = "timeseries.csv"
        if meta.get("product"):
            suggested = (f"{meta['product']}_{meta.get('layer', 'series')}"
                         f"_{meta.get('lat', '')}_{meta.get('lon', '')}.csv")
        path, _filter = QFileDialog.getSaveFileName(
            self, i18n.tr("ts_export"), suggested, "CSV (*.csv)")
        return path

    def _export(self):
        if not self.last_points:
            self._status(i18n.tr("ts_nothing"), error=True)
            return
        path = self._ask_save_path()
        if not path:
            return
        self.write_csv(path)
        self._status(i18n.tr("ts_exported", path=path))

    def write_csv(self, path):
        """date/value CSV with a commented metadata header (utf-8-sig so
        Excel opens Chinese text correctly; '# ' lines are pandas-safe)."""
        meta = self._meta or {}
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            for key in ("product", "layer", "lat", "lon", "start", "end",
                        "source"):
                if meta.get(key):
                    writer.writerow([f"# {key}: {meta[key]}"])
            writer.writerow([f"# exported: {tsl.now_stamp()}"])
            writer.writerow(["date", "value"])
            for date, value in self.last_points:
                writer.writerow([date, value])

    # -------------------------------------------------------------- chart

    def _clear_chart(self):
        """Reset the chart to its empty state; the form fields are kept so
        the same query can be tweaked and re-plotted."""
        self.render_points([])
        self._meta = None
        self._status(i18n.tr("ts_api_note"))

    def render_points(self, points):
        """Draw (or clear with []) the series; records self.last_points."""
        self.chart.removeAllSeries()
        for axis in self.chart.axes():    # removeAllSeries keeps old axes,
            self.chart.removeAxis(axis)   # so labels pile up on every re-plot
        self.last_points = [list(p) for p in (points or [])]
        if not points:
            return
        series = QLineSeries()
        times = []
        for iso, value in points:
            text = str(iso)
            moment = QDateTime.fromString(text, Qt.ISODate)
            if not moment.isValid():      # "2025-10-25T01:30" parses directly;
                moment = QDateTime.fromString(   # pad date-only stamps
                    text[:10] + "T00:00:00", Qt.ISODate)
            if not moment.isValid():
                continue
            times.append(moment)
            series.append(moment.toMSecsSinceEpoch(), float(value))
        if not times:
            return
        pen = QPen(QColor("#d6372a"))
        pen.setWidthF(1.8)
        series.setPen(pen)

        x_axis = QDateTimeAxis()
        span_days = times[0].secsTo(times[-1]) // 86400
        x_axis.setFormat("yyyy-MM-dd" if span_days <= 120 else "yyyy-MM")
        x_axis.setRange(times[0], times[-1])
        values = [float(v) for _, v in points]
        lo, hi = min(values), max(values)
        if lo == hi:
            lo, hi = lo - 1.0, hi + 1.0
        pad = (hi - lo) * 0.08
        y_axis = QValueAxis()
        y_axis.setRange(lo - pad, hi + pad)
        y_axis.setLabelFormat("%.1f")

        self.chart.addSeries(series)
        self.chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)
