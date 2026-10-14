"""Signs (standing and on walls, every wood) and their text.

Sources (relative to ``data/minecraft_src/client-src/net/minecraft/world/level/``):

* ``block/SignBlock.java``: shape ``column(8, 0, 16)``, the ``SignBlockEntity``.
* ``block/StandingSignBlock.java``: default ``rotation=8``; ``canSurvive`` (the block below
  ``isSolid``), ``updateShape`` (air when the support below is gone),
  ``getStateForPlacement`` (``RotationSegment.convertToSegment(yRot + 180)``).
* ``block/WallSignBlock.java``: ``facing`` (default north); shape ``boxZ(16, 4.5, 12.5,
  14, 16)`` turned to the facing; ``canSurvive`` (the block behind ``isSolid``),
  ``updateShape``; placement tries the nearest looking directions (horizontal ones).
* ``block/Blocks.java``: ``forceSolidOn`` (signs count as solid), ``noCollision``,
  strength 1.
* ``block/entity/SignBlockEntity.java``: front and back text (4 lines each), color, glow,
  wax. ``updateSignText`` calls ``setChanged`` (comparators around re-read).

Not modeled: water (``waterlogged`` is kept but schedules no fluid ticks), the sign
block entity's ticker (it only forgets which player may edit; no effect on the world).
Signs have a block entity, so pistons cannot move them (``PistonBaseBlock.isPushable``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos, below, offset
from redsim.world.block import Block, BlockState, PlacementContext
from redsim.world.block_entity import BlockEntity, register_block_entity
from redsim.world.properties import HORIZONTAL_FACING, boolean, integer
from redsim.world.shape import Shape, box, column

if TYPE_CHECKING:
    from redsim.sim.level import Level

ROTATION = integer("rotation", 0, 15)
WATERLOGGED = boolean("waterlogged")
WOODS = (
    "oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "pale_oak", "mangrove",
    "cherry", "bamboo", "crimson", "warped",
)  # fmt: skip
LINES = 4
_STANDING_SHAPE = column(8, 0, 16)
#: ``Shapes.rotateHorizontal(boxZ(16, 4.5, 12.5, 14, 16))``: the board against the wall
#: behind the sign (``facing`` points away from the wall). Voxel shapes are whole pixels,
#: so 4.5–12.5 is widened to 4–13 (signs have no collision; this is the outline only).
_WALL_SHAPES = {
    Direction.NORTH: box(0, 4, 14, 16, 13, 16),
    Direction.SOUTH: box(0, 4, 0, 16, 13, 2),
    Direction.WEST: box(14, 4, 0, 16, 13, 16),
    Direction.EAST: box(0, 4, 0, 2, 13, 16),
}


def rotation_segment(degrees: float) -> int:
    """``RotationSegment.convertToSegment(float)``: ``Math.round(deg * 16 / 360) & 15``."""
    import math

    return math.floor(degrees * 16 / 360 + 0.5) & 15


def _plain(message: Any) -> str:
    """A saved text component as plain text (a string, JSON text, or a compound)."""
    import json

    if isinstance(message, str):
        try:
            message = json.loads(message)
        except ValueError:
            return message
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        return "".join(_plain(part) for part in message)
    if isinstance(message, dict):
        text = str(message.get("text", message.get("translate", "")))
        return text + "".join(_plain(part) for part in message.get("extra", []))
    return "" if message is None else str(message)


class SignBlockEntity(BlockEntity):
    """Front and back text of a sign. The saved data is kept as read, so a sign written
    back to a world keeps its colors and formatting unless its text was edited."""

    type_id = "sign"
    valid_blocks = frozenset(
        {f"minecraft:{wood}_sign" for wood in WOODS}
        | {f"minecraft:{wood}_wall_sign" for wood in WOODS}
    )

    def __init__(self, pos: Pos, state: BlockState) -> None:
        super().__init__(pos, state)
        self.front: list[str] = [""] * LINES
        self.back: list[str] = [""] * LINES
        self.data: dict[str, Any] = {}  # the saved data, as read (colors, glow, wax)

    def lines(self, side: str) -> list[str]:
        return self.front if side == "front" else self.back

    def set_text(self, level: Level, side: str, lines: list[str]) -> None:
        """``SignBlockEntity.updateSignText``: new lines, then ``setChanged``."""
        from redsim.world.blocks.container import set_changed

        text = [*(str(line) for line in lines[:LINES]), *[""] * (LINES - len(lines))]
        if side == "front":
            self.front = text
        else:
            self.back = text
        set_changed(self, level)

    def to_json(self) -> dict[str, Any]:
        """Like the game's NBT: ``front_text``/``back_text`` with ``messages`` (text
        components; edited lines as plain strings) and ``is_waxed``."""
        out = dict(self.data)
        for key, lines in (("front_text", self.front), ("back_text", self.back)):
            side = dict(out.get(key) or {})
            saved = list(side.get("messages") or [])
            if [_plain(m) for m in saved] != lines:
                side["messages"] = list(lines)
            side.setdefault("color", "black")
            side.setdefault("has_glowing_text", False)
            out[key] = side
        out.setdefault("is_waxed", False)
        return out

    def load_json(self, data: dict[str, Any]) -> None:
        self.data = dict(data)
        for key, attr in (("front_text", "front"), ("back_text", "back")):
            messages = list((data.get(key) or {}).get("messages") or [])
            if key == "front_text" and not messages:  # saves before 1.20: Text1…Text4
                messages = [data.get(f"Text{i}", "") for i in range(1, LINES + 1)]
            lines = [_plain(m) for m in messages[:LINES]]
            setattr(self, attr, lines + [""] * (LINES - len(lines)))

    def describe(self) -> str:
        shown = " / ".join(line for line in self.front if line)
        return f"sign: {shown}" if shown else "sign: no text"


class SignBlock(Block):
    """``SignBlock``: shared parts of standing and wall signs."""

    has_block_entity = True
    force_solid = True
    wood: str = "oak"

    def __init__(self, block_id: str, wood: str) -> None:
        super().__init__(block_id, has_collision=False, destroy_speed=1.0)
        self.wood = wood

    def new_block_entity(self, pos: Pos, state: BlockState) -> BlockEntity | None:
        return SignBlockEntity(pos, state)


class StandingSignBlock(SignBlock):
    properties = (ROTATION, WATERLOGGED)

    def __init__(self, wood: str) -> None:
        super().__init__(f"minecraft:{wood}_sign", wood)
        self.register_default_state(self.default_state.with_(ROTATION, 8).with_(WATERLOGGED, False))

    def get_shape(self, state: BlockState) -> Shape:
        return _STANDING_SHAPE

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        return level.get_block_state(below(pos)).is_solid()

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction is Direction.DOWN and not self.can_survive(state, level, pos):
            return level.air
        return state

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        return self.default_state.with_(ROTATION, ctx.requested.get(ROTATION))


class WallSignBlock(SignBlock):
    properties = (HORIZONTAL_FACING, WATERLOGGED)

    def __init__(self, wood: str) -> None:
        super().__init__(f"minecraft:{wood}_wall_sign", wood)
        self.register_default_state(
            self.default_state.with_(HORIZONTAL_FACING, Direction.NORTH).with_(WATERLOGGED, False)
        )

    def get_shape(self, state: BlockState) -> Shape:
        return _WALL_SHAPES[state.get(HORIZONTAL_FACING)]

    def can_survive(self, state: BlockState, level: Level, pos: Pos) -> bool:
        behind = offset(pos, state.get(HORIZONTAL_FACING).opposite)
        return level.get_block_state(behind).is_solid()

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        if direction.opposite is state.get(HORIZONTAL_FACING) and not self.can_survive(
            state, level, pos
        ):
            return level.air
        return state

    def get_state_for_placement(self, ctx: PlacementContext) -> BlockState | None:
        state = self.default_state.with_(HORIZONTAL_FACING, ctx.requested.get(HORIZONTAL_FACING))
        return state if state.can_survive(ctx.level, ctx.pos) else None


def adopt_signs(level: Level, texts: dict[str, list[str]]) -> None:
    """Give sign blocks without a block entity one (documents saved while signs were
    foreign blocks), with their front text from ``texts`` ("x,y,z" → lines, the old
    ``extra["signs"]``); no updates, like loading a chunk."""
    for pos, state in level.blocks.items():
        if not isinstance(state.block, SignBlock) or pos in level.block_entities:
            continue
        entity = SignBlockEntity(pos, state)
        lines = [str(line) for line in texts.get(f"{pos[0]},{pos[1]},{pos[2]}", [])][:LINES]
        entity.front = lines + [""] * (LINES - len(lines))
        level.set_block_entity(entity)


# Registered here, not with a class decorator (classes stay compilable by mypyc).
register_block_entity(SignBlockEntity)
