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
    window._place((0, 1, 0))
    window.inventory.select_block(blocks.REDSTONE_LAMP)
    window._place((1, 1, 0))
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


def test_inspector_edits_container_slots(app: object) -> None:
    from redsim.ui.main_window import MainWindow
    from redsim.world.blocks.hopper import HopperBlockEntity

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.parse_state("hopper[facing=down]"))
    window._select((0, 1, 0))
    inspector = window.inspector
    assert not inspector.contents_box.isHidden()
    assert inspector.slot_box.maximum() == 4
    inspector.slot_box.setValue(1)
    inspector.item_box.setCurrentIndex(inspector.item_box.findData("minecraft:redstone"))
    inspector.count_box.setValue(7)
    inspector.slot_set.click()
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    hopper = document.level.get_block_entity((0, 1, 0))
    assert isinstance(hopper, HopperBlockEntity)
    assert hopper.items[1] == ("minecraft:redstone", 7)
    assert inspector.contents_grid.items[1] == ("minecraft:redstone", 7)
    assert inspector.contents_label.text() == "7 items in 1 of 5 slots"
    window.document.dirty = False
    window.close()


def test_timeline_keyframes_drag_merge_and_delete(app: object) -> None:
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtTest import QTest

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    document = window.document
    document.run_ticks(3)
    document.setblock((0, 1, 0), blocks.STONE.default_state)
    document.run_ticks(3)
    document.setblock((1, 1, 0), blocks.STONE.default_state)
    document.run_ticks(4)
    window._changed()
    canvas = window.simulation.canvas
    canvas.view_start, canvas.view_span = 0.0, 20.0
    row_y = canvas._row_top(2) + canvas.EDIT_ROW_HEIGHT // 2  # "Changed" row (/setblock)

    def send(kind: QEvent.Type, tick: int, buttons: Qt.MouseButton) -> None:
        point = QPointF(canvas._x(tick), row_y)
        button = (
            Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
        )
        event = QMouseEvent(
            kind, point, canvas.mapToGlobal(point), button, buttons, Qt.KeyboardModifier.NoModifier
        )
        QtWidgets.QApplication.sendEvent(canvas, event)

    left = Qt.MouseButton.LeftButton
    send(QEvent.Type.MouseButtonPress, 3, left)
    send(QEvent.Type.MouseMove, 4, left)
    send(QEvent.Type.MouseMove, 5, left)
    send(QEvent.Type.MouseButtonRelease, 5, Qt.MouseButton.NoButton)
    assert [b.tick for b in document.edit_batches()] == [5, 6]
    window._changed()
    canvas.selected = {(5, "edit"), (6, "edit")}
    canvas.setFocus()
    QTest.keyClick(canvas, Qt.Key.Key_M)
    assert [b.tick for b in document.edit_batches()] == [5]
    window._changed()
    canvas.selected = {(5, "edit")}
    QTest.keyClick(canvas, Qt.Key.Key_Delete)
    assert document.edit_batches() == []
    assert document.undo() and [b.tick for b in document.edit_batches()] == [5]
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


def test_e_opens_the_block_under_the_cursor_in_a_popup(app: object) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    window.inventory.select_block(blocks.REDSTONE_LAMP)
    window._place((2, 1, 0))
    assert window.keymap.bindings("block.popup") == ("E",)
    assert "E" not in window.keymap.bindings("sim.event")  # E moved to the popup
    window.viewport.hover = Hit((2, 1, 0), Direction.UP, 4.0)
    window._actions["block.popup"].trigger()
    popup = window.block_popup
    assert popup.isVisible() and popup.pos_ == (2, 1, 0)
    assert "Redstone Lamp" in popup.inspector.title.text()
    popup.inspector.apply_requested.emit((2, 1, 0), blocks.STONE.default_state)  # an edit
    assert window.document.state_at((2, 1, 0)).is_(blocks.STONE)
    popup.close()
    assert not popup.isVisible() and popup.pos_ is None
    window.document.dirty = False
    window.close()


