"""Observer: pulses on shape updates in front, powers only its back, never conducts.

Game comparisons: EXP-032..034 (observer_clock, observer_detects, observer_pushed).
"""

from __future__ import annotations

from redsim.sim.engine import Action, Engine
from redsim.world import blocks
from redsim.world.properties import LIT, POWERED


def world() -> Engine:
    engine = Engine()
    for x in range(-2, 8):
        for z in range(-2, 4):
            engine.level.blocks[(x, 0, z)] = blocks.STONE.default_state
    return engine


def test_a_block_placed_in_front_gives_a_two_tick_pulse_out_of_the_back() -> None:
    engine = world()
    engine.apply(Action("setblock", (1, 1, 0), "minecraft:observer[facing=west]"))
    engine.apply(Action("setblock", (2, 1, 0), "minecraft:redstone_lamp"))  # behind
    engine.run_ticks(4)  # settle the placement pulse
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:stone"))  # in front
    states = []
    for _ in range(6):
        engine.run_tick()
        states.append(engine.level.get_block_state((1, 1, 0)).get(POWERED))
    assert states == [False, True, True, False, False, False]
    assert engine.level.get_block_state((2, 1, 0)).get(LIT) is True  # lamp off-delay


def test_observers_do_not_conduct() -> None:
    engine = world()
    engine.apply(Action("setblock", (1, 1, 0), "minecraft:observer[facing=north]"))
    level = engine.level
    assert not level.get_block_state((1, 1, 0)).is_redstone_conductor(level, (1, 1, 0))


def test_two_observers_facing_each_other_form_a_clock() -> None:
    engine = world()
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:observer[facing=east]"))
    engine.apply(Action("setblock", (1, 1, 0), "minecraft:observer[facing=west]"))
    changes = 0
    previous = None
    for _ in range(40):
        engine.run_tick()
        now = engine.level.get_block_state((0, 1, 0)).get(POWERED)
        changes += now != previous
        previous = now
    assert changes > 10  # it keeps running
