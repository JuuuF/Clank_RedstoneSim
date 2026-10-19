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

``recover`` uses the input once or twice more after each gap that did not end clean:
does using the door normally undo the jam?

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


def press_ticks(canon: dict[str, Any]) -> int:
    """How long the input stays on after a use if it is a button (0 for a lever): a
    second use within that time does nothing (``ButtonBlock.useWithoutItem``)."""
    from redsim.world import blocks
    from redsim.world.blocks.attached import ButtonBlock

    pos = tuple(canon["timeline"]["actions"][0]["pos"])
    text = next((b[3] for b in canon["blocks"] if tuple(b[:3]) == pos), None)
    block = blocks.parse_state(text).block if text else None
    return block.ticks_to_stay_pressed if isinstance(block, ButtonBlock) else 0


def label_ignored(result: dict[str, Any], press: int) -> dict[str, Any]:
    """Mark the gaps at which the second use comes while the button is still pressed:
    it is no input at all (``ignored``, ``-`` in the line), whatever the door does."""
    for r in result["results"]:
        if r["gap"] < press and r["result"] != "clean":
            r["result"] = "ignored"
    result["press_ticks"] = press
    chars = {"clean": "#", "door ok": "+", "stuck": ".", "ignored": "-"}
    result["line"] = "".join(chars[r["result"]] for r in result["results"])
    return result


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
    return label_ignored(
        {
            "world": corpus.parse_name(path).slug,
            "designed_gap": designed,
            "rest_differs_from_build": [
                [*p, rec.start.get(p, replay.AIR), reference.get(p, replay.AIR)] for p in stale
            ],
            "clean_from": clean_from,
            "results": results,
            "line": "".join(
                {"clean": "#", "door ok": "+", "stuck": "."}[r["result"]] for r in results
            ),
        },
        press_ticks(canon),
    )


def recover(path: Any, result: dict[str, Any]) -> dict[str, Any]:
    """After each gap that did not end clean, use the input once or twice more.

    A gap **recovers** when the whole build (the input included) then ends in one of
    the door's normal rest states: those after 1 to 4 inputs that each wait until the
    door is quiet (a door can alternate between two, Nile's seamless door). One input
    can be enough: a button door's controller keeps its own state, which a bad gap can
    leave out of step with the door. It **works again** when the doorway is in a normal
    rest frame although some other block stays off. Adds ``recovers`` (1 or 2, the
    inputs needed, or None) and ``works_again`` to the gap's entry and
    ``recover_line`` to ``result``: ``#`` clean, ``-`` ignored (a button still pressed),
    ``1`` / ``2`` recovers after that many inputs, ``w`` works again, ``x`` the doorway
    is still wrong.
    """
    canon = canonical.from_file(path)
    actions = canon["timeline"]["actions"]
    start = actions[0]["tick"]
    outputs = [tuple(p) for p in canon["annotations"]["sections"]["output"]["positions"]]
    cells = interactions.doorway(outputs).cells

    def run(ticks: list[int]) -> replay.Recording:
        variant = copy.deepcopy(canon)
        variant["timeline"]["actions"] = [
            {**copy.deepcopy(actions[i % 2]), "tick": t} for i, t in enumerate(ticks)
        ]
        variant["timeline"]["end_tick"] = ticks[-1] + SETTLE
        return replay.record(canonical.rebuild(variant))

    normal_runs = [run([start + SETTLE * i for i in range(n)]) for n in range(1, 5)]
    normal = [_final(rec) for rec in normal_runs]
    frames = {replay.frames(rec, cells)[-1] for rec in normal_runs}
    for r in result["results"]:
        if r["result"] in ("clean", "ignored"):
            continue
        r["recovers"], r["works_again"] = None, False
        bad = [start, start + r["gap"]]
        for extra in (1, 2):
            rec = run(bad + [bad[-1] + SETTLE * k for k in range(1, extra + 1)])
            if _final(rec) in normal:
                r["recovers"] = extra
                break
            r["works_again"] = r["works_again"] or replay.frames(rec, cells)[-1] in frames
    result["recover_line"] = "".join(
        "#"
        if r["result"] == "clean"
        else "-"
        if r["result"] == "ignored"
        else str(r["recovers"])
        if r["recovers"]
        else "w"
        if r["works_again"]
        else "x"
        for r in result["results"]
    )
    return result


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
    parser.add_argument("--out", help="folder: one JSON file per world, written as it is done")
    parser.add_argument("--repeat", action="store_true", help="only the two-cycle test")
    parser.add_argument(
        "--explain", action="store_true", help="why the last bad gap (safe gap - 1) is too short"
    )
    parser.add_argument("--gap", type=int, help="with --explain / --jam: this gap")
    parser.add_argument(
        "--jam", action="store_true", help="with --gap: the door blocks a lasting jam leaves off"
    )
    parser.add_argument(
        "--repair", action="store_true", help="with --gap: second-cycle gaps that undo the jam"
    )
    parser.add_argument(
        "--recover",
        action="store_true",
        help="with --out: add the recovery test to the saved sweeps (1 or 2 more inputs)",
    )
    args = parser.parse_args()
    out = []
    for name in args.worlds:
        if args.recover:
            path = corpus.find(name)
            saved = f"{args.out}/{corpus.parse_name(path).slug}.json"
            with open(saved) as handle:
                r = recover(path, json.load(handle))
            with open(saved, "w") as handle:
                json.dump(r, handle, indent=1)
            print(f"{r['world']}: {r['recover_line']}")
            continue
        if args.repair:
            r = repair(corpus.find(name), args.gap, args.max)
            out.append(r)
            print(
                f"{r['world']}: jam at gap {r['gap']}: repaired by a second cycle with gap "
                f"{r['repairing_gaps'] or 'none (1-' + str(args.max) + ')'}"
            )
            continue
        if args.jam:
            j = jam(corpus.find(name), args.gap)
            out.append(j)
            print("\n".join(jam_lines(j)))
            continue
        if args.explain:
            x = explain(corpus.find(name), args.gap)
            out.append(x)
            print(explain_line(x))
            continue
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
        if args.out:
            with open(f"{args.out}/{r['world']}.json", "w") as handle:
                json.dump(r, handle, indent=1)
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


