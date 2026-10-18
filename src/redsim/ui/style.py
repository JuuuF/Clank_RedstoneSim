"""How blocks look: simple colored boxes by functional category (no Minecraft textures).

Presentation only. Nothing here feeds back into the simulation. Models are defined in
pixel units (0-16) for a block attached to the floor and facing north, then rotated to the
block's actual orientation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from redsim.core.direction import Direction
from redsim.world.block import BlockState
from redsim.world.blocks.composter import LEVEL as COMPOSTER_LEVEL
from redsim.world.blocks.redstone_wire import PROPERTY_BY_DIRECTION
from redsim.world.blocks.sign import ROTATION, SignBlock, WallSignBlock
from redsim.world.properties import (
    ATTACH_FACE,
    BITES,
    DELAY,
    ENABLED,
    EXTENDED,
    FACING,
    FACING_HOPPER,
    HAS_BOOK,
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
    "minecraft:dirt": rgb(0.53, 0.38, 0.26),
    "minecraft:grass_block": rgb(0.40, 0.60, 0.27),
    "minecraft:note_block": rgb(0.45, 0.30, 0.22),
    "minecraft:dispenser": rgb(0.48, 0.48, 0.48),
    "minecraft:dropper": rgb(0.46, 0.46, 0.46),
}
TRANSLUCENT_COLORS: dict[str, Color] = {
    "minecraft:glass": rgb(0.70, 0.88, 1.00, 0.28),
    "minecraft:barrier": rgb(0.90, 0.20, 0.20, 0.15),
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
HOPPER_METAL = rgb(0.30, 0.30, 0.33)
HOPPER_INSIDE = rgb(0.16, 0.16, 0.18)
#: ``HopperBlock`` spouts by facing (the collision shape, ``hopper.py``).
HOPPER_SPOUTS = {
    Direction.DOWN: ((6, 0, 6), (10, 4, 10)),
    Direction.NORTH: ((6, 4, 0), (10, 8, 4)),
    Direction.SOUTH: ((6, 4, 12), (10, 8, 16)),
    Direction.WEST: ((0, 4, 6), (4, 8, 10)),
    Direction.EAST: ((12, 4, 6), (16, 8, 10)),
}


def _hopper(state: BlockState) -> list[Box]:
    """Bowl, funnel and spout; a locked hopper (``enabled=false``) gets a red bowl floor."""
    floor = HOPPER_INSIDE if state.get(ENABLED) else UNLIT_RED
    low, high = HOPPER_SPOUTS[state.get(FACING_HOPPER)]
    return [
        Box((0, 11, 0), (16, 16, 2), HOPPER_METAL),
        Box((0, 11, 14), (16, 16, 16), HOPPER_METAL),
        Box((0, 11, 2), (2, 16, 14), HOPPER_METAL),
        Box((14, 11, 2), (16, 16, 14), HOPPER_METAL),
        Box((4, 4, 4), (12, 10, 12), HOPPER_METAL),
        Box(low, high, HOPPER_METAL),
        Box((0, 10, 0), (16, 11, 16), floor),
    ]


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
    if block_id.endswith("_button"):
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
    if block_id == "minecraft:barrel":
        return face_any(_barrel(), state.get(FACING))
    if block_id in RAIL_METAL:
        return _rail(block_id, state)
    if block_id == "minecraft:hopper":
        return _hopper(state)
    if block_id == "minecraft:target":
        center = LIT_RED if state.get(POWER) else rgb(0.78, 0.16, 0.14)
        body = [Box((0, 0, 0), (16, 16, 16), rgb(0.93, 0.88, 0.82))]
        dots = [
            Box((5, 5, -0.2), (11, 11, 0), center), Box((5, 5, 16), (11, 11, 16.2), center),
            Box((-0.2, 5, 5), (0, 11, 11), center), Box((16, 5, 5), (16.2, 11, 11), center),
            Box((5, 16, 5), (11, 16.2, 11), center), Box((5, -0.2, 5), (11, 0, 11), center),
        ]  # fmt: skip
        return body + dots
    if block_id == "minecraft:observer":
        return face_any(_observer(state.get(POWERED)), state.get(FACING))
    if block_id == "minecraft:lectern":
        model = _lectern(state.get(HAS_BOOK), state.get(POWERED))
        return face_horizontally(model, state.get(HORIZONTAL_FACING))
    if isinstance(state.block, SignBlock):
        return _sign(state)
    if block_id == "minecraft:composter":
        return _composter(int(state.get(COMPOSTER_LEVEL)))
    if block_id.endswith("pressure_plate"):
        return _pressure_plate(state)
    if block_id in ("minecraft:chest", "minecraft:trapped_chest"):
        return _chest(state)
    if block_id.endswith("copper_bulb"):
        return full(LAMP_ON if state.get(LIT) else rgb(0.62, 0.42, 0.30))
    own = getattr(state.block, "pixel_boxes", None)
    if own is not None:  # the game's ordinary blocks: their shape in their map color
        packed = int(getattr(state.block, "map_color", 0) or 0x9A9A9A)
        see_through = bool(getattr(state.block, "see_through", False))
        shade = rgb(((packed >> 16) & 255) / 255, ((packed >> 8) & 255) / 255, (packed & 255) / 255)
        if see_through:
            shade = (shade[0], shade[1], shade[2], 0.45)
        return [Box(tuple(lo), tuple(hi), shade, see_through) for lo, hi in own(state)]
    return full(UNKNOWN)


#: Pressure plate colors by material (stone, the weighted gold and iron plates, wood).
PLATE_COLORS = {
    "minecraft:stone_pressure_plate": rgb(0.55, 0.55, 0.55),
    "minecraft:polished_blackstone_pressure_plate": rgb(0.22, 0.20, 0.24),
    "minecraft:light_weighted_pressure_plate": rgb(0.96, 0.80, 0.25),
    "minecraft:heavy_weighted_pressure_plate": rgb(0.78, 0.78, 0.78),
}
PLATE_WOOD = rgb(0.66, 0.52, 0.32)
CHEST_WOOD = rgb(0.62, 0.42, 0.18)
CHEST_LATCH = rgb(0.78, 0.78, 0.72)


def _pressure_plate(state: BlockState) -> list[Box]:
    """``BasePressurePlateBlock``: a 14×14 plate, 1 pixel high, half a pixel pressed."""
    pressed = bool(state.get(POWERED)) if state.has(POWERED) else int(state.get(POWER)) > 0
    color = PLATE_COLORS.get(state.block.id, PLATE_WOOD)
    return [Box((1, 0, 1), (15, 0.5 if pressed else 1, 15), color)]


def _chest(state: BlockState) -> list[Box]:
    """``ChestBlock``'s 14×14×14 box; the halves of a double chest reach each other."""
    from redsim.world.blocks.chest import CHEST_TYPE, connected_direction

    lo, hi = [1.0, 0.0, 1.0], [15.0, 14.0, 15.0]
    if state.get(CHEST_TYPE) != "single":
        joined = connected_direction(state)
        axis = 0 if joined.axis.name.lower() == "x" else 2
        if joined.step[axis] > 0:
            hi[axis] = 16.0
        else:
            lo[axis] = 0.0
    facing: Direction = state.get(HORIZONTAL_FACING)
    latch = face_horizontally([Box((7, 7, 0), (9, 11, 1), CHEST_LATCH)], facing)
    return [Box(tuple(lo), tuple(hi), CHEST_WOOD), *latch]  # type: ignore[arg-type]


