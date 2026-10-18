"""Block previews for the inventory and the block search, drawn with Qt's painter.

With the game's assets (``assets.Assets``): the item's own look, a flat sprite (dust,
torches, repeaters, rails, hoppers) or its block model, textured, in the isometric view.
Without them: the colored box model (``style.block_boxes``) in the same view.

The view looks from above the south-east: the top, east and south faces of every box are
visible, shaded like Minecraft's item renders (top brightest). Boxes are drawn back to
front, which is exact for the axis-aligned, mostly non-overlapping boxes of block models.
"""

from __future__ import annotations

import math
from functools import cache
from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QTransform,
)

from redsim.core.direction import Direction
from redsim.ui.assets import Assets, Quad
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


#: Inventory items of blocks whose item has another name.
ITEM_IDS = {
    "minecraft:redstone_wire": "minecraft:redstone",
    "minecraft:redstone_wall_torch": "minecraft:redstone_torch",
    "minecraft:tripwire": "minecraft:string",  # string places tripwire
}


#: Decoded textures by name (reading one from the jar and decoding it takes ~40 µs, and a
#: prefab preview asks for one per face).
_TEXTURES: dict[str, QImage | None] = {}


def _texture_image(texture: str) -> QImage | None:
    if texture in _TEXTURES:
        return _TEXTURES[texture]
    assets = Assets.find()
    data = assets.texture_bytes(texture) if assets is not None else None
    image: QImage | None = None
    if data is not None:
        image = QImage.fromData(data)
        if image.isNull():
            image = None
        elif image.height() > image.width():  # animated: first frame
            image = image.copy(0, 0, image.width(), image.width())
    _TEXTURES[texture] = image
    return image


def render_item_sprite(texture: str, size: int) -> QPixmap | None:
    """A flat item sprite, scaled up with sharp pixels."""
    image = _texture_image(texture)
    if image is None:
        return None
    scaled = image.scaled(
        size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
    )
    return QPixmap.fromImage(scaled)


