"""Small pixel-art icons for buttons, drawn from ASCII art at 2× like the game's GUI
sprites, so every transport button has the same size, weight and font-free look."""

from __future__ import annotations

from functools import cache

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRect, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from redsim.ui import theme

#: Each icon: rows of ``#`` (filled) and ``.`` (empty), at most 9 rows high.
ICONS: dict[str, tuple[str, ...]] = {
    "start": (
        "##.....#...#",
        "##....##..##",
        "##...###.###",
        "##..########",
        "##.#########",
        "##..########",
        "##...###.###",
        "##....##..##",
        "##.....#...#",
    ),
    "previous": (
        "........#",
        "...#...##",
        "..###.###",
        ".########",
        "#########",
        ".########",
        "..###.###",
        "...#...##",
        "........#",
    ),
    "back": (
        "##....#",
        "##...##",
        "##..###",
        "##.####",
        "#######",
        "##.####",
        "##..###",
        "##...##",
        "##....#",
    ),
    "reverse": (
        "....#",
        "...##",
        "..#.#",
        ".#..#",
        "#...#",
        ".#..#",
        "..#.#",
        "...##",
        "....#",
    ),
    "play": (
        "#....",
        "##...",
        "###..",
        "####.",
        "#####",
        "####.",
        "###..",
        "##...",
        "#....",
    ),
    "pause": (
        "##..##",
        "##..##",
        "##..##",
        "##..##",
        "##..##",
        "##..##",
        "##..##",
        "##..##",
        "##..##",
    ),
    "step": (
        "#....##",
        "##...##",
        "###..##",
        "####.##",
        "#######",
        "####.##",
        "###..##",
        "##...##",
        "#....##",
    ),
    "next": (
        "#........",
        "##...#...",
        "###.###..",
        "########.",
        "#########",
        "########.",
        "###.###..",
        "##...#...",
        "#........",
    ),
    "end": (
        "#...#.....##",
        "##..##....##",
        "###.###...##",
        "########..##",
        "#########.##",
        "########..##",
        "###.###...##",
        "##..##....##",
        "#...#.....##",
    ),
}

ICONS.update(
    {
        "rotate": (
            "...####.#",
            "..#....##",
            ".#....###",
            "#........",
            "#........",
            "#........",
            ".#.....#.",
            "..#...#..",
            "...###...",
        ),
        "flip": (
            "....#.#....",
            "...##.##...",
            "..###.###..",
            ".####.####.",
            "#####.#####",
            ".####.####.",
            "..###.###..",
            "...##.##...",
            "....#.#....",
        ),
        "copy": (
            "...######",
            "...#....#",
            "######..#",
            "#....#..#",
            "#....#..#",
            "#....####",
            "#....#...",
            "#....#...",
            "######...",
        ),
        "paste": (
            "...##...",
            ".######.",
            "#.#..#.#",
            "#......#",
            "#.####.#",
            "#......#",
            "#.###..#",
            "#......#",
            "########",
        ),
        "delete": (
            "##.....##",
            ".##...##.",
            "..##.##..",
            "...###...",
            "..##.##..",
            ".##...##.",
            "##.....##",
        ),
        "lock": (
            "..###..",
            ".#...#.",
            ".#...#.",
            "#######",
            "###.###",
            "###.###",
            "#######",
            "#######",
        ),
        "search": (
            ".###.....",
            "#...#....",
            "#...#....",
            "#...#....",
            ".###.....",
            "....##...",
            ".....##..",
            "......##.",
            ".......##",
        ),
        "monitor": (
            "#........",
            "#......#.",
            "#.....#.#",
            "#....#...",
            "#.#.#....",
            "##.#.....",
            "#........",
            "#########",
        ),
        "arrow": (
            ".....###",
            "......##",
            ".....#.#",
            "....#...",
            "...#....",
            "#.#.....",
            ".#......",
            "#.#.....",
        ),
        "snowball": (
            "..###..",
            ".#####.",
            "#######",
            "#######",
            "#######",
            ".#####.",
            "..###..",
        ),
    }
)