COMPOSTER_WOOD = rgb(0.55, 0.40, 0.24)
COMPOST = rgb(0.33, 0.25, 0.14)


def _composter(level: int) -> list[Box]:
    """A hollow box (floor and four walls), the compost inside at its level."""
    model = [
        Box((0, 0, 0), (16, 2, 16), COMPOSTER_WOOD),
        Box((0, 2, 0), (2, 16, 16), COMPOSTER_WOOD),
        Box((14, 2, 0), (16, 16, 16), COMPOSTER_WOOD),
        Box((2, 2, 0), (14, 16, 2), COMPOSTER_WOOD),
        Box((2, 2, 14), (14, 16, 16), COMPOSTER_WOOD),
    ]
    if level:
        model.append(Box((2, 2, 2), (14, min(15, 1 + 2 * level), 14), COMPOST))
    return model


SIGN_WOOD = rgb(0.62, 0.47, 0.30)
_SIGN_FACINGS = (Direction.SOUTH, Direction.WEST, Direction.NORTH, Direction.EAST)


def _sign(state: BlockState) -> list[Box]:
    """A sign's board (and post), as in the game's sign models; a standing sign turns to
    the nearest quarter (its text is drawn at the exact angle, ``ui/sign_text.py``)."""
    if isinstance(state.block, WallSignBlock):  # north-facing: against the south wall
        board = [Box((0, 4.33, 14.33), (16, 12.33, 15.67), SIGN_WOOD)]
        return face_horizontally(board, state.get(HORIZONTAL_FACING))
    model = [
        Box((7.33, 0, 7.33), (8.67, 9.33, 8.67), SIGN_WOOD),
        Box((0, 9.33, 7.33), (16, 17.33, 8.67), SIGN_WOOD),
    ]
    facing = _SIGN_FACINGS[round(state.get(ROTATION) / 4) % 4]
    return face_horizontally(model, facing)


BARREL_WOOD = rgb(0.52, 0.38, 0.22)
LECTERN_WOOD = rgb(0.62, 0.47, 0.30)


RAIL_METAL = {
    "minecraft:rail": rgb(0.62, 0.62, 0.64),
    "minecraft:powered_rail": rgb(0.86, 0.70, 0.22),
    "minecraft:activator_rail": rgb(0.40, 0.36, 0.36),
    "minecraft:detector_rail": rgb(0.55, 0.45, 0.40),
}


