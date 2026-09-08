# -*- coding: utf-8 -*-
"""PyInstaller entry script for the D3LToolNASA.exe build."""

import os
import sys

# windowed builds have no stdout/stderr; give them a sink so stray prints
# (ours, or warnings from libraries) never crash the app
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


def smoke() -> int:
    """Build-time verification: construct the whole UI headlessly, then exit."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.main_window import MainWindow
    from d3ltool.gui.theme import apply_theme

    app = QApplication([])
    apply_theme(app)
    window = MainWindow()
    window.close()
    try:
        print("SMOKE OK")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        sys.exit(smoke())
    from d3ltool.app import run_gui

    sys.exit(run_gui())
