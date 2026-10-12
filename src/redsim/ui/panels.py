"""Side panels: block palette, inspector, simulation controls, diagnostics, sections, help."""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.editor.document import Document
from redsim.sim import trace as tr
from redsim.ui import theme
from redsim.ui.icons import block_pixmap
from redsim.ui.keymap import Keymap, hotkey_sections
from redsim.ui.names import block_name
from redsim.ui.preferences import Preferences
from redsim.world import blocks
from redsim.world.block import BlockState
from redsim.world.blocks.container import ContainerBlockEntity, slot_limit
from redsim.world.properties import Property

NO_SELECTION = "Left-click a block in NORMAL mode (Esc) to inspect it."

DIRECTION_LABELS = {
    "north": "↑ N",
    "east": "→ E",
    "south": "↓ S",
    "west": "← W",
    "up": "⤒ Up",
    "down": "⤓ Down",
}


def _later(callback: Any) -> None:
    """Run after the current event: edits rebuild the panel, which may delete the button
    whose click is still being handled."""
    QTimer.singleShot(0, callback)


class _Choice(QWidget):
    """Exclusive buttons for a property's values (directions get arrows)."""

    def __init__(self, prop: Property, on_pick: Any) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.buttons: dict[Any, QPushButton] = {}
        for value in prop.values:
            text = prop.serialize(value)
            label = DIRECTION_LABELS.get(text, text) if isinstance(value, Direction) else text
            button = QPushButton(label)
            button.setCheckable(True)
            button.setToolTip(f"{prop.name} = {text}")
            button.clicked.connect(lambda _=False, v=value: on_pick(v))
            layout.addWidget(button)
            self.buttons[value] = button

    def show_value(self, value: Any) -> None:
        for option, button in self.buttons.items():
            button.setChecked(option == value)


class _Toggle(QPushButton):
    """A boolean property: one button that flips it."""

    def __init__(self, prop: Property, on_pick: Any) -> None:
        super().__init__()
        self.setCheckable(True)
        self.clicked.connect(lambda checked: on_pick(bool(checked)))
        self.setToolTip(f"Click to flip {prop.name}")

    def show_value(self, value: Any) -> None:
        self.setChecked(bool(value))
        self.setText("true" if value else "false")


class _Stepper(QWidget):
    """An integer property: ◀ value ▶."""

    def __init__(self, values: tuple[Any, ...], on_pick: Any, tooltip: str) -> None:
        super().__init__()
        self.values = values
        self.value: Any = values[0]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.back = QPushButton("◀")
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumWidth(36)
        self.next = QPushButton("▶")
        for button in (self.back, self.next):
            button.setMaximumWidth(40)
            button.setToolTip(tooltip)
        self.back.clicked.connect(lambda: self._step(-1, on_pick))
        self.next.clicked.connect(lambda: self._step(1, on_pick))
        layout.addWidget(self.back)
        layout.addWidget(self.label)
        layout.addWidget(self.next)
        layout.addStretch(1)

    def _step(self, delta: int, on_pick: Any) -> None:
        index = self.values.index(self.value) + delta
        if 0 <= index < len(self.values):
            on_pick(self.values[index])

    def show_value(self, value: Any) -> None:
        self.value = value
        self.label.setText(str(value))
        index = self.values.index(value) if value in self.values else 0
        self.back.setEnabled(index > 0)
        self.next.setEnabled(index < len(self.values) - 1)


#: Items the inspector offers for barrels and hoppers (max stack size in brackets).
CONTAINER_ITEMS = (
    ("minecraft:redstone", "Redstone dust (64)"),
    ("minecraft:stone", "Stone (64)"),
    ("minecraft:ender_pearl", "Ender pearl (16)"),
    ("minecraft:wooden_sword", "Wooden sword (1)"),
)


