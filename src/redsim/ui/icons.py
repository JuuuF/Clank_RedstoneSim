"""Block previews for the inventory and the block search: the block's 3D model
(``style.block_boxes``) drawn in an isometric view with Qt's painter (no OpenGL needed).

The view looks from above the south-east: the top, east and south faces of every box are
visible, shaded like Minecraft's item renders (top brightest). Boxes are drawn back to
front, which is exact for the axis-aligned, mostly non-overlapping boxes of block models.
"""

from __future__ import annotations

import math
from functools import cache

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

from redsim.ui.style import Box, block_boxes
from redsim.world import blocks
from redsim.world.block import Block, BlockState

COS30 = math.cos(math.radians(30))
#: Face brightness: top, east (+x), south (+z).
SHADES = (1.0, 0.78, 0.6)

#: States that show a block better than its default state.
ICON_STATES = {
    "minecraft:redstone_wire": "redstone_wire[north=side,east=side,south=side,west=side,power=15]",
    "minecraft:redstone_lamp": "redstone_lamp[lit=true]",
    "minecraft:repeater": "repeater[facing=west]",
    "minecraft:comparator": "comparator[facing=west]",
    "minecraft:observer": "observer[facing=east]",
    "minecraft:piston": "piston[facing=up]",
    "minecraft:sticky_piston": "sticky_piston[facing=up]",
    "minecraft:lever": "lever[face=floor,facing=west]",
    "minecraft:stone_button": "stone_button[face=floor,facing=west]",
    "minecraft:oak_button": "oak_button[face=floor,facing=west]",
    "minecraft:hopper": "hopper[facing=down]",
    "minecraft:lectern": "lectern[facing=west,has_book=true]",
    "minecraft:target": "target[power=15]",
}


def icon_state(block: Block) -> BlockState:
    text = ICON_STATES.get(block.id)
    return blocks.parse_state(text) if text else block.default_state


def _project(x: float, y: float, z: float) -> QPointF:
    """Block units (0..1) to the icon plane: +x right-down, +z left-down, +y up."""
    return QPointF((x - z) * COS30, (x + z) * 0.5 - y)


def _faces(box: Box) -> list[tuple[list[tuple[float, float, float]], float]]:
    (x0, y0, z0), (x1, y1, z1) = (tuple(v / 16 for v in box.lo), tuple(v / 16 for v in box.hi))
    return [
        ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], SHADES[0]),  # top
        ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], SHADES[1]),  # east
        ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], SHADES[2]),  # south
    ]


def _back_to_front(boxes: list[Box]) -> list[Box]:
    """Painter's order for the view from +x, +y, +z: a box is behind another if it ends
    before the other starts on some axis (topological sort; ties by center)."""

    def center(box: Box) -> float:
        return sum(box.lo) + sum(box.hi)

    def behind(a: Box, b: Box) -> bool:
        return any(a.hi[i] <= b.lo[i] for i in range(3)) and not any(
            b.hi[i] <= a.lo[i] for i in range(3)
        )

    remaining = sorted(boxes, key=center)
    order: list[Box] = []
    while remaining:
        for index, box in enumerate(remaining):
            if not any(behind(other, box) for other in remaining if other is not box):
                order.append(remaining.pop(index))
                break
        else:  # a cycle (overlapping boxes): fall back to the center order
            order.append(remaining.pop(0))
    return order


def render_boxes(boxes: list[Box], size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if not boxes:
        return pixmap
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # A full block spans 2·cos30 wide and 2 high: fit that with a small margin.
    scale = size * 0.92 / 2.0
    painter.translate(size / 2, size / 2)
    painter.scale(scale, scale)
    order = _back_to_front(boxes)
    outline = QPen(QColor(0, 0, 0, 70))
    outline.setWidthF(0.6 / scale)
    for box in order:
        r, g, b, a = box.color
        for corners, shade in _faces(box):
            color = QColor.fromRgbF(
                min(1.0, r * shade), min(1.0, g * shade), min(1.0, b * shade), a
            )
            painter.setBrush(color)
            painter.setPen(outline)
            painter.drawPolygon(QPolygonF([_project(*corner) for corner in corners]))
    painter.end()
    return pixmap


@cache
def block_pixmap(block_id: str, size: int = 32) -> QPixmap:
    return render_boxes(block_boxes(icon_state(blocks.get(block_id))), size)


def block_icon(block: Block, size: int = 32) -> QIcon:
    return QIcon(block_pixmap(block.id, size))
