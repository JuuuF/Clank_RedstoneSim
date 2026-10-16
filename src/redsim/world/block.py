"""Blocks and interned block states.

``Block`` mirrors the overridable hooks of ``BlockBehaviour`` (``net/minecraft/world/level/
block/state/BlockBehaviour.java``) that matter for redstone; ``BlockState`` mirrors
``BlockBehaviour.BlockStateBase``, delegating to its block. States are interned: every
property combination exists exactly once, so ``a is b`` matches Java's ``==`` on states.

Hook signatures follow the Java methods. ``level`` is a ``redsim.sim.level.Level``; it is
typed loosely here to keep ``redsim.world`` independent of ``redsim.sim``.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Final

from redsim.core.compiled import mypyc_attr
from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world.properties import Property
from redsim.world.shape import EMPTY, FULL_BLOCK, Shape, SupportType

if TYPE_CHECKING:
    from redsim.sim.level import Level
    from redsim.world.block_entity import BlockEntity


class PushReaction(Enum):
    """``net/minecraft/world/level/material/PushReaction.java``."""

    PUSH_PULL = "push_pull"
    PUSH = "push"
    POPPED = "popped"
    IMMOVEABLE = "immoveable"
    IGNORE_ENTITY = "ignore_entity"


class Conductor(Enum):
    """``Properties.isRedstoneConductor`` choices used by vanilla blocks."""

    DEFAULT = "default"  # isCollisionShapeFullBlock
    NEVER = "never"  # Blocks::never
    ALWAYS = "always"  # Blocks::always


class UpdateFlags:
    """``Block.UPDATE_*`` constants (Block.java L90-106)."""

    NEIGHBORS: Final = 1
    CLIENTS: Final = 2
    INVISIBLE: Final = 4
    IMMEDIATE: Final = 8
    KNOWN_SHAPE: Final = 16
    SUPPRESS_DROPS: Final = 32
    MOVE_BY_PISTON: Final = 64
    SKIP_SHAPE_UPDATE_ON_WIRE: Final = 128
    SKIP_BLOCK_ENTITY_SIDEEFFECTS: Final = 256
    SKIP_ON_PLACE: Final = 512
    ALL: Final = 3
    ALL_IMMEDIATE: Final = 11
    UPDATE_LIMIT: Final = 512


class PlacementContext:
    """The parts of ``BlockPlaceContext`` the simulator needs.

    Not as in the game: the game derives a placed block's orientation from the player's
    look and the clicked point; here ``requested`` states it directly (``facing``,
    ``face``, ``half``, ``axis``, a door's ``hinge``: from the editor's look in the GUI,
    as written in ``redsim-cli place``). Each block's ``get_state_for_placement`` keeps
    that orientation and derives everything else the way the game does (power, shapes,
    neighbors). A state given this way can have an orientation a player could not get at
    that spot, such as a door hinge against the neighbors' rule (doc/differences.md).
    """

    def __init__(
        self,
        level: Level,
        pos: Pos,
        requested: BlockState,
    ) -> None:
        self.level = level
        self.pos = pos
        self.requested = requested


class BlockState:
    """An interned, immutable block state (``BlockBehaviour.BlockStateBase``)."""

    __slots__ = ("block", "values", "_neighbors", "_shape_cache", "_repr", "_conductor")

    def __init__(self, block: Block, values: tuple[Any, ...]) -> None:
        self.block = block
        self.values = values
        self._neighbors: dict[tuple[str, Any], BlockState] = {}
        self._shape_cache: dict[str, Shape] = {}
        self._repr: str | None = None  # states are immutable: the text is made once
        self._conductor: bool | None = None  # cached when it depends on the state only

    # --- StateHolder -------------------------------------------------------------------
    def get(self, prop: Property) -> Any:
        return self.values[self.block.property_index[prop.name]]

    def has(self, prop: Property) -> bool:
        index = self.block.property_index.get(prop.name)
        return index is not None and self.block.properties[index] is prop

    def with_(self, prop: Property, value: Any) -> BlockState:
        """``StateHolder.setValue``."""
        key = (prop.name, value)
        found = self._neighbors.get(key)
        if found is None:
            index = self.block.property_index[prop.name]
            if value not in prop.values:
                raise ValueError(f"{value!r} is not a valid {prop.name} for {self.block.id}")
            values = self.values[:index] + (value,) + self.values[index + 1 :]
            found = self.block.state_definition.states[values]
            self._neighbors[key] = found
        return found

    def cycle(self, prop: Property) -> BlockState:
        return self.with_(prop, prop.next_value(self.get(prop)))

    def is_(self, block: Block) -> bool:
        return self.block is block

    @property
    def is_air(self) -> bool:
        return self.block.is_air

    # --- shapes and physical properties ---------------------------------------------------
    def _shape(self, kind: str) -> Shape:
        shape = self._shape_cache.get(kind)
        if shape is None:
            if kind == "shape":
                shape = self.block.get_shape(self)
            elif kind == "collision":
                shape = self.block.get_collision_shape(self)
            else:
                shape = self.block.get_block_support_shape(self)
            self._shape_cache[kind] = shape
        return shape

    def get_shape(self) -> Shape:
        return self._shape("shape")

    def get_collision_shape(self) -> Shape:
        return self._shape("collision")

    def get_block_support_shape(self) -> Shape:
        return self._shape("support")

    def is_collision_shape_full_block(self) -> bool:
        return self.get_collision_shape().is_full_block()

    def is_face_sturdy(
        self, level: Level, pos: Pos, direction: Direction, support: SupportType = SupportType.FULL
    ) -> bool:
        if self.block.dynamic_shape:
            # No shape cache for dynamic shapes (BlockStateBase.initCache L510): the support
            # shape is computed with the real level, e.g. from a moving piston's entity.
            shape = self.block.get_dynamic_support_shape(self, level, pos)
            return shape.is_face_sturdy(direction, support)
        return self.get_block_support_shape().is_face_sturdy(direction, support)

    def is_redstone_conductor(self, level: Level, pos: Pos) -> bool:
        cached = self._conductor
        if cached is not None:
            return cached
        block = self.block
        result = block.is_redstone_conductor(self, level, pos)
        # The default rule reads only the state's own collision shape (the game caches it
        # per state too, BlockStateBase.Cache); blocks with their own rule or a dynamic
        # shape are asked every time.
        if not block.dynamic_shape and (
            type(block).is_redstone_conductor is Block.is_redstone_conductor
        ):
            self._conductor = result
        return result

    def is_solid(self) -> bool:
        """``BlockStateBase.isSolid`` (``calculateSolid``, BlockBehaviour.java L483)."""
        forced = self.block.force_solid
        if forced is not None:
            return forced
        shape = self.get_collision_shape()
        if shape.is_empty():
            return False
        x0, y0, z0, x1, y1, z1 = shape.bounds()
        size = ((x1 - x0) + (y1 - y0) + (z1 - z0)) / 3 / 16
        return size >= 0.7291666666666666 or (y1 - y0) >= 16

    def get_piston_push_reaction(self) -> PushReaction:
        return self.block.push_reaction

    def get_destroy_speed(self) -> float:
        return self.block.destroy_speed

    @property
    def has_block_entity(self) -> bool:
        return self.block.has_block_entity

    # --- signals --------------------------------------------------------------------------
    def is_signal_source(self) -> bool:
        return self.block.is_signal_source(self)

    def get_signal(self, level: Level, pos: Pos, direction: Direction) -> int:
        return self.block.get_signal(self, level, pos, direction)

    def get_direct_signal(self, level: Level, pos: Pos, direction: Direction) -> int:
        return self.block.get_direct_signal(self, level, pos, direction)

    def get_own_signal(self, level: Level, pos: Pos) -> int:
        return self.block.own_signal(self, level, pos)

    def should_redstone_wire_connect_to(
        self, level: Level, pos: Pos, direction: Direction | None
    ) -> bool:
        return self.block.should_redstone_wire_connect_to(self, level, pos, direction)

    def has_analog_output_signal(self) -> bool:
        return self.block.has_analog_output_signal(self)

    def get_analog_output_signal(self, level: Level, pos: Pos, direction: Direction) -> int:
        return self.block.get_analog_output_signal(self, level, pos, direction)

    # --- lifecycle --------------------------------------------------------------------------
    def can_survive(self, level: Level, pos: Pos) -> bool:
        return self.block.can_survive(self, level, pos)

    def update_shape(
        self, level: Level, pos: Pos, direction: Direction, neighbor_pos: Pos, neighbor: BlockState
    ) -> BlockState:
        return self.block.update_shape(self, level, pos, direction, neighbor_pos, neighbor)

    def handle_neighbor_changed(
        self, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        self.block.neighbor_changed(self, level, pos, source, moved_by_piston)

    def on_place(
        self, level: Level, pos: Pos, old_state: BlockState, moved_by_piston: bool
    ) -> None:
        self.block.on_place(self, level, pos, old_state, moved_by_piston)

    def affect_neighbors_after_removal(self, level: Level, pos: Pos, moved_by_piston: bool) -> None:
        self.block.affect_neighbors_after_removal(self, level, pos, moved_by_piston)

    def tick(self, level: Level, pos: Pos) -> None:
        self.block.tick(self, level, pos)

    def trigger_event(self, level: Level, pos: Pos, b0: int, b1: int) -> bool:
        return self.block.trigger_event(self, level, pos, b0, b1)

    def update_neighbour_shapes(self, level: Level, pos: Pos, flags: int, limit: int = 512) -> None:
        """``BlockStateBase.updateNeighbourShapes`` (BlockBehaviour.java L735)."""
        from redsim.core.direction import SHAPE_UPDATE_ORDER
        from redsim.core.pos import offset

        for direction in SHAPE_UPDATE_ORDER:
            level.neighbor_shape_changed(
                direction.opposite, offset(pos, direction), pos, self, flags, limit
            )

    def update_indirect_neighbour_shapes(
        self, level: Level, pos: Pos, flags: int, limit: int = 512
    ) -> None:
        self.block.update_indirect_neighbour_shapes(self, level, pos, flags, limit)

    # --- presentation helpers -------------------------------------------------------------
    def properties_dict(self) -> dict[str, str]:
        props = {
            prop.name: prop.serialize(value)
            for prop, value in zip(self.block.properties, self.values, strict=True)
        }
        if self.block.extra_properties:  # a foreign block keeps the game's properties
            props.update(self.block.extra_properties)
        return props

    def __repr__(self) -> str:
        if self._repr is None:
            props = ",".join(f"{k}={v}" for k, v in self.properties_dict().items())
            self._repr = f"{self.block.id}[{props}]" if props else self.block.id
        return self._repr


class StateDefinition:
    """All states of one block (``StateDefinition``)."""

    def __init__(self, block: Block, properties: Sequence[Property]) -> None:
        self.states: dict[tuple[Any, ...], BlockState] = {}
        for values in itertools.product(*(p.values for p in properties)):
            self.states[values] = BlockState(block, values)

    def any(self) -> BlockState:
        return next(iter(self.states.values()))

    def all(self) -> Iterable[BlockState]:
        return self.states.values()


@mypyc_attr(allow_interpreted_subclasses=True)
class Block:
    """Base block with ``BlockBehaviour`` defaults. Subclasses override the hooks."""

    properties: ClassVar[tuple[Property, ...]] = ()
    #: Properties carried as text only (``ForeignBlock``: blocks not simulated).
    extra_properties: dict[str, str] = {}  # noqa: RUF012 - never mutated

    def __init__(
        self,
        block_id: str,
        *,
        has_collision: bool = True,
        push_reaction: PushReaction = PushReaction.PUSH_PULL,
        destroy_speed: float = 1.0,
        conductor: Conductor = Conductor.DEFAULT,
        is_air: bool = False,
    ) -> None:
        self.id = block_id
        self.name = block_id.split(":", 1)[-1]  # e.g. "redstone_wire" (traces use it a lot)
        self.has_collision = has_collision
        self.push_reaction = push_reaction
        self.destroy_speed = destroy_speed
        self.conductor = conductor
        self.is_air = is_air
        self.property_index = {p.name: i for i, p in enumerate(self.properties)}
        self.state_definition = StateDefinition(self, self.properties)
        self.default_state = self.state_definition.any()

    def register_default_state(self, state: BlockState) -> None:
        self.default_state = state

    @property
    def instrument(self) -> str:
        """``BlockBehaviour.Properties.instrument`` (what a note block below plays)."""
        from redsim.world.instruments import INSTRUMENTS

        return INSTRUMENTS.get(self.id, "harp")

    # --- block entities -------------------------------------------------------------------
    has_block_entity: ClassVar[bool] = False
    has_ticker: ClassVar[bool] = False
    #: ``BaseRailBlock`` instances get removal side effects even without a block change.
    is_rail: ClassVar[bool] = False
    #: ``DiodeBlock.isDiode`` (repeaters and comparators).
    is_diode: ClassVar[bool] = False
    #: ``Properties.forceSolidOn/Off``; None means "derived from the collision shape".
    force_solid: ClassVar[bool | None] = None
    #: ``Properties.dynamicShape``: support/collision depend on the level (no cache).
    dynamic_shape: ClassVar[bool] = False

    def get_dynamic_support_shape(self, state: BlockState, level: Level, pos: Pos) -> Shape:
        """Support shape of a ``dynamic_shape`` block, evaluated in the level."""
        return state.get_block_support_shape()

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return None

    # --- shapes ------------------------------------------------------------------------------
    def get_shape(self, state: BlockState) -> Shape:
        return FULL_BLOCK

    def get_collision_shape(self, state: BlockState) -> Shape:
        return state.get_shape() if self.has_collision else EMPTY

    def get_block_support_shape(self, state: BlockState) -> Shape:
        return state.get_collision_shape()

    def is_redstone_conductor(self, state: BlockState, level: Level, pos: Pos) -> bool:
        if self.conductor is Conductor.NEVER:
            return False
        if self.conductor is Conductor.ALWAYS:
            return True
        return state.is_collision_shape_full_block()

    # --- signals (BlockBehaviour L360-385) ------------------------------------------------
    def is_signal_source(self, state: BlockState) -> bool:
        return False

    def should_redstone_wire_connect_to(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction | None
    ) -> bool:
        return state.is_signal_source() and direction is not None

    def get_signal(self, state: BlockState, level: Level, pos: Pos, direction: Direction) -> int:
        return self.own_signal(state, level, pos)

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return 0

    def get_direct_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return 0

    def has_analog_output_signal(self, state: BlockState) -> bool:
        return False

    def get_analog_output_signal(
        self, state: BlockState, level: Level, pos: Pos, direction: Direction
    ) -> int:
        return 0

    # --- lifecycle hooks --------------------------------------------------------------------
    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        return True

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        return state

    def update_indirect_neighbour_shapes(
        self, state: BlockState, level: Level, pos: Pos, flags: int, limit: int
    ) -> None:
        return None

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        return None

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        return None

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        return None

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        return None

    def trigger_event(self, state: BlockState, level: Level, pos: Pos, b0: int, b1: int) -> bool:
        return False

    # --- player interaction -----------------------------------------------------------------
    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``Block.getStateForPlacement``. The editor passes the requested state, which
        already carries the user's chosen orientation; blocks adjust derived properties."""
        return ctx.requested

    def set_placed_by(self, level: Level, pos: Pos, state: BlockState) -> None:
        return None

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """Right-click. Returns whether the interaction did something."""
        return False

    def player_will_destroy(self, level: Level, pos: Pos, state: BlockState) -> BlockState:
        return state

    def destroy(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``Block.destroy``, called after a player broke the block."""
        return None

    def __repr__(self) -> str:
        return f"Block({self.id})"
