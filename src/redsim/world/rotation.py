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


def rotate_offset(offset: Pos, quarter_turns: int) -> Pos:
    x, y, z = offset
    for _ in range(quarter_turns % 4):
        x, z = -z, x
    return (x, y, z)
