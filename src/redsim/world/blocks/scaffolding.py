"""Scaffolding: a block that stands on a sturdy block or reaches out sideways from other
scaffolding up to 6 blocks, and breaks or falls when it loses that.

Sources (relative to ``data/minecraft_src/server-src/net/minecraft/world/level/block/``):

* ``ScaffoldingBlock.java``: ``getDistance`` (0 on a sturdy top; the distance of the
  scaffolding below; one more than the nearest scaffolding beside it; 7 = unsupported),
  ``isBottom`` (supported from the side with no scaffolding below), ``onPlace`` and
  ``updateShape`` (a tick 1 later), ``tick`` (new distance and ``bottom``; at 7 it breaks,
  or falls as a falling block if it was at 7 already), ``canSurvive`` (distance < 7),
  shapes: ``SHAPE_STABLE`` (top 2 pixels and four 2×2 legs), ``SHAPE_UNSTABLE`` with a
  2-pixel bottom; ``getCollisionShape`` depends on who asks: empty for placing, the stable
  shape for an entity above it (and for ``CollisionContext.empty()``: support shapes),
  the 2-pixel bottom for an entity inside a ``bottom`` scaffolding.
* ``ScaffoldingBlockItem.java``: a scaffolding cannot be placed where it would have
  distance 7 (``updatePlacementContext``).
* ``Blocks.java``: ``noCollision`` (no effect: it has its own collision shape),
  ``dynamicShape`` (no shape cache: never ``solid``), ``pushReaction(POPPED)``, never a
  redstone conductor, instant to break.

Not as in the game (doc/differences.md): water is not simulated (``waterlogged`` stays
inert: no water tick, a falling scaffolding does not take up water where it lands). In the
editor a scaffolding is placed where you point; clicking scaffolding in the game moves the
new one to the top of the column or along the bridge (``updatePlacementContext``), which
gives the same block at that spot. Breaking drops no item (items are not simulated).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import HORIZONTAL, Direction
from redsim.core.pos import Pos, below, offset
from redsim.world.block import BlockState, PlacementContext
from redsim.world.blocks.openable import _GameBlock, box_z, rotate_horizontal
from redsim.world.properties import WATERLOGGED, boolean, integer
from redsim.world.shape import Shape, box, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: ``BlockStateProperties.STABILITY_DISTANCE``.
DISTANCE = integer("distance", 0, 7)
BOTTOM = boolean("bottom")
STABILITY_MAX_DISTANCE = 7


def _union(*shapes: Shape) -> Shape:
    out = shapes[0]
    for shape in shapes[1:]:
        out = out | shape
    return out


_LEGS = rotate_horizontal(box(0, 0, 0, 2, 16, 2))
SHAPE_STABLE = _union(column(16, 14, 16), *_LEGS.values())
SHAPE_UNSTABLE_BOTTOM = column(16, 0, 2)
SHAPE_UNSTABLE = _union(
    SHAPE_STABLE, SHAPE_UNSTABLE_BOTTOM, *rotate_horizontal(box_z(16, 0, 2, 0, 2)).values()
)

Box = tuple[float, float, float, float, float, float]
_P = 1.0 / 16.0
#: The stable shape and the unstable bottom as collision boxes in block units.
STABLE_BOXES: tuple[Box, ...] = (
    (0.0, 14 * _P, 0.0, 1.0, 1.0, 1.0),
    (0.0, 0.0, 0.0, 2 * _P, 14 * _P, 2 * _P),
    (14 * _P, 0.0, 0.0, 1.0, 14 * _P, 2 * _P),
    (0.0, 0.0, 14 * _P, 2 * _P, 14 * _P, 1.0),
    (14 * _P, 0.0, 14 * _P, 1.0, 14 * _P, 1.0),
)
BOTTOM_BOXES: tuple[Box, ...] = ((0.0, 0.0, 0.0, 1.0, 2 * _P, 1.0),)
#: ``1.0E-5F`` of ``EntityCollisionContext.isAbove`` (a float constant).
_ABOVE_EPSILON = 9.999999747378752e-06


def get_distance(level: Level, pos: Pos) -> int:
    """``ScaffoldingBlock.getDistance``."""
    under = below(pos)
    below_state = level.get_block_state(under)
    distance = STABILITY_MAX_DISTANCE
    if isinstance(below_state.block, ScaffoldingBlock):
        distance = int(below_state.get(DISTANCE))
    elif below_state.is_face_sturdy(level, under, Direction.UP):
        return 0
    for direction in HORIZONTAL:
        relative = level.get_block_state(offset(pos, direction))
        if isinstance(relative.block, ScaffoldingBlock):
            distance = min(distance, int(relative.get(DISTANCE)) + 1)
            if distance == 1:
                break
    return distance


def is_bottom(level: Level, pos: Pos, distance: int) -> bool:
    """``isBottom``: held from the side, with no scaffolding below."""
    return distance > 0 and not isinstance(
        level.get_block_state(below(pos)).block, ScaffoldingBlock
    )


class ScaffoldingBlock(_GameBlock):
    """``ScaffoldingBlock``."""

    properties = (DISTANCE, WATERLOGGED, BOTTOM)
    #: ``Properties.dynamicShape``: no shape cache, so the game finds it never ``solid``
    #: (``calculateSolid``: null cache) and always of "large" collision shape.
    dynamic_shape = True
    force_solid = False

    def __init__(self) -> None:
        super().__init__("minecraft:scaffolding")
        self.has_collision = False
        self.register_default_state(
            self.default_state.with_(DISTANCE, 7).with_(WATERLOGGED, False).with_(BOTTOM, False)
        )

    # --- shapes -------------------------------------------------------------------------
    def get_shape(self, state: BlockState) -> Shape:
        """``getShape`` for someone not holding scaffolding (holding it: a full block)."""
        return SHAPE_UNSTABLE if state.get(BOTTOM) else SHAPE_STABLE

    def get_collision_shape(self, state: BlockState) -> Shape:
        """``getCollisionShape`` with ``CollisionContext.empty()`` (``isAbove`` gives its
        default, true): the stable shape. It is the support shape, so the top is sturdy
        (wire, torches, rails can stand on it) and the sides and bottom are not."""
        return SHAPE_STABLE

    def get_dynamic_support_shape(self, state: BlockState, level: Level, pos: Pos) -> Shape:
        return SHAPE_STABLE

    def entity_collision_boxes(
        self, state: BlockState, pos: Pos, entity_bottom: float | None
    ) -> tuple[Box, ...]:
        """``getCollisionShape`` for an entity whose feet are at ``entity_bottom`` (None: a
        player placing a block, ``isPlacement``), in block units."""
        if entity_bottom is None:
            return ()
        y = pos[1]
        if entity_bottom > y + 1.0 - _ABOVE_EPSILON:  # isAbove(Shapes.block()), not descending
            return STABLE_BOXES
        if (
            state.get(DISTANCE) != 0
            and state.get(BOTTOM)
            and entity_bottom > y + 0.0 - _ABOVE_EPSILON  # isAbove(SHAPE_BELOW_BLOCK)
        ):
            return BOTTOM_BOXES
        return ()

    # --- placement ----------------------------------------------------------------------
    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        return get_distance(level, pos) < STABILITY_MAX_DISTANCE

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        """``getStateForPlacement``: its distance and ``bottom`` (no water: not
        simulated)."""
        distance = get_distance(ctx.level, ctx.pos)
        return (
            self.default_state.with_(WATERLOGGED, False)
            .with_(DISTANCE, distance)
            .with_(BOTTOM, is_bottom(ctx.level, ctx.pos, distance))
        )

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``ScaffoldingBlockItem``: nothing is placed where it would have distance 7. Not
        as in the game: clicking scaffolding does not move the new one to the column's top
        or the bridge's end (``updatePlacementContext``): it goes where the editor points."""
        if get_distance(level, pos) == STABILITY_MAX_DISTANCE:
            return None
        return self.get_state_for_placement(PlacementContext(level, pos, self.default_state))

    # --- updates ------------------------------------------------------------------------
    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        """``onPlace``: every new state checks itself a tick later."""
        level.schedule_tick(pos, self, 1)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        """``updateShape``: any neighbor change rechecks a tick later. Not as in the game:
        a waterlogged scaffolding schedules no water tick (water is not simulated)."""
        level.schedule_tick(pos, self, 1)
        return state

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        """``tick``: take the new distance; unsupported, it breaks, or it falls if it
        was unsupported already (a scaffolding put with distance 7)."""
        distance = get_distance(level, pos)
        new_state = state.with_(DISTANCE, distance).with_(BOTTOM, is_bottom(level, pos, distance))
        if distance == STABILITY_MAX_DISTANCE:
            if state.get(DISTANCE) == STABILITY_MAX_DISTANCE:
                from redsim.world.blocks.falling import fall

                fall(level, pos, new_state)
            else:
                level.destroy_block(pos, True)
        elif state is not new_state:
            level.set_block_and_update(pos, new_state)