def test_build_places_against_the_pointed_face_like_minecraft(app: object) -> None:
    from PySide6.QtCore import QPoint

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.document.setblock((0, 1, 0), blocks.STONE.default_state)
    viewport = window.viewport
    # A level ray at y 1.5 towards +x: it meets the stone's west face, never the layer.
    viewport._ray = lambda point: (np.array([-5.0, 1.5, 0.5]), np.array([1.0, 0.0, 0.0]))
    assert viewport.build_target(QPoint(0, 0)) == (-1, 1, 0)
    assert viewport.build_face is Direction.WEST
    # Looking down at open floor: the working layer decides.
    viewport._ray = lambda point: (np.array([5.5, 6.0, 5.5]), np.array([0.0, -1.0, 0.0]))
    assert viewport.build_target(QPoint(0, 0)) == (5, 1, 5)
    assert viewport.build_face is Direction.UP
    window.document.dirty = False
    window.close()


def test_diagnostics_clicks_flash_the_block(app: object) -> None:
    from redsim.ui.main_window import MainWindow
    from redsim.ui.panels import first_position

    assert first_position("  set_block (3, 1, -2) old=air") == (3, 1, -2)
    window = MainWindow()
    window.diagnostics.highlight_requested.emit((1, 2, 3))
    assert window.viewport.highlight is not None and window.viewport.highlight[0] == (1, 2, 3)
    assert len(window.viewport._highlight_body()) > 0
    window.document.dirty = False
    window.close()


def test_f3_labels_fade_out_within_the_range(app: object) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    for x in range(0, 30, 2):
        window.document.setblock((x, 1, 0), blocks.REDSTONE_WIRE.default_state)
    viewport = window.viewport
    viewport.camera.pivot = np.array([0.5, 1.0, 0.5])
    viewport.preferences.info_label_range = 13
    labels = viewport._labels()
    assert {pos[0] for *_, pos, _ in labels} == set(range(0, 13, 2))  # within 13 blocks
    alphas = {pos[0]: alpha for *_, pos, alpha in labels}
    assert alphas[0] == 1.0 and 0 < alphas[12] < alphas[8] <= 1.0  # fading at the end
    viewport.show_info, viewport.hovered_label = True, (8, 1, 0)
    assert viewport.focus_hover()  # F jumps to the hovered label's block
    window.document.dirty = False
    window.close()


def test_several_selections_are_deleted_together_and_cleared_with_alt_a(app: object) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    document = window.document
    for x in (0, 5):
        document.setblock((x, 1, 0), blocks.STONE.default_state)
    viewport = window.viewport
    viewport.extra_regions = [Region((0, 1, 0), (0, 1, 0))]  # Shift+drag kept the first
    viewport.region = Region((5, 1, 0), (5, 1, 0))
    assert len(viewport._selection_body()) > 0
    window._delete_region()  # Del clears every selection, one undo step
    assert document.state_at((0, 1, 0)).is_air and document.state_at((5, 1, 0)).is_air
    document.undo()
    assert document.state_at((0, 1, 0)).is_(blocks.STONE)
    assert document.state_at((5, 1, 0)).is_(blocks.STONE)
    assert window.keymap.bindings("select.clear_all") == ("Alt+A",)
    window._actions["select.clear_all"].trigger()
    assert viewport.region is None and viewport.extra_regions == []
    document.dirty = False
    window.close()


