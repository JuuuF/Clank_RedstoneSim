"""Fences, iron/copper bars, glass panes and walls: blocks that connect to their neighbors
through shape updates. Ported from ``CrossCollisionBlock``, ``FenceBlock``,
``IronBarsBlock`` (panes are ``IronBarsBlock`` / ``StainedGlassPaneBlock``; copper bars only
add oxidation, a random tick, not simulated) and ``WallBlock`` (26.3). Not as in the game:
leading animals with leads on fences (an entity mechanic) is left out; water is not simulated
(``waterlogged`` stays inert).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from redsim.core.direction import Direction
from redsim.core.pos import Pos, offset
from redsim.world.block import BlockState
from redsim.world.blocks.catalog_data import TAGS
from redsim.world.blocks.openable import (
    _GameBlock,
    box_z,
    column,
    connects_to_direction,
    rotate_horizontal,
)
from redsim.world.properties import WATERLOGGED, Property, boolean
from redsim.world.shape import Shape, box

if TYPE_CHECKING:
    from redsim.sim.level import Level

#: ``PipeBlock`` side properties of the cross-collision blocks.
SIDES: dict[Direction, Property] = {
    d: boolean(d.serialized)
    for d in (Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST)
}
WALL_SIDE_VALUES = ("none", "low", "tall")
WALL_SIDES: dict[Direction, Property] = {d: Property(d.serialized, WALL_SIDE_VALUES) for d in SIDES}
UP = boolean("up")
#: Blocks fences, bars and walls never connect to by their face
#: (``Block.isExceptionForConnection``).
_EXCEPTIONS = frozenset({
    "minecraft:barrier", "minecraft:carved_pumpkin", "minecraft:jack_o_lantern",
    "minecraft:melon", "minecraft:pumpkin",
})  # fmt: skip


def is_exception_for_connection(state: BlockState) -> bool:
    from redsim.world.blocks.catalog import LeavesBlock

    return isinstance(state.block, LeavesBlock) or state.block.id in _EXCEPTIONS


def _union(*shapes: Shape) -> Shape:
    grid = np.zeros_like(shapes[0].grid)
    for shape in shapes:
        grid = grid | shape.grid
    return Shape(grid)


def _cross_shapes(
    post_width: float, post_height: float, wall_width: float, wall_top: float
) -> dict[tuple[bool, ...], Shape]:
    """``CrossCollisionBlock.makeShapes`` (the wall from y=0): post plus an arm per
    connected side, keyed by (north, east, south, west)."""
    post = column(post_width, post_width, 0, post_height)
    arms = rotate_horizontal(box_z(wall_width, 0, min(wall_top, 16), 0, 8))
    out = {}
    for key in np.ndindex(2, 2, 2, 2):
        parts = [post] + [arms[d] for d, on in zip(SIDES, key, strict=True) if on]
        out[tuple(bool(v) for v in key)] = _union(*parts)
    return out


class CrossCollisionBlock(_GameBlock):
    """``CrossCollisionBlock``: four side booleans (``rotate``/``mirror`` move them)."""

    properties = (SIDES[Direction.NORTH], SIDES[Direction.EAST], SIDES[Direction.WEST],
                  SIDES[Direction.SOUTH], WATERLOGGED)  # fmt: skip
    shapes: dict[tuple[bool, ...], Shape] = {}
    collision_shapes: dict[tuple[bool, ...], Shape] = {}

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id)
        state = self.default_state.with_(WATERLOGGED, False)
        for prop in SIDES.values():
            state = state.with_(prop, False)
        self.register_default_state(state)

    @staticmethod
    def _key(state: BlockState) -> tuple[bool, ...]:
        return tuple(bool(state.get(prop)) for prop in SIDES.values())

    def get_shape(self, state: BlockState) -> Shape:
        return self.shapes[self._key(state)]

    def get_collision_shape(self, state: BlockState) -> Shape:
        return self.collision_shapes[self._key(state)]

    def attaches(self, neighbor: BlockState, face_solid: bool, direction: Direction) -> bool:
        raise NotImplementedError

    def _connections(self, level: Level, pos: Pos) -> dict[Direction, bool]:
        out = {}
        for direction in SIDES:
            at = offset(pos, direction)
            neighbor = level.get_block_state(at)
            sturdy = neighbor.is_face_sturdy(level, at, direction.opposite)
            out[direction] = self.attaches(neighbor, sturdy, direction.opposite)
        return out

    def get_state_for_placement(self, ctx: Any) -> BlockState | None:
        """``getStateForPlacement``: a side for every neighbor it attaches to."""
        state = ctx.requested
        for direction, on in self._connections(ctx.level, ctx.pos).items():
            state = state.with_(SIDES[direction], on)
        return state

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if not direction.is_horizontal:
            return state
        sturdy = neighbor.is_face_sturdy(level, neighbor_pos, direction.opposite)
        return state.with_(SIDES[direction], self.attaches(neighbor, sturdy, direction.opposite))

    def rotated(self, state: BlockState, quarter_turns: int) -> BlockState:
        """``rotate``: each side's value moves to the side turned clockwise."""
        out = state
        for direction, prop in SIDES.items():
            turned = direction
            for _ in range(quarter_turns % 4):
                turned = turned.clockwise()
            out = out.with_(SIDES[turned], state.get(prop))
        return out

    def mirrored(self, state: BlockState, axis: str) -> BlockState:
        """``mirror``: ``"x"`` (FRONT_BACK) swaps east and west, ``"z"`` (LEFT_RIGHT) north
        and south."""
        a, b = (
            (Direction.EAST, Direction.WEST) if axis == "x" else (Direction.NORTH, Direction.SOUTH)
        )
        return state.with_(SIDES[a], state.get(SIDES[b])).with_(SIDES[b], state.get(SIDES[a]))


