"""3D viewport: orbit camera, modes, targeting and edit requests.

Controls follow the owner's decisions (doc/ui-direction.md) and are rebindable through the
keymap (``redsim.ui.keymap``). By default: middle-drag orbits around the highlighted pivot,
Shift+middle-drag pans it, Ctrl+wheel moves it up and down, the wheel zooms, WASD moves the
pivot. Clicks depend on the mode: NORMAL (left inspects, right uses), BUILD (left breaks,
right places) and SELECT (left click or drag selects boxes); middle click picks a block type
in every mode.

The viewport never edits the world itself; it emits signals that the main window turns into
document edits.
"""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QFontDatabase,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QWheelEvent,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.ui.camera import Camera
from redsim.ui.debug_screen import block_lines
from redsim.ui.geometry import (
    ChunkedMesh,
    Hit,
    block_outline,
    box_lines,
    ghost_mesh,
    pick,
    ray_box,
    thick_edges,
)
from redsim.ui.gizmos import BODY_ALPHA, Hotspot, box_faces, pick_hotspot, selection_gizmos
from redsim.ui.keymap import HOLD, Keymap
from redsim.ui.pacing import RateMeter
from redsim.ui.preferences import Preferences
from redsim.ui.renderer import Renderer
from redsim.ui.selection_tools import (
    Handle,
    face_center,
    horizontal_offset,
    paste_origin,
    plane_point,
    resized,
    shifted,
    steps_along,
)
from redsim.world import blocks
from redsim.world.block import Block, BlockState
from redsim.world.properties import POWER

BACKGROUND = (0.53, 0.70, 0.86, 1.0)
ORBIT_DEGREES_PER_PIXEL = 0.3
ZOOM_PER_NOTCH = 1.15
DRAG_THRESHOLD = 4
#: The build preview is this much smaller than a block (no z-fighting with neighbors).
GHOST_SHRINK = 0.99
#: Longest line placed by one drag.
MAX_LINE = 64
DOUBLE_SHIFT_SECONDS = 0.35
PIVOT_COLOR = (1.0, 0.35, 0.05, 1.0)
SELECTION_COLOR = (0.0, 0.85, 0.95, 1.0)
LOCKED_COLOR = (1.0, 0.62, 0.15, 1.0)
TARGET_COLOR = (1.0, 1.0, 1.0, 1.0)

NORMAL, BUILD, SELECT = "normal", "build", "select"
INFO_LABEL_LIMIT = 300
INFO_COLORS = {
    "wire": QColor(170, 20, 20, 210),
    "source": QColor(120, 60, 160, 220),
    "comparator": QColor(40, 40, 40, 220),
}
PASTE_COLOR = QColor(140, 60, 170)
MODE_COLORS = {
    NORMAL: QColor(60, 100, 160),
    BUILD: QColor(50, 140, 60),
    SELECT: QColor(200, 115, 25),
}
#: Short verbs for the mode badge.
CLICK_VERBS = {
    "normal.inspect": "inspect",
    "normal.use": "use",
    "build.place": "place",
    "build.line": "line",
    "build.rotate": "turn",
    "build.break": "break",
    "select.block": "select",
    "select.box": "box / move / resize",
    "select.copy_drag": "copy",
    "select.stack": "stack",
    "select.extend": "extend",
    "pick": "pick",
}

_BUTTON_NAMES = {
    Qt.MouseButton.LeftButton: "Left",
    Qt.MouseButton.RightButton: "Right",
    Qt.MouseButton.MiddleButton: "Middle",
}


def _modifier_names(modifiers: Qt.KeyboardModifier) -> frozenset[str]:
    names = set()
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        names.add("Ctrl")
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        names.add("Shift")
    if modifiers & Qt.KeyboardModifier.AltModifier:
        names.add("Alt")
    if modifiers & Qt.KeyboardModifier.MetaModifier:
        names.add("Meta")
    return frozenset(names)


