"""Trackmania-style inventory bar: hierarchical folders at the bottom, navigated by numbers.

Number keys open the folder (or pick the block) with that number; Backspace goes up one
level. Like Trackmania, every folder level above the current one stays visible as a
compact row with the chosen folder highlighted; clicking there jumps to that level. Tiles
show a preview of the block (``icons``). Recently placed blocks sit at the top right (saved in
``recent_blocks.json`` next to the preferences). Choosing a block enters BUILD mode
(``block_chosen``). The folder tree is plain data (``INVENTORY``), so new blocks only need a
line here; folders can nest when one grows past nine entries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from redsim.editor import sources
from redsim.ui import theme
from redsim.ui.icons import block_pixmap
from redsim.ui.preferences import config_dir
from redsim.world import blocks
from redsim.world.block import Block

ICON_SIZE = 32
TILE_HEIGHT = 58


@dataclass(frozen=True)
class Folder:
    title: str
    children: tuple[Folder | str, ...] = field(default_factory=tuple)  # str: block id


INVENTORY = Folder(
    "Inventory",
    (
        Folder(
            "Redstone",
            (
                "minecraft:redstone_wire",
                "minecraft:redstone_torch",
                "minecraft:repeater",
                "minecraft:comparator",
                "minecraft:observer",
                "minecraft:redstone_lamp",
                "minecraft:redstone_block",
                "minecraft:target",
                Folder(
                    "Switches",
                    ("minecraft:lever", "minecraft:stone_button", "minecraft:oak_button"),
                ),
            ),
        ),
        Folder(
            "Movement",
            (
                "minecraft:piston",
                "minecraft:sticky_piston",
                "minecraft:slime_block",
                "minecraft:honey_block",
                "minecraft:obsidian",
            ),
        ),
        Folder("Signal sources", ("minecraft:barrel", "minecraft:lectern", "minecraft:cake")),
        Folder("Items", ("minecraft:hopper",)),
        Folder("Rails", ("minecraft:rail", "minecraft:powered_rail", "minecraft:activator_rail")),
        Folder(
            "Building",
            (
                "minecraft:stone",
                "minecraft:smooth_stone",
                "minecraft:cobblestone",
                "minecraft:oak_planks",
                "minecraft:white_wool",
                "minecraft:white_concrete",
                "minecraft:smooth_stone_slab",
            ),
        ),
        Folder("Special", ("minecraft:glass", "minecraft:glowstone", "minecraft:bedrock")),
    ),
)


#: Compact tile labels.
SHORT_NAMES = {
    "minecraft:redstone_wire": "dust",
    "minecraft:redstone_torch": "torch",
    "minecraft:redstone_lamp": "lamp",
    "minecraft:redstone_block": "block of redstone",
    "minecraft:stone_button": "stone button",
    "minecraft:oak_button": "oak button",
    "minecraft:sticky_piston": "sticky piston",
    "minecraft:smooth_stone_slab": "slab",
    "minecraft:smooth_stone": "smooth stone",
}


class InventoryNav:
    """Where the inventory is (a path of folder indices) and what number keys do there."""

    def __init__(self, root: Folder = INVENTORY) -> None:
        self.root = root
        self.path: list[int] = []

    def folder(self) -> Folder:
        folder = self.root
        for index in self.path:
            child = folder.children[index]
            assert isinstance(child, Folder)
            folder = child
        return folder

    def breadcrumb(self) -> list[str]:
        titles, folder = [], self.root
        for index in self.path:
            child = folder.children[index]
            assert isinstance(child, Folder)
            titles.append(child.title)
            folder = child
        return titles

    def press(self, number: int) -> str | None:
        """Number key (1-based): open that folder, or return that block id."""
        children = self.folder().children
        if not 1 <= number <= len(children):
            return None
        child = children[number - 1]
        if isinstance(child, Folder):
            self.path.append(number - 1)
            return None
        return child

    def up(self) -> bool:
        if not self.path:
            return False
        self.path.pop()
        return True

    def reveal(self, block_id: str) -> bool:
        """Open the folder that holds ``block_id`` (after a pick)."""

        def search(folder: Folder, path: list[int]) -> list[int] | None:
            for index, child in enumerate(folder.children):
                if child == block_id:
                    return path
                if isinstance(child, Folder):
                    found = search(child, [*path, index])
                    if found is not None:
                        return found
            return None

        found = search(self.root, [])
        if found is None:
            return False
        self.path = found
        return True


RECENT_LIMIT = 9


def recent_path() -> Path:
    return config_dir() / "recent_blocks.json"


def load_recent() -> list[str]:
    try:
        data = json.loads(recent_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    known = set(blocks.REGISTRY)
    return [b for b in data if isinstance(b, str) and b in known][:RECENT_LIMIT]


def block_label(block_id: str) -> str:
    return SHORT_NAMES.get(block_id, blocks.get(block_id).name.replace("_", " "))


def all_blocks(folder: Folder = INVENTORY, path: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    """Every block in the inventory with its folder path (``"Redstone › Switches"``)."""
    found: list[tuple[str, str]] = []
    for child in folder.children:
        if isinstance(child, Folder):
            found.extend(all_blocks(child, (*path, child.title)))
        else:
            found.append((child, " › ".join(path)))
    return found


def first_block(folder: Folder) -> str | None:
    """The block a folder shows as its icon (its first block, depth first)."""
    for child in folder.children:
        if isinstance(child, str):
            return child
        found = first_block(child)
        if found is not None:
            return found
    return None


@dataclass
class _Spot:
    """A clickable area of the inventory canvas."""

    rect: QRect
    kind: str  # "slot" (current level), "tab" (an upper level), "recent"
    depth: int
    index: int
    block: str | None
    title: str


class InventoryCanvas(QWidget):
    """The painted part of the inventory, Minecraft-style: the current folder as hotbar
    slots on top, each folder level above it as a row of tabs below, root at the bottom,
    so the stack grows upwards as you go deeper. The name of the chosen or hovered block
    floats above the slots like in the game. Recent blocks sit on the right."""

    SLOT = 46
    TAB = 26
    NAME = 22

    def __init__(self, bar: InventoryBar) -> None:
        super().__init__()
        self.bar = bar
        self.spots: list[_Spot] = []
        self.hovered: _Spot | None = None
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def rows_height(self) -> int:
        return self.NAME + self.SLOT + 8 + len(self.bar.nav.path) * (self.TAB + 4)

    def sizeHint(self) -> QSize:
        return QSize(800, self.rows_height())

    # ------------------------------------------------------------------ layout
    def _layout(self) -> list[_Spot]:
        nav = self.bar.nav
        spots: list[_Spot] = []
        x0 = 8
        top = self.NAME
        folder = nav.folder()
        for index, child in enumerate(folder.children):
            rect = QRect(x0 + index * (self.SLOT + 4), top, self.SLOT, self.SLOT)
            if isinstance(child, Folder):
                spots.append(
                    _Spot(rect, "slot", len(nav.path), index, first_block(child), child.title)
                )
            else:
                spots.append(_Spot(rect, "slot", len(nav.path), index, child, block_label(child)))
        # Upper levels as tab rows below the slots: the deepest parent first, root last.
        levels: list[tuple[int, Folder, int]] = []
        parent = nav.root
        for depth, chosen in enumerate(nav.path):
            levels.append((depth, parent, chosen))
            child = parent.children[chosen]
            assert isinstance(child, Folder)
            parent = child
        y = top + self.SLOT + 8
        for depth, level, _ in reversed(levels):
            x = x0
            for index, child in enumerate(level.children):
                title = child.title if isinstance(child, Folder) else block_label(child)
                block = first_block(child) if isinstance(child, Folder) else child
                width = QFontMetrics(self.font()).horizontalAdvance(title) + 40
                spots.append(_Spot(QRect(x, y, width, self.TAB), "tab", depth, index, block, title))
                x += width + 3
            y += self.TAB + 4
        # Recent blocks, right-aligned.
        recent = self.bar.recent
        size = 34
        x = self.width() - 8 - len(recent) * (size + 3)
        for index, block_id in enumerate(recent):
            rect = QRect(x + index * (size + 3), top + (self.SLOT - size) // 2, size, size)
            spots.append(_Spot(rect, "recent", -1, index, block_id, block_label(block_id)))
        return spots

    # ------------------------------------------------------------------ painting
    def paintEvent(self, event: object) -> None:
        self.spots = self._layout()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.PANEL))
        nav = self.bar.nav
        chosen_at = {depth: index for depth, index in enumerate(nav.path)}
        for spot in self.spots:
            hovered = self.hovered is not None and self.hovered.rect == spot.rect
            if spot.kind == "tab":
                self._paint_tab(painter, spot, chosen_at.get(spot.depth) == spot.index, hovered)
            else:
                selected = (
                    spot.block == self.bar.current
                    and spot.kind == "recent"
                    or (
                        spot.kind == "slot"
                        and isinstance(nav.folder().children[spot.index], str)
                        and spot.block == self.bar.current
                    )
                )
                self._paint_slot(painter, spot, selected, hovered)
        recent = [s for s in self.spots if s.kind == "recent"]
        if recent:
            label = "Recent"
            x = self.width() - theme.text_width(label) - 10
            theme.draw_text(painter, x, 3, label, theme.TEXT_DIM, 2, shadow=False)
        name = self.hovered.title if self.hovered is not None else self._current_name()
        if name:
            theme.draw_text(painter, 10, 3, name, theme.GOLD)
        painter.end()

    def _current_name(self) -> str:
        current = self.bar.current
        if current is None:
            return " › ".join(["Inventory", *self.bar.nav.breadcrumb()])
        return block_label(current)

    def _paint_slot(self, painter: QPainter, spot: _Spot, selected: bool, hovered: bool) -> None:
        r = spot.rect
        painter.fillRect(r, QColor(theme.SUNKEN))
        # Minecraft slot bevel: dark top/left, light bottom/right.
        painter.fillRect(QRect(r.left(), r.top(), r.width(), 2), QColor("#0b0b0c"))
        painter.fillRect(QRect(r.left(), r.top(), 2, r.height()), QColor("#0b0b0c"))
        painter.fillRect(QRect(r.left(), r.bottom() - 1, r.width(), 2), QColor(theme.LINE))
        painter.fillRect(QRect(r.right() - 1, r.top(), 2, r.height()), QColor(theme.LINE))
        if hovered:
            painter.fillRect(r.adjusted(2, 2, -2, -2), QColor(255, 255, 255, 28))
        if spot.block is not None:
            size = r.width() - 12
            painter.drawPixmap(r.left() + 6, r.top() + 6, block_pixmap(spot.block, size))
        if spot.kind == "slot":
            child = self.bar.nav.folder().children[spot.index]
            if isinstance(child, Folder):  # a folder: a small marker in the corner
                painter.fillRect(QRect(r.right() - 11, r.top() + 3, 9, 9), QColor(theme.ACCENT))
            number = str(spot.index + 1)
            theme.draw_text(
                painter, r.right() - theme.text_width(number) - 1, r.bottom() - 17, number
            )
        if selected:
            pen = QPen(QColor("#ffffff"), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r.adjusted(-1, -1, 0, 0))

    def _paint_tab(self, painter: QPainter, spot: _Spot, chosen: bool, hovered: bool) -> None:
        r = spot.rect
        background = (
            theme.ACCENT_SOFT if chosen else theme.WIDGET_HOVER if hovered else theme.WIDGET
        )
        painter.fillRect(r, QColor(background))
        if chosen:
            painter.fillRect(QRect(r.left(), r.bottom() - 1, r.width(), 2), QColor(theme.ACCENT))
        if spot.block is not None:
            painter.drawPixmap(r.left() + 5, r.top() + 4, block_pixmap(spot.block, 18))
        painter.setPen(QColor("#ffffff" if chosen else theme.TEXT))
        painter.drawText(r.adjusted(28, 0, 0, 0), int(Qt.AlignmentFlag.AlignVCenter), spot.title)

    # ------------------------------------------------------------------ input
    def _spot_at(self, point: QPoint) -> _Spot | None:
        return next((spot for spot in self.spots if spot.rect.contains(point)), None)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        spot = self._spot_at(event.position().toPoint())
        if spot != self.hovered:
            self.hovered = spot
            self.update()

    def leaveEvent(self, event: object) -> None:
        self.hovered = None
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        spot = self._spot_at(event.position().toPoint())
        if spot is None or event.button() != Qt.MouseButton.LeftButton:
            return
        if spot.kind == "slot":
            self.bar.press(spot.index + 1)
        elif spot.kind == "tab":
            self.bar.pick_at_level(spot.depth, spot.index)
        elif spot.block is not None:
            self.bar.select_block(blocks.get(spot.block))


class InventoryBar(QWidget):
    """The inventory: the painted hotbar and folder rows (``InventoryCanvas``), and on the
    right the search button and the source strength."""

    block_chosen = Signal(object)  # Block
    search_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.nav = InventoryNav()
        self.current: str | None = None
        self.recent: list[str] = load_recent()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(6)
        self.canvas = InventoryCanvas(self)
        layout.addWidget(self.canvas, 1)
        side = QVBoxLayout()
        side.setSpacing(4)
        side.setContentsMargins(0, 6, 0, 6)
        search = QToolButton()
        search.setText("🔍  Search blocks")
        search.setToolTip("Search blocks by name (Ctrl+Space, /, or press Shift twice)")
        search.clicked.connect(self.search_requested.emit)
        side.addWidget(search)
        self.strength_label = QLabel("Source strength")
        side.addWidget(self.strength_label)
        self.strength = QSpinBox()
        self.strength.setRange(0, 15)
        self.strength.setValue(15)
        self.strength.setToolTip(
            "Comparator reading of placed signal sources. The block is set up for it: "
            "barrels get the fewest items, lecterns a 15-page book open at the right page, "
            "cakes the matching bites (even values only)."
        )
        side.addWidget(self.strength)
        side.addStretch(1)
        layout.addLayout(side)
        self.refresh()

    def refresh(self) -> None:
        self.canvas.setFixedHeight(self.canvas.rows_height())
        self.canvas.update()
        is_source = self.current in sources.SOURCE_BLOCKS
        self.strength_label.setVisible(is_source)
        self.strength.setVisible(is_source)

    # ------------------------------------------------------------------ navigation
    def press(self, number: int) -> None:
        block_id = self.nav.press(number)
        if block_id is not None:
            self.current = block_id
            self._fit_strength(block_id)
            self.block_chosen.emit(blocks.get(block_id))
        self.refresh()

    def go_to_depth(self, depth: int) -> None:
        if depth < len(self.nav.path) + 1:
            self.nav.path = self.nav.path[:depth]
            self.refresh()

    def pick_at_level(self, depth: int, index: int) -> None:
        """A tab of an upper level: open that folder there, or choose that block."""
        self.nav.path = self.nav.path[:depth]
        self.press(index + 1)

    _pick_at_level = pick_at_level

    def _fit_strength(self, block_id: str) -> None:
        """The strength box offers what the chosen source can give (cakes: even 2-14)."""
        kind = sources.SOURCE_BLOCKS.get(block_id)
        if kind is None:
            return
        values = sources.KINDS[kind].strengths
        step = values[1] - values[0] if len(values) > 1 else 1
        self.strength.setRange(values[0], values[-1])
        self.strength.setSingleStep(step)
        self.strength.setValue(sources.nearest_strength(kind, self.strength.value()))

    def go_up(self) -> None:
        if self.nav.up():
            self.refresh()

    def select_block(self, block: Block) -> None:
        """Show and highlight ``block`` (after a pick or search) and choose it."""
        self.nav.reveal(block.id)
        self.current = block.id
        self._fit_strength(block.id)
        self.refresh()
        self.block_chosen.emit(block)

    def remember(self, block_id: str) -> None:
        """A block was placed: it goes to the front of the recent list (saved)."""
        if self.recent[:1] == [block_id]:
            return
        self.recent = [block_id, *(b for b in self.recent if b != block_id)][:RECENT_LIMIT]
        try:
            path = recent_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.recent) + "\n", encoding="utf-8")
        except OSError:
            pass
        self.refresh()
