"""The Hotkeys tab, the Preferences dialog and Help → About."""

from __future__ import annotations

import html
import importlib.metadata

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from redsim.ui import theme
from redsim.ui.hints import keycaps_html
from redsim.ui.keymap import Keymap, hotkey_sections
from redsim.ui.preferences import MAX_VIEW_DISTANCE, Preferences

#: Section header colors: the current mode's section in its mode color, others neutral.
MODE_TINTS = {"normal": "#2b4f80", "build": "#2c6a34", "select": "#8a5418", "animate": "#7a2832"}


def keycaps(bindings: tuple[str, ...]) -> str:
    """Rich text with each key drawn as a keycap; alternatives separated by "or"."""
    if not bindings:
        return "<i>unbound</i>"
    return " or ".join(keycaps_html(binding) for binding in bindings)


class HotkeysPanel(QWidget):
    """Every binding of the active keymap, grouped by what you are doing, searchable; the
    section of the current mode is highlighted. Generated from ``redsim.ui.keymap``."""

    def __init__(self, keymap: Keymap) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter, e.g. rotate, paste or Ctrl")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _text: self._render())
        layout.addWidget(self.search)
        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        layout.addWidget(self.view)
        self._mode = "normal"
        self._sections: list[tuple[str, str | None, list[tuple[str, tuple[str, ...]]]]] = []
        self.set_keymap(keymap)

    def set_keymap(self, keymap: Keymap) -> None:
        self._sections = hotkey_sections(keymap)
        self._render()

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._render()

    def visible_rows(self) -> list[tuple[str, str]]:
        """(section, action) pairs that pass the filter."""
        needle = self.search.text().strip().lower()
        rows = []
        for title, _, entries in self._sections:
            for action, bindings in entries:
                haystack = f"{title} {action} {' '.join(bindings)}".lower()
                if not needle or needle in haystack:
                    rows.append((title, action))
        return rows

    def _render(self) -> None:
        shown = set(self.visible_rows())
        mode = self._mode
        parts = [
            f"<p>You are in <b>{mode.upper()}</b> mode (Esc / B / V / K switch, or hold Tab "
            "for the mode ring); its section is "
            "highlighted.</p>"
        ]
        for title, section_mode, entries in self._sections:
            rows = [(a, b) for a, b in entries if (title, a) in shown]
            if not rows:
                continue
            tint = MODE_TINTS.get(mode) if section_mode == mode else theme.WIDGET
            parts.append('<table width="100%" cellspacing="0" cellpadding="3">')
            parts.append(
                f'<tr><td style="background-color:{tint};"><b>{html.escape(title)}</b></td></tr>'
            )
            for action, bindings in rows:  # stacked, so it reads well in a narrow panel
                parts.append(
                    f"<tr><td>{html.escape(action)}<br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{keycaps(bindings)}</td></tr>"
                )
            parts.append("</table><br>")
        parts.append(
            "<p><small>Rebind anything: Settings → Edit keymap file, then Reload keymap."
            "</small></p>"
        )
        self.view.setHtml("".join(parts))


PREFERENCES_WIDTH = 480


