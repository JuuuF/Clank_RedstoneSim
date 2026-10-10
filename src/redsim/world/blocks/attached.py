"""Face-attached manual sources: lever and buttons.

Source (relative to ``data/minecraft_src/client-src/net/minecraft/world/level/block/``):

* ``FaceAttachedHorizontalDirectionalBlock.java``: ``canSurvive`` L24, ``canAttach`` L28,
  ``updateShape`` L54, ``getConnectedDirection`` L69.
* ``LeverBlock.java``: ``pull`` L82, ``affectNeighborsAfterRemoval`` L112,
  ``getDirectSignal`` L119, ``updateNeighbours`` L133.
* ``ButtonBlock.java``: ``useWithoutItem`` L70, ``press`` L92, ``tick`` L131,
  ``checkPressed`` L146, ``updateNeighbours`` L164.

See doc/mechanics/manual-sources.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import Direction
from redsim.core.pos import Pos, offset
from redsim.world.block import Block, BlockState, PlacementContext, PushReaction
from redsim.world.properties import ATTACH_FACE, HORIZONTAL_FACING, POWERED
from redsim.world.shape import EMPTY, Shape

if TYPE_CHECKING:
    from redsim.sim.level import Level


def connected_direction(state: BlockState) -> Direction:
    """``getConnectedDirection``: points from the attached block toward this block."""
    face = state.get(ATTACH_FACE)
    if face == "ceiling":
        return Direction.DOWN
    if face == "floor":
        return Direction.UP
    facing: Direction = state.get(HORIZONTAL_FACING)
    return facing


def attached_pos(pos: Pos, state: BlockState) -> Pos:
    return offset(pos, connected_direction(state).opposite)


class FaceAttachedBlock(Block):
    """``FaceAttachedHorizontalDirectionalBlock`` with a ``powered`` property."""

    properties = (ATTACH_FACE, HORIZONTAL_FACING, POWERED)

    def __init__(self, block_id: str, destroy_speed: float) -> None:
        super().__init__(
            block_id,
            has_collision=False,
            push_reaction=PushReaction.POPPED,
            destroy_speed=destroy_speed,
        )
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(POWERED, False)
            .with_(ATTACH_FACE, "wall")
        )

    def get_shape(self, state: BlockState) -> Shape:
        return EMPTY  # no collision; the visual shape is irrelevant to the simulation

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        direction = connected_direction(state).opposite
        relative = offset(pos, direction)
        return level.get_block_state(relative).is_face_sturdy(level, relative, direction.opposite)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if connected_direction(state).opposite is direction and not state.can_survive(level, pos):
            return level.air
        return state

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return ctx.requested.with_(POWERED, False)

    # --- signals ------------------------------------------------------------------------
    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 15 if state.get(POWERED) else 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return 15 if state.get(POWERED) and connected_direction(state) is direction else 0

    def update_neighbours(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``LeverBlock.updateNeighbours`` / ``ButtonBlock.updateNeighbours``."""
        front = connected_direction(state).opposite
        level.update_neighbors_at(pos, self)
        level.update_neighbors_at(offset(pos, front), self)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if not moved_by_piston and state.get(POWERED):
            self.update_neighbours(state, level, pos)


class LeverBlock(FaceAttachedBlock):
    def __init__(self) -> None:
        super().__init__("minecraft:lever", destroy_speed=0.5)

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        self.pull(state, level, pos)
        return True

    def pull(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``LeverBlock.pull``: toggle (flags 3), then update both neighborhoods again."""
        state = state.cycle(POWERED)
        level.set_block_and_update(pos, state)
        self.update_neighbours(state, level, pos)


class ButtonBlock(FaceAttachedBlock):
    """Stone (20 ticks) and wooden (30 ticks) buttons. Arrows are not simulated."""

    def __init__(self, block_id: str, ticks_to_stay_pressed: int) -> None:
        super().__init__(block_id, destroy_speed=0.5)
        self.ticks_to_stay_pressed = ticks_to_stay_pressed

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        if state.get(POWERED):
            return False  # InteractionResult.CONSUME: nothing happens
        self.press(state, level, pos)
        return True

    def press(self, state: BlockState, level: Level, pos: Pos) -> None:
        level.set_block_and_update(pos, state.with_(POWERED, True))
        self.update_neighbours(state, level, pos)
        level.schedule_tick(pos, self, self.ticks_to_stay_pressed)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        if state.get(POWERED):
            self.check_pressed(state, level, pos)

    def check_pressed(self, state: BlockState, level: Level, pos: Pos) -> None:
        should_be_pressed = False  # no arrows in the simulation
        if should_be_pressed != state.get(POWERED):
            level.set_block_and_update(pos, state.with_(POWERED, should_be_pressed))
            self.update_neighbours(state, level, pos)
