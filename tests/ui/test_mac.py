"""macOS and trackpads: extra bindings (nothing replaced), ⌘ symbols, trackpad gestures."""

from __future__ import annotations

import os
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QPointingDevice, QWheelEvent  # noqa: E402

from redsim.ui.keymap import ACTIONS, MAC_EXTRA_DEFAULTS, Keymap, display  # noqa: E402


@pytest.fixture(scope="module")
def app() -> Any:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_mac_only_adds_bindings() -> None:
    mac, other = Keymap(mac=True), Keymap(mac=False)
    for spec in ACTIONS:
        assert other.bindings(spec.id) == spec.defaults  # off macOS: exactly as before
        assert mac.bindings(spec.id)[: len(spec.defaults)] == spec.defaults  # kept first
    assert mac.bindings("search.blocks")[-1] == "Ctrl+F"  # ⌘Space is Spotlight
    assert set(MAC_EXTRA_DEFAULTS) <= {spec.id for spec in ACTIONS}
    assert mac.warnings == [] and mac.changes() == {}  # no clashes, nothing "changed"


def test_mac_shows_apple_symbols() -> None:
    assert display("Ctrl+Shift+Z", mac=True) == "⇧⌘Z"
    assert display("Alt+Left Drag", mac=True) == "⌥Left Drag"
    assert display("Ctrl+Shift+Z", mac=False) == "Ctrl+Shift+Z"
    assert Keymap(mac=True).describe("edit.undo") == "⌘Z"


def _scroll(widget: Any, dx: int, dy: int, modifiers: Any = Qt.KeyboardModifier.NoModifier) -> None:
    point = QPointF(widget.width() / 2, widget.height() / 2)
    event = QWheelEvent(
        point,
        widget.mapToGlobal(point),
        QPoint(dx, dy),  # pixel delta: fingers on a trackpad
        QPoint(dx * 2, dy * 2),
        Qt.MouseButton.NoButton,
        modifiers,
        Qt.ScrollPhase.ScrollUpdate,
        False,
        Qt.MouseEventSource.MouseEventNotSynthesized,
        QPointingDevice.primaryPointingDevice(),
    )
    widget.wheelEvent(event)


def test_trackpad_scrolling_navigates_when_enabled(app: Any) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    viewport = window.viewport
    viewport.preferences.trackpad_navigation = True
    yaw = viewport.camera.yaw
    _scroll(viewport, 40, 0)  # two fingers to the side: orbit
    assert viewport.camera.yaw != yaw
    distance = viewport.camera.distance
    _scroll(viewport, 0, 80, Qt.KeyboardModifier.ControlModifier)  # ⌘ + scroll: zoom
    assert viewport._glide is not None and viewport._glide[1] < distance
    viewport._glide = None
    height = float(viewport.camera.pivot[1])
    _scroll(viewport, 0, 65, Qt.KeyboardModifier.AltModifier)  # ⌥ + scroll: up, by blocks
    assert viewport._glide is not None and viewport._glide[0][1] == pytest.approx(height + 2)
    viewport._glide = None
    viewport.preferences.trackpad_navigation = False  # off: like a mouse wheel (zoom)
    yaw = viewport.camera.yaw
    _scroll(viewport, 40, 0)
    assert viewport.camera.yaw == yaw
    window.document.dirty = False
    window.close()


def test_pinch_zooms(app: Any) -> None:
    from PySide6.QtGui import QNativeGestureEvent

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    viewport = window.viewport
    point = QPointF(10, 10)
    pinch = QNativeGestureEvent(
        Qt.NativeGestureType.ZoomNativeGesture,
        QPointingDevice.primaryPointingDevice(),
        2,
        point,
        point,
        point,
        0.25,  # fingers apart: zoom in
        QPointF(0, 0),
        0,
    )
    distance = viewport.camera.distance
    assert viewport.event(pinch)
    assert viewport._glide is not None and viewport._glide[1] == pytest.approx(distance / 1.25)
    window.document.dirty = False
    window.close()


def test_mac_hints_name_trackpad_friendly_keys() -> None:
    from redsim.ui.hints import Context, context_hints

    mac = dict((what, keys) for keys, what in context_hints(Keymap(mac=True), Context("build")))
    other = dict((what, keys) for keys, what in context_hints(Keymap(mac=False), Context("build")))
    assert mac["pick"] == "Alt+Right Click" and other["pick"] == "Middle Click"
    assert mac["search"] == "/"
    normal = dict((w, k) for k, w in context_hints(Keymap(mac=True), Context("normal")))
    assert normal["all hotkeys"] == "Ctrl+/" and normal["orbit"] == "Alt+Left Drag"
