"""Observer: emits a 2-tick pulse from its back when the block in front of it changes shape.

``net/minecraft/world/level/block/ObserverBlock.java`` (paths relative to
``data/minecraft_src/client-src/``):

* ``FACING`` (six-way) is the face that watches; the output is the back
  (``FACING.getOpposite()``). Placement: ``FACING`` = the nearest looking direction (L157).
* ``updateShape`` L57: a shape update coming from the watched side, while not powered,
  starts a signal: a scheduled tick in 2 (unless one is already pending).
* ``tick`` L45: powered → unpowered; unpowered → powered and another tick in 2. Either way
  ``updateNeighborsInFront`` (L80): ``neighborChanged`` at the block behind, then neighbor
  updates around it except back towards the observer.
* Signals L90-112: a signal source; strong and weak signal 15 only towards the back
  (``getSignal(direction) = FACING == direction ? own : 0``); dust connects only at the back.
* ``onPlace`` L114: placed (e.g. pushed) while powered without a pending tick → unpowered
  (flags 18) and the block behind is updated. ``affectNeighborsAfterRemoval`` L124: removed
  while powered with a pending tick → the block behind is updated as if unpowered.
* Pistons can move observers (``PushReaction.PUSH_PULL``). Not a redstone conductor
  (``Blocks.OBSERVER`` registers ``isRedstoneConductor(Blocks::never)``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import Direction
from redsim.core.pos import Pos, offset
from redsim.world.block import Block, BlockState, Conductor, PlacementContext
from redsim.world.properties import FACING, POWERED

if TYPE_CHECKING:
    from redsim.sim.level import Level

OBSERVER = "minecraft:observer"


class ObserverBlock(Block):
    properties = (FACING, POWERED)

    def __init__(self) -> None:
        # Blocks.OBSERVER: ``isRedstoneConductor(Blocks::never)`` (L3762): power never passes
        # through an observer (found by the game comparison, EXP-033).
        super().__init__(OBSERVER, destroy_speed=3.0, conductor=Conductor.NEVER)
        self.register_default_state(
            self.default_state.with_(FACING, Direction.SOUTH).with_(POWERED, False)
        )

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state.with_(FACING, ctx.requested.get(FACING))

    # --- detection and pulse ------------------------------------------------------------
    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if state.get(FACING) is direction and not state.get(POWERED):
            self.start_signal(level, pos)
        return state

    def start_signal(self, level: Level, pos: Pos) -> None:
        if not level.has_scheduled_tick(pos, self):
            level.schedule_tick(pos, self, 2)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        if state.get(POWERED):
            level.set_block(pos, state.with_(POWERED, False), 2)
        else:
            level.set_block(pos, state.with_(POWERED, True), 2)
            level.schedule_tick(pos, self, 2)
        self.update_neighbors_in_front(level, pos, state)

    def update_neighbors_in_front(self, level: Level, pos: Pos, state: BlockState) -> None:
        direction = state.get(FACING)
        behind = offset(pos, direction.opposite)
        level.neighbor_changed(behind, self)
        level.update_neighbors_at_except_from_facing(behind, self, direction)

    # --- signals --------------------------------------------------------------------------
    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def should_redstone_wire_connect_to(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction | None
    ) -> bool:
        return direction is state.get(FACING)

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 15 if state.get(POWERED) else 0

    def get_signal(self, state: BlockState, level: Level, pos: Pos, direction: Direction) -> int:
        return self.own_signal(state, level, pos) if state.get(FACING) is direction else 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return self.get_signal(state, level, pos, direction)

    # --- lifecycle --------------------------------------------------------------------------
    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        changed = state.block is not old_state.block
        if changed and state.get(POWERED) and not level.has_scheduled_tick(pos, self):
            unpowered = state.with_(POWERED, False)
            level.set_block(pos, unpowered, 18)
            self.update_neighbors_in_front(level, pos, unpowered)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if state.get(POWERED) and level.has_scheduled_tick(pos, self):
            self.update_neighbors_in_front(level, pos, state.with_(POWERED, False))


__all__ = ["OBSERVER", "Block", "ObserverBlock"]
