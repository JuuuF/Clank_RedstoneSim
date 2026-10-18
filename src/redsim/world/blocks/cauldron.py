"""Cauldrons: comparator sources whose signal is how full they are (cauldron, water
cauldron, lava cauldron, powder snow cauldron).

Sources (relative to ``data/minecraft_src/server-src/net/minecraft/world/level/block/``):

* ``AbstractCauldronBlock.java``: ``SHAPE`` (a full block without the inside
  ``column(12, 4, 16)`` and without the gaps between the legs: ``column(16, 8, 0, 3)``,
  ``column(8, 16, 0, 3)``, ``column(12, 0, 3)``), the same for collision;
  ``hasAnalogOutputSignal`` true.
* ``CauldronBlock.java`` (empty): analog output 0 (``BlockBehaviour`` default).
* ``LayeredCauldronBlock.java`` (water, powder snow): ``LEVEL`` 1–3 (default 1), analog
  output = the level.
* ``LavaCauldronBlock.java``: analog output 3.
* ``Blocks.java``: strength 2, no block entity (pistons move them), ``noOcclusion``; not a
  redstone conductor (``isRedstoneConductor`` default: the collision shape is not a full
  block).

Not as in the game (doc/differences.md): what fills or empties a cauldron is not simulated
(buckets and bottles in a player's hand, rain and snow, dripstone dripping into it, burning
mobs putting themselves out in water or powder snow), nor lava hurting mobs. A cauldron
keeps its level unless the editor changes it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world.block import BlockState
from redsim.world.blocks.catalog import CatalogBlock
from redsim.world.properties import integer
from redsim.world.shape import FULL_BLOCK, Shape, box, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

LEVEL = integer("level", 1, 3)  # BlockStateProperties.LEVEL_CAULDRON
#: ``AbstractCauldronBlock.SHAPE``.
SHAPE = Shape(
    FULL_BLOCK.grid
    & ~(
        box(0, 0, 4, 16, 3, 12).grid  # column(16, 8, 0, 3)
        | box(4, 0, 0, 12, 3, 16).grid  # column(8, 16, 0, 3)
        | column(12, 0, 3).grid
        | column(12, 4, 16).grid  # SHAPE_INSIDE
    )
)


class CauldronBlock(CatalogBlock):
    """``CauldronBlock``: the empty cauldron (signal 0)."""

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec, shape=SHAPE)

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return 0


class LayeredCauldronBlock(CauldronBlock):
    """``LayeredCauldronBlock``: water and powder snow, ``level`` 1–3 is the signal."""

    properties = (LEVEL,)

    def __init__(self, block_id: str, spec: tuple[Any, ...]) -> None:
        super().__init__(block_id, spec)
        self.register_default_state(self.default_state.with_(LEVEL, 1))

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return int(state.get(LEVEL))


class LavaCauldronBlock(CauldronBlock):
    """``LavaCauldronBlock``: always full (signal 3)."""

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return 3
