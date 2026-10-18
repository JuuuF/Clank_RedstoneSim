"""A door split into its mechanism and its controller (``python -m tools.doorlab.mechanism``).

The **mechanism** is what moves the door: the pistons that move door blocks or other
pistons (roles "door" and "stack" in ``analysis``), the door blocks, and the plain blocks
around them. The **controller** is everything that decides *when*: wire, repeaters,
comparators, observers, torches, the lever, droppers and hoppers used as timers, and the
pistons that only move controller parts (power switches, sliders, helpers).

``extract`` turns a door's replay into the controller's **contract**: for each mechanism
piston, the pulses it receives (start tick, length), read from its block events: an
extension at tick e and the next retract at tick r is a pulse that switches on between
tick e−1 and e and lasts r−e ticks (``pulse POS at e−1 for r−e``: the piston starts at e
and retracts at r, as R-026 measured). A pulse of 1 tick on a sticky piston that is still
pushing is a spit. A piston that is extended and powered in the build and retracts at r
first is a pulse from the start (start 0, length r).

``strip`` removes the controller from the build and puts the contract on the timeline as
editor pulses. If the stripped door moves exactly like the original (the same doorway
frames and door-block trajectories), the contract is complete: any controller that gives
these pulses runs this mechanism. That is the guide's "piston layout first, then the
sequence, then the wiring" as a test.
"""

from __future__ import annotations

import argparse
import copy
import json
from typing import Any

from tools.doorlab import analysis, canonical, corpus, interactions, replay

Pos = tuple[int, int, int]
MECHANISM_ROLES = {"door", "stack"}
CONTROLLER_ROLES = (
    interactions.LOGIC_ROLES
    | interactions.INPUT_ROLES
    | {"dropper", "dispenser", "hopper", "analog", "crafter", "trapdoor", "door", "gate"}
)


def extract(a: dict[str, Any]) -> list[dict[str, Any]]:
    """The contract: pulses per mechanism piston, in the order the original's events ran."""
    mechanism = {tuple(p["pos"]) for p in a["pistons"] if p["role"] in MECHANISM_ROLES}
    # Pistons that were moved: their events happen at other positions. Follow the
    # positions where mechanism pistons were at their events (stacks lift door pistons).
    pulses = []
    open_: dict[Pos, dict[str, Any]] = {}
    seen: set[Pos] = set()
    for e in a["events"]:
        pos = tuple(e["piston"])
        moved_here = any(
            tuple(m["to"]) == pos
            for ev in a["events"]
            for m in ev["moved"]
            if ev["tick"] <= e["tick"] and "piston[" in m["state"]
        )
        if pos not in mechanism and not moved_here:
            continue
        if e["outcome"] == "skipped":
            continue
        first = pos not in seen
        seen.add(pos)
        if e["kind"] == "extend":
            open_[pos] = {"pos": list(pos), "start": e["tick"], "order": (e["tick"], e["order"])}
        elif pos in open_:
            p = open_.pop(pos)
            p["length"] = e["tick"] - p["start"]
            pulses.append(p)
        elif first:
            # Extended and powered in the build: on from the start until this retract.
            pulses.append(
                {"pos": list(pos), "start": 0, "length": e["tick"], "order": (0, e["order"])}
            )
    for p in open_.values():
        p["length"] = None  # held to the end
        pulses.append(p)
    return sorted(pulses, key=lambda p: p["order"])


def order_constraints(a: dict[str, Any]) -> list[dict[str, Any]]:
    """Ticks where a mechanism piston retracts *before* another one extends in the same
    tick. Editor pulses (and any input between ticks) cannot give that order: a pulse that
    starts acts at the end of the tick before, a pulse that ends at the start of the tick,
    so in one tick every pulse start is queued before every pulse end. Only components
    that act in the scheduled-tick phase (repeaters, observers, torches, comparators) can
    order a retract before an extension."""
    mechanism = {tuple(p["pos"]) for p in a["pistons"] if p["role"] in MECHANISM_ROLES}
    out = []
    by_tick: dict[int, list[dict[str, Any]]] = {}
    for e in a["events"]:
        if e["outcome"] != "skipped" and tuple(e["piston"]) in mechanism:
            by_tick.setdefault(e["tick"], []).append(e)
    for tick, events in sorted(by_tick.items()):
        events.sort(key=lambda e: e["order"])
        for i, first in enumerate(events):
            if first["kind"] == "extend":
                continue
            for later in events[i + 1 :]:
                if later["kind"] == "extend" and later["piston"] != first["piston"]:
                    out.append(
                        {"tick": tick, "retract": first["piston"], "then_extend": later["piston"]}
                    )
    return out


