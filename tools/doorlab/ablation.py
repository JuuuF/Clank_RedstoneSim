"""Controlled modifications, one at a time (``python -m tools.doorlab.ablation WORLD``).

For every block of a door above the floor, the world is changed in one way and replayed
with its own timeline:

- ``remove``: the block becomes air (its block entity goes too);
- ``glass``: a solid block that conducts becomes glass (same shape for pistons and
  light, but it carries no power), to find the blocks that carry signals;
- ``delay``: a repeater gets each other delay (1-4);
- ``turn`` (``--turn``, run on its own): a retracted piston gets each other facing.

Each variant is classified against the original replay:

- **breaks**: the world's markers no longer hold (the door does not close or open);
- **timing**: the door still works, but its doorway frames differ (it moves differently
  or at other ticks);
- **internal**: the doorway is unchanged but other blocks change differently;
- **inert**: every block at every tick as before (decoration, or redundant).

Variants that break or change timing are the design's constraints; inert blocks are
slack (the build could be smaller there). A few blocks are needed only to hold others up
(a wire's block, a torch's wall): removing them breaks the part they carry.

``trim`` (``--trim``) removes the blocks whose removal was inert one by one *together*,
keeping each only if the door still replays inert with all earlier removals: the
smallest build this one-block search finds with exactly the same behavior.

``glass_roles`` (``--predict``, with ``--out`` holding the results) says what the
interaction model expects of each ``glass`` variant before it is run: a conductor that
is powered at some tick of the designed run may matter; one that is never powered
matters only as a wire cutter (wire under it and beside it) or as an immovable stopper;
any other is harmless. It prints how the measured results fall into these roles.
"""

from __future__ import annotations

import argparse
import copy
import json
import time
from collections import Counter
from typing import Any

from redsim.core.direction import HORIZONTAL, Direction
from redsim.core.pos import offset
from redsim.world import blocks
from redsim.world.properties import FACING
from tools.doorlab import canonical, corpus, interactions, replay, transform

Pos = tuple[int, int, int]
GLASS = "minecraft:glass"


def _variant(canon: dict[str, Any], pos: Pos, state: str | None) -> dict[str, Any]:
    out = copy.deepcopy(canon)
    blocks_out = [b for b in out["blocks"] if tuple(b[:3]) != pos]
    if state is not None:
        blocks_out.append([*pos, state])
    out["blocks"] = sorted(blocks_out, key=lambda b: (b[1], b[2], b[0]))
    # Drop the block entity of a removed / replaced block; tickers refer to entities by
    # index, so keep the list and mark it unmapped and removed.
    for entry in out["block_entities"]:
        if tuple(entry["pos"]) == pos:
            entry["mapped"] = False
            entry["removed"] = True
    runtime = out["engine_runtime"]
    key = ",".join(map(str, pos))
    runtime["tickers_by_pos"] = {
        k: v for k, v in runtime.get("tickers_by_pos", {}).items() if k != key
    }
    return out


def _classify(
    rec: replay.Recording, base: replay.Recording, cells: list[Pos], markers: dict[int, str]
) -> str:
    checks = [c for c in replay.check_markers(rec, cells, markers) if c["checked"]]
    if not all(c["ok"] for c in checks):
        return "breaks"
    if replay.frames(rec, cells) != replay.frames(base, cells):
        return "timing"
    if rec.changes != base.changes:
        return "internal"
    return "inert"


def variants_of(canon: dict[str, Any], floor_y: int) -> list[tuple[str, Pos, str | None]]:
    out: list[tuple[str, Pos, str | None]] = []
    for x, y, z, state in canon["blocks"]:
        if y <= floor_y or state.endswith(":air"):
            continue
        pos = (x, y, z)
        name = interactions.block_id(state)
        # A head is part of its piston: removing it alone leaves a headless extended
        # piston (inert when the piston never retracts), not a smaller door.
        if name != "piston_head":
            out.append(("remove", pos, None))
        if interactions.role(state) == "structure":
            st = blocks.parse_state(state)
            if st.block.id != GLASS and _conducts(st):
                out.append(("glass", pos, GLASS))
        if name == "repeater":
            current = blocks.parse_state(state)
            for delay in range(1, 5):
                text = state.replace(f"delay={_delay(current)}", f"delay={delay}")
                if text != state:
                    out.append((f"delay {delay}", pos, text))
    return out


