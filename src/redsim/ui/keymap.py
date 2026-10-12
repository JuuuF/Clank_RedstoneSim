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
MODES = ("normal", "build", "select", "paste")  # "paste": while a paste preview is shown
MODIFIERS = ("Ctrl", "Shift", "Alt", "Meta")
BUTTONS = ("Left", "Right", "Middle")
GESTURES = ("Click", "Drag")
KEYMAP_VERSION = 3

#: Actions older versions had (keymap files written then may still list them).
RETIRED_ACTIONS = frozenset(f"hotbar.{slot}" for slot in range(1, 10))

#: Earlier default bindings. A keymap file entry equal to one of them was not changed by
#: the user (older versions wrote every default into the file), so the current default
#: applies instead.
LEGACY_DEFAULTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "camera.zoom": (("Ctrl+Wheel",),),
    "camera.vertical": (("Ctrl+Wheel",), ("Wheel",)),
    "paste.layer": (("Wheel",),),
    "paste.zoom": (("Ctrl+Wheel",),),
    "build.layer": (("Wheel",),),
    "build.zoom": (("Ctrl+Wheel",),),
    "sim.event": (("Shift+Right", "E"),),
    "sim.step_back": (("Shift+Left",),),
    "build.break": (("Left Click",), ()),
    "build.place": (("Right Click",),),
    "build.rotate": (("Right Click",),),
    "build.rotate_back": (("Shift+Right Click",),),
    "inventory.up": (("Backspace",),),
}


@dataclass(frozen=True)
class ActionSpec:
    id: str
    title: str
    defaults: tuple[str, ...]
    kind: str = KEY


def _recent(slot: int) -> ActionSpec:
    return ActionSpec(f"recent.{slot}", f"Pick recent block {slot}", (f"Alt+{slot}",))