def test_world_picker_lists_saves_and_recent_worlds(app: object, tmp_path: object) -> None:
    from pathlib import Path

    from redsim.ui.world_picker import (
        MINECRAFT,
        SIMULATION,
        WorldPicker,
        load_recent,
        remember_world,
    )

    example = Path(__file__).resolve().parents[2] / "examples" / "showcase.redsim.json"
    remember_world(example, SIMULATION)
    assert load_recent()[0]["path"] == str(example.resolve())
    picker = WorldPicker(None, SIMULATION)
    names = [picker.list.item(r).data(0x0100).name for r in range(picker.list.count())]
    assert "showcase" in names
    picker.search.setText("showc")
    picker._open()
    assert picker.chosen is not None and picker.chosen[0] == SIMULATION
    assert picker.chosen[1].name == "showcase.redsim.json"
    saves = WorldPicker(None, MINECRAFT)  # lists whatever saves exist (maybe none)
    assert saves.kind == MINECRAFT


def test_tab_ring_switches_modes_and_animate_clicks_add_pulses(app: object) -> None:
    from PySide6.QtCore import QPoint

    from redsim.ui.main_window import MainWindow
    from redsim.ui.viewport import ANIMATE, BUILD

    window = MainWindow()
    viewport = window.viewport
    assert window.keymap.bindings("mode.ring") == ("Tab",)
    viewport.ring = (QPoint(100, 100), None)
    assert viewport.ring_mode_at(QPoint(100, 30)) == "normal"  # up
    assert viewport.ring_mode_at(QPoint(170, 100)) == BUILD  # right
    assert viewport.ring_mode_at(QPoint(100, 170)) == "select"  # down
    assert viewport.ring_mode_at(QPoint(30, 100)) == ANIMATE  # left
    assert viewport.ring_mode_at(QPoint(104, 102)) is None  # the center: nothing
    viewport.ring = None
    viewport.mode_requested.emit(ANIMATE)  # what letting go of Tab on ANIMATE does
    assert viewport.mode == ANIMATE
    document = window.document
    document.setblock((0, 1, 0), blocks.parse_state("sticky_piston[facing=east]"))
    window.sequence.duration.setValue(3)
    viewport.hover = Hit((0, 1, 0), Direction.UP, 4.0)
    viewport._click("animate.pulse")  # at tick 0: the pulse starts at tick 1
    pulses = document.pulses()
    assert [(p.tick, p.pos, p.ticks) for p in pulses] == [(1, (0, 1, 0), 3)]
    window.sequence.show_document(document)
    assert window.sequence.table.rowCount() == 1
    document.seek_tick(document.end_tick)
    document.seek_tick(2)
    viewport._click("animate.remove")  # running at tick 2: removed
    assert document.pulses() == []
    document.dirty = False
    window.close()


def test_timeline_lines_expand_and_pulse_bars_move(app: object) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.parse_state("sticky_piston[facing=east]"))
    document.add_pulse((0, 1, 0), 2, 15, 3)
    window._changed()
    canvas = window.simulation.canvas
    canvas.resize(900, canvas.height())
    canvas.view_start, canvas.view_span = 0, 20
    power = next(i for i, line in enumerate(canvas.lines) if line.row == "power")
    assert canvas.lines[power].expandable and not canvas.lines[power].expanded

    def click(x: float, y: float, button: object = Qt.MouseButton.LeftButton) -> None:
        for kind in (QMouseEvent.Type.MouseButtonPress, QMouseEvent.Type.MouseButtonRelease):
            event = QMouseEvent(kind, QPointF(x, y), QPointF(x, y), button, button,
                                Qt.KeyboardModifier.NoModifier)  # fmt: skip
            (canvas.mousePressEvent if kind == QMouseEvent.Type.MouseButtonPress
             else canvas.mouseReleaseEvent)(event)  # fmt: skip

    click(8, canvas._tops[power] + 7)  # the arrow: expand Powered
    kinds = [line.kind for line in canvas.lines if line.row == "power"]
    assert kinds == ["category", "group", "block"]
    line = len(canvas.lines) - 1 if canvas.lines[-1].kind == "block" else power + 2
    top = canvas._tops[line] + 7
    moved: list[tuple[int, int, int, int, object]] = []
    canvas.pulses_changed.connect(lambda changes: moved.extend(changes))
    start = canvas._x(3)  # inside the bar (ticks 2–5)
    press = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(start, top), QPointF(start, top),
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier)  # fmt: skip
    canvas.mousePressEvent(press)
    to = canvas._x(7)
    move = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(to, top), QPointF(to, top),
                       Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)  # fmt: skip
    canvas.mouseMoveEvent(move)
    release = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPointF(to, top),
                          QPointF(to, top), Qt.MouseButton.LeftButton,
                          Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)  # fmt: skip
    canvas.mouseReleaseEvent(release)
    assert moved and moved[0][1:4] == (6, 15, 3)  # moved 4 ticks later
    assert [(p.tick, p.ticks) for p in document.pulses()] == [(6, 3)]
    document.dirty = False
    window.close()


