"""The door lab's representation (tools/doorlab, doc/redstone/doors/representation.md).

Self-contained tests use the library's 2x2 piston door (examples/circuits); the dataset
tests run on every world of data/redstone_learning/ when it is there (third-party designs,
not committed: they are skipped elsewhere):

- round trip: the canonical form (layer 1) of a world rebuilt from its canonical form is
  identical, and the rebuilt world simulates tick by tick like the original;
- replay: the world's own markers ("Closed", "Opened") agree with the doorway's frames;
- counterfactuals: the mechanism/controller split, input timing, the two-cycle test,
  single-block ablation and the combined trim give the known answers on the 2x2 door.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from redsim.cli.session import Session
from tools.doorlab import (
    ablation,
    canonical,
    corpus,
    inputs,
    interactions,
    mechanism,
    metrics,
    replay,
    symmetry,
    transform,
)

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


def test_failure_reason(tmp_path: Path) -> None:
    """R-027 (b): the front piston of a double extender goes first; the rear one's push
    fails on it, and the replay says why."""
    session = Session(tmp_path / "extender.redsim.json", dry_run=True)
    session.run(
        [
            ["new", "size", "16", "force"],
            ["place", "2", "1", "0", "sticky_piston", "facing=east"],
            ["place", "3", "1", "0", "sticky_piston", "facing=east"],
            ["set", "4", "1", "0", "stone"],
            ["settle"],
            ["at", "2", "set", "3", "1", "-1", "redstone_block"],
            ["at", "2", "set", "2", "1", "-1", "redstone_block"],
            ["run", "10"],
        ]
    )
    rec = replay.record(session.doc)
    rear = [e for e in rec.events if e.piston == (2, 1, 0)]
    assert [e.outcome for e in rear] == ["failed"]
    assert rear[0].failure == "immovable sticky_piston[facing=east,extended=true] at 3 1 0"
    front = [e for e in rec.events if e.piston == (3, 1, 0)]
    assert [e.outcome for e in front] == ["pushed"] and front[0].failure is None


def _door_world(tmp_path: Path) -> Path:
    """The 2x2 door as a door-lab world: sections, two lever pulls, markers."""
    session = _door_session(tmp_path)
    canon = canonical.from_document(session.doc)
    canon["annotations"]["markers"] = {"10": "Opened", "30": "Closed"}
    lever = canon["timeline"]["actions"][0]["pos"]
    canon["annotations"]["sections"] = {
        "input": {"color": "#3fa9f5", "positions": [lever]},
        "output": {"color": "#7ed321", "positions": [list(c) for c in CELLS_2X2]},
    }
    path = tmp_path / "2x2 door by test.redsim.json"
    path.write_text(json.dumps(canonical.to_save(canon)))
    return path


def test_mechanism_split_2x2(tmp_path: Path) -> None:
    """The four door pistons, driven by editor pulses alone, move the door identically;
    they are powered in the build (closed door), so their first pulse starts at 0."""
    result = mechanism.check(_door_world(tmp_path))
    assert result["same_frames"]
    assert result["mechanism_pistons"] == 4
    assert {(p["start"], p["length"]) for p in result["contract"]} == {(0, 6), (24, None)}
    assert result["blocks_after"] < result["blocks_before"]


def test_input_timing_and_repeat_2x2(tmp_path: Path) -> None:
    path = _door_world(tmp_path)
    result = inputs.run(path, 6)
    assert result["designed_gap"] == 18
    assert result["clean_from"] == 1  # any gap: the door just follows the lever
    again = inputs.repeat(path)
    assert again["doorway_same"] and again["rest_same"]


def test_ablation_and_trim_2x2(tmp_path: Path) -> None:
    path = _door_world(tmp_path)
    result = ablation.run(path)
    by_change = result["summary"]
    assert by_change["remove piston"] == {"breaks": 4}
    assert by_change["remove lever"] == {"breaks": 1}
    # A head is part of its piston: never removed alone (that leaves a headless piston).
    assert "remove piston_head" not in by_change
    trim = ablation.trim(path, result["results"])
    assert trim["kept_after_all"] == []
    assert trim["blocks_after"] <= trim["blocks_before"]
    # The trimmed build replays inert: every remaining block as in the original.
    base = replay.record(canonical.rebuild(canonical.from_file(path)))
    rec = replay.record(canonical.rebuild(trim["trimmed"]))
    assert rec.changes == base.changes


def test_metrics_dominated() -> None:
    keys = (*metrics.OBJECTIVES, *metrics.HIGHER)

    def door(world: str, size: str, *values: int | None) -> dict[str, object]:
        return {"world": world, "door": size, **dict(zip(keys, values, strict=True))}

    rows = [
        door("a", "3x3", 100, 50, 10, 20, 10, 8),
        door("b", "3x3", 120, 60, 10, 20, 12, 8),  # a is as good everywhere, better in some
        door("c", "3x3", 90, 70, 10, 20, 10, 8),  # smaller box, more blocks: a trade-off
        door("d", "4x4", 200, 90, 12, 20, 9, 8),  # another doorway size: not compared
        door("e", "3x3", 100, 50, 10, 20, None, 8),  # a missing value: not compared
        door("f", "3x3", 90, 40, 9, 19, 9, 6),  # better in all five, but fewer orientations
    ]
    assert metrics.dominated(rows) == {
        "a": None,
        "b": "a",
        "c": None,
        "d": None,
        "e": None,
        "f": None,
    }


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