def _delay(state: Any) -> int:
    for prop in state.block.properties:
        if prop.name == "delay":
            return int(state.get(prop))
    return 1


def _conducts(state: Any) -> bool:
    from redsim.sim.level import Level

    level = Level()
    level.blocks[(0, 0, 0)] = state
    return bool(state.is_redstone_conductor(level, (0, 0, 0)))


def turn_variants(canon: dict[str, Any], floor_y: int) -> list[tuple[str, Pos, str | None]]:
    """Each retracted piston above the floor set to each of its other five facings."""
    out: list[tuple[str, Pos, str | None]] = []
    for x, y, z, state in canon["blocks"]:
        if y <= floor_y or interactions.block_id(state) not in ("piston", "sticky_piston"):
            continue
        if "extended=true" in state:
            continue
        current = blocks.parse_state(state).get(FACING)
        for d in Direction:
            if d is not current:
                out.append((f"turn {d.serialized}", (x, y, z), state.replace(
                    f"facing={current.serialized}", f"facing={d.serialized}"
                )))  # fmt: skip
    return out


def run(path: Any, limit: int | None = None, turns: bool = False) -> dict[str, Any]:
    """Every variant (``turns``: only the piston turns) replayed and classified."""
    started = time.perf_counter()
    canon = canonical.from_file(path)
    floor_y = transform.floor_of(canon)
    base = replay.record(canonical.rebuild(canon))
    outputs = [tuple(p) for p in canon["annotations"]["sections"]["output"]["positions"]]
    cells = interactions.doorway(outputs).cells
    cells += [c for c in outputs if c not in cells]
    markers = {int(t): n for t, n in canon["annotations"].get("markers", {}).items()}
    states = {tuple(b[:3]): b[3] for b in canon["blocks"]}
    results = []
    todo = (turn_variants if turns else variants_of)(canon, floor_y)[:limit]
    for kind, pos, state in todo:
        rec = replay.record(canonical.rebuild(_variant(canon, pos, state)))
        results.append(
            {
                "change": kind,
                "pos": list(pos),
                "block": replay.short(states[pos]),
                "role": interactions.role(states[pos]),
                "door_cell": pos in outputs,
                "result": _classify(rec, base, cells, markers),
            }
        )
    summary: dict[str, dict[str, int]] = {}
    for r in results:
        key = f"{r['change'].split()[0]} {r['role']}"
        summary.setdefault(key, Counter())[r["result"]] += 1  # type: ignore[arg-type]
    return {
        "world": corpus.parse_name(path).slug,
        "variants": len(results),
        "results": results,
        "summary": {k: dict(v) for k, v in sorted(summary.items())},
        "totals": dict(Counter(r["result"] for r in results)),
        "seconds": round(time.perf_counter() - started, 1),
    }


def trim(path: Any, results: list[dict[str, Any]]) -> dict[str, Any]:
    """Remove every individually inert block, greedily, checking the combination; a block
    that another one stands on stays (the trimmed door must be buildable)."""
    canon = canonical.from_file(path)
    base = replay.record(canonical.rebuild(canon))
    outputs = [tuple(p) for p in canon["annotations"]["sections"]["output"]["positions"]]
    cells = interactions.doorway(outputs).cells
    markers = {int(t): n for t, n in canon["annotations"].get("markers", {}).items()}
    candidates = [
        tuple(r["pos"]) for r in results if r["change"] == "remove" and r["result"] == "inert"
    ]
    floor_y = transform.floor_of(canon)

    def contraption(c: dict[str, Any]) -> list[Pos]:
        return [tuple(b[:3]) for b in c["blocks"] if b[1] > floor_y and not b[3].endswith(":air")]

    def volume(c: dict[str, Any]) -> int:
        cells_ = contraption(c)
        size = 1
        for axis in range(3):
            values = [p[axis] for p in cells_]
            size *= max(values) - min(values) + 1
        return size

    # A removal must leave a buildable door: nothing may lose the block it stands on
    # (a button, wire or torch stays in place only because no update reaches it).
    session = corpus.open_world(path)
    session.doc.seek_tick(0)
    level = session.doc.level

    def needed_below(pos: Pos) -> bool:
        saved = level.blocks.pop(pos, None)
        try:
            return any(
                not s.is_air and not s.can_survive(level, n)
                for n in (offset(pos, d) for d in Direction)
                for s in (level.get_block_state(n),)
            )
        finally:
            if saved is not None:
                level.blocks[pos] = saved

    current = canon
    removed: list[Pos] = []
    kept: list[Pos] = []
    support: list[Pos] = []
    for pos in candidates:
        if needed_below(pos):
            support.append(pos)
            continue
        trial = _variant(current, pos, None)
        rec = replay.record(canonical.rebuild(trial))
        if _classify(rec, base, cells, markers) == "inert":
            current, removed = trial, [*removed, pos]
            level.blocks.pop(pos, None)
        else:
            kept.append(pos)
    return {
        "blocks_before": len(contraption(canon)),
        "blocks_after": len(contraption(current)),
        "volume_before": volume(canon),
        "volume_after": volume(current),
        "removed": [list(p) for p in removed],
        "kept_after_all": [list(p) for p in kept],
        "kept_as_support": [list(p) for p in support],
        "trimmed": current,
    }


