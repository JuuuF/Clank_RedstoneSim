"""Cake: an analog comparator source driven purely by block state.

``net/minecraft/world/level/block/CakeBlock.java``: shapes L35 (``box(1 + 2*bites, 0, 1,
15, 8, 15)``), ``eat`` L87, ``updateShape`` L106, ``canSurvive`` L123 (``below().isSolid()``),
``getAnalogOutputSignal`` L133 / ``getOutputSignal`` L137 (``(7 - bites) * 2``).
Registered with ``forceSolidOn`` and ``PushReaction.POPPED`` (``Blocks.CAKE``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import Direction
from redsim.core.pos import Pos, below
from redsim.world.block import Block, BlockState, PushReaction
from redsim.world.properties import BITES
from redsim.world.shape import Shape, box

if TYPE_CHECKING:
    from redsim.sim.level import Level


class CakeBlock(Block):
    properties = (BITES,)
    force_solid = True

    def __init__(self) -> None:
        super().__init__("minecraft:cake", push_reaction=PushReaction.POPPED, destroy_speed=0.5)
        self.register_default_state(self.default_state.with_(BITES, 0))

    def get_shape(self, state: BlockState) -> Shape:
        bites = int(state.get(BITES))
        return box(1 + bites * 2, 0, 1, 15, 8, 15)

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        return level.get_block_state(below(pos)).is_solid()

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction is Direction.DOWN and not state.can_survive(level, pos):
            return level.air
        return state

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``eat``: a creative player can always eat."""
        bites = int(state.get(BITES))
        if bites < 6:
            level.set_block_and_update(pos, state.with_(BITES, bites + 1))
        else:
            level.remove_block(pos, False)
        return True

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return (7 - int(state.get(BITES))) * 2
