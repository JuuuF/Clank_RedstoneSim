"""Headless smoke test of the editor window (Qt offscreen platform)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["REDSIM_KEYMAP"] = os.devnull + ".missing"  # defaults, not the user's keymap
os.environ["REDSIM_CONFIG_DIR"] = os.devnull + ".missing"  # default preferences, never saved
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from redsim.core.direction import Direction  # noqa: E402
from redsim.editor.clipboard import Region  # noqa: E402
from redsim.ui.app import configure_gl  # noqa: E402
from redsim.ui.geometry import Hit  # noqa: E402
from redsim.world import blocks  # noqa: E402
from redsim.world.properties import LIT, POWERED  # noqa: E402


@pytest.fixture(scope="module")
def app() -> Iterator[object]:
    configure_gl()
    instance = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield instance


def test_window_edits_steps_and_renders(app: object) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    QtWidgets.QApplication.processEvents()

    # Right click on the floor with a lever selected, then a lamp next to it.
    window.inventory.select_block(blocks.LEVER)
    window._place(Hit((0, 0, 0), Direction.UP, 5.0))
    window.inventory.select_block(blocks.REDSTONE_LAMP)
    window._place(Hit((1, 0, 0), Direction.UP, 5.0))
    # Right click on the lever uses it (no Shift): the lamp lights immediately.
    window._use((0, 1, 0))
    document = window.document
    assert document.state_at((0, 1, 0)).get(POWERED) is True
    assert document.state_at((1, 1, 0)).get(LIT) is True

    window._use((0, 1, 0))  # lever off
    for _ in range(4):
        window._step_tick()
    assert document.state_at((1, 1, 0)).get(LIT) is False
    assert document.engine.game_time == 4

    window._tick_back()  # rewind one tick: the lamp is still lit at game time 3
    assert document.engine.game_time == 3
    assert document.state_at((1, 1, 0)).get(LIT) is True
    window._seek(document.history.end)  # replay to the end of the recorded history
    assert document.engine.game_time == 4
    assert document.state_at((1, 1, 0)).get(LIT) is False

    window._undo()  # rewinds to just before the last edit (the lever turned off)
    assert document.state_at((0, 1, 0)).get(POWERED) is True
    assert document.engine.game_time == 0

    # Region tools: mark two corners on the lever and lamp, copy, paste elsewhere, delete.
    window.viewport.region = Region.from_corners((0, 1, 0), (1, 1, 0))  # SELECT-mode box
    window._copy()
    # Paste follows the camera's working height (pivot layer y=1), centered under the cursor.
    from PySide6.QtCore import QPoint

    from redsim.ui.camera import Camera

    viewport = window.viewport
    viewport.camera = Camera(pivot=np.array([1.0, 1.2, 5.5]), distance=10.0, pitch=89.0)
    viewport._last_mouse = QPoint(viewport.width() // 2, viewport.height() // 2)
    window._paste()  # preview first
    assert viewport.paste_region() == Region((0, 1, 5), (1, 1, 5))
    target = window.viewport.paste_target()
    assert target is not None
    window._paste_at(target)  # what a left click does
    assert document.state_at((0, 1, 5)).is_(blocks.LEVER)
    assert document.state_at((1, 1, 5)).is_(blocks.REDSTONE_LAMP)
    window._delete_region()  # clears the marked selection (the original pair)
    assert document.state_at((0, 1, 0)).is_air

    QtWidgets.QApplication.processEvents()
    image = window.viewport.grabFramebuffer()
    if image.isNull():
        pytest.skip("no OpenGL framebuffer on this platform")
    colors = {
        image.pixel(x, y) for x in range(0, image.width(), 25) for y in range(0, image.height(), 25)
    }
    assert len(colors) >= 3  # at least sky and both checkerboard floor tones are drawn
    window.document.dirty = False
    window.close()


def test_run_loop_keeps_real_time(app: object) -> None:
    import time

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    start = window.document.engine.game_time
    window.simulation.play.setChecked(True)
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.002)
    window.simulation.play.setChecked(False)
    ticks = window.document.engine.game_time - start
    assert 5 <= ticks <= 12, ticks  # 20 ticks/s for 0.5 s, with slack for slow machines
    assert window.viewport.overlay_text[0].startswith("paused")
    window.document.dirty = False
    window.close()


def test_f1_brings_the_controls_to_the_front(app: object) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    QtWidgets.QApplication.processEvents()
    assert window.tabs.currentWidget() is not window.hotkeys  # the Inspector is in front
    window.viewport.setFocus()
    QTest.keyClick(window.viewport, Qt.Key.Key_F1)
    QtWidgets.QApplication.processEvents()
    assert window.tabs.currentWidget() is window.hotkeys
    window.document.dirty = False
    window.close()


def test_rotate_block_under_the_cursor(app: object) -> None:
    from redsim.ui.main_window import MainWindow
    from redsim.world.properties import FACING

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.parse_state("repeater[facing=north]"))
    window.viewport.hover = Hit((0, 1, 0), Direction.UP, 5.0)
    window._rotate_block(1)
    assert document.state_at((0, 1, 0)).get(FACING) is Direction.EAST
    window._rotate_block(3)
    assert document.state_at((0, 1, 0)).get(FACING) is Direction.NORTH
    window._undo()  # one undo per rotation
    assert document.state_at((0, 1, 0)).get(FACING) is Direction.EAST
    window.document.dirty = False
    window.close()


def test_info_overlay_lists_signal_values(app: object) -> None:
    from pathlib import Path

    from redsim.editor.document import Document
    from redsim.ui.main_window import MainWindow

    example = Path(__file__).resolve().parents[2] / "examples" / "showcase.redsim.json"
    window = MainWindow(Document.open(example))
    viewport = window.viewport
    viewport.camera.pivot = np.array([4.0, 1.0, 0.0])
    labels = {
        (tuple(int(v) for v in point), text, kind) for point, text, kind in viewport.info_labels()
    }
    assert ((6, 2, 2), "14", "source") in labels  # the barrel behind row 5's comparator
    assert any(kind == "wire" for _, _, kind in labels)
    assert any(kind == "comparator" for _, _, kind in labels)
    window.document.dirty = False
    window.close()


def test_inspector_controls_apply_immediately(app: object) -> None:
    from redsim.editor import sources
    from redsim.editor.placement import PlaceRequest
    from redsim.ui.main_window import MainWindow
    from redsim.world.properties import DELAY, FACING, HORIZONTAL_FACING, LOCKED

    def settle() -> None:
        for _ in range(3):
            QtWidgets.QApplication.processEvents()

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.parse_state("repeater[facing=north,delay=1]"))
    window._select((0, 1, 0))
    editors = window.inspector._editors
    editors["facing"].buttons[Direction.EAST].click()
    settle()
    assert document.state_at((0, 1, 0)).get(HORIZONTAL_FACING) is Direction.EAST
    editors["delay"].next.click()
    settle()
    assert document.state_at((0, 1, 0)).get(DELAY) == 2
    editors["locked"].click()
    settle()
    assert document.state_at((0, 1, 0)).get(LOCKED) is True

    document.place_source((2, 1, 0), "barrel", 6, PlaceRequest(Direction.UP, 0.0, 60.0))
    window._select((2, 1, 0))
    window.inspector.kind_buttons["lectern"].click()
    settle()
    assert document.state_at((2, 1, 0)).is_(blocks.LECTERN)
    assert sources.strength_at(document.level, (2, 1, 0)) == 6
    window.inspector.source_strength.next.click()
    settle()
    assert sources.strength_at(document.level, (2, 1, 0)) == 7
    assert document.state_at((2, 1, 0)).has(FACING) is False
    window.document.dirty = False
    window.close()


def test_inspector_hits_a_target_block(app: object) -> None:
    from redsim.ui.main_window import MainWindow
    from redsim.world.properties import POWER

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.TARGET.default_state)
    document.setblock((2, 1, 0), blocks.STONE.default_state)
    window._select((2, 1, 0))
    assert window.inspector.target_box.isHidden()
    window._select((0, 1, 0))
    assert not window.inspector.target_box.isHidden()
    for _ in range(5):
        window.inspector.hit_strength.back.click()
    window.inspector.hit_buttons[False].click()  # a snowball: 8 ticks
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    document.run_ticks(1)
    assert document.state_at((0, 1, 0)).get(POWER) == 10
    document.run_ticks(8)
    assert document.state_at((0, 1, 0)).get(POWER) == 0
    window.document.dirty = False
    window.close()


def test_hotkeys_panel_filters_and_follows_the_mode(app: object) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    panel = window.hotkeys
    assert ("SELECT mode: boxes and copies", "Drag a copy of the box (from inside it)") in set(
        panel.visible_rows()
    )
    panel.search.setText("rotate")
    rows = panel.visible_rows()
    assert rows and all("otate" in action or "otate" in section for section, action in rows)
    window.viewport.set_mode("build")
    assert "You are in BUILD mode" in panel.view.toPlainText()
    window.document.dirty = False
    window.close()


def test_cake_strength_steps_up_through_even_values(app: object) -> None:
    """Regression: the stepper asked a cake for 9, which rounded back down to 8."""
    from redsim.editor import sources
    from redsim.editor.placement import PlaceRequest
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    document = window.document
    document.place_source((0, 1, 0), "cake", 8, PlaceRequest(Direction.UP, 0.0, 60.0))
    window._select((0, 1, 0))
    for expected in (10, 12, 14):
        window.inspector.source_strength.next.click()
        for _ in range(3):
            QtWidgets.QApplication.processEvents()
        assert sources.strength_at(document.level, (0, 1, 0)) == expected
    assert not window.inspector.source_strength.next.isEnabled()  # 14 is a cake's maximum
    window.inventory.select_block(blocks.CAKE)
    assert window.inventory.strength.singleStep() == 2
    window.document.dirty = False
    window.close()


def test_unsaved_changes_prompt(app: object) -> None:
    from PySide6.QtCore import QTimer

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.document.dirty = True
    texts: list[str] = []

    def answer(label: str) -> None:
        box = QtWidgets.QApplication.activeModalWidget()
        assert isinstance(box, QtWidgets.QMessageBox)
        texts.append(box.text())
        texts.extend(button.text() for button in box.buttons())
        next(b for b in box.buttons() if b.text().replace("&", "") == label).click()

    QTimer.singleShot(50, lambda: answer("Cancel"))
    assert window._confirm_discard(closing=True) is False
    assert "You still have unsaved changes" in texts[0]
    assert {"Close without saving", "Save as…"} <= {t.replace("&", "") for t in texts}
    QTimer.singleShot(50, lambda: answer("Close without saving"))
    assert window._confirm_discard(closing=True) is True
    window.document.dirty = False
    window.close()