def _mirrored(rows: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(row[::-1] for row in rows)


def _transposed(rows: tuple[str, ...]) -> tuple[str, ...]:
    return tuple("".join(row[i] for row in rows) for i in range(len(rows[0])))


ICONS.update(
    {
        "normal": (
            "#......",
            "##.....",
            "###....",
            "####...",
            "#####..",
            "######.",
            "###....",
            "#.##...",
            "...##..",
        ),
        "build": (
            "....#....",
            "..##.##..",
            "##.....##",
            "#.##.##.#",
            "#...#...#",
            "#...#...#",
            "#...#...#",
            ".##.#.##.",
            "...###...",
        ),
        "select": (
            "###.#.###",
            "#.......#",
            "#.......#",
            ".........",
            "#.......#",
            ".........",
            "#.......#",
            "#.......#",
            "###.#.###",
        ),
    }
)
ICONS.update(
    {
        "mouse_left": (
            ".#####.",
            "####..#",
            "####..#",
            "####..#",
            "#######",
            "#.....#",
            "#.....#",
            "#.....#",
            ".#####.",
        ),
        "mouse_middle": (
            ".#####.",
            "#..#..#",
            "#.###.#",
            "#..#..#",
            "#######",
            "#.....#",
            "#.....#",
            "#.....#",
            ".#####.",
        ),
    }
)
# Compass arrows for direction properties; "face_*" point at the top or bottom face.
ICONS["north"] = (
    "...#...",
    "..###..",
    ".#####.",
    "#######",
    "..###..",
    "..###..",
    "..###..",
)
ICONS["south"] = ICONS["north"][::-1]
ICONS["west"] = _transposed(ICONS["north"])
ICONS["east"] = _mirrored(ICONS["west"])
ICONS["face_up"] = ("#######", ".......", *ICONS["north"][:5])
ICONS["face_down"] = ICONS["face_up"][::-1]
ICONS["less"] = _mirrored(ICONS["play"])  # stepper and page buttons
ICONS["more"] = ICONS["play"]
ICONS["undo"] = (
    "..#......",
    ".##......",
    "#######..",
    ".##....#.",
    "..#.....#",
    "........#",
    "........#",
    ".......#.",
    "..#####..",
)
ICONS["redo"] = _mirrored(ICONS["undo"])
ICONS["mouse_right"] = _mirrored(ICONS["mouse_left"])
ICONS["rotate_back"] = _mirrored(ICONS["rotate"])
ICONS["flip_depth"] = _transposed(ICONS["flip"])

SCALE = 2
#: Every icon's size: the canvas fits the widest and tallest art, plus the shadow pixel.
ICON_SIZE = QSize(
    (max(len(row) for icon in ICONS.values() for row in icon) + 1) * SCALE,
    (max(len(icon) for icon in ICONS.values()) + 1) * SCALE,
)


@cache
def pixel_pixmap(
    name: str, color: str = theme.TEXT, scale: int = SCALE, tight: bool = False
) -> QPixmap:
    """``name``'s art in ``color`` with the game's 1-pixel drop shadow, on a canvas wide
    enough for the widest icon, so all icons line up (``tight``: just the art); ``scale``
    screen pixels per art pixel."""
    rows = ICONS[name]
    if tight:
        width, height = len(rows[0]) + 1, len(rows) + 1
    else:
        width = max(len(row) for icon in ICONS.values() for row in icon) + 1
        height = max(len(icon) for icon in ICONS.values()) + 1
    pixmap = QPixmap(width * scale, height * scale)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    left = (width - 1 - len(rows[0])) // 2
    top = (height - 1 - len(rows)) // 2
    shade = QColor(color).darker(400)
    for offset, fill in ((1, shade), (0, QColor(color))):
        for y, row in enumerate(rows):
            for x, cell in enumerate(row):
                if cell == "#":
                    rect = QRect(
                        (left + x + offset) * scale, (top + y + offset) * scale, scale, scale
                    )
                    painter.fillRect(rect, fill)
    painter.end()
    return pixmap


@cache
def pixel_data_uri(name: str, color: str = theme.TEXT, scale: int = SCALE) -> str:
    """The art, tightly cropped, as a ``data:`` URI for ``<img>`` in rich text labels."""
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixel_pixmap(name, color, scale, tight=True).save(buffer, "PNG")
    return "data:image/png;base64," + bytes(data.toBase64().data()).decode()


def pixel_icon(name: str) -> QIcon:
    """The icon at 2× (buttons) and 1× (menus: crisp instead of scaled down), with dimmed
    variants for disabled actions."""
    icon = QIcon()
    for scale in (1, SCALE):
        icon.addPixmap(pixel_pixmap(name, theme.TEXT, scale))
        icon.addPixmap(pixel_pixmap(name, theme.TEXT_DIM, scale), QIcon.Mode.Disabled)
    return icon
