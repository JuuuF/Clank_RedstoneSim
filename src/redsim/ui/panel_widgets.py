"""Small widgets the panels share: exclusive value buttons that wrap, toggles, steppers, a
signal meter, a container's slot grid, hover watching, list placeholders."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QWidget,
)

from redsim.core.direction import Direction
from redsim.ui import pixel_icons, theme
from redsim.ui.icons import item_pixmap
from redsim.ui.names import item_name
from redsim.ui.style import wire_color
from redsim.world.properties import Property

NO_SELECTION = (
    f"<span style='color:{theme.TEXT_DIM}'>No block selected. Left-click a block in "
    "NORMAL mode (Esc) to inspect it.</span>"
)


#: Direction values: button text and pixel icon.
DIRECTION_LABELS = {
    "north": ("N", "north"),
    "east": ("E", "east"),
    "south": ("S", "south"),
    "west": ("W", "west"),
    "up": ("Up", "face_up"),
    "down": ("Down", "face_down"),
}


def _later(callback: Any) -> None:
    """Run after the current event: edits rebuild the panel, which may delete the button
    whose click is still being handled."""
    QTimer.singleShot(0, callback)


class FlowLayout(QLayout):
    """Widgets in rows that wrap at the available width (Qt's flow layout example), so
    long button lists (a note block's 23 instruments) never widen the panel."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 2) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802 - Qt's name
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem:  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None  # type: ignore[return-value]

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _arrange(self, rect: QRect, apply: bool) -> int:
        x, y, line = rect.x(), rect.y(), 0
        gap = self.spacing()
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line > 0:
                x, y, line = rect.x(), y + line + gap, 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + gap
            line = max(line, hint.height())
        return y + line - rect.y()


class _Choice(QWidget):
    """Exclusive buttons for a property's values (directions get arrows). More than six
    values wrap into rows that fit the panel."""

    def __init__(self, prop: Property, on_pick: Any) -> None:
        super().__init__()
        layout: QLayout
        if len(prop.values) > 6:
            layout = FlowLayout(self)
            policy = self.sizePolicy()
            policy.setHeightForWidth(True)
            policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
            self.setSizePolicy(policy)
        else:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
        self.buttons: dict[Any, QPushButton] = {}
        for value in prop.values:
            text = prop.serialize(value)
            label, icon = DIRECTION_LABELS.get(text, (text, None))
            button = QPushButton(label if isinstance(value, Direction) else text)
            if isinstance(value, Direction) and icon:
                button.setIcon(pixel_icons.pixel_icon(icon))
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
        self.setMaximumWidth(110)
        self.clicked.connect(lambda checked: on_pick(bool(checked)))
        self.setToolTip(f"Click to flip {prop.name}")

    def show_value(self, value: Any) -> None:
        self.setChecked(bool(value))
        self.setText("true" if value else "false")


class SignalMeter(QWidget):
    """A signal strength as 15 segments lit in the dust's color for that strength."""

    SEGMENT = 5

    def __init__(self) -> None:
        super().__init__()
        self.level = 0
        self.setFixedSize(15 * (self.SEGMENT + 1) + 1, 14)

    def set_level(self, level: int) -> None:
        self.level = max(0, min(15, level))
        self.setToolTip(f"Signal strength {self.level}")
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        red, green, blue, _ = wire_color(self.level)
        lit = QColor.fromRgbF(red, green, blue)
        for index in range(15):
            x = 1 + index * (self.SEGMENT + 1)
            color = lit if index < self.level else QColor(theme.SUNKEN)
            painter.fillRect(x, 2, self.SEGMENT, self.height() - 4, color)
        painter.end()


class _Stepper(QWidget):
    """An integer property: a value between back and next buttons; signal strengths
    (values up to 15) also get a ``SignalMeter``."""

    def __init__(self, values: tuple[Any, ...], on_pick: Any, tooltip: str) -> None:
        super().__init__()
        self.values = values
        self.value: Any = values[0]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.back = QPushButton()
        self.back.setIcon(pixel_icons.pixel_icon("less"))
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumWidth(36)
        self.next = QPushButton()
        self.next.setIcon(pixel_icons.pixel_icon("more"))
        for button in (self.back, self.next):
            button.setMaximumWidth(40)
            button.setToolTip(tooltip)
        self.back.clicked.connect(lambda: self._step(-1, on_pick))
        self.next.clicked.connect(lambda: self._step(1, on_pick))
        layout.addWidget(self.back)
        layout.addWidget(self.label)
        layout.addWidget(self.next)
        is_signal = all(isinstance(v, int) for v in values) and max(values) == 15
        self.meter = SignalMeter() if is_signal else None
        if self.meter is not None:
            layout.addSpacing(8)
            layout.addWidget(self.meter)
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
        if self.meter is not None and isinstance(value, int):
            self.meter.set_level(value)


#: Items the inspector offers for barrels and hoppers (max stack size in brackets).
CONTAINER_ITEMS = (
    ("minecraft:redstone", "Redstone dust (64)"),
    ("minecraft:stone", "Stone (64)"),
    ("minecraft:ender_pearl", "Ender pearl (16)"),
    ("minecraft:wooden_sword", "Wooden sword (1)"),
)


class ContainerGrid(QWidget):
    """A container's slots as the game draws them: rows of 9 slots with item icons and
    counts. Clicking a slot picks it for the slot editor below (``slot_clicked``, the
    slot number in the inspected block). For a double chest the grid shows all 54 slots;
    the other half's (``dimmed``) are greyed and cannot be picked."""

    slot_clicked = Signal(int)
    COLUMNS = 9

    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, int] | None] = []
        self.selected: int | None = None
        self.dimmed: frozenset[int] = frozenset()
        self.first = 0  # the grid index of the inspected block's slot 0
        self.other_name = ""  # where the dimmed slots are ("the other half at x y z")
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def slot_size(self) -> int:
        return max(24, min(36, (self.width() - 2) // self.COLUMNS))

    def set_items(
        self,
        items: Iterable[tuple[str, int] | None],
        dimmed: Iterable[int] = (),
        first: int = 0,
        other_name: str = "",
    ) -> None:
        self.items = list(items)
        self.dimmed, self.first, self.other_name = frozenset(dimmed), first, other_name
        if self.selected is not None and self.selected >= len(self.items):
            self.selected = None
        rows = max(1, -(-len(self.items) // self.COLUMNS))
        self.setFixedHeight(rows * self.slot_size() + 2)
        self.update()

    def resizeEvent(self, event: Any) -> None:
        self.set_items(self.items, self.dimmed, self.first, self.other_name)  # width → size
        super().resizeEvent(event)

    def _rect(self, slot: int) -> QRect:
        size = self.slot_size()
        row, column = divmod(slot, self.COLUMNS)
        return QRect(1 + column * size, 1 + row * size, size, size)

    def slot_at(self, point: QPoint) -> int | None:
        return next((i for i in range(len(self.items)) if self._rect(i).contains(point)), None)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        for slot, stack in enumerate(self.items):
            rect = self._rect(slot).adjusted(1, 1, -1, -1)
            dim = slot in self.dimmed
            painter.setOpacity(0.35 if dim else 1.0)
            theme.paint_slot(painter, rect)
            if stack is not None:
                item, count = stack
                icon = rect.width() - 8
                painter.drawPixmap(rect.left() + 4, rect.top() + 4, item_pixmap(item, icon))
                if count > 1:  # the game's stack count: bottom right, white, shadowed
                    text = str(count)
                    x = rect.right() - theme.text_width(text, 1) - 2
                    theme.draw_text(painter, x, rect.bottom() - 9, text, "#ffffff", 1)
            painter.setOpacity(1.0)
            if slot == self.selected:
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.end()

    def mouseMoveEvent(self, event: Any) -> None:
        slot = self.slot_at(event.position().toPoint())
        stack = self.items[slot] if slot is not None else None
        number = slot - self.first if slot is not None and slot not in self.dimmed else slot
        tip = (
            f"Slot {number}: empty"
            if stack is None
            else f"Slot {number}: {item_name(stack[0])} ×{stack[1]}"
        )
        if slot is not None and slot in self.dimmed:
            tip = f"{tip.replace(f'Slot {number}', 'Item', 1)} (in {self.other_name})"
        self.setToolTip(tip if slot is not None else "")

    def mousePressEvent(self, event: Any) -> None:
        slot = self.slot_at(event.position().toPoint())
        usable = slot is not None and slot not in self.dimmed
        if usable and event.button() == Qt.MouseButton.LeftButton:
            assert slot is not None
            self.selected = slot
            self.update()
            self.slot_clicked.emit(slot - self.first)


def _placeholder[T: (QTableWidgetItem, QListWidgetItem)](item: T) -> T:
    """``item`` as a dim, unselectable row that says a list is empty."""
    item.setFlags(Qt.ItemFlag.NoItemFlags)
    item.setForeground(QColor(theme.TEXT_DIM))
    return item


class HoverWatch(QObject):
    """Calls ``on_enter`` when the mouse enters a widget and ``on_leave`` when it leaves
    (panels light up the block whose coordinates are under the mouse); with ``on_move``,
    also on every mouse move (the point), e.g. to notice the empty space below a list."""

    def __init__(
        self,
        widget: QWidget,
        on_enter: Callable[[], object],
        on_leave: Callable[[], object],
        on_move: Callable[[QPoint], object] | None = None,
    ) -> None:
        super().__init__(widget)
        self.on_enter, self.on_leave, self.on_move = on_enter, on_leave, on_move
        if on_move is not None:
            widget.setMouseTracking(True)
        widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Enter:
            self.on_enter()
        elif event.type() == QEvent.Type.Leave:
            self.on_leave()
        elif event.type() == QEvent.Type.MouseMove and self.on_move is not None:
            self.on_move(event.position().toPoint())  # type: ignore[attr-defined]
        return False


def _swatch(color: str, size: int = 14) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(theme.BORDER))
    painter = QPainter(pixmap)
    painter.fillRect(1, 1, size - 2, size - 2, QColor(color))
    painter.end()
    return QIcon(pixmap)
