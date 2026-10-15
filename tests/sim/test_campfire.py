"""Campfires (``world/blocks/campfire.py``); EXP-056 compares them with the real server."""

from __future__ import annotations

from pathlib import Path

from redsim.io import save as save_io
from redsim.sim.engine import Action, Engine
from redsim.world import blocks
from redsim.world.blocks.campfire import SIGNAL_FIRE, CampfireBlockEntity


def flat() -> Engine:
    engine = Engine()
    for x in range(-4, 5):
        for z in range(-4, 5):
            engine.level.blocks[(x, 0, z)] = blocks.STONE.default_state
    return engine


def ticks(engine: Engine, count: int) -> None:
    for _ in range(count):
        engine.step()
        engine.finish_tick()


def test_a_hay_bale_below_makes_a_signal_fire() -> None:
    engine = flat()
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:campfire"))
    assert not engine.level.get_block_state((0, 1, 0)).get(SIGNAL_FIRE)
    engine.apply(Action("setblock", (0, 0, 0), "minecraft:hay_block"))
    assert engine.level.get_block_state((0, 1, 0)).get(SIGNAL_FIRE)
    engine.apply(Action("setblock", (0, 0, 0), "minecraft:stone"))
    assert not engine.level.get_block_state((0, 1, 0)).get(SIGNAL_FIRE)


def test_pistons_cannot_push_a_campfire() -> None:
    engine = flat()
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:piston[facing=east]"))
    engine.apply(Action("setblock", (1, 1, 0), "minecraft:soul_campfire"))
    engine.apply(Action("setblock", (-1, 1, 0), "minecraft:redstone_block"))
    ticks(engine, 4)
    assert engine.level.get_block_state((1, 1, 0)).is_(blocks.get("soul_campfire"))
    assert engine.level.get_block_state((2, 1, 0)).is_air


def test_food_cooks_while_lit_and_cools_while_unlit(tmp_path: Path) -> None:
    engine = flat()
    food = {"Items": [{"Slot": 0, "id": "minecraft:beef", "count": 1}],
            "CookingTimes": [3, 0, 0, 0], "CookingTotalTimes": [6, 0, 0, 0]}  # fmt: skip
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:campfire", payload={"nbt": food}))
    engine.apply(
        Action("setblock", (2, 1, 0), "minecraft:campfire[lit=false]", payload={"nbt": food})
    )
    lit = engine.level.get_block_entity((0, 1, 0))
    assert isinstance(lit, CampfireBlockEntity)
    ticks(engine, 2)
    save_io.save(tmp_path / "w.redsim.json", engine)
    ticks(engine, 1)
    assert lit.items[0] is None and lit.cooking_progress[0] == 6  # left at its cooking time
    unlit = engine.level.get_block_entity((2, 1, 0))
    assert isinstance(unlit, CampfireBlockEntity)
    assert unlit.items[0] is not None and unlit.cooking_progress[0] == 0  # 3 → 1 → 0
    loaded, _ = save_io.load(tmp_path / "w.redsim.json")
    again = loaded.level.get_block_entity((0, 1, 0))
    assert isinstance(again, CampfireBlockEntity) and again.cooking_progress[0] == 5