def test_selected_pulses_move_together_switch_lines_and_delete(app: object) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QKeyEvent, QMouseEvent

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    document = window.document
    for z in (0, 1):
        document.setblock((0, 1, z), blocks.parse_state("sticky_piston[facing=east]"))
    document.add_pulse((0, 1, 0), 2, 15, 2)
    document.add_pulse((0, 1, 0), 6, 15, 2)
    document.add_pulse((0, 1, 1), 4, 15, 2)
    window._changed()
    canvas = window.simulation.canvas
    canvas.resize(900, canvas.height())
    canvas.view_start, canvas.view_span = 0, 20
    canvas.expanded = {"power"}
    window._changed()
    lines = {line.pos: i for i, line in enumerate(canvas.lines) if line.kind == "block"}

    def mouse(kind: object, x: float, y: float, buttons: object, mods: object = None) -> None:
        button = Qt.MouseButton.LeftButton
        event = QMouseEvent(kind, QPointF(x, y), QPointF(x, y), button, buttons,  # type: ignore[arg-type]
                            mods or Qt.KeyboardModifier.NoModifier)  # fmt: skip
        {QMouseEvent.Type.MouseButtonPress: canvas.mousePressEvent,
         QMouseEvent.Type.MouseMove: canvas.mouseMoveEvent,
         QMouseEvent.Type.MouseButtonRelease: canvas.mouseReleaseEvent}[kind](event)  # fmt: skip

    top0 = canvas._tops[lines[(0, 1, 0)]] + 7
    top1 = canvas._tops[lines[(0, 1, 1)]] + 7
    left = Qt.MouseButton.LeftButton
    # Select both pulses of the first line (Shift+click the second).
    mouse(QMouseEvent.Type.MouseButtonPress, canvas._x(2.5), top0, left)
    mouse(QMouseEvent.Type.MouseButtonRelease, canvas._x(2.5), top0, Qt.MouseButton.NoButton)
    shift = Qt.KeyboardModifier.ShiftModifier
    mouse(QMouseEvent.Type.MouseButtonPress, canvas._x(6.5), top0, left, shift)
    mouse(QMouseEvent.Type.MouseButtonRelease, canvas._x(6.5), top0, Qt.MouseButton.NoButton, shift)
    assert len(canvas.selected_pulses) == 2
    # Drag them one tick later and down onto the second line: both move, both switch.
    mouse(QMouseEvent.Type.MouseButtonPress, canvas._x(2.3), top0, left)
    mouse(QMouseEvent.Type.MouseMove, canvas._x(3.3), top1, left)
    mouse(QMouseEvent.Type.MouseButtonRelease, canvas._x(3.3), top1, Qt.MouseButton.NoButton)
    assert sorted((p.tick, p.pos) for p in document.pulses()) == [
        (3, (0, 1, 1)),
        (4, (0, 1, 1)),
        (7, (0, 1, 1)),
    ]
    # Del deletes the selected ones.
    window._changed()
    canvas.selected_pulses = {p.index for p in document.pulses() if p.tick in (3, 7)}
    canvas.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    )
    assert [(p.tick, p.pos) for p in document.pulses()] == [(4, (0, 1, 1))]
    document.dirty = False
    window.close()


