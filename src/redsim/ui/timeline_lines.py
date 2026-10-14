"""The timeline's per-block lines: each category opens into one line per block position,
in the owner's colored groups and order (drag a line's label to reorder it or move it to
another group). Powered lines have pulse bars to select, move (also onto another line),
stretch, add, delete and mute; the other categories show their edits as diamonds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QMenu,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor.document import EDIT_ROWS, Pulse
from redsim.ui import pixel_icons
from redsim.ui.timeline_common import BACKGROUND, ROW_COLORS, ROW_TITLES

if TYPE_CHECKING:
    from redsim.ui.timeline import TimelineCanvas


class LineArea:
    """Part of ``TimelineCanvas`` (a mixin; its methods run on it)."""

    def _build_lines(self) -> None:
        """The edit area's lines: each category, and when expanded its groups and their
        per-block lines (in the user's groups and order)."""
        view = cast("TimelineCanvas", self)
        lines: list[_Line] = []
        for row in EDIT_ROWS:
            groups = view.groups.get(row, [])
            has = any(g.members for g in groups)
            open_ = has and row in view.expanded
            lines.append(_Line("category", row, ROW_TITLES[row], 0, ROW_COLORS[row], None,
                               None, has, open_))  # fmt: skip
            if not open_:
                continue
            for index, group in enumerate(groups):
                color = QColor(group.color)
                title = f"{group.name} ({len(group.members)})"
                lines.append(_Line("group", row, title, 1, color, index, None, True,
                                   not group.collapsed))  # fmt: skip
                if not group.collapsed:
                    for pos in group.members:
                        lines.append(view._block_line(row, pos, color, 2, index))
        view.lines = lines
        tops, y = [], view.RULER_HEIGHT
        for _ in lines:
            tops.append(y)
            y += view.EDIT_ROW_HEIGHT
        view._tops = tops

    def _block_line(
        self, row: str, pos: Pos, color: QColor, depth: int, group: int | None
    ) -> _Line:
        view = cast("TimelineCanvas", self)
        where = " ".join(str(v) for v in pos)
        # The block there now (at the current tick): pistons move blocks, the line stays
        # with the position.
        line = _Line("block", row, where, depth, color, group, pos)
        line.detail = view.names.get(pos, "")
        return line

    def _line_at(self, y: float) -> int | None:
        view = cast("TimelineCanvas", self)
        if y < view.RULER_HEIGHT:
            return None
        index = int((y - view.RULER_HEIGHT) // view.EDIT_ROW_HEIGHT)
        return index if 0 <= index < len(view.lines) else None

    def _power_positions(self) -> list[Pos]:
        """The positions of the shown Powered lines, top to bottom."""
        view = cast("TimelineCanvas", self)
        return [
            line.pos
            for line in view.lines
            if line.kind == "block" and line.row == "power" and line.pos is not None
        ]

    def _previewed(self, pulse: Pulse) -> tuple[int, int, Pos]:
        """Where a pulse is shown: moved or stretched while the selection is dragged."""
        view = cast("TimelineCanvas", self)
        tick, ticks, pos = pulse.tick, pulse.ticks, pulse.pos
        if view._pulse_drag is None or pulse.index not in view.selected_pulses:
            return tick, ticks, pos
        mode = view._pulse_drag[1]
        dt, dl = view._drag_offset
        if mode == "resize":
            return tick, max(0, ticks + dt), pos
        if dl:
            order = view._power_positions()
            if pos in order:
                pos = order[max(0, min(len(order) - 1, order.index(pos) + dl))]
        return max(1, tick + dt), ticks, pos

    def _pulse_box(self, tick: int, ticks: int, top: float) -> QRectF:
        view = cast("TimelineCanvas", self)
        left, right = view._x(tick), view._x(tick + ticks)
        return QRectF(left, top + 3, max(4.0, right - left), view.EDIT_ROW_HEIGHT - 6)

    def _paint_block_lines(self, painter: QPainter) -> None:
        """Per-block lines: pulse bars (Powered, in the group's color, 0-ticks as thin
        marks) or the block's edits as small diamonds."""
        view = cast("TimelineCanvas", self)
        for line, top in zip(view.lines, view._tops, strict=True):
            y = top + view.EDIT_ROW_HEIGHT / 2
            if line.kind == "group":  # a faint summary of the group's pulses or edits
                groups = view.groups.get(line.row, [])
                members = set(groups[line.group or 0].members) if groups else set()
                color = QColor(line.color)
                color.setAlpha(70)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                if line.row == "power":
                    for pulse in view.pulses:
                        if pulse.pos in members:
                            painter.drawRect(view._pulse_box(pulse.tick, pulse.ticks, top))
                    continue
                for event in view.events:
                    if event.row == line.row and event.pos in members:
                        x = view._x(event.tick)
                        if x >= view.LABEL_WIDTH:
                            painter.drawPolygon(_diamond(x, y, 3.0))
                continue
            if line.kind != "block":
                continue
            if line.row == "power":
                for pulse in view.pulses:
                    tick, ticks, pos = view._previewed(pulse)
                    if pos != line.pos:
                        continue
                    box = view._pulse_box(tick, ticks, top)
                    if box.right() < view.LABEL_WIDTH:
                        continue
                    fill = QColor(line.color)
                    fill.setAlpha(110 + 9 * pulse.strength)
                    edge = QPen(fill.lighter(150), 1)
                    if pulse.muted:  # bypassed: grey and dashed
                        fill = QColor(120, 120, 128, 70)
                        edge = QPen(QColor(150, 150, 158), 1, Qt.PenStyle.DashLine)
                    selected = pulse.index in view.selected_pulses
                    painter.setPen(QPen(QColor(255, 255, 255), 1.6) if selected else edge)
                    painter.setBrush(fill)
                    painter.drawRoundedRect(box, 2, 2)
                continue
            painter.setBrush(line.color)
            painter.setPen(QPen(BACKGROUND, 1))
            for event in view.events:
                if event.row == line.row and event.pos == line.pos:
                    x = view._x(event.tick)
                    if x >= view.LABEL_WIDTH:
                        painter.drawPolygon(_diamond(x, y, 3.5))

    def _pulse_hit(self, line: _Line, x: float, top: float) -> tuple[Pulse, str] | None:
        """The pulse of a Powered line under ``x``: ("resize" near its end, else "move")."""
        view = cast("TimelineCanvas", self)
        for pulse in reversed(view.pulses):
            if pulse.pos != line.pos:
                continue
            box = view._pulse_box(pulse.tick, pulse.ticks, top)
            if abs(x - box.right()) <= 4 and pulse.ticks > 0:
                return pulse, "resize"
            if box.left() - 3 <= x <= box.right():
                return pulse, "move"
        return None

    def _line_press(self, event: QMouseEvent, line: _Line, top: float) -> bool:
        """Clicks on the lines' labels and on pulse bars; True when handled."""
        view = cast("TimelineCanvas", self)
        x, y = event.position().x(), event.position().y()
        left_button = event.button() == Qt.MouseButton.LeftButton
        right_button = event.button() == Qt.MouseButton.RightButton
        where = event.globalPosition().toPoint()
        block = line.kind == "block" and line.pos is not None
        power_block = block and line.row == "power"
        if x < view.LABEL_WIDTH:
            if left_button and line.kind == "category" and line.expandable:
                view.expanded ^= {line.row}
                view._build_lines()
                view._resize_to_tracks()
                view.update()
                return True
            if left_button and line.kind == "group" and line.group is not None:
                view.group_request.emit("toggle", line.row, line.group)
                return True
            if left_button and block:
                assert line.pos is not None
                view._line_drag = (line.row, line.pos, y)
                return True
            if right_button and line.kind == "category" and line.row == "power":
                self._power_menu(where)
                return True
            if right_button and line.kind == "group" and line.group is not None:
                view._group_menu(where, line.row, line.group)
                return True
            if right_button and block:
                assert line.pos is not None
                view._line_menu(where, line.row, line.pos)
                return True
            return False
        if not power_block:
            return False
        hit = view._pulse_hit(line, x, top)
        if right_button and hit is not None:
            menu = QMenu(view)
            pulse = hit[0]
            remove = menu.addAction(f"Delete this pulse (tick {pulse.tick}, {pulse.ticks} ticks)")
            remove.setIcon(pixel_icons.pixel_icon("delete"))
            remove.triggered.connect(lambda: view.pulses_deleted.emit([pulse.index]))
            mute = menu.addAction("Unmute this pulse" if pulse.muted else "Mute this pulse (0)")
            mute.triggered.connect(lambda: view.pulses_muted.emit([pulse.index], not pulse.muted))
            if len(view.selected_pulses) > 1 and pulse.index in view.selected_pulses:
                chosen = sorted(view.selected_pulses)
                every = menu.addAction(f"Delete the {len(chosen)} selected pulses (Del)")
                every.triggered.connect(lambda: view.pulses_deleted.emit(chosen))
                for muted, verb in ((True, "Mute"), (False, "Unmute")):
                    menu.addAction(f"{verb} the {len(chosen)} selected pulses").triggered.connect(
                        lambda _=False, m=muted: view.pulses_muted.emit(chosen, m)
                    )
            menu.exec(where)
            return True
        if left_button and hit is not None:
            pulse, mode = hit
            additive = bool(
                event.modifiers()
                & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)
            )
            view._pulse_additive = additive
            if additive:
                view.selected_pulses ^= {pulse.index}
            elif pulse.index not in view.selected_pulses:
                view.selected_pulses = {pulse.index}
            view.selected = set()
            if pulse.index in view.selected_pulses:
                order = view._power_positions()
                line_index = order.index(line.pos) if line.pos in order else 0
                view._pulse_drag = (pulse, mode, x, line_index)
                view._drag_offset = (0, 0)
            view.setFocus()
            view.update()
            return True
        if left_button and view.selected_pulses:
            view.selected_pulses = set()
            view.update()
        return False

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """A double click on an empty spot of a Powered line adds a pulse there."""
        view = cast("TimelineCanvas", self)
        x, y = event.position().x(), event.position().y()
        index = view._line_at(y)
        if index is not None and x >= view.LABEL_WIDTH:
            line = view.lines[index]
            power = line.kind == "block" and line.row == "power" and line.pos is not None
            if power and view._pulse_hit(line, x, view._tops[index]) is None:
                assert line.pos is not None
                view.pulse_added.emit(line.pos, max(1, view.tick_at(x)))
                return
        QWidget.mouseDoubleClickEvent(view, event)

    def _drop_target(self, category: str, y: float) -> tuple[int, int, float] | None:
        """Where a dragged line of ``category`` would go: (group, row, the marker's y)."""
        view = cast("TimelineCanvas", self)
        groups = view.groups.get(category, [])
        if not groups:
            return None
        rows = [
            (i, line)
            for i, line in enumerate(view.lines)
            if line.row == category and line.kind != "category"
        ]
        if not rows:
            return None
        for i, line in rows:
            top = view._tops[i]
            if y < top + view.EDIT_ROW_HEIGHT:
                below = y > top + view.EDIT_ROW_HEIGHT / 2
                if line.kind == "group" and line.group is not None:
                    return line.group, 0, top + view.EDIT_ROW_HEIGHT
                if line.group is not None and line.pos is not None:
                    members = groups[line.group].members
                    row = members.index(line.pos) + (1 if below else 0)
                    return line.group, row, top + (view.EDIT_ROW_HEIGHT if below else 0)
        last = len(groups) - 1
        bottom = view._tops[rows[-1][0]] + view.EDIT_ROW_HEIGHT
        return last, len(groups[last].members), bottom

    def _add_mute_actions(self, menu: QMenu, pulses: list[Pulse], what: str) -> None:
        """ "Mute …" / "Unmute …" entries for these pulses (bypassed, not deleted)."""
        view = cast("TimelineCanvas", self)
        indices = [p.index for p in pulses]
        if not indices:
            return
        menu.addSeparator()
        if any(not p.muted for p in pulses):
            menu.addAction(f"Mute {what}").triggered.connect(
                lambda: view.pulses_muted.emit(indices, True)
            )
        if any(p.muted for p in pulses):
            menu.addAction(f"Unmute {what}").triggered.connect(
                lambda: view.pulses_muted.emit(indices, False)
            )

    def _power_menu(self, where: QPoint) -> None:
        """The Powered category's menu: mute or unmute every pulse."""
        view = cast("TimelineCanvas", self)
        menu = QMenu(view)
        self._add_mute_actions(menu, view.pulses, "all pulses")
        if not menu.isEmpty():
            menu.exec(where)

    def _group_menu(self, where: QPoint, category: str, group: int) -> None:
        view = cast("TimelineCanvas", self)
        menu = QMenu(view)
        groups = view.groups.get(category, [])
        name = groups[group].name
        for text, action in (
            (f"Rename “{name}”…", "rename"),
            ("Color…", "color"),
            ("Move group up", "up"),
            ("Move group down", "down"),
            ("New group…", "new"),
            ("Delete group (its lines join the group above)", "delete"),
        ):
            item = menu.addAction(text)
            item.triggered.connect(
                lambda _=False, a=action: view.group_request.emit(a, category, group)
            )
        if category == "power":
            members = set(groups[group].members)
            self._add_mute_actions(
                menu, [p for p in view.pulses if p.pos in members], f"the group “{name}”"
            )
        menu.exec(where)

    def _line_menu(self, where: QPoint, category: str, pos: Pos) -> None:
        view = cast("TimelineCanvas", self)
        menu = QMenu(view)
        move = menu.addMenu("Move to group")
        groups = view.groups.get(category, [])
        for index, group in enumerate(groups):
            move.addAction(group.name).triggered.connect(
                lambda _=False, g=index: view.line_moved.emit(
                    category, pos, g, len(groups[g].members)
                )
            )
        menu.addAction("New group with this line…").triggered.connect(
            lambda: view.line_group_new.emit(category, pos)
        )
        if category == "power":
            self._add_mute_actions(menu, [p for p in view.pulses if p.pos == pos], "this line")
        menu.exec(where)

    def _hover_position(self, y: float) -> None:
        """Tell which block's line is under the cursor (the view lights it up)."""
        view = cast("TimelineCanvas", self)
        index = view._line_at(y)
        pos = view.lines[index].pos if index is not None else None
        if pos is None and y >= view._tracks_top():  # a monitor track
            row = int((y - view._tracks_top()) // view.ROW_HEIGHT)
            pos = view.tracks[row].pos if 0 <= row < len(view.tracks) else None
        if pos != view._hovered_pos:
            view._hovered_pos = pos
            view.position_hovered.emit(pos)


def _diamond(x: float, y: float, size: float) -> QPolygonF:
    return QPolygonF(
        [QPointF(x, y - size), QPointF(x + size, y), QPointF(x, y + size), QPointF(x - size, y)]
    )


@dataclass(frozen=True)
class EditEvent:
    """One recorded edit, for the per-block lines of a category."""

    index: int
    tick: int
    row: str
    pos: Pos
    label: str


@dataclass
class _Line:
    """A line of the edit area: a category, a group (Powered), or one block's events."""

    kind: str  # "category" | "group" | "block"
    row: str  # the category (EDIT_ROWS)
    title: str
    depth: int
    color: QColor
    group: int | None = None
    pos: Pos | None = None
    expandable: bool = False
    expanded: bool = False
    detail: str = ""  # shown dim after the title (a block line: what is there now)
