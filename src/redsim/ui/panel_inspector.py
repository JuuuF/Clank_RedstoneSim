"""The Inspector tab (and the E block popup): the chosen block's state, signal source,
projectile hits, pressure-plate visitors, container contents, sign text, section and
monitor."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.editor.document import Document
from redsim.ui import pixel_icons, theme
from redsim.ui.icons import block_pixmap
from redsim.ui.names import block_name
from redsim.ui.panel_widgets import (
    CONTAINER_ITEMS,
    NO_SELECTION,
    ContainerGrid,
    FlowLayout,
    HoverWatch,
    _Choice,
    _later,
    _Stepper,
    _Toggle,
)
from redsim.world import blocks
from redsim.world.block import BlockState
from redsim.world.blocks.container import ContainerBlockEntity, slot_limit
from redsim.world.blocks.sign import LINES, SignBlockEntity
from redsim.world.properties import Property

#: Characters per sign line the fields take (the game limits a line by its width: 90
#: font pixels, about 15 wide letters).
SIGN_LINE_LENGTH = 50


class InspectorPanel(QWidget):
    """The selected block. Every control applies at once, as a /setblock edit (one undo
    step each); widgets are updated in place while the same kind of block stays selected."""

    apply_requested = Signal(object, object)  # Pos, BlockState
    section_requested = Signal(object, object)  # Pos, str | None
    source_requested = Signal(object, str, int)  # Pos, kind, strength
    page_requested = Signal(object, int)  # Pos, page (a player turning the page)
    monitor_requested = Signal(object)  # Pos: add/remove on the timeline monitor
    hit_requested = Signal(object, int, bool)  # Pos, strength, arrow
    plate_requested = Signal(object, int, int, int)  # Pos, mobs, others, ticks
    contents_requested = Signal(object, object, object, int)  # Pos, slot|None, item|None, n
    sign_requested = Signal(object, str, list)  # Pos, "front" | "back", the 4 lines
    position_hovered = Signal(object)  # Pos | None: the title (coordinates) is hovered

    def __init__(self) -> None:
        super().__init__()
        self._pos: Pos | None = None
        self._state: BlockState | None = None
        self._layout_key: tuple[Any, ...] | None = None
        self._editors: dict[str, Any] = {}
        self._page: int | None = None
        layout = QVBoxLayout(self)
        title_row = QHBoxLayout()
        self.icon = QLabel()
        self.icon.setFixedSize(36, 36)
        title_row.addWidget(self.icon)
        self.title = QLabel(NO_SELECTION)
        self.title.setWordWrap(True)
        self.title.setToolTip("Hover: the block lights up in the view")
        for hover_target in (self.title, self.icon):
            HoverWatch(
                hover_target,
                lambda: self.position_hovered.emit(self._pos),
                lambda: self.position_hovered.emit(None),
            )
        title_row.addWidget(self.title, 1)
        self.monitor = QPushButton("Monitor")
        self.monitor.setIcon(pixel_icons.pixel_icon("monitor"))
        self.monitor.setIconSize(pixel_icons.ICON_SIZE)
        self.monitor.setCheckable(True)
        self.monitor.setToolTip("Show this block's value per tick on the timeline")
        self.monitor.clicked.connect(lambda: self._pos and self.monitor_requested.emit(self._pos))
        title_row.addWidget(self.monitor)
        layout.addLayout(title_row)
        layout.addSpacing(6)
        self.form_widget = QWidget()
        self.form = QFormLayout(self.form_widget)
        self.form.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.form_widget)
        self.entity = QLabel("")
        self.entity.setWordWrap(True)
        self.entity.setStyleSheet(f"color: {theme.TEXT_DIM};")
        layout.addWidget(self.entity)
        self.note = QLabel(
            f"<small style='color:{theme.TEXT_DIM}'>Edits apply at once with /setblock "
            "semantics (state adjusted by neighbor shapes, then neighbor updates). Right "
            "click in NORMAL mode uses a block like a player instead.</small>"
        )
        self.note.setWordWrap(True)
        self.source_box = QWidget()
        source_layout = self._source_form = QFormLayout(self.source_box)
        source_layout.setContentsMargins(0, 6, 0, 0)
        self.source_kind = QWidget()
        kind_layout = FlowLayout(self.source_kind)  # six kinds: they wrap
        self.kind_buttons: dict[str, QPushButton] = {}
        for kind in sources.KINDS.values():
            button = QPushButton(kind.id.capitalize())
            button.setIcon(QIcon(block_pixmap(kind.block_id, 16)))
            button.setCheckable(True)
            button.setToolTip(kind.tooltip)
            button.clicked.connect(lambda _=False, k=kind.id: self._pick_source(k, None))
            kind_layout.addWidget(button)
            self.kind_buttons[kind.id] = button
        source_layout.addRow("Signal source", self.source_kind)
        self.source_strength = _Stepper(
            tuple(range(16)),
            lambda value: self._pick_source(None, int(value)),
            "Strength as a comparator reads it (the block is set up for it)",
        )
        source_layout.addRow("Strength", self.source_strength)
        self.page_row = QWidget()
        page_layout = QHBoxLayout(self.page_row)
        page_layout.setContentsMargins(0, 0, 0, 0)
        self.page_back = QPushButton("Page")
        self.page_back.setIcon(pixel_icons.pixel_icon("less"))
        self.page_next = QPushButton("Page")
        self.page_next.setIcon(pixel_icons.pixel_icon("more"))
        self.page_next.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # icon after text
        for button, step in ((self.page_back, -1), (self.page_next, 1)):
            button.setToolTip(
                "Turn the page like a player: the signal changes and the lectern sends a "
                "2-tick pulse into the block below (verified from the game source)."
            )
            button.clicked.connect(lambda _=False, d=step: self._turn_page(d))
            page_layout.addWidget(button)
        source_layout.addRow("Player", self.page_row)
        layout.addWidget(self.source_box)
        self.target_box = QWidget()
        target_layout = QFormLayout(self.target_box)
        target_layout.setContentsMargins(0, 6, 0, 0)
        self.hit_strength = _Stepper(tuple(range(1, 16)), self._pick_hit_strength, "Hit strength")
        self.hit_strength.show_value(15)
        target_layout.addRow("Hit strength", self.hit_strength)
        hit_row = QWidget()
        hit_layout = QHBoxLayout(hit_row)
        hit_layout.setContentsMargins(0, 0, 0, 0)
        self.hit_buttons: dict[bool, QPushButton] = {}  # arrow? → button
        for text, arrow, tip in (
            ("Arrow", True, "An arrow hits the target: power for 20 ticks"),
            ("Snowball", False, "Another projectile hits the target: power for 8 ticks"),
        ):
            button = QPushButton(text)
            button.setIcon(pixel_icons.pixel_icon(text.lower()))
            button.setIconSize(pixel_icons.ICON_SIZE)
            button.setToolTip(tip + " (it lands in the next tick's entity phase)")
            button.clicked.connect(lambda _=False, a=arrow: self._hit(a))
            hit_layout.addWidget(button)
            self.hit_buttons[arrow] = button
        target_layout.addRow("Projectile", hit_row)
        layout.addWidget(self.target_box)
        self.plate_box = QWidget()  # pressure plates: entities standing on them
        plate_layout = QFormLayout(self.plate_box)
        plate_layout.setContentsMargins(0, 6, 0, 0)
        self.plate_mobs = QSpinBox()
        self.plate_mobs.setRange(0, 150)
        self.plate_mobs.setValue(1)
        self.plate_mobs.setToolTip("Players and other mobs (stone plates react only to these)")
        plate_layout.addRow("Players/mobs", self.plate_mobs)
        self.plate_items = QSpinBox()
        self.plate_items.setRange(0, 150)
        self.plate_items.setToolTip("Items and other entities (wooden and weighted plates)")
        plate_layout.addRow("Items", self.plate_items)
        self.plate_ticks = QSpinBox()
        self.plate_ticks.setRange(1, 100000)
        self.plate_ticks.setValue(20)
        self.plate_ticks.setSuffix(" ticks")
        self.plate_ticks.setToolTip("How long they stand on it (from the next tick on)")
        plate_layout.addRow("For", self.plate_ticks)
        self.plate_step = QPushButton("Step on it")
        self.plate_step.setToolTip(
            "Entities are not simulated: they stand on the plate from the next tick on; it "
            "presses in that tick's entity phase and releases at its next recheck (20 ticks, "
            "10 for weighted plates) after they leave."
        )
        self.plate_step.clicked.connect(self._step_on_plate)
        plate_layout.addRow("", self.plate_step)
        layout.addWidget(self.plate_box)
        self.contents_box = QWidget()
        contents_layout = QFormLayout(self.contents_box)
        contents_layout.setContentsMargins(0, 6, 0, 0)
        self.contents_label = QLabel("")  # a summary: filled slots and items
        self.contents_label.setStyleSheet(f"color: {theme.TEXT_DIM};")
        contents_layout.addRow("Contents", self.contents_label)
        self.contents_grid = ContainerGrid()
        self.contents_grid.slot_clicked.connect(self._pick_slot)
        contents_layout.addRow(self.contents_grid)
        slot_row = QWidget()
        slot_layout = QHBoxLayout(slot_row)
        slot_layout.setContentsMargins(0, 0, 0, 0)
        self.slot_box = QSpinBox()
        self.slot_box.setToolTip("Slot number (0-based, as in the game's NBT)")
        self.item_box = QComboBox()
        for item, label in CONTAINER_ITEMS:
            self.item_box.addItem(label, item)
        self.item_box.currentIndexChanged.connect(self._fit_count)
        self.count_box = QSpinBox()
        self.count_box.setToolTip("Item count (0 empties the slot)")
        self._fit_count()
        self.slot_set = QPushButton("Set")
        self.slot_set.setToolTip(
            "Put the items into the slot (/setblock with the block-entity data: comparators "
            "update, a hopper keeps its cooldown)"
        )
        self.slot_set.clicked.connect(self._set_slot)
        for widget in (self.slot_box, self.item_box, self.count_box, self.slot_set):
            slot_layout.addWidget(widget)
        contents_layout.addRow("Slot", slot_row)
        self.empty_all = QPushButton("Empty all slots")
        self.empty_all.clicked.connect(
            lambda: self._pos is not None and self.contents_requested.emit(self._pos, None, None, 0)
        )
        contents_layout.addRow("", self.empty_all)
        layout.addWidget(self.contents_box)
        self.sign_box = QWidget()  # signs: their text, front and back
        sign_layout = QFormLayout(self.sign_box)
        sign_layout.setContentsMargins(0, 6, 0, 0)
        self.sign_lines: dict[str, list[QLineEdit]] = {}
        for side, title in (("front", "Front"), ("back", "Back")):
            edits = []
            for index in range(LINES):
                edit = QLineEdit()
                edit.setMaxLength(SIGN_LINE_LENGTH)
                edit.setPlaceholderText(f"line {index + 1}")
                edit.setToolTip(
                    "Text on the sign, as a player writes it (Enter or leaving the field "
                    "applies it; one undo step)"
                )
                edit.editingFinished.connect(lambda s=side: self._write_sign(s))
                sign_layout.addRow(title if index == 0 else "", edit)
                edits.append(edit)
            self.sign_lines[side] = edits
        layout.addWidget(self.sign_box)
        self.section_row = QWidget()  # hidden while nothing is selected
        section_row = QHBoxLayout(self.section_row)
        section_row.setContentsMargins(0, 0, 0, 0)
        section_row.addWidget(QLabel("Section:"))
        self.section_box = QComboBox()
        self.section_box.activated.connect(self._section_changed)
        section_row.addWidget(self.section_box, 1)
        layout.addWidget(self.section_row)
        layout.addStretch(1)
        layout.addWidget(self.note)
        self.show_block(None, None)

    # ------------------------------------------------------------------ display
    def show_block(self, document: Document | None, pos: Pos | None) -> None:
        self._pos = pos
        self._document = document
        self.source_box.setVisible(False)
        self.target_box.setVisible(False)
        self.plate_box.setVisible(False)
        self.contents_box.setVisible(False)
        self.sign_box.setVisible(False)
        if document is None or pos is None:
            self.monitor.setVisible(False)
            self._rebuild(None)
            self._state = None
            self.title.setText(NO_SELECTION)
            self.icon.clear()
            self.entity.setText("")
            self.note.setVisible(False)
            self.section_box.clear()
            self.section_row.setVisible(False)
            return
        self.section_row.setVisible(True)
        state = document.state_at(pos)
        self._state = state
        editable = document.can_edit
        self.monitor.setVisible(True)
        self.monitor.setChecked(pos in document.monitors)
        key = (pos, state.block.id)
        if key != self._layout_key:
            self._rebuild(state)
            self._layout_key = key
        x, y, z = pos
        self.title.setText(
            f"<span style='font-size:14px; font-weight:600'>{block_name(state.block.id)}</span>"
            f"<br><span style='color:{theme.TEXT_DIM}'>x {x} · y {y} · z {z}</span>"
        )
        self.icon.setPixmap(block_pixmap(state.block.id, 32) if not state.is_air else QPixmap())
        for prop in state.block.properties:
            editor = self._editors[prop.name]
            editor.show_value(state.get(prop))
            editor.setEnabled(editable)
        self.note.setVisible(bool(state.block.properties))
        be = document.level.get_block_entity(pos, create=False)
        self.entity.setText(f"Block entity: {be.describe()}" if be is not None else "")
        self.target_box.setVisible(state.is_(blocks.TARGET))
        from redsim.world.blocks.pressure_plate import BasePressurePlateBlock

        self.plate_box.setVisible(isinstance(state.block, BasePressurePlateBlock))
        self.plate_box.setEnabled(editable)
        self.target_box.setEnabled(editable)
        if isinstance(be, ContainerBlockEntity):
            self.contents_box.setVisible(True)
            self.contents_box.setEnabled(editable)
            self.slot_box.setRange(0, be.SIZE - 1)
            filled = [stack for stack in be.items if stack is not None]
            total = sum(count for _, count in filled)
            self.contents_label.setText(
                f"{total} items in {len(filled)} of {be.SIZE} slots"
                if filled
                else f"empty ({be.SIZE} slots)"
            )
            self.contents_grid.set_items(be.items)
        if isinstance(be, SignBlockEntity):
            self.sign_box.setVisible(True)
            self.sign_box.setEnabled(editable)
            for side, edits in self.sign_lines.items():
                for edit, text in zip(edits, be.lines(side), strict=True):
                    if not edit.hasFocus() and edit.text() != text:
                        edit.setText(text)
        kind = sources.kind_of(state)
        if kind is not None:
            self.source_box.setVisible(True)
            self.source_box.setEnabled(editable)
            for name, button in self.kind_buttons.items():
                button.setChecked(name == kind)
            # Step through what this block can give (a cake only makes even values).
            self.source_strength.values = sources.KINDS[kind].strengths
            self.source_strength.show_value(sources.strength_at(document.level, pos) or 0)
            page = getattr(be, "page", None) if getattr(be, "book", None) else None
            self._page = page
            self._source_form.setRowVisible(self.page_row, kind == "lectern")  # with label
            self.page_row.setEnabled(page is not None)
        self.section_box.blockSignals(True)
        self.section_box.clear()
        self.section_box.setEnabled(True)
        self.section_box.addItem("(none)", None)
        for name in document.sections.sections:
            self.section_box.addItem(name, name)
        current = document.sections.section_at(pos)
        if current is not None:
            self.section_box.setCurrentText(current.name)
        self.section_box.blockSignals(False)

    def _write_sign(self, side: str) -> None:
        """A sign's line edited: write the side's text (only when it changed)."""
        if self._pos is None or self._document is None:
            return
        be = self._document.level.get_block_entity(self._pos, create=False)
        lines = [edit.text() for edit in self.sign_lines[side]]
        if isinstance(be, SignBlockEntity) and be.lines(side) != lines:
            self.sign_requested.emit(self._pos, side, lines)

    def _rebuild(self, state: BlockState | None) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._editors.clear()
        self._layout_key = None
        if state is None:
            return
        for prop in state.block.properties:
            editor: Any
            values = prop.values
            if values == (True, False):
                editor = _Toggle(prop, lambda v, p=prop: self._pick(p, v))
            elif all(isinstance(v, int) and not isinstance(v, bool) for v in values):
                editor = _Stepper(values, lambda v, p=prop: self._pick(p, v), prop.name)
            else:
                editor = _Choice(prop, lambda v, p=prop: self._pick(p, v))
            label = QLabel(prop.name.replace("_", " ").capitalize())
            label.setToolTip(f"Block state property {prop.name!r}")
            self.form.addRow(label, editor)
            self._editors[prop.name] = editor

    # ------------------------------------------------------------------ edits
    def _pick(self, prop: Property, value: Any) -> None:
        if self._pos is None or self._state is None or self._state.get(prop) == value:
            if self._state is not None:
                self._editors[prop.name].show_value(self._state.get(prop))
            return
        pos, state = self._pos, self._state.with_(prop, value)
        _later(lambda: self.apply_requested.emit(pos, state))

    def _pick_source(self, kind: str | None, strength: int | None) -> None:
        if self._pos is None or self._state is None:
            return
        current = sources.kind_of(self._state)
        kind = kind or current
        if kind is None:
            return
        value = self.source_strength.value if strength is None else strength
        pos = self._pos
        _later(lambda: self.source_requested.emit(pos, kind, int(value)))

    def _fit_count(self) -> None:
        item = self.item_box.currentData()
        self.count_box.setRange(0, slot_limit(item) if item else 64)
        self.count_box.setValue(min(max(self.count_box.value(), 1), self.count_box.maximum()))

    def _pick_slot(self, slot: int) -> None:
        """A click on a slot of the grid: edit that slot, starting from its contents."""
        self.slot_box.setValue(slot)
        stack = self.contents_grid.items[slot]
        if stack is not None:
            index = self.item_box.findData(stack[0])
            if index >= 0:
                self.item_box.setCurrentIndex(index)
            self.count_box.setValue(stack[1])

    def _set_slot(self) -> None:
        if self._pos is not None:
            pos, slot = self._pos, self.slot_box.value()
            item, count = self.item_box.currentData(), self.count_box.value()
            _later(lambda: self.contents_requested.emit(pos, slot, item, count))

    def _pick_hit_strength(self, value: int) -> None:
        self.hit_strength.show_value(value)

    def _hit(self, arrow: bool) -> None:
        if self._pos is not None:
            pos, strength = self._pos, int(self.hit_strength.value)
            _later(lambda: self.hit_requested.emit(pos, strength, arrow))

    def _step_on_plate(self) -> None:
        if self._pos is not None:
            pos = self._pos
            mobs, items = self.plate_mobs.value(), self.plate_items.value()
            ticks = self.plate_ticks.value()
            _later(lambda: self.plate_requested.emit(pos, mobs, items, ticks))

    def _turn_page(self, step: int) -> None:
        if self._pos is not None and self._page is not None:
            pos, page = self._pos, self._page + step
            _later(lambda: self.page_requested.emit(pos, page))

    def _section_changed(self, index: int) -> None:
        if self._pos is not None:
            self.section_requested.emit(self._pos, self.section_box.itemData(index))