# ------------------------------------------------------------------ why a gap is too short
def _events(rec: replay.Recording) -> list[dict[str, Any]]:
    return [e.to_json() for e in rec.events]


def _key(e: dict[str, Any], shift: int) -> tuple[Any, ...]:
    return (e["tick"] - shift, tuple(e["piston"]), e["kind"], e["outcome"], tuple(
        (tuple(m["from"]), tuple(m["to"])) for m in e["moved"]
    ))  # fmt: skip


SAVED_SWEEPS = ".sandbox/doors/inputs"


def safe_gap(path: Any) -> int | None:
    """The door's safe gap (``clean_from``): from the saved sweep when there is one."""
    import os

    saved = f"{SAVED_SWEEPS}/{corpus.parse_name(path).slug}.json"
    if os.path.exists(saved):
        with open(saved) as handle:
            return json.load(handle)["clean_from"]
    return run(path)["clean_from"]


def explain(path: Any, gap: int | None = None) -> dict[str, Any]:
    """Why the gap ``gap`` (default: the last bad one, the safe gap − 1) is too short: the
    first piston event of the run with ``gap`` that is not in the run with ``gap + 1``
    (the second sequence aligned to the second flip, the first to the first), its
    counterpart in the good run (the same piston's nearest event of the same kind: what
    it moved there instead), what it ran into (its failure reason, or the first-sequence
    move of the cell in front of it), and the ticks relative to both flips. The safe gap
    follows from that pair: the second sequence's event must come after the first
    sequence's move it collides with."""
    canon = canonical.from_file(path)
    actions = canon["timeline"]["actions"]
    start = actions[0]["tick"]
    if gap is None:
        gap = (safe_gap(path) or 2) - 1
    bad, good = _with_gap(canon, gap), _with_gap(canon, gap + 1)
    flip2_bad = start + gap
    bad_events, good_events = _events(bad), _events(good)
    # An event of the bad run is matched by the same event in the good run at the same
    # tick (the first sequence, aligned to the first flip) or one tick later (the second
    # sequence, aligned to the second flip), whichever side of the second flip it is on.
    good_same = {_key(e, 0) for e in good_events}
    good_shifted = {_key(e, 1) for e in good_events}
    index = None
    for i, e in enumerate(bad_events):
        if _key(e, 0) not in good_same and _key(e, 0) not in good_shifted:
            index = i
            break
    if index is None:
        return {"world": corpus.parse_name(path).slug, "gap": gap, "first_difference": None}
    first_diff = bad_events[index]
    tick = first_diff["tick"]
    same_tick = [e for i, e in enumerate(bad_events) if e["tick"] == tick and i != index]
    counterpart = min(
        (
            e
            for e in good_events
            if e["piston"] == first_diff["piston"]
            and e["kind"] == first_diff["kind"]
            and abs(e["tick"] - (tick + 1)) <= 3
        ),
        key=lambda e: abs(e["tick"] - (tick + 1)),
        default=None,
    )
    failure = first_diff.get("failure")
    step = {"up": (0, 1, 0), "down": (0, -1, 0), "north": (0, 0, -1), "south": (0, 0, 1),
            "west": (-1, 0, 0), "east": (1, 0, 0)}[first_diff["facing"]]  # fmt: skip
    reach = 2 if first_diff["kind"] != "extend" else 1
    front = tuple(first_diff["piston"][i] + step[i] * reach for i in range(3))
    cell = front
    if failure and " at " in failure:
        cell = tuple(map(int, failure.rsplit(" at ", 1)[1].split()))
    collided = None
    for e in bad_events:
        if e["tick"] <= tick and e["tick"] <= flip2_bad + 1:
            for m in e["moved"]:
                if tuple(m["to"]) == cell or tuple(m["from"]) == cell:
                    collided = e
    return {
        "world": corpus.parse_name(path).slug,
        "gap": gap,
        "flip1": start,
        "flip2": flip2_bad,
        "first_difference": first_diff,
        "counterpart": counterpart,
        "after_flip1": tick - start,
        "after_flip2": tick - flip2_bad,
        "same_tick": same_tick,
        "front": list(front),
        "collided_with": collided,
        "collided_after_flip1": None if collided is None else collided["tick"] - start,
    }