class Viewport(QOpenGLWidget):
    hover_changed = Signal(object)  # Hit | None
    place_requested = Signal(object)  # Pos: a cell on the working layer
    line_requested = Signal(object)  # [Pos]: a straight line on the working layer
    rotate_requested = Signal(object, int)  # Pos, quarter turns
    use_requested = Signal(object)  # Pos
    break_requested = Signal(object)  # Pos
    pick_requested = Signal(object)  # Pos
    select_requested = Signal(object)  # Pos | None (inspector selection)
    region_changed = Signal(object)  # Region | None
    region_move_requested = Signal(object, object, bool)  # Region, offset, copy
    region_stack_requested = Signal(object, object, int)  # Region, step, count
    transform_requested = Signal(int, object)  # quarter turns, mirror axis | None
    gizmo_hover_changed = Signal(object)  # Hotspot | None
    paste_requested = Signal(object)  # Pos (minimum corner)
    mode_changed = Signal(str)
    search_requested = Signal()  # Shift pressed twice (like Rider's search everywhere)

    def __init__(
        self, document: Document, keymap: Keymap | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.document = document
        self.camera = Camera()
        self.renderer: Renderer | None = None
        self.mode = NORMAL
        self.hover: Hit | None = None
        self._hover_direction: np.ndarray | None = None
        self.selection: Pos | None = None
        self.region: Region | None = None
        self._region_anchor: Pos | None = None
        #: Annotation outlines (View menu): sections (colored cells) and groups (white boxes).
        self.show_sections = True
        self.show_groups = True
        #: Blender-like X-ray (building blocks see-through) and the block-info overlay.
        self.xray = 0  # 0 off, 1 building blocks see-through, 2 everything see-through
        self.show_info = False
        self.preferences = Preferences.load()
        #: F3 debug screen: the left column comes from the main window (it knows the rates).
        self.debug_left: list[str] = []
        #: SELECT mode: the face handle under the cursor, and drags in progress.
        self.gizmo_hover: Hotspot | None = None
        self.region_locked = False  # Enter: clicks can no longer replace the selection
        self._shift = False  # Shift held: resize arrows show their stacking look
        self._gizmo_cache: tuple[Any, tuple[np.ndarray, list[Hotspot]]] | None = None
        self._resize: tuple[Handle, Region, QPoint, np.ndarray] | None = None
        self._move: _MoveDrag | None = None
        self._stack: _StackDrag | None = None
        #: Ctrl+V preview: the prefab follows the cursor until a click places it.
        self.paste_preview: Prefab | None = None
        self._ghost: tuple[np.ndarray, Pos] | None = None  # vertices at offset 0, offset
        self._paste_base = np.zeros((0, 7), dtype=np.float32)
        #: BUILD mode preview: the block as it would be placed, translucent.
        self.build_block: Block | None = None
        self.build_strength = 15
        self._build_ghost: tuple[np.ndarray, Pos] | None = None
        self._build_meshes: dict[BlockState, np.ndarray] = {}
        self._line_ghost: tuple[Any, np.ndarray] | None = None
        self._last_shift = 0.0
        self.build_blocked: Pos | None = None  # target cell where placing is impossible
        #: BUILD mode line drag: the start cell.
        self._line: Pos | None = None
        self._line_end: Pos | None = None
        self._build_cell: Pos | None = None  # the layer cell the preview was made for
        self._ghost_uploaded: tuple[int, Pos] | None = None
        self.world_mesh = ChunkedMesh()
        self._mesh_revision = -1
        #: Lines of text drawn over the top-left corner (run status, achieved rates).
        self.overlay_text: list[str] = []
        self.frame_rate = RateMeter()
        self.keymap = Keymap()
        self._held_actions: dict[int, str] = {}
        self.set_keymap(keymap if keymap is not None else Keymap())
        self._held: set[str] = set()
        # Mouse gesture in progress: press point, button, modifiers; drag action once moving.
        self._press: tuple[QPoint, Qt.MouseButton, frozenset[str]] | None = None
        self._drag_action: str | None = None
        self._drag_last: QPoint | None = None
        self._last_mouse: QPoint | None = None
        self._last_frame = time.monotonic()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_camera)
        self._timer.start(16)

    # ------------------------------------------------------------------ setup
    def set_keymap(self, keymap: Keymap) -> None:
        self.keymap = keymap
        self._held_actions = {}
        for action in keymap.actions(HOLD):
            for binding in keymap.bindings(action):
                sequence = QKeySequence(binding)
                if sequence.count():
                    key = sequence[0].key()  # type: ignore[index]
                    self._held_actions[int(key.value)] = action
        self.update()

    def set_mode(self, mode: str) -> None:
        if mode != self.mode:
            self.mode = mode
            self.mode_changed.emit(mode)
            self._update_build_ghost()
        self.update()

    def set_document(self, document: Document) -> None:
        self.document = document
        self.selection = None
        self.region = None
        self._mesh_revision = -1  # the diff against the old world drops what is gone
        self.update()

    def refresh(self) -> None:
        """Call after the world changed (edits or simulation steps)."""
        self._update_build_ghost()
        self.update()

    def set_build_block(self, block: Block, strength: int) -> None:
        self.build_block = block
        self.build_strength = strength
        self._update_build_ghost()

    def _update_build_ghost(self) -> None:
        """Preview of the block(s) to place: oriented like the placement would orient them
        (cursor-ray yaw/pitch, wire connections, source setup), or a red outline. While a
        line is dragged, the whole line."""
        ghost, blocked = None, None
        block = self.build_block
        busy = self.paste_preview is not None or self._move is not None
        if self._line is not None and block is not None:
            start = self._line
            cells = self.line_cells()
            request = PlaceRequest(Direction.UP, *self.player_view())
            states = [(cell, self._placed_state(block, request, cell)) for cell in cells]
            parts = tuple(
                ((c[0] - start[0], c[1] - start[1], c[2] - start[2]), st)
                for c, st in states
                if st is not None
            )
            if parts:
                ghost = (self._combined_ghost(parts), start)
        elif self.mode == BUILD and block is not None and not busy:
            target = self.build_target()
            self._build_cell = target
            request = PlaceRequest(Direction.UP, *self.player_view())
            state = None if target is None else self._placed_state(block, request, target)
            if target is not None and state is None:
                blocked = target
            elif target is not None and state is not None:
                ghost = (self._single_ghost(state), target)
        if _ghost_key(ghost) != _ghost_key(self._build_ghost) or blocked != self.build_blocked:
            self._build_ghost, self.build_blocked = ghost, blocked
            self.update()

    def _placed_state(self, block: Block, request: PlaceRequest, target: Pos) -> BlockState | None:
        level = self.document.level
        if not level.get_block_state(target).is_air:
            return None
        state = placement_state(block, request, level, target)
        kind = sources.SOURCE_BLOCKS.get(block.id)
        if state is not None and kind is not None:
            text, _ = sources.source_setblock(kind, self.build_strength, state)
            state = blocks.parse_state(text)
        if state is None or not state.can_survive(level, target):
            return None
        return state

    def _single_ghost(self, state: BlockState) -> np.ndarray:
        vertices = self._build_meshes.get(state)
        if vertices is None:
            vertices = ghost_mesh({(0, 0, 0): state}, 0.5, self.world_mesh.mesher)
            # Shrink it a little around the block center, so none of its faces lies in the
            # plane of a neighbor's face (z-fighting flicker, e.g. wire on a block).
            vertices[:, :3] = 0.5 + (vertices[:, :3] - 0.5) * GHOST_SHRINK
            self._build_meshes[state] = vertices
        return vertices

    def _combined_ghost(self, parts: tuple[tuple[Pos, BlockState], ...]) -> np.ndarray:
        cached = self._line_ghost
        if cached is not None and cached[0] == parts:
            return cached[1]
        pieces = []
        for rel, state in parts:
            vertices = self._single_ghost(state).copy()
            vertices[:, :3] += np.array(rel, dtype=np.float32)
            pieces.append(vertices)
        combined = np.vstack(pieces)
        self._line_ghost = (parts, combined)
        return combined

    # ------------------------------------------------------------------ line drag
    def line_cells(self) -> list[Pos]:
        """The cells of the dragged line: from the start along the axis the cursor moved
        most on (x or z, on the start's layer), at most ``MAX_LINE`` long."""
        if self._line is None:
            return []
        start = self._line
        end = self._line_end or start
        dx, dz = end[0] - start[0], end[2] - start[2]
        if abs(dx) >= abs(dz):
            length, step = abs(dx), (1 if dx >= 0 else -1, 0, 0)
        else:
            length, step = abs(dz), (0, 0, 1 if dz >= 0 else -1)
        length = min(length, MAX_LINE - 1)
        return [
            (start[0] + step[0] * i, start[1], start[2] + step[2] * i) for i in range(length + 1)
        ]

    def build_target(self, point: QPoint | None = None) -> Pos | None:
        """BUILD mode places on the working layer (the camera pivot's height; the wheel
        moves it), in the cell under the cursor, like Trackmania's editor."""
        point = point if point is not None else self._last_mouse
        if point is None:
            return None
        origin, direction = self._ray(point)
        self._hover_direction = direction
        return paste_origin(origin, direction, self.working_height(), (1, 1, 1))

    def _begin_line(self, point: QPoint) -> bool:
        start = self.build_target(point)
        if start is None or self.build_block is None:
            return False
        self._line = start
        self._line_end = None
        return True

    def _continue_line(self, point: QPoint) -> None:
        if self._line is None:
            return
        end = self.build_target(point)
        if end is not None and end != self._line_end:
            self._line_end = end
            self._update_build_ghost()

    def _end_line(self) -> None:
        if self._line is None:
            return
        cells = self.line_cells()
        self._line, self._line_end = None, None
        self.line_requested.emit(cells)
        self._update_build_ghost()

    # ------------------------------------------------------------------ GL
    def initializeGL(self) -> None:
        # Called again whenever Qt recreates the context (e.g. on re-parenting), so all GPU
        # data must be uploaded again.
        self.renderer = Renderer()
        self.world_mesh.reset()
        self._mesh_revision = -1

    def resizeGL(self, width: int, height: int) -> None:
        # The same mouse position now casts a different ray: retarget the previews.
        self._update_build_ghost()
        self._update_paste_ghost()

    def paintGL(self) -> None:
        renderer = self.renderer
        if renderer is None:
            return
        if self._mesh_revision != self.document.revision:
            # Only chunks whose blocks (or neighbors) changed are rebuilt and re-uploaded.
            chunks = self.world_mesh.chunks
            for key in self.world_mesh.update(self.document.level):
                mesh = chunks.get(key)
                if mesh is None:
                    renderer.remove_chunk(key)
                else:
                    renderer.set_chunk(key, mesh.opaque, mesh.translucent, mesh.solid)
            for stale in [stale for stale in renderer.chunks if stale not in chunks]:
                renderer.remove_chunk(stale)
            self._mesh_revision = self.document.revision
        renderer.upload_lines(self._overlay_lines())
        renderer.upload_overlay(self._overlay_triangles())
        renderer.upload_volume(self._selection_body())
        renderer.upload_top_lines(self._pivot_lines())
        self._upload_ghost(renderer)
        ratio = self.devicePixelRatioF()
        width, height = int(self.width() * ratio), int(self.height() * ratio)
        aspect = max(width, 1) / max(height, 1)
        mvp = self.camera.projection_matrix(aspect) @ self.camera.view_matrix()
        prefs = self.preferences
        renderer.draw(
            mvp,
            width,
            height,
            BACKGROUND,
            xray=self.xray,
            building_alpha=prefs.xray_building_alpha,
            circuit_alpha=prefs.xray_circuit_alpha,
            eye=tuple(float(v) for v in self.camera.position),  # type: ignore[arg-type]
            fog=(60.0 + self.camera.distance, 200.0 + 2 * self.camera.distance),
        )
        self.frame_rate.record(time.monotonic())
        self._draw_overlays()

    def _draw_overlays(self) -> None:
        painter = QPainter(self)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        painter.setFont(font)
        if self.show_info:
            self._draw_info_labels(painter)
            self._draw_debug_columns(painter)
        metrics = painter.fontMetrics()
        line_height = metrics.height()
        if self.overlay_text and not self.show_info:
            width = max(metrics.horizontalAdvance(line) for line in self.overlay_text) + 12
            height = line_height * len(self.overlay_text) + 8
            painter.fillRect(6, 6, width, height, QColor(0, 0, 0, 120))
            painter.setPen(QColor(255, 255, 255))
            for index, line in enumerate(self.overlay_text):
                painter.drawText(12, 10 + metrics.ascent() + index * line_height, line)
        # Mode badge (bottom left) with what the mouse buttons do in this mode.
        pasting = self.paste_preview is not None
        badge = " PASTE " if pasting else f" {self.mode.upper()} "
        top = self.height() - line_height - 14
        badge_width = metrics.horizontalAdvance(badge) + 8
        room = max(0, self.width() - badge_width - 30)  # the full list is in the help (F1)
        text = self.paste_hint() if pasting else self.mode_hint()
        hint = metrics.elidedText(text, Qt.TextElideMode.ElideRight, room)
        color = PASTE_COLOR if pasting else MODE_COLORS[self.mode]
        painter.fillRect(6, top, badge_width, line_height + 8, color)
        painter.fillRect(
            6 + badge_width,
            top,
            metrics.horizontalAdvance(hint) + 16,
            line_height + 8,
            QColor(0, 0, 0, 120),
        )
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, top + 4 + metrics.ascent(), badge)
        xray_tag = ("", "X-RAY", "X-RAY ALL")[self.xray]
        flags = [name for name, on in ((xray_tag, self.xray), ("INFO", self.show_info)) if on]
        if flags:
            tag = " " + " · ".join(flags) + " "
            tag_width = metrics.horizontalAdvance(tag) + 8
            tag_top = top - line_height - 12
            painter.fillRect(6, tag_top, tag_width, line_height + 8, QColor(30, 30, 30, 200))
            painter.drawText(10, tag_top + 4 + metrics.ascent(), tag)
        painter.drawText(14 + badge_width, top + 4 + metrics.ascent(), hint)
        painter.end()

    def info_labels(self, max_distance: float = 48.0) -> list[tuple[np.ndarray, str, str]]:
        """Signal values shown by the info overlay: (world point, text, kind), nearest last.

        Wire: its power; signal sources (barrel, lectern, cake): the value a comparator
        reads; comparators: their stored output signal."""
        level = self.document.level
        eye = self.camera.position
        labels: list[tuple[float, np.ndarray, str, str]] = []
        for pos, state in level.blocks.items():
            block_id = state.block.id
            if block_id == "minecraft:redstone_wire":
                text, kind, height = str(state.get(POWER)), "wire", 0.1
            elif block_id == "minecraft:comparator":
                entity = level.get_block_entity(pos, create=False)
                output = entity.to_json().get("OutputSignal", 0) if entity is not None else 0
                text, kind, height = str(output), "comparator", 0.3
            elif sources.kind_of(state) is not None:
                value = sources.strength_at(level, pos)
                text, kind = str(value), "source"
                height = 0.55 if block_id == "minecraft:cake" else 1.0
            elif block_id == "minecraft:hopper":
                value = state.block.get_analog_output_signal(state, level, pos, Direction.NORTH)
                text, kind, height = str(value), "source", 1.0
            else:
                continue
            point = np.array([pos[0] + 0.5, pos[1] + height, pos[2] + 0.5])
            distance = float(np.linalg.norm(point - eye))
            if distance <= max_distance:
                labels.append((distance, point, text, kind))
        labels.sort(key=lambda label: -label[0])
        return [(point, text, kind) for _, point, text, kind in labels[-INFO_LABEL_LIMIT:]]

    def _draw_debug_columns(self, painter: QPainter) -> None:
        """Minecraft-like F3 text: world state on the left, the targeted block on the right."""
        metrics = painter.fontMetrics()
        line_height = metrics.height() + 2
        right = block_lines(self.document, self.hover.pos) if self.hover is not None else []
        for lines, align_right in ((self.debug_left, False), (right, True)):
            for index, line in enumerate(lines):
                width = metrics.horizontalAdvance(line) + 8
                left = self.width() - width - 6 if align_right else 6
                top = 6 + index * line_height
                painter.fillRect(left, top, width, line_height, QColor(0, 0, 0, 130))
                painter.setPen(QColor(235, 235, 235))
                painter.drawText(left + 4, top + 1 + metrics.ascent(), line)

    def _draw_info_labels(self, painter: QPainter) -> None:
        metrics = painter.fontMetrics()
        width, height = max(self.width(), 1), max(self.height(), 1)
        mvp = self.camera.projection_matrix(width / height) @ self.camera.view_matrix()
        for point, text, kind in self.info_labels():
            clip = mvp @ np.array([*point, 1.0])
            if clip[3] <= 0.05:
                continue  # behind the camera
            x = (clip[0] / clip[3] + 1) / 2 * width
            y = (1 - clip[1] / clip[3]) / 2 * height
            if not (0 <= x <= width and 0 <= y <= height):
                continue
            box_width = metrics.horizontalAdvance(text) + 8
            box_height = metrics.height() + 2
            left, top = int(x - box_width / 2), int(y - box_height / 2)
            background = INFO_COLORS[kind]
            if text == "0":
                background = QColor(70, 70, 70, 170)
            painter.fillRect(left, top, box_width, box_height, background)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(left + 4, top + 1 + metrics.ascent(), text)

    def paste_hint(self) -> str:
        return (
            f"layer y={self.working_height()} (Wheel moves it) · Left Click: place · "
            "R: rotate · H: flip · Right Click / Esc: cancel"
        )

    def mode_hint(self) -> str:
        """``Left Click: place · Left Drag: line · …`` for the current mode."""
        parts = []
        for action, verb in CLICK_VERBS.items():
            prefix = action.split(".")[0]
            bindings = self.keymap.bindings(action)
            if bindings and prefix in (self.mode, "pick"):
                parts.append(f"{bindings[0]}: {verb}")
        if self.mode == BUILD:
            delete = self.keymap.bindings("edit.delete")
            if delete:
                parts.insert(3, f"{delete[0]}: remove")
            parts.insert(0, f"layer y={self.working_height()} (Wheel moves it)")
        return " · ".join(parts)

    def _overlay_lines(self) -> np.ndarray:
        level = self.document.level
        parts = []
        sections = self.document.sections.sections.values() if self.show_sections else ()
        groups = self.document.groups.groups.values() if self.show_groups else ()
        for section in sections:
            color = _hex_color(section.color)
            for pos in section.positions:
                parts.append(box_lines(pos, (pos[0] + 1, pos[1] + 1, pos[2] + 1), color, 0.01))
        for group in groups:
            low, high = group.region.low, group.region.high
            parts.append(
                box_lines(low, (high[0] + 1, high[1] + 1, high[2] + 1), (1, 1, 1, 1), 0.03)
            )
            for port in group.ports:
                color = (0.2, 0.5, 1.0, 1.0) if port.role == "input" else (1.0, 0.5, 0.1, 1.0)
                p = port.pos
                parts.append(box_lines(p, (p[0] + 1, p[1] + 1, p[2] + 1), color, 0.05))
        paste_box = self.paste_region()
        if paste_box is not None:
            parts.extend(self._paste_guides(paste_box))
        if self.selection is not None:
            parts.append(block_outline(level, self.selection, (1.0, 0.85, 0.1, 1.0)))
        if self.hover is not None:
            parts.append(block_outline(level, self.hover.pos, (0.05, 0.05, 0.05, 1.0)))
        if self.mode == BUILD and self.paste_preview is None:
            cell = self._line_end or self._build_cell  # where a block would go
            if cell is not None:
                parts.extend(self._paste_guides(Region(cell, cell)))  # layer grid
                color = (1.0, 0.2, 0.2, 1.0) if cell == self.build_blocked else (1, 1, 1, 1)
                parts.append(box_lines(cell, (cell[0] + 1, cell[1] + 1, cell[2] + 1), color))
        if not parts:
            return np.zeros((0, 7), dtype=np.float32)
        return np.vstack(parts)

    def _paste_guides(self, box: Region) -> list[np.ndarray]:
        """A grid on the working plane around the paste, and drop lines from its corners to
        the first block below, so its height reads at a glance (Trackmania-style)."""
        y = float(box.low[1])
        grid = (1.0, 1.0, 1.0, 0.35)
        x0, x1 = box.low[0] - 4, box.high[0] + 5
        z0, z1 = box.low[2] - 4, box.high[2] + 5
        rows = []
        for x in range(x0, x1 + 1):
            rows += [(x, y, z0, *grid), (x, y, z1, *grid)]
        for z in range(z0, z1 + 1):
            rows += [(x0, y, z, *grid), (x1, y, z, *grid)]
        parts = [np.array(rows, dtype=np.float32)]
        drop = (1.0, 0.9, 0.3, 1.0)
        level = self.document.level
        for cx in (box.low[0], box.high[0] + 1):
            for cz in (box.low[2], box.high[2] + 1):
                bx, bz = min(cx, box.high[0]), min(cz, box.high[2])  # the corner block column
                ground = box.low[1]
                while ground > max(level.min_y, box.low[1] - 64):
                    if (bx, ground - 1, bz) in level.blocks:
                        break
                    ground -= 1
                if ground < box.low[1]:
                    line = [(cx, y, cz, *drop), (cx, ground, cz, *drop)]
                    parts.append(np.array(line, dtype=np.float32))
        return parts

    def _overlay_triangles(self) -> np.ndarray:
        """Selection box, its handles and drop targets: thick, and visible through blocks."""
        parts = []
        width = self._edge_width()
        if self.region is not None:
            lo, hi = _bounds(self.region)
            color = LOCKED_COLOR if self.region_locked else SELECTION_COLOR
            parts.append(thick_edges(lo, hi, color, width))
            if self._gizmos_shown():
                parts.append(self._gizmos()[0])
        if self._move is not None:
            lo, hi = _bounds(shifted(self._move.region, self._move.offset_pos))
            parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        if self._stack is not None and self._stack.count:
            far = shifted(self._stack.region, self._stack.offset(self._stack.count))
            lo = np.minimum(_bounds(self._stack.region)[0], _bounds(far)[0])
            hi = np.maximum(_bounds(self._stack.region)[1], _bounds(far)[1])
            parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        paste_box = self.paste_region()
        if paste_box is not None:
            lo, hi = _bounds(paste_box)
            parts.append(thick_edges(lo, hi, TARGET_COLOR, width))
        if not parts:
            return np.zeros((0, 7), dtype=np.float32)
        return np.vstack(parts)

    def _edge_width(self) -> float:
        """Selection edges keep a similar on-screen thickness at any zoom."""
        return min(0.2, max(0.035, 0.006 * self.camera.distance))

    def gizmo_unit(self) -> float:
        """Gizmo scale: grows with the distance to the selection, so it stays usable."""
        if self.region is None:
            return 0.1
        lo, hi = _bounds(self.region)
        distance = float(np.linalg.norm((lo + hi) / 2 - self.camera.position))
        return min(0.6, max(0.07, 0.017 * distance))

    def _gizmos_shown(self) -> bool:
        busy = self._move is not None or self._stack is not None or self._resize is not None
        return (
            self.region is not None
            and self.mode == SELECT
            and not busy
            and self.paste_preview is None
        )

    def _gizmos(self) -> tuple[np.ndarray, list[Hotspot]]:
        """Gizmo triangles and hot spots for the current selection (cached)."""
        assert self.region is not None
        unit = self.gizmo_unit()
        key = (self.region, round(unit, 3), round(self.camera.yaw), self._shift, self.gizmo_hover)
        if self._gizmo_cache is None or self._gizmo_cache[0] != key:
            built = selection_gizmos(
                self.region, unit, self.camera.yaw, self._shift, self.gizmo_hover
            )
            self._gizmo_cache = (key, built)
        return self._gizmo_cache[1]

    def _gizmo_at(self, point: QPoint) -> Hotspot | None:
        if not self._gizmos_shown():
            return None
        origin, direction = self._ray(point)
        return pick_hotspot(origin, direction, self._gizmos()[1])

    def _selection_body(self) -> np.ndarray:
        """A very faint body, so it is clear which blocks are inside the selection."""
        if self.region is None:
            return np.zeros((0, 7), dtype=np.float32)
        lo, hi = _bounds(self.region)
        color = LOCKED_COLOR if self.region_locked else SELECTION_COLOR
        return box_faces(lo, hi, (color[0], color[1], color[2], BODY_ALPHA))

    def _upload_ghost(self, renderer: Renderer) -> None:
        ghost = self._ghost or self._build_ghost
        key = _ghost_key(ghost)
        if key == self._ghost_uploaded:
            return
        self._ghost_uploaded = key
        if ghost is None:
            renderer.upload_ghost(np.zeros((0, 7), dtype=np.float32))
            return
        vertices = ghost[0].copy()
        vertices[:, :3] += np.array(ghost[1], dtype=np.float32)
        renderer.upload_ghost(vertices)

    def _pivot_lines(self) -> np.ndarray:
        """A small cross and ring at the pivot, drawn on top of everything."""
        x, y, z = (float(v) for v in self.camera.pivot)
        size = 0.12 + self.camera.distance * 0.015
        rows = [
            (x - size, y, z), (x + size, y, z),
            (x, y - size, z), (x, y + size, z),
            (x, y, z - size), (x, y, z + size),
        ]  # fmt: skip
        ring = [
            (x + math.cos(a) * size * 1.6, y, z + math.sin(a) * size * 1.6)
            for a in (i * math.pi / 8 for i in range(17))
        ]
        for a, b in zip(ring, ring[1:], strict=False):
            rows.extend((a, b))
        return np.array([(*row, *PIVOT_COLOR) for row in rows], dtype=np.float32)

    # ------------------------------------------------------------------ keyboard
    def _track_shift(self, held: bool) -> None:
        if held != self._shift:
            self._shift = held
            self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Shift and not event.isAutoRepeat():
            now = time.monotonic()
            if now - self._last_shift < DOUBLE_SHIFT_SECONDS:
                self._last_shift = 0.0
                self.search_requested.emit()
            else:
                self._last_shift = now
        elif event.key() != Qt.Key.Key_Shift:
            self._last_shift = 0.0
        if event.key() == Qt.Key.Key_Shift:
            self._track_shift(True)
        action = self._held_actions.get(event.key())
        if action is not None and not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            self._held.add(action)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Shift:
            self._track_shift(False)
        action = self._held_actions.get(event.key())
        if action is not None and not event.isAutoRepeat():
            self._held.discard(action)
            return
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._held.clear()

    def _tick_camera(self) -> None:
        now = time.monotonic()
        dt = min(now - self._last_frame, 0.1)
        self._last_frame = now
        held = self._held
        if not held:
            return
        speed = max(4.0, self.camera.distance * 0.8) * dt
        forward = ("camera.forward" in held) - ("camera.back" in held)
        strafe = ("camera.right" in held) - ("camera.left" in held)
        up = ("camera.up" in held) - ("camera.down" in held)
        if forward or strafe:
            self.camera.pan(forward * speed, strafe * speed)
        if up:
            self.camera.raise_pivot(up * speed)
        if forward or strafe or up:
            self._camera_moved()

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if self._press is not None:
            return  # one gesture at a time
        point = event.position().toPoint()
        self._press = (point, event.button(), _modifier_names(event.modifiers()))
        self._drag_action = None
        self._drag_last = point

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        point = event.position().toPoint()
        self._last_mouse = point
        self._track_shift(bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
        self._update_hover(point)
        if self.paste_preview is not None:
            self._update_paste_ghost()
        if self._press is None:
            return
        start, button, modifiers = self._press
        if self._drag_action is None:
            if (point - start).manhattanLength() <= DRAG_THRESHOLD:
                return
            name = _BUTTON_NAMES.get(button)
            action = self.keymap.mouse_action(self.mode, modifiers, name, "Drag")
            self._drag_action = action or ""
            if self._drag_action == "build.line" and not self._begin_line(start):
                self._drag_action = ""
            if self._drag_action in ("select.box", "select.copy_drag"):
                self._begin_select_drag(start, copy=self._drag_action == "select.copy_drag")
            elif self._drag_action == "select.stack":
                self._begin_stack(start)
        last = self._drag_last or point
        self._drag(self._drag_action, point.x() - last.x(), point.y() - last.y())
        self._drag_last = point

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._press is None or event.button() != self._press[1]:
            return
        _, button, modifiers = self._press
        drag_action = self._drag_action
        self._press = None
        self._drag_action = None
        if drag_action is None:
            self._update_hover(event.position().toPoint())
            spot = self.gizmo_hover
            if self.paste_preview is not None:
                self._paste_click(button)
            elif button == Qt.MouseButton.LeftButton and spot is not None:
                if spot.kind == "rotate":
                    self.transform_requested.emit(1 if spot.data == 1 else 3, None)
                elif spot.kind == "flip":
                    self.transform_requested.emit(0, spot.data)
            else:
                name = _BUTTON_NAMES.get(button)
                action = self.keymap.mouse_action(self.mode, modifiers, name, "Click")
                if action is not None:
                    self._click(action)
        elif drag_action in ("select.box", "select.copy_drag"):
            self._end_select_drag()
        elif drag_action == "select.stack":
            self._end_stack()
        elif drag_action == "build.line":
            self._end_line()
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta()
        steps = (delta.y() or delta.x()) / 120.0  # some systems turn Shift+wheel sideways
        if not steps:
            return
        if self._move is not None:  # while dragging a selection, the wheel lifts it
            self._move.lift += 1 if steps > 0 else -1
            self._ghost = (self._move.ghost, self._move.offset_pos)
            self.update()
            return
        modifiers = _modifier_names(event.modifiers())
        mode = "paste" if self.paste_preview is not None else self.mode
        action = self.keymap.mouse_action(mode, modifiers, None, "Wheel")
        if action in ("camera.zoom", "paste.zoom", "build.zoom"):
            self.camera.zoom(ZOOM_PER_NOTCH**-steps)
        elif action in ("camera.vertical", "paste.layer", "build.layer"):
            self.camera.raise_pivot(steps)  # one block per notch; the paste layer follows
        else:
            return
        self._camera_moved()

    def _drag(self, action: str, dx: int, dy: int) -> None:
        camera = self.camera
        if action == "camera.orbit":
            camera.orbit(dx * ORBIT_DEGREES_PER_PIXEL, dy * ORBIT_DEGREES_PER_PIXEL)
        elif action == "camera.pan":
            # The world follows the mouse: blocks per pixel at the pivot's distance.
            scale = 2 * camera.distance * math.tan(math.radians(camera.fov) / 2)
            scale /= max(self.height(), 1)
            camera.pan(dy * scale, -dx * scale)
        elif action in ("select.box", "select.copy_drag"):
            self._continue_select_drag()
            return
        elif action == "select.stack":
            self._continue_stack()
            return
        elif action == "build.line":
            if self._drag_last is not None:
                self._continue_line(self._drag_last + QPoint(dx, dy))
            return
        else:
            return
        self._camera_moved()

    def _click(self, action: str) -> None:
        hit = self.hover
        if action == "normal.inspect":
            self.selection = hit.pos if hit else None
            self.select_requested.emit(self.selection)
        elif action in ("select.block", "select.extend") and self.region_locked:
            return  # a locked selection keeps its box
        elif action == "select.block":
            self._region_anchor = hit.pos if hit else None
            self.region = Region.from_corners(hit.pos, hit.pos) if hit else None
            self.region_changed.emit(self.region)
        elif action == "select.extend" and hit is not None:
            anchor = self._region_anchor or hit.pos
            self._region_anchor = anchor
            self.region = Region.from_corners(anchor, hit.pos)
            self.region_changed.emit(self.region)
        elif action == "build.place":
            target = self.build_target()
            if target is not None:
                self.place_requested.emit(target)
        elif hit is None:
            return
        elif action == "pick":
            self.pick_requested.emit(hit.pos)
        elif action in ("normal.use", "build.use"):
            self.use_requested.emit(hit.pos)
        elif action == "build.break":
            self.break_requested.emit(hit.pos)

        elif action in ("build.rotate", "build.rotate_back"):
            self.rotate_requested.emit(hit.pos, 1 if action == "build.rotate" else 3)

    # ------------------------------------------------------------------ selections
    def _begin_select_drag(self, start: QPoint, copy: bool) -> None:
        """A left drag in SELECT mode: resize from a handle, move/copy from inside the box,
        otherwise draw a new box."""
        origin, direction = self._ray(start)
        block = pick(self.document.level, origin, direction)
        region = self.region
        spot = self._gizmo_at(start)
        if region is not None and not copy and spot is not None:
            if spot.kind == "resize":  # gizmos are drawn on top, so they win over blocks
                handle = spot.data
                center = face_center(region, handle)
                axis = self._screen_vector(center, center + handle.normal)
                self._resize = (handle, region, start, axis)
            return  # rotate/flip gizmos act on click, not drag
        grab = self._grab_point(region, origin, direction, block)
        if region is not None and grab is not None:
            ghost = self._region_ghost(region)
            self._move = _MoveDrag(region, copy, float(grab[1]), grab, ghost)
            self._ghost = (ghost, (0, 0, 0))
            return
        if copy or self.region_locked:
            return  # copy-drags start inside the selection; a locked one cannot be replaced
        self._region_anchor = block.pos if block else None
        self._extend_box()

    @staticmethod
    def _grab_point(
        region: Region | None, origin: np.ndarray, direction: np.ndarray, block: Hit | None
    ) -> np.ndarray | None:
        """Where a drag grabs the selection: a block inside it, else anywhere the ray meets
        the box itself (selections usually contain air)."""
        if region is None:
            return None
        if block is not None and region.contains(block.pos):
            return origin + direction * block.distance
        lo, hi = _bounds(region)
        hit = ray_box(origin, direction, lo, hi)
        return None if hit is None else origin + direction * hit[0]

    def _continue_select_drag(self) -> None:
        point = self._last_mouse
        if point is None:
            return
        if self._resize is not None:
            handle, region, start, axis = self._resize
            drag = (point.x() - start.x(), point.y() - start.y())
            self.region = resized(region, handle, steps_along(drag, axis))
            self.update()
        elif self._move is not None:
            origin, direction = self._ray(point)
            hit = plane_point(origin, direction, self._move.plane_y)
            if hit is not None:
                self._move.dx, self._move.dz = horizontal_offset(self._move.grab, hit)
                self._ghost = (self._move.ghost, self._move.offset_pos)
                self.update()
        else:
            self._extend_box()

    def _end_select_drag(self) -> None:
        move, self._move = self._move, None
        resize, self._resize = self._resize, None
        self._ghost = None
        if move is not None:
            if move.offset_pos != (0, 0, 0):
                self.region_move_requested.emit(move.region, move.offset_pos, move.copy)
        elif resize is not None or self._region_anchor is not None:
            self.region_changed.emit(self.region)

    def _begin_stack(self, start: QPoint) -> None:
        """Shift+drag on a face handle: repeat the selection along that face's normal."""
        region = self.region
        if region is None:
            return
        spot = self._gizmo_at(start)
        if spot is None or spot.kind != "resize":
            return
        handle = spot.data
        center = face_center(region, handle)
        axis = self._screen_vector(center, center + handle.normal)
        self._stack = _StackDrag(region, handle, start, axis, self._region_ghost(region))

    def _continue_stack(self) -> None:
        stack, point = self._stack, self._last_mouse
        if stack is None or point is None:
            return
        drag = (point.x() - stack.start.x(), point.y() - stack.start.y())
        count = max(0, round(steps_along(drag, stack.axis) / stack.length))
        if count != stack.count:
            stack.count = count
            copies = [stack.ghost.copy() for _ in range(count)]
            for i, vertices in enumerate(copies, start=1):
                vertices[:, :3] += np.array(stack.offset(i), dtype=np.float32)
            self._ghost = (np.vstack(copies), (0, 0, 0)) if copies else None
            self.update()

    def _end_stack(self) -> None:
        stack, self._stack = self._stack, None
        self._ghost = None
        if stack is not None and stack.count:
            self.region_stack_requested.emit(stack.region, stack.offset(1), stack.count)

    def _extend_box(self) -> None:
        if self._region_anchor is not None and self.hover is not None:
            self.region = Region.from_corners(self._region_anchor, self.hover.pos)
            self.update()

    def _region_ghost(self, region: Region) -> np.ndarray:
        level = self.document.level
        states = {pos: level.blocks[pos] for pos in region.positions() if pos in level.blocks}
        return ghost_mesh(states, mesher=self.world_mesh.mesher)

    # ------------------------------------------------------------------ paste preview
    def begin_paste(self, prefab: Prefab) -> None:
        """Show ``prefab`` as a ghost at the cursor; a left click places it."""
        states = {(dx, dy, dz): blocks.parse_state(text) for dx, dy, dz, text, _ in prefab.blocks}
        self.paste_preview = prefab
        self._paste_base = ghost_mesh(states, mesher=self.world_mesh.mesher)
        self._update_paste_ghost()

    def cancel_paste(self) -> None:
        self.paste_preview = None
        self._ghost = None
        self.update()

    def paste_target(self) -> Pos | None:
        """Minimum corner of the paste, Trackmania-editor style: on the horizontal plane at
        the camera's working height (the pivot's block layer; Ctrl+wheel moves it),
        centered under the cursor. Works in the air and inside blocks."""
        if self.paste_preview is None or self._last_mouse is None:
            return None
        origin, direction = self._ray(self._last_mouse)
        return paste_origin(origin, direction, self.working_height(), self.paste_preview.size)

    def working_height(self) -> int:
        """The block layer the camera pivot is in."""
        return math.floor(float(self.camera.pivot[1]))

    def paste_region(self) -> Region | None:
        target = self.paste_target()
        if self.paste_preview is None or target is None:
            return None
        sx, sy, sz = self.paste_preview.size
        return Region(target, (target[0] + sx - 1, target[1] + sy - 1, target[2] + sz - 1))

    def _update_paste_ghost(self) -> None:
        target = self.paste_target()
        if self.paste_preview is None:
            return
        self._ghost = None if target is None else (self._paste_base, target)
        self.update()

    def _paste_click(self, button: Qt.MouseButton) -> None:
        target = self.paste_target()
        if button == Qt.MouseButton.LeftButton and target is not None:
            self.cancel_paste()
            self.paste_requested.emit(target)
        elif button == Qt.MouseButton.RightButton:
            self.cancel_paste()

    # ------------------------------------------------------------------ targeting
    def _ray(self, point: QPoint) -> tuple[np.ndarray, np.ndarray]:
        width, height = max(self.width(), 1), max(self.height(), 1)
        ndc_x = 2.0 * point.x() / width - 1.0
        ndc_y = 1.0 - 2.0 * point.y() / height
        return self.camera.ray_through(ndc_x, ndc_y, width / height)

    def _screen_vector(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """On-screen vector (pixels) from world point ``a`` to ``b``."""
        width, height = max(self.width(), 1), max(self.height(), 1)
        mvp = self.camera.projection_matrix(width / height) @ self.camera.view_matrix()
        points = []
        for world in (a, b):
            clip = mvp @ np.array([*world, 1.0])
            w = clip[3] if abs(clip[3]) > 1e-9 else 1e-9
            points.append(np.array([(clip[0] / w + 1) / 2 * width, (1 - clip[1] / w) / 2 * height]))
        return points[1] - points[0]

    def _pick_at(self, point: QPoint) -> Hit | None:
        origin, direction = self._ray(point)
        self._hover_direction = direction
        return pick(self.document.level, origin, direction)

    def _update_hover(self, point: QPoint) -> None:
        hit = self._pick_at(point)
        spot = self._gizmo_at(point) if self._press is None else self.gizmo_hover
        if spot != self.gizmo_hover:
            self.gizmo_hover = spot
            self.gizmo_hover_changed.emit(spot)
            self.update()
        if hit != self.hover:
            self.hover = hit
            self.hover_changed.emit(hit)
            self._update_paste_ghost()
            self.update()
        self._update_build_ghost()  # orientation follows the cursor ray even on one cell

    def _camera_moved(self) -> None:
        if self._last_mouse is not None:
            self._update_hover(self._last_mouse)
        self._update_paste_ghost()
        self._update_build_ghost()
        self.update()

    # ------------------------------------------------------------------ helpers
    def look_at(self, target: Pos) -> None:
        self.camera.focus(np.array(target, dtype=float) + 0.5)
        self.update()

    def focus_hover(self) -> bool:
        """Move the pivot to the center of the block under the cursor."""
        if self.hover is None:
            return False
        self.look_at(self.hover.pos)
        return True

    def player_view(self) -> tuple[float, float]:
        """Yaw and pitch of a player looking at the targeted block from the camera."""
        if self._hover_direction is not None:
            return Camera.angles_of(self._hover_direction)
        return self.camera.yaw, self.camera.pitch


class _MoveDrag:
    """A selection being dragged to a new place (or copied there)."""

    def __init__(
        self, region: Region, copy: bool, plane_y: float, grab: np.ndarray, ghost: np.ndarray
    ) -> None:
        self.region = region
        self.copy = copy
        self.plane_y = plane_y
        self.grab = grab
        self.ghost = ghost
        self.dx = self.dz = self.lift = 0

    @property
    def offset_pos(self) -> Pos:
        return (self.dx, self.lift, self.dz)


class _StackDrag:
    """Copies being pulled out of a selection along one face's normal."""

    def __init__(
        self, region: Region, handle: Handle, start: QPoint, axis: np.ndarray, ghost: np.ndarray
    ) -> None:
        self.region = region
        self.handle = handle
        self.start = start
        self.axis = axis
        self.ghost = ghost
        self.length = region.size[handle.axis]
        self.count = 0

    def offset(self, copies: int) -> Pos:
        step = self.handle.normal * self.length * copies
        return (int(step[0]), int(step[1]), int(step[2]))


_HANDLES = tuple(Handle(axis, high) for axis in range(3) for high in (False, True))


def _ghost_key(ghost: tuple[np.ndarray, Pos] | None) -> tuple[int, Pos] | None:
    """Compare ghosts by mesh identity and place (comparing arrays would be elementwise)."""
    return None if ghost is None else (id(ghost[0]), ghost[1])


def _bounds(region: Region) -> tuple[np.ndarray, np.ndarray]:
    low, high = region.low, region.high
    return np.array(low, dtype=float), np.array(high, dtype=float) + 1.0


def _hex_color(text: str) -> tuple[float, float, float, float]:
    text = text.lstrip("#")
    return (int(text[0:2], 16) / 255, int(text[2:4], 16) / 255, int(text[4:6], 16) / 255, 1.0)


__all__ = ["BUILD", "NORMAL", "SELECT", "Direction", "Viewport"]
