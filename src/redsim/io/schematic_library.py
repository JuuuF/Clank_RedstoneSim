"""The schematic library: a folder of schematic files, like the game's saves folder
(owner, 2026-10-14). Every schematic imported once is copied here and offered again for
later imports; each file gets a small ``<file>.meta.json`` beside it (name, size, block
count, author and description from the file, where it came from, when it was imported)
and the editor adds a ``<file>.png`` preview.

Schematic folders of Minecraft mods (Litematica's ``.minecraft/schematics``, WorldEdit's
``config/worldedit/schematics``) are listed too, read only: importing one of their files
copies it into the library.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from redsim.io.schematics import SUFFIXES, read_schematic, read_schematic_metadata

META_SUFFIX = ".meta.json"
PREVIEW_SUFFIX = ".png"


def minecraft_schematic_folders() -> list[Path]:
    """Where Minecraft mods keep schematics on this system (only existing folders)."""
    roots = [Path.home() / ".minecraft"]
    if sys.platform == "darwin":
        roots.append(Path.home() / "Library" / "Application Support" / "minecraft")
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata) / ".minecraft")
    folders = []
    for root in roots:
        folders += [root / "schematics", root / "config" / "worldedit" / "schematics"]
    return [folder for folder in folders if folder.is_dir()]


@dataclass
class SchematicEntry:
    path: Path
    name: str
    size: tuple[int, int, int]
    blocks: int  # blocks that are not air
    author: str
    description: str
    source: str  # where it was imported from
    imported: float  # seconds; the file's time for files not imported
    in_library: bool  # False: a Minecraft mod's folder (read only)

    @property
    def preview(self) -> Path:
        return self.path.with_name(self.path.name + PREVIEW_SUFFIX)


def is_schematic(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUFFIXES


def _meta_path(path: Path) -> Path:
    return path.with_name(path.name + META_SUFFIX)


def describe(path: Path, source: str = "", imported: float | None = None) -> dict[str, Any]:
    """The metadata of a schematic file (reads the whole file)."""
    prefab = read_schematic(path)
    info = read_schematic_metadata(path)
    return {
        "name": info.get("name") or prefab.name,
        "size": list(prefab.size),
        "blocks": prefab.non_air_count,
        "author": info.get("author", ""),
        "description": info.get("description", ""),
        "source": source or str(path),
        "imported": imported if imported is not None else path.stat().st_mtime,
    }


def _entry(path: Path, in_library: bool) -> SchematicEntry | None:
    meta_path = _meta_path(path)
    meta: dict[str, Any] | None = None
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = None
    if meta is None:
        try:
            meta = describe(path)
        except (OSError, ValueError, KeyError, IndexError, EOFError):
            return None
        if in_library:  # remembered, so the next listing is quick
            _write_meta(path, meta)
    size = meta.get("size") or [0, 0, 0]
    return SchematicEntry(
        path=path,
        name=str(meta.get("name") or path.name.split(".")[0]),
        size=(int(size[0]), int(size[1]), int(size[2])),
        blocks=int(meta.get("blocks", 0)),
        author=str(meta.get("author", "")),
        description=str(meta.get("description", "")),
        source=str(meta.get("source", path)),
        imported=float(meta.get("imported", path.stat().st_mtime)),
        in_library=in_library,
    )


def _write_meta(path: Path, meta: dict[str, Any]) -> None:
    with contextlib.suppress(OSError):
        _meta_path(path).write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")


def entries(library: Path, others: list[Path] | None = None) -> list[SchematicEntry]:
    """The library's schematics (newest first), then those of ``others`` folders."""
    found: list[SchematicEntry] = []
    if library.is_dir():
        mine = [_entry(p, True) for p in sorted(library.iterdir()) if is_schematic(p)]
        found += sorted((e for e in mine if e is not None), key=lambda e: -e.imported)
    for folder in others or []:
        theirs = [_entry(p, False) for p in sorted(folder.rglob("*")) if is_schematic(p)]
        found += [e for e in theirs if e is not None]
    return found


def _digest(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def add(library: Path, source: Path) -> Path:
    """Copy a schematic into the library (once: the same file content is found again)
    with its metadata; returns the library copy. Reads the file first, so a file that is
    not a schematic raises before anything is copied."""
    meta = describe(source, source=str(source.resolve()), imported=time.time())
    library.mkdir(parents=True, exist_ok=True)
    digest = _digest(source)
    for existing in library.iterdir():
        if is_schematic(existing) and _digest(existing) == digest:
            return existing
    target = library / source.name
    number = 2
    while target.exists():
        target = library / f"{source.name.split('.')[0]} ({number}){''.join(source.suffixes)}"
        number += 1
    shutil.copy2(source, target)
    _write_meta(target, meta)
    return target


def remove(path: Path) -> None:
    """Delete a library schematic with its metadata and preview."""
    for file in (path, _meta_path(path), path.with_name(path.name + PREVIEW_SUFFIX)):
        with contextlib.suppress(FileNotFoundError):
            file.unlink()
