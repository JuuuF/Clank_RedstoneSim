"""The door lab's representation (tools/doorlab, doc/redstone/doors/representation.md).

Self-contained tests use the library's 2x2 piston door (examples/circuits); the dataset
tests run on every world of data/redstone_learning/ when it is there (third-party designs,
not committed: they are skipped elsewhere):

- round trip: the canonical form (layer 1) of a world rebuilt from its canonical form is
  identical, and the rebuilt world simulates tick by tick like the original;
- replay: the world's own markers ("Closed", "Opened") agree with the doorway's frames.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tools.doorlab import canonical, corpus, interactions, replay, symmetry, transform

ROOT = Path(__file__).resolve().parents[2]
DOOR_2X2 = ROOT / "examples" / "circuits" / "piston_door_2x2.redsim.json"
CELLS_2X2 = [(4, 1, 0), (4, 2, 0), (5, 1, 0), (5, 2, 0)]
WORLDS = corpus.world_files()
#: Worlds whose doorway does not return to its build state by the "Opened" marker in the
#: simulator, which matches the 26.3 server there (EXP-068): the build itself does this.
KNOWN_STUCK = {"7x7-piston-door-legden", "8x8-piston-door-legden"}


def _door_session(tmp_path: Path):
    world = tmp_path / "door.redsim.json"
    shutil.copy(DOOR_2X2, world)
    session = corpus.open_world(world)
    session.run([["at", "2", "use", "@L"], ["at", "20", "use", "@L"], ["run", "40"]])
    return session


def test_names() -> None:
    name = corpus.parse_name(Path("5x5 Vault Door by Nile [broken sim].redsim.json"))
    assert (name.size, name.title, name.creator, name.broken_sim) == (
        "5x5",
        "Vault Door",
        "Nile",
        True,
    )
    assert name.slug == "5x5-vault-door-nile"
    other = corpus.parse_name(Path("5x5 Glass Piston Door By ashevoy.redsim.json"))
    assert other.creator == "ashevoy"
    plain = corpus.parse_name(Path("3x3 Seamless Glass Door by Nile"))
    assert (plain.size, plain.title, plain.creator) == ("3x3", "Seamless Glass Door", "Nile")


def test_doorway_plane() -> None:
    way = interactions.doorway(CELLS_2X2 + [(9, 9, 9)])
    assert (way.normal, way.plane, way.width, way.height) == ("z", 0, 2, 2)
    assert way.extra_cells == [(9, 9, 9)]
    assert way.grid({c: "#" for c in CELLS_2X2}) == ["##", "##"]


def test_canonical_round_trip_2x2(tmp_path: Path) -> None:
    session = _door_session(tmp_path)
    first = canonical.from_document(session.doc)
    assert first["timeline"]["actions"][0]["tick"] == 2
    rebuilt = canonical.rebuild(first)
    assert canonical.dumps(canonical.from_document(rebuilt)) == canonical.dumps(first)
    assert replay.record(rebuilt).fingerprint() == replay.record(session.doc).fingerprint()


def test_replay_2x2(tmp_path: Path) -> None:
    session = _door_session(tmp_path)
    rec = replay.record(session.doc, causes=True)
    summary = replay.doorway_summary(rec, CELLS_2X2)
    # Lever on at 2: the wall torches turn off, the four sticky pistons retract
    # (open); lever off at 20: they extend again (closed).
    assert summary["frames"][0] == "####"
    assert 2 < min(t for t in summary["open_ticks"]) < 10
    assert summary["frames"][-1] == "####"
    kinds = {(e.kind, e.outcome) for e in rec.events}
    assert ("retract", "pulled") in kinds and ("extend", "pushed") in kinds
    extensions = [e for e in rec.events if e.kind == "extend"]
    assert all(e.power is not None for e in extensions)
    # The lever's change is a player action; the pistons' moves trace back to it.
    assert any(link.via == "action" and link.pos == (4, 1, 3) for link in rec.links)
    checks = replay.check_markers(rec, CELLS_2X2, {30: "Closed", 10: "Opened"})
    assert all(c["ok"] for c in checks)


def test_static_pistons_2x2() -> None:
    session = corpus.open_world(DOOR_2X2)
    found = interactions.pistons(session.doc.level)
    assert len(found) == 4 and all(p.sticky and p.extended for p in found)
    # Each extended sticky piston would pull exactly its door cell.
    pulled = sorted(tuple(p.would_move[0]) for p in found)
    assert pulled == sorted(CELLS_2X2)


@pytest.mark.skipif(not WORLDS, reason="the dataset (data/redstone_learning) is not here")
@pytest.mark.parametrize("path", WORLDS, ids=[corpus.parse_name(p).slug for p in WORLDS])
def test_dataset_round_trip_and_markers(path: Path) -> None:
    session = corpus.open_world(path)
    doc = session.doc
    first = canonical.from_document(doc)
    rebuilt = canonical.rebuild(first)
    assert canonical.dumps(canonical.from_document(rebuilt)) == canonical.dumps(first)
    original = replay.record(doc)
    assert replay.record(rebuilt).fingerprint() == original.fingerprint()
    outputs = [tuple(p) for p in first["annotations"]["sections"]["output"]["positions"]]
    way = interactions.doorway(outputs)
    markers = {int(t): n for t, n in first["annotations"]["markers"].items()}
    checks = [c for c in replay.check_markers(original, way.cells, markers) if c["checked"]]
    assert checks
    stuck = corpus.parse_name(path).slug in KNOWN_STUCK
    assert all(c["ok"] for c in checks) != stuck


def test_transform_inverts() -> None:
    session = corpus.open_world(DOOR_2X2)
    canon = canonical.from_document(session.doc)
    # A mirror keeps the box, so mirroring twice is the identity. (Turns are about the
    # box's center, which moves by half a block for odd-by-even boxes: no identity.)
    once, _ = transform.transform(canon, 0, True)
    assert canonical.dumps(once) != canonical.dumps(canon)
    twice, _ = transform.transform(once, 0, True)
    assert canonical.dumps(twice) == canonical.dumps(canon)
    turned, sym = transform.transform(canon, 1, False)
    states = {tuple(b[:3]): b[3] for b in turned["blocks"]}
    lever = next(b for b in canon["blocks"] if "lever" in b[3])
    assert states[sym.pos(tuple(lever[:3]))] == sym.state(lever[3])
    assert "facing=east" in sym.state(
        "minecraft:repeater[facing=north,delay=1,locked=false,powered=false]"
    )
    moved, sym = transform.transform(canon, 0, False, (3, -5))
    assert sym.pos((4, 1, 0)) == (7, 1, -5)
    assert len(moved["blocks"]) == len(canon["blocks"])


def test_symmetry_2x2(tmp_path: Path) -> None:
    session = _door_session(tmp_path)
    canon = canonical.from_document(session.doc)
    canon["annotations"]["markers"] = {"10": "Opened", "30": "Closed"}
    canon["annotations"]["sections"] = {
        "output": {"color": "#7ed321", "positions": [list(c) for c in CELLS_2X2]}
    }
    result = symmetry.check_canonical(canon)
    assert result["all_identical"]
    assert all(o["markers_ok"] for o in result["orientations"])
    # Not vacuous: the turned run differs from the original when not turned back.
    turned, sym = transform.transform(canon, 1, False)
    original = replay.record(canonical.rebuild(canon))
    rec = replay.record(canonical.rebuild(turned))
    assert rec.changes != original.changes
    assert symmetry._turned_changes(original, sym, transform.floor_of(canon)) == rec.changes
