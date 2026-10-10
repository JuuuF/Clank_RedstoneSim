"""Diodes: the shared ``DiodeBlock`` logic and the repeater.

Source (relative to ``data/minecraft_src/client-src/net/minecraft/world/level/block/``):

* ``DiodeBlock.java``: ``canSurvive`` L40, ``tick`` L50, ``neighborChanged`` L66,
  ``checkTickOnNeighbor`` L84, ``shouldTurnOn`` L105, ``getInputSignal`` L109,
  ``getAlternateSignal`` L121, ``getSignal`` L148, ``setPlacedBy`` L158, ``onPlace`` L165,
  ``affectNeighborsAfterRemoval`` L170, ``updateNeighborsInFront`` L176,
  ``shouldPrioritize`` L196.
* ``RepeaterBlock.java``: ``useWithoutItem`` L35, ``getDelay`` L47, ``getStateForPlacement``
  L52, ``updateShape`` L58, ``shouldRedstoneWireConnectTo`` L78, ``isLocked`` L84.

``FACING`` points toward the input; output goes into ``pos - FACING``.
See doc/mechanics/repeater.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import ALL, Direction
from redsim.core.pos import Pos, below, offset
from redsim.world import ids
from redsim.world.block import (
    Block,
    BlockState,
    Conductor,
    PlacementContext,
    PushReaction,
    UpdateFlags,
)
from redsim.world.properties import DELAY, HORIZONTAL_FACING, LOCKED, POWER, POWERED
from redsim.world.shape import Shape, SupportType, column
from redsim.world.tick_priority import TickPriority

if TYPE_CHECKING:
    from redsim.sim.level import Level

DIODE_SHAPE = column(16, 0, 2)


def facing(state: BlockState) -> Direction:
    value: Direction = state.get(HORIZONTAL_FACING)
    return value


class DiodeBlock(Block):
    """Abstract base of repeater and comparator (``DiodeBlock``)."""

    is_diode = True

    def __init__(self, block_id: str) -> None:
        super().__init__(
            block_id,
            push_reaction=PushReaction.POPPED,
            conductor=Conductor.NEVER,
            destroy_speed=0.0,
        )

    def get_shape(self, state: BlockState) -> Shape:
        return DIODE_SHAPE

    # --- support ------------------------------------------------------------------------
    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        support = below(pos)
        return self.can_survive_on(level, support, level.get_block_state(support))

    def can_survive_on(self, level: Level, pos: Pos, state: BlockState) -> bool:
        return state.is_face_sturdy(level, pos, Direction.UP, SupportType.RIGID)

    # --- ticking ------------------------------------------------------------------------
    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        if not self.is_locked(level, pos, state):
            on = state.get(POWERED)
            should_turn_on = self.should_turn_on(level, pos, state)
            if on and not should_turn_on:
                level.set_block(pos, state.with_(POWERED, False), UpdateFlags.CLIENTS)
            elif not on:
                level.set_block(pos, state.with_(POWERED, True), UpdateFlags.CLIENTS)
                if not should_turn_on:
                    level.schedule_tick(pos, self, self.get_delay(state), TickPriority.VERY_HIGH)

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        if level.get_block_state(pos).is_(self):
            if state.can_survive(level, pos):
                self.check_tick_on_neighbor(level, pos, state)
            else:
                level.remove_block(pos, False)  # dropResources is not simulated
                for direction in ALL:
                    level.update_neighbors_at(offset(pos, direction), self)

    def check_tick_on_neighbor(self, level: Level, pos: Pos, state: BlockState) -> None:
        if not self.is_locked(level, pos, state):
            on = state.get(POWERED)
            should_turn_on = self.should_turn_on(level, pos, state)
            if on != should_turn_on and not level.will_tick_this_tick(pos, self):
                priority = TickPriority.HIGH
                if self.should_prioritize(level, pos, state):
                    priority = TickPriority.EXTREMELY_HIGH
                elif on:
                    priority = TickPriority.VERY_HIGH
                level.schedule_tick(pos, self, self.get_delay(state), priority)

    def is_locked(self, level: Level, pos: Pos, state: BlockState) -> bool:
        return False

    def should_turn_on(self, level: Level, pos: Pos, state: BlockState) -> bool:
        return self.get_input_signal(level, pos, state) > 0

    def get_input_signal(self, level: Level, pos: Pos, state: BlockState) -> int:
        direction = facing(state)
        target = offset(pos, direction)
        signal = level.get_signal(target, direction)
        if signal >= 15:
            return signal
        target_state = level.get_block_state(target)
        wire_power = (
            int(target_state.get(POWER)) if target_state.block.id == ids.REDSTONE_WIRE else 0
        )
        return max(signal, wire_power)

    def get_alternate_signal(self, level: Level, pos: Pos, state: BlockState) -> int:
        direction = facing(state)
        clockwise = direction.clockwise()
        counter_clockwise = direction.counter_clockwise()
        diodes_only = self.side_input_diodes_only()
        return max(
            level.get_control_input_signal(offset(pos, clockwise), clockwise, diodes_only),
            level.get_control_input_signal(
                offset(pos, counter_clockwise), counter_clockwise, diodes_only
            ),
        )

    def side_input_diodes_only(self) -> bool:
        return False

    def get_delay(self, state: BlockState) -> int:
        raise NotImplementedError

    def get_output_signal(self, level: Level, pos: Pos, state: BlockState) -> int:
        return 15

    def should_prioritize(self, level: Level, pos: Pos, state: BlockState) -> bool:
        """``shouldPrioritize`` L196: the block in front is a diode not facing back at us."""
        direction = facing(state).opposite
        front = level.get_block_state(offset(pos, direction))
        return front.block.is_diode and facing(front) is not direction

    # --- signals ------------------------------------------------------------------------
    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return self.get_output_signal(level, pos, state) if state.get(POWERED) else 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return state.get_signal(level, pos, direction)

    def get_signal(self, state: BlockState, level: Level, pos: Pos, direction: Direction) -> int:
        return self.own_signal(state, level, pos) if facing(state) is direction else 0

    # --- placement and updates ------------------------------------------------------------
    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state.with_(HORIZONTAL_FACING, facing(ctx.requested))

    def set_placed_by(self, level: Level, pos: Pos, state: BlockState) -> None:
        if self.should_turn_on(level, pos, state):
            level.schedule_tick(pos, self, 1)

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        self.update_neighbors_in_front(level, pos, state)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        if not moved_by_piston:
            self.update_neighbors_in_front(level, pos, state)

    def update_neighbors_in_front(self, level: Level, pos: Pos, state: BlockState) -> None:
        direction = facing(state)
        front = offset(pos, direction.opposite)
        level.neighbor_changed(front, self)
        level.update_neighbors_at_except_from_facing(front, self, direction)


class RepeaterBlock(DiodeBlock):
    properties = (HORIZONTAL_FACING, DELAY, LOCKED, POWERED)

    def __init__(self) -> None:
        super().__init__(ids.REPEATER)
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(DELAY, 1)
            .with_(LOCKED, False)
            .with_(POWERED, False)
        )

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        level.set_block_and_update(pos, state.cycle(DELAY))
        return True

    def get_delay(self, state: BlockState) -> int:
        return int(state.get(DELAY)) * 2

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        state = super().get_state_for_placement(ctx)
        assert state is not None
        return state.with_(LOCKED, self.is_locked(ctx.level, ctx.pos, state))

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction is Direction.DOWN and not self.can_survive_on(level, neighbor_pos, neighbor):
            return level.air
        if direction.axis is not facing(state).axis:
            return state.with_(LOCKED, self.is_locked(level, pos, state))
        return state

    def should_redstone_wire_connect_to(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction | None
    ) -> bool:
        return direction is not None and direction.axis is facing(state).axis

    def is_locked(self, level: Level, pos: Pos, state: BlockState) -> bool:
        return self.get_alternate_signal(level, pos, state) > 0

    def side_input_diodes_only(self) -> bool:
        return True