def _rail(block_id: str, state: BlockState) -> list[Box]:
    """Ties and two rails; slopes as four steps; curves as an L (presentation only)."""
    shape = next(state.get(p) for p in state.block.properties if p.name == "shape")
    powered = any(p.name == "powered" for p in state.block.properties) and state.get(POWERED)
    metal = LIT_RED if powered else RAIL_METAL[block_id]
    ties = rgb(0.45, 0.33, 0.20)
    # A north-south straight rail, then turned.
    straight = [Box((1, 0, z), (15, 1, z + 2), ties) for z in (1, 5, 9, 13)] + [
        Box((3, 1, 0), (5, 2, 16), metal),
        Box((11, 1, 0), (13, 2, 16), metal),
    ]
    if shape in ("north_south", "east_west"):
        turn = Direction.EAST if shape == "east_west" else Direction.NORTH
        return face_horizontally(straight, turn)
    if shape.startswith("ascending_"):
        rises = Direction[shape.split("_")[1].upper()]
        steps = [Box((1, 2 * i, 4 * i), (15, 2 * i + 1, 4 * i + 4), ties) for i in range(4)]
        steps += [Box((3, 2 * i + 1, 4 * i), (5, 2 * i + 2, 4 * i + 4), metal) for i in range(4)]
        steps += [Box((11, 2 * i + 1, 4 * i), (13, 2 * i + 2, 4 * i + 4), metal) for i in range(4)]
        return face_horizontally(steps, rises.opposite)  # model rises towards +z (south)
    return _curved_rail(shape, metal, ties)


def _curved_rail(shape: str, metal: Color, ties: Color) -> list[Box]:
    """A curve joining two sides (``south_east``: south and east): both rails are quarter
    circles around the corner between those sides, radius 4 and 12, so they meet the
    straight rails (x = 3-5 and 11-13) at the edges; ties run radially."""
    cx = 16.0 if "east" in shape else 0.0
    cz = 16.0 if "south" in shape else 0.0
    sx = -1.0 if cx else 1.0  # from the corner into the block
    sz = -1.0 if cz else 1.0

    def at(radius: float, angle: float) -> tuple[float, float]:
        return cx + sx * radius * math.cos(angle), cz + sz * radius * math.sin(angle)

    boxes = []
    for degrees in (12, 45, 78):  # ties: small squares along three radii
        angle = math.radians(degrees)
        for step in range(2, 15, 2):
            x, z = at(step + 0.5, angle)
            boxes.append(Box((x - 1.1, 0, z - 1.1), (x + 1.1, 1, z + 1.1), ties))
    for rail_radius, count in ((4.0, 7), (12.0, 16)):  # the rails
        for i in range(count + 1):
            x, z = at(rail_radius, math.radians(90 * i / count))
            boxes.append(Box((x - 1, 1, z - 1), (x + 1, 2, z + 1), metal))
    return boxes


def _observer(powered: bool) -> list[Box]:
    """Facing north: the watching face (z = 0) is dark; arrows on the top, bottom and sides
    point to the back (the signal's way); the output dot is on the back."""
    body = rgb(0.42, 0.42, 0.42)
    mark = rgb(0.74, 0.74, 0.76)
    boxes = [
        Box((0, 0, 1), (16, 16, 15), body),
        Box((0, 0, 0), (16, 16, 1), rgb(0.22, 0.22, 0.24)),  # the face
        Box((0, 0, 15), (16, 16, 16), rgb(0.33, 0.33, 0.33)),
        Box((6, 6, 16), (10, 10, 16.4), LIT_RED if powered else UNLIT_RED),  # output dot
    ]
    # An arrow (shaft and stepped head) on every side face, pointing to the back (+z).
    arrow = [
        ((7, 9), (2, 9)),  # shaft
        ((3, 13), (9, 10)),  # head, narrowing towards the back
        ((4, 12), (10, 11)),
        ((5, 11), (11, 12)),
        ((6, 10), (12, 13)),
        ((7, 9), (13, 14)),
    ]
    for (a0, a1), (z0, z1) in arrow:
        boxes += [
            Box((a0, 16, z0), (a1, 16.3, z1), mark),  # top
            Box((a0, -0.3, z0), (a1, 0, z1), mark),  # bottom
            Box((16, a0, z0), (16.3, a1, z1), mark),  # east side
            Box((-0.3, a0, z0), (0, a1, z1), mark),  # west side
        ]
    return boxes


def _barrel() -> list[Box]:
    # Facing north: the lid (darker) is the z = 0 side.
    return [
        Box((0, 0, 1), (16, 16, 16), BARREL_WOOD),
        Box((0, 0, 0), (16, 16, 1), rgb(0.34, 0.24, 0.13)),
    ]


def _lectern(has_book: bool, powered: bool) -> list[Box]:
    boxes = [
        Box((0, 0, 0), (16, 2, 16), LECTERN_WOOD),
        Box((4, 2, 4), (12, 12, 12), LECTERN_WOOD),
        Box((0, 12, 2), (16, 15, 14), rgb(0.56, 0.42, 0.26)),
    ]
    if has_book:
        boxes.append(Box((2, 15, 4), (14, 16, 12), rgb(0.93, 0.91, 0.84)))
    if powered:  # the 2-tick page-turn pulse
        boxes.append(Box((6, 2, 0), (10, 3, 4), LIT_RED))
    return boxes


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