def test_hovered_coordinates_light_up_and_groups_color_the_view(app: object) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.parse_state("sticky_piston[facing=east]"))
    document.add_pulse((0, 1, 0), 1, 15, 50)
    document.run_ticks(2)
    window._changed()
    document.lines.groups[0].color = "#00ff00"
    body = window.viewport._power_body()
    assert len(body) and abs(float(body[0, 4]) - 1.0) < 1e-6 and float(body[0, 3]) == 0.0
    window.viewport.selection = (0, 1, 0)
    window._changed()
    window.inspector.position_hovered.emit((0, 1, 0))  # the inspector's title hovered
    assert window.viewport.located == (0, 1, 0)
    assert len(window.viewport._highlight_body()) > 0
    window.inspector.position_hovered.emit(None)
    assert window.viewport.located is None
    document.dirty = False
    window.close()


def test_leaving_the_last_sequence_row_stops_the_highlight(app: object) -> None:
    from PySide6.QtCore import QPoint

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.document.setblock((0, 1, 0), blocks.parse_state("sticky_piston[facing=east]"))
    window.document.add_pulse((0, 1, 0), 2, 15, 2)
    window._changed()
    panel = window.sequence
    panel._hovered(0, 1)
    assert window.viewport.located == (0, 1, 0)
    panel._moved(QPoint(5, panel.table.viewport().height() - 2))  # below the only row
    assert window.viewport.located is None
    window.document.dirty = False
    window.close()


def test_opening_another_document_leaves_nothing_of_the_old_view(app: object) -> None:
    from redsim.editor.clipboard import Region
    from redsim.editor.document import Document
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    viewport = window.viewport
    window.document.setblock((0, 1, 0), blocks.STONE.default_state)
    viewport.region, viewport.region_locked = Region((0, 1, 0), (0, 1, 0)), True
    viewport.extra_regions = [Region((2, 1, 0), (2, 1, 0))]
    viewport.locate((0, 1, 0))
    viewport.flash((0, 1, 0))
    viewport.hover = Hit((0, 1, 0), Direction.UP, 4.0)
    window._open_block_popup()
    window.simulation.canvas.selected_pulses = {3}
    window._set_document(Document.new_flat())
    assert viewport.region is None and not viewport.region_locked and not viewport.extra_regions
    assert viewport.located is None and viewport.highlight is None and viewport.hover is None
    assert not window.block_popup.isVisible()
    assert not window.simulation.canvas.selected_pulses
    window.document.dirty = False
    window.close()


def test_closing_the_window_stops_its_timers(app: object) -> None:
    from PySide6.QtCore import QTimer

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    window.document.dirty = False
    window.close()
    assert not [t for t in window.findChildren(QTimer) if t.isActive()]


def test_pulses_mute_from_the_timeline_and_the_sequence_tab(app: object) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.parse_state("sticky_piston[facing=east]"))
    document.add_pulse((0, 1, 0), 2, 15, 3)
    window._changed()
    canvas = window.simulation.canvas
    canvas.expanded = {"power"}
    window._changed()
    canvas.selected_pulses = {document.pulses()[0].index}
    key = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_0, Qt.KeyboardModifier.NoModifier)
    canvas.keyPressEvent(key)  # 0: mute the selected pulses
    assert document.pulses()[0].muted
    window._changed()
    box = window.sequence.table.cellWidget(0, 4)
    assert box is not None
    check = box.findChild(QtWidgets.QCheckBox)
    assert check is not None and not check.isChecked()  # shown as off in the Sequence tab
    check.setChecked(True)  # back on
    assert not document.pulses()[0].muted
    # Lines are named by their position; what is there now follows as a dim detail.
    window._changed()
    line = next(line for line in canvas.lines if line.kind == "block")
    assert line.title == "0 1 0" and line.detail == "Sticky Piston"
    document.dirty = False
    window.close()
