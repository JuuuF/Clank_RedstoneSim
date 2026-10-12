"""Main window: viewport in the center, panels around it, menus and shortcuts."""

from __future__ import annotations

import contextlib
import json
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QByteArray, QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDesktopServices,
    QKeyEvent,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document, EditError
from redsim.editor.groups import Group, Port
from redsim.editor.placement import PlaceRequest
from redsim.mcworld.importer import open_world
from redsim.ui import pixel_icons, theme
from redsim.ui.block_search import BlockSearch
from redsim.ui.camera import Camera
from redsim.ui.debug_screen import world_lines
from redsim.ui.geometry import Hit
from redsim.ui.hints import Context, HintBar, context_hints
from redsim.ui.icons import block_icon
from redsim.ui.inventory import InventoryBar
from redsim.ui.keymap import SPECS, Keymap, default_path
from redsim.ui.keymap_editor import KeymapEditor
from redsim.ui.names import block_name
from redsim.ui.pacing import RateMeter, TickPacer
from redsim.ui.panels import (
    AboutDialog,
    ContraptionsPanel,
    DiagnosticsPanel,
    HotkeysPanel,
    InspectorPanel,
    PreferencesDialog,
    SectionsPanel,
)
from redsim.ui.preferences import load_window_layout, save_window_layout
from redsim.ui.timeline import TimelineBar
from redsim.ui.viewport import BUILD, MODE_COLORS, NORMAL, SELECT, Viewport
from redsim.world import blocks
from redsim.world.block import Block
from redsim.world.blocks.torch import RedstoneWallTorchBlock
from redsim.world.rotation import default_pivot2, rotate_state

FILE_FILTER = "Redstone simulator worlds (*.redsim.json *.json)"
#: Run loop: timer period, the longest it may simulate in one go (keeps the UI responsive),
#: and how often the side panels refresh while running.
PLAY_INTERVAL_MS = 5
RUN_BUDGET_SECONDS = 0.035
PANEL_REFRESH_SECONDS = 0.1


#: Where Minecraft keeps its saves (the example world first).
MINECRAFT_SAVE_FOLDERS = (
    Path("data/minecraft_saves"),
    Path.home() / ".minecraft" / "saves",
)


def _plain_cube(block_id: str) -> bool:
    """A foreign block that behaves like any full cube (quartz, bricks, …): nothing to warn
    about."""
    from redsim.world.blocks.foreign import foreign_block

    name = block_id.split(":", 1)[-1]
    block = foreign_block(block_id, {})
    plain_names = ("_block", "bricks", "planks", "wool", "concrete", "terracotta", "stone")
    components = ("note_block", "target", "observer", "dispenser", "dropper", "crafter", "bulb")
    return (
        block.full
        and block.conductor.value == "default"
        and name.endswith(plain_names)
        and not any(part in name for part in components)
    )


#: Steps listed under Edit → Undo History.
HISTORY_MENU_SIZE = 25


def history_label(label: str) -> str:
    """An edit label for people: "place redstone_wire" → "Place Redstone Dust"."""
    verb, _, rest = (label or "edit").partition(" ")
    if rest and " " not in rest and f"minecraft:{rest}" in blocks.REGISTRY:
        rest = block_name(f"minecraft:{rest}")
    else:
        rest = rest.replace("_", " ")
    return f"{verb[:1].upper()}{verb[1:]} {rest}".strip()