IMMOVABLE = ("minecraft:obsidian", "minecraft:crying_obsidian", "minecraft:bedrock")


def glass_roles(path: Any, positions: list[Pos]) -> dict[Pos, str]:
    """Layer 2's role of each conductor for the ``glass`` change: ``powered`` (receives
    power at some tick of the designed run), ``cutter``, ``immovable`` or ``none``."""
    doc = canonical.rebuild(canonical.from_file(path))
    doc.seek_tick(doc.end_tick)
    powered: set[Pos] = set()
    for t in range(doc.end_tick + 1):
        doc.seek_tick(t)
        powered |= {p for p in positions if doc.level.has_neighbor_signal(p)}
    doc.seek_tick(0)
    level = doc.level

    def wire(p: Pos) -> bool:
        return level.get_block_state(p).block.id == "minecraft:redstone_wire"

    def role(p: Pos) -> str:
        if p in powered:
            return "powered"
        if wire(offset(p, Direction.DOWN)) and any(wire(offset(p, d)) for d in HORIZONTAL):
            return "cutter"
        return "immovable" if level.get_block_state(p).block.id in IMMOVABLE else "none"

    return {p: role(p) for p in positions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worlds", nargs="+")
    parser.add_argument("--out", help="folder for the JSON results")
    parser.add_argument("--trim", action="store_true", help="also remove all inert blocks together")
    parser.add_argument(
        "--predict", action="store_true", help="with --out: score layer 2's glass roles"
    )
    parser.add_argument(
        "--turn", action="store_true", help="only the piston turns (written as SLUG-turn.json)"
    )
    args = parser.parse_args()
    for name in args.worlds:
        path = corpus.find(name)
        if args.predict:
            with open(f"{args.out}/{corpus.parse_name(path).slug}.json") as handle:
                saved = json.load(handle)["results"]
            glass = {tuple(r["pos"]): r["result"] for r in saved if r["change"] == "glass"}
            roles = glass_roles(path, list(glass))
            score = Counter((roles[p], res in ("breaks", "timing")) for p, res in glass.items())
            print(corpus.parse_name(path).slug + ": " + ", ".join(
                f"{k} {score[(k, True)]} of {score[(k, True)] + score[(k, False)]} break"
                for k in ("powered", "cutter", "immovable", "none")
            ))  # fmt: skip
            continue
        r = run(path, turns=args.turn)
        print(f"{r['world']}: {r['variants']} variants in {r['seconds']}s: {r['totals']}")
        if args.turn:
            if args.out:
                with open(f"{args.out}/{r['world']}-turn.json", "w") as handle:
                    json.dump(r, handle, indent=1)
            continue
        for key, counts in r["summary"].items():
            print(f"  {key}: {counts}")
        if args.trim:
            t = trim(path, r["results"])
            print(
                f"  trim: blocks {t['blocks_before']} -> {t['blocks_after']}, box volume "
                f"{t['volume_before']} -> {t['volume_after']}, "
                f"{len(t['kept_after_all'])} inert alone but needed together, "
                f"{len(t['kept_as_support'])} kept as a support"
            )
            trimmed = t.pop("trimmed")
            r["trim"] = t
            if args.out:
                with open(f"{args.out}/{r['world']}-trimmed.redsim.json", "w") as handle:
                    json.dump(canonical.to_save(trimmed), handle)
        if args.out:
            with open(f"{args.out}/{r['world']}.json", "w") as handle:
                json.dump(r, handle, indent=1)


if __name__ == "__main__":
    main()
