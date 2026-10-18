"""Comparing two contraptions up to rotation, mirroring and position
(``python -m tools.doorlab.compare [A B]``; without arguments: every pair of the dataset).

Each contraption (the build's blocks above the floor, layer 1) is turned through the
eight horizontal symmetries (four quarter turns, with and without a mirror) with the
simulator's own state transforms (``redsim.world.rotation``: a piston facing east turns to
face south, …), moved to the origin and compared cell by cell with the other one. Two
levels:

- **exact**: full block states;
- **structure**: block ids plus the properties that describe the build (facing, delay,
  mode, half, …), without the ones the simulation changes (power, lit, extended,
  powered, wire connections …); piston heads are left out and pistons count as
  retracted, so a door saved open and the same door saved closed still match;
- **abstract**: like structure, but plain building blocks (role "structure") are named
  by what the simulator says they do, not by their material: "solid" (conducts) or
  "clear" (does not), and whether a piston moves them ("movable", "immovable",
  "breaks"). Iron blocks and white concrete are then the same.

The similarity is |A ∩ B| / |A ∪ B| for the best of the eight variants.

``behavior`` compares what two doors *do*: every door block's trajectory (ticks and cells,
from ``analysis``) in doorway coordinates (u along the door, v up, w across), with and
without a left-right mirror. Two doors with the same behavior move the same blocks the
same way at the same ticks, whatever their wiring looks like.
"""

from __future__ import annotations

import argparse
from itertools import combinations
from typing import Any

from redsim.cli.views import state_text
from redsim.world.rotation import mirror_state, rotate_offset, rotate_state
from tools.doorlab import corpus, interactions

Pos = tuple[int, int, int]
#: Properties the simulation changes; left out at the structure level.
DYNAMIC = {
    "powered",
    "power",
    "lit",
    "extended",
    "triggered",
    "enabled",
    "locked",
    "north",
    "south",
    "east",
    "west",
    "up",
    "down",
    "waterlogged",
    "short",
    "attached",
    "disarmed",
    "has_record",
    "crafting",
    "orientation",
    "level",
    "has_book",
    "bottom",
    "distance",
    "persistent",
}
SKIP = {"piston_head", "moving_piston"}


def contraption(level: Any) -> dict[Pos, Any]:
    floor = interactions.floor_top(level)
    return {p: s for p, s in level.blocks.items() if not s.is_air and p[1] > floor}


def _abstract_name(level: Any, pos: Pos, state: Any) -> str:
    if interactions.role(state) != "structure":
        return interactions.block_id(state)
    facts = interactions.block_facts(level, pos)
    kind = "solid" if facts.conductor else "clear"
    move = {
        "move": "movable",
        "push_only": "movable",
        "blocks": "immovable",
        "break": "breaks",
    }.get(facts.push, facts.push)
    return f"{kind}-{move}"


def _structure_key(state: Any, name: str | None = None) -> str | None:
    name = name or interactions.block_id(state)
    if interactions.block_id(state) in SKIP:
        return None
    props = []
    for prop in state.block.properties:
        if prop.name in DYNAMIC:
            continue
        props.append(f"{prop.name}={state.get(prop)}")
    return name + ("[" + ",".join(props) + "]" if props else "")


LEVELS = ("exact", "structure", "abstract")


def variants(
    blocks: dict[Pos, Any], level: str = "structure", names: dict[Pos, str] | None = None
) -> list[tuple[str, frozenset]]:
    out = []
    for mirror in (None, "x"):
        for turns in range(4):
            cells = {}
            for (x, y, z), state in blocks.items():
                pos = (-x, y, z) if mirror else (x, y, z)
                st = mirror_state(state, "x") if mirror else state
                name = names.get((x, y, z)) if names else None
                pos, st = rotate_offset(pos, turns), rotate_state(st, turns)
                key = state_text(st) if level == "exact" else _structure_key(st, name)
                if key is not None:
                    cells[pos] = key
            if not cells:
                out.append((f"{'mirror x, ' if mirror else ''}{turns} turns", frozenset()))
                continue
            low = [min(p[i] for p in cells) for i in range(3)]
            shifted = frozenset(
                ((p[0] - low[0], p[1] - low[1], p[2] - low[2]), k) for p, k in cells.items()
            )
            out.append((f"{'mirror x, ' if mirror else ''}{turns} turns", shifted))
    return out


