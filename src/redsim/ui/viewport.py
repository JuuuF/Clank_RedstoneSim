"""3D viewport: camera control, targeting and edit requests (Minecraft-style controls).

Controls (confirmed by the owner): WASD move, Space up, Shift down, Ctrl faster; hold the
right mouse button and drag to look around; left click breaks, right click places (or uses a
usable block; Shift+right click always places), middle click picks the block type,
Ctrl+left click selects a block for the inspector.

The viewport never edits the world itself; it emits signals that the main window turns into
document edits.
"""

from __future__ import annotations

import time

import numpy as np
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QFontDatabase,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QWheelEvent,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.ui.camera import Camera
from redsim.ui.geometry import ChunkedMesh, Hit, block_outline, box_lines, pick
from redsim.ui.pacing import RateMeter
from redsim.ui.renderer import Renderer

BACKGROUND = (0.53, 0.70, 0.86, 1.0)
LOOK_SENSITIVITY = 0.25
DRAG_THRESHOLD = 4
SPEED = 6.0  # blocks per second


class Viewport(QOpenGLWidget):
    hover_changed = Signal(object)  # Hit | None
    place_requested = Signal(object, bool)  # Hit, force_place (shift)
    break_requested = Signal(object)  # Pos
    pick_requested = Signal(object)  # Pos
    select_requested = Signal(object)  # Pos | None

    def __init__(self, document: Document, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.document = document
        self.camera = Camera()
        self.renderer: Renderer | None = None
        self.hover: Hit | None = None
        self.selection: Pos | None = None
        self.region: Region | None = None
        self.world_mesh = ChunkedMesh()
        self._mesh_revision = -1
        #: Lines of text drawn over the top-left corner (run status, achieved rates).
        self.overlay_text: list[str] = []
        self.frame_rate = RateMeter()
        self._keys: set[int] = set()
        self._press_pos: QPoint | None = None
        self._press_button: Qt.MouseButton | None = None
        self._looking = False
        self._last_mouse: QPoint | None = None
        self._last_frame = time.monotonic()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_camera)
        self._timer.start(16)

    # ------------------------------------------------------------------ document
    def set_document(self, document: Document) -> None:
        self.document = document
        self.selection = None
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
        ratio = self.devicePixelRatioF()
        width, height = int(self.width() * ratio), int(self.height() * ratio)
        aspect = max(width, 1) / max(height, 1)
        mvp = self.camera.projection_matrix(aspect) @ self.camera.view_matrix()
        renderer.draw(mvp, width, height, BACKGROUND)
        self.frame_rate.record(time.monotonic())
        if self.overlay_text:
            self._draw_overlay_text()

    def _draw_overlay_text(self) -> None:
        painter = QPainter(self)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        line_height = metrics.height()
        width = max(metrics.horizontalAdvance(line) for line in self.overlay_text) + 12
        height = line_height * len(self.overlay_text) + 8
        painter.fillRect(6, 6, width, height, QColor(0, 0, 0, 120))
        painter.setPen(QColor(255, 255, 255))
        for index, line in enumerate(self.overlay_text):
            painter.drawText(12, 10 + metrics.ascent() + index * line_height, line)
        painter.end()

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
        if self.selection is not None:
            parts.append(block_outline(level, self.selection, (1.0, 0.85, 0.1, 1.0)))
        if self.hover is not None:
            parts.append(block_outline(level, self.hover.pos, (0.05, 0.05, 0.05, 1.0)))
        if not parts:
            return np.zeros((0, 7), dtype=np.float32)
        return np.vstack(parts)

    # ------------------------------------------------------------------ input
    def keyPressEvent(self, event: QKeyEvent) -> None:
        self._keys.add(event.key())
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self._keys.discard(event.key())
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._keys.clear()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        self._press_pos = event.position().toPoint()
        self._press_button = event.button()
        self._last_mouse = self._press_pos
        self._looking = False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()
        if event.buttons() & Qt.MouseButton.RightButton and self._last_mouse is not None:
            assert self._press_pos is not None
            if (pos - self._press_pos).manhattanLength() > DRAG_THRESHOLD:
                self._looking = True
            if self._looking:
                delta = pos - self._last_mouse
                self.camera.rotate(delta.x() * LOOK_SENSITIVITY, delta.y() * LOOK_SENSITIVITY)
        self._last_mouse = pos
        self._update_hover(pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        button = event.button()
        modifiers = event.modifiers()
        if button == self._press_button and not self._looking:
            self._update_hover(event.position().toPoint())
            hit = self.hover
            if button == Qt.MouseButton.LeftButton:
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    self.selection = hit.pos if hit else None
                    self.select_requested.emit(self.selection)
                elif hit is not None:
                    self.break_requested.emit(hit.pos)
            elif button == Qt.MouseButton.RightButton and hit is not None:
                self.place_requested.emit(hit, bool(modifiers & Qt.KeyboardModifier.ShiftModifier))
            elif button == Qt.MouseButton.MiddleButton and hit is not None:
                self.pick_requested.emit(hit.pos)
        self._looking = False
        self._press_button = None
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.camera.fov = max(20.0, min(100.0, self.camera.fov - event.angleDelta().y() / 60.0))
        self.update()

    def _update_hover(self, point: QPoint) -> None:
        width, height = max(self.width(), 1), max(self.height(), 1)
        ndc_x = 2.0 * point.x() / width - 1.0
        ndc_y = 1.0 - 2.0 * point.y() / height
        origin, direction = self.camera.ray_through(ndc_x, ndc_y, width / height)
        hit = pick(self.document.level, origin, direction)
        if hit != self.hover:
            self.hover = hit
            self.hover_changed.emit(hit)
            self.update()

    def _tick_camera(self) -> None:
        now = time.monotonic()
        dt = min(now - self._last_frame, 0.1)
        self._last_frame = now
        keys = self._keys
        if not keys:
            return
        speed = SPEED * (3.0 if Qt.Key.Key_Control in keys else 1.0) * dt
        forward = (Qt.Key.Key_W in keys) - (Qt.Key.Key_S in keys)
        strafe = (Qt.Key.Key_D in keys) - (Qt.Key.Key_A in keys)
        up = (Qt.Key.Key_Space in keys) - (Qt.Key.Key_Shift in keys)
        if forward or strafe or up:
            self.camera.move(forward * speed, strafe * speed, up * speed)
            if self._last_mouse is not None:
                self._update_hover(self._last_mouse)
            self.update()

    # ------------------------------------------------------------------ helpers
    def look_at(self, target: Pos) -> None:
        self.camera.position = np.array([target[0] + 0.5, target[1] + 5.0, target[2] - 6.0])
        self.camera.yaw, self.camera.pitch = 0.0, 35.0
        self.update()

    def player_view(self) -> tuple[float, float]:
        return self.camera.yaw, self.camera.pitch


def _hex_color(text: str) -> tuple[float, float, float, float]:
    text = text.lstrip("#")
    return (int(text[0:2], 16) / 255, int(text[2:4], 16) / 255, int(text[4:6], 16) / 255, 1.0)


__all__ = ["Direction", "Viewport"]
