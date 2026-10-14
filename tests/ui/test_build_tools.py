"""Block search ranking, recent blocks, icons, line placement and turning blocks."""

from __future__ import annotations

from typing import Any

import pytest
from PySide6 import QtWidgets

from redsim.core.direction import Direction
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest
from redsim.ui.block_search import rank_blocks
from redsim.world import blocks
from redsim.world.properties import FACING, POWER


@pytest.fixture(scope="module")
def app() -> Any:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_search_ranks_prefixes_then_words_then_fuzzy() -> None:
    ids = [block_id for block_id, _ in rank_blocks("rep", [])]
    assert ids[0] == "minecraft:repeater"
    assert rank_blocks("sticky", [])[0][0] == "minecraft:sticky_piston"
    assert rank_blocks("obsrv", [])[0][0] == "minecraft:observer"  # letters in order
    assert rank_blocks("qqqq", []) == []
    recent = ["minecraft:hopper", "minecraft:target"]
    assert [b for b, _ in rank_blocks("", recent)][:2] == recent


def test_recent_blocks_are_remembered_and_saved(app: Any) -> None:
    from redsim.ui.inventory import InventoryBar, load_recent

    bar = InventoryBar()
    bar.remember("minecraft:repeater")
    bar.remember("minecraft:redstone_wire")
    bar.remember("minecraft:repeater")
    assert bar.recent[:2] == ["minecraft:repeater", "minecraft:redstone_wire"]
    assert load_recent()[:2] == bar.recent[:2]
    bar.nav.path = [0, 7]  # Redstone › Switches
    bar.refresh()
    bar.go_to_depth(1)
    assert bar.nav.breadcrumb() == ["Redstone"]
    # Regression: going back after a refresh touched already deleted path buttons.
    from PySide6.QtCore import QCoreApplication, QEvent

    def run_deletes() -> None:  # what the event loop does with deleteLater
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    for _ in range(3):
        bar.press(8)  # Switches
        run_deletes()
        bar.go_up()
        run_deletes()
    bar.go_up()
    assert bar.nav.breadcrumb() == []


def test_every_inventory_block_has_a_preview(app: Any) -> None:
    from redsim.ui.icons import block_pixmap
    from redsim.ui.inventory import all_blocks

    for block_id, _ in all_blocks():
        image = block_pixmap(block_id, 24).toImage()
        assert any(image.pixelColor(x, y).alpha() for x in range(24) for y in range(24)), block_id


def test_a_dragged_line_is_one_batch_and_one_undo_step() -> None:
    doc = Document.new_flat()
    doc.setblock((-1, 1, 0), blocks.REDSTONE_BLOCK.default_state)
    doc.setblock((2, 1, 0), blocks.STONE.default_state)  # in the way: skipped
    cells = [(x, 1, 0) for x in range(5)]
    request = PlaceRequest(Direction.UP, 90.0, 60.0)
    assert doc.place_many(cells, blocks.REDSTONE_WIRE, request) == 4
    assert doc.state_at((1, 1, 0)).get(POWER) == 14
    doc.run_ticks(3)
    doc.place_many([(0, 1, 2), (1, 1, 2)], blocks.REDSTONE_WIRE, request)
    batches = doc.edit_batches()
    assert len(batches) == 1 and batches[0].tick == 3 and len(batches[0].indices) == 2
    assert doc.undo() and doc.edit_batches() == []
    assert doc.undo() and doc.state_at((0, 1, 0)).is_air  # the whole line at once


def test_right_click_turns_vertical_facings_too(app: Any) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.parse_state("observer[facing=up]"))
    window._rotate_block_at((0, 1, 0), 1)
    assert document.state_at((0, 1, 0)).get(FACING) is not Direction.UP
    document.setblock((2, 1, 0), blocks.parse_state("repeater[facing=north]"))
    window._rotate_block_at((2, 1, 0), 1)
    assert document.state_at((2, 1, 0)).get(blocks.REPEATER.properties[0]) is Direction.EAST
    window.document.dirty = False
    window.close()


