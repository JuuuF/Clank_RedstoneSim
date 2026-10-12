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
from functools import cache
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
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
from redsim.ui import pixel_icons, theme
from redsim.ui.assets import Assets
from redsim.ui.icons import block_pixmap
from redsim.ui.names import block_name
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
                "minecraft:redstone_block",
                "minecraft:target",
                Folder(
                    "Switches",
                    (
                        "minecraft:lever",
                        "minecraft:stone_button",
                        "minecraft:oak_button",
                        "minecraft:stone_pressure_plate",
                        "minecraft:oak_pressure_plate",
                        "minecraft:light_weighted_pressure_plate",
                        "minecraft:heavy_weighted_pressure_plate",
                    ),
                ),
                Folder(
                    "Outputs",
                    ("minecraft:redstone_lamp", "minecraft:copper_bulb", "minecraft:note_block"),
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
        Folder(
            "Items",
            (
                "minecraft:hopper",
                "minecraft:dropper",
                "minecraft:dispenser",
                "minecraft:chest",
                "minecraft:trapped_chest",
            ),
        ),
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
#: Recent slots shown even before anything was placed (so the strip can be found).
RECENT_SHOWN = 5


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
    """The name the game shows ("Redstone Dust")."""
    return block_name(block_id)


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
    kind: str  # "slot": a folder level's row
    depth: int
    index: int
    block: str | None
    title: str


#: Opacity the chosen block's name fades to above the hotbar.
NAME_FADED = 0.35
#: Slots per row, like the game's hotbar; rows with fewer entries end in empty slots.
HOTBAR_SLOTS = 9


@cache
def hud_sprite(name: str) -> QPixmap | None:
    """One of the game's HUD sprites (``hotbar``, ``hotbar_selection``) at 2×, from the
    client jar; None without it."""
    assets = Assets.find()
    path = f"assets/minecraft/textures/gui/sprites/hud/{name}.png"
    data = assets.file_bytes(path) if assets is not None else None
    image = QImage.fromData(data) if data else QImage()
    if image.isNull():
        return None
    return QPixmap.fromImage(
        image.scaled(
            image.width() * 2,
            image.height() * 2,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
    )


class InventoryCanvas(QWidget):
    """The painted part of the inventory, Minecraft-style hotbar rows: one row of slots per
    folder level, all alike. The root row stays at the bottom; opening a folder adds its
    row above, so the stack grows upwards and nothing changes its look. The open folder
    of each lower row is framed; number keys act on the top row (marked by a red bar). The
    name of the chosen or hovered block floats above, like in the game; recent blocks sit
    on the right."""

    SLOT = 40  # the game's hotbar at 2×: 20-pixel slots
    GAP = 6
    NAME = 22
    X0 = 16  # left edge of the first slot (the hotbar sprite starts 2 pixels earlier)

    def __init__(self, bar: InventoryBar) -> None:
        super().__init__()
        self.bar = bar
        self.spots: list[_Spot] = []
        self.hovered: _Spot | None = None
        self.setMouseTracking(True)
        # The chosen block's name fades after a while, like the held item's name in the
        # game (to NAME_FADED, so it stays readable); hovered names show at full strength.
        self._name_shown = ""
        self.name_alpha = 1.0
        #: Height during a row's slide (opening or closing a folder), else None.
        self.animated_height: int | None = None
        self._grow = QVariantAnimation(self)
        self._grow.setDuration(120)
        self._grow.valueChanged.connect(self._set_height)
        self._grow.finished.connect(self._grown)
        self._fade = QVariantAnimation(self)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(NAME_FADED)
        self._fade.setDuration(500)
        self._fade.valueChanged.connect(self._set_name_alpha)
        self._fade_delay = QTimer(self)
        self._fade_delay.setSingleShot(True)
        self._fade_delay.setInterval(2000)
        self._fade_delay.timeout.connect(self._fade.start)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def shown_height(self) -> int:
        """The height being shown: while a row slides in or out, the animated one."""
        return self.animated_height or self.rows_height()

    def rows_height(self) -> int:
        return self.NAME + (len(self.bar.nav.path) + 1) * (self.SLOT + self.GAP) + 4

    def sizeHint(self) -> QSize:
        return QSize(self.X0 + HOTBAR_SLOTS * self.SLOT + 6, self.rows_height())

    def _levels(self) -> list[tuple[int, Folder]]:
        """(depth, folder) from the root to the open folder."""
        levels = [(0, self.bar.nav.root)]
        folder = self.bar.nav.root
        for depth, chosen in enumerate(self.bar.nav.path, start=1):
            child = folder.children[chosen]
            assert isinstance(child, Folder)
            levels.append((depth, child))
            folder = child
        return levels

    # ------------------------------------------------------------------ layout
    def _layout(self) -> list[_Spot]:
        spots: list[_Spot] = []
        bottom = self.shown_height() - 4
        for depth, folder in self._levels():  # the root lowest, deeper rows above
            top = bottom - (depth + 1) * (self.SLOT + self.GAP) + self.GAP
            for index, child in enumerate(folder.children):
                rect = QRect(self.X0 + index * self.SLOT, top, self.SLOT, self.SLOT)
                if isinstance(child, Folder):
                    spots.append(_Spot(rect, "slot", depth, index, first_block(child), child.title))
                else:
                    spots.append(_Spot(rect, "slot", depth, index, child, block_label(child)))
        return spots

    # ------------------------------------------------------------------ painting
    def paintEvent(self, event: object) -> None:
        self.spots = self._layout()
        painter = QPainter(self)
        # Drawn over the 3D view like the game's hotbar: no background of its own.
        path = self.bar.nav.path
        active = len(path)
        bottom = self.shown_height() - 4
        hotbar = hud_sprite("hotbar")
        sprite = hotbar is not None
        for depth in range(len(self.bar.nav.path) + 1):  # each row: a whole 9-slot hotbar
            top = bottom - (depth + 1) * (self.SLOT + self.GAP) + self.GAP
            if hotbar is not None:  # the game's own hotbar
                painter.drawPixmap(self.X0 - 2, top - 2, hotbar)
                continue
            for index in range(HOTBAR_SLOTS):
                rect = QRect(self.X0 + index * self.SLOT, top, self.SLOT, self.SLOT)
                theme.paint_slot(painter, rect.adjusted(1, 1, -1, -1))
        for spot in self.spots:
            hovered = self.hovered is not None and self.hovered.rect == spot.rect
            child = self._levels()[spot.depth][1].children[spot.index]
            if isinstance(child, Folder):
                selected = spot.depth < active and path[spot.depth] == spot.index
            else:
                selected = child == self.bar.current
            number = spot.index + 1 if spot.depth == active else None
            self._paint_slot(
                painter, spot, selected, hovered, number, isinstance(child, Folder), sprite
            )
        top_row = [s for s in self.spots if s.kind == "slot" and s.depth == active]
        if top_row:  # the row the number keys act on
            r = top_row[0].rect
            painter.fillRect(QRect(4, r.top(), 3, r.height()), QColor(theme.ACCENT))
        name = self.hovered.title if self.hovered is not None else self._current_name()
        if self.hovered is None and name != self._name_shown:  # a new choice: show it
            self._name_shown = name
            self._fade.stop()
            self.name_alpha = 1.0
            self._fade_delay.start()
        if name:
            painter.setOpacity(1.0 if self.hovered is not None else self.name_alpha)
            theme.draw_text(painter, 14, 3, name, theme.GOLD)
            painter.setOpacity(1.0)
        painter.end()

    def resize_rows(self) -> None:
        """Fit the rows: slide to the new height when visible, else jump."""
        target = self.rows_height()
        if not self.isVisible() or self.height() in (0, target):
            self._grow.stop()
            self.animated_height = None
            self.setFixedHeight(target)
            return
        self._grow.stop()
        self._grow.setStartValue(self.height())
        self._grow.setEndValue(target)
        self._grow.start()

    def _set_height(self, value: object) -> None:
        self.animated_height = int(value)  # type: ignore[call-overload]
        self.setFixedHeight(self.animated_height)

    def _grown(self) -> None:
        self.animated_height = None
        self.setFixedHeight(self.rows_height())
        self.update()

    def _set_name_alpha(self, value: object) -> None:
        self.name_alpha = float(value)  # type: ignore[arg-type]
        self.update()

    def _current_name(self) -> str:
        current = self.bar.current
        if current is None:
            return " › ".join(["Inventory", *self.bar.nav.breadcrumb()])
        return block_label(current)

    def _paint_slot(
        self,
        painter: QPainter,
        spot: _Spot,
        selected: bool,
        hovered: bool,
        number: int | None,
        folder: bool = False,
        sprite: bool = False,
    ) -> None:
        """One slot; ``sprite``: drawn on the game's hotbar sprite (it has the frames)."""
        r = spot.rect
        if not sprite:
            theme.paint_slot(painter, r.adjusted(1, 1, -1, -1))
        if hovered:  # the game's slot highlight: white over the item area
            painter.fillRect(r.adjusted(4, 4, -4, -4), QColor(255, 255, 255, 60))
        if spot.block is not None:
            size = r.width() - 8
            painter.drawPixmap(r.left() + 4, r.top() + 4, block_pixmap(spot.block, size))
        if folder:  # opening it adds a row above: a small up chevron
            color = QColor(theme.ACCENT if selected else theme.GOLD)
            x, y = r.right() - 9, r.top() + 4
            for row in range(3):
                painter.fillRect(QRect(x + 3 - row, y + row, 1 + 2 * row, 1), color)
        if number is not None:  # the number key, as a small key cap
            text = str(number)
            width = theme.text_width(text, 1)
            cap = QRect(r.left() + 2, r.bottom() - 10, width + 5, 10)
            painter.fillRect(cap, QColor(0, 0, 0, 170))
            theme.draw_text(painter, cap.left() + 3, cap.top() + 2, text, theme.TEXT, 1, False)
        selection = hud_sprite("hotbar_selection") if sprite else None
        if selected and selection is not None:
            painter.drawPixmap(r.left() - 4, r.top() - 4, selection)
        elif selected:
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r.adjusted(0, 0, -1, -1))

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
        self.bar.pick_at_level(spot.depth, spot.index)


class RecentStrip(QWidget):
    """The blocks placed last, as a short hotbar next to the inventory (Alt+1–9 pick
    them). Always shown in BUILD mode, with empty slots and a hint until something is
    placed, so it is easy to find."""

    SLOT = InventoryCanvas.SLOT
    LABEL = 14  # the "RECENT" label above the slots

    def __init__(self, bar: InventoryBar) -> None:
        super().__init__()
        self.bar = bar
        self.hovered: int | None = None
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def slots(self) -> int:
        return max(RECENT_SHOWN, len(self.bar.recent))

    def sizeHint(self) -> QSize:
        return QSize(self.slots() * self.SLOT + 6, self.LABEL + self.SLOT + 4)

    def _rect(self, index: int) -> QRect:
        return QRect(2 + index * self.SLOT, self.LABEL + 2, self.SLOT, self.SLOT)

    def slot_at(self, point: QPoint) -> int | None:
        return next((i for i in range(self.slots()) if self._rect(i).contains(point)), None)

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        theme.draw_text(painter, 2, 1, "RECENT", theme.GOLD, 1)
        hotbar = hud_sprite("hotbar")
        count = self.slots()
        if hotbar is not None:  # a piece of the game's hotbar, with its right end
            width = 2 + self.SLOT * count
            painter.drawPixmap(0, self.LABEL, hotbar, 0, 0, width, hotbar.height())
            painter.drawPixmap(width, self.LABEL, hotbar, hotbar.width() - 2, 0, 2, hotbar.height())
        selection = hud_sprite("hotbar_selection")
        for index in range(count):
            r = self._rect(index)
            if hotbar is None:
                theme.paint_slot(painter, r.adjusted(1, 1, -1, -1))
            if index == self.hovered:
                painter.fillRect(r.adjusted(4, 4, -4, -4), QColor(255, 255, 255, 60))
            if index >= len(self.bar.recent):
                continue
            block_id = self.bar.recent[index]
            painter.drawPixmap(r.left() + 4, r.top() + 4, block_pixmap(block_id, r.width() - 8))
            if block_id == self.bar.current and selection is not None:
                painter.drawPixmap(r.left() - 4, r.top() - 4, selection)
        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        index = self.slot_at(event.position().toPoint())
        if index != self.hovered:
            self.hovered = index
            self.update()
        if index is not None and index < len(self.bar.recent):
            self.setToolTip(f"{block_label(self.bar.recent[index])} (Alt+{index + 1})")
        else:
            self.setToolTip("The blocks you place appear here; Alt+1–9 picks them.")

    def leaveEvent(self, event: object) -> None:
        self.hovered = None
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        index = self.slot_at(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and index is not None:
            self.bar.pick_recent(index)


class InventoryBar(QWidget):
    """The inventory, drawn over the bottom of the 3D view in BUILD mode like the game's
    hotbar: the folder rows (``InventoryCanvas``), and on the right the recent blocks
    (``RecentStrip``), the search button and the source strength."""

    block_chosen = Signal(object)  # Block
    search_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.nav = InventoryNav()
        self.current: str | None = None
        self.recent: list[str] = load_recent()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.canvas = InventoryCanvas(self)
        layout.addWidget(self.canvas, 0, Qt.AlignmentFlag.AlignBottom)
        side = QVBoxLayout()
        side.setSpacing(4)
        side.setContentsMargins(0, 0, 0, 4)
        side.addStretch(1)
        self.recent_strip = RecentStrip(self)
        side.addWidget(self.recent_strip)
        tools = QHBoxLayout()
        tools.setSpacing(6)
        search = QToolButton()
        search.setText("Search blocks")
        search.setIcon(pixel_icons.pixel_icon("search"))
        search.setIconSize(pixel_icons.ICON_SIZE)
        search.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        search.setToolTip("Search blocks by name (Ctrl+Space, /, or press Shift twice)")
        search.clicked.connect(self.search_requested.emit)
        tools.addWidget(search)
        self.strength_label = QLabel("Strength")
        tools.addWidget(self.strength_label)
        self.strength = QSpinBox()
        self.strength.setRange(0, 15)
        self.strength.setValue(15)
        self.strength.setToolTip(
            "Comparator reading of placed signal sources. The block is set up for it: "
            "barrels get the fewest items, lecterns a 15-page book open at the right page, "
            "cakes the matching bites (even values only)."
        )
        tools.addWidget(self.strength)
        tools.addStretch(1)
        side.addLayout(tools)
        layout.addLayout(side)
        self.refresh()

    def refresh(self) -> None:
        self.canvas.resize_rows()
        self.canvas.update()
        self.recent_strip.updateGeometry()
        self.recent_strip.update()
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

    def pick_recent(self, index: int) -> None:
        """Choose the ``index``-th recently placed block (Alt+1–9, or a click)."""
        if 0 <= index < len(self.recent):
            self.select_block(blocks.get(self.recent[index]))

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
