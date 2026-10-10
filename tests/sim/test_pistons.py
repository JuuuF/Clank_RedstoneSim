"""Piston structure rules and lifecycle (doc/mechanics/pistons.md).

Timing (push/pull, short pulses, QC/BUD, door) is game-verified by the recordings replayed in
test_game_verified.py; these tests cover structure resolution and block interactions.
"""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.world import blocks
from redsim.world.blocks.piston import PistonStructureResolver
from redsim.world.properties import EXTENDED
from tests.sim.bench import Bench


def extend_once(b: Bench, piston: tuple[int, int, int], source: tuple[int, int, int]) -> None:
    b.setblock(source, "redstone_block")
    b.tick(4)


def test_pushes_up_to_twelve_blocks() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "piston[facing=east]")
    for x in range(2, 14):
        b.setblock((x, 1, 0), "stone")  # 12 blocks
    extend_once(b, (1, 1, 0), (0, 1, 0))
    assert b.get((1, 1, 0), EXTENDED) is True
    assert b.state((14, 1, 0)).is_(blocks.STONE)

    b2 = Bench()
    b2.setblock((1, 1, 0), "piston[facing=east]")
    for x in range(2, 15):
        b2.setblock((x, 1, 0), "stone")  # 13 blocks: too many
    extend_once(b2, (1, 1, 0), (0, 1, 0))
    assert b2.get((1, 1, 0), EXTENDED) is False


def test_immovable_blocks_stop_the_push() -> None:
    for blocker in ("obsidian", "bedrock", "piston[facing=east,extended=true]"):
        b = Bench()
        b.setblock((1, 1, 0), "piston[facing=east]")
        b.setblock((2, 1, 0), "stone")
        b.setblock((3, 1, 0), blocker)
        extend_once(b, (1, 1, 0), (0, 1, 0))
        assert b.get((1, 1, 0), EXTENDED) is False, blocker


def test_popped_blocks_are_destroyed_in_the_line() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "piston[facing=east]")
    b.setblock((2, 1, 0), "stone")
    b.setblock((3, 1, 0), "redstone_wire")
    extend_once(b, (1, 1, 0), (0, 1, 0))
    assert b.state((3, 1, 0)).is_(blocks.STONE)
    assert b.state((4, 1, 0)).is_air  # the wire was destroyed, not pushed


def test_block_entities_are_immovable() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "piston[facing=east]")
    b.setblock((2, 1, 0), "stone")
    b.setblock((3, 1, 0), "stone")
    b.setblock((3, 2, 0), "comparator[facing=west]")  # on top: not in the push line
    resolver = PistonStructureResolver(b.level, (1, 1, 0), Direction.EAST, True)
    assert resolver.resolve()
    assert resolver.to_push == [(2, 1, 0), (3, 1, 0)]


def test_slime_drags_attached_blocks_but_not_honey() -> None:
    b = Bench()
    b.setblock((1, 5, 0), "piston[facing=east]")  # in the air: the floor would stick too
    b.setblock((2, 5, 0), "slime_block")
    b.setblock((2, 6, 0), "stone")  # stuck to the slime: moves too
    b.setblock((2, 5, 1), "honey_block")  # honey does not stick to slime
    resolver = PistonStructureResolver(b.level, (1, 5, 0), Direction.EAST, True)
    assert resolver.resolve()
    assert set(resolver.to_push) == {(2, 5, 0), (2, 6, 0)}


def test_slime_on_the_floor_grabs_the_floor() -> None:
    """A slime block sticks to the floor below it; the floor row exceeds the push limit."""
    b = Bench()
    b.setblock((1, 1, 0), "piston[facing=east]")
    b.setblock((2, 1, 0), "slime_block")
    resolver = PistonStructureResolver(b.level, (1, 1, 0), Direction.EAST, True)
    assert not resolver.resolve()


def test_sticky_piston_pulls_and_normal_piston_does_not() -> None:
    for piston, pulled in (("sticky_piston", True), ("piston", False)):
        b = Bench()
        b.setblock((1, 1, 0), f"{piston}[facing=east]")
        b.setblock((2, 1, 0), "stone")
        extend_once(b, (1, 1, 0), (0, 1, 0))
        b.setblock((0, 1, 0), "air")
        b.tick(4)
        assert b.state((2, 1, 0)).is_(blocks.STONE) is pulled
        assert b.state((3, 1, 0)).is_(blocks.STONE) is not pulled


def test_breaking_the_head_removes_the_base() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "piston[facing=east]")
    extend_once(b, (1, 1, 0), (0, 1, 0))
    assert b.state((2, 1, 0)).is_(blocks.PISTON_HEAD)
    b.break_block((2, 1, 0))
    assert b.state((1, 1, 0)).is_air


def test_wire_on_a_pushed_block_pops() -> None:
    b = Bench()
    b.setblock((1, 1, 0), "piston[facing=east]")
    b.setblock((2, 1, 0), "stone")
    b.setblock((2, 2, 0), "redstone_wire")
    extend_once(b, (1, 1, 0), (0, 1, 0))
    assert b.state((2, 2, 0)).is_air
    assert b.state((3, 2, 0)).is_air