class InspectorPanel(QWidget):
    """The selected block. Every control applies at once, as a /setblock edit (one undo
    step each); widgets are updated in place while the same kind of block stays selected."""

    apply_requested = Signal(object, object)  # Pos, BlockState
    section_requested = Signal(object, object)  # Pos, str | None
    source_requested = Signal(object, str, int)  # Pos, kind, strength
    page_requested = Signal(object, int)  # Pos, page (a player turning the page)
    monitor_requested = Signal(object)  # Pos: add/remove on the timeline monitor
    hit_requested = Signal(object, int, bool)  # Pos, strength, arrow
    contents_requested = Signal(object, object, object, int)  # Pos, slot|None, item|None, n

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
        self.icon.setFixedSize(32, 32)
        title_row.addWidget(self.icon)
        self.title = QLabel(NO_SELECTION)
        self.title.setWordWrap(True)
        title_row.addWidget(self.title, 1)
        self.monitor = QPushButton("📈 Monitor")
        self.monitor.setCheckable(True)
        self.monitor.setToolTip("Show this block's value per tick on the timeline")
        self.monitor.clicked.connect(lambda: self._pos and self.monitor_requested.emit(self._pos))
        title_row.addWidget(self.monitor)
        layout.addLayout(title_row)
        self.form_widget = QWidget()
        self.form = QFormLayout(self.form_widget)
        self.form.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.form_widget)
        self.entity = QLabel("")
        self.entity.setWordWrap(True)
        layout.addWidget(self.entity)
        self.note = QLabel(
            "<small>Edits apply at once with /setblock semantics (state adjusted by "
            "neighbor shapes, then neighbor updates). Right click in NORMAL mode uses a "
            "block like a player instead.</small>"
        )
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.source_box = QWidget()
        source_layout = QFormLayout(self.source_box)
        source_layout.setContentsMargins(0, 6, 0, 0)
        self.source_kind = QWidget()
        kind_layout = QHBoxLayout(self.source_kind)
        kind_layout.setContentsMargins(0, 0, 0, 0)
        kind_layout.setSpacing(2)
        self.kind_buttons: dict[str, QPushButton] = {}
        for kind in sources.KINDS.values():
            button = QPushButton(kind.id.capitalize())
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
        self.page_back = QPushButton("◀ Page")
        self.page_next = QPushButton("Page ▶")
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
            ("🏹 Arrow", True, "An arrow hits the target: power for 20 ticks"),
            ("❄ Snowball", False, "Another projectile hits the target: power for 8 ticks"),
        ):
            button = QPushButton(text)
            button.setToolTip(tip + " (it lands in the next tick's entity phase)")
            button.clicked.connect(lambda _=False, a=arrow: self._hit(a))
            hit_layout.addWidget(button)
            self.hit_buttons[arrow] = button
        target_layout.addRow("Projectile", hit_row)
        layout.addWidget(self.target_box)
        self.contents_box = QWidget()
        contents_layout = QFormLayout(self.contents_box)
        contents_layout.setContentsMargins(0, 6, 0, 0)
        self.contents_label = QLabel("")
        self.contents_label.setWordWrap(True)
        contents_layout.addRow("Contents", self.contents_label)
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
        section_row = QHBoxLayout()
        section_row.addWidget(QLabel("Section:"))
        self.section_box = QComboBox()
        self.section_box.activated.connect(self._section_changed)
        section_row.addWidget(self.section_box)
        layout.addLayout(section_row)
        layout.addStretch(1)
        self.show_block(None, None)

    # ------------------------------------------------------------------ display
    def show_block(self, document: Document | None, pos: Pos | None) -> None:
        self._pos = pos
        self.source_box.setVisible(False)
        self.target_box.setVisible(False)
        self.contents_box.setVisible(False)
        if document is None or pos is None:
            self.monitor.setVisible(False)
            self._rebuild(None)
            self._state = None
            self.title.setText(NO_SELECTION)
            self.icon.clear()
            self.entity.setText("")
            self.note.setVisible(False)
            self.section_box.clear()
            self.section_box.setEnabled(False)
            return
        state = document.state_at(pos)
        self._state = state
        editable = document.can_edit
        self.monitor.setVisible(True)
        self.monitor.setChecked(pos in document.monitors)
        key = (pos, state.block.id)
        if key != self._layout_key:
            self._rebuild(state)
            self._layout_key = key
        self.title.setText(f"<b>{block_name(state.block.id)}</b> at {pos}")
        self.icon.setPixmap(block_pixmap(state.block.id, 32) if not state.is_air else QPixmap())
        for prop in state.block.properties:
            editor = self._editors[prop.name]
            editor.show_value(state.get(prop))
            editor.setEnabled(editable)
        self.note.setVisible(bool(state.block.properties))
        be = document.level.get_block_entity(pos, create=False)
        self.entity.setText(f"Block entity: {be.describe()}" if be is not None else "")
        self.target_box.setVisible(state.is_(blocks.TARGET))
        self.target_box.setEnabled(editable)
        if isinstance(be, ContainerBlockEntity):
            self.contents_box.setVisible(True)
            self.contents_box.setEnabled(editable)
            self.slot_box.setRange(0, be.SIZE - 1)
            filled = [
                f"{slot}: {stack[0].removeprefix('minecraft:')} ×{stack[1]}"
                for slot, stack in enumerate(be.items)
                if stack is not None
            ]
            self.contents_label.setText(", ".join(filled) if filled else f"empty ({be.SIZE} slots)")
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
            self.page_row.setVisible(kind == "lectern")
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
            self.form.addRow(prop.name, editor)
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

    def _turn_page(self, step: int) -> None:
        if self._pos is not None and self._page is not None:
            pos, page = self._pos, self._page + step
            _later(lambda: self.page_requested.emit(pos, page))

    def _section_changed(self, index: int) -> None:
        if self._pos is not None:
            self.section_requested.emit(self._pos, self.section_box.itemData(index))