def render_quads(quads: list[Quad], size: int, tint: Any = None) -> QPixmap:
    """The game's block model in the isometric view, textured: every quad facing the
    viewer is mapped from its texture rectangle onto its projected corners."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    scale = size * 0.92 / 2.0
    base = QTransform().translate(size / 2, size / 2).scale(scale, scale)
    shades = {Direction.UP: 1.0, Direction.EAST: 0.78, Direction.SOUTH: 0.6}

    def depth(quad: Quad) -> float:
        return sum(c[0] + c[1] + c[2] for c in quad.corners)

    for quad in sorted(quads, key=depth):
        if quad.facing not in shades:
            continue
        image = _texture_image(quad.texture)
        if image is None:
            continue
        if quad.tint >= 0 and tint is not None:
            image = _tinted(image, tint)
        source = QPolygonF([QPointF(u * image.width(), v * image.height()) for u, v in quad.uvs])
        target = QPolygonF([_project(x - 0.5, y - 0.5, z - 0.5) for x, y, z in quad.corners])
        mapping = QTransform()
        if not QTransform.quadToQuad(source, target, mapping):
            continue
        painter.save()
        painter.setTransform(mapping * base)
        clip = QPainterPath()
        clip.addPolygon(source)
        painter.setClipPath(clip)
        painter.drawImage(0, 0, image)
        painter.restore()
        shade = shades[quad.facing] if quad.shade else 1.0
        if shade < 1.0:
            painter.save()
            painter.setTransform(base)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, int(255 * (1 - shade))))
            painter.drawPolygon(target)
            painter.restore()
    painter.end()
    return pixmap


#: Tinted textures by (texture, tint): grass, leaves and dust are tinted per face.
_TINTED: dict[tuple[str, tuple[float, ...]], QImage] = {}


def _tinted_texture(texture: str, image: QImage, color: tuple[float, float, float]) -> QImage:
    key = (texture, tuple(color))
    tinted = _TINTED.get(key)
    if tinted is None:
        tinted = _TINTED[key] = _tinted(image, color)
    return tinted


def _tinted(image: QImage, color: tuple[float, float, float]) -> QImage:
    tinted = image.convertToFormat(QImage.Format.Format_ARGB32)
    painter = QPainter(tinted)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    painter.fillRect(tinted.rect(), QColor.fromRgbF(*color))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, image)
    painter.end()
    return tinted


def game_pixmap(block_id: str, size: int) -> QPixmap | None:
    """The game's inventory look: the item's sprite, or its block model."""
    assets = Assets.find()
    if assets is None:
        return None
    model = assets.item_model(ITEM_IDS.get(block_id, block_id))
    if model is not None and assets.is_generated_item(model):
        layer = assets.resolve_texture(assets.model(model)["textures"], "#layer0")
        return render_item_sprite(layer[0], size) if layer else None
    block = blocks.get(block_id)
    if model is not None:
        quads = assets.bake(assets.model(model))
    else:
        quads = list(assets.block_quads(icon_state(block)))
    if not quads:
        return None
    from redsim.ui.geometry import tint_color

    return render_quads(quads, size, tint_color(icon_state(block), 0))


@cache
def block_pixmap(block_id: str, size: int = 32) -> QPixmap:
    textured = game_pixmap(block_id, size)
    if textured is not None:
        return textured
    return render_boxes(block_boxes(icon_state(blocks.get(block_id))), size)


def block_icon(block: Block, size: int = 32) -> QIcon:
    return QIcon(block_pixmap(block.id, size))


@cache
def item_pixmap(item_id: str, size: int = 32) -> QPixmap:
    """An item as the game's inventory shows it: its sprite or its block model; a gray
    square without the game's assets."""
    assets = Assets.find()
    model = assets.item_model(item_id) if assets is not None else None
    if assets is not None and model is not None:
        if assets.is_generated_item(model):
            layer = assets.resolve_texture(assets.model(model)["textures"], "#layer0")
            sprite = render_item_sprite(layer[0], size) if layer else None
            if sprite is not None:
                return sprite
        else:
            quads = assets.bake(assets.model(model))
            if quads:
                return render_quads(quads, size)
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.fillRect(size // 4, size // 4, size // 2, size // 2, QColor("#8e8f96"))
    painter.end()
    return pixmap


#: Prefab previews made so far, by their blocks (rendering takes a moment). Images, not
#: pixmaps: a world's loading thread draws them too (``prefab_image``).
_PREFAB_PREVIEWS: dict[Any, QImage] = {}
#: The pixmaps by prefab object (the Circuit panel asks again after every change): the
#: object, so that a reused id() is not mistaken for it, and the preview.
_PREVIEWS_BY_ID: dict[tuple[int, int], tuple[Any, QPixmap]] = {}
#: Below this many pixels per block, blocks are drawn as their colored boxes.
FLAT_BELOW_PX = 5.0


def cached_prefab_pixmap(prefab: Any, size: int = 64) -> QPixmap | None:
    """The preview of ``prefab`` if it was drawn already (cheap: by object)."""
    entry = _PREVIEWS_BY_ID.get((id(prefab), size))
    return entry[1] if entry is not None and entry[0] is prefab else None


def prefab_image(prefab: Any, size: int = 64) -> QImage:
    """The preview of ``prefab`` as an image; safe to call from a loading thread (it paints
    on a QImage) and cached by the prefab's blocks."""
    entries = [
        (dx, dy, dz, text)
        for dx, dy, dz, text, _ in prefab.blocks
        if not text.startswith("minecraft:air")
    ]
    key = (size, hash(tuple(entries)), len(entries))
    image = _PREFAB_PREVIEWS.get(key)
    if image is None:
        states = {(dx, dy, dz): blocks.parse_state(text) for dx, dy, dz, text in entries}
        image = _render_prefab(states, size)
        if len(_PREFAB_PREVIEWS) > 200:
            _PREFAB_PREVIEWS.clear()
        _PREFAB_PREVIEWS[key] = image
    return image


def prefab_pixmap(prefab: Any, size: int = 64) -> QPixmap:
    """A prefab in the isometric view of the inventory icons (textured with the game's
    assets, else the colored box models), scaled to fit ``size``."""
    cached = cached_prefab_pixmap(prefab, size)
    if cached is not None:
        return cached
    pixmap = QPixmap.fromImage(prefab_image(prefab, size))
    if len(_PREVIEWS_BY_ID) > 200:
        _PREVIEWS_BY_ID.clear()
    _PREVIEWS_BY_ID[(id(prefab), size)] = (prefab, pixmap)
    return pixmap


_VISIBLE = {Direction.UP: (0, 1, 0), Direction.EAST: (1, 0, 0), Direction.SOUTH: (0, 0, 1)}


def _visible_blocks(
    states: dict[tuple[int, int, int], BlockState], opaque: set[tuple[int, int, int]]
) -> dict[tuple[int, int, int], BlockState]:
    """The blocks the isometric view can see. A step of (1, 1, 1) lands on the same spot
    of the icon plane, nearer to the viewer, so a block with an opaque cube anywhere along
    that diagonal in front of it is hidden completely."""
    front: dict[tuple[int, int], int] = {}  # per diagonal: the nearest opaque cube's y
    for x, y, z in opaque:
        key = (x - y, z - y)
        if front.get(key, y - 1) < y:
            front[key] = y
    return {
        pos: state
        for pos, state in states.items()
        if front.get((pos[0] - pos[1], pos[2] - pos[1]), pos[1]) <= pos[1]
    }


def _pixels_per_block(states: dict[tuple[int, int, int], BlockState], size: int) -> float:
    """How wide one block is in a preview of ``size`` (from the blocks' bounding box)."""
    xs = [x for x, _, _ in states]
    ys = [y for _, y, _ in states]
    zs = [z for _, _, z in states]
    corners = [
        _project(x, y, z)
        for x in (min(xs), max(xs) + 1)
        for y in (min(ys), max(ys) + 1)
        for z in (min(zs), max(zs) + 1)
    ]
    width = max(p.x() for p in corners) - min(p.x() for p in corners)
    height = max(p.y() for p in corners) - min(p.y() for p in corners)
    return size * 0.94 / max(width, height, 1e-6)


def _render_prefab(states: dict[tuple[int, int, int], BlockState], size: int) -> QImage:
    canvas = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(Qt.GlobalColor.transparent)
    if not states:
        return canvas
    from redsim.ui.geometry import is_full_opaque, tint_color

    full = {pos for pos, state in states.items() if state.is_collision_shape_full_block()}
    opaque = {pos for pos in full if is_full_opaque(block_boxes(states[pos]))}  # not glass
    states = _visible_blocks(states, opaque)
    assets = Assets.find()
    # Blocks only a few pixels wide: their colored boxes (the textures would not show).
    flat = assets is None or _pixels_per_block(states, size) < FLAT_BELOW_PX
    #: Depth, projected corners, the quad (None: a colored box face), its tint or shade,
    #: the box color.
    faces: list[tuple[float, list[QPointF], Any, Any, Any]] = []
    for (bx, by, bz), state in states.items():
        if not flat:
            tint = tint_color(state, 0)
            for quad in assets.block_quads(state):  # type: ignore[union-attr]
                step = _VISIBLE.get(quad.facing)
                if step is None:
                    continue
                if quad.cull is not None and (bx + step[0], by + step[1], bz + step[2]) in full:
                    continue
                corners = [(x + bx, y + by, z + bz) for x, y, z in quad.corners]
                depth = sum(c[0] + c[1] + c[2] for c in corners) / 4
                faces.append((depth, [_project(*c) for c in corners], quad, tint, None))
            continue
        cube = (bx, by, bz) in opaque
        for box in block_boxes(state):
            for (corners, shade), step in zip(_faces(box), _VISIBLE.values(), strict=True):
                if cube and (bx + step[0], by + step[1], bz + step[2]) in opaque:
                    continue  # covered by the neighbor on that side
                moved = [(x + bx, y + by, z + bz) for x, y, z in corners]
                depth = sum(c[0] + c[1] + c[2] for c in moved) / 4
                faces.append((depth, [_project(*c) for c in moved], None, shade, box.color))
    points = [point for _, projected, *_ in faces for point in projected]
    if not points:
        return canvas
    left = min(p.x() for p in points)
    right = max(p.x() for p in points)
    top = min(p.y() for p in points)
    bottom = max(p.y() for p in points)
    scale = size * 0.94 / max(right - left, bottom - top, 1e-6)
    base = (
        QTransform()
        .translate(size / 2, size / 2)
        .scale(scale, scale)
        .translate(-(left + right) / 2, -(top + bottom) / 2)
    )
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    painter.setPen(Qt.PenStyle.NoPen)
    shades = {Direction.UP: 1.0, Direction.EAST: 0.78, Direction.SOUTH: 0.6}
    for _, points, quad, extra, color in sorted(faces, key=lambda face: face[0]):
        target = QPolygonF(points)
        if quad is None:  # a colored box face
            r, g, b, a = color
            painter.setTransform(base)
            painter.setBrush(
                QColor.fromRgbF(min(1.0, r * extra), min(1.0, g * extra), min(1.0, b * extra), a)
            )
            painter.drawPolygon(target)
            continue
        image = _texture_image(quad.texture)
        if image is None:
            continue
        if quad.tint >= 0:
            image = _tinted_texture(quad.texture, image, extra)
        source = QPolygonF([QPointF(u * image.width(), v * image.height()) for u, v in quad.uvs])
        mapping = QTransform()
        if not QTransform.quadToQuad(source, target, mapping):
            continue
        painter.save()
        painter.setTransform(mapping * base)
        clip = QPainterPath()
        clip.addPolygon(source)
        painter.setClipPath(clip)
        painter.drawImage(0, 0, image)
        painter.restore()
        shade = shades[quad.facing] if quad.shade else 1.0
        if shade < 1.0:
            painter.setTransform(base)
            painter.setBrush(QColor(0, 0, 0, int(255 * (1 - shade))))
            painter.drawPolygon(target)
    painter.end()
    return canvas
