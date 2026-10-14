"""Sign text drawn on the sign's board, like the game's sign renderer: four centered lines
on the front and on the back, in the pixel font, in perspective. Text is shown within
``SIGN_TEXT_DISTANCE`` blocks, only on sides facing the camera and not hidden behind
other blocks.

Board geometry comes from the game's sign models (``template_sign_rot_0``,
``template_wall_sign``, ``template_hanging_sign_rot_0``, ``template_wall_hanging_sign``):
a standing sign's board is 16×8 pixels from y 9.33, 0.67 px in front of the post; a wall
sign's 16×8 from y 4.33, 1.67 px from the wall; a hanging sign's 14×10 from y 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPolygonF, QTransform

from redsim.core.pos import Pos
from redsim.ui import theme
from redsim.world.block import BlockState
from redsim.world.blocks.sign import LINES, SignBlockEntity

#: Text colors of the dyes (``DyeColor.textColor``); sign text without glow is drawn at
#: 40 % of it (``SignRenderer.getDarkColor``), so black text is nearly black.
DYE_TEXT = {
    "white": 0xF0F0F0, "orange": 0xF9801D, "magenta": 0xC74EBD, "light_blue": 0x3AB3DA,
    "yellow": 0xFED83D, "lime": 0x80C71F, "pink": 0xF38BAA, "gray": 0x474F52,
    "light_gray": 0x9D9D97, "cyan": 0x169C9C, "purple": 0x8932B8, "blue": 0x3C44AA,
    "brown": 0x835432, "green": 0x5E7C16, "red": 0xB02E26, "black": 0x1D1D21,
}  # fmt: skip
#: Font pixels per block along a board (a line is 10 font pixels high, 4 lines fit).
FONT_PER_BLOCK = 96
LINE_PIXELS = 10


@dataclass(frozen=True)
class Board:
    """One side of a sign's board: its middle, outward normal, the viewer's right along
    it and its size (blocks)."""

    center: np.ndarray
    normal: np.ndarray
    right: np.ndarray
    width: float
    height: float
    side: str  # "front" or "back"


def _prop(state: BlockState, name: str, default: str) -> str:
    """A property's value as text (real sign blocks and foreign ones alike)."""
    values = state.properties_dict() if hasattr(state, "properties_dict") else {}
    if name in values:
        return str(values[name])
    return str(getattr(state.block, "extra_properties", {}).get(name, default))


_HORIZONTAL = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}


def boards(pos: Pos, state: BlockState) -> list[Board]:
    """The front and back of a sign's board at ``pos`` (none for other blocks)."""
    block_id = state.block.id
    if not block_id.endswith("_sign"):
        return []
    hanging = "hanging" in block_id
    wall = "_wall_" in block_id
    if wall:
        normal = np.array(_HORIZONTAL.get(_prop(state, "facing", "north"), (0, 0, -1)), float)
    else:
        angle = math.radians(int(_prop(state, "rotation", "0")) * 22.5)
        normal = np.array([-math.sin(angle), 0.0, math.cos(angle)])
    base = np.array(pos, dtype=float) + 0.5
    if hanging:  # 14×10 pixels, 2 pixels thick, from the bottom of the block
        center = base + np.array([0.0, 5 / 16 - 0.5, 0.0]) + normal * (1 / 16)
        width, height = 14 / 16, 10 / 16
    elif wall:  # 16×8 pixels against the wall behind
        center = base + np.array([0.0, 8.333 / 16 - 0.5, 0.0]) - normal * (0.5 - 1.667 / 16)
        width, height = 1.0, 0.5
    else:  # standing: on a post
        center = base + np.array([0.0, 13.333 / 16 - 0.5, 0.0]) + normal * (0.667 / 16)
        width, height = 1.0, 0.5
    right = np.array([normal[2], 0.0, -normal[0]])
    thickness = (2 / 16 if hanging else 1.333 / 16) + 0.004
    back = center - normal * thickness
    return [
        Board(center + normal * 0.004, normal, right, width, height, "front"),
        Board(back, -normal, -right, width, height, "back"),
    ]


def sign_lines(document: Any, pos: Pos, side: str) -> tuple[list[str], str, bool]:
    """A sign's lines on ``side``, its dye color and glow: from its block entity, or for
    signs the simulator keeps as foreign blocks (hanging signs) from ``extra["signs"]``."""
    entity = document.level.get_block_entity(pos, create=False)
    if isinstance(entity, SignBlockEntity):
        data = entity.data.get("front_text" if side == "front" else "back_text") or {}
        color = str(data.get("color", "black"))
        return entity.lines(side), color, bool(data.get("has_glowing_text", False))
    if side != "front":
        return [], "black", False
    saved = (document.extra.get("signs") or {}).get(f"{pos[0]},{pos[1]},{pos[2]}") or []
    return [str(line) for line in saved][:LINES], "black", False


def text_color(dye: str, glowing: bool) -> QColor:
    value = DYE_TEXT.get(dye, DYE_TEXT["black"])
    red, green, blue = (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF
    if not glowing:
        red, green, blue = int(red * 0.4), int(green * 0.4), int(blue * 0.4)
    return QColor(red, green, blue)


@lru_cache(maxsize=256)
def board_image(lines: tuple[str, ...], width: float, height: float, color: str) -> QImage | None:
    """The board's text as an image (font pixels): lines centered, 10 pixels apart."""
    font = theme.PixelFont.load()
    if font is None:
        return None
    size_w, size_h = round(width * FONT_PER_BLOCK), round(height * FONT_PER_BLOCK)
    image = QImage(size_w, size_h, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    top = (size_h - LINES * LINE_PIXELS) // 2
    for index, text in enumerate(lines[:LINES]):
        if not text:
            continue
        pixmap = font.pixmap(text, color, 1, shadow=False)
        x = (size_w - font.width(text, 1)) // 2
        painter.drawPixmap(x, top + index * LINE_PIXELS - font.TOP + 1, pixmap)
    painter.end()
    return image


def draw_board(
    painter: QPainter, image: QImage, board: Board, mvp: np.ndarray, width: int, height: int
) -> bool:
    """Draw ``image`` over the board's projected quad; False when it is not on screen."""
    up = np.array([0.0, 1.0, 0.0])
    half_w, half_h = board.right * board.width / 2, up * board.height / 2
    corners = [  # top left, top right, bottom right, bottom left (as the image)
        board.center - half_w + half_h,
        board.center + half_w + half_h,
        board.center + half_w - half_h,
        board.center - half_w - half_h,
    ]
    points = []
    for corner in corners:
        clip = mvp @ np.array([*corner, 1.0])
        if clip[3] <= 0.05:
            return False
        points.append(
            QPointF((clip[0] / clip[3] + 1) / 2 * width, (1 - clip[1] / clip[3]) / 2 * height)
        )
    source = QPolygonF(
        [
            QPointF(0, 0),
            QPointF(image.width(), 0),
            QPointF(image.width(), image.height()),
            QPointF(0, image.height()),
        ]
    )
    transform = QTransform()
    if not QTransform.quadToQuad(source, QPolygonF(points), transform):
        return False
    painter.save()
    painter.setTransform(transform)
    painter.drawImage(QRectF(0, 0, image.width(), image.height()), image)
    painter.restore()
    return True


def facing_camera(board: Board, eye: np.ndarray) -> bool:
    return float(np.dot(board.normal, eye - board.center)) > 0.0


__all__ = [
    "Board",
    "board_image",
    "boards",
    "draw_board",
    "facing_camera",
    "sign_lines",
    "text_color",
]
