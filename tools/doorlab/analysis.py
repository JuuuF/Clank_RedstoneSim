"""Layer 3: a door explained from its replay (``python -m tools.doorlab.analysis WORLD``).

From the piston events of ``replay`` (what each block event moved, from where to where)
this follows every moved block as a **token** through the run, so each door block has a
trajectory (its cell when closed → the cells it passes → where it is stored when open).
From the tokens and events it derives:

- **piston roles**: a piston that moves door blocks is a *door* piston; one that moves
  other pistons is a *stack* (an extender's lower stage); one that moves redstone parts
  (observers, redstone blocks, dust carriers) is a *power mover* (slider, block swapper);
  one that moves only other blocks a *helper*; one that never fires is *idle*;
- **groups**: door cells cleared by the same pistons (the guide's "grouping"), with the
  direction they leave in and where they are stored;
- **moves**: each piston's actions compressed into pulses (extend → retract) with their
  lengths, including spits (a retract during the extension);
- **power access**: per piston, how its extensions were powered (the block giving the
  signal, quasi-connectivity or not), from the trace notes;
- **phases**: bursts of piston activity separated by quiet ticks.

Everything is read from the simulation; nothing is inferred from block names except the
role words.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from tools.doorlab import corpus, interactions, replay

Pos = tuple[int, int, int]
POWER_PARTS = {
    "observer",
    "redstone_block",
    "torch",
    "repeater",
    "comparator",
    "wire",
    "target",
    "lever",
    "bud",
    "lamp",
}


@dataclass
class Token:
    """One block that moved at least once, followed through the run."""

    id: int
    state: str  # what it is (state text when it first moved)
    path: list[tuple[int, Pos]] = field(default_factory=list)  # (tick, position) from build

    @property
    def start(self) -> Pos:
        return self.path[0][1]

    def at(self, tick: int) -> Pos:
        where = self.path[0][1]
        for t, p in self.path:
            if t > tick:
                break
            where = p
        return where


def track(rec: replay.Recording) -> tuple[list[Token], dict[int, list[int]]]:
    """Follow every moved block. Returns the tokens and, per event index, the tokens it
    moved. A piston's own head or base (source entries) is not a token."""
    tokens: list[Token] = []
    at: dict[Pos, int] = {}  # position → token there now
    moved_by: dict[int, list[int]] = {}
    for index, event in enumerate(rec.events):
        moves = [m for m in event.moved if not m.source]
        if not moves:
            continue
        lifted = []
        for m in moves:
            token_id = at.pop(m.origin, None)
            if token_id is None:
                token_id = len(tokens)
                tokens.append(Token(token_id, m.state, [(0, m.origin)]))
            lifted.append((token_id, m.dest))
        for token_id, dest in lifted:
            at[dest] = token_id
            tokens[token_id].path.append((event.tick, dest))
        moved_by[index] = [t for t, _ in lifted]
    return tokens, moved_by


@dataclass
class PistonInfo:
    pos: Pos
    sticky: bool
    facing: str
    role: str = "idle"
    events: list[dict[str, Any]] = field(default_factory=list)
    moved_door_tokens: set[int] = field(default_factory=set)
    moved_kinds: Counter[str] = field(default_factory=Counter)
    power: Counter[str] = field(default_factory=Counter)