def strip(canon: dict[str, Any], a: dict[str, Any], pulses: list[dict[str, Any]]) -> dict[str, Any]:
    """The build without its controller, driven by the contract's pulses."""
    out = copy.deepcopy(canon)
    keep_pistons = {tuple(p["pos"]) for p in a["pistons"] if p["role"] in MECHANISM_ROLES}
    drop: set[Pos] = set()
    for x, y, z, state in out["blocks"]:
        pos = (x, y, z)
        role = interactions.role(state)
        if role in CONTROLLER_ROLES:
            drop.add(pos)
        elif role == "piston" and pos not in keep_pistons:
            drop.add(pos)
            if "extended=true" in state:
                facing = state.split("facing=")[1].split(",")[0].split("]")[0]
                step = {
                    "north": (0, 0, -1),
                    "south": (0, 0, 1),
                    "east": (1, 0, 0),
                    "west": (-1, 0, 0),
                    "up": (0, 1, 0),
                    "down": (0, -1, 0),
                }[facing]
                drop.add((x + step[0], y + step[1], z + step[2]))
    out["blocks"] = [b for b in out["blocks"] if tuple(b[:3]) not in drop]
    for entry in out["block_entities"]:
        if tuple(entry["pos"]) in drop:
            entry["mapped"] = False
            entry["removed"] = True
    runtime = out["engine_runtime"]
    runtime["tickers_by_pos"] = {
        k: v
        for k, v in runtime.get("tickers_by_pos", {}).items()
        if tuple(int(c) for c in k.split(",")) not in drop
    }
    runtime["scheduled_ticks"] = [
        t for t in runtime.get("scheduled_ticks", []) if tuple(t["pos"]) not in drop
    ]
    end = out["timeline"]["end_tick"]
    actions = []
    for p in pulses:
        # A pulse at T for N ticks extends the piston at T + 1 and retracts it at
        # T + N + 1 (R-026). Pulses start at tick 1 at the earliest: a piston extended in
        # the build (start 0) stays out until its pulse ends, one extending at tick 1
        # extends a tick late.
        start = max(1, p["start"] - 1)
        retract = p["start"] + p["length"] if p["length"] is not None else end + 1
        length = max(1, retract - start - 1)
        actions.append(
            {
                "tick": start,
                "kind": "power_pulse",
                "pos": p["pos"],
                "state": None,
                "flags": 3,
                "payload": {"strength": 15, "ticks": length},
                "label": "power pulse",
            }
        )
    out["timeline"]["actions"] = actions
    return out


def check(path: Any) -> dict[str, Any]:
    canon = canonical.from_file(path)
    a = analysis.analyze(path)
    pulses = extract(a)
    stripped = strip(canon, a, pulses)
    rec = replay.record(canonical.rebuild(stripped))
    cells = [tuple(c) for c in a["doorway"]["cells"]]
    frames = replay.frames(rec, cells)
    same = frames == a["frames"]
    first = next(
        (t for t, (x, y) in enumerate(zip(frames, a["frames"], strict=False)) if x != y), None
    )
    kept = len(stripped["blocks"])
    return {
        "world": a["world"],
        "order_constraints": order_constraints(a),
        "pulses": len(pulses),
        "mechanism_pistons": sum(1 for p in a["pistons"] if p["role"] in MECHANISM_ROLES),
        "blocks_before": len(canon["blocks"]),
        "blocks_after": kept,
        "same_frames": same,
        "first_difference": first,
        "contract": [{"pos": p["pos"], "start": p["start"], "length": p["length"]} for p in pulses],
        "stripped": stripped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worlds", nargs="+")
    parser.add_argument("--save", help="folder: write each stripped world there")
    args = parser.parse_args()
    for name in args.worlds:
        r = check(corpus.find(name))
        ticks = sorted({c["tick"] for c in r["order_constraints"]})
        print(
            f"{r['world']}: {r['mechanism_pistons']} mechanism pistons, {r['pulses']} "
            f"pulses, retract-before-extend ticks {ticks or 'none'}; doorway "
            f"{'IDENTICAL' if r['same_frames'] else 'differs from tick '}"
            f"{'' if r['same_frames'] else r['first_difference']}"
        )
        if args.save:
            path = f"{args.save}/{r['world']}-mechanism.redsim.json"
            with open(path, "w") as handle:
                json.dump(canonical.to_save(r["stripped"]), handle)


if __name__ == "__main__":
    main()
