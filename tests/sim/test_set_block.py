"""``Level.setBlock`` flag handling (doc/mechanics/neighbor-updates.md, setBlock steps)."""

from __future__ import annotations

from typing import Any

from redsim.sim.level import Level
from redsim.world import blocks
from redsim.world.block import UpdateFlags
from tests.sim.probe import VALUE, ProbeBlock

ORIGIN = (0, 0, 0)
WEST, EAST, DOWN, UP, NORTH, SOUTH = (
    (-1, 0, 0),
    (1, 0, 0),
    (0, -1, 0),
    (0, 1, 0),
    (0, 0, -1),
    (0, 0, 1),
)


def surround(level: Level, block: ProbeBlock) -> None:
    for pos in (WEST, EAST, DOWN, UP, NORTH, SOUTH):
        level.blocks[pos] = block.default_state


def test_flags_3_neighbor_updates_then_shape_updates() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    surround(level, ProbeBlock("n", log))
    level.set_block(ORIGIN, blocks.STONE.default_state, UpdateFlags.ALL)
    kinds = [(entry[0], entry[2]) for entry in log]
    neighbor = [("neighbor", p) for p in (WEST, EAST, DOWN, UP, NORTH, SOUTH)]
    shape = [("shape", p) for p in (WEST, EAST, NORTH, SOUTH, DOWN, UP)]
    assert kinds == neighbor + shape
    # The neighbor update carries the *old* block (Level.java L245: oldState.getBlock()).
    assert {entry[3] for entry in log if entry[0] == "neighbor"} == {"air"}


def test_shape_update_direction_points_at_the_changed_block() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    surround(level, ProbeBlock("n", log))
    level.set_block(ORIGIN, blocks.STONE.default_state, UpdateFlags.ALL)
    shapes = {entry[2]: entry[3] for entry in log if entry[0] == "shape"}
    assert shapes[WEST] == "east" and shapes[UP] == "down"


def test_flags_2_sends_only_shape_updates() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    surround(level, ProbeBlock("n", log))
    level.set_block(ORIGIN, blocks.STONE.default_state, UpdateFlags.CLIENTS)
    assert {entry[0] for entry in log} == {"shape"}


def test_flag_16_suppresses_shape_updates() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    surround(level, ProbeBlock("n", log))
    level.set_block(
        ORIGIN, blocks.STONE.default_state, UpdateFlags.CLIENTS | UpdateFlags.KNOWN_SHAPE
    )
    assert log == []


def test_same_state_is_a_no_op() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    surround(level, ProbeBlock("n", log))
    level.blocks[ORIGIN] = blocks.STONE.default_state
    assert level.set_block(ORIGIN, blocks.STONE.default_state, UpdateFlags.ALL) is False
    assert log == []


def test_on_place_runs_for_property_changes_without_removal() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    probe = ProbeBlock("p", log)
    probe.log_place = True
    level.blocks[ORIGIN] = probe.default_state
    level.set_block(ORIGIN, probe.default_state.with_(VALUE, 2), UpdateFlags.CLIENTS)
    assert ("place", "p", ORIGIN, 2) in log
    assert not any(entry[0] == "removed" for entry in log)


def test_removal_side_effects_need_block_change_and_flag_1_or_64() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    probe = ProbeBlock("p", log)
    level.blocks[ORIGIN] = probe.default_state
    level.set_block(ORIGIN, blocks.STONE.default_state, UpdateFlags.CLIENTS)  # flag 2 only
    assert not any(entry[0] == "removed" for entry in log)

    level.blocks[ORIGIN] = probe.default_state
    level.set_block(ORIGIN, blocks.STONE.default_state, UpdateFlags.ALL)
    assert ("removed", "p", ORIGIN, False) in log

    log.clear()
    level.blocks[ORIGIN] = probe.default_state
    level.set_block(
        ORIGIN, blocks.STONE.default_state, UpdateFlags.CLIENTS | UpdateFlags.MOVE_BY_PISTON
    )
    assert ("removed", "p", ORIGIN, True) in log


def test_shape_change_from_shape_update_sends_no_neighbor_updates() -> None:
    """``updateOrDestroy`` re-sets with flags lacking bit 1 (Q-UPD-SHAPE-NOUPD)."""
    log: list[tuple[Any, ...]] = []
    level = Level()
    reacting = ProbeBlock("r", log)
    reacting.on_shape = lambda state, direction: state.with_(VALUE, 1)
    watcher = ProbeBlock("w", log)
    level.blocks[EAST] = reacting.default_state
    level.blocks[(2, 0, 0)] = watcher.default_state  # neighbor of the reacting block only
    level.set_block(ORIGIN, blocks.STONE.default_state, UpdateFlags.ALL)
    assert level.get_block_state(EAST).get(VALUE) == 1
    assert not any(entry[0] == "neighbor" and entry[1] == "w" for entry in log)
    assert any(entry[0] == "shape" and entry[1] == "w" for entry in log)


def test_out_of_bounds_set_block_fails() -> None:
    level = Level(min_y=-64, max_y=319)
    assert level.set_block((0, 320, 0), blocks.STONE.default_state, UpdateFlags.ALL) is False
    assert level.set_block((0, -65, 0), blocks.STONE.default_state, UpdateFlags.ALL) is False
