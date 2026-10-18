"""Is a contraption direction-independent? (``python -m tools.doorlab.symmetry [WORLD …]``)

Minecraft's redstone is not symmetric: neighbor updates go west, east, down, up, north,
south; wire updates spread in a fixed order; quasi-connectivity looks up only. So the same
contraption turned or mirrored can behave differently ("directional" or "locational"
designs). This experiment builds all eight horizontal orientations of a world
(``transform``), replays each, and compares every block change of every tick with the
original's, turned the same way:

- **identical**: every tick's changes match (the design is independent of direction);
- otherwise the first tick that differs and how many ticks differ, and whether the
  door still works (its own markers hold in that orientation).
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from tools.doorlab import canonical, corpus, interactions, replay, transform

ORIENTATIONS = [(t, m) for m in (False, True) for t in range(4)][1:]


def _turned_changes(
    rec: replay.Recording, sym: transform.Symmetry, floor_y: int
) -> dict[int, dict[tuple[int, int, int], str]]:
    out = {}
    for tick, row in rec.changes.items():
        out[tick] = {
            (p if p[1] <= floor_y else sym.pos(p)): (
                s if p[1] <= floor_y or s == replay.AIR else replay.short(sym.state(s))
            )
            for p, s in row.items()
        }
    return out


def check(path: Any, shifts: list[tuple[int, int]] | None = None) -> dict[str, Any]:
    """All seven other orientations; with ``shifts``, the unturned world translated by
    each (dx, dz) instead (the floor moves along)."""
    started = time.perf_counter()
    result = check_canonical(canonical.from_file(path), shifts)
    result["world"] = corpus.parse_name(path).slug
    result["seconds"] = round(time.perf_counter() - started, 1)
    return result


def check_canonical(
    canon: dict[str, Any], shifts: list[tuple[int, int]] | None = None
) -> dict[str, Any]:
    """``check`` on a canonical world (layer 1)."""
    original = replay.record(canonical.rebuild(canon))
    markers = {int(t): n for t, n in canon["annotations"].get("markers", {}).items()}
    results = []
    cases = [(0, False, s) for s in shifts] if shifts else [(t, m, (0, 0)) for t, m in ORIENTATIONS]
    for turns, mirror, shift in cases:
        turned, sym = transform.transform(canon, turns, mirror, shift)
        floor_y = -(10**9) if any(shift) else transform.floor_of(canon)
        rec = replay.record(canonical.rebuild(turned))
        expected = _turned_changes(original, sym, floor_y)
        differing = []
        cells = 0
        for tick in range(1, rec.end_tick + 1):
            want, got = expected.get(tick, {}), rec.changes.get(tick, {})
            if want != got:
                differing.append(tick)
                cells += len(set(want.items()) ^ set(got.items()))
        outputs = [
            tuple(p)
            for p in turned["annotations"]
            .get("sections", {})
            .get("output", {})
            .get("positions", [])
        ]
        way = interactions.doorway(outputs)
        checks = [c for c in replay.check_markers(rec, way.cells, markers) if c["checked"]]
        results.append(
            {
                "orientation": sym.name,
                "identical": not differing,
                "first_difference": differing[0] if differing else None,
                "ticks_differing": len(differing),
                "cells_differing": cells,
                "markers_ok": all(c["ok"] for c in checks) if checks else None,
            }
        )
    return {"orientations": results, "all_identical": all(r["identical"] for r in results)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worlds", nargs="*", help="slugs (default: the whole dataset)")
    parser.add_argument("--json", help="write the results here")
    parser.add_argument(
        "--shift", nargs="*", default=None, help="translations DX,DZ instead of the orientations"
    )
    args = parser.parse_args()
    paths = [corpus.find(w) for w in args.worlds] or corpus.world_files()
    shifts = [tuple(int(v) for v in s.split(",")) for s in args.shift] if args.shift else None
    out = []
    for path in paths:
        r = check(path, shifts)
        out.append(r)
        summary = ", ".join(
            f"{o['orientation']}: "
            + (
                "same"
                if o["identical"]
                else f"differs from {o['first_difference']} "
                f"({o['ticks_differing']} ticks), door "
                f"{'works' if o['markers_ok'] else 'FAILS'}"
            )
            for o in r["orientations"]
        )
        print(f"{r['world']} ({r['seconds']}s): {summary}")
    if args.json:
        with open(args.json, "w") as handle:
            json.dump(out, handle, indent=1)


if __name__ == "__main__":
    main()