def test_viewport_line_cells_follow_the_main_axis(app: Any) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    viewport = window.viewport
    viewport._line = (0, 1, 0)
    viewport._line_end = (5, 1, 2)
    assert viewport.line_cells() == [(x, 1, 0) for x in range(6)]
    viewport._line_end = (1, 1, -3)
    assert viewport.line_cells() == [(0, 1, -z) for z in range(4)]
    viewport._line = None
    window.document.dirty = False
    window.close()


def test_playing_backwards_stops_at_tick_0(app: Any) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    document = window.document
    document.setblock((0, 1, 0), blocks.REDSTONE_LAMP.default_state)
    document.run_ticks(10)
    bar = window.simulation
    bar.warp.setChecked(True)
    bar.reverse.setChecked(True)
    assert bar.backwards and not bar.play.isChecked()
    for _ in range(50):  # each call runs what fits its time budget (as each frame does)
        window._play_tick()
        if not bar.reverse.isChecked():
            break
    assert document.tick == 0 and not bar.reverse.isChecked()
    bar.play.setChecked(True)
    bar.reverse.setChecked(True)
    assert not bar.play.isChecked()  # one direction at a time
    bar.stop()
    window.document.dirty = False
    window.close()


def test_build_mode_places_on_the_camera_layer(app: Any) -> None:
    from PySide6.QtCore import QPoint

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    viewport = window.viewport
    viewport.camera.pivot[1] = 3.5  # the working layer is y = 3, in the air
    target = viewport.build_target(QPoint(viewport.width() // 2, viewport.height() // 2))
    assert target is not None and target[1] == 3
    keymap = viewport.keymap
    assert keymap.mouse_action("build", frozenset({"Shift"}), None, "Wheel") == "build.layer"
    assert keymap.mouse_action("build", frozenset(), None, "Wheel") == "build.zoom"
    window.document.dirty = False
    window.close()


def test_inventory_stack_grows_upwards(app: Any) -> None:
    """Every folder level is a row of the same hotbar slots: the root row stays at the
    bottom, opening a folder adds its row above (nothing changes its look)."""
    from redsim.ui.inventory import InventoryBar

    bar = InventoryBar()
    bar.resize(1200, 300)
    root_spots = bar.canvas._layout()
    root_top = min(s.rect.top() for s in root_spots if s.kind == "slot")
    bar.press(1)  # Redstone
    bar.press(8)  # Switches
    spots = bar.canvas._layout()
    rows = {}
    for spot in spots:
        if spot.kind == "slot":
            rows.setdefault(spot.depth, set()).add((spot.rect.top(), spot.rect.height()))
    assert all(len(r) == 1 for r in rows.values())  # one row per level, same slot size
    tops = {depth: next(iter(r))[0] for depth, r in rows.items()}
    assert tops[2] < tops[1] < tops[0]  # root lowest, deeper above
    assert len({next(iter(r))[1] for r in rows.values()}) == 1
    names = [s.title for s in spots if s.kind == "slot" and s.depth == 2]
    assert names[0] in ("Lever", "lever")
    assert root_top == min(s.rect.top() for s in root_spots if s.kind == "slot")
    bar.pick_at_level(0, 1)  # the Movement slot of the root row
    assert bar.nav.breadcrumb() == ["Movement"]


def test_pixel_font_and_theme(app: Any) -> None:
    from redsim.ui import theme

    assert theme.text_width("Redstone") > 0 and theme.line_height(2) >= 16
    font = theme.PixelFont.load()
    if font is not None:  # the client jar is there: the game's font
        assert font.advance("i") < font.advance("W")  # proportional, like the game
        assert font.advance(" ") == 4


def test_camera_glides_but_the_build_layer_jumps_at_once(app: Any) -> None:
    import numpy as np

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    viewport = window.viewport
    viewport.camera.pivot = np.array([0.5, 1.5, 0.5])
    start = viewport.camera.distance
    viewport.glide_to(pivot=np.array([0.5, 4.5, 0.5]), distance=start * 2)
    assert viewport.working_height() == 4  # placement follows the target immediately
    assert viewport.camera.pivot[1] == 1.5  # the view eases there
    viewport._advance_glide(0.02)
    assert 1.5 < viewport.camera.pivot[1] < 4.5
    for _ in range(100):
        viewport._advance_glide(0.02)
    assert viewport._glide is None and viewport.camera.distance == start * 2
    window.document.dirty = False
    window.close()


def test_layer_grid_fades_and_drop_lines_reach_the_ground(app: Any) -> None:
    import numpy as np

    from redsim.editor.clipboard import Region
    from redsim.ui.main_window import MainWindow
    from redsim.ui.viewport import GRID_ALPHA, _layer_grid

    grid = _layer_grid(Region((0, 3, 0), (0, 3, 0)))
    assert np.allclose(grid[:, 1], 3.01)  # just above the layer's floor
    alphas = {(x, z): a for x, _, z, *_, a in grid}
    assert alphas[(0, 0)] == pytest.approx(GRID_ALPHA)  # the target cell's corner: full
    assert alphas[(4, 0)] < alphas[(2, 0)] < GRID_ALPHA  # fading with distance
    window = MainWindow()  # floor at y=0: the box at y=3 floats, so it gets drop lines
    parts = window.viewport._paste_guides(Region((0, 3, 0), (1, 3, 1)))
    drops = [p for p in parts[1:] if p[0, 1] != p[1, 1]]
    assert len(drops) == 4 and all(p[1, 1] == 1 for p in drops)
    window.document.dirty = False
    window.close()


def test_window_layout_round_trips(app: Any) -> None:
    from redsim.ui.main_window import MainWindow
    from redsim.ui.preferences import load_window_layout

    window = MainWindow()
    assert not window.restore_layout()  # nothing saved yet (private config folder)
    window.resize(1000, 700)
    window.show()
    QtWidgets.QApplication.processEvents()
    window.document.dirty = False
    window.close()  # saves the layout
    assert set(load_window_layout()) == {"geometry", "state", "timeline"}
    again = MainWindow()
    assert again.restore_layout()
    again.show()
    QtWidgets.QApplication.processEvents()
    # Qt fits restored geometry onto the screen: the offscreen test platform's screen is
    # only 800 px wide, so compare sizes only where the saved one fits.
    screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
    if screen.width() >= 1100 and screen.height() >= 800:
        assert abs(again.width() - 1000) <= 4 and abs(again.height() - 700) <= 4
    again.document.dirty = False
    again.close()


def test_preferences_looks_follow_the_view_menu(app: Any) -> None:
    from redsim.ui.main_window import MainWindow
    from redsim.ui.panels import PreferencesDialog

    window = MainWindow()
    dialog = PreferencesDialog(window.viewport.preferences, window)
    dialog.look_changed.connect(window._apply_look)
    dialog.looks["scenery"].setChecked(False)
    assert not window.viewport.preferences.scenery
    assert not window._scenery_action.isChecked()
    dialog.looks["scenery"].setChecked(True)
    assert window._scenery_action.isChecked()
    window.document.dirty = False
    window.close()


def test_chosen_block_name_fades_like_the_game(app: Any) -> None:
    from redsim.ui.inventory import NAME_FADED, InventoryBar

    bar = InventoryBar()
    bar.resize(800, 120)
    bar.show()
    QtWidgets.QApplication.processEvents()  # exposed: repaint() paints at once
    bar.select_block(blocks.REPEATER)
    canvas = bar.canvas
    canvas.repaint()
    assert canvas.name_alpha == 1.0 and canvas._fade_delay.isActive()
    canvas._fade_delay.timeout.emit()  # the delay is over: fade out
    canvas._fade.setCurrentTime(canvas._fade.duration())
    assert canvas.name_alpha == pytest.approx(NAME_FADED)
    bar.select_block(blocks.COMPARATOR)  # a new choice shows at full strength again
    canvas.repaint()
    assert canvas.name_alpha == 1.0
    bar.close()


def test_region_buttons_show_confirmed_and_availability(app: Any) -> None:
    from redsim.editor.clipboard import Region
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window._update_hints()
    assert not window._region_buttons["edit.copy"].isEnabled()  # nothing selected: dim
    assert not window._region_buttons["edit.delete"].isEnabled()  # Del: selections only
    window.viewport.region = Region((0, 1, 0), (1, 1, 1))
    window._update_hints()
    assert window._region_buttons["edit.copy"].isEnabled()
    window._confirm()
    window._update_hints()
    assert window._lock_action.isChecked()
    window._confirm()
    window._update_hints()
    assert not window._lock_action.isChecked()
    window.document.dirty = False
    window.close()


def test_monitor_track_reads_the_value_under_the_cursor(app: Any) -> None:
    from redsim.ui.timeline import TimelineCanvas, Track

    canvas = TimelineCanvas()
    canvas.resize(600, 200)
    canvas.set_data(0, 20, 20, [], [Track((1, 1, 0), "Redstone Dust", {5: 15, 6: 14})])
    canvas.view_start, canvas.view_span = 0.0, 20.0
    width = canvas.width() - canvas.LABEL_WIDTH
    x = canvas.LABEL_WIDTH + 5.5 / 20 * width  # inside tick 5's column
    y = canvas._tracks_top() + canvas.ROW_HEIGHT / 2
    assert canvas.track_reading(x, y) == "Redstone Dust 1 1 0 · tick 5: 15"
    assert canvas.track_reading(x, 2) is None  # on the ruler: no track


def test_player_row_shows_only_for_lecterns(app: Any) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    request = PlaceRequest(Direction.UP, 0.0, 30.0)
    window.document.place_source((0, 1, 0), "barrel", 7, request)
    window.document.place_source((2, 1, 0), "lectern", 7, request)
    form = window.inspector._source_form
    window._select((0, 1, 0))
    assert not form.isRowVisible(window.inspector.page_row)  # no "Player" label alone
    window._select((2, 1, 0))
    assert form.isRowVisible(window.inspector.page_row)
    window.document.dirty = False
    window.close()


def test_signal_steppers_get_a_meter(app: Any) -> None:
    from redsim.ui.panels import _Stepper

    power = _Stepper(tuple(range(16)), lambda v: None, "power")
    power.show_value(9)
    assert power.meter is not None and power.meter.level == 9
    delay = _Stepper((1, 2, 3, 4), lambda v: None, "delay")  # not a signal strength
    assert delay.meter is None


def test_undo_history_menu_undoes_several_steps(app: Any) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    request = PlaceRequest(Direction.UP, 0.0, 30.0)
    for x in range(3):
        window.document.place((x, 1, 0), blocks.REDSTONE_LAMP, request)
    window._fill_history_menu()
    entries = window._history_menu.actions()
    assert [a.text() for a in entries] == ["Place Redstone Lamp"] * 3
    entries[1].trigger()  # back to before the second lamp
    assert window.document.state_at((0, 1, 0)).is_(blocks.REDSTONE_LAMP)
    assert window.document.state_at((1, 1, 0)).is_air
    window.document.dirty = False
    window.close()


def test_markers_get_a_strip_in_the_ruler(app: Any) -> None:
    from redsim.ui.timeline import TimelineCanvas

    canvas = TimelineCanvas()
    canvas.resize(600, 200)
    canvas.view_start, canvas.view_span = 0.0, 20.0
    plain = canvas.RULER_HEIGHT
    canvas.set_markers({5: "clock on"})
    assert plain + canvas.MARKER_STRIP == canvas.RULER_HEIGHT
    assert canvas.marker_at(canvas._x(5) + 2, canvas.RULER_HEIGHT - 4) == 5
    assert canvas.marker_at(canvas._x(9), canvas.RULER_HEIGHT - 4) is None
    canvas.set_markers({})
    assert plain == canvas.RULER_HEIGHT


def test_hint_bar_keeps_its_height_in_every_mode(app: Any) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    heights = set()
    for mode in ("normal", "build", "select"):
        window.viewport.set_mode(mode)
        window._update_hints()
        QtWidgets.QApplication.processEvents()
        heights.add((window.hint_bar.height(), window.viewport.height()))
    assert len(heights) == 1  # nothing above it resizes
    window.document.dirty = False
    window.close()


def test_playhead_glides_while_playing_and_snaps_when_paused(app: Any) -> None:
    import time

    from redsim.ui.timeline import GLIDE_LOOKAHEAD, TimelineCanvas

    canvas = TimelineCanvas()
    canvas.set_data(0, 10, 10, [], [])
    canvas.set_running(20.0)
    start = time.monotonic()
    assert canvas.shown_tick(start) == pytest.approx(10.0, abs=0.1)
    assert 10.5 < canvas.shown_tick(start + 0.05) < 11.5  # gliding towards tick 11
    assert canvas.shown_tick(start + 5.0) == pytest.approx(10 + max(1.0, 20 * GLIDE_LOOKAHEAD))
    before = canvas.shown_tick()
    canvas.set_data(0, 11, 11, [], [])  # the next known tick: no jump backwards
    assert canvas.shown_tick() >= before
    canvas.set_running(None)
    assert canvas.shown_tick() == 11.0  # paused: exactly on the tick


def test_hotbar_is_a_build_mode_overlay_with_recent_blocks(app: Any) -> None:
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    QtWidgets.QApplication.processEvents()
    assert window.inventory.parent() is window.viewport  # drawn over the 3D view
    assert not window.inventory.isVisible()  # NORMAL mode: no hotbar
    height = window.viewport.height()
    window._inventory_key(1)  # a number key goes to BUILD and opens the first folder
    QtWidgets.QApplication.processEvents()
    assert window.viewport.mode == "build" and window.inventory.isVisible()
    assert window.viewport.height() == height  # nothing resized
    inventory = window.inventory
    inventory.current = "minecraft:observer"
    inventory.set_favourite(1, "minecraft:observer")  # right click on slot 2
    inventory.current = None
    inventory.pick_favourite(1)  # Alt+2
    assert inventory.current == "minecraft:observer"
    assert window.keymap.bindings("recent.2") == ("Alt+2",)
    inventory.switch_palette(1)  # another palette: slot 2 is empty there
    inventory.current = None
    inventory.pick_favourite(1)
    assert inventory.current is None and inventory.palette_index == 1
    inventory.switch_palette(-1)
    assert inventory.favourites[0][1] == "minecraft:observer"
    window.document.dirty = False
    window.close()


def test_build_keys_vary_the_block_to_place(app: Any) -> None:
    from redsim.editor.clipboard import Region
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    window.viewport.region = Region((5, 1, 5), (6, 1, 6))  # a selection that must not turn
    window.inventory.select_block(blocks.SMOOTH_STONE_SLAB)  # BUILD mode
    window._flip(depth=True)  # Shift+H: upside down → a top slab
    assert window.viewport.build_upside_down
    assert "upside down" in window.viewport.mode_status()
    window._place((0, 1, 0))
    assert "type=top" in repr(window.document.state_at((0, 1, 0)))
    window._rotate(1)  # R in BUILD turns the block to place, not the selection
    assert window.viewport.build_turns == 1
    assert window.viewport.region == Region((5, 1, 5), (6, 1, 6))
    window.inventory.select_block(blocks.REPEATER)  # another block starts plain
    assert window.viewport.build_variant() == ""
    window.document.dirty = False
    window.close()


def test_pivot_is_a_block_with_a_shadow_on_the_ground(app: Any) -> None:
    import numpy as np

    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    viewport = window.viewport
    viewport.camera.pivot = np.array([0.5, 4.5, 0.5])
    assert viewport.pivot_ground() == 1.0  # the floor's top
    window.document.place((0, 2, 0), blocks.STONE, PlaceRequest(Direction.UP, 0.0, 30.0))
    assert viewport.pivot_ground() == 3.0  # now the stone's top
    shadow = viewport._pivot_shadow()
    assert np.allclose(shadow[:, 1], 3.01) and (shadow[:, 6] > 0).all()
    assert len(viewport._pivot_lines()) == 2  # the drop line to it
    window.document.dirty = False
    window.close()


def test_selection_fill_breathes(app: Any) -> None:
    from redsim.ui.main_window import MainWindow
    from redsim.ui.viewport import BODY_ALPHA, BODY_PULSE, PULSE_SECONDS

    window = MainWindow()
    viewport = window.viewport
    values = [viewport.body_alpha(t * PULSE_SECONDS / 8) for t in range(8)]
    assert min(values) >= BODY_ALPHA - BODY_PULSE - 1e-9 and max(values) > min(values)
    window.document.dirty = False
    window.close()