class PreferencesDialog(QDialog):
    """Preferences; changes apply live (``changed``, ``look_changed``) and are saved on
    close."""

    changed = Signal()
    look_changed = Signal(str, bool)  # preference name, on

    def __init__(
        self,
        preferences: Preferences,
        parent: QWidget | None = None,
        textures_available: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setFixedWidth(PREFERENCES_WIDTH)  # sliders stay usable without resizing
        self.preferences = preferences
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)
        group = QGroupBox("X-ray transparency")
        form = QFormLayout(group)
        form.setContentsMargins(10, 14, 10, 10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        explanation = QLabel(
            f"<small style='color:{theme.TEXT_DIM}'>How opaque blocks stay when X-ray is on "
            "(Alt+Z): building blocks in both levels, circuit blocks in the second.</small>"
        )
        explanation.setWordWrap(True)
        form.addRow(explanation)
        self.sliders: dict[str, QSlider] = {}
        for attribute, text, tip in (
            (
                "xray_building_alpha",
                "Building blocks",
                "How visible building blocks (stone, planks, …) stay in both X-ray levels.",
            ),
            (
                "xray_circuit_alpha",
                "Circuit blocks",
                "How visible circuit parts stay in the 'everything' X-ray level.",
            ),
        ):
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(round(getattr(preferences, attribute) * 100))
            slider.setToolTip(tip)
            slider.setMinimumWidth(220)
            value = QLabel(f"{slider.value()} %")
            value.setFixedWidth(44)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            slider.valueChanged.connect(lambda v, a=attribute, label=value: self._set(a, v, label))
            row = QHBoxLayout()
            row.addWidget(slider)
            row.addWidget(value)
            form.addRow(text, row)
            self.sliders[attribute] = slider
        layout.addWidget(group)
        looks = QGroupBox("Looks")
        looks_layout = QVBoxLayout(looks)
        looks_layout.setContentsMargins(10, 14, 10, 10)
        self.looks: dict[str, QCheckBox] = {}
        for attribute, text, tip in (
            (
                "game_textures",
                "Game textures",
                "The game's own models and textures from the supplied client jar",
            ),
            ("scenery", "Scenery", "A grass superflat around the floor and the game's clouds"),
        ):
            box = QCheckBox(text)
            box.setToolTip(tip)
            box.setChecked(getattr(preferences, attribute))
            box.toggled.connect(lambda on, a=attribute: self.look_changed.emit(a, on))
            looks_layout.addWidget(box)
            self.looks[attribute] = box
        self.looks["game_textures"].setEnabled(textures_available)
        layout.addWidget(looks)
        trackpad = QGroupBox("Trackpad")
        trackpad_layout = QVBoxLayout(trackpad)
        trackpad_layout.setContentsMargins(10, 14, 10, 10)
        box = QCheckBox("Two-finger scrolling navigates (like Blender on a Mac)")
        box.setToolTip(
            "Scroll: orbit · Shift: pan · Ctrl/⌘: zoom · Alt/⌥: up and down. "
            "Off: scrolling acts as a mouse wheel. Pinching always zooms."
        )
        box.setChecked(preferences.trackpad_navigation)
        box.toggled.connect(lambda on: self.look_changed.emit("trackpad_navigation", on))
        trackpad_layout.addWidget(box)
        self.looks["trackpad_navigation"] = box
        layout.addWidget(trackpad)
        worlds = QGroupBox("Minecraft worlds")
        worlds_form = QFormLayout(worlds)
        worlds_form.setContentsMargins(10, 14, 10, 10)
        self.view_distance = QSpinBox()
        self.view_distance.setRange(2, MAX_VIEW_DISTANCE)
        self.view_distance.setSuffix(" chunks")
        self.view_distance.setValue(preferences.world_view_distance)
        self.view_distance.setToolTip(
            "Chunks of an opened world load around the camera up to this far, like the "
            "game's render distance. Farther means more blocks to simulate and draw."
        )
        self.view_distance.valueChanged.connect(self._set_view_distance)
        worlds_form.addRow("View distance", self.view_distance)
        layout.addWidget(worlds)
        buttons = QHBoxLayout()
        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(self._reset)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def _reset(self) -> None:
        defaults = Preferences()
        for attribute, slider in self.sliders.items():
            slider.setValue(round(getattr(defaults, attribute) * 100))
        for attribute, box in self.looks.items():
            if box.isEnabled():
                box.setChecked(getattr(defaults, attribute))
        self.view_distance.setValue(defaults.world_view_distance)

    def _set_view_distance(self, value: int) -> None:
        self.preferences.world_view_distance = value
        self.changed.emit()

    def _set(self, attribute: str, value: int, label: QLabel) -> None:
        setattr(self.preferences, attribute, value / 100)
        label.setText(f"{value} %")
        self.changed.emit()


class AboutDialog(QDialog):
    """Help → About: the title in the game's font, what the simulator follows, and where
    its looks come from."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Redstone Simulator")
        self.setFixedWidth(PREFERENCES_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(10)
        title = QLabel()
        font = theme.PixelFont.load()
        if font is not None:
            title.setPixmap(font.pixmap("Redstone Simulator", theme.GOLD, 3))
        else:
            title.setText("<b>Redstone Simulator</b>")
        layout.addWidget(title)
        try:
            version = importlib.metadata.version("redsim")
        except importlib.metadata.PackageNotFoundError:
            version = "development"
        text = QLabel(
            f"<p>Version {html.escape(version)} · Minecraft Java Edition 26.3 rules, "
            "ported from the game's server code and checked tick by tick against a "
            "real 26.3 server.</p>"
            f"<p style='color:{theme.TEXT_DIM}'>Block models, textures, names, the font "
            "and the clouds are read at runtime from your own client jar and are never "
            "shipped. Without the jar, simple colored models are drawn.</p>"
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        close = QPushButton("Close")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)