def explain_line(x: dict[str, Any]) -> str:
    e = x["first_difference"]
    if e is None:
        return f"{x['world']}: gap {x['gap']}: no piston event differs"
    what = f"{e['kind']} {e['outcome']}" + (f" ({e['failure']})" if e.get("failure") else "")
    text = (
        f"{x['world']}: gap {x['gap']}: first odd event at tick {e['tick']} "
        f"(flip1+{x['after_flip1']}, flip2+{x['after_flip2']}): piston {e['piston']} {what}"
    )
    cp = x.get("counterpart")
    if cp is not None:
        moves = ", ".join(f"{m['from']}->{m['to']}" for m in cp["moved"][:2])
        text += f"; at gap+1 the same {cp['kind']} at tick {cp['tick']} {cp['outcome']} {moves}"
    c = x["collided_with"]
    if c is not None:
        moved = c["moved"][0] if c["moved"] else None
        text += (
            f"; the cell was moved by {c['piston']} {c['kind']} at tick {c['tick']} "
            f"(flip1+{x['collided_after_flip1']})"
            + (f", {moved['from']} -> {moved['to']}" if moved else "")
        )
    elif x["same_tick"]:
        others = ", ".join(f"{o['piston']} {o['kind']} {o['outcome']}" for o in x["same_tick"][:3])
        text += f"; same tick: {others}"
    return text


