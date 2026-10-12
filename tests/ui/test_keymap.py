"""Keymap parsing, overrides, conflicts and mode lookup (no display needed)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from redsim.ui.keymap import SPECS, Keymap, normalize_key, parse_mouse


def test_defaults_have_no_conflicts() -> None:
    assert Keymap().warnings == []


def test_parse_mouse_bindings() -> None:
    binding = parse_mouse("Shift+Middle Drag")
    assert binding.modifiers == {"Shift"} and binding.button == "Middle"
    assert binding.gesture == "Drag"
    wheel = parse_mouse("control+wheel")
    assert wheel.modifiers == {"Ctrl"} and wheel.button is None and wheel.gesture == "Wheel"
    for bad in ("Middle", "Hyper+Left Click", "Left Tap", "Up Drag"):
        with pytest.raises(ValueError):
            parse_mouse(bad)


def test_normalize_key_ignores_modifier_order_and_case() -> None:
    assert normalize_key("shift+ctrl+z") == normalize_key("Ctrl+Shift+Z")


def test_owner_camera_and_mode_defaults() -> None:
    keymap = Keymap()
    none: frozenset[str] = frozenset()
    shift = frozenset({"Shift"})
    ctrl = frozenset({"Ctrl"})
    assert keymap.mouse_action("normal", none, "Middle", "Drag") == "camera.orbit"
    assert keymap.mouse_action("build", shift, "Middle", "Drag") == "camera.pan"
    # The wheel moves the camera up and down in every mode; Ctrl+wheel zooms.
    assert keymap.mouse_action("select", none, None, "Wheel") == "camera.vertical"
    assert keymap.mouse_action("normal", ctrl, None, "Wheel") == "camera.zoom"
    assert keymap.mouse_action("build", none, "Left", "Click") == "build.place"
    assert keymap.mouse_action("build", none, "Left", "Drag") == "build.line"
    assert keymap.mouse_action("build", none, "Right", "Click") == "build.rotate"
    assert keymap.mouse_action("normal", none, "Right", "Click") == "normal.use"
    assert keymap.mouse_action("select", none, "Left", "Drag") == "select.box"
    assert keymap.mouse_action("normal", none, "Middle", "Click") == "pick"
    assert keymap.mouse_action("normal", none, "Left", "Drag") is None
    # Shift is not a camera key: rewinding has its own bindings.
    assert "Shift+T" not in keymap.bindings("sim.tick_back")
    # While pasting, the plain wheel moves the paste layer (owner, round three).
    assert keymap.mouse_action("paste", none, None, "Wheel") == "paste.layer"
    assert keymap.mouse_action("paste", ctrl, None, "Wheel") == "paste.zoom"
    assert keymap.mouse_action("paste", none, "Middle", "Drag") == "camera.orbit"
    # Blender timeline keys.
    assert keymap.bindings("sim.start") == ("Shift+Left",)
    assert keymap.bindings("sim.tick") == ("Right", "T")


def test_overrides_replace_unbind_and_warn(tmp_path: Path) -> None:
    path = tmp_path / "keymap.json"
    path.write_text(
        json.dumps(
            {
                "bindings": {
                    "camera.orbit": ["Right Drag"],
                    "pick": [],
                    "no.such.action": ["X"],
                    "build.place": ["Right Click", "Left Flick"],
                }
            }
        )
    )
    keymap = Keymap.load(path)
    none: frozenset[str] = frozenset()
    assert keymap.mouse_action("normal", none, "Right", "Drag") == "camera.orbit"
    assert keymap.mouse_action("normal", none, "Middle", "Drag") is None
    assert keymap.mouse_action("build", none, "Middle", "Click") is None
    assert keymap.bindings("build.place") == ("Right Click",)
    assert any("no.such.action" in w for w in keymap.warnings)
    assert any("Left Flick" in w for w in keymap.warnings)


def test_a_user_binding_takes_the_key_from_a_default() -> None:
    keymap = Keymap({"sim.run": ["B"]})
    assert keymap.bindings("mode.build") == ()
    assert any("mode.build" in w and "sim.run" in w for w in keymap.warnings)


def test_conflicting_user_bindings_are_reported() -> None:
    keymap = Keymap({"sim.run": ["X"], "mode.select": ["X"]})
    assert any("mode.select" in w and "sim.run" in w for w in keymap.warnings)


def test_old_defaults_in_a_keymap_file_follow_the_new_defaults() -> None:
    """Older versions wrote every default into the file; those are not user choices."""
    keymap = Keymap(
        {
            "sim.step_back": ["Shift+Left"],
            "build.place": ["Right Click"],
            "build.break": ["Left Click"],
        }
    )
    assert keymap.bindings("sim.start") == ("Shift+Left",)
    assert keymap.bindings("sim.step_back") == ("Ctrl+Left",)
    assert keymap.mouse_action("build", frozenset(), "Left", "Click") == "build.place"
    assert keymap.warnings == []


def test_the_keymap_template_leaves_bindings_empty(tmp_path: Path) -> None:
    path = tmp_path / "keymap.json"
    Keymap.write_defaults(path)
    data = json.loads(path.read_text())
    assert data["bindings"] == {} and data["defaults"]["sim.start"] == ["Shift+Left"]


def test_unreadable_file_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "keymap.json"
    path.write_text("{not json")
    keymap = Keymap.load(path)
    assert keymap.bindings("sim.run") == SPECS["sim.run"].defaults
    assert keymap.warnings and "cannot read" in keymap.warnings[0]


def test_written_defaults_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "keymap.json"
    Keymap.write_defaults(path)
    keymap = Keymap.load(path)
    assert keymap.warnings == []
    assert all(keymap.bindings(a) == spec.defaults for a, spec in SPECS.items())


def test_hotkey_sections_cover_every_action() -> None:
    from redsim.ui.keymap import ACTIONS, hotkey_sections

    sections = hotkey_sections(Keymap())
    titles = {title for _, _, rows in sections for title, _ in rows}
    assert {spec.title for spec in ACTIONS} <= titles
    assert all(title != "Other" for title, _, _ in sections)  # everything has a home
    modes = {mode for _, mode, _ in sections if mode}
    assert modes == {"normal", "build", "select", "paste"}
