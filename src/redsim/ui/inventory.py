"""Trackmania-style inventory bar: hierarchical folders at the bottom, navigated by numbers.

Number keys open the folder (or pick the block) with that number; Backspace goes up one
level, and every level of the folder path above the tiles is a button. Tiles show a preview
of the block (``icons``). Recently placed blocks sit at the top right (saved in
``recent_blocks.json`` next to the preferences). Choosing a block enters BUILD mode
(``block_chosen``). The folder tree is plain data (``INVENTORY``), so new blocks only need a
line here; folders can nest when one grows past nine entries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from redsim.editor import sources
from redsim.ui.icons import block_icon
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


class InventoryBar(QWidget):
    """The bar: the folder path (click a level to go back), recently used blocks, and the
    numbered tiles of the current folder with block previews; source strength."""

    block_chosen = Signal(object)  # Block
    search_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.nav = InventoryNav()
        self.current: str | None = None
        self.recent: list[str] = load_recent()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 2, 6, 2)
        outer.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(2)
        outer.addLayout(top)
        self.back = QToolButton()
        self.back.setText("⌫")
        self.back.setToolTip("Up one folder (Backspace)")
        self.back.clicked.connect(self.go_up)
        top.addWidget(self.back)
        self.path_row = QHBoxLayout()
        self.path_row.setSpacing(0)
        top.addLayout(self.path_row)
        top.addStretch(1)
        search = QToolButton()
        search.setText("🔍 Search")
        search.setToolTip("Search blocks by name (Ctrl+Space, /, or press Shift twice)")
        search.clicked.connect(self.search_requested.emit)
        top.addWidget(search)
        top.addSpacing(10)
        top.addWidget(QLabel("Recent:"))
        self.recent_row = QHBoxLayout()
        self.recent_row.setSpacing(2)
        top.addLayout(self.recent_row)
        top.addSpacing(10)
        self.strength_label = QLabel("Source strength")
        top.addWidget(self.strength_label)
        self.strength = QSpinBox()
        self.strength.setRange(0, 15)
        self.strength.setValue(15)
        self.strength.setToolTip(
            "Comparator reading of placed signal sources. The block is set up for it: "
            "barrels get the fewest items, lecterns a 15-page book open at the right page, "
            "cakes the matching bites (even values only)."
        )
        top.addWidget(self.strength)
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
        scroller.setFixedHeight(TILE_HEIGHT + 14)  # tiles plus a horizontal scrollbar
        outer.addWidget(scroller)
        self._tiles: list[QWidget] = []
        self._path_widgets: list[QWidget] = []
        self._recent_widgets: list[QWidget] = []
        self.refresh()

    # ------------------------------------------------------------------ display
    def _clear(self, layout: QHBoxLayout, widgets: list[QWidget]) -> None:
        for widget in widgets:
            layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        widgets.clear()

    def refresh(self) -> None:
        self._clear(self.tiles_row, self._tiles)
        self._clear(self.path_row, self._path_widgets)
        self._clear(self.recent_row, self._recent_widgets)
        self._build_path()
        self._build_recent()
        self.back.setEnabled(bool(self.nav.path))
        for number, child in enumerate(self.nav.folder().children, start=1):
            tile = QToolButton()
            tile.setAutoRaise(False)
            tile.setFixedHeight(TILE_HEIGHT)
            tile.setMinimumWidth(64)
            if isinstance(child, Folder):
                tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                tile.setIcon(folder_icon(child))
                tile.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
                tile.setText(f"{number}  {child.title} ›")
                tile.setToolTip(f"Open {child.title} ({number})")
            else:
                tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                tile.setIcon(block_icon(blocks.get(child), ICON_SIZE))
                tile.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
                tile.setText(f"{number}  {block_label(child)}")
                kind = sources.SOURCE_BLOCKS.get(child)
                tile.setToolTip(sources.KINDS[kind].tooltip if kind else child)
                tile.setCheckable(True)
                tile.setChecked(child == self.current)
            tile.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            tile.clicked.connect(lambda _=False, n=number: self.press(n))
            self.tiles_row.insertWidget(self.tiles_row.count() - 1, tile)
            self._tiles.append(tile)
        is_source = self.current in sources.SOURCE_BLOCKS
        self.strength_label.setVisible(is_source)
        self.strength.setVisible(is_source)

    def _build_path(self) -> None:
        """``Inventory › Redstone › Switches``: every level is a button that goes there."""
        crumbs = ["Inventory", *self.nav.breadcrumb()]
        for depth, title in enumerate(crumbs):
            if depth:
                arrow = QLabel("›")
                self.path_row.addWidget(arrow)
                self._path_widgets.append(arrow)
            button = QToolButton()
            button.setAutoRaise(True)
            button.setText(title)
            last = depth == len(crumbs) - 1
            button.setStyleSheet("font-weight: bold;" if last else "")
            button.setToolTip("Current folder" if last else f"Back to {title}")
            button.clicked.connect(lambda _=False, d=depth: self.go_to_depth(d))
            self.path_row.addWidget(button)
            self._path_widgets.append(button)

    def _build_recent(self) -> None:
        for block_id in self.recent:
            button = QToolButton()
            button.setAutoRaise(True)
            button.setIcon(block_icon(blocks.get(block_id), 22))
            button.setIconSize(QSize(22, 22))
            button.setToolTip(f"{block_label(block_id)} (recently used)")
            button.setCheckable(True)
            button.setChecked(block_id == self.current)
            button.clicked.connect(lambda _=False, b=block_id: self.select_block(blocks.get(b)))
            self.recent_row.addWidget(button)
            self._recent_widgets.append(button)

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


def folder_icon(folder: Folder) -> QIcon:
    """A folder tile shows its first block."""
    first: Folder | str = folder
    while isinstance(first, Folder) and first.children:
        first = first.children[0]
    return block_icon(blocks.get(first), ICON_SIZE) if isinstance(first, str) else QIcon()
