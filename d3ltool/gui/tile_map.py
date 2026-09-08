# -*- coding: utf-8 -*-
"""Clickable 36x18 MODIS sinusoidal tile map."""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QToolTip, QWidget

from .. import tiles

TILE_W = 9
TILE_H = 13
CANVAS_W = tiles.N_COLS * TILE_W    # 324
CANVAS_H = tiles.N_ROWS * TILE_H    # 234


class TileMap(QWidget):
    tiles_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CANVAS_W, CANVAS_H)
        self.setMouseTracking(True)
        self._selected = set()   # {(h, v)}
        self._hover = None

    # ------------------------------------------------------------------ public

    def selected_tiles(self) -> list:
        return [tiles.tile_name(h, v) for h, v in sorted(self._selected)]

    def clear_selection(self) -> None:
        if self._selected:
            self._selected.clear()
            self.tiles_changed.emit()
        self.update()

    def select_lonlat(self, lon: float, lat: float) -> None:
        h, v = tiles.lonlat_to_tile(lon, lat)
        self._selected = {(h, v)}
        self.tiles_changed.emit()
        self.update()

    def set_selected_names(self, names: list) -> None:
        sel = set()
        for name in names:
            try:
                sel.add(tiles.parse_tile(name))
            except ValueError:
                continue
        self._selected = sel
        self.tiles_changed.emit()
        self.update()

    # ------------------------------------------------------------------ events

    def mousePressEvent(self, event) -> None:
        cell = self._cell_at(event.position().x(), event.position().y())
        if cell is not None:
            if cell in self._selected:
                self._selected.discard(cell)
            else:
                self._selected.add(cell)
            self.tiles_changed.emit()
            self.update()

    def mouseMoveEvent(self, event) -> None:
        cell = self._cell_at(event.position().x(), event.position().y())
        if cell != self._hover:
            self._hover = cell
            self.update()
        if cell is not None:
            h, v = cell
            lon0, lat0, lon1, lat1 = tiles.tile_bounds_lonlat(h, v)
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"{tiles.tile_name(h, v)}  ({lon0:.0f}~{lon1:.0f}E, {lat0:.0f}~{lat1:.0f}N)",
                              self)

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f4f7fb"))
        cx = CANVAS_W / 2.0

        for v in range(tiles.N_ROWS):
            frac = tiles.row_width_fraction(v)
            band_half = frac * CANVAS_W / 2.0
            x0 = cx - band_half
            y0 = v * TILE_H
            # row band background
            painter.fillRect(QRectF(x0, y0, band_half * 2, TILE_H), QColor("#dfe9f5"))
            # vertical cell lines
            painter.setPen(QPen(QColor("#b8cbe2"), 1))
            for i in range(tiles.N_COLS + 1):
                x = x0 + i * TILE_W
                painter.drawLine(int(x), int(y0), int(x), int(y0 + TILE_H))
            painter.drawLine(int(x0), int(y0 + TILE_H), int(x0 + band_half * 2), int(y0 + TILE_H))
            # row band border
            painter.setPen(QPen(QColor("#9fb6d0"), 1))
            painter.drawRect(QRectF(x0, y0, band_half * 2, TILE_H))

        # selection & hover overlays
        for (h, v) in self._selected:
            rect = self._cell_rect(h, v)
            if rect is not None:
                painter.fillRect(rect, QColor(30, 120, 220, 200))
        if self._hover is not None:
            rect = self._cell_rect(*self._hover)
            if rect is not None:
                painter.setPen(QPen(QColor("#e05500"), 2))
                painter.drawRect(rect)

        painter.end()

    # ----------------------------------------------------------------- helpers

    def _cell_rect(self, h, v):
        frac = tiles.row_width_fraction(v)
        band_half = frac * CANVAS_W / 2.0
        x0 = cx = CANVAS_W / 2.0
        x0 = cx - band_half
        x = x0 + h * TILE_W
        y = v * TILE_H
        if x < 0 or x + TILE_W > CANVAS_W:
            return None
        return QRectF(x, y, TILE_W, TILE_H)

    def _cell_at(self, px, py):
        v = int(py // TILE_H)
        if not (0 <= v < tiles.N_ROWS):
            return None
        frac = tiles.row_width_fraction(v)
        band_half = frac * CANVAS_W / 2.0
        cx = CANVAS_W / 2.0
        rel = (px - cx) / band_half if band_half > 0 else 2.0
        if abs(rel) > 1.0:
            return None
        h = int((rel + 1.0) / 2.0 * tiles.N_COLS)
        return min(tiles.N_COLS - 1, max(0, h)), v
