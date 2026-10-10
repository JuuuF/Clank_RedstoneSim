"""Redstone lamp: ``net/minecraft/world/level/block/RedstoneLampBlock.java``.

On immediately, off after a 4-tick scheduled tick; both via ``setBlock(..., 2)`` (no
neighbor updates). See doc/mechanics/manual-sources.md (Q-LAMP-ASYM).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.pos import Pos
from redsim.world.block import Block, BlockState, PlacementContext, UpdateFlags
from redsim.world.properties import LIT

if TYPE_CHECKING:
    from redsim.sim.level import Level


class RedstoneLampBlock(Block):
    properties = (LIT,)

    def __init__(self) -> None:
        super().__init__("minecraft:redstone_lamp", destroy_speed=0.3)
        self.register_default_state(self.default_state.with_(LIT, False))

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement`` L24."""
        return self.default_state.with_(LIT, ctx.level.has_neighbor_signal(ctx.pos))

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        """``neighborChanged`` L29."""
        is_lit = state.get(LIT)
        if is_lit != level.has_neighbor_signal(pos):
            if is_lit:
                level.schedule_tick(pos, self, 4)
            else:
                level.set_block(pos, state.cycle(LIT), UpdateFlags.CLIENTS)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``tick`` L45."""
        if state.get(LIT) and not level.has_neighbor_signal(pos):
            level.set_block(pos, state.cycle(LIT), UpdateFlags.CLIENTS)