# ------------------------------------------------------------------------ lasting jams
def jam(path: Any, gap: int, cycles: int = 2) -> dict[str, Any]:
    """A too-short gap followed by ``cycles`` more designed cycles: which door blocks end
    in a wrong cell, where each one went instead, which of the designed cycle's moves of
    it the jammed cycle did not make (the pulls that are missing, backlog D10), and what
    the later cycles did with it."""
    from tools.doorlab import analysis

    canon = canonical.from_file(path)
    actions = canon["timeline"]["actions"]
    start = actions[0]["tick"]
    outputs = [tuple(p) for p in canon["annotations"]["sections"]["output"]["positions"]]

    def run(ticks: list[int]) -> replay.Recording:
        variant = copy.deepcopy(canon)
        variant["timeline"]["actions"] = [
            {**copy.deepcopy(actions[i % 2]), "tick": t} for i, t in enumerate(ticks)
        ]
        variant["timeline"]["end_tick"] = ticks[-1] + SETTLE
        return replay.record(canonical.rebuild(variant))

    designed_gap = actions[1]["tick"] - start
    good = run([start, start + designed_gap])
    cycle_end = start + gap + SETTLE  # the jammed cycle; later cycles start here
    bad_ticks = [start, start + gap] + [cycle_end + SETTLE * k for k in range(0, cycles)]
    bad = run(bad_ticks)
    good_tokens, good_moved_by = analysis.track(good)
    bad_tokens, bad_moved_by = analysis.track(bad)

    def moves(rec: replay.Recording, moved_by: dict[int, list[int]], token: Any) -> list[Any]:
        out = []
        for i, ids in moved_by.items():
            if token.id in ids:
                e = rec.events[i]
                dest = next(p for t, p in token.path if t == e.tick)
                out.append((e.tick, e.piston, e.kind, dest))
        return out

    wrong = []
    for token in good_tokens:
        if token.start not in outputs and not any(p in outputs for _, p in token.path):
            continue  # not a door block
        twin = next((t for t in bad_tokens if t.start == token.start), None)
        rest_good = token.path[-1][1]
        rest_bad = twin.path[-1][1] if twin else token.start
        if rest_good == rest_bad:
            continue
        good_moves = moves(good, good_moved_by, token)
        bad_moves = moves(bad, bad_moved_by, twin) if twin else []
        in_jam = [m for m in bad_moves if m[0] < cycle_end]
        made = {(m[1], m[2]) for m in in_jam}
        missing = [m for m in good_moves if (m[1], m[2]) not in made]
        wrong.append(
            {
                "block": token.state,
                "built": list(token.start),
                "rest_designed": list(rest_good),
                "rest_after_jam": list(rest_bad),
                "designed_moves": [[t, list(p), k, list(d)] for t, p, k, d in good_moves],
                "jam_cycle_moves": [[t, list(p), k, list(d)] for t, p, k, d in in_jam],
                "missing_in_jam_cycle": [[t, list(p), k, list(d)] for t, p, k, d in missing],
                "later_moves": [
                    [t, list(p), k, list(d)] for t, p, k, d in bad_moves if t >= cycle_end
                ],
            }
        )
    return {
        "world": corpus.parse_name(path).slug,
        "gap": gap,
        "cycles": cycles,
        "wrong_blocks": wrong,
        "quiet": not any(bad.changes.get(t) for t in range(bad.end_tick - 10, bad.end_tick + 1)),
    }


def jam_lines(j: dict[str, Any]) -> list[str]:
    out = [
        f"{j['world']}: gap {j['gap']} + {j['cycles']} cycles: {len(j['wrong_blocks'])} door "
        f"blocks off ({'quiet' if j['quiet'] else 'still moving'})"
    ]
    for w in j["wrong_blocks"]:
        name = w["block"].split("[", 1)[0].replace("minecraft:", "")
        out.append(
            f"  {name} built {w['built']}: rests at {w['rest_after_jam']} instead of "
            f"{w['rest_designed']}; the jammed cycle made {len(w['jam_cycle_moves'])} of its "
            f"{len(w['designed_moves'])} moves; missing: "
            + (
                "; ".join(f"t{t} {p} {k} -> {d}" for t, p, k, d in w["missing_in_jam_cycle"])
                or "none"
            )
            + "; later: "
            + ("; ".join(f"t{t} {p} {k} -> {d}" for t, p, k, d in w["later_moves"][:6]) or "none")
        )
    return out


def repair(path: Any, gap: int, max_gap: int = 40) -> dict[str, Any]:
    """After a lasting jam (gap ``gap``), can a second cycle with some other gap bring the
    whole build back to a normal rest state? Tries every second-cycle gap from 1 to
    ``max_gap`` (and the designed one): the first flip of the second cycle comes when the
    jammed door is quiet, the second after that gap. Reports the gaps that repair."""
    canon = canonical.from_file(path)
    actions = canon["timeline"]["actions"]
    start = actions[0]["tick"]

    def run(ticks: list[int]) -> replay.Recording:
        variant = copy.deepcopy(canon)
        variant["timeline"]["actions"] = [
            {**copy.deepcopy(actions[i % 2]), "tick": t} for i, t in enumerate(ticks)
        ]
        variant["timeline"]["end_tick"] = ticks[-1] + SETTLE
        return replay.record(canonical.rebuild(variant))

    normal = [_final(run([start + SETTLE * i for i in range(n)])) for n in range(1, 5)]
    second = start + gap + SETTLE
    repairs = []
    for g in range(1, max_gap + 1):
        rec = run([start, start + gap, second, second + g])
        if _final(rec) in normal:
            repairs.append(g)
    return {"world": corpus.parse_name(path).slug, "gap": gap, "repairing_gaps": repairs}


if __name__ == "__main__":
    main()