def similarity(a: Build, b: Build, level: str = "structure") -> dict[str, Any]:
    """The best match of ``b``'s variants against ``a`` (as built)."""
    base = variants(a.blocks, level, a.names if level == "abstract" else None)[0][1]
    best: dict[str, Any] | None = None
    for name, cells in variants(b.blocks, level, b.names if level == "abstract" else None):
        common = len(base & cells)
        union = len(base | cells)
        score = common / union if union else 1.0
        if best is None or score > best["score"]:
            best = {
                "score": round(score, 4),
                "transform": name,
                "common": common,
                "only_a": len(base - cells),
                "only_b": len(cells - base),
            }
    assert best is not None
    return best


class Build:
    """A contraption's blocks and, for the abstract level, their simulator names."""

    def __init__(self, level: Any, roles: set[str] | None = None) -> None:
        blocks = contraption(level)
        if roles is not None:
            blocks = {p: s for p, s in blocks.items() if interactions.role(s) in roles}
        self.blocks = blocks
        self.names = {p: _abstract_name(level, p, s) for p, s in blocks.items()}


def load(name: str, roles: set[str] | None = None) -> Build:
    session = corpus.open_world(corpus.find(name))
    session.doc.seek_tick(0)
    return Build(session.doc.level, roles)


def _local_paths(a: dict[str, Any]) -> tuple[list[tuple], int]:
    way = a["doorway"]
    cells = way["cells"]
    along = 2 if way["normal"] == "x" else 0
    across = 0 if way["normal"] == "x" else 2
    low = min(c[along] for c in cells)
    bottom = min(c[1] for c in cells)
    width = max(c[along] for c in cells) - low
    paths = [
        tuple((t, (p[along] - low, p[1] - bottom, p[across] - way["plane"])) for t, p in b["path"])
        for b in a["door_blocks"]
    ]
    return paths, width


def behavior(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """How many door-block trajectories of ``b`` equal one of ``a`` (best of: as is,
    mirrored left-right, mirrored front-back, both)."""
    paths_a, _ = _local_paths(a)
    paths_b, width = _local_paths(b)
    base = sorted(paths_a)
    best: dict[str, Any] | None = None
    for mirror_u in (False, True):
        for mirror_w in (False, True):
            moved = sorted(
                tuple(
                    (t, (width - u if mirror_u else u, v, -w if mirror_w else w))
                    for t, (u, v, w) in path
                )
                for path in paths_b
            )
            same = sum(1 for path in moved if path in base)
            name = " + ".join(
                n
                for n, on in (("mirror left-right", mirror_u), ("mirror front-back", mirror_w))
                if on
            )
            if best is None or same > best["identical"]:
                best = {
                    "identical": same,
                    "of": (len(base), len(moved)),
                    "transform": name or "as is",
                }
    assert best is not None
    best["same_frames"] = (
        a["frames"] == b["frames"] or [r[::-1] for r in a["frames"]] == b["frames"]
    )
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worlds", nargs="*", help="two slugs (default: every pair)")
    parser.add_argument("--level", choices=LEVELS, default="abstract")
    parser.add_argument("--min", type=float, default=0.3, help="report pairs above this")
    args = parser.parse_args()
    if args.worlds:
        a, b = (load(w) for w in args.worlds)
        for level in LEVELS:
            print(level, similarity(a, b, level))
        from tools.doorlab import analysis

        found = [analysis.analyze(corpus.find(w)) for w in args.worlds]
        print("behavior", behavior(found[0], found[1]))
        return
    builds = {
        corpus.parse_name(p).slug: load(corpus.parse_name(p).slug) for p in corpus.world_files()
    }
    for x, y in combinations(builds, 2):
        result = similarity(builds[x], builds[y], args.level)
        if result["score"] >= args.min:
            print(
                f"{result['score']:.3f}  {x}  ~  {y}  ({result['transform']}; "
                f"{result['common']} common, {result['only_a']}/{result['only_b']} apart)"
            )


if __name__ == "__main__":
    main()