def _pulses(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extend → retract pairs of one piston: their start, length and outcome."""
    out: list[dict[str, Any]] = []
    open_: dict[str, Any] | None = None
    for e in events:
        if e["kind"] == "extend" and e["outcome"] != "skipped":
            open_ = {"start": e["tick"], "push": e["outcome"]}
        elif e["kind"] in ("retract", "drop") and e["outcome"] != "skipped":
            if open_ is not None:
                out.append({**open_, "length": e["tick"] - open_["start"], "end": e["outcome"]})
                open_ = None
            else:
                out.append({"start": None, "length": None, "end": e["outcome"], "at": e["tick"]})
    if open_ is not None:
        out.append({**open_, "length": None, "end": "held"})
    return out


def analyze(path_or_doc: Any, end_tick: int | None = None) -> dict[str, Any]:
    if hasattr(path_or_doc, "level"):
        doc, name = path_or_doc, None
    else:
        session = corpus.open_world(path_or_doc)
        doc, name = session.doc, corpus.parse_name(path_or_doc)
    sections = doc.sections.to_json()
    outputs = [tuple(p) for p in sections.get("output", {}).get("positions", [])]
    inputs = [tuple(p) for p in sections.get("input", {}).get("positions", [])]
    way = interactions.doorway(outputs)
    rec = replay.record(doc, end_tick)
    tokens, moved_by = track(rec)
    cells = set(way.cells) | set(way.extra_cells)
    door_tokens = {t.id for t in tokens if any(p in cells for _, p in t.path)}

    # Pistons: the static list at the build plus everything that fired.
    doc.seek_tick(0)
    static = {p.pos: p for p in interactions.pistons(doc.level)}
    info: dict[Pos, PistonInfo] = {}
    for pos, p in static.items():
        info[pos] = PistonInfo(pos, p.sticky, p.facing)
    for index, e in enumerate(rec.events):
        # A piston that was itself moved is known by its position at that moment.
        pi = info.setdefault(e.piston, PistonInfo(e.piston, e.sticky, e.facing))
        pi.events.append(e.to_json())
        for token_id in moved_by.get(index, []):
            kind = interactions.role(tokens[token_id].state)
            pi.moved_kinds[kind] += 1
            if token_id in door_tokens:
                pi.moved_door_tokens.add(token_id)
        if e.power:
            pi.power[power_kind(e.power)] += 1
    # Blocks that carried power to a piston at some moment (the ``via`` of its note).
    vias: set[tuple[int, Pos]] = {
        (e.power["tick"], tuple(e.power["via"])) for e in rec.events if e.power
    }
    carriers = {t.id for t in tokens if any(t.at(tick) == pos for tick, pos in vias)}
    for index, e in enumerate(rec.events):
        if carriers & set(moved_by.get(index, [])):
            info[e.piston].moved_kinds["power carrier"] += 1
    for pi in info.values():
        if not pi.events:
            pi.role = "idle"
        elif pi.moved_door_tokens:
            pi.role = "door"
        elif pi.moved_kinds.get("piston") or pi.moved_kinds.get("piston_head"):
            pi.role = "stack"
        elif any(k in POWER_PARTS for k in pi.moved_kinds):
            pi.role = "power mover"
        elif pi.moved_kinds.get("power carrier"):
            pi.role = "power switch"
        elif pi.moved_kinds:
            pi.role = "helper"
        else:
            pi.role = "fires, moves nothing"
    # A stack piston that also moves door blocks through the piston above is "door";
    # mark pistons that moved other pistons as stacks too.
    stacks = {
        pos
        for pos, pi in info.items()
        if pi.moved_kinds.get("piston") or pi.moved_kinds.get("piston_head")
    }

    # Door blocks: where each one is when closed and when open.
    frames = replay.frames(rec, way.cells) if way.cells else []
    closed = [t for t, f in enumerate(frames) if f and set(f) == {"#"}]
    opened = [t for t, f in enumerate(frames) if f and set(f) <= {"."}]
    # The reference ticks: the world's own end-state markers if it has them (they name
    # the states of non-door contraptions too), else the last fully closed / open frame.
    marked = {n.lower(): t for t, n in sorted(doc.markers.items()) if t <= rec.end_tick}
    t_closed = marked.get("closed", closed[-1] if closed else None)
    t_open = marked.get("opened", opened[-1] if opened else None)
    blocks = []
    for t in tokens:
        if t.id not in door_tokens:
            continue
        movers = sorted({rec.events[i].piston for i, ids in moved_by.items() if t.id in ids})
        blocks.append(
            {
                "token": t.id,
                "block": interactions.block_id(t.state),
                "closed_at": list(t.at(t_closed)) if t_closed is not None else None,
                "open_at": list(t.at(t_open)) if t_open is not None else None,
                "moves": len(t.path) - 1,
                "path": [[tick, list(p)] for tick, p in t.path],
                "pistons": [list(p) for p in movers],
            }
        )
    groups = _groups(blocks, way)

    # Phases: bursts of events separated by >= 3 quiet ticks.
    phases: list[dict[str, Any]] = []
    for e in rec.events:
        if not phases or e.tick - phases[-1]["to"] > 3:
            phases.append({"from": e.tick, "to": e.tick, "events": 0, "pistons": set()})
        phases[-1]["to"] = e.tick
        phases[-1]["events"] += 1
        phases[-1]["pistons"].add(e.piston)
    for ph in phases:
        ph["pistons"] = len(ph["pistons"])

    actions = [
        {"tick": t, "what": a.label if hasattr(a, "label") else str(a)}
        for t, acts in sorted(doc.history.plan().items())
        for a in acts
    ]
    roles = Counter(pi.role for pi in info.values())
    power_total: Counter[str] = Counter()
    for pi in info.values():
        power_total.update(pi.power)
    return {
        "world": name.slug if name else None,
        "title": name.title if name else None,
        "creator": name.creator if name else None,
        "doorway": way.to_json(),
        "inputs": [list(p) for p in inputs],
        "actions": actions,
        "markers": {str(k): v for k, v in sorted(doc.markers.items())},
        "frames": frames,
        "closed_ticks": closed,
        "open_ticks": opened,
        "reference_ticks": {"closed": t_closed, "open": t_open},
        "piston_roles": dict(roles),
        "stacks": [list(p) for p in sorted(stacks)],
        "power_access": dict(power_total.most_common()),
        "pistons": [
            {
                "pos": list(pi.pos),
                "sticky": pi.sticky,
                "facing": pi.facing,
                "role": pi.role,
                "fires": len(pi.events),
                "pulses": _pulses(pi.events),
                "door_blocks": len(pi.moved_door_tokens),
                "moved": dict(pi.moved_kinds),
                "power": dict(pi.power),
            }
            for pi in sorted(info.values(), key=lambda p: (p.role, p.pos))
        ],
        "door_blocks": blocks,
        "groups": groups,
        "phases": phases,
        "events": [e.to_json() for e in rec.events],
        "end_tick": rec.end_tick,
    }


def power_kind(power: dict[str, Any]) -> str:
    """How an extension was powered, in words: "repeater", "wire (QC)", "block←torch" …
    (``via`` is the block giving the signal; a solid block names what powers it)."""
    via = interactions.role(power["via_block"])
    if via in ("structure", "analog", "piston", "sticky_block"):
        sources = sorted({interactions.role(b) for _, b in power["sources"]})
        via = "block←" + "+".join(sources) if sources else "block"
    return via + (" (QC)" if power["quasi"] else "")


def exit_side(way: interactions.Doorway, closed: Pos, opened: Pos) -> str:
    """Where a door block goes when the door opens, seen from the doorway: above, below,
    left/right (the low/high end of the in-plane horizontal axis, west/north first),
    or out of the plane ("recess") while still in front of the opening."""
    if way.normal is None:
        return _direction(closed, opened)
    across = 0 if way.normal == "x" else 2
    along = 2 if way.normal == "x" else 0
    top, bottom = max(way.rows), min(way.rows)
    low, high = min(way.columns), max(way.columns)
    if opened[1] > top:
        return "above"
    if opened[1] < bottom:
        return "below"
    if opened[along] < low:
        return "west" if along == 0 else "north"
    if opened[along] > high:
        return "east" if along == 0 else "south"
    if opened[across] != way.plane:
        return "recess"
    return "stays in the doorway"


def _direction(a: Pos, b: Pos) -> str:
    d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    names = []
    for value, plus, minus in (
        (d[1], "up", "down"),
        (d[0], "east", "west"),
        (d[2], "south", "north"),
    ):
        if value:
            names.append(f"{plus if value > 0 else minus} {abs(value)}")
    return ", ".join(names) or "stays"


def _groups(blocks: list[dict[str, Any]], way: interactions.Doorway) -> list[dict[str, Any]]:
    """Door blocks grouped by the side they leave through (the guide's grouping)."""
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in blocks:
        if b["closed_at"] and b["open_at"]:
            side = exit_side(way, tuple(b["closed_at"]), tuple(b["open_at"]))
        else:
            side = "unknown"
        b["exit"] = side
        by[side].append(b)
    out = []
    for side, members in sorted(by.items(), key=lambda kv: -len(kv[1])):
        pistons = sorted({tuple(p) for m in members for p in m["pistons"]})
        out.append(
            {
                "exit": side,
                "blocks": len(members),
                "cells": [m["closed_at"] for m in members],
                "pistons": [list(p) for p in pistons],
                "moves_per_block": dict(Counter(m["moves"] for m in members)),
                "closed_to_open": dict(
                    Counter(
                        _direction(tuple(m["closed_at"]), tuple(m["open_at"]))
                        for m in members
                        if m["closed_at"] and m["open_at"]
                    )
                ),
            }
        )
    return out


def report(a: dict[str, Any]) -> str:
    """A short text report (what ``python -m tools.doorlab.analysis`` prints)."""
    way = a["doorway"]
    lines = [
        f"{a['title']} by {a['creator']} ({a['world']})",
        f"doorway {way['width']}x{way['height']} across {way['normal']}={way['plane']}"
        f" (+{len(way['extra_cells'])} other output cells)",
        f"actions: {a['actions']}  markers: {a['markers']}",
        f"pistons by role: {a['piston_roles']}",
        f"power access of extensions: {a['power_access']}",
        f"closed at ticks {_runs(a['closed_ticks'])}, open at {_runs(a['open_ticks'])}",
        "phases: "
        + "; ".join(
            f"{p['from']}-{p['to']} ({p['events']} events, {p['pistons']} pistons)"
            for p in a["phases"]
        ),
        "groups (door blocks cleared by the same pistons):",
    ]
    for g in a["groups"]:
        lines.append(
            f"  {g['exit']}: {g['blocks']} blocks, {len(g['pistons'])} pistons, "
            f"moves per block {g['moves_per_block']}, closed→open "
            f"{g['closed_to_open']}"
        )
    return "\n".join(lines)


def _runs(ticks: list[int]) -> str:
    out: list[list[int]] = []
    for t in ticks:
        if out and out[-1][1] == t - 1:
            out[-1][1] = t
        else:
            out.append([t, t])
    return ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in out) or "never"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", help="slug or file-name part of a dataset world, or a path")
    parser.add_argument("--json", help="write the full analysis to this file")
    args = parser.parse_args()
    from pathlib import Path

    path = Path(args.world)
    if not path.exists():
        path = corpus.find(args.world)
    a = analyze(path)
    print(report(a))
    if args.json:
        Path(args.json).write_text(json.dumps(a, indent=1) + "\n")


if __name__ == "__main__":
    main()
