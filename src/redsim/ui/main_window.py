"""Main window: viewport in the center, panels around it, menus and shortcuts."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QWidget,
)

from redsim.core.pos import Pos, offset
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document, EditError
from redsim.editor.groups import Group, Port
from redsim.editor.placement import PlaceRequest
from redsim.ui.camera import Camera
from redsim.ui.geometry import Hit
from redsim.ui.keymap import SPECS, Keymap, default_path
from redsim.ui.pacing import RateMeter, TickPacer
from redsim.ui.panels import (
    HOTBAR,
    ContraptionsPanel,
    DiagnosticsPanel,
    InspectorPanel,
    PalettePanel,
    SectionsPanel,
    SimulationPanel,
    controls_help,
    controls_help_html,
)
from redsim.ui.viewport import BUILD, NORMAL, SELECT, Viewport
from redsim.world import blocks
from redsim.world.blocks.torch import RedstoneWallTorchBlock

FILE_FILTER = "Redstone simulator worlds (*.redsim.json *.json)"
#: Run loop: timer period, the longest it may simulate in one go (keeps the UI responsive),
#: and how often the side panels refresh while running.
PLAY_INTERVAL_MS = 5
RUN_BUDGET_SECONDS = 0.035
PANEL_REFRESH_SECONDS = 0.1


class MainWindow(QMainWindow):
    def __init__(self, document: Document | None = None, keymap: Keymap | None = None) -> None:
        super().__init__()
        self.document = document or Document.new_flat()
        self.keymap = keymap if keymap is not None else Keymap.load()
        self.current_block = blocks.STONE
        self.last_steps: list[Any] = []
        self.viewport = Viewport(self.document, self.keymap)
        self.setCentralWidget(self.viewport)

        self.block_palette = PalettePanel()
        self.inspector = InspectorPanel()
        self.simulation = SimulationPanel()
        self.diagnostics = DiagnosticsPanel()
        self.sections = SectionsPanel(self.document)
        left = Qt.DockWidgetArea.LeftDockWidgetArea
        right = Qt.DockWidgetArea.RightDockWidgetArea
        blocks_dock = self._dock("Blocks", self.block_palette, left)
        self.help_label = controls_help(self.keymap)
        help_scroll = QScrollArea()  # the generated list is long: never let it size the window
        help_scroll.setWidget(self.help_label)
        help_scroll.setWidgetResizable(True)
        self.help_dock = self._dock("Controls", help_scroll, left)
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

        self.play_timer = QTimer(self)
        self.play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.play_timer.timeout.connect(self._play_tick)
        self.pacer = TickPacer(self.simulation.speed.value())
        self.tick_rate = RateMeter()
        self._panels_refreshed = 0.0
        self._actions: dict[str, QAction] = {}
        self._mode_actions: dict[str, QAction] = {}
        self._connect()
        self._build_menus()
        self._apply_saved_camera()
        self._changed()
        if self.keymap.warnings:
            self._message("Keymap: " + "; ".join(self.keymap.warnings), error=True)

    # ------------------------------------------------------------------ setup
    def _dock(self, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(title)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _connect(self) -> None:
        self.block_palette.block_chosen.connect(self._choose_block)
        self.viewport.hover_changed.connect(self._hover)
        self.viewport.place_requested.connect(self._place)
        self.viewport.use_requested.connect(self._use)
        self.viewport.break_requested.connect(self._break)
        self.viewport.pick_requested.connect(self._pick)
        self.viewport.select_requested.connect(self._select)
        self.viewport.region_changed.connect(self._region_changed)
        self.viewport.mode_changed.connect(self._mode_changed)
        self.inspector.apply_requested.connect(self._apply_state)
        self.inspector.section_requested.connect(self._assign_section)
        self.sections.changed.connect(lambda: self._changed())
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

    def _action(self, menu: Any, text: str, slot: Any, keymap_id: str | None = None) -> QAction:
        """A menu action; its shortcuts come from the keymap entry ``keymap_id``."""
        action = QAction(text, self)
        action.triggered.connect(slot)
        menu.addAction(action)
        self.addAction(action)
        if keymap_id is not None:
            self._actions[keymap_id] = action
            self._apply_shortcuts(keymap_id)
        return action

    def _apply_shortcuts(self, keymap_id: str) -> None:
        shortcuts = [QKeySequence(binding) for binding in self.keymap.bindings(keymap_id)]
        self._actions[keymap_id].setShortcuts(shortcuts)

    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")
        self._action(file_menu, "&New", self._new, "file.new")
        self._action(file_menu, "&Open…", self._open, "file.open")
        self._action(file_menu, "&Save", self._save, "file.save")
        self._action(file_menu, "Save &as…", self._save_as, "file.save_as")
        file_menu.addSeparator()
        self._action(file_menu, "&Quit", self.close, "file.quit")
        edit_menu = bar.addMenu("&Edit")
        self._action(edit_menu, "&Undo", self._undo, "edit.undo")
        self._action(edit_menu, "&Redo", self._redo, "edit.redo")
        mode_menu = bar.addMenu("&Mode")
        group = QActionGroup(self)
        for mode, text in ((NORMAL, "&Normal"), (BUILD, "&Build"), (SELECT, "&Select")):
            action = self._action(mode_menu, text, lambda _=False, m=mode: self._mode_key(m))
            self._actions[f"mode.{mode}"] = action
            self._apply_shortcuts(f"mode.{mode}")
            action.setCheckable(True)
            action.setToolTip(SPECS[f"mode.{mode}"].title)
            group.addAction(action)
            self._mode_actions[mode] = action
        self._mode_actions[self.viewport.mode].setChecked(True)
        mode_menu.addSeparator()
        self._action(mode_menu, "Move pivot to the block", self._focus_pivot, "camera.focus")
        sim_menu = bar.addMenu("&Simulation")
        self._action(sim_menu, "Run / pause", self.simulation.play.toggle, "sim.run")
        self._action(sim_menu, "Step tick", self._step_tick, "sim.tick")
        self._action(sim_menu, "Step event", self._step_event, "sim.event")
        self._action(sim_menu, "Tick back", self._tick_back, "sim.tick_back")
        self._action(sim_menu, "Step back", self._step_back, "sim.step_back")
        region_menu = bar.addMenu("&Region")
        self._action(region_menu, "Copy selection", self._copy, "edit.copy")
        self._action(region_menu, "Paste at target", self._paste, "edit.paste")
        self._action(region_menu, "Rotate clipboard 90°", self._rotate_clipboard, "edit.rotate")
        self._action(
            region_menu, "Clear selection (fill with air)", self._delete_region, "edit.delete"
        )
        view_menu = bar.addMenu("&View")
        for dock in self.findChildren(QDockWidget):
            view_menu.addAction(dock.toggleViewAction())
        hotbar_menu = bar.addMenu("&Hotbar")
        for index, block_id in enumerate(HOTBAR, start=1):
            block = blocks.get(block_id)
            self._action(
                hotbar_menu,
                f"{index}: {block.name}",
                lambda _=False, b=block: self.block_palette.select_block(b),
                f"hotbar.{index}",
            )
        settings_menu = bar.addMenu("Se&ttings")
        self._action(settings_menu, "Edit keymap file…", self._edit_keymap)
        self._action(settings_menu, "Reload keymap", self._reload_keymap)
        help_menu = bar.addMenu("&Help")
        self._action(
            help_menu, "Controls", lambda: self.help_dock.setVisible(True), "help.controls"
        )

    # ------------------------------------------------------------------ modes and keymap
    def _mode_key(self, mode: str) -> None:
        """Mode shortcuts; the NORMAL key pressed in NORMAL mode clears the selections."""
        if mode == NORMAL and self.viewport.mode == NORMAL:
            self.viewport.region = None
            self._select(None)
            return
        self.viewport.set_mode(mode)

    def _mode_changed(self, mode: str) -> None:
        self._mode_actions[mode].setChecked(True)
        self._message(f"{mode.upper()} mode: {self.viewport.mode_hint()}")

    def _focus_pivot(self) -> None:
        if not self.viewport.focus_hover():
            self._message("Point at a block to move the pivot there.")

    def _edit_keymap(self) -> None:
        path = default_path()
        if not path.exists():
            Keymap.write_defaults(path)
        self._message(f"Keymap file: {path} (Settings → Reload keymap after editing)")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _reload_keymap(self) -> None:
        self.set_keymap(Keymap.load())
        if self.keymap.warnings:
            self._message("Keymap: " + "; ".join(self.keymap.warnings), error=True)
        else:
            self._message(f"Keymap reloaded from {default_path()}")

    def set_keymap(self, keymap: Keymap) -> None:
        self.keymap = keymap
        for keymap_id in self._actions:
            self._apply_shortcuts(keymap_id)
        self.viewport.set_keymap(keymap)
        self.help_label.setText(controls_help_html(keymap))

    # ------------------------------------------------------------------ refresh
    def _changed(self, running: bool = False) -> None:
        """Refresh views after any change; while running, panels refresh at a lower rate."""
        self.viewport.overlay_text = self._overlay_text(self.play_timer.isActive())
        self.viewport.refresh()
        now = time.monotonic()
        if running and now - self._panels_refreshed < PANEL_REFRESH_SECONDS:
            return
        self._panels_refreshed = now
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

    def _overlay_text(self, running: bool) -> list[str]:
        game_time = self.document.engine.game_time
        if not running:
            return [f"paused · game time {game_time}"]
        now = time.monotonic()
        if self.simulation.warp.isChecked():
            target = "warp"
        else:
            target = f"target {self.simulation.speed.value()}"
        return [
            f"running · {self.tick_rate.rate(now):5.1f} ticks/s ({target})",
            f"game time {game_time} · {self.viewport.frame_rate.rate(now):3.0f} frames/s",
        ]

    def _message(self, text: str, error: bool = False) -> None:
        self.statusBar().showMessage(text, 6000 if error else 3000)

    # ------------------------------------------------------------------ editing
    def _choose_block(self, block: Any) -> None:
        """Choosing a block to place (palette, hotbar, pick) enters BUILD mode."""
        self.current_block = block
        self.viewport.set_mode(BUILD)
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

    def _place(self, hit: Hit) -> None:
        target: Pos = offset(hit.pos, hit.face)
        yaw, pitch = self.viewport.player_view()
        request = PlaceRequest(hit.face, yaw, pitch)
        self._edit(self.document.place, target, self.current_block, request)

    def _use(self, pos: Pos) -> None:
        block = self.document.state_at(pos).block
        if Document.is_usable(block):
            self._edit(self.document.use, pos)
        else:
            self._message(f"{block.name} cannot be used (to place blocks, switch to BUILD mode).")

    def _break(self, pos: Pos) -> None:
        self._edit(self.document.break_block, pos)

    def _pick(self, pos: Pos) -> None:
        block = self.document.state_at(pos).block
        if isinstance(block, RedstoneWallTorchBlock):
            block = blocks.REDSTONE_TORCH
        self.block_palette.select_block(block)

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
    def _region_changed(self, region: Region | None) -> None:
        if region is not None:
            size = region.size
            self._message(f"Selected {size[0]}×{size[1]}×{size[2]} blocks.")

    def _region(self) -> Region | None:
        if self.viewport.region is None:
            self._message(
                "No selection: press V (select mode), then click or drag over blocks.", error=True
            )
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
            now = time.monotonic()
            self.pacer.rate = self.simulation.speed.value()
            self.pacer.start(now)
            self.tick_rate.reset(now)
            self.viewport.frame_rate.reset(now)
            self.play_timer.start(PLAY_INTERVAL_MS)
        else:
            self.play_timer.stop()
            self._changed()

    def _speed(self, tps: int) -> None:
        self.pacer.set_rate(tps, time.monotonic())

    def _play_tick(self) -> None:
        """Run the ticks that are due by the wall clock (decoupled from drawing).

        Rendering happens at most once per frame afterwards, however many ticks ran, so the
        simulation keeps its rate even when drawing is slow.
        """
        start = time.monotonic()
        warp = self.simulation.warp.isChecked()
        due = 1 << 30 if warp else self.pacer.due(start)
        ran = 0
        while ran < due:
            self.last_steps = self.document.run_tick()
            ran += 1
            if time.monotonic() - start > RUN_BUDGET_SECONDS:
                break
        if not warp:
            self.pacer.ran(ran)
        if ran:  # nothing changed otherwise: no repaint
            self.tick_rate.record(time.monotonic(), ran)
            self._changed(running=True)

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
        self._apply_saved_camera()
        self._changed()

    def _apply_saved_camera(self) -> None:
        """Restore the camera stored in the file (``extra["camera"]``), else a default view."""
        camera = self.document.extra.get("camera")
        self.viewport.camera = Camera.from_json(camera) if camera else Camera()
        self.viewport.update()

    def _store_camera(self) -> None:
        self.document.extra["camera"] = self.viewport.camera.to_json()

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
        self._store_camera()
        self._edit(self.document.save)
        self._message(f"Saved {self.document.path}")

    def _save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save world", "circuit.redsim.json", FILE_FILTER
        )
        if path:
            self._store_camera()
            self._edit(self.document.save, Path(path))
            self._message(f"Saved {path}")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
