"""Hopper: one item per 8 ticks, pulling from above and pushing in front; redstone locks it.

Game comparisons: EXP-038..041 (hopper_chain, hopper_lock, hopper_clock, hopper_item_replace).
"""

from __future__ import annotations

from typing import Any

from redsim.io.save import engine_from_json, engine_to_json
from redsim.sim.engine import Action, Engine
from redsim.world import blocks
from redsim.world.blocks.hopper import HopperBlockEntity
from redsim.world.properties import ENABLED

REDSTONE = "minecraft:redstone"


def world() -> Engine:
    engine = Engine()
    for x in range(-2, 8):
        for z in range(-2, 4):
            engine.level.blocks[(x, 0, z)] = blocks.STONE.default_state
    return engine


def items(*stacks: tuple[str, int]) -> dict[str, Any]:
    return {
        "Items": [
            {"Slot": slot, "id": item, "count": count} for slot, (item, count) in enumerate(stacks)
        ]
    }


def setblock(engine: Engine, pos: tuple[int, int, int], state: str, nbt: Any = None) -> None:
    engine.apply(Action("setblock", pos, state, payload={"nbt": nbt} if nbt is not None else None))


def count(engine: Engine, pos: tuple[int, int, int]) -> int:
    entity = engine.level.get_block_entity(pos)
    return sum(stack[1] for stack in getattr(entity, "items", []) if stack is not None)


def test_a_hopper_moves_one_item_every_8_ticks_starting_at_once() -> None:
    engine = world()
    setblock(engine, (1, 1, 0), "minecraft:hopper[facing=east]", items((REDSTONE, 3)))
    setblock(engine, (2, 1, 0), "minecraft:barrel[facing=up]")
    moved = []
    for tick in range(1, 20):
        engine.run_tick()
        moved.append((tick, count(engine, (2, 1, 0))))
    assert [
        tick for (tick, n), (_, before) in zip(moved[1:], moved, strict=False) if n > before
    ] == [9, 17]
    assert moved[0] == (1, 1)
    assert count(engine, (1, 1, 0)) == 0


def test_chained_hoppers_move_one_item_per_8_ticks_in_either_ticker_order() -> None:
    for first_placed in ("upstream", "downstream"):
        engine = world()
        up = ((1, 1, 0), "minecraft:hopper[facing=east]", items((REDSTONE, 2)))
        down = ((2, 1, 0), "minecraft:hopper[facing=east]", None)
        for pos, state, nbt in (up, down) if first_placed == "upstream" else (down, up):
            setblock(engine, pos, state, nbt)
        setblock(engine, (3, 1, 0), "minecraft:barrel[facing=up]")
        arrivals = []
        for tick in range(1, 20):
            before = count(engine, (3, 1, 0))
            engine.run_tick()
            if count(engine, (3, 1, 0)) > before:
                arrivals.append(tick)
        # The receiving hopper waits 8 ticks, or 7 if it already ticked this game tick.
        assert arrivals == [8, 16], first_placed


def test_a_powered_hopper_is_locked_and_resumes_at_once() -> None:
    engine = world()
    setblock(engine, (1, 1, 0), "minecraft:hopper[facing=east]", items((REDSTONE, 5)))
    setblock(engine, (2, 1, 0), "minecraft:barrel[facing=up]")
    engine.run_tick()  # first item moves
    setblock(engine, (1, 1, -1), "minecraft:redstone_block")
    assert engine.level.get_block_state((1, 1, 0)).get(ENABLED) is False
    engine.run_ticks(20)
    assert count(engine, (2, 1, 0)) == 1
    hopper = engine.level.get_block_entity((1, 1, 0))
    assert isinstance(hopper, HopperBlockEntity) and hopper.cooldown_time == 0
    setblock(engine, (1, 1, -1), "minecraft:air")
    assert engine.level.get_block_state((1, 1, 0)).get(ENABLED) is True
    engine.run_tick()
    assert count(engine, (2, 1, 0)) == 2


def test_a_hopper_pulls_from_a_barrel_above_and_fills_up_by_item_kind() -> None:
    engine = world()
    stacks = [(REDSTONE, 1)] + [(f"minecraft:item_{i}", 64) for i in range(4)]
    setblock(engine, (1, 1, 0), "minecraft:hopper[facing=down]", items(*stacks))
    setblock(
        engine,
        (1, 2, 0),
        "minecraft:barrel[facing=up]",
        items(("minecraft:stone", 3), (REDSTONE, 2)),
    )
    engine.run_ticks(9)
    # The stone fits nowhere (all slots taken), so the redstone after it is pulled.
    hopper = engine.level.get_block_entity((1, 1, 0))
    assert isinstance(hopper, HopperBlockEntity)
    assert hopper.items[0] == (REDSTONE, 3)
    assert count(engine, (1, 2, 0)) == 3


def test_comparator_reads_a_hopper_but_item_replace_does_not_update_it() -> None:
    engine = world()
    setblock(engine, (1, 1, 0), "minecraft:hopper[facing=down]")
    setblock(engine, (1, 1, 1), "minecraft:comparator[facing=north]")
    setblock(engine, (4, 1, 0), "minecraft:barrel[facing=up]")
    setblock(engine, (4, 1, 1), "minecraft:comparator[facing=north]")
    for pos in ((1, 1, 0), (4, 1, 0)):
        engine.apply(
            Action("container_item", pos, payload={"slot": 0, "item": REDSTONE, "count": 64})
        )
    engine.run_ticks(4)
    output = engine.level.get_block_entity((1, 1, 1))
    assert getattr(output, "output", None) == 0  # HopperBlockEntity.setItem: no setChanged
    assert getattr(engine.level.get_block_entity((4, 1, 1)), "output", None) == 1
    setblock(engine, (0, 1, 1), "minecraft:stone")  # any neighbor update re-reads it
    engine.run_ticks(2)
    assert getattr(output, "output", None) == 3  # 64 of 5 × 64


def test_saves_keep_the_cooldown_and_the_last_tick_time() -> None:
    engine = world()
    setblock(engine, (1, 1, 0), "minecraft:hopper[facing=east]", items((REDSTONE, 3)))
    setblock(engine, (2, 1, 0), "minecraft:hopper[facing=down]")
    engine.run_ticks(3)
    restored = engine_from_json(engine_to_json(engine))
    for pos in ((1, 1, 0), (2, 1, 0)):
        a, b = engine.level.get_block_entity(pos), restored.level.get_block_entity(pos)
        assert isinstance(a, HopperBlockEntity) and isinstance(b, HopperBlockEntity)
        assert (a.items, a.cooldown_time, a.ticked_game_time) == (
            b.items,
            b.cooldown_time,
            b.ticked_game_time,
        )


def test_dust_sits_on_a_hopper_but_a_torch_does_not() -> None:
    engine = world()
    setblock(engine, (1, 1, 0), "minecraft:hopper")
    level = engine.level
    assert blocks.REDSTONE_WIRE.default_state.can_survive(level, (1, 2, 0))
    assert not blocks.REDSTONE_TORCH.default_state.can_survive(level, (1, 2, 0))
    assert not level.get_block_state((1, 1, 0)).is_redstone_conductor(level, (1, 1, 0))
