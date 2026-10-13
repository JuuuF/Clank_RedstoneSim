"""Constants shared by the timeline's modules (colors, row titles, glide timing)."""

from __future__ import annotations

from PySide6.QtGui import (
    QColor,
)

from redsim.ui import theme

#: While playing, the playhead may glide this many seconds of ticks past the last known one
#: (the panels are refreshed a few times a second).
GLIDE_LOOKAHEAD = 0.15


#: Icon-only transport buttons: less side padding than text buttons.
COMPACT = "QToolButton { padding: 3px 4px; }"


BACKGROUND = QColor(theme.PANEL)


RECORDED = QColor(theme.WIDGET)


GRID = QColor(theme.LINE)


TEXT = QColor(theme.TEXT)


TEXT_DIM = QColor(theme.TEXT_DIM)


RULER = QColor(theme.SUNKEN)


ROW_COLORS = {
    "build": QColor(110, 200, 95),
    "remove": QColor(235, 85, 70),
    "edit": QColor(95, 150, 255),
    "interact": QColor(240, 196, 60),
    "power": QColor(255, 70, 70),
}


ROW_TITLES = {
    "build": "Placed",
    "remove": "Removed",
    "edit": "Changed",
    "interact": "Used",
    "power": "Powered",
}


PLAYHEAD = QColor(theme.ACCENT)


SIGNAL = QColor(theme.ACCENT)
