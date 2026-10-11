"""Rails: shape connections and powered-rail propagation (game: EXP-035, EXP-036)."""

from __future__ import annotations

from redsim.sim.engine import Action, Engine
from redsim.world import blocks
from redsim.world.properties import POWERED


def world() -> Engine:
    engine = Engine()
    for x in range(-2, 16):
        for z in range(-2, 8):
            engine.level.blocks[(x, 0, z)] = blocks.STONE.default_state
    return engine


def shape(engine: Engine, pos: tuple[int, int, int]) -> str:
    state = engine.level.get_block_state(pos)
    return str(next(state.get(p) for p in state.block.properties if p.name == "shape"))


def test_powered_rails_carry_power_eight_rails_and_not_through_activator_rails() -> None:
    engine = world()
    for x in range(1, 13):
        engine.apply(Action("setblock", (x, 1, 1), "minecraft:powered_rail[shape=east_west]"))
    for x in (1, 2, 4, 5):
        engine.apply(Action("setblock", (x, 1, 3), "minecraft:powered_rail[shape=east_west]"))
    engine.apply(Action("setblock", (3, 1, 3), "minecraft:activator_rail[shape=east_west]"))
    engine.apply(Action("setblock", (0, 1, 1), "minecraft:redstone_block"))
    engine.apply(Action("setblock", (0, 1, 3), "minecraft:redstone_block"))
    row = [engine.level.get_block_state((x, 1, 1)).get(POWERED) for x in range(1, 13)]
    assert row == [True] * 9 + [False] * 3
    mixed = [engine.level.get_block_state((x, 1, 3)).get(POWERED) for x in (1, 2, 4, 5)]
    assert mixed == [True, True, False, False]


def test_rail_shapes_corner_t_junction_and_slope() -> None:
    engine = world()
    for pos in ((1, 1, 1), (2, 1, 1), (2, 1, 2)):
        engine.apply(Action("setblock", pos, "minecraft:rail"))
    assert shape(engine, (2, 1, 1)) == "south_west"
    for pos in ((6, 1, 1), (7, 1, 1), (8, 1, 1), (7, 1, 2)):
        engine.apply(Action("setblock", pos, "minecraft:rail"))
    before = shape(engine, (7, 1, 1))
    engine.apply(Action("setblock", (7, 1, 0), "minecraft:redstone_block"))
    assert before == "east_west" and shape(engine, (7, 1, 1)) == "south_west"
    engine.apply(Action("setblock", (11, 1, 5), "minecraft:stone"))
    engine.apply(Action("setblock", (11, 2, 5), "minecraft:rail"))
    engine.apply(Action("setblock", (10, 1, 5), "minecraft:rail"))
    assert shape(engine, (10, 1, 5)) == "ascending_east"
