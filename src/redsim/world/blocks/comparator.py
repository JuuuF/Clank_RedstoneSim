"""Comparator: ``net/minecraft/world/level/block/ComparatorBlock.java`` and
``block/entity/ComparatorBlockEntity.java``.

Methods: ``getDelay`` L39, ``updateShape`` L44, ``getOutputSignal`` L60,
``calculateOutputSignal`` L64, ``shouldTurnOn`` L79, ``getInputSignal`` L90,
``useWithoutItem`` L123, ``checkTickOnNeighbor`` L140, ``refreshOutputState`` L151, ``tick`` L174.
Item frames (entities) are not simulated, so the "item frame behind a block" input is
always absent. See doc/mechanics/comparator.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos, offset
from redsim.world import ids
from redsim.world.block import BlockState, PlacementContext, UpdateFlags
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.blocks.diode import DiodeBlock, facing
from redsim.world.properties import HORIZONTAL_FACING, MODE_COMPARATOR, POWERED
from redsim.world.tick_priority import TickPriority

if TYPE_CHECKING:
    from redsim.sim.level import Level


@register_block_entity
class ComparatorBlockEntity(BlockEntity):
    type_id = "comparator"
    valid_blocks = frozenset({ids.COMPARATOR})

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        self.output = 0

    def to_json(self) -> dict[str, Any]:
        return {"OutputSignal": self.output}

    def load_json(self, data: dict[str, Any]) -> None:
        self.output = int(data.get("OutputSignal", 0))

    def describe(self) -> str:
        return f"comparator output={self.output}"


class ComparatorBlock(DiodeBlock):
    properties = (HORIZONTAL_FACING, MODE_COMPARATOR, POWERED)
    has_block_entity = True

    def __init__(self) -> None:
        super().__init__(ids.COMPARATOR)
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(POWERED, False)
            .with_(MODE_COMPARATOR, "compare")
        )

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return ComparatorBlockEntity(pos, state)

    def get_delay(self, state: BlockState) -> int:
        return 2

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
        return state

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state.with_(HORIZONTAL_FACING, facing(ctx.requested))

    # --- signal computation -------------------------------------------------------------
    def stored_output(self, level: Level, pos: Pos) -> int:
        be = level.get_block_entity(pos)
        return be.output if isinstance(be, ComparatorBlockEntity) else 0

    def get_output_signal(self, level: Level, pos: Pos, state: BlockState) -> int:
        return self.stored_output(level, pos)

    def calculate_output_signal(self, level: Level, pos: Pos, state: BlockState) -> int:
        input_signal = self.get_input_signal(level, pos, state)
        if input_signal == 0:
            return 0
        alternate = self.get_alternate_signal(level, pos, state)
        if alternate > input_signal:
            return 0
        if state.get(MODE_COMPARATOR) == "subtract":
            return input_signal - alternate
        return input_signal

    def should_turn_on(self, level: Level, pos: Pos, state: BlockState) -> bool:
        input_signal = self.get_input_signal(level, pos, state)
        if input_signal == 0:
            return False
        side = self.get_alternate_signal(level, pos, state)
        if input_signal > side:
            return True
        return input_signal == side and state.get(MODE_COMPARATOR) == "compare"

    def get_input_signal(self, level: Level, pos: Pos, state: BlockState) -> int:
        result = super().get_input_signal(level, pos, state)
        direction = facing(state)
        target = offset(pos, direction)
        target_state = level.get_block_state(target)
        if target_state.has_analog_output_signal():
            result = target_state.get_analog_output_signal(level, target, direction.opposite)
        elif result < 15 and target_state.is_redstone_conductor(level, target):
            target = offset(target, direction)
            target_state = level.get_block_state(target)
            # No item frames: only an analog block can replace the signal.
            if target_state.has_analog_output_signal():
                result = target_state.get_analog_output_signal(level, target, direction.opposite)
        return result

    # --- updates ------------------------------------------------------------------------
    def check_tick_on_neighbor(self, level: Level, pos: Pos, state: BlockState) -> None:
        if not level.will_tick_this_tick(pos, self):
            output = self.calculate_output_signal(level, pos, state)
            old = self.stored_output(level, pos)
            if output != old or state.get(POWERED) != self.should_turn_on(level, pos, state):
                priority = (
                    TickPriority.HIGH
                    if self.should_prioritize(level, pos, state)
                    else TickPriority.NORMAL
                )
                level.schedule_tick(pos, self, 2, priority)

    def refresh_output_state(self, level: Level, pos: Pos, state: BlockState) -> None:
        output = self.calculate_output_signal(level, pos, state)
        be = level.get_block_entity(pos)
        old = 0
        if isinstance(be, ComparatorBlockEntity):
            old = be.output
            be.output = output
        if old != output or state.get(MODE_COMPARATOR) == "compare":
            source_on = self.should_turn_on(level, pos, state)
            is_on = state.get(POWERED)
            if is_on and not source_on:
                level.set_block(pos, state.with_(POWERED, False), UpdateFlags.CLIENTS)
            elif not is_on and source_on:
                level.set_block(pos, state.with_(POWERED, True), UpdateFlags.CLIENTS)
            self.update_neighbors_in_front(level, pos, state)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        self.refresh_output_state(level, pos, state)

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        state = state.cycle(MODE_COMPARATOR)
        level.set_block(pos, state, UpdateFlags.CLIENTS)
        if level.get_block_state(pos).is_(self):
            self.refresh_output_state(level, pos, state)
        return True
