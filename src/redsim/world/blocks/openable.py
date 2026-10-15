"""Doors, trapdoors and fence gates: blocks that open by hand and by redstone. Ported
from ``DoorBlock``, ``TrapDoorBlock`` and ``FenceGateBlock`` (26.3); the copper ones
(``WeatheringCopperDoorBlock``, ``…TrapDoorBlock``) only add oxidation, a random tick, which
the simulator does not run. Sounds and game events (``BLOCK_OPEN``) have no effect on
blocks and are left out; explosions (wind charges) are not simulated. Water is not
simulated: ``waterlogged`` is kept for the state text and stays inert.

Shapes come from the game's shape code (``Shapes.rotateHorizontal`` / ``rotateAll`` with
the ``OctahedralGroup`` rotations below); they decide what the blocks support and that
they never conduct redstone (``isRedstoneConductor`` defaults to a full collision shape).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import numpy as np

from redsim.core.direction import Axis, Direction
from redsim.core.pos import Pos, offset
from redsim.world.block import Block, BlockState, PushReaction, UpdateFlags
from redsim.world.blocks.catalog_data import BLOCKS, TAGS
from redsim.world.properties import HORIZONTAL_FACING, OPEN, POWERED, WATERLOGGED, Property, boolean
from redsim.world.shape import EMPTY, N, Shape, box

if TYPE_CHECKING:
    from redsim.sim.level import Level

DOUBLE_BLOCK_HALF = Property("half", ("upper", "lower"))
HINGE = Property("hinge", ("left", "right"))
HALF = Property("half", ("top", "bottom"))
IN_WALL = boolean("in_wall")
#: ``catalog_data`` flag of ``Properties.replaceable()``.
REPLACEABLE = 32

_FROM_YAW = (Direction.SOUTH, Direction.WEST, Direction.NORTH, Direction.EAST)


def horizontal_direction(yaw: float) -> Direction:
    """``Entity.getDirection`` / ``BlockPlaceContext.getHorizontalDirection``."""
    return _FROM_YAW[math.floor(yaw / 90.0 + 0.5) & 3]


# ---------------------------------------------------------------- shapes
def rotated(shape: Shape, permutation: tuple[int, int, int], invert: tuple[bool, ...]) -> Shape:
    """``Shapes.rotate`` with an ``OctahedralGroup``: the axes permuted (``SymmetricGroup3``),
    then the flagged axes inverted (voxel ``i`` → ``15 - i``)."""
    cells = np.argwhere(shape.grid)
    moved = cells[:, list(permutation)]
    for axis, flip in enumerate(invert):
        if flip:
            moved[:, axis] = N - 1 - moved[:, axis]
    grid = np.zeros((N, N, N), dtype=np.bool_)
    grid[moved[:, 0], moved[:, 1], moved[:, 2]] = True
    return Shape(grid)


#: ``OctahedralGroup`` elements the block shapes use: (permutation, inverted x, y, z).
ROT_Y_90 = ((2, 1, 0), (True, False, False))  # BLOCK_ROT_Y_90 = ROT_90_Y_NEG (P321)
ROT_X_270 = ((0, 2, 1), (False, True, False))  # BLOCK_ROT_X_270 = ROT_90_X_POS (P132)
ROT_X_90 = ((0, 2, 1), (False, False, True))  # BLOCK_ROT_X_90 = ROT_90_X_NEG (P132)


def rotate_horizontal(north: Shape) -> dict[Direction, Shape]:
    """``Shapes.rotateHorizontal``: north as given, east/south/west turned clockwise."""
    out = {Direction.NORTH: north}
    shape = north
    for direction in (Direction.EAST, Direction.SOUTH, Direction.WEST):
        shape = rotated(shape, *ROT_Y_90)
        out[direction] = shape
    return out


def rotate_all(north: Shape) -> dict[Direction, Shape]:
    """``Shapes.rotateAll``: the horizontal turns, up = ``BLOCK_ROT_X_270``, down =
    ``BLOCK_ROT_X_90``."""
    out = rotate_horizontal(north)
    out[Direction.UP] = rotated(north, *ROT_X_270)
    out[Direction.DOWN] = rotated(north, *ROT_X_90)
    return out


def rotate_horizontal_axis(z_axis: Shape) -> dict[Axis, Shape]:
    """``Shapes.rotateHorizontalAxis``."""
    return {Axis.Z: z_axis, Axis.X: rotated(z_axis, *ROT_Y_90)}


def box_z(size_x: float, min_y: float, max_y: float, min_z: float, max_z: float) -> Shape:
    """``Block.boxZ(sizeX, minY, maxY, minZ, maxZ)``."""
    half = size_x / 2
    return box(8 - half, min_y, min_z, 8 + half, max_y, max_z)


def column(size_x: float, size_z: float, min_y: float, max_y: float) -> Shape:
    """``Block.column(sizeX, sizeZ, minY, maxY)`` (clipped to the block: parts above it,
    like a fence gate's 24-pixel collision, change none of the face checks)."""
    return box(
        8 - size_x / 2, min_y, 8 - size_z / 2, 8 + size_x / 2, min(max_y, 16), 8 + size_z / 2
    )


def _settings(block_id: str) -> dict[str, Any]:
    """The game's settings of a block (``catalog_data``)."""
    from redsim.world.blocks.catalog import _conductor

    kind, destroy, push, conductor, flags, color = BLOCKS[block_id]
    return {
        "destroy_speed": float(destroy),
        "push_reaction": PushReaction[push],
        "conductor": _conductor(conductor),
    }


def can_be_replaced(state: BlockState) -> bool:
    """``BlockState.canBeReplaced(context)`` for a player holding another block: air or a
    ``replaceable`` block (tall grass, …)."""
    if state.is_air:
        return True
    spec = BLOCKS.get(state.block.id)
    return spec is not None and bool(spec[4] & REPLACEABLE)


class _GameBlock(Block):
    """A block with its game settings; drawn without textures from its shape."""

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id, **_settings(block_id))
        color = BLOCKS[block_id][5]
        self.map_color = int(color) or 0x8F7748
        self.see_through = True  # noOcclusion: never hides its neighbors' faces

    def pixel_boxes(self, state: BlockState) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        from redsim.world.blocks.catalog import shape_boxes

        return shape_boxes(self.get_shape(state))  # type: ignore[return-value]


