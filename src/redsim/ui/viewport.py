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
from redsim.core.pos import Pos, offset
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document import Document
from redsim.ui.camera import Camera
from redsim.ui.geometry import ChunkedMesh, Hit, block_outline, box_lines, ghost_mesh, pick
from redsim.ui.keymap import HOLD, Keymap
from redsim.ui.pacing import RateMeter
from redsim.ui.renderer import Renderer
from redsim.ui.selection_tools import (
    Handle,
    handle_hit,
    handle_square,
    horizontal_offset,
    plane_point,
    resized,
    shifted,
    steps_along,
)
from redsim.world import blocks

BACKGROUND = (0.53, 0.70, 0.86, 1.0)
ORBIT_DEGREES_PER_PIXEL = 0.3
ZOOM_PER_NOTCH = 1.15
DRAG_THRESHOLD = 4
PIVOT_COLOR = (1.0, 0.35, 0.05, 1.0)

NORMAL, BUILD, SELECT = "normal", "build", "select"
MODE_COLORS = {
    NORMAL: QColor(60, 100, 160),
    BUILD: QColor(50, 140, 60),
    SELECT: QColor(200, 115, 25),
}
#: Short verbs for the mode badge.
CLICK_VERBS = {
    "normal.inspect": "inspect",
    "normal.use": "use",
    "build.break": "break",
    "build.place": "place",
    "build.use": "use",
    "select.block": "select",
    "select.box": "box / move / resize",
    "select.copy_drag": "copy",
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
    place_requested = Signal(object)  # Hit
    use_requested = Signal(object)  # Pos
    break_requested = Signal(object)  # Pos
    pick_requested = Signal(object)  # Pos
    select_requested = Signal(object)  # Pos | None (inspector selection)
    region_changed = Signal(object)  # Region | None
    region_move_requested = Signal(object, object, bool)  # Region, offset, copy
    paste_requested = Signal(object)  # Pos (minimum corner)
    mode_changed = Signal(str)

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
        #: SELECT mode: the face handle under the cursor, and drags in progress.
        self.handle_hover: Handle | None = None
        self._resize: tuple[Handle, Region, QPoint, np.ndarray] | None = None
        self._move: _MoveDrag | None = None
        #: Ctrl+V preview: the prefab follows the cursor until a click places it.
        self.paste_preview: Prefab | None = None
        self._ghost: tuple[np.ndarray, Pos] | None = None  # vertices at offset 0, offset
        self._paste_base = np.zeros((0, 7), dtype=np.float32)
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
        self.update()

    def set_document(self, document: Document) -> None:
        self.document = document
        self.selection = None
        self.region = None
        self._mesh_revision = -1  # the diff against the old world drops what is gone
        self.update()

    def refresh(self) -> None:
        """Call after the world changed (edits or simulation steps)."""
        self.update()

    # ------------------------------------------------------------------ GL
    def initializeGL(self) -> None:
        # Called again whenever Qt recreates the context (e.g. on re-parenting), so all GPU
        # data must be uploaded again.
        self.renderer = Renderer()
        self.world_mesh.reset()
        self._mesh_revision = -1

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
                    renderer.set_chunk(key, mesh.opaque, mesh.translucent)
            for stale in [stale for stale in renderer.chunks if stale not in chunks]:
                renderer.remove_chunk(stale)
            self._mesh_revision = self.document.revision
        renderer.upload_lines(self._overlay_lines())
        renderer.upload_top_lines(self._pivot_lines())
        self._upload_ghost(renderer)
        ratio = self.devicePixelRatioF()
        width, height = int(self.width() * ratio), int(self.height() * ratio)
        aspect = max(width, 1) / max(height, 1)
        mvp = self.camera.projection_matrix(aspect) @ self.camera.view_matrix()
        renderer.draw(mvp, width, height, BACKGROUND)
        self.frame_rate.record(time.monotonic())
        self._draw_overlays()

    def _draw_overlays(self) -> None:
        painter = QPainter(self)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        line_height = metrics.height()
        if self.overlay_text:
            width = max(metrics.horizontalAdvance(line) for line in self.overlay_text) + 12
            height = line_height * len(self.overlay_text) + 8
            painter.fillRect(6, 6, width, height, QColor(0, 0, 0, 120))
            painter.setPen(QColor(255, 255, 255))
            for index, line in enumerate(self.overlay_text):
                painter.drawText(12, 10 + metrics.ascent() + index * line_height, line)
        # Mode badge (bottom left) with what the mouse buttons do in this mode.
        badge = f" {self.mode.upper()} "
        top = self.height() - line_height - 14
        badge_width = metrics.horizontalAdvance(badge) + 8
        room = max(0, self.width() - badge_width - 30)  # the full list is in the help (F1)
        hint = metrics.elidedText(self.mode_hint(), Qt.TextElideMode.ElideRight, room)
        painter.fillRect(6, top, badge_width, line_height + 8, MODE_COLORS[self.mode])
        painter.fillRect(
            6 + badge_width,
            top,
            metrics.horizontalAdvance(hint) + 16,
            line_height + 8,
            QColor(0, 0, 0, 120),
        )
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, top + 4 + metrics.ascent(), badge)
        painter.drawText(14 + badge_width, top + 4 + metrics.ascent(), hint)
        painter.end()

    def mode_hint(self) -> str:
        """``Left Click: break · Right Click: place · …`` for the current mode."""
        parts = []
        for action, verb in CLICK_VERBS.items():
            prefix = action.split(".")[0]
            bindings = self.keymap.bindings(action)
            if bindings and prefix in (self.mode, "pick"):
                parts.append(f"{bindings[0]}: {verb}")
        return " · ".join(parts)

    def _overlay_lines(self) -> np.ndarray:
        level = self.document.level
        parts = []
        for section in self.document.sections.sections.values():
            color = _hex_color(section.color)
            for pos in section.positions:
                parts.append(box_lines(pos, (pos[0] + 1, pos[1] + 1, pos[2] + 1), color, 0.01))
        for group in self.document.groups.groups.values():
            low, high = group.region.low, group.region.high
            parts.append(
                box_lines(low, (high[0] + 1, high[1] + 1, high[2] + 1), (1, 1, 1, 1), 0.03)
            )
            for port in group.ports:
                color = (0.2, 0.5, 1.0, 1.0) if port.role == "input" else (1.0, 0.5, 0.1, 1.0)
                p = port.pos
                parts.append(box_lines(p, (p[0] + 1, p[1] + 1, p[2] + 1), color, 0.05))
        if self.region is not None:
            low, high = self.region.low, self.region.high
            parts.append(
                box_lines(low, (high[0] + 1, high[1] + 1, high[2] + 1), (0.0, 0.9, 0.9, 1.0), 0.02)
            )
            if self.mode == SELECT and self._move is None:
                parts.extend(self._handle_lines(self.region))
        if self._move is not None:
            moved = shifted(self._move.region, self._move.offset_pos)
            parts.append(_region_lines(moved, (1.0, 1.0, 1.0, 1.0), 0.03))
        paste_box = self.paste_region()
        if paste_box is not None:
            parts.append(_region_lines(paste_box, (1.0, 1.0, 1.0, 1.0), 0.03))
        if self.selection is not None:
            parts.append(block_outline(level, self.selection, (1.0, 0.85, 0.1, 1.0)))
        if self.hover is not None:
            parts.append(block_outline(level, self.hover.pos, (0.05, 0.05, 0.05, 1.0)))
            if self.mode == BUILD and self.paste_preview is None:
                cell = offset(self.hover.pos, self.hover.face)  # where a block would go
                parts.append(box_lines(cell, (cell[0] + 1, cell[1] + 1, cell[2] + 1), (1, 1, 1, 1)))
        if not parts:
            return np.zeros((0, 7), dtype=np.float32)
        return np.vstack(parts)

    def _handle_lines(self, region: Region) -> list[np.ndarray]:
        """Face handles of the selection box (the hovered one larger and yellow)."""
        parts = []
        for handle in _HANDLES:
            center, half = handle_square(region, handle)
            hovered = handle == self.handle_hover
            if hovered:
                half *= 1.4
            color = (1.0, 0.85, 0.1, 1.0) if hovered else (0.0, 0.9, 0.9, 1.0)
            lo, hi = center - half, center + half
            lo[handle.axis] = hi[handle.axis] = center[handle.axis]
            parts.append(box_lines(lo, hi, color, 0.01))
        return parts

    def _upload_ghost(self, renderer: Renderer) -> None:
        ghost = self._ghost
        key = None if ghost is None else (id(ghost[0]), ghost[1])
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
    def keyPressEvent(self, event: QKeyEvent) -> None:
        action = self._held_actions.get(event.key())
        if action is not None and not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            self._held.add(action)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
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
        self._update_hover(point)
        if self._press is None:
            return
        start, button, modifiers = self._press
        if self._drag_action is None:
            if (point - start).manhattanLength() <= DRAG_THRESHOLD:
                return
            name = _BUTTON_NAMES.get(button)
            action = self.keymap.mouse_action(self.mode, modifiers, name, "Drag")
            self._drag_action = action or ""
            if self._drag_action in ("select.box", "select.copy_drag"):
                self._begin_select_drag(start, copy=self._drag_action == "select.copy_drag")
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
            if self.paste_preview is not None:
                self._paste_click(button)
            else:
                name = _BUTTON_NAMES.get(button)
                action = self.keymap.mouse_action(self.mode, modifiers, name, "Click")
                if action is not None:
                    self._click(action)
        elif drag_action in ("select.box", "select.copy_drag"):
            self._end_select_drag()
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
        action = self.keymap.mouse_action(self.mode, modifiers, None, "Wheel")
        if action == "camera.zoom":
            self.camera.zoom(ZOOM_PER_NOTCH**-steps)
        elif action == "camera.vertical":
            self.camera.raise_pivot(steps)  # one block per notch
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
        else:
            return
        self._camera_moved()

    def _click(self, action: str) -> None:
        hit = self.hover
        if action == "normal.inspect":
            self.selection = hit.pos if hit else None
            self.select_requested.emit(self.selection)
        elif action == "select.block":
            self._region_anchor = hit.pos if hit else None
            self.region = Region.from_corners(hit.pos, hit.pos) if hit else None
            self.region_changed.emit(self.region)
        elif action == "select.extend" and hit is not None:
            anchor = self._region_anchor or hit.pos
            self._region_anchor = anchor
            self.region = Region.from_corners(anchor, hit.pos)
            self.region_changed.emit(self.region)
        elif hit is None:
            return
        elif action == "pick":
            self.pick_requested.emit(hit.pos)
        elif action in ("normal.use", "build.use"):
            self.use_requested.emit(hit.pos)
        elif action == "build.break":
            self.break_requested.emit(hit.pos)
        elif action == "build.place":
            self.place_requested.emit(hit)

    # ------------------------------------------------------------------ selections
    def _begin_select_drag(self, start: QPoint, copy: bool) -> None:
        """A left drag in SELECT mode: resize from a handle, move/copy from inside the box,
        otherwise draw a new box."""
        origin, direction = self._ray(start)
        block = pick(self.document.level, origin, direction)
        region = self.region
        if region is not None and not copy:
            handle = handle_hit(region, origin, direction)
            if handle is not None and (block is None or handle[1] <= block.distance + 0.01):
                center, _ = handle_square(region, handle[0])
                axis = self._screen_vector(center, center + handle[0].normal)
                self._resize = (handle[0], region, start, axis)
                return
        if region is not None and block is not None and region.contains(block.pos):
            grab = origin + direction * block.distance
            ghost = self._region_ghost(region)
            self._move = _MoveDrag(region, copy, float(grab[1]), grab, ghost)
            self._ghost = (ghost, (0, 0, 0))
            return
        if copy:
            return  # copy-drags start inside the selection
        self._region_anchor = block.pos if block else None
        self._extend_box()

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
        """Minimum corner of the paste: the cell in front of the targeted face."""
        if self.hover is None:
            return None
        return offset(self.hover.pos, self.hover.face)

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
        handle = None
        if self.mode == SELECT and self.region is not None and self._press is None:
            origin, direction = self._ray(point)
            found = handle_hit(self.region, origin, direction)
            if found is not None and (hit is None or found[1] <= hit.distance + 0.01):
                handle = found[0]
        if handle != self.handle_hover:
            self.handle_hover = handle
            self.update()
        if hit != self.hover:
            self.hover = hit
            self.hover_changed.emit(hit)
            self._update_paste_ghost()
            self.update()

    def _camera_moved(self) -> None:
        if self._last_mouse is not None:
            self._update_hover(self._last_mouse)
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


_HANDLES = tuple(Handle(axis, high) for axis in range(3) for high in (False, True))


def _region_lines(
    region: Region, color: tuple[float, float, float, float], grow: float
) -> np.ndarray:
    high = region.high
    return box_lines(region.low, (high[0] + 1, high[1] + 1, high[2] + 1), color, grow)


def _hex_color(text: str) -> tuple[float, float, float, float]:
    text = text.lstrip("#")
    return (int(text[0:2], 16) / 255, int(text[2:4], 16) / 255, int(text[4:6], 16) / 255, 1.0)


__all__ = ["BUILD", "NORMAL", "SELECT", "Direction", "Viewport"]
