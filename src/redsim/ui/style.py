"""How blocks look: simple colored boxes by functional category (no Minecraft textures).

Presentation only. Nothing here feeds back into the simulation. Models are defined in
pixel units (0-16) for a block attached to the floor and facing north, then rotated to the
block's actual orientation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from redsim.core.direction import Direction
from redsim.world.block import BlockState
from redsim.world.blocks.redstone_wire import PROPERTY_BY_DIRECTION
from redsim.world.properties import (
    ATTACH_FACE,
    BITES,
    DELAY,
    EXTENDED,
    FACING,
    HORIZONTAL_FACING,
    LIT,
    LOCKED,
    MODE_COMPARATOR,
    PISTON_TYPE,
    POWER,
    POWERED,
    SLAB_TYPE,
)

Color = tuple[float, float, float, float]


@dataclass(frozen=True)
class Box:
    lo: tuple[float, float, float]
    hi: tuple[float, float, float]
    color: Color
    translucent: bool = False


def rgb(r: float, g: float, b: float, a: float = 1.0) -> Color:
    return (r, g, b, a)


SOLID_COLORS: dict[str, Color] = {
    "minecraft:stone": rgb(0.50, 0.50, 0.50),
    "minecraft:smooth_stone": rgb(0.62, 0.62, 0.63),
    "minecraft:cobblestone": rgb(0.40, 0.40, 0.41),
    "minecraft:oak_planks": rgb(0.66, 0.52, 0.32),
    "minecraft:white_wool": rgb(0.92, 0.92, 0.92),
    "minecraft:white_concrete": rgb(0.82, 0.84, 0.84),
    "minecraft:obsidian": rgb(0.14, 0.09, 0.22),
    "minecraft:bedrock": rgb(0.22, 0.22, 0.22),
    "minecraft:glowstone": rgb(0.95, 0.82, 0.45),
    "minecraft:redstone_block": rgb(0.72, 0.07, 0.04),
}
TRANSLUCENT_COLORS: dict[str, Color] = {
    "minecraft:glass": rgb(0.70, 0.88, 1.00, 0.28),
    "minecraft:slime_block": rgb(0.45, 0.82, 0.35, 0.75),
    "minecraft:honey_block": rgb(0.98, 0.66, 0.15, 0.75),
}
COMPONENT_BASE = rgb(0.66, 0.66, 0.66)
TORCH_STICK = rgb(0.45, 0.32, 0.18)
LIT_RED = rgb(1.0, 0.18, 0.08)
UNLIT_RED = rgb(0.35, 0.05, 0.03)
LAMP_OFF = rgb(0.42, 0.26, 0.14)
LAMP_ON = rgb(1.0, 0.86, 0.48)
UNKNOWN = rgb(1.0, 0.0, 1.0)


def wire_color(power: int) -> Color:
    """``RedstoneWireBlock.COLORS`` (red/green/blue formulas of the game)."""
    p = power / 15.0
    red = p * 0.6 + (0.4 if p > 0.0 else 0.3)
    green = min(max(p * p * 0.7 - 0.5, 0.0), 1.0)
    blue = min(max(p * p * 0.6 - 0.7, 0.0), 1.0)
    return (red, green, blue, 1.0)


# ---------------------------------------------------------------- orientation helpers
_ROT_Y = {  # rotate a north-facing model to face the given horizontal direction
    Direction.NORTH: np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
    Direction.EAST: np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]]),
    Direction.SOUTH: np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]]),
    Direction.WEST: np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]]),
}
#: floor model → wall model: the floor side (attached block) moves to the south, so the wall
#: model faces north
_FLOOR_TO_WALL = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
#: floor model → ceiling model
_FLOOR_TO_CEILING = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]])
#: north-facing model → up / down facing (for six-way FACING blocks such as pistons)
_NORTH_TO_UP = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
_NORTH_TO_DOWN = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])


def transform(boxes: list[Box], matrix: np.ndarray) -> list[Box]:
    out = []
    for box in boxes:
        lo = np.array(box.lo) - 8.0
        hi = np.array(box.hi) - 8.0
        a = matrix @ lo + 8.0
        b = matrix @ hi + 8.0
        new_lo = tuple(float(v) for v in np.minimum(a, b))
        new_hi = tuple(float(v) for v in np.maximum(a, b))
        out.append(Box(new_lo, new_hi, box.color, box.translucent))  # type: ignore[arg-type]
    return out


def face_horizontally(boxes: list[Box], facing: Direction) -> list[Box]:
    return transform(boxes, _ROT_Y[facing])


def face_any(boxes: list[Box], facing: Direction) -> list[Box]:
    """Rotate a north-facing model to any of the six directions."""
    if facing is Direction.UP:
        return transform(boxes, _NORTH_TO_UP)
    if facing is Direction.DOWN:
        return transform(boxes, _NORTH_TO_DOWN)
    return face_horizontally(boxes, facing)


def attach(boxes: list[Box], face: str, facing: Direction) -> list[Box]:
    """Orient a floor model like a face-attached block (``face``/``facing`` properties)."""
    if face == "floor":
        return face_horizontally(boxes, facing)
    if face == "ceiling":
        return face_horizontally(transform(boxes, _FLOOR_TO_CEILING), facing.opposite)
    # Wall: ``facing`` points away from the wall; the wall model faces north.
    return face_horizontally(transform(boxes, _FLOOR_TO_WALL), facing)


def full(color: Color, translucent: bool = False) -> list[Box]:
    return [Box((0, 0, 0), (16, 16, 16), color, translucent)]


# ---------------------------------------------------------------- models
def block_boxes(state: BlockState) -> list[Box]:
    """Visual boxes (pixels) for a state; also used for picking. Air: no boxes."""
    block_id = state.block.id
    if state.is_air:
        return []
    if block_id in SOLID_COLORS:
        return full(SOLID_COLORS[block_id])
    if block_id in TRANSLUCENT_COLORS:
        return full(TRANSLUCENT_COLORS[block_id], translucent=True)
    if block_id == "minecraft:redstone_lamp":
        return full(LAMP_ON if state.get(LIT) else LAMP_OFF)
    if block_id == "minecraft:smooth_stone_slab":
        color = SOLID_COLORS["minecraft:smooth_stone"]
        kind = state.get(SLAB_TYPE)
        if kind == "double":
            return full(color)
        y0, y1 = (8, 16) if kind == "top" else (0, 8)
        return [Box((0, y0, 0), (16, y1, 16), color)]
    if block_id == "minecraft:redstone_wire":
        return _wire(state)
    if block_id == "minecraft:redstone_torch":
        return _torch(state.get(LIT))
    if block_id == "minecraft:redstone_wall_torch":
        return face_horizontally(_wall_torch(state.get(LIT)), state.get(HORIZONTAL_FACING))
    if block_id == "minecraft:repeater":
        return face_horizontally(_repeater(state), state.get(HORIZONTAL_FACING))
    if block_id == "minecraft:comparator":
        return face_horizontally(_comparator(state), state.get(HORIZONTAL_FACING))
    if block_id == "minecraft:lever":
        return attach(
            _lever(state.get(POWERED)), state.get(ATTACH_FACE), state.get(HORIZONTAL_FACING)
        )
    if block_id in ("minecraft:stone_button", "minecraft:oak_button"):
        color = rgb(0.55, 0.55, 0.55) if "stone" in block_id else rgb(0.66, 0.52, 0.32)
        depth = 1 if state.get(POWERED) else 2
        model = [Box((5, 0, 6), (11, depth, 10), color)]
        return attach(model, state.get(ATTACH_FACE), state.get(HORIZONTAL_FACING))
    if block_id in ("minecraft:piston", "minecraft:sticky_piston"):
        sticky = block_id == "minecraft:sticky_piston"
        return face_any(_piston_base(state.get(EXTENDED), sticky), state.get(FACING))
    if block_id == "minecraft:piston_head":
        return face_any(_piston_head(state.get(PISTON_TYPE) == "sticky"), state.get(FACING))
    if block_id == "minecraft:moving_piston":
        return []  # drawn from its block entity (see moving_boxes)
    if block_id == "minecraft:cake":
        bites = int(state.get(BITES))
        return [Box((1 + 2 * bites, 0, 1), (15, 8, 15), rgb(0.95, 0.90, 0.88))]
    return full(UNKNOWN)


def _wire(state: BlockState) -> list[Box]:
    color = wire_color(int(state.get(POWER)))
    boxes = [Box((5, 0, 5), (11, 1, 11), color)]
    arms = {
        Direction.NORTH: ((6, 0, 0), (10, 1, 5), (6, 0, 0), (10, 16, 0.6)),
        Direction.SOUTH: ((6, 0, 11), (10, 1, 16), (6, 0, 15.4), (10, 16, 16)),
        Direction.WEST: ((0, 0, 6), (5, 1, 10), (0, 0, 6), (0.6, 16, 10)),
        Direction.EAST: ((11, 0, 6), (16, 1, 10), (15.4, 0, 6), (16, 16, 10)),
    }
    for direction, prop in PROPERTY_BY_DIRECTION.items():
        side = state.get(prop)
        if side == "none":
            continue
        lo, hi, up_lo, up_hi = arms[direction]
        boxes.append(Box(lo, hi, color))
        if side == "up":
            boxes.append(Box(up_lo, up_hi, color))
    return boxes


def _torch(lit: bool) -> list[Box]:
    return [
        Box((7, 0, 7), (9, 8, 9), TORCH_STICK),
        Box((6.5, 8, 6.5), (9.5, 11, 9.5), LIT_RED if lit else UNLIT_RED),
    ]


def _wall_torch(lit: bool) -> list[Box]:
    # Facing north: attached block to the south.
    return [
        Box((7, 3, 11), (9, 11, 15), TORCH_STICK),
        Box((6.5, 10, 10), (9.5, 13, 13), LIT_RED if lit else UNLIT_RED),
    ]


def _repeater(state: BlockState) -> list[Box]:
    # FACING north: input north (z=0), output south (z=16). Torch positions follow the game
    # models (assets/minecraft/models/block/repeater_<n>tick.json, mirrored from their
    # facing=south frame): the fixed torch sits at the output end and the delay torch moves
    # from next to it (delay 1) towards the input (delay 4).
    powered = state.get(POWERED)
    torch = LIT_RED if powered else UNLIT_RED
    delay = int(state.get(DELAY))
    z = 8 - 2 * (delay - 1)
    boxes = [
        Box((0, 0, 0), (16, 2, 16), COMPONENT_BASE),
        Box((5, 2, 14), (11, 2.4, 16), rgb(0.85, 0.85, 0.85)),  # output edge marker
        Box((7, 2, 12), (9, 7, 14), torch),  # fixed (output) torch
    ]
    if state.get(LOCKED):
        boxes.append(Box((2, 2, z), (14, 4, z + 2), rgb(0.25, 0.25, 0.25)))
    else:
        boxes.append(Box((7, 2, z), (9, 7, z + 2), torch))
    return boxes


def _comparator(state: BlockState) -> list[Box]:
    powered = state.get(POWERED)
    subtract = state.get(MODE_COMPARATOR) == "subtract"
    back = LIT_RED if powered else UNLIT_RED
    return [
        Box((0, 0, 0), (16, 2, 16), COMPONENT_BASE),
        Box((5, 2, 14), (11, 2.4, 16), rgb(0.85, 0.85, 0.85)),
        Box((3, 2, 2), (5, 7, 4), back),
        Box((11, 2, 2), (13, 7, 4), back),
        Box((7, 2, 11), (9, 5, 13), LIT_RED if subtract else UNLIT_RED),
    ]


PISTON_BODY = rgb(0.47, 0.47, 0.45)
PISTON_WOOD = rgb(0.70, 0.56, 0.36)
PISTON_SLIME = rgb(0.47, 0.78, 0.35)


def _piston_base(extended: bool, sticky: bool) -> list[Box]:
    # Facing north: the push side is z = 0.
    if extended:
        return [Box((0, 0, 4), (16, 16, 16), PISTON_BODY)]
    face = PISTON_SLIME if sticky else PISTON_WOOD
    return [Box((0, 0, 4), (16, 16, 16), PISTON_BODY), Box((0, 0, 0), (16, 16, 4), face)]


def _piston_head(sticky: bool) -> list[Box]:
    face = PISTON_SLIME if sticky else PISTON_WOOD
    return [Box((0, 0, 0), (16, 16, 4), face), Box((6, 6, 4), (10, 10, 16), PISTON_WOOD)]


def moving_boxes(moved: BlockState, direction: Direction, extended_progress: float) -> list[Box]:
    """Boxes of a block being moved by a piston, shifted to its current progress."""
    shift = np.array(direction.step, dtype=float) * extended_progress * 16.0
    out = []
    for box in block_boxes(moved):
        lo = tuple(float(v) for v in np.array(box.lo) + shift)
        hi = tuple(float(v) for v in np.array(box.hi) + shift)
        out.append(Box(lo, hi, box.color, box.translucent))  # type: ignore[arg-type]
    return out


def _lever(powered: bool) -> list[Box]:
    base = rgb(0.42, 0.42, 0.42)
    handle = rgb(0.55, 0.40, 0.25)
    tip = LIT_RED if powered else rgb(0.30, 0.30, 0.30)
    z0 = 9 if powered else 5
    return [
        Box((5, 0, 4), (11, 3, 12), base),
        Box((7, 3, z0), (9, 9, z0 + 2), handle),
        Box((6.5, 9, z0 - 0.5), (9.5, 10.5, z0 + 2.5), tip),
    ]