# ---------------------------------------------------------------- doors
_DOOR_SHAPES = rotate_horizontal(box_z(16, 0, 16, 13, 16))


class DoorBlock(_GameBlock):
    """``DoorBlock``: two halves that copy each other (``updateShape``), opened by hand
    (not iron: ``BlockSetType.canOpenByHand``) and by a signal at either half."""

    properties = (DOUBLE_BLOCK_HALF, HORIZONTAL_FACING, OPEN, HINGE, POWERED)

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id)
        self.can_open_by_hand = not block_id.startswith("minecraft:iron_")
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(OPEN, False)
            .with_(HINGE, "left")
            .with_(POWERED, False)
            .with_(DOUBLE_BLOCK_HALF, "lower")
        )

    def get_shape(self, state: BlockState) -> Shape:
        facing = state.get(HORIZONTAL_FACING)
        if state.get(OPEN):
            right = state.get(HINGE) == "right"
            facing = facing.counter_clockwise() if right else facing.clockwise()
        return _DOOR_SHAPES[facing]

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        half = state.get(DOUBLE_BLOCK_HALF)
        lower = half == "lower"
        if direction.axis is not Axis.Y or lower != (direction is Direction.UP):
            if lower and direction is Direction.DOWN and not self.can_survive(state, level, pos):
                return level.air
            return state
        if isinstance(neighbor.block, DoorBlock) and neighbor.get(DOUBLE_BLOCK_HALF) != half:
            return neighbor.with_(DOUBLE_BLOCK_HALF, half)
        return level.air

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        below_pos = offset(pos, Direction.DOWN)
        below = level.get_block_state(below_pos)
        if state.get(DOUBLE_BLOCK_HALF) == "lower":
            return below.is_face_sturdy(level, below_pos, Direction.UP)
        return below.block is self

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``getStateForPlacement``: needs room above; facing the way the player looks;
        open and powered when either half has a signal."""
        above = offset(pos, Direction.UP)
        if pos[1] >= level.max_y or not can_be_replaced(level.get_block_state(above)):
            return None
        powered = level.has_neighbor_signal(pos) or level.has_neighbor_signal(above)
        facing = horizontal_direction(request.yaw)
        return (
            self.default_state.with_(HORIZONTAL_FACING, facing)
            .with_(HINGE, self._hinge(request, level, pos, facing))
            .with_(POWERED, powered)
            .with_(OPEN, powered)
            .with_(DOUBLE_BLOCK_HALF, "lower")
        )

    def _hinge(self, request: Any, level: Level, pos: Pos, facing: Direction) -> str:
        """``getHinge``: full blocks and doors beside it, else the side of the click."""
        above = offset(pos, Direction.UP)
        left, right = facing.counter_clockwise(), facing.clockwise()

        def full(at: Pos) -> bool:
            return level.get_block_state(at).is_collision_shape_full_block()

        balance = (
            (-1 if full(offset(pos, left)) else 0)
            + (-1 if full(offset(above, left)) else 0)
            + (1 if full(offset(pos, right)) else 0)
            + (1 if full(offset(above, right)) else 0)
        )

        def lower_door(at: Pos) -> bool:
            state = level.get_block_state(at)
            return isinstance(state.block, DoorBlock) and state.get(DOUBLE_BLOCK_HALF) == "lower"

        door_left, door_right = lower_door(offset(pos, left)), lower_door(offset(pos, right))
        if (door_left and not door_right) or balance > 0:
            return "right"
        if (door_right and not door_left) or balance < 0:
            return "left"
        step_x, _, step_z = facing.step
        click_x, _, click_z = request.click_in(pos)
        left_side = (
            (step_x >= 0 or not click_z < 0.5)
            and (step_x <= 0 or not click_z > 0.5)
            and (step_z >= 0 or not click_x > 0.5)
            and (step_z <= 0 or not click_x < 0.5)
        )
        return "left" if left_side else "right"

    def set_placed_by(self, level: Level, pos: Pos, state: BlockState) -> None:
        """``setPlacedBy``: the upper half goes on top (``setBlockAndUpdate``)."""
        level.set_block_and_update(
            offset(pos, Direction.UP), state.with_(DOUBLE_BLOCK_HALF, "upper")
        )

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``useWithoutItem``: toggles ``open`` with flags 10 (the other half follows
        through its shape update)."""
        if not self.can_open_by_hand:
            return False
        level.set_block(pos, state.cycle(OPEN), UpdateFlags.CLIENTS | UpdateFlags.IMMEDIATE)
        return True

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        """``neighborChanged``: a signal at this half or the other opens it (flag 2)."""
        other = Direction.UP if state.get(DOUBLE_BLOCK_HALF) == "lower" else Direction.DOWN
        signal = level.has_neighbor_signal(pos) or level.has_neighbor_signal(offset(pos, other))
        if source is not self and signal != state.get(POWERED):
            updated = state.with_(POWERED, signal).with_(OPEN, signal)
            level.set_block(pos, updated, UpdateFlags.CLIENTS)

    def player_will_destroy(self, level: Level, pos: Pos, state: BlockState) -> BlockState:
        """``playerWillDestroy`` for the editor's creative player (no drops):
        ``DoublePlantBlock.preventDropFromBottomPart`` removes the lower half first
        (flags 35) when the upper half is broken."""
        if state.get(DOUBLE_BLOCK_HALF) == "upper":
            bottom_pos = offset(pos, Direction.DOWN)
            bottom = level.get_block_state(bottom_pos)
            if bottom.block is self and bottom.get(DOUBLE_BLOCK_HALF) == "lower":
                flags = UpdateFlags.ALL | UpdateFlags.SUPPRESS_DROPS
                level.set_block(bottom_pos, level.air, flags)
        return state

    def mirrored(self, state: BlockState, axis: str) -> BlockState:
        """``mirror``: the facing turned as for any facing block, then the hinge swapped."""
        facing = state.get(HORIZONTAL_FACING)
        flipped = Axis.X if axis == "x" else Axis.Z
        if facing.axis is flipped:
            state = state.with_(HORIZONTAL_FACING, facing.opposite)
        return state.cycle(HINGE)


