"""Copper bulb: ``net/minecraft/world/level/block/CopperBulbBlock.java``.

A T flip-flop: each rising signal toggles ``lit``; ``powered`` follows the signal. A
comparator reads 15 while lit. Never a conductor (``Blocks.COPPER_BULB``,
``isRedstoneConductor(Blocks::never)``). The weathering stages (``exposed_``, …) and the
waxed bulbs behave the same; only their light level differs, and oxidation needs random
ticks, which are off in the simulation (doc/decisions.md).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world.block import Block, BlockState, Conductor
from redsim.world.properties import LIT, POWERED

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: Every copper bulb: ``Blocks.COPPER_BULB`` (a ``WeatheringCopperCollection``).
COPPER_BULB_IDS = tuple(
    f"minecraft:{wax}{stage}copper_bulb"
    for wax in ("", "waxed_")
    for stage in ("", "exposed_", "weathered_", "oxidized_")
)


class CopperBulbBlock(Block):
    properties = (LIT, POWERED)

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id, destroy_speed=3.0, conductor=Conductor.NEVER)
        self.register_default_state(self.default_state.with_(LIT, False).with_(POWERED, False))

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        """``onPlace`` L14: only when the block type changes."""
        if old_state.block is not state.block:
            self.check_and_flip(state, level, pos)

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        """``neighborChanged`` L21."""
        self.check_and_flip(state, level, pos)

    def check_and_flip(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``checkAndFlip`` L29: a rising signal toggles ``lit``; flags 3."""
        signal = level.has_neighbor_signal(pos)
        if signal != state.get(POWERED):
            new_state = state if state.get(POWERED) else state.cycle(LIT)
            level.set_block_and_update(pos, new_state.with_(POWERED, signal))

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return True

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        """``getAnalogOutputSignal`` L53: reads the block at ``pos`` again."""
        return 15 if level.get_block_state(pos).get(LIT) else 0
