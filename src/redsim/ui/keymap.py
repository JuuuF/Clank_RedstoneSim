"""Rebindable input bindings (pure Python, no Qt).

Every keyboard shortcut, held camera key and mouse gesture of the editor is an *action* with
default bindings. A user keymap file (JSON) replaces the bindings of the actions it names:

.. code-block:: json

    {"version": 1, "bindings": {"sim.run": ["Space"], "camera.orbit": ["Right Drag"]}}

An empty list unbinds an action. Binding strings:

* keys: Qt key sequence text, e.g. ``"Ctrl+Z"``, ``"Shift+Right"``, ``"Space"``, ``"B"``;
* mouse: optional modifiers, then ``"<Left|Right|Middle> <Click|Drag>"`` or ``"Wheel"``,
  e.g. ``"Shift+Middle Drag"``, ``"Ctrl+Wheel"``.

Mouse actions whose id starts with a mode name (``normal.``, ``build.``, ``select.``) only
apply in that mode and win over mode-independent ones (``camera.``, ``pick``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

KEY, HOLD, MOUSE = "key", "hold", "mouse"
MODES = ("normal", "build", "select")
MODIFIERS = ("Ctrl", "Shift", "Alt", "Meta")
BUTTONS = ("Left", "Right", "Middle")
GESTURES = ("Click", "Drag")
KEYMAP_VERSION = 1


@dataclass(frozen=True)
class ActionSpec:
    id: str
    title: str
    defaults: tuple[str, ...]
    kind: str = KEY


def _hotbar(slot: int) -> ActionSpec:
    return ActionSpec(f"hotbar.{slot}", f"Hotbar slot {slot}", (str(slot),))


ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec("mode.normal", "Normal mode: inspect, use, run (again: clear selection)", ("Esc",)),
    ActionSpec("mode.build", "Build mode: place and break blocks", ("B",)),
    ActionSpec("mode.select", "Select mode: boxes, copy, paste", ("V",)),
    ActionSpec("camera.orbit", "Orbit around the pivot", ("Middle Drag", "Alt+Left Drag"), MOUSE),
    ActionSpec(
        "camera.pan",
        "Move the pivot horizontally",
        ("Shift+Middle Drag", "Shift+Alt+Left Drag"),
        MOUSE,
    ),
    ActionSpec("camera.zoom", "Zoom (distance to the pivot)", ("Wheel",), MOUSE),
    ActionSpec("camera.vertical", "Move the pivot up or down", ("Ctrl+Wheel",), MOUSE),
    ActionSpec("camera.forward", "Move the pivot forward", ("W",), HOLD),
    ActionSpec("camera.back", "Move the pivot back", ("S",), HOLD),
    ActionSpec("camera.left", "Move the pivot left", ("A",), HOLD),
    ActionSpec("camera.right", "Move the pivot right", ("D",), HOLD),
    ActionSpec("camera.up", "Move the pivot up", ("PgUp",), HOLD),
    ActionSpec("camera.down", "Move the pivot down", ("PgDown",), HOLD),
    ActionSpec("camera.focus", "Move the pivot to the block under the cursor", ("F",)),
    ActionSpec("pick", "Pick the block type under the cursor", ("Middle Click",), MOUSE),
    ActionSpec("normal.inspect", "Select a block for the inspector", ("Left Click",), MOUSE),
    ActionSpec("normal.use", "Use a lever, button, repeater, …", ("Right Click",), MOUSE),
    ActionSpec("build.break", "Break the block", ("Left Click",), MOUSE),
    ActionSpec("build.place", "Place the palette block", ("Right Click",), MOUSE),
    ActionSpec("build.use", "Use instead of placing", ("Ctrl+Right Click",), MOUSE),
    ActionSpec("select.block", "Select one block", ("Left Click",), MOUSE),
    ActionSpec(
        "select.box",
        "Drag a box; from a face handle: resize; from inside the box: move it",
        ("Left Drag",),
        MOUSE,
    ),
    ActionSpec(
        "select.copy_drag", "Drag a copy of the box (from inside it)", ("Ctrl+Left Drag",), MOUSE
    ),
    ActionSpec("select.extend", "Extend the box to the block", ("Shift+Left Click",), MOUSE),
    ActionSpec("sim.run", "Run / pause", ("Space", "P")),
    ActionSpec("sim.tick", "Step one tick", ("Right", "T")),
    ActionSpec("sim.event", "Step one event (engine step)", ("Shift+Right", "E")),
    ActionSpec("sim.tick_back", "Tick back", ("Left",)),
    ActionSpec("sim.step_back", "Step back (one engine step)", ("Shift+Left",)),
    ActionSpec("edit.undo", "Undo", ("Ctrl+Z",)),
    ActionSpec("edit.redo", "Redo", ("Ctrl+Y", "Ctrl+Shift+Z")),
    ActionSpec("edit.copy", "Copy the selection", ("Ctrl+C",)),
    ActionSpec("edit.paste", "Paste at the block under the cursor", ("Ctrl+V",)),
    ActionSpec("edit.rotate", "Rotate the clipboard 90°", ("R",)),
    ActionSpec("edit.rotate_block", "Rotate the block under the cursor clockwise", ("Q",)),
    ActionSpec(
        "edit.rotate_block_back",
        "Rotate the block under the cursor counter-clockwise",
        ("Shift+Q",),
    ),
    ActionSpec("edit.delete", "Clear the selection (fill with air)", ("Del",)),
    ActionSpec("file.new", "New world", ("Ctrl+N",)),
    ActionSpec("file.open", "Open…", ("Ctrl+O",)),
    ActionSpec("file.save", "Save", ("Ctrl+S",)),
    ActionSpec("file.save_as", "Save as…", ("Ctrl+Shift+S",)),
    ActionSpec("file.quit", "Quit", ("Ctrl+Q",)),
    ActionSpec("help.controls", "Show the controls", ("F1",)),
    *(_hotbar(slot) for slot in range(1, 10)),
)
SPECS: dict[str, ActionSpec] = {spec.id: spec for spec in ACTIONS}

#: Section titles of the controls help, by action id prefix.
CATEGORIES = {
    "mode": "Modes",
    "camera": "Camera",
    "pick": "Any mode",
    "normal": "Normal mode",
    "build": "Build mode",
    "select": "Select mode",
    "sim": "Simulation",
    "edit": "Editing",
    "file": "File",
    "help": "Help",
    "hotbar": "Hotbar",
}


@dataclass(frozen=True)
class MouseBinding:
    modifiers: frozenset[str]
    button: str | None  # None for the wheel
    gesture: str  # "Click", "Drag" or "Wheel"


def parse_mouse(text: str) -> MouseBinding:
    """Parse ``"Shift+Middle Drag"`` or ``"Ctrl+Wheel"``; raises ``ValueError`` if invalid."""
    *mods, last = [part.strip() for part in text.split("+")]
    modifiers = set()
    for mod in mods:
        canonical = mod.capitalize()
        if canonical == "Control":
            canonical = "Ctrl"
        if canonical not in MODIFIERS:
            raise ValueError(f"unknown modifier {mod!r} in {text!r}")
        modifiers.add(canonical)
    words = last.split()
    if [w.capitalize() for w in words] == ["Wheel"]:
        return MouseBinding(frozenset(modifiers), None, "Wheel")
    if len(words) != 2:
        raise ValueError(f"expected '<Left|Right|Middle> <Click|Drag>' or 'Wheel' in {text!r}")
    button, gesture = (w.capitalize() for w in words)
    if button not in BUTTONS or gesture not in GESTURES:
        raise ValueError(f"expected '<Left|Right|Middle> <Click|Drag>' or 'Wheel' in {text!r}")
    return MouseBinding(frozenset(modifiers), button, gesture)


def normalize_key(text: str) -> str:
    """Canonical form for comparing key bindings (modifier order and letter case)."""
    *mods, key = [part.strip() for part in text.split("+")]
    order = {name: index for index, name in enumerate(MODIFIERS)}
    canonical = sorted(
        {"Ctrl" if m.capitalize() == "Control" else m.capitalize() for m in mods},
        key=lambda m: order.get(m, 99),
    )
    return "+".join([*canonical, key.upper()])


def default_path() -> Path:
    """``$REDSIM_KEYMAP``, else ``$XDG_CONFIG_HOME/redsim/keymap.json`` (``~/.config``)."""
    override = os.environ.get("REDSIM_KEYMAP")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "redsim" / "keymap.json"


class Keymap:
    def __init__(self, overrides: dict[str, list[str]] | None = None) -> None:
        self.warnings: list[str] = []
        self._bindings: dict[str, tuple[str, ...]] = {s.id: s.defaults for s in ACTIONS}
        for action, bindings in (overrides or {}).items():
            spec = SPECS.get(action)
            if spec is None:
                self.warnings.append(f"unknown action {action!r} (ignored)")
                continue
            if not isinstance(bindings, list) or not all(isinstance(b, str) for b in bindings):
                self.warnings.append(f"{action}: bindings must be a list of strings (ignored)")
                continue
            if spec.kind == MOUSE:
                valid = []
                for binding in bindings:
                    try:
                        parse_mouse(binding)
                        valid.append(binding)
                    except ValueError as exc:
                        self.warnings.append(f"{action}: {exc}")
                bindings = valid
            self._bindings[action] = tuple(bindings)
        self.warnings.extend(self.conflicts())
        self._mouse: list[tuple[str, MouseBinding]] = [
            (action, parse_mouse(binding))
            for action, bindings in self._bindings.items()
            if SPECS[action].kind == MOUSE
            for binding in bindings
        ]

    # ------------------------------------------------------------------ files
    @staticmethod
    def load(path: Path | None = None) -> Keymap:
        """The defaults, overridden by the keymap file if it exists."""
        path = path if path is not None else default_path()
        if not path.exists():
            return Keymap()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            overrides = data.get("bindings", {})
            if not isinstance(overrides, dict):
                raise ValueError("'bindings' must be an object")
        except (OSError, ValueError, AttributeError) as exc:
            keymap = Keymap()
            keymap.warnings.insert(0, f"cannot read {path}: {exc}")
            return keymap
        return Keymap(overrides)

    @staticmethod
    def write_defaults(path: Path) -> None:
        """Write every action with its default bindings, as a template to edit."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": KEYMAP_VERSION,
            "help": "Each action maps to a list of bindings; [] unbinds. Keys use Qt key "
            "sequence text (Ctrl+Z, Shift+Right, Space); mouse bindings are "
            "'[Mods+]<Left|Right|Middle> <Click|Drag>' or '[Mods+]Wheel'. "
            "Remove actions you do not change.",
            "bindings": {spec.id: list(spec.defaults) for spec in ACTIONS},
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------ queries
    def bindings(self, action: str) -> tuple[str, ...]:
        return self._bindings[action]

    def actions(self, kind: str) -> list[str]:
        return [action for action in self._bindings if SPECS[action].kind == kind]

    def mouse_action(
        self, mode: str, modifiers: frozenset[str], button: str | None, gesture: str
    ) -> str | None:
        """The action for a mouse gesture in ``mode`` (mode-specific bindings win)."""
        fallback = None
        for action, binding in self._mouse:
            if (binding.modifiers, binding.button, binding.gesture) != (
                modifiers,
                button,
                gesture,
            ):
                continue
            prefix = action.split(".")[0]
            if prefix == mode:
                return action
            if prefix not in MODES and fallback is None:
                fallback = action
        return fallback

    def describe(self, action: str) -> str:
        bindings = self._bindings[action]
        return " / ".join(bindings) if bindings else "(unbound)"

    def conflicts(self) -> list[str]:
        """Bindings used twice in the same context (both would fire, or neither)."""
        seen: dict[tuple[str, str], str] = {}
        problems = []
        for action, bindings in self._bindings.items():
            spec = SPECS[action]
            prefix = action.split(".")[0]
            for binding in bindings:
                if spec.kind == MOUSE:
                    context = prefix if prefix in MODES else "any"
                    try:
                        key = repr(parse_mouse(binding))
                    except ValueError:
                        continue
                else:
                    context, key = "keyboard", normalize_key(binding)
                other = seen.get((context, key))
                if other is not None and other != action:
                    problems.append(f"{binding!r} is bound to both {other} and {action}")
                seen[(context, key)] = action
        return problems
