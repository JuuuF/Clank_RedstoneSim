"""The door lab's whole pipeline on the project's own 3x3 flush door (``door_3x3``).

The dataset's designs are third-party and stay uncommitted; ``door_3x3`` was designed in
this repository (Q18, Q21), so its analysis, experiments and derived worlds can be kept
here. Steps (each one a tool in ``tools/doorlab``):

1. round trip: canonical form → save → canonical form, and the replay of both;
2. analysis: doorway frames, groups, piston roles, power access;
3. mechanism / controller split: the contract and the stripped door;
4. input timing: every gap 1..70 between the two lever pulls; the two-cycle test;
5. symmetry: the 8 orientations and 4 translations;
6. ablation of every block and the combined trim;
7. comparison with Mumbo Jumbo's 3x3 flush door when the dataset is present.

    PYTHONPATH=src python experiments/doors/door_3x3/annotate.py
    PYTHONPATH=src python experiments/doors/door_3x3/lab.py

Writes ``results.json`` and the derived worlds (``*-mechanism``, ``*-trimmed``) next to
this file.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from tools.doorlab import (
    ablation,
    analysis,
    canonical,
    compare,
    corpus,
    inputs,
    mechanism,
    replay,
    symmetry,
)

HERE = Path(__file__).resolve().parent
WORLD = HERE / "3x3 flush door by redsim.redsim.json"


def main() -> None:
    out: dict = {"world": str(WORLD.name)}
    started = time.perf_counter()

    canon = canonical.from_file(WORLD)
    again = canonical.from_file(WORLD) | {}
    rec_a = replay.record(canonical.rebuild(canon))
    rec_b = replay.record(canonical.rebuild(again))
    out["round_trip"] = {
        "canonical_equal": canonical.dumps(canon) == canonical.dumps(again),
        "replay_equal": rec_a.changes == rec_b.changes,
    }

    a = analysis.analyze(WORLD)
    cells = [tuple(c) for c in a["doorway"]["cells"]]
    markers = {int(t): n for t, n in canon["annotations"]["markers"].items()}
    out["analysis"] = {
        "roles": a["piston_roles"],
        "power_access": a["power_access"],
        "closed": a["closed_ticks"],
        "open": a["open_ticks"],
        "groups": [
            {k: g[k] for k in ("exit", "blocks", "pistons", "closed_to_open")} for g in a["groups"]
        ],
        "markers_ok": all(
            c["ok"] for c in replay.check_markers(rec_a, cells, markers) if c["checked"]
        ),
    }
    print("analysis", out["analysis"]["roles"], "markers ok", out["analysis"]["markers_ok"])

    m = mechanism.check(WORLD)
    stripped = m.pop("stripped")
    with (HERE / "3x3 flush door by redsim-mechanism.redsim.json").open("w") as handle:
        json.dump(canonical.to_save(stripped), handle)
    out["mechanism"] = m
    print("mechanism", m["pulses"], "pulses, identical:", m["same_frames"], m["first_difference"])

    timing = inputs.run(WORLD, 70)
    out["inputs"] = timing
    print("inputs clean from", timing["clean_from"], timing["line"])
    out["repeat"] = inputs.repeat(WORLD)
    print("repeat", out["repeat"]["doorway_same"], out["repeat"]["rest_same"])

    sym = symmetry.check(WORLD, [(1, 0), (0, 1), (-1, 0), (0, -1)])
    out["symmetry"] = {k: v for k, v in sym.items() if k != "world"}
    print("symmetry all identical:", sym["all_identical"])

    abl = ablation.run(WORLD)
    trim = ablation.trim(WORLD, abl["results"])
    trimmed = trim.pop("trimmed")
    with (HERE / "3x3 flush door by redsim-trimmed.redsim.json").open("w") as handle:
        json.dump(canonical.to_save(trimmed), handle)
    out["ablation"] = abl
    out["trim"] = trim
    print("ablation", abl["totals"], "trim", trim["blocks_before"], "->", trim["blocks_after"])

    try:
        mumbo_path = corpus.find("mumbo")
    except LookupError:
        mumbo_path = None
    if mumbo_path is not None:
        ours = compare.Build(corpus.open_world(WORLD).doc.level)
        session = corpus.open_world(mumbo_path)
        session.doc.seek_tick(0)
        theirs = compare.Build(session.doc.level)
        out["compare_mumbo"] = {
            level: compare.similarity(ours, theirs, level)["score"] for level in compare.LEVELS
        }
        mumbo = analysis.analyze(mumbo_path)
        out["compare_mumbo"]["mechanism"] = compare.similarity(
            compare.Build(corpus.open_world(WORLD).doc.level, {"piston"}),
            compare.Build(session.doc.level, {"piston"}),
            "abstract",
        )["score"]
        out["compare_mumbo"]["behavior"] = compare.behavior(mumbo, a)
        out["compare_mumbo"]["open_ticks"] = {
            "ours": a["open_ticks"],
            "mumbo": mumbo["open_ticks"],
        }
        print("compare", out["compare_mumbo"])

    out["seconds"] = round(time.perf_counter() - started, 1)
    with (HERE / "results.json").open("w") as handle:
        json.dump(out, handle, indent=1, default=list)
    print("done in", out["seconds"], "s")


if __name__ == "__main__":
    main()