class DiagnosticsPanel(QTabWidget):
    """Pending scheduled ticks, queued block events, and the last step's trace."""

    def __init__(self) -> None:
        super().__init__()
        self.ticks = QTableWidget(0, 5)
        self.ticks.setHorizontalHeaderLabels(["at tick", "priority", "sub-tick", "block", "pos"])
        self.addTab(self.ticks, "Scheduled ticks")
        self.events = QListWidget()
        self.addTab(self.events, "Block events")
        self.trace = QPlainTextEdit()
        self.trace.setReadOnly(True)
        self.addTab(self.trace, "Last step trace")

    def show_state(self, document: Document, last_steps: list[Any]) -> None:
        level = document.level
        collected = list(level.block_ticks.to_run)
        pending = level.block_ticks.pending()
        rows = [("this tick", t) for t in collected] + [(str(t.trigger_tick), t) for t in pending]
        self.ticks.setRowCount(len(rows))
        for row, (when, tick) in enumerate(rows):
            values = [
                when,
                tick.priority.name,
                str(tick.sub_tick),
                tick.block_id[10:],
                str(tick.pos),
            ]
            for column, value in enumerate(values):
                self.ticks.setItem(row, column, QTableWidgetItem(value))
        self.events.clear()
        for pos, block_id, b0, b1 in level.block_events:
            self.events.addItem(f"{block_id[10:]} at {pos}: ({b0}, {b1})")
        lines: list[str] = []
        trace = level.trace
        for step in last_steps[-40:]:
            lines.append(step.describe())
            if step.record is None:
                continue
            depth = {step.record: 0}
            for record in trace.after(step.record):
                if record.step != step.index:
                    break
                level_depth = depth.get(record.parent, 0) + 1 if record.parent is not None else 1
                depth[record.id] = level_depth
                if record.kind == tr.SHAPE_UPDATE and not record.detail.get("changed"):
                    continue  # unchanged shape updates are noise in this view
                lines.append("  " * level_depth + record.summary())
        self.trace.setPlainText("\n".join(lines[-2000:]))