class FenceBlock(CrossCollisionBlock):
    """``FenceBlock`` (4-pixel posts; collision 24 high): connects to sturdy faces, to fences
    of its kind (wooden or not) and to fence gates across its side."""

    #: The collision shape's top in pixels (``sim/entities.local_boxes``).
    collision_height = 24

    shapes = _cross_shapes(4, 16, 4, 16)
    collision_shapes = _cross_shapes(4, 24, 4, 24)

    def attaches(self, neighbor: BlockState, face_solid: bool, direction: Direction) -> bool:
        """``connectsTo``."""
        from redsim.world.blocks.openable import FenceGateBlock

        block_id = neighbor.block.id
        same_fence = block_id in TAGS["fences"] and (
            (block_id in TAGS["wooden_fences"]) == (self.id in TAGS["wooden_fences"])
        )
        gate = isinstance(neighbor.block, FenceGateBlock) and connects_to_direction(
            neighbor, direction
        )
        return (not is_exception_for_connection(neighbor) and face_solid) or same_fence or gate


class IronBarsBlock(CrossCollisionBlock):
    """``IronBarsBlock`` (bars and glass panes: 2-pixel posts): attach to sturdy faces, to
    other bars and panes, and to walls."""

    shapes = _cross_shapes(2, 16, 2, 16)
    collision_shapes = _cross_shapes(2, 16, 2, 16)

    def attaches(self, neighbor: BlockState, face_solid: bool, direction: Direction) -> bool:
        """``attachsTo``."""
        return (
            (not is_exception_for_connection(neighbor) and face_solid)
            or isinstance(neighbor.block, IronBarsBlock)
            or neighbor.block.id in TAGS["walls"]
        )


# ---------------------------------------------------------------- walls
_TEST_POST = column(2, 2, 0, 16)
_TEST_WALL = rotate_horizontal(box_z(2, 0, 16, 0, 9))


def _wall_shapes(post_height: float, wall_top: float) -> dict[tuple[Any, ...], Shape]:
    """``WallBlock.makeShapes`` keyed by (up, north, east, south, west)."""
    post = column(8, 8, 0, post_height)
    low = rotate_horizontal(box_z(6, 0, min(wall_top, 16), 0, 11))
    tall = rotate_horizontal(box_z(6, 0, min(post_height, 16), 0, 11))
    out = {}
    empty = box(0, 0, 0, 0, 0, 0)
    for up in (True, False):
        for sides in np.ndindex(3, 3, 3, 3):
            parts = [post if up else empty]
            for direction, side in zip(SIDES, sides, strict=True):
                if side == 1:
                    parts.append(low[direction])
                elif side == 2:
                    parts.append(tall[direction])
            key = (up, *(WALL_SIDE_VALUES[s] for s in sides))
            out[key] = _union(*parts)
    return out


def _covers(above: np.ndarray, test: Shape) -> bool:
    """``isCovered``: the test shape lies within the face shape of the block above (both
    reach through the whole height: compare their footprints)."""
    footprint = test.grid.any(axis=1)
    return bool(np.all(above[footprint]))


