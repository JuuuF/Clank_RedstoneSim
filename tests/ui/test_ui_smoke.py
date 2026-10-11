"""Headless smoke test of the editor window (Qt offscreen platform)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["REDSIM_KEYMAP"] = os.devnull + ".missing"  # defaults, not the user's keymap
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
    window.block_palette.select_block(blocks.LEVER)
    window._place(Hit((0, 0, 0), Direction.UP, 5.0))
    window.block_palette.select_block(blocks.REDSTONE_LAMP)
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
    window.viewport.hover = Hit((0, 0, 5), Direction.UP, 5.0)  # floor block: paste above it
    window._paste()
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
    assert window.help_dock.visibleRegion().isEmpty()  # behind the block palette tab
    window.viewport.setFocus()
    QTest.keyClick(window.viewport, Qt.Key.Key_F1)
    QtWidgets.QApplication.processEvents()
    assert not window.help_dock.visibleRegion().isEmpty()
    window.document.dirty = False
    window.close()
