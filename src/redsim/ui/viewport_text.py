"""2D overlays of the viewport in the game's pixel font: status lines, the mode badge, F3
columns and signal labels (with their range slider), sign text, the welcome text and the
Tab mode ring."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, cast

import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QPolygon,
)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor import pins, sources
from redsim.ui import theme
from redsim.ui.debug_screen import block_lines
from redsim.ui.geometry import pick
from redsim.ui.names import block_name
from redsim.ui.preferences import INT_RANGES
from redsim.ui.sign_text import (
    board_image,
    boards,
    draw_board,
    facing_camera,
    sign_lines,
    text_color,
)
from redsim.ui.view_common import (
    BUILD,
    CLICK_VERBS,
    INFO_COLORS,
    INFO_LABEL_LIMIT,
    MODE_COLORS,
    NORMAL,
    PASTE_COLOR,
    RING_DEAD_ZONE,
    RING_MODES,
    RING_RADIUS,
    SELECT,
    SIGN_TEXT_DISTANCE,
    _elide,
)
from redsim.world.blocks.sign import SignBlockEntity
from redsim.world.properties import POWER

#: Pinned value tags (``_draw_pins``): background, accent bar, how far they show.
PIN_BACKGROUND = QColor(18, 18, 24, 210)
PIN_ACCENT = QColor(255, 210, 74)
PIN_DISTANCE = 72.0

if TYPE_CHECKING:
    from redsim.ui.viewport import Viewport


class TextOverlays:
    """Part of ``Viewport`` (a mixin; its methods run on the viewport)."""

    def _draw_overlays(self) -> None:
        """2D overlays in the game's pixel font (``theme.draw_text``): status lines, the
        mode badge with the mouse hints, view tags, F3 columns and signal labels."""
        view = cast("Viewport", self)
        if view.label_range.isVisible() != view.show_info:
            view.label_range.setVisible(view.show_info)
            view.label_range.place()
        painter = QPainter(view)
        line = theme.line_height(2)
        view._draw_sign_texts(painter)
        view._draw_pins(painter)
        if view.show_info:
            view._draw_info_labels(painter)
            view._draw_debug_columns(painter)
        if view.overlay_text and not view.show_info:
            for index, text in enumerate(view.overlay_text):
                top = 8 + index * (line + 4)
                painter.fillRect(
                    8, top, theme.text_width(text) + 12, line + 4, QColor(0, 0, 0, 110)
                )
                theme.draw_text(painter, 14, top + 3, text, "#ffffff")
        if not view.show_info and view.paste_preview is None:
            view._draw_welcome(painter)
        # Mode badge (bottom left) with what the mode works on (the hint bar below the
        # window lists the keys).
        pasting = view.paste_preview is not None
        badge = "PASTE" if pasting else view.mode.upper()
        top = view.height() - line - 16
        badge_width = theme.text_width(badge) + 16
        room = max(0, view.width() - badge_width - 40)
        hint = _elide(view.mode_status(), room)
        covered = view._overlay_top(8, 8 + badge_width + theme.text_width(hint) + 22)
        if covered is not None:  # the hotbar is in the way: sit just above it
            top = min(top, covered - line - 14)
        color = PASTE_COLOR if pasting else MODE_COLORS[view.mode]
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 120))
        if hint:
            width = badge_width + theme.text_width(hint) + 22
            painter.drawRoundedRect(8, top, width, line + 8, 5, 5)
        painter.setBrush(color)
        painter.drawRoundedRect(8, top, badge_width, line + 8, 5, 5)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        theme.draw_text(painter, 16, top + 5, badge, "#ffffff")
        theme.draw_text(painter, 18 + badge_width, top + 5, hint, theme.TEXT)
        xray_tag = ("", "X-RAY", "X-RAY ALL")[view.xray]
        flags = [name for name, on in ((xray_tag, view.xray), ("INFO", view.show_info)) if on]
        if flags:
            tag = " · ".join(flags)
            tag_top = top - line - 14
            painter.fillRect(8, tag_top, theme.text_width(tag) + 16, line + 8, QColor(0, 0, 0, 150))
            theme.draw_text(painter, 16, tag_top + 5, tag, theme.GOLD)
        view._draw_ring(painter)
        painter.end()

    def info_labels(self, max_distance: float | None = None) -> list[tuple[np.ndarray, str, str]]:
        """Signal values shown by the info overlay: (world point, text, kind), nearest last.

        Wire: its power; signal sources (barrel, lectern, cake): the value a comparator
        reads; comparators: their stored output signal. Within ``max_distance`` (default:
        the F3 range preference)."""
        view = cast("Viewport", self)
        return [(point, text, kind) for point, text, kind, _, _ in view._labels(max_distance)]

    def _labels(
        self, max_distance: float | None = None
    ) -> list[tuple[np.ndarray, str, str, Pos, float]]:
        """``info_labels`` with each label's block and opacity (fading out over the last
        third of the range). Distances count from the camera pivot."""
        view = cast("Viewport", self)
        if max_distance is None:
            max_distance = float(view.preferences.info_label_range)
        level = view.document.level
        eye = np.asarray(view.camera.pivot, dtype=float)  # zooming keeps the same labels
        labels: list[tuple[float, np.ndarray, str, str, Pos]] = []
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
                labels.append((distance, point, text, kind, pos))
        labels.sort(key=lambda label: -label[0])
        fade = max(1.0, max_distance / 3)
        return [
            (point, text, kind, pos, min(1.0, (max_distance - distance) / fade))
            for distance, point, text, kind, pos in labels[-INFO_LABEL_LIMIT:]
        ]

    def _draw_debug_columns(self, painter: QPainter) -> None:
        """Minecraft's F3 text: world state on the left, the targeted block on the right,
        each line on its own grey strip."""
        view = cast("Viewport", self)
        line = theme.line_height(2) + 2
        right = block_lines(view.document, view.hover.pos) if view.hover is not None else []
        for lines, align_right in ((view.debug_left, False), (right, True)):
            for index, text in enumerate(lines):
                width = theme.text_width(text) + 6
                left = view.width() - width - 4 if align_right else 4
                top = 4 + index * line
                painter.fillRect(left, top, width, line, QColor(80, 80, 80, 144))
                theme.draw_text(painter, left + 3, top + 2, text, "#e0e0e0")

    def _draw_sign_texts(self, painter: QPainter) -> None:
        """Sign text on the signs' boards (``ui/sign_text.py``): both sides, in
        perspective, within ``SIGN_TEXT_DISTANCE`` (fading out), not through blocks."""
        view = cast("Viewport", self)
        document = view.document
        level = document.level
        positions = {
            pos
            for pos, entity in level.block_entities.items()
            if isinstance(entity, SignBlockEntity)
        }
        for key in document.extra.get("signs") or {}:
            x, y, z = (int(v) for v in key.split(","))
            positions.add((x, y, z))
        if not positions:
            return
        width, height = max(view.width(), 1), max(view.height(), 1)
        mvp = (
            view.camera.projection_matrix(width / height, lens=view.lens)
            @ view.camera.view_matrix()
        )
        eye = np.asarray(view.camera.position, dtype=float)
        for pos in positions:
            state = level.blocks.get(pos)
            if state is None:
                continue
            for board in boards(pos, state):
                distance = float(np.linalg.norm(board.center - eye))
                if distance > SIGN_TEXT_DISTANCE or not facing_camera(board, eye):
                    continue
                lines, dye, glowing = sign_lines(document, pos, board.side)
                if not any(lines):
                    continue
                ray = board.center - eye
                hit = pick(level, eye, ray / max(distance, 1e-6), distance)
                if hit is not None and hit.pos != pos and hit.distance < distance - 0.05:
                    continue  # another block is in front
                image = board_image(
                    tuple(lines), board.width, board.height, text_color(dye, glowing).name()
                )
                if image is None:
                    continue
                painter.setOpacity(min(1.0, (SIGN_TEXT_DISTANCE - distance) / 4.0))
                draw_board(painter, image, board, mvp, width, height)
        painter.setOpacity(1.0)

    def _draw_pins(self, painter: QPainter) -> None:
        """Pinned values (the block popup's pin chips, ``editor/pins.py``): a small tag
        above each pinned block, live, fading out far away."""
        view = cast("Viewport", self)
        document = view.document
        pinned = pins.pins(document)
        if not pinned:
            return
        width, height = max(view.width(), 1), max(view.height(), 1)
        mvp = (
            view.camera.projection_matrix(width / height, lens=view.lens)
            @ view.camera.view_matrix()
        )
        eye = np.asarray(view.camera.position, dtype=float)
        line = theme.line_height(2)
        for pos, keys in pinned.items():
            texts = pins.lines(document, pos, keys)
            if not texts:
                continue
            point = np.array([pos[0] + 0.5, pos[1] + 1.05, pos[2] + 0.5])
            distance = float(np.linalg.norm(point - eye))
            alpha = min(1.0, (PIN_DISTANCE - distance) / 8.0)
            clip = mvp @ np.array([*point, 1.0])
            if clip[3] <= 0.05 or alpha <= 0:
                continue
            x = (clip[0] / clip[3] + 1) / 2 * width
            y = (1 - clip[1] / clip[3]) / 2 * height
            if not (-200 <= x <= width + 200 and 0 <= y <= height + 200):
                continue
            box_width = max(theme.text_width(text) for text in texts) + 14
            box_height = len(texts) * (line + 2) + 6
            rect = QRect(int(x - box_width / 2), int(y - box_height - 7), box_width, box_height)
            painter.setOpacity(alpha)
            painter.fillRect(rect, PIN_BACKGROUND)
            painter.fillRect(QRect(rect.left(), rect.top(), 2, rect.height()), PIN_ACCENT)
            tip = QPolygon(
                [
                    QPoint(int(x) - 5, rect.bottom() + 1),
                    QPoint(int(x) + 5, rect.bottom() + 1),
                    QPoint(int(x), rect.bottom() + 7),
                ]
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(PIN_BACKGROUND)
            painter.drawPolygon(tip)
            for index, text in enumerate(texts):
                theme.draw_text(
                    painter, rect.left() + 8, rect.top() + 4 + index * (line + 2), text, "#ffffff"
                )
        painter.setOpacity(1.0)

    def _draw_info_labels(self, painter: QPainter) -> None:
        view = cast("Viewport", self)
        width, height = max(view.width(), 1), max(view.height(), 1)
        mvp = (
            view.camera.projection_matrix(width / height, lens=view.lens)
            @ view.camera.view_matrix()
        )
        line = theme.line_height(2)
        rects: list[tuple[QRect, Pos]] = []
        for point, text, kind, pos, alpha in view._labels():
            clip = mvp @ np.array([*point, 1.0])
            if clip[3] <= 0.05 or alpha <= 0:
                continue  # behind the camera, or faded out
            x = (clip[0] / clip[3] + 1) / 2 * width
            y = (1 - clip[1] / clip[3]) / 2 * height
            if not (0 <= x <= width and 0 <= y <= height):
                continue
            box_width = theme.text_width(text) + 10
            box_height = line + 4
            rect = QRect(int(x - box_width / 2), int(y - box_height / 2), box_width, box_height)
            hovered = pos == view.hovered_label
            background = INFO_COLORS[kind]
            if text == "0":
                background = QColor(70, 70, 70, 170)
            painter.setOpacity(1.0 if hovered else alpha)
            if hovered:  # a white frame and a little larger: F jumps to it
                painter.fillRect(rect.adjusted(-2, -2, 2, 2), QColor(255, 255, 255, 230))
            painter.fillRect(rect, background)
            theme.draw_text(painter, rect.left() + 5, rect.top() + 3, text, "#ffffff")
            rects.append((rect, pos))
        painter.setOpacity(1.0)
        view._label_rects = rects

    @property
    def label_range(self) -> LabelRange:
        """The F3 labels' range slider (top center), made on first use."""
        view = cast("Viewport", self)
        if view._label_range is None:
            view._label_range = LabelRange(view)
        return view._label_range

    def label_at(self, point: QPoint) -> Pos | None:
        """The block of the F3 label under ``point`` (the nearest label wins)."""
        view = cast("Viewport", self)
        for rect, pos in reversed(view._label_rects):
            if rect.contains(point):
                return pos
        return None

    def welcome_lines(self) -> list[str]:
        """How to start, while the world is only its floor (nothing above y=0)."""
        view = cast("Viewport", self)
        if any(pos[1] > 0 for pos in view.document.level.blocks):
            return []

        def key(action: str) -> str:
            bindings = view.keymap.bindings(action)
            return bindings[0] if bindings else "?"

        build = f"Press {key('mode.build')} to build" if view.mode != BUILD else "Building"
        return [
            f"{build}: pick a block with 1-9, the hotbar or {key('search.blocks')}",
            f"{key('camera.orbit')} orbits · the wheel moves the camera up and down",
            f"{key('help.controls')} lists every key",
        ]

    def _draw_welcome(self, painter: QPainter) -> None:
        view = cast("Viewport", self)
        lines = view.welcome_lines()
        if not lines:
            return
        line = theme.line_height(2) + 6
        top = view.height() // 4
        title = "An empty world"
        width = max(theme.text_width(text) for text in [title, *lines]) + 40
        height = (len(lines) + 1) * line + 30
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(16, 16, 20, 170))
        painter.drawRoundedRect((view.width() - width) // 2, top - 14, width, height, 6, 6)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        theme.draw_text(
            painter, (view.width() - theme.text_width(title)) // 2, top, title, theme.GOLD
        )
        for index, text in enumerate(lines, start=1):
            x = (view.width() - theme.text_width(text)) // 2
            theme.draw_text(painter, x, top + index * line + 6, text, "#ffffff")

    def ring_mode_at(self, point: QPoint) -> str | None:
        """The mode of the Tab ring in the direction of ``point`` (None near the center)."""
        view = cast("Viewport", self)
        if view.ring is None:
            return None
        center = view.ring[0]
        dx, dy = point.x() - center.x(), point.y() - center.y()
        if math.hypot(dx, dy) < RING_DEAD_ZONE:
            return None
        angle = math.degrees(math.atan2(dx, -dy)) % 360  # 0 = up, clockwise
        return RING_MODES[int(((angle + 45) % 360) // 90)]

    def _draw_ring(self, painter: QPainter) -> None:
        """The Tab ring: the modes around the cursor, the pointed one highlighted."""
        view = cast("Viewport", self)
        if view.ring is None:
            return
        center, chosen = view.ring
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor(255, 255, 255, 90), 2))
        painter.setBrush(QColor(20, 20, 24, 150))
        painter.drawEllipse(center, RING_RADIUS + 30, RING_RADIUS + 30)
        painter.setBrush(QColor(255, 255, 255, 60))
        painter.drawEllipse(center, RING_DEAD_ZONE, RING_DEAD_ZONE)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        line = theme.line_height(2)
        for index, mode in enumerate(RING_MODES):
            angle = math.radians(index * 90)
            x = center.x() + RING_RADIUS * math.sin(angle)
            y = center.y() - RING_RADIUS * math.cos(angle)
            text = mode.upper()
            width = theme.text_width(text) + 16
            box = QRect(int(x - width / 2), int(y - line / 2 - 4), width, line + 8)
            color = MODE_COLORS[mode]
            painter.fillRect(box, color if mode == chosen else QColor(40, 40, 46, 220))
            if mode == chosen:
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(box.adjusted(-1, -1, 0, 0))
            elif mode == view.mode:
                painter.fillRect(box.left(), box.bottom() - 2, box.width(), 3, color)
            theme.draw_text(painter, box.left() + 8, box.top() + 4, text, "#ffffff")

    def mode_status(self) -> str:
        """What the badge shows next to the mode: the block to place and the layer, the
        selection's size, or the inspected block."""
        view = cast("Viewport", self)
        if view.paste_preview is not None:
            return f"layer y={view.working_height()}"
        if view.mode == BUILD:
            block = block_name(view.build_block.id) if view.build_block else "no block chosen"
            variant = view.build_variant()
            variant = f" ({variant})" if variant else ""
            return f"{block}{variant} · layer y={view.working_height()}"
        if view.mode == SELECT and view.region is not None:
            low, high = view.region.low, view.region.high
            dx, dy, dz = (high[i] - low[i] + 1 for i in range(3))
            locked = " · locked" if view.region_locked else ""
            return f"{dx}×{dy}×{dz} = {dx * dy * dz} blocks{locked}"
        if view.mode == NORMAL and view.selection is not None:
            state = view.document.state_at(view.selection)
            x, y, z = view.selection
            return f"{block_name(state.block.id)} at {x} {y} {z}"
        return ""

    def mode_hint(self) -> str:
        """``Left Click: place · Left Drag: line · …`` for the current mode."""
        view = cast("Viewport", self)
        parts = []
        for action, verb in CLICK_VERBS.items():
            prefix = action.split(".")[0]
            bindings = view.keymap.bindings(action)
            if bindings and prefix in (view.mode, "pick"):
                parts.append(f"{bindings[0]}: {verb}")
        if view.mode == BUILD:
            delete = view.keymap.bindings("edit.delete")
            if delete:
                parts.insert(3, f"{delete[0]}: remove")
            parts.insert(0, f"layer y={view.working_height()} (Wheel moves it)")
        return " · ".join(parts)


class LabelRange(QWidget):
    """F3's range slider for the signal labels (top center of the view)."""

    def __init__(self, viewport: Viewport) -> None:
        super().__init__(viewport)
        self.viewport = viewport
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        self.text = QLabel()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(*INT_RANGES["info_label_range"])
        self.slider.setFixedWidth(140)
        self.slider.setValue(viewport.preferences.info_label_range)
        self.slider.setToolTip("How far signal labels show (they fade out towards the end)")
        self.slider.valueChanged.connect(self._changed)
        layout.addWidget(self.text)
        layout.addWidget(self.slider)
        self.setStyleSheet("background: rgba(40, 40, 44, 200); color: #e0e0e0;")
        self._changed(self.slider.value())
        self.hide()

    def _changed(self, value: int) -> None:
        self.viewport.preferences.info_label_range = value
        self.text.setText(f"Labels within {value} blocks")
        self.viewport.update()

    def place(self) -> None:
        self.adjustSize()
        self.move((self.viewport.width() - self.width()) // 2, 6)
