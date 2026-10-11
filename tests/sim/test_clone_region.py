"""``/clone <begin> <end> <dest> replace <normal|force|move>`` (``CloneCommands.clone``).

The game comparison is EXP-023 (experiments/results/clone_move_running.json); these tests
pin the command's rules.
"""

from __future__ import annotations

import pytest

from redsim.core.pos import Pos
from redsim.sim.engine import Action, ActionError, Engine
from redsim.world import blocks
from redsim.world.properties import POWERED


def clone(engine: Engine, begin: Pos, end: Pos, dest: Pos, mode: str) -> None:
    payload = {"begin": list(begin), "end": list(end), "mode": mode}
    engine.apply(Action("clone_region", dest, payload=payload))


def floor(engine: Engine, size: int = 8) -> None:
    for x in range(-1, size):
        for z in range(-1, size):
            engine.level.blocks[(x, 0, z)] = blocks.STONE.default_state


def test_normal_mode_rejects_overlap_force_and_move_allow_it() -> None:
    engine = Engine()
    floor(engine)
    engine.apply(Action("setblock", (0, 1, 0), "minecraft:redstone_lamp"))
    with pytest.raises(ActionError, match="overlap"):
        clone(engine, (0, 1, 0), (1, 1, 0), (1, 1, 0), "normal")
    clone(engine, (0, 1, 0), (1, 1, 0), (1, 1, 0), "force")
    assert engine.level.get_block_state((1, 1, 0)).is_(blocks.REDSTONE_LAMP)
    assert engine.level.get_block_state((0, 1, 0)).is_(blocks.REDSTONE_LAMP)  # force copies
    clone(engine, (0, 1, 0), (0, 1, 0), (0, 1, 3), "move")
    assert engine.level.get_block_state((0, 1, 0)).is_air  # move clears the source
    assert engine.level.get_block_state((0, 1, 3)).is_(blocks.REDSTONE_LAMP)


def test_area_limit() -> None:
    engine = Engine()
    with pytest.raises(ActionError, match="Too many blocks"):
        clone(engine, (0, 1, 0), (32, 32, 32), (100, 1, 0), "normal")


def test_move_copies_pending_scheduled_ticks() -> None:
    engine = Engine()
    floor(engine)
    engine.apply(Action("setblock", (1, 1, 1), "minecraft:repeater[facing=west,delay=4]"))
    engine.apply(Action("setblock", (0, 1, 1), "minecraft:redstone_block"))  # schedules
    engine.run_ticks(2)
    clone(engine, (1, 1, 1), (1, 1, 1), (1, 1, 4), "move")
    pending = [(t.pos, t.block_id) for t in engine.level.block_ticks.pending()]
    assert ((1, 1, 4), "minecraft:repeater") in pending
    engine.run_ticks(8)
    assert engine.level.get_block_state((1, 1, 4)).get(POWERED) is True
