"""Editor layer: placement orientation, document edits, undo, files (no Qt needed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from redsim.core.direction import Direction
from redsim.editor.document import Document, EditError
from redsim.editor.placement import (
    PlaceRequest,
    horizontal_direction,
    nearest_looking_directions,
    ordered_by_nearest,
)
from redsim.world import blocks
from redsim.world.properties import ATTACH_FACE, HORIZONTAL_FACING, LIT, POWERED


def test_horizontal_direction_follows_minecraft_yaw() -> None:
    assert horizontal_direction(0) is Direction.SOUTH
    assert horizontal_direction(90) is Direction.WEST
    assert horizontal_direction(180) is Direction.NORTH
    assert horizontal_direction(270) is Direction.EAST
    assert horizontal_direction(-90) is Direction.EAST
    assert horizontal_direction(44) is Direction.SOUTH


def test_ordered_by_nearest_looking_down_south() -> None:
    order = ordered_by_nearest(yaw=0, pitch=60)
    assert order[0] is Direction.DOWN
    assert order[1] is Direction.SOUTH
    assert order[-1] is Direction.UP


def test_clicked_face_opposite_comes_first() -> None:
    request = PlaceRequest(Direction.EAST, yaw=0, pitch=10)  # clicked a block's east face
    assert nearest_looking_directions(request)[0] is Direction.WEST


def test_lever_on_wall_and_on_floor() -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.STONE, PlaceRequest(Direction.UP, yaw=0, pitch=45))
    # Clicking the stone's east face places a wall lever east of it, pointing east.
    doc.place((1, 1, 0), blocks.LEVER, PlaceRequest(Direction.EAST, yaw=90, pitch=0))
    state = doc.state_at((1, 1, 0))
    assert state.get(ATTACH_FACE) == "wall" and state.get(HORIZONTAL_FACING) is Direction.EAST
    # Clicking the floor from the north places a floor lever facing the player's direction.
    doc.place((3, 1, 3), blocks.LEVER, PlaceRequest(Direction.UP, yaw=180, pitch=50))
    floor = doc.state_at((3, 1, 3))
    assert floor.get(ATTACH_FACE) == "floor" and floor.get(HORIZONTAL_FACING) is Direction.NORTH


def test_torch_on_top_or_wall() -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.STONE, PlaceRequest(Direction.UP, yaw=0, pitch=45))
    doc.place((0, 2, 0), blocks.REDSTONE_TORCH, PlaceRequest(Direction.UP, yaw=0, pitch=60))
    assert doc.state_at((0, 2, 0)).is_(blocks.REDSTONE_TORCH)
    doc.place((0, 1, 1), blocks.REDSTONE_TORCH, PlaceRequest(Direction.SOUTH, yaw=0, pitch=0))
    wall = doc.state_at((0, 1, 1))
    assert wall.is_(blocks.REDSTONE_WALL_TORCH)
    assert wall.get(HORIZONTAL_FACING) is Direction.SOUTH


def test_repeater_points_away_from_the_player() -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.REPEATER, PlaceRequest(Direction.UP, yaw=180, pitch=40))
    # Player looks north: input on the player's side (south), output north.
    assert doc.state_at((0, 1, 0)).get(HORIZONTAL_FACING) is Direction.SOUTH


def test_unsupported_placement_is_rejected() -> None:
    doc = Document.new_flat()
    with pytest.raises(EditError):
        doc.place((0, 5, 0), blocks.REDSTONE_WIRE, PlaceRequest(Direction.UP, yaw=0, pitch=0))


def test_use_undo_redo() -> None:
    doc = Document.new_flat()
    request = PlaceRequest(Direction.UP, yaw=0, pitch=60)
    doc.place((0, 1, 0), blocks.LEVER, request)
    doc.place((1, 1, 0), blocks.REDSTONE_LAMP, request)
    doc.use((0, 1, 0))
    assert doc.state_at((1, 1, 0)).get(LIT) is True
    assert doc.undo()
    assert doc.state_at((0, 1, 0)).get(POWERED) is False
    assert doc.state_at((1, 1, 0)).get(LIT) is False
    assert doc.redo()
    assert doc.state_at((1, 1, 0)).get(LIT) is True


def test_edits_blocked_mid_tick() -> None:
    doc = Document.new_flat()
    request = PlaceRequest(Direction.UP, yaw=0, pitch=60)
    doc.place((0, 1, 0), blocks.REDSTONE_BLOCK, request)
    doc.place((1, 1, 0), blocks.REPEATER, PlaceRequest(Direction.UP, yaw=270, pitch=60))
    doc.step()  # tick start collects the repeater's placement tick: now inside a tick
    with pytest.raises(EditError):
        doc.place((2, 1, 0), blocks.STONE, request)


def test_save_and_open_keep_sections(tmp_path: Path) -> None:
    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.LEVER, PlaceRequest(Direction.UP, yaw=0, pitch=60))
    doc.assign_section((0, 1, 0), "input")
    path = tmp_path / "circuit.redsim.json"
    doc.save(path)
    opened = Document.open(path)
    section = opened.sections.section_at((0, 1, 0))
    assert section is not None and section.name == "input"
    assert opened.state_at((0, 1, 0)).is_(blocks.LEVER)
    assert not opened.dirty


def test_usable_blocks() -> None:
    assert Document.is_usable(blocks.LEVER)
    assert Document.is_usable(blocks.REPEATER)
    assert not Document.is_usable(blocks.STONE)


def test_blender_like_jumps_through_the_history() -> None:
    from redsim.world import blocks as b

    doc = Document.new_flat()
    doc.run_ticks(3)
    doc.setblock((0, 1, 0), b.REDSTONE_BLOCK.default_state)  # edit 1 at game time 3
    doc.run_ticks(4)
    doc.setblock((1, 1, 0), b.REDSTONE_LAMP.default_state)  # edit 2 at game time 7
    doc.run_ticks(2)
    assert doc.engine.game_time == 9
    assert doc.jump("start") and doc.engine.game_time == 0
    assert not doc.jump("start")
    assert doc.jump("next") and doc.state_at((0, 1, 0)).is_(b.REDSTONE_BLOCK)
    assert doc.engine.game_time == 3 and doc.state_at((1, 1, 0)).is_air
    assert doc.jump("next") and doc.state_at((1, 1, 0)).is_(b.REDSTONE_LAMP)
    assert not doc.jump("next")
    assert doc.jump("end") and doc.engine.game_time == 9
    assert doc.jump("previous") and doc.engine.game_time == 7
    assert doc.jump("previous") and doc.engine.game_time == 3


def test_hopper_points_into_the_clicked_block_or_down() -> None:
    from redsim.world.properties import FACING_HOPPER

    doc = Document.new_flat()
    doc.place((0, 1, 0), blocks.HOPPER, PlaceRequest(Direction.UP, 0.0, 60.0))
    assert doc.state_at((0, 1, 0)).get(FACING_HOPPER) is Direction.DOWN
    doc.setblock((2, 1, 0), blocks.STONE.default_state)
    # Clicking the stone's west face from (1, 1, 0): the spout points east, into the stone.
    doc.place((1, 1, 0), blocks.HOPPER, PlaceRequest(Direction.WEST, -90.0, 0.0))
    assert doc.state_at((1, 1, 0)).get(FACING_HOPPER) is Direction.EAST


def test_container_slots_are_set_as_setblock_data_and_update_comparators() -> None:
    from redsim.editor.monitor import monitor_value
    from redsim.world.blocks.hopper import HopperBlockEntity

    doc = Document.new_flat()
    doc.setblock((0, 1, 0), blocks.parse_state("hopper[facing=down]"))
    doc.setblock((0, 1, 1), blocks.parse_state("comparator[facing=north]"))
    doc.set_container_slot((0, 1, 0), 2, "minecraft:ender_pearl", 40)  # capped at 16
    doc.run_ticks(2)
    hopper = doc.level.get_block_entity((0, 1, 0))
    assert isinstance(hopper, HopperBlockEntity)
    assert hopper.items[2] == ("minecraft:ender_pearl", 16)
    assert monitor_value(doc.level, (0, 1, 0)) == 3  # one full 16-stack of 5 slots
    assert monitor_value(doc.level, (0, 1, 1)) == 3  # the comparator saw it
    doc.set_container_slot((0, 1, 0), None, None, 0)
    assert hopper.is_empty()
    with pytest.raises(EditError):
        doc.set_container_slot((0, 1, 1), 0, "minecraft:stone", 1)


def test_undo_history_labels_and_multi_step_undo() -> None:
    doc = Document.new_flat()
    request = PlaceRequest(Direction.UP, yaw=0, pitch=60)
    doc.place((0, 1, 0), blocks.LEVER, request)
    doc.place((1, 1, 0), blocks.REDSTONE_LAMP, request)
    doc.use((0, 1, 0))
    assert doc.undo_labels == ["use lever", "place redstone_lamp", "place lever"]
    assert doc.undo_to(2)  # back to just the lever, in one re-run
    assert doc.state_at((1, 1, 0)).is_air and doc.state_at((0, 1, 0)).is_(blocks.LEVER)
    assert doc.undo_labels == ["place lever"]
    assert doc.redo()  # redo brings back the lamp first, with its label
    assert doc.state_at((1, 1, 0)).is_(blocks.REDSTONE_LAMP)
    assert doc.undo_labels == ["place redstone_lamp", "place lever"]
    assert doc.redo()
    assert doc.state_at((1, 1, 0)).get(LIT) is True
    assert not doc.undo_to(0)


def test_markers_follow_tick_zero_and_its_undo(tmp_path: Path) -> None:
    doc = Document.new_flat()
    request = PlaceRequest(Direction.UP, yaw=0, pitch=60)
    doc.place((0, 1, 0), blocks.REDSTONE_LAMP, request)
    for _ in range(10):
        doc.run_tick()
    doc.set_marker(3, "lamp on")
    doc.set_marker(8, "check")
    doc.seek_tick(5)
    doc.set_tick_zero()  # tick 5 becomes tick 0: markers move along
    assert doc.visible_markers() == {3: "check"}
    assert doc.undo()  # and come back, including the one before the new tick 0
    assert doc.visible_markers() == {3: "lamp on", 8: "check"}
    assert doc.redo()
    assert doc.visible_markers() == {3: "check"}
    doc.save(tmp_path / "markers.redsim.json")
    assert Document.open(tmp_path / "markers.redsim.json").markers == {3: "check"}
    doc.set_marker(3, "")
    assert doc.visible_markers() == {}