class SectionsPanel(QWidget):
    changed = Signal()

    def __init__(self, document: Document) -> None:
        super().__init__()
        self.document = document
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        layout.addWidget(self.list)
        row = QHBoxLayout()
        add = QPushButton("Add…")
        add.clicked.connect(self._add)
        row.addWidget(add)
        color = QPushButton("Color…")
        color.clicked.connect(self._recolor)
        row.addWidget(color)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove)
        row.addWidget(remove)
        layout.addLayout(row)
        hint = QLabel("Sections color the view only; they never affect the simulation.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.refresh()

    def set_document(self, document: Document) -> None:
        self.document = document
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for name, section in self.document.sections.sections.items():
            item = QListWidgetItem(f"{name}  ({len(section.positions)} blocks)")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setForeground(QColor(section.color))
            self.list.addItem(item)

    def _selected(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add(self) -> None:
        name, ok = QInputDialog.getText(self, "New section", "Name:")
        if ok and name:
            color = QColorDialog.getColor(QColor("#ff5555"), self, "Section color")
            if color.isValid():
                self.document.sections.add(name, color.name())
                self.changed.emit()
                self.refresh()

    def _recolor(self) -> None:
        name = self._selected()
        if name:
            section = self.document.sections.sections[name]
            color = QColorDialog.getColor(QColor(section.color), self, "Section color")
            if color.isValid():
                section.color = color.name()
                self.changed.emit()
                self.refresh()

    def _remove(self) -> None:
        name = self._selected()
        if name:
            self.document.sections.remove(name)
            self.changed.emit()
            self.refresh()


#: Section header colors: the current mode's section in its mode color, others neutral.
MODE_TINTS = {"normal": "#2b4f80", "build": "#2c6a34", "select": "#8a5418"}


def keycaps(bindings: tuple[str, ...]) -> str:
    """Rich text with each key drawn as a keycap; alternatives separated by "or"."""
    if not bindings:
        return "<i>unbound</i>"
    cap = (
        f'<span style="background-color:{theme.WIDGET_HOVER}; color:{theme.TEXT};">'
        "&nbsp;{}&nbsp;</span>"
    )
    shown = []
    for binding in bindings:
        *mods, last = binding.split("+")
        parts = [cap.format(html.escape(part)) for part in (*mods, last)]
        shown.append("+".join(parts))
    return " or ".join(shown)


class HotkeysPanel(QWidget):
    """Every binding of the active keymap, grouped by what you are doing, searchable; the
    section of the current mode is highlighted. Generated from ``redsim.ui.keymap``."""

    def __init__(self, keymap: Keymap) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter, e.g. rotate, paste or Ctrl")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _text: self._render())
        layout.addWidget(self.search)
        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        layout.addWidget(self.view)
        self._mode = "normal"
        self._sections: list[tuple[str, str | None, list[tuple[str, tuple[str, ...]]]]] = []
        self.set_keymap(keymap)

    def set_keymap(self, keymap: Keymap) -> None:
        self._sections = hotkey_sections(keymap)
        self._render()

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._render()

    def visible_rows(self) -> list[tuple[str, str]]:
        """(section, action) pairs that pass the filter."""
        needle = self.search.text().strip().lower()
        rows = []
        for title, _, entries in self._sections:
            for action, bindings in entries:
                haystack = f"{title} {action} {' '.join(bindings)}".lower()
                if not needle or needle in haystack:
                    rows.append((title, action))
        return rows

    def _render(self) -> None:
        shown = set(self.visible_rows())
        mode = self._mode
        parts = [
            f"<p>You are in <b>{mode.upper()}</b> mode (Esc / B / V switch); its section is "
            "highlighted.</p>"
        ]
        for title, section_mode, entries in self._sections:
            rows = [(a, b) for a, b in entries if (title, a) in shown]
            if not rows:
                continue
            tint = MODE_TINTS.get(mode) if section_mode == mode else theme.WIDGET
            parts.append('<table width="100%" cellspacing="0" cellpadding="3">')
            parts.append(
                f'<tr><td style="background-color:{tint};"><b>{html.escape(title)}</b></td></tr>'
            )
            for action, bindings in rows:  # stacked, so it reads well in a narrow panel
                parts.append(
                    f"<tr><td>{html.escape(action)}<br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{keycaps(bindings)}</td></tr>"
                )
            parts.append("</table><br>")
        parts.append(
            "<p><small>Rebind anything: Settings → Edit keymap file, then Reload keymap."
            "</small></p>"
        )
        self.view.setHtml("".join(parts))


PREFERENCES_WIDTH = 480


class PreferencesDialog(QDialog):
    """Preferences; changes apply live (``changed``) and are saved on close."""

    changed = Signal()

    def __init__(self, preferences: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setFixedWidth(PREFERENCES_WIDTH)  # sliders stay usable without resizing
        self.preferences = preferences
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for attribute, text, tip in (
            (
                "xray_building_alpha",
                "X-ray: building blocks",
                "How visible building blocks (stone, planks, …) stay in both X-ray levels.",
            ),
            (
                "xray_circuit_alpha",
                "X-ray: circuit blocks",
                "How visible circuit parts stay in the 'everything' X-ray level.",
            ),
        ):
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(round(getattr(preferences, attribute) * 100))
            slider.setToolTip(tip)
            slider.setMinimumWidth(220)
            value = QLabel(f"{slider.value()} %")
            value.setFixedWidth(44)
            slider.valueChanged.connect(lambda v, a=attribute, label=value: self._set(a, v, label))
            row = QHBoxLayout()
            row.addWidget(slider)
            row.addWidget(value)
            form.addRow(text, row)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        form.addRow(close)

    def _set(self, attribute: str, value: int, label: QLabel) -> None:
        setattr(self.preferences, attribute, value / 100)
        label.setText(f"{value} %")
        self.changed.emit()


class ContraptionsPanel(QTabWidget):
    """Prefab library and groups with exposed ports."""

    save_prefab = Signal()
    load_prefab = Signal(str)
    delete_prefab = Signal(str)
    import_prefab = Signal()
    export_prefab = Signal(str)
    create_group = Signal()
    add_port = Signal(str)
    toggle_port = Signal(str, int)
    delete_group = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        prefab_page = QWidget()
        prefab_layout = QVBoxLayout(prefab_page)
        self.prefab_list = QListWidget()
        self.prefab_list.itemDoubleClicked.connect(lambda item: self.load_prefab.emit(item.text()))
        prefab_layout.addWidget(self.prefab_list)
        row = QHBoxLayout()
        for text, slot in (
            ("Save selection…", self.save_prefab.emit),
            ("To clipboard", lambda: self._with_prefab(self.load_prefab)),
            ("Delete", lambda: self._with_prefab(self.delete_prefab)),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        prefab_layout.addLayout(row)
        row = QHBoxLayout()
        for text, slot in (
            ("Import…", self.import_prefab.emit),
            ("Export…", lambda: self._with_prefab(self.export_prefab)),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        prefab_layout.addLayout(row)
        hint = QLabel(
            "B: mark selection corners · Ctrl+C copy · Ctrl+V paste (like /clone) · "
            "R rotate clipboard · Del clear selection (like /fill air)"
        )
        hint.setWordWrap(True)
        prefab_layout.addWidget(hint)
        self.addTab(prefab_page, "Prefabs")

        group_page = QWidget()
        group_layout = QVBoxLayout(group_page)
        self.group_list = QListWidget()
        group_layout.addWidget(self.group_list)
        row = QHBoxLayout()
        create = QPushButton("Group selection…")
        create.clicked.connect(self.create_group.emit)
        row.addWidget(create)
        port = QPushButton("Add port…")
        port.setToolTip("Expose the inspected block (Ctrl+click) as an input or output port")
        port.clicked.connect(lambda: self._with_group(self.add_port))
        row.addWidget(port)
        remove = QPushButton("Delete")
        remove.clicked.connect(lambda: self._with_group(self.delete_group))
        row.addWidget(remove)
        group_layout.addLayout(row)
        self.ports = QListWidget()
        self.ports.setToolTip("Double-click an input port to use (toggle) its block")
        self.ports.itemDoubleClicked.connect(self._port_clicked)
        group_layout.addWidget(self.ports)
        note = QLabel(
            "Groups only name parts of a circuit and expose ports; the internals still "
            "simulate block by block with unchanged timing."
        )
        note.setWordWrap(True)
        group_layout.addWidget(note)
        self.group_list.currentTextChanged.connect(lambda _: self._refresh_ports())
        self.addTab(group_page, "Groups")
        self._document: Document | None = None

    def _with_prefab(self, signal: Any) -> None:
        item = self.prefab_list.currentItem()
        if item is not None:
            signal.emit(item.text())

    def _with_group(self, signal: Any) -> None:
        item = self.group_list.currentItem()
        if item is not None:
            signal.emit(item.text())

    def _port_clicked(self, item: QListWidgetItem) -> None:
        group = self.group_list.currentItem()
        if group is not None:
            self.toggle_port.emit(group.text(), self.ports.row(item))

    def show_document(self, document: Document) -> None:
        from redsim.editor.groups import port_reading

        self._document = document
        current_prefab = self.prefab_list.currentItem()
        selected = current_prefab.text() if current_prefab else None
        self.prefab_list.clear()
        for name in sorted(document.prefabs):
            self.prefab_list.addItem(name)
            if name == selected:
                self.prefab_list.setCurrentRow(self.prefab_list.count() - 1)
        current_group = self.group_list.currentItem()
        group_name = current_group.text() if current_group else None
        self.group_list.blockSignals(True)
        self.group_list.clear()
        for name in sorted(document.groups.groups):
            self.group_list.addItem(name)
            if name == group_name:
                self.group_list.setCurrentRow(self.group_list.count() - 1)
        self.group_list.blockSignals(False)
        self._refresh_ports(port_reading)

    def _refresh_ports(self, reading: Any = None) -> None:
        from redsim.editor.groups import port_reading

        reading = reading or port_reading
        self.ports.clear()
        item = self.group_list.currentItem()
        if self._document is None or item is None:
            return
        group = self._document.groups.groups.get(item.text())
        if group is None:
            return
        for port in group.ports:
            arrow = "→ in " if port.role == "input" else "out →"
            value = reading(self._document.level, port)
            self.ports.addItem(f"{arrow} {port.name} {port.pos}: {value}")
