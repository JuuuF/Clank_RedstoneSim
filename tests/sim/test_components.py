"""Unit tests for levers, buttons, lamps, torches and wire (doc/mechanics/*)."""

from __future__ import annotations

from redsim.core.direction import ALL, Direction
from redsim.core.javahash import JavaHashSet
from redsim.core.pos import Pos, java_hash, offset
from redsim.sim import trace as tr
from redsim.world.properties import LIT, POWER, POWERED
from tests.sim.bench import Bench

# ----------------------------------------------------------------------------- lever


def test_lever_strongly_powers_only_its_attached_block() -> None:
    b = Bench()
    b.place((1, 1, 0), "stone")
    b.place((0, 1, 0), "lever[face=wall,facing=west]")  # attached to (1, 1, 0)
    b.use((0, 1, 0))
    level = b.level
    assert level.get_direct_signal_to((1, 1, 0)) == 15
    assert level.get_signal((1, 1, 0), Direction.UP) == 15  # conductor passes it on
    assert level.get_direct_signal_to((0, 0, 0)) == 0  # floor below the lever: weak only
    assert level.get_signal((0, 1, 0), Direction.NORTH) == 15  # weak power to all sides


def test_lever_through_block_lights_lamp_immediately() -> None:
    b = Bench()
    b.place((1, 1, 0), "stone")
    b.place((2, 1, 0), "redstone_lamp")
    b.place((0, 1, 0), "lever[face=wall,facing=west]")
    b.use((0, 1, 0))
    assert b.get((2, 1, 0), LIT) is True
    b.use((0, 1, 0))
    b.tick(3)
    assert b.get((2, 1, 0), LIT) is True
    b.tick(1)
    assert b.get((2, 1, 0), LIT) is False


def test_lever_toggle_updates_its_own_neighbors_twice() -> None:
    """``LeverBlock.pull``: setBlockAndUpdate, then updateNeighbours (Q-LEVER-DOUBLE)."""
    b = Bench()
    b.place((0, 1, 0), "lever[face=floor,facing=north]")
    start = len(b.level.trace.records)
    b.use((0, 1, 0))
    multi_sources = [
        r.detail["source_pos"]
        for r in b.level.trace.records[start:]
        if r.kind == tr.NEIGHBOR_UPDATE and r.detail["source"] == "lever"
    ]
    # 6 updates around the lever (setBlock) + 6 again + 6 around the floor block below.
    assert multi_sources.count((0, 1, 0)) == 12
    assert multi_sources.count((0, 0, 0)) == 6


# ----------------------------------------------------------------------------- buttons


def test_stone_button_releases_after_20_ticks_and_oak_after_30() -> None:
    b = Bench()
    b.place((0, 1, 0), "stone_button[face=floor,facing=north]")
    b.place((5, 1, 0), "oak_button[face=floor,facing=north]")
    b.use((0, 1, 0))
    b.use((5, 1, 0))
    b.tick(19)
    assert b.get((0, 1, 0), POWERED) is True
    b.tick(1)
    assert b.get((0, 1, 0), POWERED) is False
    b.tick(9)
    assert b.get((5, 1, 0), POWERED) is True
    b.tick(1)
    assert b.get((5, 1, 0), POWERED) is False


def test_pressing_a_pressed_button_does_nothing() -> None:
    b = Bench()
    b.place((0, 1, 0), "stone_button[face=floor,facing=north]")
    b.use((0, 1, 0))
    b.tick(10)
    b.use((0, 1, 0))  # no re-press: the release tick stays at t=20
    b.tick(10)
    assert b.get((0, 1, 0), POWERED) is False


def test_attached_component_pops_without_support() -> None:
    b = Bench()
    b.place((1, 1, 0), "stone")
    b.place((0, 1, 0), "lever[face=wall,facing=west]")
    b.break_block((1, 1, 0))
    assert b.state((0, 1, 0)).is_air


# ----------------------------------------------------------------------------- torch


def test_torch_strongly_powers_block_above_but_not_its_support() -> None:
    b = Bench()
    b.place((0, 1, 0), "stone")
    b.place((0, 2, 0), "redstone_torch")
    b.place((0, 3, 0), "stone")
    level = b.level
    assert level.get_direct_signal_to((0, 3, 0)) == 15
    assert level.get_signal((0, 2, 0), Direction.DOWN) == 15  # into the block above
    assert level.get_signal((0, 2, 0), Direction.UP) == 0  # into its support block


def test_wall_torch_reads_attached_block_and_inverts_after_2_ticks() -> None:
    b = Bench()
    b.place((1, 1, 0), "stone")
    b.place((2, 1, 0), "redstone_wall_torch[facing=east]")
    b.place((0, 1, 0), "lever[face=wall,facing=west]")
    b.use((0, 1, 0))
    b.tick(1)
    assert b.get((2, 1, 0), LIT) is True
    b.tick(1)
    assert b.get((2, 1, 0), LIT) is False


