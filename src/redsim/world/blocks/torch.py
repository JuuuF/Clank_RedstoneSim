"""Redstone torch and wall torch.

Source (relative to ``data/minecraft_src/client-src/net/minecraft/world/level/block/``):

* ``RedstoneTorchBlock.java``: ``onPlace`` L37, ``notifyNeighbors`` L41,
  ``affectNeighborsAfterRemoval`` L50, ``hasNeighborSignal`` L56, ``tick`` L61,
  ``neighborChanged`` L83, ``getDirectSignal`` L92, ``ownSignal`` L102, ``getSignal`` L107,
  ``isToggledTooFrequently`` L126 (burnout: ``RECENT_TOGGLES``, 60/8/160).
* ``RedstoneWallTorchBlock.java``: ``canSurvive`` L38, ``updateShape`` L43,
  ``hasNeighborSignal`` L75, ``getSignal`` L81.
* ``BaseTorchBlock.java``: ``updateShape`` L27, ``canSurvive`` L43;
  ``WallTorchBlock.canSurvive`` L46.

Burnout is deterministic: ``RECENT_TOGGLES`` maps each level to one list of
``(pos, gameTime)`` toggles shared by all torches. It is stored on the level as
``level.torch_toggles`` so snapshots and saves include it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from redsim.core.direction import ALL, Direction
from redsim.core.pos import Pos, below, offset
from redsim.world.block import Block, BlockState, PlacementContext, PushReaction
from redsim.world.properties import HORIZONTAL_FACING, LIT, Property
from redsim.world.shape import EMPTY, Shape, SupportType

if TYPE_CHECKING:
    from redsim.sim.level import Level

RECENT_TOGGLE_TIMER = 60
MAX_RECENT_TOGGLES = 8
RESTART_DELAY = 160
TOGGLE_DELAY = 2


def is_toggled_too_frequently(level: Level, pos: Pos, add: bool) -> bool:
    """``RedstoneTorchBlock.isToggledTooFrequently`` (L126)."""
    toggles = level.torch_toggles
    if add:
        toggles.append((pos, level.game_time))
    count = 0
    for toggle_pos, _ in toggles:
        if toggle_pos == pos:
            count += 1
            if count >= MAX_RECENT_TOGGLES:
                return True
    return False


class RedstoneTorchBlock(Block):
    properties: ClassVar[tuple[Property, ...]] = (LIT,)

    def __init__(self, block_id: str = "minecraft:redstone_torch") -> None:
        super().__init__(
            block_id, has_collision=False, push_reaction=PushReaction.POPPED, destroy_speed=0.0
        )
        self.register_default_state(self.default_state.with_(LIT, True))

    def get_shape(self, state: BlockState) -> Shape:
        return EMPTY  # no collision; visual shape irrelevant to the simulation

    # --- support ------------------------------------------------------------------------
    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``BaseTorchBlock.canSurvive``: ``canSupportCenter(below, UP)``."""
        support = below(pos)
        return level.get_block_state(support).is_face_sturdy(
            level, support, Direction.UP, SupportType.CENTER
        )

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction is Direction.DOWN and not self.can_survive(state, level, pos):
            return level.air
        return state

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state  # LIT=true; the torch corrects itself 2 ticks later

    # --- updates ------------------------------------------------------------------------
    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        self.notify_neighbors(level, pos)

    def notify_neighbors(self, level: Level, pos: Pos) -> None:
        """``notifyNeighbors`` L41: ``updateNeighborsAt`` around each of the 6 neighbors."""
        for direction in ALL:
            level.update_neighbors_at(offset(pos, direction), self)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if not moved_by_piston:
            self.notify_neighbors(level, pos)

    def has_neighbor_signal(self, level: Level, pos: Pos, state: BlockState) -> bool:
        return level.has_signal(below(pos), Direction.DOWN)

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        if state.get(LIT) == self.has_neighbor_signal(
            level, pos, state
        ) and not level.will_tick_this_tick(pos, self):
            level.schedule_tick(pos, self, TOGGLE_DELAY)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``tick`` L61."""
        neighbor_signal = self.has_neighbor_signal(level, pos, state)
        toggles = level.torch_toggles
        while toggles and level.game_time - toggles[0][1] > RECENT_TOGGLE_TIMER:
            toggles.pop(0)
        if state.get(LIT):
            if neighbor_signal:
                level.set_block_and_update(pos, state.with_(LIT, False))
                if is_toggled_too_frequently(level, pos, True):
                    level.schedule_tick(pos, level.get_block_state(pos).block, RESTART_DELAY)
        elif not neighbor_signal and not is_toggled_too_frequently(level, pos, False):
            level.set_block_and_update(pos, state.with_(LIT, True))

    # --- signals ------------------------------------------------------------------------
    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 15 if state.get(LIT) else 0

    def get_signal(self, state: BlockState, level: Level, pos: Pos, direction: Direction) -> int:
        return self.own_signal(state, level, pos) if direction is not Direction.UP else 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        """Strong power only into the block above (``direction == DOWN``)."""
        return state.get_signal(level, pos, direction) if direction is Direction.DOWN else 0


class RedstoneWallTorchBlock(RedstoneTorchBlock):
    properties = (HORIZONTAL_FACING, LIT)

    def __init__(self) -> None:
        super().__init__("minecraft:redstone_wall_torch")
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH).with_(LIT, True)
        )

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``WallTorchBlock.canSurvive``: the attached block's facing side must be sturdy."""
        facing: Direction = state.get(HORIZONTAL_FACING)
        attached = offset(pos, facing.opposite)
        return level.get_block_state(attached).is_face_sturdy(level, attached, facing)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction.opposite is state.get(HORIZONTAL_FACING) and not state.can_survive(level, pos):
            return level.air
        return state

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state.with_(HORIZONTAL_FACING, ctx.requested.get(HORIZONTAL_FACING))

    def has_neighbor_signal(self, level: Level, pos: Pos, state: BlockState) -> bool:
        opposite: Direction = state.get(HORIZONTAL_FACING).opposite
        return level.has_signal(offset(pos, opposite), opposite)

    def get_signal(self, state: BlockState, level: Level, pos: Pos, direction: Direction) -> int:
        if state.get(HORIZONTAL_FACING) is not direction:
            return self.own_signal(state, level, pos)
        return 0