def _inventory(slot: int) -> ActionSpec:
    title = f"Inventory: open folder / pick block {slot}"
    return ActionSpec(f"inventory.{slot}", title, (str(slot),))


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
    ActionSpec("camera.vertical", "Move the camera (pivot) up or down", ("Shift+Wheel",), MOUSE),
    ActionSpec("camera.forward", "Move the pivot forward", ("W",), HOLD),
    ActionSpec("camera.back", "Move the pivot back", ("S",), HOLD),
    ActionSpec("camera.left", "Move the pivot left", ("A",), HOLD),
    ActionSpec("camera.right", "Move the pivot right", ("D",), HOLD),
    ActionSpec("camera.up", "Move the pivot up", ("PgUp",), HOLD),
    ActionSpec("camera.down", "Move the pivot down", ("PgDown",), HOLD),
    ActionSpec("camera.focus", "Move the pivot to the block under the cursor", ("F",)),
    ActionSpec("pick", "Pick the block type under the cursor", ("Middle Click",), MOUSE),
    ActionSpec(
        "paste.layer", "While pasting: move the paste layer up/down", ("Shift+Wheel",), MOUSE
    ),
    ActionSpec("paste.zoom", "While pasting: zoom", ("Wheel",), MOUSE),
    ActionSpec("build.layer", "BUILD: move the build layer up/down", ("Shift+Wheel",), MOUSE),
    ActionSpec("build.zoom", "BUILD: zoom", ("Wheel",), MOUSE),
    ActionSpec("normal.inspect", "Select a block for the inspector", ("Left Click",), MOUSE),
    ActionSpec("normal.use", "Use a lever, button, repeater, …", ("Right Click",), MOUSE),
    ActionSpec("build.place", "Place the chosen block", ("Left Click",), MOUSE),
    ActionSpec("build.line", "Drag a straight line of the chosen block", ("Left Drag",), MOUSE),
    ActionSpec("build.rotate", "Turn the block under the cursor (Q does too)", (), MOUSE),
    ActionSpec("build.rotate_back", "Turn the block under the cursor back", (), MOUSE),
    ActionSpec("build.break", "Remove the block under the cursor", ("Right Click",), MOUSE),
    ActionSpec("build.use", "Use the block (lever, button, …)", ("Ctrl+Right Click",), MOUSE),
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
    ActionSpec(
        "select.stack", "Stack copies: drag a face handle outwards", ("Shift+Left Drag",), MOUSE
    ),
    ActionSpec("select.lock", "Lock / unlock the selection (Enter, like GIMP)", ("Return",)),
    ActionSpec("select.extend", "Extend the box to the block", ("Shift+Left Click",), MOUSE),
    ActionSpec("sim.run", "Run / pause", ("Space", "P")),
    ActionSpec("sim.run_back", "Play backwards / pause", ("Ctrl+Shift+Space",)),
    ActionSpec(
        "sim.set_zero", "Set tick 0 here (the current state becomes the build)", ("Ctrl+0",)
    ),
    ActionSpec("sim.tick", "Step one tick", ("Right", "T")),
    ActionSpec("sim.event", "Step one event (engine step)", ("Ctrl+Right", "E")),
    ActionSpec("sim.tick_back", "Tick back", ("Left",)),
    ActionSpec("sim.step_back", "Step back (one engine step)", ("Ctrl+Left",)),
    ActionSpec("sim.start", "Jump to the start of the recorded history", ("Shift+Left",)),
    ActionSpec("sim.end", "Jump to the end of the recorded history", ("Shift+Right",)),
    ActionSpec("sim.prev_edit", "Jump to the previous edit", ("Down",)),
    ActionSpec("sim.next_edit", "Jump to the next edit", ("Up",)),
    ActionSpec("sim.marker", "Add a named marker at the current tick", ("Ctrl+M",)),
    ActionSpec("edit.undo", "Undo", ("Ctrl+Z",)),
    ActionSpec("edit.redo", "Redo", ("Ctrl+Y", "Ctrl+Shift+Z")),
    ActionSpec("edit.copy", "Copy the selection", ("Ctrl+C",)),
    ActionSpec("edit.paste", "Paste at the block under the cursor", ("Ctrl+V",)),
    ActionSpec("edit.rotate", "Rotate the selection (or paste preview) 90° clockwise", ("R",)),
    ActionSpec("edit.rotate_back", "Rotate the selection 90° counter-clockwise", ("Shift+R",)),
    ActionSpec("edit.flip", "Flip the selection left/right (as seen from the camera)", ("H",)),
    ActionSpec("edit.flip_depth", "Flip the selection front/back", ("Shift+H",)),
    ActionSpec("search.blocks", "Search blocks to build with", ("Ctrl+Space", "/")),
    ActionSpec("edit.rotate_block", "Rotate the block under the cursor clockwise", ("Q",)),
    ActionSpec(
        "edit.rotate_block_back",
        "Rotate the block under the cursor counter-clockwise",
        ("Shift+Q",),
    ),
    ActionSpec(
        "edit.delete",
        "Delete the selection (fill it with air); right click removes single blocks",
        ("Del",),
    ),
    ActionSpec("file.new", "New world", ("Ctrl+N",)),
    ActionSpec("file.open", "Open…", ("Ctrl+O",)),
    ActionSpec("file.save", "Save", ("Ctrl+S",)),
    ActionSpec("file.save_as", "Save as…", ("Ctrl+Shift+S",)),
    ActionSpec("file.quit", "Quit", ("Ctrl+Q",)),
    ActionSpec("view.info", "Debug screen: world, targeted block, signal values", ("F3",)),
    ActionSpec(
        "view.xray", "X-ray: cycle off / building blocks / everything see-through", ("Alt+Z",)
    ),
    ActionSpec("help.controls", "Show the controls", ("F1",)),
    *(_inventory(slot) for slot in range(1, 10)),
    *(_recent(slot) for slot in range(1, 10)),
    # ^ is the key left of 1 on German layouts (` on US ones); its dead-key form is
    # translated by the main window.
    ActionSpec("inventory.up", "Inventory: back to the parent folder (the row below)", ("^", "`")),
)
SPECS: dict[str, ActionSpec] = {spec.id: spec for spec in ACTIONS}


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
        self._overridden: set[str] = set()
        self._bindings: dict[str, tuple[str, ...]] = {s.id: s.defaults for s in ACTIONS}
        for action, bindings in (overrides or {}).items():
            spec = SPECS.get(action)
            if spec is None:
                if action not in RETIRED_ACTIONS:  # actions of older versions: silently
                    self.warnings.append(f"unknown action {action!r} (ignored)")
                continue
            if not isinstance(bindings, list) or not all(isinstance(b, str) for b in bindings):
                self.warnings.append(f"{action}: bindings must be a list of strings (ignored)")
                continue
            if tuple(bindings) in LEGACY_DEFAULTS.get(action, ()):
                continue  # an old default, not a user choice
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
            self._overridden.add(action)
        self._drop_shadowed_defaults()
        self.warnings.extend(self.conflicts())
        self._mouse: list[tuple[str, MouseBinding]] = [
            (action, parse_mouse(binding))
            for action, bindings in self._bindings.items()
            if SPECS[action].kind == MOUSE
            for binding in bindings
        ]

    def _drop_shadowed_defaults(self) -> None:
        """A key the user bound to an action is taken away from another action that only
        has it by default (otherwise Qt fires neither: an ambiguous shortcut)."""
        claimed = {
            normalize_key(binding)
            for action in self._overridden
            if SPECS[action].kind != MOUSE
            for binding in self._bindings[action]
        }
        for action, bindings in self._bindings.items():
            if action in self._overridden or SPECS[action].kind == MOUSE:
                continue
            kept = tuple(b for b in bindings if normalize_key(b) not in claimed)
            if kept != bindings:
                self._bindings[action] = kept
                for binding in sorted(set(bindings) - set(kept)):
                    owner = next(
                        a
                        for a in self._overridden
                        if SPECS[a].kind != MOUSE
                        and normalize_key(binding) in {normalize_key(b) for b in self._bindings[a]}
                    )
                    self.warnings.append(f"{binding!r} now belongs to {owner}, not {action}")

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
    def migrate(path: Path | None = None) -> bool:
        """Rewrite an older keymap file to hold only the user's own changes. Older versions
        wrote every default into the file, so it listed bindings the program no longer
        uses (old defaults are ignored on load). The original is kept as ``.bak``.
        Returns whether the file was rewritten."""
        path = path if path is not None else default_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not isinstance(data, dict) or data.get("version", 1) >= KEYMAP_VERSION:
            return False
        overrides = data.get("bindings", {})
        if not isinstance(overrides, dict):
            return False
        keymap = Keymap(overrides)
        kept = {
            action: list(keymap.bindings(action))
            for action in keymap._overridden
            if keymap.bindings(action) != SPECS[action].defaults
        }
        backup = path.with_name(path.name + f".v{data.get('version', 1)}.bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        Keymap.write_defaults(path, kept)
        return True

    @staticmethod
    def write_defaults(path: Path, bindings: dict[str, list[str]] | None = None) -> None:
        """Write a template: empty ``bindings`` plus every default for reference, so later
        versions can change defaults the user never touched."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": KEYMAP_VERSION,
            "help": "Copy the actions you want to change from 'defaults' into 'bindings'. "
            "Each action maps to a list of bindings; [] unbinds. Keys use Qt key "
            "sequence text (Ctrl+Z, Shift+Right, Space); mouse bindings are "
            "'[Mods+]<Left|Right|Middle> <Click|Drag>' or '[Mods+]Wheel'. "
            "Only 'bindings' is read.",
            "bindings": bindings or {},
            "defaults": {spec.id: list(spec.defaults) for spec in ACTIONS},
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


#: The hotkeys panel's sections: (title, mode it belongs to or None, action ids).
HOTKEY_GROUPS: tuple[tuple[str, str | None, tuple[str, ...]], ...] = (
    (
        "Getting around",
        None,
        (
            "camera.orbit",
            "camera.pan",
            "camera.zoom",
            "camera.vertical",
            "camera.forward",
            "camera.back",
            "camera.left",
            "camera.right",
            "camera.up",
            "camera.down",
            "camera.focus",
        ),
    ),
    ("Modes", None, ("mode.normal", "mode.build", "mode.select")),
    ("NORMAL mode: inspect and use", "normal", ("normal.inspect", "normal.use", "pick")),
    (
        "BUILD mode: place and break",
        "build",
        (
            "build.place",
            "build.line",
            "build.layer",
            "build.zoom",
            "build.rotate",
            "build.rotate_back",
            "build.break",
            "edit.delete",
            "build.use",
            "pick",
            "search.blocks",
            "edit.rotate_block",
            "edit.rotate_block_back",
        ),
    ),
    (
        "SELECT mode: boxes and copies",
        "select",
        (
            "select.block",
            "select.extend",
            "select.box",
            "select.copy_drag",
            "select.stack",
            "edit.rotate",
            "edit.rotate_back",
            "edit.flip",
            "edit.flip_depth",
            "edit.copy",
            "edit.paste",
            "edit.delete",
            "select.lock",
        ),
    ),
    (
        "Simulation",
        None,
        (
            "sim.run",
            "sim.run_back",
            "sim.set_zero",
            "sim.tick",
            "sim.tick_back",
            "sim.event",
            "sim.step_back",
            "sim.start",
            "sim.end",
            "sim.next_edit",
            "sim.prev_edit",
            "sim.marker",
        ),
    ),
    ("Pasting", "paste", ("paste.layer", "paste.zoom")),
    ("View", None, ("view.info", "view.xray")),
    (
        "Edit and file",
        None,
        (
            "edit.undo",
            "edit.redo",
            "file.new",
            "file.open",
            "file.save",
            "file.save_as",
            "file.quit",
            "help.controls",
        ),
    ),
    (
        "Inventory",
        None,
        (
            *(f"inventory.{slot}" for slot in range(1, 10)),
            "inventory.up",
            *(f"recent.{slot}" for slot in range(1, 10)),
        ),
    ),
)


def hotkey_sections(
    keymap: Keymap,
) -> list[tuple[str, str | None, list[tuple[str, tuple[str, ...]]]]]:
    """Sections for the hotkeys panel: (title, mode, [(action title, bindings)]). Actions
    not placed in ``HOTKEY_GROUPS`` end up under "Other", so new ones are never hidden."""
    placed = {action for _, _, actions in HOTKEY_GROUPS for action in actions}
    sections = [
        (title, mode, [(SPECS[a].title, keymap.bindings(a)) for a in actions])
        for title, mode, actions in HOTKEY_GROUPS
    ]
    rest = [(spec.title, keymap.bindings(spec.id)) for spec in ACTIONS if spec.id not in placed]
    if rest:
        sections.append(("Other", None, rest))
    return sections
