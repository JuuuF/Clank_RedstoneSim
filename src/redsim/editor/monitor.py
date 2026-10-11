"""What the timeline monitor shows for a block: one 0-15 value per tick.

Wire and target blocks: their power; comparator: its stored output; lamps and torches: lit
(15) or not; repeaters, levers, buttons, lecterns: powered (15) or not; pistons: extended
(15) or not; signal sources and hoppers: the value a comparator reads; anything else: the
strongest signal it receives (``Level.getBestNeighborSignal``).
"""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.sim.level import Level
from redsim.world.properties import EXTENDED, LIT, POWER, POWERED


def monitor_value(level: Level, pos: Pos) -> int:
    state = level.get_block_state(pos)
    block_id = state.block.id
    if state.has(POWER):  # redstone wire, target block
        return int(state.get(POWER))
    if block_id == "minecraft:comparator":
        entity = level.get_block_entity(pos, create=False)
        return int(entity.to_json().get("OutputSignal", 0)) if entity is not None else 0
    for prop in (LIT, POWERED, EXTENDED):
        if state.has(prop):
            return 15 if state.get(prop) else 0
    if sources.kind_of(state) is not None:
        return sources.strength_at(level, pos) or 0
    if state.has_analog_output_signal():  # hoppers
        return state.block.get_analog_output_signal(state, level, pos, Direction.NORTH)
    if state.is_air:
        return 0
    return level.get_best_neighbor_signal(pos)
