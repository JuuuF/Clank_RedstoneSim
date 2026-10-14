"""The schematic library (``io/schematic_library.py``): imported schematics are kept in a
folder with their metadata and offered again."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.io import schematic_library as library
from redsim.io.schematics import write_schematic
from redsim.world import blocks


def _schematic(path: Path, name: str = "lamp") -> Path:
    doc = Document.new_flat()
    doc.setblock((0, 1, 0), blocks.parse_state("lever[face=floor,facing=east]"))
    doc.setblock((1, 1, 0), blocks.parse_state("redstone_lamp"))
    prefab = doc.copy(Region((0, 1, 0), (1, 1, 0)))
    prefab.name = name
    write_schematic(path, prefab, author="Steve")
    return path


def test_an_import_is_kept_once_with_its_metadata(tmp_path: Path) -> None:
    (tmp_path / "downloads").mkdir()
    source = _schematic(tmp_path / "downloads" / "lamp.litematic")
    shelf = tmp_path / "schematics"
    kept = library.add(shelf, source)
    assert kept.parent == shelf and kept.read_bytes() == source.read_bytes()
    assert library.add(shelf, source) == kept  # the same file is found again
    meta = json.loads((shelf / "lamp.litematic.meta.json").read_text())
    assert meta["size"] == [2, 1, 1] and meta["blocks"] == 2 and meta["author"] == "Steve"
    assert meta["source"] == str(source.resolve())
    found = library.entries(shelf)
    assert [e.name for e in found] == ["lamp"] and found[0].in_library
    library.remove(kept)
    assert library.entries(shelf) == [] and not (shelf / "lamp.litematic.meta.json").exists()


def test_a_name_clash_keeps_both(tmp_path: Path) -> None:
    shelf = tmp_path / "schematics"
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = library.add(shelf, _schematic(tmp_path / "a" / "x.schem", "one"))
    second = library.add(shelf, _schematic(tmp_path / "b" / "x.schem", "two"))
    assert first != second and second.name == "x (2).schem"
    assert {e.name for e in library.entries(shelf)} == {"one", "two"}


def test_a_file_that_is_no_schematic_is_not_copied(tmp_path: Path) -> None:
    bad = tmp_path / "bad.litematic"
    bad.write_bytes(b"not nbt")
    with pytest.raises((ValueError, OSError, EOFError, KeyError, IndexError)):
        library.add(tmp_path / "schematics", bad)
    assert not (tmp_path / "schematics").exists() or not any((tmp_path / "schematics").iterdir())


def test_the_prefabs_panel_imports_from_the_library(tmp_path: Path, monkeypatch: Any) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets

    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from redsim.ui import schematic_picker
    from redsim.ui.main_window import MainWindow

    monkeypatch.setattr(library, "minecraft_schematic_folders", lambda: [])
    shelf = schematic_picker.library_folder()
    (tmp_path / "in").mkdir()
    kept = library.add(shelf, _schematic(tmp_path / "in" / "lamp.litematic"))
    picker = schematic_picker.SchematicPicker(None, "Add as prefab")
    assert picker.list.count() == 1 and picker.pick_button.isEnabled()
    picker.close()

    def choose(self: schematic_picker.SchematicPicker) -> int:
        self.chosen = kept
        return 1

    monkeypatch.setattr(schematic_picker.SchematicPicker, "exec", choose)
    window = MainWindow()
    window._import_schematic_prefab()
    window._import_schematic_prefab()  # again: a second prefab with its own name
    assert set(window.document.prefabs) == {"lamp", "lamp 2"}
    assert window.document.prefabs["lamp"].non_air_count == 2
    assert (shelf / "lamp.litematic.png").is_file()  # the picker drew its picture
    window.document.dirty = False
    window.close()
