"""Application entry point: ``python -m redsim [world.redsim.json]``."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def configure_platform() -> None:
    """This PySide6 build cannot create GL contexts with the native Wayland plugin
    (doc/research/repository-report.md), so prefer XWayland unless the user chose."""
    if os.environ.get("WAYLAND_DISPLAY") and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def configure_gl() -> None:
    from PySide6.QtGui import QSurfaceFormat

    surface = QSurfaceFormat()
    surface.setVersion(3, 3)
    surface.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    surface.setDepthBufferSize(24)
    surface.setSamples(4)
    QSurfaceFormat.setDefaultFormat(surface)


def main(argv: list[str] | None = None) -> int:
    configure_platform()
    configure_gl()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from redsim.ui.main_window import MainWindow

    args = list(sys.argv if argv is None else argv)
    app = QApplication(args)
    app.setApplicationName("Redstone Simulator")
    window = MainWindow()
    if not window.restore_layout():
        window.resize(1400, 900)
    window.show()
    if len(args) > 1:  # behind the loading screen, once the window is up
        QTimer.singleShot(0, lambda: window.load_path(Path(args[1])))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
