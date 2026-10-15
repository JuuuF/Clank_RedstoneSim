"""Pressure plates: ``BasePressurePlateBlock.java``, ``PressurePlateBlock.java`` and
``WeightedPressurePlateBlock.java``.

Mobs and items are not simulated; the editor puts "visitors" on a plate instead: a number
of mobs (players count) and of other entities (items) standing on it for some ticks
(``Level.plate_visitors``). Falling blocks are real entities (``sim/entities.py``): they
press a plate they pass or land on, and count while they touch it. In the entity phase a
visited, unpressed plate is pressed (``entityInside`` → ``checkPressed``); while pressed
it rechecks every 20 ticks (10 for weighted plates) and releases once nobody is left.
Stone and polished-blackstone plates count mobs only (``PressurePlateSensitivity.MOBS``),
wooden plates everything, weighted plates count entities: light (gold) up to 15, heavy
(iron) up to 150.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, ClassVar

from redsim.core.direction import Direction
from redsim.core.pos import Pos, below
from redsim.world.block import Block, BlockState, PushReaction, UpdateFlags
from redsim.world.properties import POWER, POWERED
from redsim.world.shape import Shape, SupportType, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: ``BasePressurePlateBlock.SHAPE``. Not as in the game: the pressed shape is half a pixel
#: high, which the whole-pixel shape grid cannot hold. Plates have no collision and nothing
#: rests on them, so using the same shape changes no outcome.
SHAPE = column(14, 0, 1)

#: ``BlockSetType`` with ``PressurePlateSensitivity.MOBS``; every other plate is EVERYTHING.
MOBS_ONLY = frozenset(
    {"minecraft:stone_pressure_plate", "minecraft:polished_blackstone_pressure_plate"}
)
WOODS = (
    "oak", "spruce", "birch", "jungle", "acacia", "cherry", "dark_oak", "pale_oak",
    "mangrove", "bamboo", "crimson", "warped", "poplar",
)  # fmt: skip
PLATE_IDS = (
    "minecraft:stone_pressure_plate",
    "minecraft:polished_blackstone_pressure_plate",
    *(f"minecraft:{wood}_pressure_plate" for wood in WOODS),
)


class BasePressurePlateBlock(Block):
    force_solid = True  # forceSolidOn

    def __init__(self, block_id: str) -> None:
        super().__init__(
            block_id, has_collision=False, push_reaction=PushReaction.POPPED, destroy_speed=0.5
        )

    pressed_time: ClassVar[int] = 20  # getPressedTime

    # --- the subclass parts --------------------------------------------------------------
    def signal_for_state(self, state: BlockState) -> int:
        raise NotImplementedError

    def with_signal(self, state: BlockState, signal: int) -> BlockState:
        raise NotImplementedError

    def signal_strength(self, level: Level, pos: Pos) -> int:
        raise NotImplementedError

    # --- BasePressurePlateBlock ---------------------------------------------------------
    def get_shape(self, state: BlockState) -> Shape:
        return SHAPE

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``canSurvive`` L46: a rigid top, or centre support, below."""
        support = below(pos)
        under = level.get_block_state(support)
        return under.is_face_sturdy(
            level, support, Direction.UP, SupportType.RIGID
        ) or under.is_face_sturdy(level, support, Direction.UP, SupportType.CENTER)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        """``updateShape`` L30: breaks without support below."""
        if direction is Direction.DOWN and not self.can_survive(state, level, pos):
            return level.air
        return state

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``tick`` L52: recheck while pressed."""
        signal = self.signal_for_state(state)
        if signal > 0:
            self.check_pressed(level, pos, state, signal)

    def entity_inside(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``entityInside`` L60: an entity presses an unpressed plate."""
        signal = self.signal_for_state(state)
        if signal == 0:
            self.check_pressed(level, pos, state, signal)

    def entity_inside_entity(
        self, state: BlockState, level: Level, pos: Pos, entity: object
    ) -> None:
        """``entityInside`` for a simulated entity (a falling block)."""
        self.entity_inside(state, level, pos)

    def check_pressed(self, level: Level, pos: Pos, state: BlockState, old_signal: int) -> None:
        """``checkPressed`` L71."""
        signal = self.signal_strength(level, pos)
        if old_signal != signal:
            level.set_block(pos, self.with_signal(state, signal), UpdateFlags.CLIENTS)
            self.update_neighbours(level, pos)
        if signal > 0:
            level.schedule_tick(pos, self, self.pressed_time)

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        """``affectNeighborsAfterRemoval`` L94."""
        if not moved_by_piston and self.signal_for_state(state) > 0:
            self.update_neighbours(level, pos)

    def update_neighbours(self, level: Level, pos: Pos) -> None:
        """``updateNeighbours`` L100: around the plate and around the block below."""
        level.update_neighbors_at(pos, self)
        level.update_neighbors_at(below(pos), self)

    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return self.signal_for_state(state)

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        """``getDirectSignal`` L106: strong power only into the block below."""
        return self.signal_for_state(state) if direction is Direction.UP else 0


class PressurePlateBlock(BasePressurePlateBlock):
    properties = (POWERED,)

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id)
        self.register_default_state(self.default_state.with_(POWERED, False))
        self.mobs_only = block_id in MOBS_ONLY

    def signal_for_state(self, state: BlockState) -> int:
        return 15 if state.get(POWERED) else 0

    def with_signal(self, state: BlockState, signal: int) -> BlockState:
        return state.with_(POWERED, signal > 0)

    def signal_strength(self, level: Level, pos: Pos) -> int:
        """``getSignalStrength``: any entity (mobs only for stone plates) gives 15."""
        mobs, others = level.plate_visitors_at(pos)
        return 15 if mobs + (0 if self.mobs_only else others) > 0 else 0


class WeightedPressurePlateBlock(BasePressurePlateBlock):
    properties = (POWER,)
    pressed_time = 10

    def __init__(self, block_id: str, max_weight: int) -> None:
        super().__init__(block_id)
        self.register_default_state(self.default_state.with_(POWER, 0))
        self.max_weight = max_weight

    def signal_for_state(self, state: BlockState) -> int:
        return int(state.get(POWER))

    def with_signal(self, state: BlockState, signal: int) -> BlockState:
        return state.with_(POWER, signal)

    def signal_strength(self, level: Level, pos: Pos) -> int:
        """``getSignalStrength``: ceil(min(count, max) / max · 15) with float math."""
        mobs, others = level.plate_visitors_at(pos)
        count = min(mobs + others, self.max_weight)
        if count <= 0:
            return 0
        import numpy as np

        percent = np.float32(min(self.max_weight, count)) / np.float32(self.max_weight)
        return math.ceil(float(np.float32(percent * np.float32(15.0))))
