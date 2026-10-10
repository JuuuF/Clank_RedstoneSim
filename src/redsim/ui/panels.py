"""Side panels: block palette, inspector, simulation controls, diagnostics, sections, help."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor.document import Document
from redsim.sim import trace as tr
from redsim.world import blocks
from redsim.world.block import Block, BlockState

#: Palette order; the first nine are the hotbar (keys 1-9).
PALETTE: list[tuple[str, list[str]]] = [
    (
        "Redstone",
        [
            "minecraft:redstone_wire",
            "minecraft:redstone_torch",
            "minecraft:repeater",
            "minecraft:comparator",
            "minecraft:lever",
            "minecraft:redstone_lamp",
            "minecraft:redstone_block",
            "minecraft:stone_button",
            "minecraft:oak_button",
            "minecraft:piston",
            "minecraft:sticky_piston",
            "minecraft:cake",
        ],
    ),
    (
        "Building",
        [
            "minecraft:stone",
            "minecraft:smooth_stone",
            "minecraft:cobblestone",
            "minecraft:oak_planks",
            "minecraft:white_wool",
            "minecraft:white_concrete",
            "minecraft:smooth_stone_slab",
        ],
    ),
    (
        "Special",
        [
            "minecraft:glass",
            "minecraft:glowstone",
            "minecraft:obsidian",
            "minecraft:bedrock",
            "minecraft:slime_block",
            "minecraft:honey_block",
        ],
    ),
]
HOTBAR = [
    "minecraft:stone",
    "minecraft:redstone_wire",
    "minecraft:redstone_torch",
    "minecraft:repeater",
    "minecraft:comparator",
    "minecraft:lever",
    "minecraft:redstone_lamp",
    "minecraft:redstone_block",
    "minecraft:sticky_piston",
]


class PalettePanel(QListWidget):
    block_chosen = Signal(object)  # Block

    def __init__(self) -> None:
        super().__init__()
        for title, ids in PALETTE:
            header = QListWidgetItem(title)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            self.addItem(header)
            for block_id in ids:
                item = QListWidgetItem("   " + blocks.get(block_id).name.replace("_", " "))
                item.setData(Qt.ItemDataRole.UserRole, block_id)
                self.addItem(item)
        self.currentItemChanged.connect(self._changed)
        self.select_block(blocks.STONE)

    def _changed(self, item: QListWidgetItem | None) -> None:
        if item is not None and item.data(Qt.ItemDataRole.UserRole):
            self.block_chosen.emit(blocks.get(item.data(Qt.ItemDataRole.UserRole)))

    def select_block(self, block: Block) -> None:
        for row in range(self.count()):
            if self.item(row).data(Qt.ItemDataRole.UserRole) == block.id:
                self.setCurrentRow(row)
                return

    def current_block(self) -> Block:
        item = self.currentItem()
        block_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        return blocks.get(block_id) if block_id else blocks.STONE


class InspectorPanel(QWidget):
    """Shows the selected block; property edits are applied with /setblock semantics."""

    apply_requested = Signal(object, object)  # Pos, BlockState
    section_requested = Signal(object, object)  # Pos, str | None

    def __init__(self) -> None:
        super().__init__()
        self._pos: Pos | None = None
        self._state: BlockState | None = None
        self._editors: dict[str, QComboBox] = {}
        layout = QVBoxLayout(self)
        self.title = QLabel("Ctrl+click a block to inspect it.")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.form = QFormLayout()
        layout.addLayout(self.form)
        self.entity = QLabel("")
        layout.addWidget(self.entity)
        self.apply_button = QPushButton("Apply (/setblock)")
        self.apply_button.setToolTip(
            "Applies the edited properties like the /setblock command: the state is adjusted "
            "by neighbor shapes, then neighbors are updated. Player actions (right click) use "
            "the in-game interaction logic instead."
        )
        self.apply_button.clicked.connect(self._apply)
        layout.addWidget(self.apply_button)
        section_row = QHBoxLayout()
        section_row.addWidget(QLabel("Section:"))
        self.section_box = QComboBox()
        self.section_box.activated.connect(self._section_changed)
        section_row.addWidget(self.section_box)
        layout.addLayout(section_row)
        layout.addStretch(1)
        self.show_block(None, None)

    def show_block(self, document: Document | None, pos: Pos | None) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._editors.clear()
        self._pos = pos
        self._state = None
        self.section_box.clear()
        if document is None or pos is None:
            self.title.setText("Ctrl+click a block to inspect it.")
            self.entity.setText("")
            self.apply_button.setEnabled(False)
            self.section_box.setEnabled(False)
            return
        state = document.state_at(pos)
        self._state = state
        self.title.setText(f"<b>{state.block.name}</b> at {pos}")
        for prop in state.block.properties:
            box = QComboBox()
            for value in prop.values:
                box.addItem(prop.serialize(value), value)
            box.setCurrentText(prop.serialize(state.get(prop)))
            self.form.addRow(prop.name, box)
            self._editors[prop.name] = box
        be = document.level.get_block_entity(pos, create=False)
        self.entity.setText(f"Block entity: {be.describe()}" if be is not None else "")
        self.apply_button.setEnabled(bool(state.block.properties) and document.can_edit)
        self.section_box.setEnabled(True)
        self.section_box.addItem("(none)", None)
        for name in document.sections.sections:
            self.section_box.addItem(name, name)
        current = document.sections.section_at(pos)
        if current is not None:
            self.section_box.setCurrentText(current.name)

    def _apply(self) -> None:
        if self._pos is None or self._state is None:
            return
        state = self._state
        for prop in state.block.properties:
            state = state.with_(prop, self._editors[prop.name].currentData())
        self.apply_requested.emit(self._pos, state)

    def _section_changed(self, index: int) -> None:
        if self._pos is not None:
            self.section_requested.emit(self._pos, self.section_box.itemData(index))


class SimulationPanel(QWidget):
    play_toggled = Signal(bool)
    step_tick = Signal()
    step_event = Signal()
    tick_back = Signal()
    step_back = Signal()
    seek_requested = Signal(int)
    speed_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        back_row = QHBoxLayout()
        tick_back = QPushButton("⏮ Tick back")
        tick_back.setToolTip("Rewind to the previous tick boundary (Shift+T)")
        tick_back.clicked.connect(self.tick_back.emit)
        back_row.addWidget(tick_back)
        step_back = QPushButton("◀ Step back")
        step_back.setToolTip("Rewind one engine step (Shift+E)")
        step_back.clicked.connect(self.step_back.emit)
        back_row.addWidget(step_back)
        layout.addLayout(back_row)
        row = QHBoxLayout()
        self.play = QPushButton("▶ Run")
        self.play.setCheckable(True)
        self.play.setToolTip("Run/pause the simulation at the chosen tick rate (P)")
        self.play.toggled.connect(self._toggled)
        row.addWidget(self.play)
        tick = QPushButton("Step tick")
        tick.setToolTip("Finish the current game tick, or run one whole tick (T)")
        tick.clicked.connect(self.step_tick.emit)
        row.addWidget(tick)
        event = QPushButton("Step event")
        event.setToolTip(
            "Run one engine step: tick start, one scheduled tick, one block event or one "
            "block-entity tick (the simulator's 'sub-tick', see doc/architecture.md) (E)"
        )
        event.clicked.connect(self.step_event.emit)
        row.addWidget(event)
        layout.addLayout(row)
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Ticks per second:"))
        self.speed = QSpinBox()
        self.speed.setRange(1, 200)
        self.speed.setValue(20)
        self.speed.valueChanged.connect(self.speed_changed.emit)
        speed_row.addWidget(self.speed)
        self.warp = QCheckBox("Warp")
        self.warp.setToolTip("Run as many ticks as possible (normal event order is kept)")
        speed_row.addWidget(self.warp)
        layout.addLayout(speed_row)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setToolTip(
            "Timeline of engine steps: drag to rewind or replay (deterministic re-execution)"
        )
        self.slider.valueChanged.connect(self._slider_moved)
        layout.addWidget(self.slider)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def _toggled(self, on: bool) -> None:
        self.play.setText("⏸ Pause" if on else "▶ Run")
        self.play_toggled.emit(on)

    def _slider_moved(self, value: int) -> None:
        if not self.slider.signalsBlocked():
            self.seek_requested.emit(value)

    def show_status(self, document: Document) -> None:
        engine = document.engine
        history = document.history
        self.slider.blockSignals(True)
        self.slider.setRange(history.start, history.end)
        self.slider.setValue(history.position)
        self.slider.blockSignals(False)
        ahead = history.end - history.position
        future = f" ({ahead} recorded steps ahead)" if ahead else ""
        self.status.setText(
            f"Game time: <b>{engine.game_time}</b><br>"
            f"Phase: {engine.phase.value}<br>"
            f"Next step: {engine.peek_next_step()}<br>"
            f"Engine step: {history.position} of {history.end}{future}"
        )


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


CONTROLS_HELP = """<b>Camera</b><br>
W A S D: move &nbsp; Space / Shift: up / down &nbsp; Ctrl: faster<br>
Hold right mouse button and drag: look around &nbsp; Wheel: zoom (field of view)<br><br>
<b>Building</b><br>
Left click: break block<br>
Right click: place the palette block (or use a lever, button, repeater, comparator,
dust or cake)<br>
Shift + right click: always place<br>
Middle click: pick the block type<br>
Ctrl + left click: select a block for the inspector; Esc clears<br>
1-9: hotbar (stone, dust, torch, repeater, comparator, lever, lamp, redstone block,
sticky piston)<br><br>
<b>Simulation</b><br>
P: run/pause &nbsp; T: step tick &nbsp; E: step event<br>
Shift+T: tick back &nbsp; Shift+E: step back &nbsp; timeline slider: rewind/replay<br>
Ctrl+Z / Ctrl+Y: undo / redo the last edit (rewinds to just before it)<br>
Edits are only possible between ticks, like player actions in the game. Editing after a
rewind discards the recorded future.
"""


def controls_help() -> QLabel:
    label = QLabel(CONTROLS_HELP)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignTop)
    label.setMargin(8)
    return label


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
