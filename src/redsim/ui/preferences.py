"""User preferences (pure Python, no Qt), stored as JSON next to the keymap.

``$REDSIM_CONFIG_DIR`` overrides the folder (tests use it), else
``$XDG_CONFIG_HOME/redsim`` or ``~/.config/redsim``.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


def config_dir() -> Path:
    override = os.environ.get("REDSIM_CONFIG_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "redsim"


@dataclass
class Preferences:
    #: X-ray: alpha of building blocks (both X-ray levels) and of circuit blocks (level 2).
    xray_building_alpha: float = 0.30
    xray_circuit_alpha: float = 0.50
    #: Draw blocks with the game's models and textures (when the client jar is there).
    game_textures: bool = True
    #: The ground around the floor and the clouds (View → Scenery).
    scenery: bool = True

    @staticmethod
    def path() -> Path:
        return config_dir() / "preferences.json"

    @staticmethod
    def load() -> Preferences:
        prefs = Preferences()
        try:
            data = json.loads(Preferences.path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return prefs
        for field in fields(prefs):
            value = data.get(field.name) if isinstance(data, dict) else None
            if isinstance(getattr(prefs, field.name), bool):
                if isinstance(value, bool):
                    setattr(prefs, field.name, value)
            elif isinstance(value, int | float) and not isinstance(value, bool):
                setattr(prefs, field.name, min(1.0, max(0.0, float(value))))
        return prefs

    def save(self) -> None:
        path = Preferences.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")


def window_layout_path() -> Path:
    return config_dir() / "window.json"


def load_window_layout() -> dict[str, str]:
    """The main window's saved geometry and dock layout (base64 strings), or ``{}``."""
    try:
        data = json.loads(window_layout_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}


def save_window_layout(layout: dict[str, str]) -> None:
    """Best effort: a read-only config folder only loses the layout."""
    path = window_layout_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
