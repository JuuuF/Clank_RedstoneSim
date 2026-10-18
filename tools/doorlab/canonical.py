"""Layer 1: the canonical world, exactly what the file says, as plain sorted data.

A world file stores the build (tick 0) as an engine snapshot (``extra.history.base``), the
recorded edits per tick (``plan``) and the annotations (sections, markers, labels …). The
canonical form keeps all of it, normalized so two worlds can be compared line by line:

- ``blocks``: every block of the build, ``[x, y, z, state]`` sorted by y, z, x (the floor
  too), states with every property as the simulator writes them;
- ``block_entities``: their saved data, in the engine's order (tickers refer to them by
  index, and the order of block-entity ticks is simulation order);
- ``engine_runtime``: the rest of the snapshot (game time, pending scheduled ticks, block
  events, ticker lists, …) as the save codec writes it. Usually only defaults; it is kept
  so nothing that influences the simulation is dropped;
- ``timeline``: the recorded actions with their ticks, and the simulated length;
- ``annotations``: sections (the designated inputs and outputs), markers, groups, labels,
  notes, targets.

``to_save`` turns it back into a world file; ``rebuild`` opens that as a ``Document``. The
round-trip tests (tests/doorlab/test_canonical.py) check that the canonical form of a
rebuilt world is identical and that it simulates tick by tick like the original.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from redsim.editor.document import Document
from redsim.io import save as save_io
from redsim.sim.engine import Engine
from tools.doorlab import corpus

SCHEMA = "doorlab.canonical/1"
#: Level fields the canonical form spells out itself (the rest is ``engine_runtime``).
_SPELLED_OUT = ("palette", "blocks", "block_entities", "block_entity_map")
#: Annotation fields of ``extra`` (the editor-only rest, like the camera, is not kept).
_ANNOTATIONS = ("sections", "markers", "groups", "labels", "notes", "targets", "monitors")


def _build_snapshot(document: Document) -> dict[str, Any]:
    """The build (tick 0) as the save codec writes it."""
    base = Engine()
    base.restore(document.history.base)
    return save_io.engine_to_json(base)


def from_document(document: Document, source: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = _build_snapshot(document)
    level = snapshot["level"]
    palette = level["palette"]
    blocks = sorted(
        ([x, y, z, palette[i]] for x, y, z, i in level["blocks"]),
        key=lambda b: (b[1], b[2], b[0]),
    )
    runtime = {k: v for k, v in level.items() if k not in _SPELLED_OUT}
    runtime["engine"] = snapshot["engine"]
    entity_positions = {index: key for key, index in level["block_entity_map"].items()}
    entities = []
    for index, entry in enumerate(level["block_entities"]):
        entities.append({**entry, "mapped": index in entity_positions})
    plan = document.history.plan()
    actions = [{"tick": tick, **action.to_json()} for tick in sorted(plan) for action in plan[tick]]
    saved = _saved_extra(document)
    annotations = {k: saved[k] for k in _ANNOTATIONS if k in saved}
    return {
        "schema": SCHEMA,
        "source": source or {},
        "game_version": snapshot["game_version"],
        "blocks": blocks,
        "block_entities": entities,
        "engine_runtime": runtime,
        "timeline": {"end_tick": document.end_tick, "actions": actions},
        "annotations": annotations,
    }


def _saved_extra(document: Document) -> dict[str, Any]:
    """The annotations as ``Document.save`` would write them (without writing a file)."""
    extra: dict[str, Any] = {
        "sections": document.sections.to_json(),
        "groups": document.groups.to_json(),
        "monitors": [list(pos) for pos in document.monitors],
        "markers": {str(t): n for t, n in document.visible_markers().items()},
    }
    if document.labels:
        extra["labels"] = {name: label.to_json() for name, label in document.labels.items()}
    if document.notes:
        extra["notes"] = list(document.notes)
    if document.targets:
        extra["targets"] = list(document.targets)
    return extra


def from_file(path: Path) -> dict[str, Any]:
    name = corpus.parse_name(path)
    source = {
        "file": str(path.relative_to(corpus.DATASET))
        if corpus.DATASET in path.parents
        else path.name,
        "sha256": corpus.sha256(path),
        "title": name.title,
        "creator": name.creator,
        "size": name.size,
    }
    session = corpus.open_world(path)
    try:
        return from_document(session.doc, source)
    finally:
        session.close()


def to_save(canonical: dict[str, Any]) -> dict[str, Any]:
    """A world file (``redsim-save``) holding exactly the canonical world, view at tick 0."""
    palette: dict[str, int] = {}
    rows = []
    for x, y, z, state in sorted(canonical["blocks"]):
        rows.append([x, y, z, palette.setdefault(state, len(palette))])
    runtime = dict(canonical["engine_runtime"])
    engine_part = runtime.pop("engine")
    entities, entity_map = [], {}
    for index, entry in enumerate(canonical["block_entities"]):
        entry = dict(entry)
        if entry.pop("mapped"):
            x, y, z = entry["pos"]
            entity_map[f"{x},{y},{z}"] = index
        entities.append(entry)
    level = {
        **runtime,
        "palette": list(palette),
        "blocks": rows,
        "block_entities": entities,
        "block_entity_map": entity_map,
    }
    snapshot = {
        "format": save_io.FORMAT,
        "version": save_io.VERSION,
        "game_version": canonical["game_version"],
        "level": level,
        "engine": engine_part,
    }
    plan: dict[str, list[dict[str, Any]]] = {}
    for action in canonical["timeline"]["actions"]:
        entry = dict(action)
        plan.setdefault(str(entry.pop("tick")), []).append(entry)
    extra = json.loads(json.dumps(canonical["annotations"]))
    extra["history"] = {
        "base": snapshot,
        "plan": plan,
        "end_tick": canonical["timeline"]["end_tick"],
        "tick": 0,
    }
    return {**snapshot, "extra": extra}


def rebuild(canonical: dict[str, Any]) -> Document:
    """The canonical world opened as an editor document (through a temporary file)."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "rebuilt.redsim.json"
        path.write_text(json.dumps(to_save(canonical)))
        document = Document.open(path)
    document.path = None
    return document


def dumps(canonical: dict[str, Any]) -> str:
    """Stable text: one block per line, so diffs between worlds stay readable."""
    head = {k: v for k, v in canonical.items() if k != "blocks"}
    lines = ["{", f' "schema": {json.dumps(canonical["schema"])},', ' "blocks": [']
    blocks = canonical["blocks"]
    for i, block in enumerate(blocks):
        lines.append("  " + json.dumps(block) + ("," if i < len(blocks) - 1 else ""))
    lines.append(" ],")
    rest = {k: v for k, v in head.items() if k != "schema"}
    body = json.dumps(rest, indent=1, sort_keys=True)
    lines.append(body[1:-1].strip("\n"))
    lines.append("}")
    return "\n".join(lines) + "\n"
