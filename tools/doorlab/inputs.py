"""How a door tolerates its input's timing (``python -m tools.doorlab.inputs WORLD …``).

The world's timeline flips the input twice (close, open). Here the second flip comes
after every gap from 1 to ``--max`` ticks, and each run continues until it is quiet. A gap
is **clean** when the whole build ends in the same rest state as after the designed gap
(every block), **door ok** when only the doorway is back (the door looks right, but some
internal state differs), **stuck** otherwise. The designed run's rest state is the
reference, not the tick-0 build: some saved builds hold stale shapes (a note block's
instrument, a wire's connections) that the first neighbor update corrects.

The result per door: the smallest gap from which every longer gap is clean (the minimum
time between the two flips a user must leave), and the shorter gaps that fail or work.

``repeat`` runs the designed cycle again from the rest state the first one left and
compares the doorway frame by frame: a door that does not come back to its own start
(a block left behind) shows it here.
"""

from __future__ import annotations

import argparse
import copy
import json
from typing import Any

from tools.doorlab import canonical, corpus, interactions, replay

SETTLE = 120  # ticks after the second flip (the slowest door needs 60)


def _final(rec: replay.Recording) -> dict[Any, str]:
    final = dict(rec.start)
    for t in range(1, rec.end_tick + 1):
        for p, s in rec.changes.get(t, {}).items():
            if s == replay.AIR:
                final.pop(p, None)
            else:
                final[p] = s
    return final


def _with_gap(canon: dict[str, Any], gap: int) -> replay.Recording:
    variant = copy.deepcopy(canon)
    start = variant["timeline"]["actions"][0]["tick"]
    variant["timeline"]["actions"][1]["tick"] = start + gap
    variant["timeline"]["end_tick"] = start + gap + SETTLE
    return replay.record(canonical.rebuild(variant))


def _two_flips(canon: dict[str, Any]) -> bool:
    actions = canon["timeline"]["actions"]
    return len(actions) == 2 and actions[0]["pos"] == actions[1]["pos"]


def run(path: Any, max_gap: int = 40) -> dict[str, Any]:
    canon = canonical.from_file(path)
    actions = canon["timeline"]["actions"]
    if not _two_flips(canon):
        return {"world": corpus.parse_name(path).slug, "skipped": "not two flips of one input"}
    outputs = [tuple(p) for p in canon["annotations"]["sections"]["output"]["positions"]]
    cells = interactions.doorway(outputs).cells
    start = actions[0]["tick"]
    designed = actions[1]["tick"] - start
    reference = _final(_with_gap(canon, designed))
    results = []
    for gap in range(1, max_gap + 1):
        rec = _with_gap(canon, gap)
        end = rec.end_tick
        final = _final(rec)
        quiet = not any(rec.changes.get(t) for t in range(end - 10, end + 1))
        clean = quiet and final == reference
        door_back = replay.frames(rec, cells)[end] == replay.frames(rec, cells)[0]
        results.append(
            {
                "gap": gap,
                "result": "clean" if clean else "door ok" if door_back and quiet else "stuck",
            }
        )
    clean_from = None
    for r in reversed(results):
        if r["result"] != "clean":
            break
        clean_from = r["gap"]
    stale = sorted(
        p for p in set(reference) | set(rec.start) if reference.get(p) != rec.start.get(p)
    )
    return {
        "world": corpus.parse_name(path).slug,
        "designed_gap": designed,
        "rest_differs_from_build": [
            [*p, rec.start.get(p, replay.AIR), reference.get(p, replay.AIR)] for p in stale
        ],
        "clean_from": clean_from,
        "results": results,
        "line": "".join({"clean": "#", "door ok": "+", "stuck": "."}[r["result"]] for r in results),
    }


def repeat(path: Any) -> dict[str, Any]:
    """Run the designed cycle twice; compare the second cycle's doorway with the first."""
    canon = canonical.from_file(path)
    if not _two_flips(canon):
        return {"world": corpus.parse_name(path).slug, "skipped": "not two flips of one input"}
    actions = canon["timeline"]["actions"]
    start, second = actions[0]["tick"], actions[1]["tick"]
    period = second - start + SETTLE
    variant = copy.deepcopy(canon)
    for a in actions:
        again = copy.deepcopy(a)
        again["tick"] = a["tick"] + period
        variant["timeline"]["actions"].append(again)
    variant["timeline"]["end_tick"] = start + 2 * period
    rec = replay.record(canonical.rebuild(variant))
    outputs = [tuple(p) for p in canon["annotations"]["sections"]["output"]["positions"]]
    cells = interactions.doorway(outputs).cells
    frames = replay.frames(rec, cells)
    first = frames[start : start + period]
    again_ = frames[start + period : start + 2 * period]
    differ = next((i for i, (x, y) in enumerate(zip(first, again_, strict=True)) if x != y), None)
    rest1 = _final(replay.record(canonical.rebuild(_cycle(canon, period))))
    rest2 = _final(rec)
    return {
        "world": corpus.parse_name(path).slug,
        "period": period,
        "doorway_same": differ is None,
        "first_difference": None if differ is None else start + period + differ,
        "rest_same": rest1 == rest2,
        "rest_moved": sorted([*p] for p in set(rest1) | set(rest2) if rest1.get(p) != rest2.get(p)),
    }


def _cycle(canon: dict[str, Any], period: int) -> dict[str, Any]:
    variant = copy.deepcopy(canon)
    variant["timeline"]["end_tick"] = canon["timeline"]["actions"][0]["tick"] + period
    return variant


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worlds", nargs="+")
    parser.add_argument("--max", type=int, default=40)
    parser.add_argument("--json")
    parser.add_argument("--repeat", action="store_true", help="only the two-cycle test")
    args = parser.parse_args()
    out = []
    for name in args.worlds:
        if args.repeat:
            r = repeat(corpus.find(name))
            out.append(r)
            if "skipped" in r:
                print(f"{r['world']}: skipped ({r['skipped']})")
                continue
            doorway = "same" if r["doorway_same"] else f"differs from {r['first_difference']}"
            rest = "same" if r["rest_same"] else f"differs at {r['rest_moved'][:4]}"
            print(f"{r['world']}: second cycle doorway {doorway}, rest state {rest}")
            continue
        r = run(corpus.find(name), args.max)
        out.append(r)
        if "skipped" in r:
            print(f"{r['world']}: skipped ({r['skipped']})")
            continue
        print(
            f"{r['world']}: designed gap {r['designed_gap']}, clean from {r['clean_from']}: "
            f"{r['line']}"
        )
    if args.json:
        with open(args.json, "w") as handle:
            json.dump(out, handle, indent=1)


if __name__ == "__main__":
    main()
