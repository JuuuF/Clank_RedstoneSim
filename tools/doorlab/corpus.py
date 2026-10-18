"""The dataset: finding the worlds, naming them, opening them read-only.

The worlds are the editor's own files (``format: redsim-save``), some without the
``.redsim.json`` extension. They are opened through the command line's ``Session`` (the same
code ``redsim-cli`` runs) and never saved: nothing here writes to the dataset.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import redsim.cli.commands  # noqa: F401  (registers the commands a Session runs)
from redsim.cli.session import Session

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data" / "redstone_learning"

_NAME = re.compile(
    r"^(?:(?P<size>\d+x\d+)\s+)?(?P<title>.*?)\s+[Bb]y\s+(?P<creator>.+?)"
    r"(?P<broken>\s*\[broken sim\])?$"
)


@dataclass(frozen=True)
class WorldName:
    """What a file name says: ``5x5 Vault Door by Nile [broken sim].redsim.json``."""

    stem: str
    size: str | None  # "5x5" (width x height of the doorway) or None
    title: str  # "Vault Door"
    creator: str  # "Nile"
    broken_sim: bool  # the owner marked it as simulated wrongly (at some point)

    @property
    def slug(self) -> str:
        """A short id: ``5x5-vault-door-nile``."""
        words = [self.size or "", self.title, self.creator]
        text = "-".join(w for w in words if w).lower()
        return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def stem_of(path: Path) -> str:
    name = path.name
    for suffix in (".redsim.json", ".json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def parse_name(path: Path) -> WorldName:
    stem = stem_of(path)
    match = _NAME.match(stem)
    if match is None:
        return WorldName(stem, None, stem, "unknown", "[broken sim]" in stem)
    return WorldName(
        stem=stem,
        size=match["size"],
        title=match["title"].strip(),
        creator=match["creator"].strip(),
        broken_sim=bool(match["broken"]),
    )


def is_world(path: Path) -> bool:
    """A redsim save, whatever its extension (``.undo`` files and documents are not)."""
    if not path.is_file() or path.suffix in (".undo", ".docx", ".md", ".txt"):
        return False
    try:
        with path.open("rb") as handle:
            head = handle.read(200)
    except OSError:
        return False
    return b'"redsim-save"' in head


def world_files(root: Path = DATASET) -> list[Path]:
    """Every world of the dataset, sorted by category folder and name."""
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if is_world(p))


def category_of(path: Path, root: Path = DATASET) -> str:
    relative = path.relative_to(root)
    return relative.parts[0] if len(relative.parts) > 1 else ""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_extra(path: Path) -> dict[str, Any]:
    """The file's ``extra`` part as stored (sections, markers, groups, camera …)."""
    return dict(json.loads(path.read_text()).get("extra", {}))


def open_world(path: Path) -> Session:
    """The world in a command-line session that never saves (``dry_run``)."""
    session = Session(path, dry_run=True)
    session.open()
    if not session.has_document:
        raise FileNotFoundError(path)
    return session


def find(text: str, root: Path = DATASET) -> Path:
    """The one world whose slug or file name contains ``text`` (case-insensitive)."""
    wanted = text.lower()
    hits = [
        p for p in world_files(root) if wanted in p.name.lower() or wanted in parse_name(p).slug
    ]
    if len(hits) != 1:
        names = ", ".join(parse_name(p).slug for p in hits) or "none"
        raise LookupError(f"{text!r} matches {len(hits)} worlds: {names}")
    return hits[0]
