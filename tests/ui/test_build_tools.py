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
    bar.nav.path = [0, 8]  # Redstone › Switches
    bar.refresh()
    bar.go_to_depth(1)
    assert bar.nav.breadcrumb() == ["Redstone"]


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
    from redsim.ui.geometry import Hit
    from redsim.ui.main_window import MainWindow

    window = MainWindow()
    viewport = window.viewport
    viewport._line = ((0, 1, 0), Hit((0, 0, 0), Direction.UP, 1.0))
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
    window._play_tick()
    assert document.tick == 0 and not bar.reverse.isChecked()
    bar.play.setChecked(True)
    bar.reverse.setChecked(True)
    assert not bar.play.isChecked()  # one direction at a time
    bar.stop()
    window.document.dirty = False
    window.close()
