"""Main window: viewport in the center, panels around it, menus and shortcuts."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QWidget,
)

from redsim.core.pos import Pos, offset
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document, EditError
from redsim.editor.groups import Group, Port
from redsim.editor.placement import PlaceRequest
from redsim.ui.geometry import Hit
from redsim.ui.panels import (
    HOTBAR,
    ContraptionsPanel,
    DiagnosticsPanel,
    InspectorPanel,
    PalettePanel,
    SectionsPanel,
    SimulationPanel,
    controls_help,
)
from redsim.ui.viewport import Viewport
from redsim.world import blocks
from redsim.world.blocks.torch import RedstoneWallTorchBlock

FILE_FILTER = "Redstone simulator worlds (*.redsim.json *.json)"


class MainWindow(QMainWindow):
    def __init__(self, document: Document | None = None) -> None:
        super().__init__()
        self.document = document or Document.new_flat()
        self.current_block = blocks.STONE
        self.last_steps: list[Any] = []
        self.viewport = Viewport(self.document)
        self.setCentralWidget(self.viewport)

        self.palette = PalettePanel()
        self.inspector = InspectorPanel()
        self.simulation = SimulationPanel()
        self.diagnostics = DiagnosticsPanel()
        self.sections = SectionsPanel(self.document)
        left = Qt.DockWidgetArea.LeftDockWidgetArea
        right = Qt.DockWidgetArea.RightDockWidgetArea
        blocks_dock = self._dock("Blocks", self.palette, left)
        self.help_dock = self._dock("Controls", controls_help(), left)
        self.tabifyDockWidget(blocks_dock, self.help_dock)
        blocks_dock.raise_()
        simulation_dock = self._dock("Simulation", self.simulation, right)
        inspector_dock = self._dock("Inspector", self.inspector, right)
        sections_dock = self._dock("Sections", self.sections, right)
        self.tabifyDockWidget(inspector_dock, sections_dock)
        self.contraptions = ContraptionsPanel()
        contraptions_dock = self._dock("Contraptions", self.contraptions, right)
        self.tabifyDockWidget(sections_dock, contraptions_dock)
        inspector_dock.raise_()
        self.diagnostics_dock = self._dock(
            "Diagnostics", self.diagnostics, Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.resizeDocks([blocks_dock, simulation_dock], [210, 320], Qt.Orientation.Horizontal)
        self.resizeDocks([self.diagnostics_dock], [190], Qt.Orientation.Vertical)

        self._corner: Pos | None = None
        self._corner_done = False
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._play_tick)
        self._connect()
        self._build_menus()
        self.viewport.look_at((0, 1, 0))
        self._changed()

    # ------------------------------------------------------------------ setup
    def _dock(self, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(title)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _connect(self) -> None:
        self.palette.block_chosen.connect(self._choose_block)
        self.viewport.hover_changed.connect(self._hover)
        self.viewport.place_requested.connect(self._place)
        self.viewport.break_requested.connect(self._break)
        self.viewport.pick_requested.connect(self._pick)
        self.viewport.select_requested.connect(self._select)
        self.inspector.apply_requested.connect(self._apply_state)
        self.inspector.section_requested.connect(self._assign_section)
        self.sections.changed.connect(self._changed)
        self.simulation.play_toggled.connect(self._play)
        self.simulation.step_tick.connect(self._step_tick)
        self.simulation.step_event.connect(self._step_event)
        self.simulation.tick_back.connect(self._tick_back)
        self.simulation.step_back.connect(self._step_back)
        self.simulation.seek_requested.connect(self._seek)
        self.contraptions.save_prefab.connect(self._save_prefab)
        self.contraptions.load_prefab.connect(self._load_prefab)
        self.contraptions.delete_prefab.connect(self._delete_prefab)
        self.contraptions.import_prefab.connect(self._import_prefab)
        self.contraptions.export_prefab.connect(self._export_prefab)
        self.contraptions.create_group.connect(self._create_group)
        self.contraptions.add_port.connect(self._add_port)
        self.contraptions.toggle_port.connect(self._toggle_port)
        self.contraptions.delete_group.connect(self._delete_group)
        self.simulation.speed_changed.connect(self._speed)

    def _action(
        self, menu: Any, text: str, slot: Any, shortcut: str | QKeySequence | None = None
    ) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        menu.addAction(action)
        self.addAction(action)
        return action

    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")
        self._action(file_menu, "&New", self._new, QKeySequence.StandardKey.New)
        self._action(file_menu, "&Open…", self._open, QKeySequence.StandardKey.Open)
        self._action(file_menu, "&Save", self._save, QKeySequence.StandardKey.Save)
        self._action(file_menu, "Save &as…", self._save_as, QKeySequence.StandardKey.SaveAs)
        file_menu.addSeparator()
        self._action(file_menu, "&Quit", self.close, QKeySequence.StandardKey.Quit)
        edit_menu = bar.addMenu("&Edit")
        self._action(edit_menu, "&Undo", self._undo, QKeySequence.StandardKey.Undo)
        self._action(edit_menu, "&Redo", self._redo, QKeySequence.StandardKey.Redo)
        self._action(edit_menu, "Clear selection", lambda: self._select(None), "Esc")
        sim_menu = bar.addMenu("&Simulation")
        self._action(sim_menu, "Run / pause", self.simulation.play.toggle, "P")
        self._action(sim_menu, "Step tick", self._step_tick, "T")
        self._action(sim_menu, "Step event", self._step_event, "E")
        self._action(sim_menu, "Tick back", self._tick_back, "Shift+T")
        self._action(sim_menu, "Step back", self._step_back, "Shift+E")
        region_menu = bar.addMenu("&Region")
        self._action(region_menu, "Mark selection corner", self._mark_corner, "B")
        self._action(region_menu, "Copy selection", self._copy, QKeySequence.StandardKey.Copy)
        self._action(region_menu, "Paste at target", self._paste, QKeySequence.StandardKey.Paste)
        self._action(region_menu, "Rotate clipboard 90°", self._rotate_clipboard, "R")
        self._action(region_menu, "Clear selection (fill with air)", self._delete_region, "Del")
        view_menu = bar.addMenu("&View")
        for dock in self.findChildren(QDockWidget):
            view_menu.addAction(dock.toggleViewAction())
        hotbar_menu = bar.addMenu("&Hotbar")
        for index, block_id in enumerate(HOTBAR, start=1):
            block = blocks.get(block_id)
            self._action(
                hotbar_menu,
                f"{index}: {block.name}",
                lambda _=False, b=block: self.palette.select_block(b),
                str(index),
            )
        help_menu = bar.addMenu("&Help")
        self._action(help_menu, "Controls", lambda: self.help_dock.setVisible(True), "F1")

    # ------------------------------------------------------------------ refresh
    def _changed(self) -> None:
        self.viewport.refresh()
        self.inspector.show_block(self.document, self.viewport.selection)
        self.simulation.show_status(self.document)
        self.sections.refresh()
        self.contraptions.show_document(self.document)
        if self.diagnostics_dock.isVisible():
            self.diagnostics.show_state(self.document, self.last_steps)
        name = self.document.path.name if self.document.path else "untitled"
        self.setWindowTitle(
            f"Redstone Simulator (Java 26.3) — {name}{' *' if self.document.dirty else ''}"
        )

    def _message(self, text: str, error: bool = False) -> None:
        self.statusBar().showMessage(text, 6000 if error else 3000)

    # ------------------------------------------------------------------ editing
    def _choose_block(self, block: Any) -> None:
        self.current_block = block
        self._message(f"Placing: {block.name}")

    def _hover(self, hit: Hit | None) -> None:
        if hit is None:
            self.statusBar().clearMessage()
            return
        state = self.document.state_at(hit.pos)
        self.statusBar().showMessage(f"{hit.pos}  {state!r}")

    def _edit(self, function: Any, *args: Any) -> None:
        self.document.notice = ""
        try:
            function(*args)
        except EditError as exc:
            self._message(str(exc), error=True)
        if self.document.notice:
            self._message(self.document.notice)
        self._changed()

    def _place(self, hit: Hit, force: bool) -> None:
        state = self.document.state_at(hit.pos)
        if not force and Document.is_usable(state.block):
            self._edit(self.document.use, hit.pos)
            return
        target: Pos = offset(hit.pos, hit.face)
        yaw, pitch = self.viewport.player_view()
        request = PlaceRequest(hit.face, yaw, pitch)
        self._edit(self.document.place, target, self.current_block, request)

    def _break(self, pos: Pos) -> None:
        self._edit(self.document.break_block, pos)

    def _pick(self, pos: Pos) -> None:
        block = self.document.state_at(pos).block
        if isinstance(block, RedstoneWallTorchBlock):
            block = blocks.REDSTONE_TORCH
        self.palette.select_block(block)

    def _select(self, pos: Pos | None) -> None:
        self.viewport.selection = pos
        self._changed()

    def _apply_state(self, pos: Pos, state: Any) -> None:
        self._edit(self.document.setblock, pos, state)

    def _assign_section(self, pos: Pos, name: str | None) -> None:
        self.document.assign_section(pos, name)
        self._changed()

    def _undo(self) -> None:
        self.simulation.play.setChecked(False)
        if not self.document.undo():
            self._message("Nothing to undo.")
        self._changed()

    def _redo(self) -> None:
        if not self.document.redo():
            self._message("Nothing to redo.")
        self._changed()

    # ------------------------------------------------------------------ regions
    def _mark_corner(self) -> None:
        hit = self.viewport.hover
        if hit is None:
            self._message("Point at a block to mark a selection corner.")
            return
        if self._corner is None or self.viewport.region is not None and self._corner_done:
            self._corner = hit.pos
            self._corner_done = False
            self.viewport.region = Region.from_corners(hit.pos, hit.pos)
            self._message(f"Selection corner 1 at {hit.pos}; press B again for corner 2.")
        else:
            self.viewport.region = Region.from_corners(self._corner, hit.pos)
            self._corner_done = True
            size = self.viewport.region.size
            self._message(f"Selected {size[0]}×{size[1]}×{size[2]} blocks.")
        self.viewport.update()

    def _region(self) -> Region | None:
        if self.viewport.region is None:
            self._message("No selection: press B on two corner blocks first.", error=True)
        return self.viewport.region

    def _copy(self) -> None:
        region = self._region()
        if region is not None:
            prefab = self.document.copy(region)
            self._message(f"Copied {prefab.non_air_count} blocks (with air: {len(prefab.blocks)}).")

    def _paste(self) -> None:
        hit = self.viewport.hover
        if hit is None:
            self._message("Point at the place to paste.", error=True)
            return
        self._edit(self.document.paste, offset(hit.pos, hit.face))

    def _rotate_clipboard(self) -> None:
        if self.document.clipboard is None:
            self._message("The clipboard is empty.")
            return
        self.document.rotate_clipboard(1)
        self._message("Clipboard rotated 90° clockwise.")

    def _delete_region(self) -> None:
        region = self._region()
        if region is not None:
            self._edit(self.document.fill, region, blocks.AIR.default_state)

    def _save_prefab(self) -> None:
        region = self._region()
        if region is None:
            return
        name, ok = QInputDialog.getText(self, "Save prefab", "Name:")
        if ok and name:
            self.document.save_prefab(name, region)
            self._changed()

    def _load_prefab(self, name: str) -> None:
        self.document.clipboard = self.document.prefabs[name]
        self._message(f"Prefab '{name}' is in the clipboard: Ctrl+V to paste.")

    def _delete_prefab(self, name: str) -> None:
        self.document.prefabs.pop(name, None)
        self._changed()

    def _import_prefab(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import prefab", "", "Prefabs (*.json)")
        if path:
            try:
                prefab = Prefab.from_json(json.loads(Path(path).read_text()))
            except (OSError, ValueError, KeyError) as exc:
                QMessageBox.critical(self, "Cannot import prefab", str(exc))
                return
            self.document.prefabs[prefab.name] = prefab
            self._changed()

    def _export_prefab(self, name: str) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export prefab", f"{name}.prefab.json", "Prefabs (*.json)"
        )
        if path:
            Path(path).write_text(
                json.dumps(self.document.prefabs[name].to_json(), indent=1) + "\n"
            )

    def _create_group(self) -> None:
        region = self._region()
        if region is None:
            return
        name, ok = QInputDialog.getText(self, "New group", "Name:")
        if ok and name:
            self.document.groups.add(Group(name, region))
            self._changed()

    def _add_port(self, group_name: str) -> None:
        pos = self.viewport.selection
        if pos is None:
            self._message("Ctrl+click the block to expose as a port first.", error=True)
            return
        role, ok = QInputDialog.getItem(self, "Port", "Role:", ["input", "output"], 0, False)
        if not ok:
            return
        name, ok = QInputDialog.getText(self, "Port", "Port name:")
        if ok and name:
            self.document.groups.groups[group_name].ports.append(
                Port(name, pos, "input" if role == "input" else "output")
            )
            self._changed()

    def _toggle_port(self, group_name: str, index: int) -> None:
        port = self.document.groups.groups[group_name].ports[index]
        if port.role != "input":
            return
        state = self.document.state_at(port.pos)
        if Document.is_usable(state.block):
            self._edit(self.document.use, port.pos)
        else:
            self._message(f"{state.block.name} at {port.pos} cannot be used directly.")

    def _delete_group(self, name: str) -> None:
        self.document.groups.remove(name)
        self._changed()

    # ------------------------------------------------------------------ simulation
    def _play(self, on: bool) -> None:
        if on:
            self.play_timer.start(max(1, int(1000 / self.simulation.speed.value())))
        else:
            self.play_timer.stop()

    def _speed(self, tps: int) -> None:
        if self.play_timer.isActive():
            self.play_timer.start(max(1, int(1000 / tps)))

    def _play_tick(self) -> None:
        if self.simulation.warp.isChecked():
            deadline = time.monotonic() + 0.04
            while time.monotonic() < deadline:
                self.last_steps = self.document.run_tick()
        else:
            self.last_steps = self.document.run_tick()
        self._changed()

    def _step_tick(self) -> None:
        self.last_steps = self.document.run_tick()
        self._changed()

    def _step_event(self) -> None:
        self.last_steps = [self.document.step()]
        self._changed()

    def _rewound(self, moved: bool) -> None:
        self.simulation.play.setChecked(False)
        self.last_steps = []
        if not moved:
            self._message("Already at the start of the recorded history.")
        self._changed()

    def _tick_back(self) -> None:
        self._rewound(self.document.tick_back())

    def _step_back(self) -> None:
        self._rewound(self.document.step_back())

    def _seek(self, step_index: int) -> None:
        self.simulation.play.setChecked(False)
        self.document.seek(step_index)
        self.last_steps = []
        self._changed()

    # ------------------------------------------------------------------ files
    def _confirm_discard(self) -> bool:
        if not self.document.dirty:
            return True
        answer = QMessageBox.question(self, "Unsaved changes", "Discard unsaved changes?")
        return answer == QMessageBox.StandardButton.Yes

    def _set_document(self, document: Document) -> None:
        self.simulation.play.setChecked(False)
        self.document = document
        self.last_steps = []
        self.viewport.set_document(document)
        self.sections.set_document(document)
        self._changed()

    def _new(self) -> None:
        if self._confirm_discard():
            self._set_document(Document.new_flat())

    def _open(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open world", "", FILE_FILTER)
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path) -> None:
        try:
            self._set_document(Document.open(path))
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(self, "Cannot open file", str(exc))

    def _save(self) -> None:
        if self.document.path is None:
            self._save_as()
            return
        self._edit(self.document.save)
        self._message(f"Saved {self.document.path}")

    def _save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save world", "circuit.redsim.json", FILE_FILTER
        )
        if path:
            self._edit(self.document.save, Path(path))
            self._message(f"Saved {path}")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
