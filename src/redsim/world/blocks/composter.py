"""Composter: a comparator source with nine levels (0–8).

Sources (relative to ``data/minecraft_src/client-src/net/minecraft/world/level/block/``):

* ``ComposterBlock.java``: ``LEVEL`` 0–8 (8: ready); shapes (a full block hollowed by a
  12-wide column from ``max(2, 1 + 2·level)`` up; collision always the level-0 shape);
  ``onPlace`` schedules a tick in 20 at level 7; ``tick`` turns 7 into 8
  (``setBlockAndUpdate``); ``useWithoutItem`` at level 8 empties it (``setBlockAndUpdate``
  to 0; the bone meal item entity is not simulated); analog output = the level.
* ``getContainer``: at level 8 an output container with one bone meal that hoppers below
  take (``setChanged`` empties the composter); below 7 an input container that only
  takes compostable items.
* ``Blocks.java``: strength 0.6, no block entity (pistons move it).

Not as in the game: composting itself is not simulated (players or hoppers putting
compostable items in), which adds a layer only by chance (``Compostable.layers``, random).
The editor's container items are not compostable, so hoppers never put anything in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.properties import integer
from redsim.world.shape import FULL_BLOCK, Shape, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

LEVEL = integer("level", 0, 8)
READY = 8
#: Ticks from level 7 to 8 (``ComposterBlock.tick``).
READY_DELAY = 20
BONE_MEAL = "minecraft:bone_meal"


def _shape(level: int) -> Shape:
    floor = min(16, max(2, 1 + level * 2))
    return FULL_BLOCK if floor >= 16 else Shape(FULL_BLOCK.grid & ~column(12, floor, 16).grid)


_SHAPES = tuple(_shape(level) for level in range(9))


class ComposterBlock(Block):
    properties = (LEVEL,)

    def __init__(self) -> None:
        super().__init__("minecraft:composter", destroy_speed=0.6)
        self.register_default_state(self.default_state.with_(LEVEL, 0))

    def get_shape(self, state: BlockState) -> Shape:
        return _SHAPES[state.get(LEVEL)]

    def get_collision_shape(self, state: BlockState) -> Shape:
        return _SHAPES[0]

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if state.get(LEVEL) == 7:
            level.schedule_tick(pos, self, READY_DELAY)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        if state.get(LEVEL) == 7:
            level.set_block_and_update(pos, state.with_(LEVEL, READY))

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``useWithoutItem``: a full composter is emptied (``extractProduce``)."""
        if state.get(LEVEL) != READY:
            return False
        level.set_block_and_update(pos, state.with_(LEVEL, 0))
        return True

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return int(state.get(LEVEL))


def take_produce(level: Level, pos: Pos) -> bool:
    """A hopper below takes the bone meal of a full composter (``OutputContainer``:
    ``setChanged`` empties it). Returns whether there was any."""
    state = level.get_block_state(pos)
    if not isinstance(state.block, ComposterBlock) or state.get(LEVEL) != READY:
        return False
    level.set_block_and_update(pos, state.with_(LEVEL, 0))
    return True