class WallBlock(_GameBlock):
    """``WallBlock``: sides none/low/tall and a post (``up``) from the neighbors and the
    collision shape of the block above."""

    #: The collision shape's top in pixels (``sim/entities.local_boxes``).
    collision_height = 24

    properties = (UP, WALL_SIDES[Direction.NORTH], WALL_SIDES[Direction.EAST],
                  WALL_SIDES[Direction.WEST], WALL_SIDES[Direction.SOUTH], WATERLOGGED)  # fmt: skip
    _shapes = _wall_shapes(16, 14)
    _collision = _wall_shapes(24, 24)

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id)
        state = self.default_state.with_(UP, True).with_(WATERLOGGED, False)
        for prop in WALL_SIDES.values():
            state = state.with_(prop, "none")
        self.register_default_state(state)

    @staticmethod
    def _key(state: BlockState) -> tuple[Any, ...]:
        return (state.get(UP), *(state.get(prop) for prop in WALL_SIDES.values()))

    def get_shape(self, state: BlockState) -> Shape:
        return self._shapes[self._key(state)]

    def get_collision_shape(self, state: BlockState) -> Shape:
        return self._collision[self._key(state)]

    def connects_to(self, neighbor: BlockState, face_solid: bool, direction: Direction) -> bool:
        """``connectsTo``."""
        from redsim.world.blocks.openable import FenceGateBlock

        gate = isinstance(neighbor.block, FenceGateBlock) and connects_to_direction(
            neighbor, direction
        )
        return (
            neighbor.block.id in TAGS["walls"]
            or (not is_exception_for_connection(neighbor) and face_solid)
            or isinstance(neighbor.block, IronBarsBlock)
            or gate
        )

    def _side(self, level: Level, pos: Pos, direction: Direction) -> bool:
        at = offset(pos, direction)
        neighbor = level.get_block_state(at)
        sturdy = neighbor.is_face_sturdy(level, at, direction.opposite)
        return self.connects_to(neighbor, sturdy, direction.opposite)

    def get_state_for_placement(self, ctx: Any) -> BlockState | None:
        level, pos = ctx.level, ctx.pos
        connected = {d: self._side(level, pos, d) for d in SIDES}
        top_pos = offset(pos, Direction.UP)
        state = ctx.requested.with_(WATERLOGGED, False)
        return self._update(state, level.get_block_state(top_pos), connected)

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction is Direction.DOWN:
            return state
        connected = {d: state.get(WALL_SIDES[d]) != "none" for d in SIDES}
        if direction is Direction.UP:  # topUpdate
            return self._update(state, neighbor, connected)
        sturdy = neighbor.is_face_sturdy(level, neighbor_pos, direction.opposite)
        connected[direction] = self.connects_to(neighbor, sturdy, direction.opposite)
        above = level.get_block_state(offset(pos, Direction.UP))
        return self._update(state, above, connected)  # sideUpdate

    def _update(
        self, state: BlockState, top: BlockState, connected: dict[Direction, bool]
    ) -> BlockState:
        """``updateShape(level, state, topPos, topNeighbour, north, east, south, west)``."""
        above = top.get_collision_shape().face_slice(Direction.DOWN)
        for direction, on in connected.items():
            side = ("tall" if _covers(above, _TEST_WALL[direction]) else "low") if on else "none"
            state = state.with_(WALL_SIDES[direction], side)
        return state.with_(UP, self._raise_post(state, top, above))

    def _raise_post(self, state: BlockState, top: BlockState, above: np.ndarray) -> bool:
        """``shouldRaisePost``."""
        if isinstance(top.block, WallBlock) and top.get(UP):
            return True
        north, south = (
            state.get(WALL_SIDES[Direction.NORTH]),
            state.get(WALL_SIDES[Direction.SOUTH]),
        )
        east, west = state.get(WALL_SIDES[Direction.EAST]), state.get(WALL_SIDES[Direction.WEST])
        north_none, south_none = north == "none", south == "none"
        east_none, west_none = east == "none", west == "none"
        corner = (
            (north_none and south_none and west_none and east_none)
            or north_none != south_none
            or west_none != east_none
        )
        if corner:
            return True
        high = (north == "tall" and south == "tall") or (east == "tall" and west == "tall")
        if high:
            return False
        return top.block.id in TAGS["wall_post_override"] or _covers(above, _TEST_POST)

    def rotated(self, state: BlockState, quarter_turns: int) -> BlockState:
        out = state
        for direction, prop in WALL_SIDES.items():
            turned = direction
            for _ in range(quarter_turns % 4):
                turned = turned.clockwise()
            out = out.with_(WALL_SIDES[turned], state.get(prop))
        return out

    def mirrored(self, state: BlockState, axis: str) -> BlockState:
        a, b = (
            (Direction.EAST, Direction.WEST) if axis == "x" else (Direction.NORTH, Direction.SOUTH)
        )
        pa, pb = WALL_SIDES[a], WALL_SIDES[b]
        return state.with_(pa, state.get(pb)).with_(pb, state.get(pa))
