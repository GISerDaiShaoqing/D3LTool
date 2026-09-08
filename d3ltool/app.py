# -*- coding: utf-8 -*-
"""GUI entry point."""

import sys


def run_gui() -> int:
    from pathlib import Path

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from . import APP_NAME, __version__
    from .gui.main_window import MainWindow
    from .gui.theme import apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName("D3LTool")
    app.setApplicationDisplayName(f"{APP_NAME} v{__version__}")
    apply_theme(app)

    icon_file = Path(__file__).resolve().parent / "resources" / "D3L.ico"
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_gui())
