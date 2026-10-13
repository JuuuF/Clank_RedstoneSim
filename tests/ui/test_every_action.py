"""Every action of the main window, triggered in every mode on an empty and on a busy
document, must not raise (dialogs are answered "cancel" at once)."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["REDSIM_KEYMAP"] = os.devnull + ".missing"
os.environ["REDSIM_CONFIG_DIR"] = os.devnull + ".missing"
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from redsim.core.direction import Direction  # noqa: E402
from redsim.editor.clipboard import Region  # noqa: E402
from redsim.ui.geometry import Hit  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "showcase.redsim.json"
#: Actions that would end the test (quitting) or wait for a user.
SKIPPED = {"file.quit"}


@pytest.fixture(scope="module")
def app() -> Iterator[object]:
    from redsim.ui.app import configure_gl

    configure_gl()
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def no_dialogs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every dialog returns at once as if cancelled."""
    widgets = QtWidgets
    monkeypatch.setattr(widgets.QDialog, "exec", lambda self: 0)
    monkeypatch.setattr(widgets.QMenu, "exec", lambda self, *a, **k: None)
    monkeypatch.setattr(widgets.QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
    monkeypatch.setattr(widgets.QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    monkeypatch.setattr(widgets.QFileDialog, "getExistingDirectory", lambda *a, **k: "")
    monkeypatch.setattr(widgets.QInputDialog, "getText", lambda *a, **k: ("", False))
    monkeypatch.setattr(widgets.QColorDialog, "getColor", lambda *a, **k: _invalid_color())
    from PySide6.QtGui import QDesktopServices

    monkeypatch.setattr(QDesktopServices, "openUrl", lambda *a, **k: True)  # no editors
    for name in ("critical", "warning", "information", "question"):
        monkeypatch.setattr(widgets.QMessageBox, name, lambda *a, **k: 0)


def _invalid_color() -> Any:
    from PySide6.QtGui import QColor

    return QColor()


def _actions(window: Any) -> list[tuple[str, Any]]:
    """Every QAction of the window: menu entries and shortcuts (the quit action aside)."""
    from PySide6.QtGui import QAction

    named = {id(action): key for key, action in window._actions.items()}
    found = []
    for action in window.findChildren(QAction):
        key = named.get(id(action), f"menu:{action.text()}")
        if key in SKIPPED or action.text().replace("&", "") in ("Quit", "Exit"):
            continue
        if action.menu() is not None or action.isSeparator():
            continue
        found.append((key, action))
    return found


@pytest.mark.parametrize("busy", [False, True])
def test_every_action_in_every_mode(app: object, no_dialogs: None, busy: bool) -> None:
    from redsim.editor.document import Document
    from redsim.ui.main_window import MainWindow

    document = Document.open(EXAMPLE) if busy else Document.new_flat()
    window = MainWindow(document)
    window.resize(1000, 700)
    window.show()
    failures: list[str] = []
    errors: list[str] = []
    hook = sys.excepthook
    sys.excepthook = lambda kind, value, tb: errors.append(f"{kind.__name__}: {value}")
    try:
        for mode in ("normal", "build", "select", "animate"):
            window._mode_key(mode)
            viewport = window.viewport
            # Something under the cursor and a selection, so block actions have a target.
            viewport.hover = Hit((0, 1, 0), Direction.UP, 4.0)
            viewport.selection = (0, 1, 0)
            viewport.region = Region((-1, 1, -1), (1, 2, 1))
            for key, action in _actions(window):
                try:
                    action.trigger()
                    QtWidgets.QApplication.processEvents()
                except Exception as exc:  # noqa: BLE001 - collect every failure
                    failures.append(f"{mode} {key}: {type(exc).__name__}: {exc}")
                if window.simulation.play.isChecked():
                    window.simulation.stop()
            window._play(False)
    finally:
        sys.excepthook = hook
    window.document.dirty = False
    window.close()
    assert not failures, "\n".join(failures)
    assert not errors, "\n".join(errors)