class MainWindow(QMainWindow):
    def __init__(self, document: Document | None = None, keymap: Keymap | None = None) -> None:
        super().__init__()
        app = QApplication.instance()
        if isinstance(app, QApplication) and not app.property("redsim_theme"):
            theme.apply(app)  # the dark Minecraft-meets-Blender look, once per app
            app.setProperty("redsim_theme", True)
        self.setWindowIcon(block_icon(blocks.REDSTONE_TORCH, 64))
        self.document = document or Document.new_flat()
        migrated = keymap is None and Keymap.migrate()  # old files listed every default
        self.keymap = keymap if keymap is not None else Keymap.load()
        self.current_block = blocks.STONE
        self.last_steps: list[Any] = []
        self.viewport = Viewport(self.document, self.keymap)
        # Layout: the 3D view in the middle, with the inventory drawn over its bottom in
        # BUILD mode like the game's hotbar (round 8); below it the Blender-like timeline;
        # one tabbed panel on the right; a Blender-like hint bar at the very bottom.
        self.simulation = TimelineBar()
        self.inventory = InventoryBar()
        central = QWidget()
        column = QVBoxLayout(central)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.viewport, 1)
        column.addWidget(self.simulation)
        self.viewport.add_overlay(self.inventory)
        self.inventory.setVisible(self.viewport.mode == BUILD)
        self.setCentralWidget(central)

        self.inspector = InspectorPanel()
        self.diagnostics = DiagnosticsPanel()
        self.sections = SectionsPanel(self.document)
        self.contraptions = ContraptionsPanel()
        self.hotkeys = HotkeysPanel(self.keymap)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)  # flat tabs, no frame (Blender-like)
        self.tabs.addTab(self.inspector, "Inspector")
        circuit = QTabWidget()
        circuit.setProperty("subtabs", True)
        circuit.setDocumentMode(True)
        circuit.addTab(self.sections, "Sections")
        circuit.addTab(self.contraptions.group_page, "Groups")
        circuit.addTab(self.contraptions.prefab_page, "Prefabs")
        self.tabs.addTab(circuit, "Circuit")
        self.tabs.addTab(self.diagnostics, "Diagnostics")
        self.tabs.addTab(self.hotkeys, "Hotkeys")
        self.side_dock = self._dock("Properties", self.tabs, Qt.DockWidgetArea.RightDockWidgetArea)
        self.side_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.side_dock.setTitleBarWidget(QWidget())  # no title: the tabs name the panel
        self.resizeDocks([self.side_dock], [360], Qt.Orientation.Horizontal)
        self.hint_bar = HintBar()
        self.statusBar().addWidget(self.hint_bar, 1)
        self.statusBar().setSizeGripEnabled(False)

        self.play_timer = QTimer(self)
        self.play_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.play_timer.timeout.connect(self._play_tick)
        self.pacer = TickPacer(self.simulation.speed.value())
        self._hint_timer = QTimer(self)
        self._hint_timer.timeout.connect(self._update_hints)
        self._hint_timer.start(120)
        self._rotation_pivot: tuple[Region, tuple[int, int]] | None = None
        self.tick_rate = RateMeter()
        self._panels_refreshed = 0.0
        self._actions: dict[str, QAction] = {}
        self._mode_actions: dict[str, QAction] = {}
        self._connect()
        self._build_menus()
        self._apply_saved_camera()
        self._changed()
        if migrated:
            self._message(
                "Keymap file cleaned up: it now lists only your own changes "
                "(the old one is kept next to it as .bak)."
            )
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)  # the dead-key ^ (German layout)
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
        self.inventory.block_chosen.connect(self._choose_block)
        self.inventory.search_requested.connect(self._search_blocks)
        self.viewport.search_requested.connect(self._search_blocks)
        # Hand the keyboard back to the viewport, so mode and inventory keys keep working.
        self.inventory.strength.editingFinished.connect(self.viewport.setFocus)
        self.inventory.strength.valueChanged.connect(
            lambda value: self.viewport.set_build_block(self.current_block, value)
        )
        self.simulation.jump.connect(self._jump)
        self.simulation.canvas.scrub.connect(self._scrub)
        self.simulation.canvas.remove_monitor.connect(self._toggle_monitor)
        canvas = self.simulation.canvas
        canvas.move_edits.connect(
            lambda indices, delta: self._history_edit(self.document.move_edits, indices, delta)
        )
        canvas.merge_edits.connect(
            lambda indices, tick: self._history_edit(self.document.merge_edits, indices, tick)
        )
        canvas.delete_edits.connect(
            lambda indices: self._history_edit(self.document.delete_edits, indices)
        )
        canvas.set_tick_zero.connect(self._set_tick_zero)
        canvas.rename_marker.connect(self._rename_marker)
        canvas.delete_marker.connect(lambda tick: self._name_marker(tick, ""))
        self.simulation.set_tick_zero.connect(self._set_tick_zero)
        self.inspector.monitor_requested.connect(self._toggle_monitor)
        self.inspector.hit_requested.connect(self._projectile_hit)
        self.inspector.plate_requested.connect(self._plate_visitors)
        self.inspector.contents_requested.connect(self._set_container_slot)
        self.viewport.hover_changed.connect(self._hover)
        self.viewport.place_requested.connect(self._place)
        self.viewport.line_requested.connect(self._place_line)
        self.viewport.rotate_requested.connect(self._rotate_block_at)
        self.viewport.use_requested.connect(self._use)
        self.viewport.break_requested.connect(self._break)
        self.viewport.pick_requested.connect(self._pick)
        self.viewport.select_requested.connect(self._select)
        self.viewport.region_changed.connect(self._region_changed)
        self.viewport.region_move_requested.connect(self._move_region)
        self.viewport.region_stack_requested.connect(self._stack_region)
        self.viewport.transform_requested.connect(self._gizmo_transform)
        self.viewport.paste_requested.connect(self._paste_at)
        self.viewport.mode_changed.connect(self._mode_changed)
        self.viewport.mode_changed.connect(self.hotkeys.set_mode)
        self.inspector.apply_requested.connect(self._apply_state)
        self.inspector.source_requested.connect(self._set_source)
        self.inspector.page_requested.connect(self._turn_page)
        self.inspector.section_requested.connect(self._assign_section)
        self.sections.changed.connect(lambda: self._changed())
        self.simulation.play_toggled.connect(self._play)
        self.simulation.step_tick.connect(self._step_tick)
        self.simulation.step_event.connect(self._step_event)
        self.simulation.tick_back.connect(self._tick_back)
        self.simulation.step_back.connect(self._step_back)
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
        self._action(file_menu, "Open Minecraft world…", self._open_minecraft_world)
        self._action(file_menu, "&Save", self._save, "file.save")
        self._action(file_menu, "Save &as…", self._save_as, "file.save_as")
        file_menu.addSeparator()
        self._action(file_menu, "&Quit", self.close, "file.quit")
        edit_menu = bar.addMenu("&Edit")
        self._action(edit_menu, "&Undo", self._undo, "edit.undo").setIcon(
            pixel_icons.pixel_icon("undo")
        )
        self._action(edit_menu, "&Redo", self._redo, "edit.redo").setIcon(
            pixel_icons.pixel_icon("redo")
        )
        self._history_menu = edit_menu.addMenu("Undo History")
        self._history_menu.aboutToShow.connect(self._fill_history_menu)
        edit_menu.addSeparator()
        self._action(
            edit_menu, "Rotate block clockwise", lambda: self._rotate_block(1), "edit.rotate_block"
        ).setIcon(pixel_icons.pixel_icon("rotate"))
        self._action(
            edit_menu,
            "Rotate block counter-clockwise",
            lambda: self._rotate_block(3),
            "edit.rotate_block_back",
        ).setIcon(pixel_icons.pixel_icon("rotate_back"))
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
        # The transport buttons' pixel icons, where a button does the same.
        for text, slot, keymap_id, icon in (
            ("Run / pause", self.simulation.play.toggle, "sim.run", "play"),
            (
                "Play backwards / pause",
                self.simulation.reverse.toggle,
                "sim.run_back",
                "reverse",
            ),
            ("Set tick 0 here", self._set_tick_zero, "sim.set_zero", "tick_zero"),
            ("Step tick", self._step_tick, "sim.tick", "step"),
            ("Step event", self._step_event, "sim.event", None),
            ("Tick back", self._tick_back, "sim.tick_back", "back"),
            ("Step back", self._step_back, "sim.step_back", None),
        ):
            action = self._action(sim_menu, text, slot, keymap_id)
            if icon:
                action.setIcon(pixel_icons.pixel_icon(icon))
        self._action(sim_menu, "Add marker…", self._add_marker, "sim.marker").setIcon(
            pixel_icons.pixel_icon("tick_zero")
        )
        sim_menu.addSeparator()
        for text, where, keymap_id in (
            ("Jump to start", "start", "sim.start"),
            ("Jump to end", "end", "sim.end"),
            ("Previous edit", "previous", "sim.prev_edit"),
            ("Next edit", "next", "sim.next_edit"),
        ):
            action = self._action(sim_menu, text, lambda _=False, w=where: self._jump(w), keymap_id)
            action.setIcon(pixel_icons.pixel_icon(where))
        region_menu = bar.addMenu("&Region")
        toolbar = self.addToolBar("Tools")
        toolbar.setObjectName("Tools toolbar")
        toolbar.setMovable(False)
        for mode in (NORMAL, BUILD, SELECT):
            self._mode_actions[mode].setIcon(pixel_icons.pixel_icon(mode))
            toolbar.addAction(self._mode_actions[mode])
            button = toolbar.widgetForAction(self._mode_actions[mode])
            if button is not None:  # checked: the mode's badge color (viewport corner)
                color = MODE_COLORS[mode]
                button.setStyleSheet(
                    f"QToolButton:checked {{ background: {color.name()}; "
                    f"border: 1px solid {color.lighter(130).name()}; color: #ffffff; }}"
                )
        toolbar.addSeparator()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.setIconSize(pixel_icons.ICON_SIZE)
        #: Region buttons, dimmed while they have nothing to work on (the actions stay
        #: enabled: their shortcuts explain why nothing happens).
        self._region_buttons: dict[str, QToolButton] = {}
        # Menu text, toolbar label (None: the icon alone), pixel icon. Pairs share a label.
        for text, short, icon, slot, keymap_id in (
            ("Rotate clockwise", "Rotate", "rotate", lambda: self._rotate(1), "edit.rotate"),
            (
                "Rotate counter-clockwise",
                None,
                "rotate_back",
                lambda: self._rotate(3),
                "edit.rotate_back",
            ),
            ("Flip left/right", "Flip", "flip", lambda: self._flip(depth=False), "edit.flip"),
            (
                "Flip front/back",
                None,
                "flip_depth",
                lambda: self._flip(depth=True),
                "edit.flip_depth",
            ),
            ("Copy", "Copy", "copy", self._copy, "edit.copy"),
            ("Paste", "Paste", "paste", self._paste, "edit.paste"),
            ("Delete", "Delete", "delete", self._delete_region, "edit.delete"),
            ("Lock", "Lock", "lock", self._toggle_lock, "select.lock"),
        ):
            action = self._action(region_menu, text, slot, keymap_id)
            action.setIcon(pixel_icons.pixel_icon(icon))
            if keymap_id == "select.lock":  # pressed while the selection is locked
                action.setCheckable(True)
                self._lock_action = action
            action.setIconText(short or text)
            action.setToolTip(f"{SPECS[keymap_id].title} ({self.keymap.describe(keymap_id)})")
            toolbar.addAction(action)
            button = toolbar.widgetForAction(action)
            if isinstance(button, QToolButton):
                self._region_buttons[keymap_id] = button
            if short is None and isinstance(button, QToolButton):
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            if keymap_id in ("edit.rotate_back", "edit.flip_depth", "edit.paste"):
                toolbar.addSeparator()
        view_menu = bar.addMenu("&View")
        for attribute, text, tip in (
            (
                "show_sections",
                "Show sections",
                "Sections: colored outlines of single blocks (Sections panel), e.g. blue "
                "inputs, green outputs, orange processing. Annotations only.",
            ),
            (
                "show_groups",
                "Show groups",
                "Groups: white boxes around named contraptions with input/output ports "
                "(Circuit → Groups). Annotations only.",
            ),
        ):
            toggle = self._action(
                view_menu, text, lambda on, a=attribute: self._set_view_flag(a, on)
            )
            toggle.setCheckable(True)
            toggle.setChecked(True)
            toggle.setToolTip(tip)
            toggle.setStatusTip(tip)
        info = self._action(
            view_menu,
            "Info overlay (signal values)",
            lambda on: self._set_view_flag("show_info", on),
            "view.info",
        )
        info.setCheckable(True)
        info.setToolTip(SPECS["view.info"].title)
        textures = self._action(view_menu, "Game textures", self._toggle_textures)
        self._textures_action = textures
        textures.setCheckable(True)
        textures.setChecked(self.viewport.atlas is not None)
        textures.setEnabled(self.viewport.textures_available)
        textures.setToolTip(
            "Draw blocks with the game's own models and textures, read from the supplied "
            "client jar (data/minecraft_jars/client.jar). Off: simple colored models."
        )
        scenery = self._action(view_menu, "Scenery (ground and clouds)", self._toggle_scenery)
        self._scenery_action = scenery
        scenery.setCheckable(True)
        scenery.setChecked(self.viewport.preferences.scenery)
        scenery.setToolTip(
            "A grass superflat around the floor fading into the horizon, and the game's "
            "clouds. Off: the floor alone in the sky."
        )
        self._action(view_menu, "Cycle X-ray", self._cycle_xray, "view.xray")
        xray_group = QActionGroup(self)
        self._xray_actions = []
        for level, text in enumerate(("X-ray off", "X-ray: building blocks", "X-ray: everything")):
            action = self._action(view_menu, text, lambda _=False, v=level: self._set_xray(v))
            action.setCheckable(True)
            action.setChecked(level == 0)
            xray_group.addAction(action)
            self._xray_actions.append(action)
        view_menu.setToolTipsVisible(True)
        view_menu.addSeparator()
        for dock in self.findChildren(QDockWidget):
            view_menu.addAction(dock.toggleViewAction())
        inventory_menu = bar.addMenu("&Inventory")
        for number in range(1, 10):
            self._action(
                inventory_menu,
                f"Slot {number}",
                lambda _=False, n=number: self._inventory_key(n),
                f"inventory.{number}",
            )
        for number in range(1, 10):
            self._action(
                inventory_menu,
                f"Recent block {number}",
                lambda _=False, n=number: self.inventory.pick_recent(n - 1),
                f"recent.{number}",
            )
        self._action(inventory_menu, "Up one folder", self.inventory.go_up, "inventory.up")
        self._action(
            inventory_menu, "Search blocks…", self._search_blocks, "search.blocks"
        ).setIcon(pixel_icons.pixel_icon("search"))
        settings_menu = bar.addMenu("Se&ttings")
        self._action(settings_menu, "Preferences…", self._preferences)
        self._action(settings_menu, "Keymap…", self._open_keymap_editor)
        self._action(settings_menu, "Edit keymap file…", self._edit_keymap)
        self._action(settings_menu, "Reload keymap", self._reload_keymap)
        help_menu = bar.addMenu("&Help")
        self._action(help_menu, "Controls", self._show_controls, "help.controls")
        help_menu.addSeparator()
        self._action(help_menu, "About Redstone Simulator", lambda: AboutDialog(self).exec())

    # ------------------------------------------------------------------ modes and keymap
    def _mode_key(self, mode: str) -> None:
        """Mode shortcuts; the NORMAL key pressed in NORMAL mode clears the selections."""
        if mode == NORMAL and self.viewport.region_locked:
            self.viewport.region_locked = False
            self.viewport.update()
            self._message("Selection unlocked.")
            return
        if mode == NORMAL and self.viewport.paste_preview is not None:
            self.viewport.cancel_paste()
            self._message("Paste cancelled.")
            return
        if mode == NORMAL and self.viewport.mode == NORMAL:
            self.viewport.region = None
            self._select(None)
            return
        self.viewport.set_mode(mode)

    def _inventory_key(self, number: int) -> None:
        """1–9: the inventory is only shown in BUILD mode, so a number key goes there."""
        if self.viewport.mode != BUILD:
            self.viewport.set_mode(BUILD)
        self.inventory.press(number)

    def _mode_changed(self, mode: str) -> None:
        self._mode_actions[mode].setChecked(True)
        self.inventory.setVisible(mode == BUILD)  # the hotbar belongs to BUILD mode
        self._message(f"{mode.upper()} mode: {self.viewport.mode_hint()}")

    def _show_controls(self) -> None:
        """Show every binding: the side panel's Hotkeys tab."""
        self.side_dock.show()
        self.tabs.setCurrentWidget(self.hotkeys)

    def _cycle_xray(self) -> None:
        self._set_xray((self.viewport.xray + 1) % 3)

    def _set_xray(self, level: int) -> None:
        self.viewport.xray = level
        self._xray_actions[level].setChecked(True)
        labels = ("off", "building blocks see-through", "everything see-through")
        self._message(f"X-ray: {labels[level]} (Alt+Z cycles; levels in Settings → Preferences)")
        self.viewport.update()

    def _toggle_textures(self, on: bool) -> None:
        self.viewport.set_game_textures(on)
        self.viewport.preferences.game_textures = on
        with contextlib.suppress(OSError):
            self.viewport.preferences.save()

    def _toggle_scenery(self, on: bool) -> None:
        self.viewport.preferences.scenery = on
        with contextlib.suppress(OSError):
            self.viewport.preferences.save()
        self.viewport.update()

    def _preferences(self) -> None:
        dialog = PreferencesDialog(
            self.viewport.preferences, self, self.viewport.textures_available
        )
        dialog.changed.connect(self.viewport.update)
        dialog.look_changed.connect(self._apply_look)
        dialog.exec()
        self.viewport.preferences.save()

    def _apply_look(self, attribute: str, on: bool) -> None:
        """A look switched in the Preferences dialog: apply it and update the View menu."""
        if attribute == "game_textures":
            self._toggle_textures(on)
            self._textures_action.setChecked(on)
        elif attribute == "scenery":
            self._toggle_scenery(on)
            self._scenery_action.setChecked(on)
        elif attribute == "trackpad_navigation":
            self.viewport.preferences.trackpad_navigation = on
            with contextlib.suppress(OSError):
                self.viewport.preferences.save()

    def _set_view_flag(self, attribute: str, on: bool) -> None:
        setattr(self.viewport, attribute, on)
        self.viewport.update()

    def _focus_pivot(self) -> None:
        if not self.viewport.focus_hover():
            self._message("Point at a block to move the pivot there.")

    def _open_keymap_editor(self) -> None:
        editor = KeymapEditor(self.keymap, self)
        editor.applied.connect(self._keymap_saved)
        editor.exec()

    def _keymap_saved(self, keymap: Keymap) -> None:
        self.set_keymap(keymap)
        self._message(f"Keymap saved ({len(keymap.changes())} changes from the defaults).")

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
        self.hotkeys.set_keymap(keymap)

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
        if self.tabs.currentWidget() is self.diagnostics:
            self.diagnostics.show_state(self.document, self.last_steps)
        name = self.document.path.name if self.document.path else "untitled"
        self.setWindowTitle(
            f"Redstone Simulator (Java 26.3) — {name}{' *' if self.document.dirty else ''}"
        )

    def _overlay_text(self, running: bool) -> list[str]:
        tick = self.document.tick
        if not running:
            return ["paused · the build (tick 0)" if tick == 0 else f"paused · tick {tick}"]
        now = time.monotonic()
        if self.simulation.warp.isChecked():
            target = "warp"
        else:
            target = f"target {self.simulation.speed.value()}"
        return [
            f"running · {self.tick_rate.rate(now):5.1f} ticks/s ({target})",
            f"tick {tick} · {self.viewport.frame_rate.rate(now):3.0f} frames/s",
        ]

    def _message(self, text: str, error: bool = False) -> None:
        self.hint_bar.show_message(text, error)

    def _update_hints(self) -> None:
        viewport = self.viewport
        locked = viewport.region_locked and viewport.region is not None
        if self._lock_action.isChecked() != locked:
            self._lock_action.setChecked(locked)
        has_region = viewport.region is not None
        transformable = has_region or viewport.paste_preview is not None
        usable = {
            "edit.rotate": transformable,
            "edit.rotate_back": transformable,
            "edit.flip": transformable,
            "edit.flip_depth": transformable,
            "edit.copy": has_region,
            "edit.paste": self.document.clipboard is not None,
            "edit.delete": has_region,
            "select.lock": has_region,
        }
        for keymap_id, on in usable.items():
            button = self._region_buttons.get(keymap_id)
            if button is not None and button.isEnabled() != on:
                button.setEnabled(on)
        spot = viewport.gizmo_hover
        context = Context(
            mode=viewport.mode,
            has_region=viewport.region is not None,
            locked=viewport.region_locked,
            pasting=viewport.paste_preview is not None,
            shift=viewport._shift,
            gizmo=spot.kind if spot is not None else None,
            running=self.play_timer.isActive(),
        )
        self.hint_bar.show_hints(context_hints(self.keymap, context))
        if viewport.show_info:
            viewport.debug_left = self._debug_lines()
            viewport.update()

    def _debug_lines(self) -> list[str]:
        viewport, camera = self.viewport, self.viewport.camera
        now = time.monotonic()
        target = "warp" if self.simulation.warp.isChecked() else self.simulation.speed.value()
        running = "running" if self.play_timer.isActive() else "paused"
        rates = (
            f"{running} · {self.tick_rate.rate(now):.1f} ticks/s (target {target}) · "
            f"{viewport.frame_rate.rate(now):.0f} frames/s"
        )
        px, py, pz = (float(v) for v in camera.pivot)
        facing = ("south", "west", "north", "east")[round(camera.yaw / 90) % 4]
        view = (
            f"Pivot: {px:.1f} / {py:.1f} / {pz:.1f} · yaw {camera.yaw:.0f} pitch "
            f"{camera.pitch:.0f} · facing {facing} · distance {camera.distance:.1f}"
        )
        return world_lines(
            self.document, rates, view, viewport.mode, viewport.region, viewport.region_locked
        )

    def _set_tick_zero(self) -> None:
        self._history_edit(self.document.set_tick_zero)

    def _history_edit(self, function: Any, *args: Any) -> None:
        """Keyframe operations re-run the history; the run stops first."""
        self.simulation.stop()
        self.last_steps = []
        self._edit(function, *args)

    def _scrub(self, tick: int) -> None:
        self.simulation.stop()
        if self.document.seek_tick(tick):
            self.last_steps = []
            self._changed()

    def _set_container_slot(self, pos: Pos, slot: int | None, item: str | None, count: int) -> None:
        self._edit(self.document.set_container_slot, pos, slot, item, count)

    def _projectile_hit(self, pos: Pos, strength: int, arrow: bool) -> None:
        self._edit(self.document.projectile_hit, pos, strength, arrow)
        self._message("The projectile lands during the next tick (step a tick to see it).")

    def _plate_visitors(self, pos: Pos, mobs: int, others: int, ticks: int) -> None:
        self._edit(self.document.plate_visitors, pos, mobs, others, ticks)
        self._message(f"They step on the plate in the next tick and stay {ticks} ticks.")

    def _toggle_monitor(self, pos: Pos) -> None:
        on = self.document.toggle_monitor(pos)
        self._message(f"{'Monitoring' if on else 'Stopped monitoring'} {pos} on the timeline.")
        self._changed()

    # ------------------------------------------------------------------ editing
    def _search_blocks(self) -> None:
        """The quick block search popup over the viewport."""
        popup = BlockSearch(self, self.inventory.recent)
        popup.chosen.connect(self.inventory.select_block)
        popup.open_over(self.viewport)
        self._block_search = popup  # keep it alive while open

    def _choose_block(self, block: Any) -> None:
        """Choosing a block to place (palette, hotbar, pick) enters BUILD mode."""
        self.current_block = block
        self.viewport.set_build_block(block, self.inventory.strength.value())
        self.viewport.set_mode(BUILD)
        self._message(f"Placing: {block_name(block.id)}")

    def _hover(self, hit: Hit | None) -> None:
        if hit is None:
            self.hint_bar.show_hover("")
            return
        state = self.document.state_at(hit.pos)
        self.hint_bar.show_hover(f"{hit.pos}  {state!r}")

    def _edit(self, function: Any, *args: Any) -> None:
        self.document.notice = ""
        try:
            function(*args)
        except EditError as exc:
            self._message(str(exc), error=True)
        if self.document.notice:
            self._message(self.document.notice)
        self._changed()

    def _place(self, target: Pos) -> None:
        """A click in BUILD mode: place on the working layer, like a player clicking the top
        of the block below (orientation from the cursor ray)."""
        yaw, pitch = self.viewport.player_view()
        request = PlaceRequest(Direction.UP, yaw, pitch)
        kind = sources.SOURCE_BLOCKS.get(self.current_block.id)
        if kind is not None:
            strength = self.inventory.strength.value()
            vary = self.viewport.vary_state
            self._edit(self.document.place_source, target, kind, strength, request, vary)
        else:
            vary = self.viewport.vary_state
            self._edit(self.document.place, target, self.current_block, request, vary)
        self._remember_block(self.current_block)

    def _remember_block(self, block: Block) -> None:
        """Recently used blocks: shown first in the inventory and the block search."""
        self.inventory.remember(block.id)

    def _set_source(self, pos: Pos, kind: str, strength: int) -> None:
        self._edit(self.document.set_source, pos, kind, strength)

    def _turn_page(self, pos: Pos, page: int) -> None:
        self._edit(self.document.turn_page, pos, page)

    def _use(self, pos: Pos) -> None:
        block = self.document.state_at(pos).block
        if Document.is_usable(block):
            self._edit(self.document.use, pos)
        else:
            self._message(
                f"{block_name(block.id)} cannot be used (to place blocks, switch to BUILD mode)."
            )

    def _rotate_block(self, quarter_turns: int) -> None:
        """Rotate the block under the cursor (else the inspected one) with ``/setblock``."""
        hit = self.viewport.hover
        pos = hit.pos if hit is not None else self.viewport.selection
        if pos is None:
            self._message("Point at a block to rotate it.")
            return
        self._rotate_block_at(pos, quarter_turns)

    def _rotate_block_at(self, pos: Pos, quarter_turns: int) -> None:
        """Turn a block with ``/setblock``: around the vertical axis, or, for a block facing
        up or down (pistons, observers, hoppers), on to its next facing."""
        state = self.document.state_at(pos)
        rotated = rotate_state(state, quarter_turns)
        if rotated is state:
            for prop in state.block.properties:
                value = state.get(prop)
                if isinstance(value, Direction) and len(prop.values) > 4:
                    values = list(prop.values)
                    step = 1 if quarter_turns == 1 else -1
                    rotated = state.with_(prop, values[(values.index(value) + step) % len(values)])
                    break
        if rotated is state:
            self._message(
                f"{block_name(state.block.id)} has no facing to turn; the inspector can set "
                "any property."
            )
            return
        self._edit(self.document.setblock, pos, rotated)

    def _place_line(self, cells: list[Pos]) -> None:
        """A dragged line: every block placed as one edit batch (one undo step)."""
        if len(cells) <= 1:
            if cells:
                self._place(cells[0])
            return
        yaw, pitch = self.viewport.player_view()
        request = PlaceRequest(Direction.UP, yaw, pitch)
        block = self.current_block
        kind = sources.SOURCE_BLOCKS.get(block.id)
        self.document.notice = ""
        if kind is not None:
            strength = self.inventory.strength.value()
            with self.document.batch():
                for cell in cells:
                    try:
                        self.document.place_source(cell, kind, strength, request)
                    except EditError:
                        continue
        else:
            placed = self.document.place_many(cells, block, request, self.viewport.vary_state)
            if placed < len(cells):
                self._message(
                    f"Placed {placed} of {len(cells)} blocks (the rest had no room or support)."
                )
        self._remember_block(block)
        self._changed()

    def _break(self, pos: Pos) -> None:
        self._edit(self.document.break_block, pos)

    def _pick(self, pos: Pos) -> None:
        block = self.document.state_at(pos).block
        if isinstance(block, RedstoneWallTorchBlock):
            block = blocks.REDSTONE_TORCH
        self.inventory.select_block(block)

    def _select(self, pos: Pos | None) -> None:
        self.viewport.selection = pos
        self._changed()

    def _apply_state(self, pos: Pos, state: Any) -> None:
        self._edit(self.document.setblock, pos, state)

    def _assign_section(self, pos: Pos, name: str | None) -> None:
        self.document.assign_section(pos, name)
        self._changed()

    def _undo(self) -> None:
        self.simulation.stop()
        if not self.document.undo():
            self._message("Nothing to undo.")
        self._changed()

    def _fill_history_menu(self) -> None:
        """Edit → Undo History: the latest steps, newest first; choosing one undoes it and
        everything after it (like Blender's undo history)."""
        menu = self._history_menu
        menu.clear()
        labels = self.document.undo_labels
        if not labels:
            menu.addAction("Nothing to undo").setEnabled(False)
            return
        for count, label in enumerate(labels[:HISTORY_MENU_SIZE], start=1):
            action = menu.addAction(history_label(label))
            action.setToolTip(f"Undo {count} step{'s' if count > 1 else ''}")
            action.triggered.connect(lambda _=False, n=count: self._undo_to(n))
        if len(labels) > HISTORY_MENU_SIZE:
            menu.addAction(f"… {len(labels) - HISTORY_MENU_SIZE} older steps").setEnabled(False)

    def _add_marker(self) -> None:
        tick = self.document.tick
        name, ok = QInputDialog.getText(
            self, "Add marker", f"Name of the marker at tick {tick}:", text=f"tick {tick}"
        )
        if ok:
            self._name_marker(tick, name.strip() or f"tick {tick}")

    def _rename_marker(self, tick: int) -> None:
        current = self.document.markers.get(tick, "")
        name, ok = QInputDialog.getText(self, "Rename marker", f"Tick {tick}:", text=current)
        if ok:
            self._name_marker(tick, name.strip())

    def _name_marker(self, tick: int, name: str) -> None:
        """Set, rename (or with an empty name delete) the marker at ``tick``."""
        self.document.set_marker(tick, name)
        self._changed()

    def _undo_to(self, count: int) -> None:
        self.simulation.stop()
        if self.document.undo_to(count):
            self._message(f"Undid {count} step{'s' if count > 1 else ''}.")
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
        """Ctrl+V: preview the clipboard at the cursor; a left click places it."""
        if self.document.clipboard is None:
            self._message("The clipboard is empty.", error=True)
            return
        self.viewport.begin_paste(self.document.clipboard)
        self._message("Paste: left click places it · R rotates · right click or Esc cancels.")

    def _paste_at(self, origin: Pos) -> None:
        self._edit(self.document.paste, origin)

    def _move_region(self, region: Region, by: Pos, copy: bool) -> None:
        """A dragged selection: ``/clone … replace move`` (or ``force`` for a copy)."""
        self.document.notice = ""
        try:
            moved = self.document.clone_region(region, by, "force" if copy else "move")
        except EditError as exc:
            self._message(str(exc), error=True)
        else:
            self.viewport.region = moved
            verb = "Copied" if copy else "Moved"
            self._message(f"{verb} the selection by {by[0]}, {by[1]}, {by[2]}.")
        self._changed()

    def _rotate(self, quarter_turns: int) -> None:
        """R / Shift+R: the paste preview if one is shown, else the selection in place,
        else the clipboard."""
        viewport, document = self.viewport, self.document
        direction = "clockwise" if quarter_turns == 1 else "counter-clockwise"
        if viewport.mode == BUILD and viewport.paste_preview is None:  # the block to place
            variant = viewport.vary_build(turns=quarter_turns)
            self._message(
                f"Block to place: {variant} (R / Shift+R turn, H mirrors, Shift+H flips)."
            )
        elif viewport.paste_preview is not None and document.clipboard is not None:
            document.rotate_clipboard(quarter_turns)
            viewport.begin_paste(document.clipboard)
            self._message(f"Paste rotated 90° {direction}.")
        elif viewport.region is not None:
            self._transform(quarter_turns=quarter_turns)
        elif document.clipboard is not None:
            document.rotate_clipboard(quarter_turns)
            self._message(f"Clipboard rotated 90° {direction}.")
        else:
            self._message("Nothing to rotate: select a box (V) or copy something first.")

    def _flip(self, depth: bool) -> None:
        """H: mirror left/right as seen from the camera; Shift+H: front/back."""
        right = self.viewport.camera.right()
        sideways = "x" if abs(right[0]) >= abs(right[2]) else "z"
        axis = ("z" if sideways == "x" else "x") if depth else sideways
        viewport, document = self.viewport, self.document
        if viewport.mode == BUILD and viewport.paste_preview is None:  # the block to place
            variant = viewport.vary_build(mirror=None if depth else axis, flip=depth)
            self._message(f"Block to place: {variant} (Shift+H turns it upside down).")
        elif viewport.paste_preview is not None and document.clipboard is not None:
            document.mirror_clipboard(axis)
            viewport.begin_paste(document.clipboard)
            self._message("Paste flipped.")
        elif viewport.region is not None:
            self._transform(mirror=axis)
        else:
            self._message("Nothing to flip: select a box (V) first.")

    def _transform(self, quarter_turns: int = 0, mirror: str | None = None) -> None:
        region = self.viewport.region
        if region is None:
            return
        # Keep turning around the same pivot while the same selection is turned again, so
        # R then Shift+R (or R four times) returns exactly to the start.
        last = self._rotation_pivot
        pivot = last[1] if last is not None and last[0] == region else None
        if pivot is None:
            pivot = default_pivot2(region.low, region.high)
        try:
            moved = self.document.transform_region(region, quarter_turns, mirror, pivot)
            self.viewport.region = moved
            self._rotation_pivot = (moved, pivot)
        except EditError as exc:
            self._message(str(exc), error=True)
        else:
            what = f"rotated {quarter_turns * 90}°" if quarter_turns else "flipped"
            self._message(f"Selection {what} in place (no block updates).")
        self._changed()

    def _gizmo_transform(self, quarter_turns: int, mirror: str | None) -> None:
        if mirror is not None:
            self._transform(mirror=mirror)
        else:
            self._rotate(quarter_turns)

    def _toggle_lock(self) -> None:
        """Enter (like GIMP): lock the selection so clicks cannot replace it; rotate, flip,
        move and stack keep working on it."""
        viewport = self.viewport
        if viewport.region is None:
            self._message("Nothing to lock: select a box first (V).")
            return
        viewport.region_locked = not viewport.region_locked
        viewport.update()
        state = "locked (Enter or Esc unlocks)" if viewport.region_locked else "unlocked"
        self._message(f"Selection {state}.")

    def _stack_region(self, region: Region, step: Pos, count: int) -> None:
        try:
            self.viewport.region = self.document.stack_region(region, step, count)
        except EditError as exc:
            self._message(str(exc), error=True)
        else:
            self._message(f"Stacked {count} copies (no block updates).")
        self._changed()

    def _delete_region(self) -> None:
        """Del: clear the selection (in BUILD mode, right click removes single blocks)."""
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
            self._message(f"{block_name(state.block.id)} at {port.pos} cannot be used directly.")

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
            self._glide(self.pacer.rate)
        else:
            self.play_timer.stop()
            self.simulation.canvas.set_running(None)  # snap to the exact tick
            self._changed()

    def _glide(self, rate: float) -> None:
        """Let the timeline's playhead glide at ``rate`` ticks per second."""
        sign = -1.0 if self.simulation.backwards else 1.0
        self.simulation.canvas.set_running(sign * rate)

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
            if self.simulation.backwards:
                if not self.document.tick_back():
                    self.simulation.stop()  # back at tick 0
                    break
                self.last_steps = []
            else:
                self.last_steps = self.document.run_tick()
            ran += 1
            if time.monotonic() - start > RUN_BUDGET_SECONDS:
                break
        if not warp:
            self.pacer.ran(ran)
        if ran:  # nothing changed otherwise: no repaint
            now = time.monotonic()
            self.tick_rate.record(now, ran)
            measured = self.tick_rate.rate(now)
            self._glide(measured if measured > 0 else self.pacer.rate)
            self._changed(running=True)

    def _step_tick(self) -> None:
        self.last_steps = self.document.run_tick()
        self._changed()

    def _step_event(self) -> None:
        self.last_steps = [self.document.step()]
        self._changed()

    def _rewound(self, moved: bool) -> None:
        self.simulation.stop()
        self.last_steps = []
        if not moved:
            self._message("Already at the start of the recorded history.")
        self._changed()

    def _jump(self, where: str) -> None:
        self.simulation.stop()
        if not self.document.jump(where):
            self._message("Already there.")
        self.last_steps = []
        self._changed()

    def _tick_back(self) -> None:
        self._rewound(self.document.tick_back())

    def _step_back(self) -> None:
        self._rewound(self.document.step_back())

    def _seek(self, step_index: int) -> None:
        self.simulation.stop()
        self.document.seek(step_index)
        self.last_steps = []
        self._changed()

    # ------------------------------------------------------------------ files
    def _confirm_discard(self, closing: bool = False) -> bool:
        """Ask before unsaved changes would be lost; True means go ahead."""
        if not self.document.dirty:
            return True
        box = QMessageBox(self)
        box.setIconPixmap(pixel_icons.pixel_pixmap("warning", theme.GOLD, 4, tight=True))
        box.setWindowTitle("Unsaved changes")
        box.setText("You still have unsaved changes. Do you want to save the changes?")
        discard = box.addButton(
            "Close without saving" if closing else "Discard changes",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel = box.addButton(QMessageBox.StandardButton.Cancel)
        save = box.addButton(
            "Save" if self.document.path is not None else "Save as…",
            QMessageBox.ButtonRole.AcceptRole,
        )
        box.setDefaultButton(save)
        box.setEscapeButton(cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is discard:
            return True
        if clicked is save:
            self._save()
            return not self.document.dirty  # a cancelled "Save as" keeps the window open
        return False

    def _set_document(self, document: Document) -> None:
        self.simulation.stop()
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

    def _open_minecraft_world(self) -> None:
        """Import the area around the player of a Minecraft Java save (doc/world-import.md)."""
        if not self._confirm_discard():
            return
        start = next((str(p) for p in MINECRAFT_SAVE_FOLDERS if p.exists()), str(Path.home()))
        folder = QFileDialog.getExistingDirectory(
            self, "Open Minecraft world (a save folder)", start
        )
        if folder:
            self.open_minecraft_world(Path(folder))

    def open_minecraft_world(self, folder: Path, radius: int = 4) -> None:
        if not (folder / "level.dat").exists():
            QMessageBox.critical(self, "Not a Minecraft world", f"{folder} has no level.dat.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            opened = open_world(folder, radius)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(self, "Cannot open the world", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._set_document(opened.document)
        area = opened.area
        approx = [
            f"{block_name(i)} ×{n}" for i, n in opened.foreign.most_common() if not _plain_cube(i)
        ]
        note = f" Approximated (not simulated yet): {', '.join(approx)}." if approx else ""
        self._message(
            f"Opened {area.info.name}: {area.chunks} chunks around the player, "
            f"{len(opened.document.level.blocks)} blocks ({area.skipped_terrain} buried "
            f"terrain blocks left out).{note}"
        )

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

    def restore_layout(self) -> bool:
        """Restore the saved window size and dock layout; False if none was saved."""
        layout = load_window_layout()
        geometry, state = layout.get("geometry"), layout.get("state")
        if not geometry:
            return False
        restored = self.restoreGeometry(QByteArray.fromBase64(geometry.encode()))
        if state:
            self.restoreState(QByteArray.fromBase64(state.encode()))
        return restored

    def save_layout(self) -> None:
        save_window_layout(
            {
                "geometry": bytes(self.saveGeometry().toBase64().data()).decode(),
                "state": bytes(self.saveState().toBase64().data()).decode(),
            }
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """The ^ key of German layouts is a dead key, which Qt shortcuts cannot bind: it
        does what "^" is bound to (by default: back to the parent inventory folder)."""
        if (
            event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and event.key() == Qt.Key.Key_Dead_Circumflex
            and not isinstance(QApplication.focusWidget(), QLineEdit | QAbstractSpinBox)
            and "^" in self.keymap.bindings("inventory.up")
        ):
            self.inventory.go_up()
            return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard(closing=True):
            self.save_layout()
            self.viewport.release_gl()  # while the GL context still exists
            event.accept()
        else:
            event.ignore()
