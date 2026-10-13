"""The side panels and dialogs, one module each (``panel_inspector``, ``panel_diagnostics``,
``panel_circuit``, ``panel_settings``; shared widgets in ``panel_widgets``). This module
keeps the old import paths working."""

from __future__ import annotations

from redsim.ui.panel_circuit import ContraptionsPanel, SectionsPanel
from redsim.ui.panel_diagnostics import _POSITION, DiagnosticsPanel, first_position
from redsim.ui.panel_inspector import InspectorPanel
from redsim.ui.panel_settings import (
    MODE_TINTS,
    PREFERENCES_WIDTH,
    AboutDialog,
    HotkeysPanel,
    PreferencesDialog,
    keycaps,
)
from redsim.ui.panel_widgets import (
    CONTAINER_ITEMS,
    DIRECTION_LABELS,
    NO_SELECTION,
    ContainerGrid,
    FlowLayout,
    HoverWatch,
    SignalMeter,
    _Choice,
    _later,
    _placeholder,
    _Stepper,
    _swatch,
    _Toggle,
)

__all__ = [
    "AboutDialog",
    "CONTAINER_ITEMS",
    "ContainerGrid",
    "ContraptionsPanel",
    "DIRECTION_LABELS",
    "DiagnosticsPanel",
    "FlowLayout",
    "HotkeysPanel",
    "HoverWatch",
    "InspectorPanel",
    "MODE_TINTS",
    "NO_SELECTION",
    "PREFERENCES_WIDTH",
    "PreferencesDialog",
    "SectionsPanel",
    "SignalMeter",
    "_Choice",
    "_POSITION",
    "_Stepper",
    "_Toggle",
    "_later",
    "_placeholder",
    "_swatch",
    "first_position",
    "keycaps",
]
