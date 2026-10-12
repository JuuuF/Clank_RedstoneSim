"""Settings → Keymap…: edit bindings in the program instead of the JSON file."""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt  # noqa: E402

from redsim.ui.keymap import Keymap, binding_text, default_path  # noqa: E402
from redsim.ui.keymap_editor import KeymapEditor  # noqa: E402


@pytest.fixture(scope="module")
def app() -> Any:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_binding_text_orders_modifiers_and_ignores_lone_modifiers() -> None:
    assert binding_text(Qt.Key.Key_R, ["Shift", "Ctrl"]) == "Ctrl+Shift+R"
    assert binding_text(Qt.Key.Key_Shift, ["Shift"]) is None
    assert binding_text(Qt.Key.Key_Dead_Circumflex, []) == "^"


def test_editor_records_checks_and_saves_only_changes(app: Any) -> None:
    saved: list[Keymap] = []
    editor = KeymapEditor(Keymap())
    editor.applied.connect(saved.append)
    row = editor.row_of("sim.run")
    editor.table.selectRow(row)
    editor._start_recording()
    editor.record_key(Qt.Key.Key_Shift, ["Shift"])  # a modifier alone: still waiting
    editor.record_key(Qt.Key.Key_K, ["Ctrl"])
    assert editor.bindings_at(row) == ["Space", "P", "Ctrl+K"]
    editor.set_bindings("mode.build", ["Ctrl+K"])  # a clash
    editor._check()
    assert "Ctrl+K" in editor.status.text()
    editor._save()
    assert not saved  # not saved while bindings clash
    editor.set_bindings("mode.build", ["B"])  # the default again
    editor._save()
    assert saved and saved[0].bindings("sim.run") == ("Space", "P", "Ctrl+K")
    data = json.loads(default_path().read_text(encoding="utf-8"))
    assert data["bindings"] == {"sim.run": ["Space", "P", "Ctrl+K"]}  # only the change


def test_editor_reset_brings_back_defaults(app: Any) -> None:
    editor = KeymapEditor(Keymap({"sim.run": ["P"]}))
    editor.table.selectRow(editor.row_of("sim.run"))
    editor._reset_row()
    assert editor.edited() == {}
