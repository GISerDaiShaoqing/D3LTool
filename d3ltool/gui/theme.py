# -*- coding: utf-8 -*-
"""Application theme: Fusion style + brand QSS (D3L red / deep navy)."""

QSS = """
* {
    outline: none;
}
QMainWindow, QDialog {
    background: #f5f7fa;
}
QWidget {
    color: #1f2937;
    font-size: 13px;
}

/* ---------- menus ---------- */
QMenuBar {
    background: #ffffff;
    border-bottom: 1px solid #e3e8ef;
    padding: 2px 6px;
}
QMenuBar::item {
    padding: 5px 12px;
    border-radius: 6px;
    color: #334155;
}
QMenuBar::item:selected {
    background: #eef2f7;
}
QMenu {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item {
    padding: 6px 26px 6px 14px;
    border-radius: 6px;
    color: #1f2937;
}
QMenu::item:selected {
    background: #fdeceb;
    color: #b02a20;
}
QMenu::item:disabled {
    color: #9aa5b1;
}
QMenu::separator {
    height: 1px;
    background: #edf0f4;
    margin: 4px 8px;
}

/* ---------- toolbar / statusbar ---------- */
QToolBar {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid #e3e8ef;
    padding: 4px 8px;
    spacing: 6px;
}
QToolBar QToolButton {
    padding: 5px 12px;
    border-radius: 6px;
    color: #334155;
}
QToolBar QToolButton:hover {
    background: #eef2f7;
}
QStatusBar {
    background: #f5f7fa;
    border-top: 1px solid #e3e8ef;
    color: #64748b;
}

/* ---------- cards (group boxes) ---------- */
QGroupBox {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 10px;
    margin-top: 13px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    top: 1px;
    padding: 0 5px;
    color: #123252;
    background: #f5f7fa;
}

/* ---------- inputs ---------- */
QLineEdit, QComboBox, QSpinBox, QDateEdit {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 7px;
    padding: 5px 9px;
    selection-background-color: #d6372a;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {
    border: 1.5px solid #d6372a;
}
QComboBox::drop-down, QDateEdit::drop-down {
    border: none;
    width: 22px;
}
QSpinBox::up-button, QSpinBox::down-button {
    border: none;
    background: transparent;
    width: 16px;
}
QCalendarWidget QWidget {
    alternate-background-color: #f5f7fa;
}

/* ---------- buttons ---------- */
QPushButton {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 7px;
    padding: 6px 16px;
    color: #334155;
}
QPushButton:hover {
    background: #f0f3f7;
    border-color: #b9c4d0;
}
QPushButton:pressed {
    background: #e4e9ef;
}
QPushButton:disabled {
    color: #9aa5b1;
    background: #f2f4f7;
    border-color: #e3e8ef;
}
QPushButton#accentButton {
    background: #d6372a;
    border: 1px solid #d6372a;
    color: #ffffff;
    font-weight: 600;
    font-size: 14px;
    padding: 10px 16px;
    border-radius: 9px;
}
QPushButton#accentButton:hover {
    background: #b92e23;
    border-color: #b92e23;
}
QPushButton#accentButton:pressed {
    background: #a3271d;
}
QPushButton#accentButton:disabled {
    background: #efb9b4;
    border-color: #efb9b4;
    color: #ffffff;
}

/* ---------- tables ---------- */
QTableWidget {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 10px;
    gridline-color: transparent;
    alternate-background-color: #fafbfd;
    selection-background-color: #e3ecf7;
    selection-color: #1f2937;
}
QTableWidget::item {
    padding: 4px 6px;
    border: none;
}
QHeaderView::section {
    background: #f1f4f8;
    color: #475569;
    border: none;
    border-bottom: 1px solid #e3e8ef;
    padding: 7px 8px;
    font-weight: 600;
}
QTableCornerButton::section {
    background: #f1f4f8;
    border: none;
}

/* ---------- progress bar ---------- */
QProgressBar {
    background: #e9edf3;
    border: none;
    border-radius: 6px;
    min-height: 12px;
    max-height: 14px;
    text-align: center;
    color: #ffffff;
    font-size: 10px;
    font-weight: 600;
}
QProgressBar::chunk {
    background: #d6372a;
    border-radius: 6px;
}

/* ---------- scrollbars / splitter / misc ---------- */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #c7cfda;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #aeb8c6;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #c7cfda;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0;
    width: 0;
}
QSplitter::handle {
    background: transparent;
}
QSplitter::handle:horizontal {
    width: 5px;
}
QSplitter::handle:hover {
    background: #e3e8ef;
    border-radius: 2px;
}
QScrollArea#searchPanelScroll {
    background: transparent;
    border: none;
}
QWidget#searchPanelBody {
    background: transparent;
}
QToolTip {
    background: #1f2937;
    color: #f8fafc;
    border: none;
    border-radius: 5px;
    padding: 5px 8px;
}
"""


def apply_theme(app) -> None:
    """Fusion style + brand stylesheet + platform CJK-friendly font."""
    import sys

    from PySide6.QtGui import QFont

    app.setStyle("Fusion")
    if sys.platform == "darwin":
        app.setFont(QFont("PingFang SC", 13))
    elif sys.platform == "win32":
        app.setFont(QFont("Microsoft YaHei UI", 9))
    else:
        font = QFont("Noto Sans CJK SC", 9)
        app.setFont(font)
    app.setStyleSheet(QSS)