def test_torch_burnout_needs_eight_offs_within_sixty_ticks() -> None:
    from redsim.world.blocks.torch import is_toggled_too_frequently

    b = Bench()
    level = b.level
    pos: Pos = (0, 1, 0)
    for t in range(7):
        level.game_time = t * 8
        assert is_toggled_too_frequently(level, pos, True) is False
    level.game_time = 56
    assert is_toggled_too_frequently(level, pos, True) is True
    assert is_toggled_too_frequently(level, (5, 1, 0), False) is False


# ----------------------------------------------------------------------------- wire


def test_wire_decays_by_one_per_block_and_steps_up_and_down() -> None:
    b = Bench()
    b.place((0, 1, 0), "redstone_block")
    b.place((1, 1, 0), "redstone_wire")
    b.place((2, 1, 0), "stone")
    b.place((2, 2, 0), "redstone_wire")  # step up onto the block
    b.place((3, 1, 0), "redstone_wire")  # step down on the far side
    assert b.get((1, 1, 0), POWER) == 15
    assert b.get((2, 2, 0), POWER) == 14
    assert b.get((3, 1, 0), POWER) == 13


def test_conductor_above_cuts_the_step_up() -> None:
    b = Bench()
    b.place((0, 1, 0), "redstone_block")
    b.place((1, 1, 0), "redstone_wire")
    b.place((2, 1, 0), "stone")
    b.place((2, 2, 0), "redstone_wire")
    b.place((1, 2, 0), "stone")  # conductor above the lower wire
    assert b.get((2, 2, 0), POWER) == 0


def test_glass_lets_power_climb_but_not_descend() -> None:
    """Glass is not a conductor. A lower wire reads the wire *below* a non-conductor
    neighbor, never the wire on top of it, so signals go up glass but not down
    (``RedstoneWireEvaluator.getIncomingWireSignal``; the upward-only glass staircase)."""
    b = Bench()
    b.place((1, 1, 0), "glass")
    b.place((1, 2, 0), "redstone_wire")  # on top of the glass
    b.place((0, 1, 0), "redstone_wire")  # floor, west of the glass
    b.place((2, 1, 0), "redstone_wire")  # floor, east of the glass
    b.place((3, 1, 0), "redstone_block")
    assert b.get((2, 1, 0), POWER) == 15
    assert b.get((1, 2, 0), POWER) == 14  # climbed onto the glass
    assert b.get((0, 1, 0), POWER) == 0  # but cannot come down the other side


def test_wire_powered_block_does_not_power_other_wire() -> None:
    b = Bench()
    b.place((0, 1, 0), "redstone_block")
    b.place((1, 1, 0), "redstone_wire")  # points into the stone below its line
    b.place((2, 1, 0), "stone")
    b.place((3, 1, 0), "redstone_wire")
    b.place((2, 1, 1), "redstone_lamp")
    assert b.level.get_signal((2, 1, 0), Direction.WEST) == 15  # stone weakly powered
    assert b.get((3, 1, 0), POWER) == 0  # but wire ignores wire-powered blocks
    assert b.get((2, 1, 1), LIT) is True  # other components do see the weak power


def test_dot_powers_only_the_block_below() -> None:
    b = Bench()
    b.place((1, 1, 0), "redstone_wire")  # isolated: placed as a cross
    b.use((1, 1, 0))  # toggle to a dot
    b.place((0, 1, 0), "redstone_lamp")
    b.place((1, 2, 0), "redstone_block")  # powers the wire from above
    assert b.get((1, 1, 0), POWER) == 15
    assert b.get((0, 1, 0), LIT) is False
    assert b.level.get_signal((1, 1, 0), Direction.UP) == 15


def wire_burst_order(at: Pos) -> list[Pos]:
    """Positions whose neighbors the wire updates, in the order the engine used."""
    b = Bench(floor=False)
    level = b.level
    from redsim.world import blocks

    level.blocks[(at[0], at[1] - 1, at[2])] = blocks.STONE.default_state
    level.blocks[at] = blocks.REDSTONE_WIRE.cross_state
    start = len(level.trace.records)
    level.set_block((at[0] - 1, at[1], at[2]), blocks.REDSTONE_BLOCK.default_state, 3)
    order: list[Pos] = []
    for record in level.trace.records[start:]:
        if record.kind == tr.NEIGHBOR_UPDATE and record.detail["source"] == "redstone_wire":
            source = record.detail["source_pos"]
            if source not in order:
                order.append(source)
    return order[:7]


def test_wire_update_burst_follows_java_hashset_order() -> None:
    for at in [(0, 1, 0), (7, 64, -13), (-200, 5, 31)]:
        expected = list(JavaHashSet(java_hash, [at] + [offset(at, d) for d in ALL]))
        assert wire_burst_order(at) == expected


def test_wire_burst_order_is_location_dependent() -> None:
    orders = {tuple(p[0] - 5 * i for p in wire_burst_order((5 * i, 1, 0))) for i in range(8)}
    assert len(orders) > 1