# ---------------------------------------------------------------- trapdoors
_TRAPDOOR_SHAPES = rotate_all(box_z(16, 0, 16, 13, 16))


class TrapDoorBlock(_GameBlock):
    """``TrapDoorBlock``: opened by hand (not iron) and by a signal (flag 2)."""

    properties = (HORIZONTAL_FACING, OPEN, HALF, POWERED, WATERLOGGED)

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id)
        self.can_open_by_hand = not block_id.startswith("minecraft:iron_")
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(OPEN, False)
            .with_(HALF, "bottom")
            .with_(POWERED, False)
            .with_(WATERLOGGED, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        if state.get(OPEN):
            return _TRAPDOOR_SHAPES[state.get(HORIZONTAL_FACING)]
        return _TRAPDOOR_SHAPES[Direction.DOWN if state.get(HALF) == "top" else Direction.UP]

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``useWithoutItem`` → ``toggle``: ``open`` cycled with flag 2."""
        if not self.can_open_by_hand:
            return False
        level.set_block(pos, state.cycle(OPEN), UpdateFlags.CLIENTS)
        return True

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        signal = level.has_neighbor_signal(pos)
        if signal != state.get(POWERED):
            if state.get(OPEN) != signal:
                state = state.with_(OPEN, signal)
            level.set_block(pos, state.with_(POWERED, signal), UpdateFlags.CLIENTS)

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        """``getStateForPlacement``: against a side face it hangs on that face (top half
        when clicked above the middle); else it faces away from the player, on the top
        half when placed under a block."""
        state = self.default_state
        face = request.clicked_face
        if face.is_horizontal:
            top = request.click_in(pos)[1] > 0.5
            state = state.with_(HORIZONTAL_FACING, face).with_(HALF, "top" if top else "bottom")
        else:
            state = state.with_(
                HORIZONTAL_FACING, horizontal_direction(request.yaw).opposite
            ).with_(HALF, "bottom" if face is Direction.UP else "top")
        if level.has_neighbor_signal(pos):
            state = state.with_(OPEN, True).with_(POWERED, True)
        return state


# ---------------------------------------------------------------- fence gates
_GATE = rotate_horizontal_axis(column(16, 4, 0, 16))
_GATE_IN_WALL = {
    axis: Shape(shape.grid & ~box(0, 13, 0, 16, 16, 16).grid) for axis, shape in _GATE.items()
}
_GATE_COLLISION = rotate_horizontal_axis(column(16, 4, 0, 24))
_GATE_SUPPORT = rotate_horizontal_axis(column(16, 4, 5, 24))


def is_wall(state: BlockState) -> bool:
    return state.block.id in TAGS["walls"]


class FenceGateBlock(_GameBlock):
    """``FenceGateBlock``: opened by hand (towards the player) and by a signal (flag 2);
    lowered in walls (``in_wall``); no collision or support while open."""

    properties = (HORIZONTAL_FACING, OPEN, POWERED, IN_WALL)

    def __init__(self, block_id: str) -> None:
        super().__init__(block_id)
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH)
            .with_(OPEN, False)
            .with_(POWERED, False)
            .with_(IN_WALL, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        axis = state.get(HORIZONTAL_FACING).axis
        return (_GATE_IN_WALL if state.get(IN_WALL) else _GATE)[axis]

    def get_collision_shape(self, state: BlockState) -> Shape:
        return EMPTY if state.get(OPEN) else _GATE_COLLISION[state.get(HORIZONTAL_FACING).axis]

    def get_block_support_shape(self, state: BlockState) -> Shape:
        return EMPTY if state.get(OPEN) else _GATE_SUPPORT[state.get(HORIZONTAL_FACING).axis]

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if state.get(HORIZONTAL_FACING).clockwise().axis is not direction.axis:
            return state
        across = level.get_block_state(offset(pos, direction.opposite))
        return state.with_(IN_WALL, is_wall(neighbor) or is_wall(across))

    def player_placement(self, request: Any, level: Level, pos: Pos) -> BlockState | None:
        is_open = level.has_neighbor_signal(pos)
        facing = horizontal_direction(request.yaw)
        sides = (
            (Direction.WEST, Direction.EAST)
            if facing.axis is Axis.Z
            else (Direction.NORTH, Direction.SOUTH)
        )
        in_wall = any(is_wall(level.get_block_state(offset(pos, d))) for d in sides)
        return (
            self.default_state.with_(HORIZONTAL_FACING, facing)
            .with_(OPEN, is_open)
            .with_(POWERED, is_open)
            .with_(IN_WALL, in_wall)
        )

    def use_without_item(self, state: BlockState, level: Level, pos: Pos) -> bool:
        """``useWithoutItem``: closes, or opens away from the player (it turns to face
        the player's way if it faced them); flags 10."""
        flags = UpdateFlags.CLIENTS | UpdateFlags.IMMEDIATE
        if state.get(OPEN):
            level.set_block(pos, state.with_(OPEN, False), flags)
            return True
        player = horizontal_direction(level.player_yaw)
        if state.get(HORIZONTAL_FACING) is player.opposite:
            state = state.with_(HORIZONTAL_FACING, player)
        level.set_block(pos, state.with_(OPEN, True), flags)
        return True

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        powered = level.has_neighbor_signal(pos)
        if state.get(POWERED) != powered:
            updated = state.with_(POWERED, powered).with_(OPEN, powered)
            level.set_block(pos, updated, UpdateFlags.CLIENTS)


def connects_to_direction(state: BlockState, direction: Direction) -> bool:
    """``FenceGateBlock.connectsToDirection``."""
    return state.get(HORIZONTAL_FACING).axis is direction.clockwise().axis


__all__ = [
    "DOUBLE_BLOCK_HALF",
    "HALF",
    "HINGE",
    "IN_WALL",
    "DoorBlock",
    "FenceGateBlock",
    "TrapDoorBlock",
]
