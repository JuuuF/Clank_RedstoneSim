"""Small pixel-art icons for buttons, drawn from ASCII art at 2× like the game's GUI
sprites, so every transport button has the same size, weight and font-free look."""

from __future__ import annotations

from functools import cache

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from redsim.ui import theme

#: Each icon: rows of ``#`` (filled) and ``.`` (empty), 9 rows high.
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

SCALE = 2


@cache
def pixel_pixmap(name: str, color: str = theme.TEXT) -> QPixmap:
    """``name``'s art in ``color`` with the game's 1-pixel drop shadow, on a canvas wide
    enough for the widest icon, so all icons line up."""
    rows = ICONS[name]
    width = max(len(row) for icon in ICONS.values() for row in icon) + 1
    height = len(rows) + 1
    pixmap = QPixmap(width * SCALE, height * SCALE)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    left = (width - 1 - len(rows[0])) // 2
    shade = QColor(color).darker(400)
    for offset, fill in ((1, shade), (0, QColor(color))):
        for y, row in enumerate(rows):
            for x, cell in enumerate(row):
                if cell == "#":
                    rect = QRect((left + x + offset) * SCALE, (y + offset) * SCALE, SCALE, SCALE)
                    painter.fillRect(rect, fill)
    painter.end()
    return pixmap


def pixel_icon(name: str) -> QIcon:
    """The icon, with a dimmed variant for disabled buttons."""
    icon = QIcon(pixel_pixmap(name))
    icon.addPixmap(pixel_pixmap(name, theme.TEXT_DIM), QIcon.Mode.Disabled)
    return icon
