"""Rotating block states and positions (``Rotation.CLOCKWISE_90`` and its powers).

Mirrors the ``rotate`` overrides of the in-scope blocks: every horizontal ``facing`` turns
with the rotation (``HorizontalDirectionalBlock``/``DirectionalBlock``/face-attached blocks;
up/down stay), and redstone wire permutes its side properties
(``RedstoneWireBlock.rotate``). Positions rotate as ``BlockPos.rotate``: ``(x, z) → (-z, x)``.
"""

from __future__ import annotations

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.world.block import BlockState
from redsim.world.blocks.redstone_wire import PROPERTY_BY_DIRECTION


def rotate_direction(direction: Direction, quarter_turns: int) -> Direction:
    if not direction.is_horizontal:
        return direction
    for _ in range(quarter_turns % 4):
        direction = direction.clockwise()
    return direction


def rotate_state(state: BlockState, quarter_turns: int) -> BlockState:
    turns = quarter_turns % 4
    if turns == 0:
        return state
    from redsim.world.blocks.rail import ROTATE_CW, BaseRailBlock

    if isinstance(state.block, BaseRailBlock):  # BaseRailBlock.rotate tables
        prop = state.block.shape_property
        shape = state.get(prop)
        for _ in range(turns):
            shape = ROTATE_CW[shape]
        return state.with_(prop, shape)
    if state.block.id == "minecraft:redstone_wire":
        sides = {d: state.get(p) for d, p in PROPERTY_BY_DIRECTION.items()}
        for direction, value in sides.items():
            state = state.with_(PROPERTY_BY_DIRECTION[rotate_direction(direction, turns)], value)
        return state
    for prop in state.block.properties:
        value = state.get(prop)
        if isinstance(value, Direction):
            state = state.with_(prop, rotate_direction(value, turns))
    return state


def mirror_state(state: BlockState, axis: str) -> BlockState:
    """``BlockState.mirror``. ``axis="x"`` is ``Mirror.FRONT_BACK`` (east and west swap),
    ``axis="z"`` is ``Mirror.LEFT_RIGHT`` (north and south swap).

    Every in-scope block with a facing mirrors as ``rotate(mirror.getRotation(facing))``
    (``HorizontalDirectionalBlock``, ``BarrelBlock``, ``LecternBlock``, pistons, wall torch:
    the facing turns around only if it lies on the mirrored axis); redstone wire swaps its
    two side properties on that axis (``RedstoneWireBlock.mirror`` L465)."""
    flipped = Direction.EAST if axis == "x" else Direction.SOUTH
    from redsim.world.blocks.rail import MIRROR, BaseRailBlock

    if isinstance(state.block, BaseRailBlock):  # BaseRailBlock.mirror tables
        prop = state.block.shape_property
        return state.with_(prop, MIRROR[axis].get(state.get(prop), state.get(prop)))
    if state.block.id == "minecraft:redstone_wire":
        a, b = PROPERTY_BY_DIRECTION[flipped], PROPERTY_BY_DIRECTION[flipped.opposite]
        return state.with_(a, state.get(b)).with_(b, state.get(a))
    for prop in state.block.properties:
        value = state.get(prop)
        if isinstance(value, Direction) and value.axis is flipped.axis:
            state = state.with_(prop, value.opposite)
    return state


def rotate_offset(offset: Pos, quarter_turns: int) -> Pos:
    x, y, z = offset
    for _ in range(quarter_turns % 4):
        x, z = -z, x
    return (x, y, z)


def default_pivot2(low: Pos, high: Pos) -> tuple[int, int]:
    """Twice the (x, z) point a box turns around: its center, so cells land on cells.

    A quarter turn maps cell centers onto cell centers only if the doubled pivot
    coordinates have the same parity. When exactly one side length is odd, the center is
    moved half a block (x down or z up). Callers keep the pivot for further turns of the
    same selection, so turning back (or four times) returns exactly to the start."""
    x2 = low[0] + high[0] + 1
    z2 = low[2] + high[2] + 1
    if x2 % 2 != z2 % 2:
        if x2 % 2:
            x2 -= 1
        else:
            z2 += 1
    return x2, z2


def rotate_about(pos: Pos, pivot2: tuple[int, int], quarter_turns: int) -> Pos:
    """Turn a block position clockwise (seen from above) around a doubled pivot."""
    dx = 2 * pos[0] + 1 - pivot2[0]
    dz = 2 * pos[2] + 1 - pivot2[1]
    for _ in range(quarter_turns % 4):
        dx, dz = -dz, dx
    return ((pivot2[0] + dx - 1) // 2, pos[1], (pivot2[1] + dz - 1) // 2)


def rotated_box(
    low: Pos, high: Pos, quarter_turns: int, pivot2: tuple[int, int] | None = None
) -> tuple[Pos, Pos]:
    """The box a region occupies after turning around ``pivot2`` (default: its center)."""
    pivot = pivot2 if pivot2 is not None else default_pivot2(low, high)
    a = rotate_about(low, pivot, quarter_turns)
    b = rotate_about(high, pivot, quarter_turns)
    return (
        (min(a[0], b[0]), low[1], min(a[2], b[2])),
        (max(a[0], b[0]), high[1], max(a[2], b[2])),
    )


#: Property values that swap when a block is turned upside down (by serialized text).
_UPSIDE_DOWN = {"top": "bottom", "bottom": "top", "floor": "ceiling", "ceiling": "floor"}


def upside_down(state: BlockState) -> BlockState:
    """The block turned upside down, as far as its properties allow (editor only, for
    choosing variants before placing): slab and half ``top``/``bottom``, attach face
    ``floor``/``ceiling``, and a facing ``up``/``down``. Values the block does not have
    stay (a hopper cannot face up)."""
    for prop in state.block.properties:
        value = state.get(prop)
        if isinstance(value, Direction):
            if value.axis is Direction.UP.axis and value.opposite in prop.values:
                state = state.with_(prop, value.opposite)
            continue
        text = _UPSIDE_DOWN.get(prop.serialize(value))
        if text is not None and text in {prop.serialize(v) for v in prop.values}:
            state = state.with_(prop, prop.parse(text))
    return state
