"""Trackmania-style inventory bar: hierarchical folders at the bottom, navigated by numbers.

Number keys open the folder (or pick the block) with that number; Backspace goes up one
level. Choosing a block enters BUILD mode (``block_chosen``). The folder tree is plain data
(``INVENTORY``), so new blocks only need a line here; folders can nest when one grows past
nine entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QWidget,
)

from redsim.editor import sources
from redsim.ui.style import block_boxes
from redsim.world import blocks
from redsim.world.block import Block


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


def block_icon(block: Block, size: int = 22) -> QIcon:
    """A swatch in the block's main color (presentation only)."""
    boxes = block_boxes(block.default_state)
    color = QColor.fromRgbF(*boxes[0].color[:3]) if boxes else QColor(128, 128, 128)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(color)
    painter.setPen(color.darker(160))
    painter.drawRoundedRect(1, 1, size - 3, size - 3, 4, 4)
    painter.end()
    return QIcon(pixmap)


class InventoryBar(QWidget):
    """The bar: breadcrumb, numbered tiles of the current folder, source strength."""

    block_chosen = Signal(object)  # Block

    def __init__(self) -> None:
        super().__init__()
        self.nav = InventoryNav()
        self.current: str | None = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        self.back = QToolButton()
        self.back.setText("⌫")
        self.back.setToolTip("Up one folder (Backspace)")
        self.back.clicked.connect(self.go_up)
        layout.addWidget(self.back)
        self.crumb = QLabel()
        self.crumb.setMinimumWidth(150)
        self.crumb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.crumb)
        tiles = QWidget()
        self.tiles_row = QHBoxLayout(tiles)
        self.tiles_row.setContentsMargins(0, 0, 0, 0)
        self.tiles_row.setSpacing(4)
        self.tiles_row.addStretch(1)
        scroller = QScrollArea()  # never let nine tiles force the window wider
        scroller.setWidget(tiles)
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.Shape.NoFrame)
        scroller.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroller.setFixedHeight(52)  # tiles plus a horizontal scrollbar when needed
        layout.addWidget(scroller, 1)
        self.strength_label = QLabel("Source strength")
        layout.addWidget(self.strength_label)
        self.strength = QSpinBox()
        self.strength.setRange(0, 15)
        self.strength.setValue(15)
        self.strength.setToolTip(
            "Comparator reading of placed signal sources. The block is set up for it: "
            "barrels get the fewest items, lecterns a 15-page book open at the right page, "
            "cakes the matching bites (even values only)."
        )
        layout.addWidget(self.strength)
        self._tiles: list[QToolButton] = []
        self.refresh()

    def refresh(self) -> None:
        for tile in self._tiles:
            self.tiles_row.removeWidget(tile)
            tile.setParent(None)
            tile.deleteLater()
        self._tiles = []
        crumbs = ["Inventory", *self.nav.breadcrumb()]
        self.crumb.setText(" › ".join(f"<b>{c}</b>" if c == crumbs[-1] else c for c in crumbs))
        self.back.setEnabled(bool(self.nav.path))
        for number, child in enumerate(self.nav.folder().children, start=1):
            tile = QToolButton()
            tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            tile.setAutoRaise(False)
            if isinstance(child, Folder):
                tile.setText(f"{number}  {child.title} ›")
                tile.setToolTip(f"Open {child.title} ({number})")
            else:
                block = blocks.get(child)
                tile.setIcon(block_icon(block))
                tile.setIconSize(QSize(22, 22))
                tile.setText(f"{number}  {SHORT_NAMES.get(child, block.name.replace('_', ' '))}")
                kind = sources.SOURCE_BLOCKS.get(child)
                tile.setToolTip(sources.KINDS[kind].tooltip if kind else block.name)
                tile.setCheckable(True)
                tile.setChecked(child == self.current)
            tile.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            tile.clicked.connect(lambda _=False, n=number: self.press(n))
            self.tiles_row.insertWidget(self.tiles_row.count() - 1, tile)
            self._tiles.append(tile)
        in_sources = self.nav.breadcrumb()[-1:] == ["Signal sources"]
        self.strength_label.setVisible(in_sources)
        self.strength.setVisible(in_sources)

    def press(self, number: int) -> None:
        block_id = self.nav.press(number)
        if block_id is not None:
            self.current = block_id
            self._fit_strength(block_id)
            self.block_chosen.emit(blocks.get(block_id))
        self.refresh()

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
        """Show and highlight ``block`` (after a pick) and choose it."""
        self.nav.reveal(block.id)
        self.current = block.id
        self._fit_strength(block.id)
        self.refresh()
        self.block_chosen.emit(block)
