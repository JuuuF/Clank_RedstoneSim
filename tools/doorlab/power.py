"""Who reads whose power: the signal reads of a run (``python -m tools.doorlab.power WORLD``).

Layer 2's static model says which blocks *could* power a piston; the replay says where each
extension's power *came from*. In between lie all the other readers: wire reading the block
a repeater powers, a torch reading the block it stands on, a lamp, a comparator, the block
above a piston (quasi-connectivity). This module records every one of them during the
designed run with the simulator's own probe (``Level.signal_probe``: every signal read that
returned more than 0), finds the component that asked (the first engine frame above the
level's helpers: a piston's ``get_neighbor_signal``, wire's ``get_block_signal``, a
diode's ``get_input_signal`` …; a read of a cell that is not one of the asker's six
neighbors is a quasi-connectivity read), and judges each read:

- a read is **decisive** when the asker got nothing as strong from any other position it
  reads at that moment (a piston: its six neighbors and the five above it, the push
  direction left out; wire: the muted-wire block signal and the incoming wire signal; a
  torch or a diode reads one position only);
- otherwise it is **redundant**: another path gave the asker the same (or a stronger)
  signal there and then.

Reads follow a block when a piston moves it (``replay``'s moves), so a conductor's role is
the block's, not the cell's: Mumbo Jumbo's wire-cutter wool matters where the helper
piston puts it, not where it is built.

A conductor's **role** for the glass counterfactual ([[robustness]]) follows: ``decisive
<asker kinds>``, ``redundant`` (read, never decisive), ``unread`` (powered at some tick,
never read), and the structural roles checked at every cell the block occupies during the
run: ``cutter`` (wire under it and beside it: it breaks a wire step), ``step`` (wire on it
and beside it: it carries the upper wire of a step; glass there cuts the step the other
way), ``stopper`` (an extension failed on it: ``immovable … at``), ``support`` (a part
attached to it would fall off glass), ``immovable`` (obsidian that is never in the way),
``none``.

The reads are what happened; what layer 2 *predicts* for the glass change is the **local
counterfactual** ``glass_effect``: at every tick boundary of the designed run, each
conductor (followed where pistons move it) is swapped for glass and every component that
reads it (the six neighbors, the pistons and droppers one below them for quasi-connectivity)
recomputes its own input with the block's own rule (``getNeighborSignal``, the wire's target
strength, a diode's input, a torch's attached block, ``hasNeighborSignal``). The ticks and
readers whose input differs are the block's effect; a block with none, no support role and
no stopper role is predicted harmless. Wire steps and cutters need no rule of their own:
the wire's recomputation sees them.

``--predict --out DIR`` scores the counterfactual (and, with ``--reads``, the read roles)
against saved ablation results like ``ablation --predict`` does, per world and in total;
``--list`` prints every block.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Any

from redsim.core.direction import ALL, HORIZONTAL, Direction
from redsim.core.pos import above, below, offset
from redsim.sim.level import Level
from redsim.world.blocks.falling import FallingBlock
from redsim.world.blocks.piston import PistonStructureResolver, piston_facing
from redsim.world.properties import EXTENDED
from tools.doorlab import ablation, canonical, corpus, interactions, replay

Pos = tuple[int, int, int]

PISTONS = ("piston", "sticky_piston")
STICKY = ("minecraft:slime_block", "minecraft:honey_block")
QC_READERS = ("piston", "sticky_piston", "dropper", "dispenser")
LEVEL_HELPERS = (
    "get_signal",
    "_get_signal",
    "has_signal",
    "has_neighbor_signal",
    "get_best_neighbor_signal",
    "get_direct_signal_to",
    "get_direct_signal",
    "<genexpr>",
    "probe",
)


@dataclass(slots=True)
class Read:
    """One signal read that returned more than 0."""

    tick: int
    asker: Pos  #: the component that asked
    kind: str  #: piston, piston (QC), wire, repeater, comparator, torch, lamp, dropper …
    target: Pos  #: the cell read (``origin``: the cell the block there was built in)
    origin: Pos
    target_block: str
    conductor: bool  #: the target carries power it got from others (a solid block)
    value: int
    alt: int  #: the best signal the asker gets from its other inputs at that moment
    context: str = ""  #: update (a neighbor update), event (a piston's block event), tick
    extended: bool = False  #: a piston asker that is extended at the read
    sources: tuple[Pos, ...] = ()  #: for a conductor target: the neighbors giving it signal

    @property
    def decisive(self) -> bool:
        return self.value > self.alt

    @property
    def queues(self) -> bool:
        """A retracted piston's update read that nothing else would have made positive: the
        read that queues its extension then and there (a later source would not update a
        quasi-connected piston: the update problem)."""
        return (
            self.kind.startswith("piston")
            and self.context == "update"
            and not self.extended
            and self.alt == 0
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "asker": list(self.asker),
            "kind": self.kind,
            "target": list(self.target),
            "origin": list(self.origin),
            "target_block": self.target_block,
            "conductor": self.conductor,
            "value": self.value,
            "alt": self.alt,
            "decisive": self.decisive,
            "context": self.context,
            "extended": self.extended,
            "sources": [list(p) for p in self.sources],
        }


def _adjacent(a: Pos, b: Pos) -> bool:
    return sum(abs(a[i] - b[i]) for i in range(3)) == 1


CONTEXTS = {"trigger_event": "event", "check_if_extend": "update", "tick": "tick"}


def asker_of(level: Level, target: Pos) -> tuple[Pos, str, str]:
    """The component whose code asked for ``target``'s signal: the first frame above the
    level's signal helpers that has a ``pos`` local (the block's own method), whether it
    read through quasi-connectivity (a cell that is not one of its neighbors), and the
    context of the read (update, event, tick)."""
    frame = sys._getframe(1)
    asker: Pos | None = None
    context = ""
    while frame is not None:
        code = frame.f_code
        if asker is None and code.co_name not in LEVEL_HELPERS and "pos" in frame.f_locals:
            pos = frame.f_locals["pos"]
            if isinstance(pos, tuple) and len(pos) == 3:
                asker = pos
        if code.co_name in CONTEXTS:
            context = CONTEXTS[code.co_name]
            break
        frame = frame.f_back
    if asker is None:
        asker = target
    name = interactions.block_id(level.get_block_state(asker))
    if name in PISTONS:
        kind = "piston"
    elif name in ("redstone_torch", "redstone_wall_torch"):
        kind = "torch"
    elif name == "redstone_wire":
        kind = "wire"
    elif name == "redstone_lamp":
        kind = "lamp"
    else:
        kind = name
    if kind in ("piston", "dropper", "dispenser") and not _adjacent(asker, target):
        kind += " (QC)"
    return asker, kind, context


def alternatives(level: Level, asker: Pos, kind: str, target: Pos) -> int:
    """The best signal ``asker`` gets from every input it reads except ``target``, read now
    (the same rules the asker uses: ``getNeighborSignal`` for a piston, the muted-wire block
    signal plus the incoming wire signal for wire, one position for torches and diodes)."""
    if kind in ("torch", "repeater", "comparator"):
        return 0
    state = level.get_block_state(asker)
    reads: list[tuple[Pos, Direction]] = []
    base = kind.removesuffix(" (QC)")
    if base == "piston":
        push = piston_facing(state)
        reads += [(asker, d) for d in ALL if d is not push]
        reads += [(above(asker), d) for d in ALL if d is not Direction.DOWN]
    elif base in ("dropper", "dispenser"):
        reads += [(asker, d) for d in ALL]
        reads += [(above(asker), d) for d in ALL]
    else:
        reads += [(asker, d) for d in ALL]
    best = 0
    for pos, d in reads:
        neighbor = offset(pos, d)
        if neighbor != target:
            best = max(best, level.get_signal(neighbor, d))
    if kind == "wire":
        best = max(best, state.block.get_incoming_wire_signal(level, asker))
    return best


def trace_reads(document: Any, end_tick: int | None = None) -> list[Read]:
    """Every positive signal read of the designed run, tick by tick, with its asker, its
    alternatives and the built position of the block read (moved blocks are followed)."""
    doc = document
    end = doc.end_tick if end_tick is None else end_tick
    rec = replay.record(doc, end)
    moves: dict[int, list[tuple[Pos, Pos]]] = {}
    for event in rec.events:
        for m in event.moved:
            moves.setdefault(event.tick, []).append((m.origin, m.dest))
    origin: dict[Pos, Pos] = {}  # current cell → built cell, for moved blocks only
    doc.history.seek(doc.history.start)
    doc.seek_tick(0)
    history = doc.history
    reads: list[Read] = []
    busy = [False]
    tick_now = [0]

    def probe(level: Level, pos: Pos, direction: Direction, state: Any, value: int) -> None:
        if busy[0]:
            return
        busy[0] = True
        try:
            asker, kind, context = asker_of(level, pos)
            alt = alternatives(level, asker, kind, pos)
            asker_state = level.get_block_state(asker)
            conductor = bool(state.is_redstone_conductor(level, pos))
            sources: tuple[Pos, ...] = ()
            if conductor:
                sources = tuple(
                    offset(pos, d) for d in ALL if level.get_direct_signal(offset(pos, d), d) > 0
                )
            reads.append(
                Read(
                    tick=tick_now[0],
                    asker=asker,
                    kind=kind,
                    target=pos,
                    origin=origin.get(pos, pos),
                    target_block=interactions.block_id(state),
                    conductor=conductor,
                    value=value,
                    alt=alt,
                    context=context,
                    extended=kind.startswith("piston") and bool(asker_state.get(EXTENDED)),
                    sources=sources,
                )
            )
        finally:
            busy[0] = False

    previous = Level.signal_probe
    Level.signal_probe = probe
    try:
        for tick in range(1, end + 1):
            tick_now[0] = tick
            stop = doc.tick_steps.get(tick)
            if stop is None:
                raise RuntimeError(f"tick {tick} is not in the recorded history")
            while history.position < stop:
                history.seek(history.position + 1)
            # The blocks a piston started to move this tick land in their new cells; reads
            # of those cells from now on are reads of the moved blocks.
            for src, dst in moves.get(tick, []):
                origin[dst] = origin.pop(src, src)
    finally:
        Level.signal_probe = previous
    return reads


def mechanism_pistons(path: Any) -> set[Pos]:
    """The pistons that move door blocks or other pistons (roles door and stack)."""
    from tools.doorlab import analysis

    a = analysis.analyze(path)
    return {tuple(p["pos"]) for p in a["pistons"] if p["role"] in ("door", "stack")}


def read_graph(
    reads: list[Read], level: Level | None = None, rec: replay.Recording | None = None
) -> dict[Pos, set[Pos]]:
    """Who feeds whom, time collapsed: a conductor's sources feed it, a read target feeds
    its asker (a quasi-connectivity asker is the piston itself). Positions are the cells
    read, so a moved block's cells are separate nodes. With the build (``level``) and the
    run (``rec``), the links that are not signal reads are added: wire to wire (the
    incoming-wire rule), the cell an observer watches to the observer, a comparator's
    side inputs and the container it measures, and a piston to every cell it moved a
    block from or to."""
    from redsim.world.blocks.diode import facing as diode_facing
    from redsim.world.properties import FACING

    graph: dict[Pos, set[Pos]] = {}

    def link(a: Pos, b: Pos) -> None:
        graph.setdefault(a, set()).add(b)

    for r in reads:
        link(r.target, r.asker)
        for src in r.sources:
            link(src, r.target)
    if level is not None:
        for pos, state in list(level.blocks.items()):
            name = interactions.block_id(state)
            if name == "redstone_wire":
                above_conducts = level.get_block_state(above(pos)).is_redstone_conductor(
                    level, above(pos)
                )
                for h in HORIZONTAL:
                    n = offset(pos, h)
                    ns = level.get_block_state(n)
                    if interactions.block_id(ns) == "redstone_wire":
                        link(n, pos)
                    elif ns.is_redstone_conductor(level, n):
                        if (
                            not above_conducts
                            and interactions.block_id(level.get_block_state(above(n)))
                            == "redstone_wire"
                        ):
                            link(above(n), pos)
                    elif interactions.block_id(level.get_block_state(below(n))) == "redstone_wire":
                        link(below(n), pos)
            elif name == "observer":
                link(offset(pos, state.get(FACING)), pos)
            elif name == "comparator":
                front = diode_facing(state)
                for side in (front.clockwise(), front.counter_clockwise()):
                    link(offset(pos, side), pos)
                behind = offset(pos, front)
                link(behind, pos)
                link(offset(behind, front), pos)  # a container measured through a block
    if rec is not None:
        for event in rec.events:
            for m in event.moved:
                link(event.piston, m.origin)
                link(event.piston, m.dest)
    return graph


def reaches(graph: dict[Pos, set[Pos]], start: set[Pos], sinks: set[Pos]) -> bool:
    """Is some sink reachable from the start cells along the read graph?"""
    seen = set(start)
    todo = list(start)
    while todo:
        p = todo.pop()
        if p in sinks:
            return True
        for q in graph.get(p, ()):
            if q not in seen:
                seen.add(q)
                todo.append(q)
    return False


def cells_of(rec: replay.Recording, pos: Pos) -> list[Pos]:
    """Every cell the block built at ``pos`` occupies during the run."""
    cells = [pos]
    for event in rec.events:
        for m in event.moved:
            if m.origin == cells[-1]:
                cells.append(m.dest)
    return cells


def loses_support(level: Level, pos: Pos) -> bool:
    """Would a neighbor fall off if ``pos`` were glass (a torch on its side, a lever …)?"""
    from redsim.world import blocks

    saved = level.blocks.get(pos)
    level.blocks[pos] = blocks.parse_state(ablation.GLASS)
    try:
        for d in Direction:
            n = offset(pos, d)
            s = level.get_block_state(n)
            if not s.is_air and not s.can_survive(level, n):
                return True
        return False
    finally:
        if saved is None:
            level.blocks.pop(pos, None)
        else:
            level.blocks[pos] = saved


def structural_roles(level: Level, rec: replay.Recording, pos: Pos) -> list[str]:
    """The roles a conductor plays by shape at any cell it occupies: cutter, step, stopper,
    support (checked on the build's wires, which do not move in these doors)."""

    def wire(p: Pos) -> bool:
        return level.get_block_state(p).block.id == "minecraft:redstone_wire"

    stoppers = set()
    held = set()
    for event in rec.events:
        if event.failure and event.failure.startswith("immovable"):
            stoppers.add(tuple(map(int, event.failure.rsplit(" at ", 1)[1].split())))
        if event.kind == "retract" and event.sticky:
            # the cell in front of the head: a sticky piston pulls it unless it is immovable
            facing = Direction[event.facing.upper()]
            held.add(offset(event.piston, facing, 2))
        for m in event.moved:
            if m.state.split("[", 1)[0] in STICKY:
                held |= {offset(m.origin, d) for d in ALL}
    out: list[str] = []
    immovable = level.get_block_state(pos).block.id in ablation.IMMOVABLE
    for cell in cells_of(rec, pos):
        beside = any(wire(offset(cell, d)) for d in HORIZONTAL)
        if wire(below(cell)) and beside:
            out.append("cutter")
        if wire(above(cell)) and beside:
            out.append("step")
        if cell in stoppers:
            out.append("stopper")
        if immovable and cell in held:
            out.append("stopper")
    if loses_support(level, pos):
        out.append("support")
    if isinstance(level.get_block_state(pos).block, FallingBlock):
        out.append("falling")
    return sorted(set(out))


def roles(path: Any, positions: list[Pos]) -> tuple[dict[Pos, str], list[Read]]:
    """Each conductor's role for the glass change, from the reads of the designed run."""
    static = ablation.glass_roles(path, positions)
    doc = canonical.rebuild(canonical.from_file(path))
    rec = replay.record(doc)
    reads = trace_reads(doc)
    doc.seek_tick(0)
    by_origin: dict[Pos, list[Read]] = {}
    for r in reads:
        by_origin.setdefault(r.origin, []).append(r)
    out: dict[Pos, str] = {}
    for p in positions:
        parts = structural_roles(doc.level, rec, p)
        mine = by_origin.get(p, [])
        decisive = [r for r in mine if r.decisive]
        if decisive:
            parts.append("decisive " + "+".join(sorted({r.kind for r in decisive})))
        elif mine:
            parts.append("redundant")
        elif static[p] == "powered":
            parts.append("unread")
        elif not parts:
            parts.append(static[p])
        out[p] = ", ".join(parts)
    return out, reads


SIMPLE_READERS = ("redstone_lamp", "note_block", "hopper", "copper_bulb", "crafter", "tnt", "bell")


def piston_decision(level: Level, pos: Pos, state: Any) -> str:
    """What the piston would do if updated now: extend (powered, retracted, and its push
    resolves), retract (unpowered, extended) or nothing."""
    from redsim.world.blocks.piston import PistonBaseBlock

    facing = piston_facing(state)
    block: PistonBaseBlock = state.block
    powered = block.get_neighbor_signal(level, pos, facing)
    if powered and not state.get(EXTENDED):
        return (
            "extend" if PistonStructureResolver(level, pos, facing, True).resolve() else "blocked"
        )
    if not powered and state.get(EXTENDED):
        return "retract"
    return "nothing"


def inputs_around(level: Level, cell: Pos) -> dict[tuple[str, Pos], Any]:
    """What every component that reads ``cell`` reads now, by its own rule."""
    from redsim.world.blocks.diode import DiodeBlock
    from redsim.world.blocks.piston import PistonBaseBlock
    from redsim.world.blocks.redstone_wire import RedstoneWireBlock
    from redsim.world.blocks.torch import RedstoneTorchBlock

    out: dict[tuple[str, Pos], Any] = {}
    neighbors = {offset(cell, d) for d in ALL}
    quasi = {below(n) for n in neighbors} - {cell}
    for n in sorted(neighbors | quasi):
        state = level.get_block_state(n)
        block = state.block
        name = interactions.block_id(state)
        if isinstance(block, PistonBaseBlock):
            out[("piston", n)] = piston_decision(level, n, state)
        elif name in ("dropper", "dispenser"):
            out[(name, n)] = level.has_neighbor_signal(n) or level.has_neighbor_signal(above(n))
        elif n not in neighbors:
            continue
        elif isinstance(block, RedstoneWireBlock):
            out[("wire", n)] = block.calculate_target_strength(level, n)
        elif isinstance(block, DiodeBlock):
            out[(name, n)] = block.get_input_signal(level, n, state)
        elif isinstance(block, RedstoneTorchBlock):
            out[("torch", n)] = block.has_neighbor_signal(level, n, state)
        elif name in SIMPLE_READERS or "rail" in name or "door" in name or "gate" in name:
            out[(name, n)] = level.has_neighbor_signal(n)
    return out


def glass_effect(path: Any, positions: list[Pos]) -> dict[Pos, list[tuple[int, str]]]:
    """Per conductor (built position): the ticks at which some component would read a
    different input if the block were glass, with the reader's kind."""
    from redsim.world import blocks

    doc = canonical.rebuild(canonical.from_file(path))
    rec = replay.record(doc)
    moves: dict[int, list[tuple[Pos, Pos]]] = {}
    for event in rec.events:
        for m in event.moved:
            moves.setdefault(event.tick, []).append((m.origin, m.dest))
    where = {p: p for p in positions}
    origin = {p: p for p in positions}
    glass = blocks.parse_state(ablation.GLASS)
    out: dict[Pos, list[tuple[int, str]]] = {p: [] for p in positions}
    for tick in range(doc.end_tick + 1):
        doc.seek_tick(tick)
        level = doc.level
        for p in positions:
            cell = where[p]
            state = level.get_block_state(cell)
            if state.is_air or not state.is_redstone_conductor(level, cell):
                continue  # moving (a moving-piston placeholder) or gone
            before = inputs_around(level, cell)
            level.blocks[cell] = glass
            try:
                after = inputs_around(level, cell)
            finally:
                level.blocks[cell] = state
            for key in before:
                if before[key] != after.get(key):
                    out[p].append((tick, key[0]))
        for src, dst in moves.get(tick + 1, []):
            p = origin.pop(src, None)
            if p is not None:
                where[p] = dst
                origin[dst] = p
    return out


def effect_role(effect: list[tuple[int, str]]) -> str:
    if not effect:
        return "none"
    kinds = sorted({k for _, k in effect})
    ticks = sorted({t for t, _ in effect})
    return "+".join(kinds) + " @" + _runs(ticks)


def _runs(ticks: list[int]) -> str:
    runs: list[str] = []
    start = prev = ticks[0]
    for t in ticks[1:] + [None]:  # type: ignore[list-item]
        if t is not None and t == prev + 1:
            prev = t
            continue
        runs.append(str(start) if start == prev else f"{start}-{prev}")
        if t is not None:
            start = prev = t
    return ",".join(runs)


GROUPS = (
    "decisive",
    "cutter",
    "step",
    "stopper",
    "support",
    "redundant",
    "unread",
    "immovable",
    "none",
)


def group(role: str) -> str:
    """The role's class for scoring: a structural role first, else the read role."""
    for key in ("cutter", "step", "stopper", "support"):
        if key in role:
            return key
    return "decisive" if role.startswith("decisive") else role


def predicted(role: str) -> bool:
    """Does layer 2 expect the glass change to break the door (or its timing)?"""
    return group(role) in ("decisive", "cutter", "step", "stopper", "support")


def predict(path: Any, positions: list[Pos]) -> dict[Pos, str]:
    """Layer 2's verdict per conductor: the counterfactual's readers and ticks, else a
    structural role (``stopper``, ``support``), else ``none``."""
    effect = glass_effect(path, positions)
    doc = canonical.rebuild(canonical.from_file(path))
    rec = replay.record(doc)
    reads = trace_reads(doc)
    doc.seek_tick(0)
    graph = read_graph(reads, doc.level, rec)
    sinks = mechanism_pistons(path)
    queued: dict[Pos, list[int]] = {}
    for r in reads:
        if r.queues and r.conductor:
            queued.setdefault(r.origin, []).append(r.tick)
    out: dict[Pos, str] = {}
    for p in positions:
        parts = []
        role = effect_role(effect[p])
        if role != "none":
            parts.append(role)
        if p in queued:
            parts.append("queues @" + _runs(sorted(set(queued[p]))))
        if parts:
            cells = set(cells_of(rec, p))
            parts.append("reaches mechanism" if reaches(graph, cells, sinks) else "dead end")
        parts += [
            r for r in structural_roles(doc.level, rec, p) if r in ("stopper", "support", "falling")
        ]
        out[p] = ", ".join(parts) if parts else "none"
    return out


def verdict(role: str) -> str:
    """The predicted class: ``read`` (some reader's input changes), ``stopper``,
    ``support`` or ``none``."""
    if "@" in role:
        return "read" if "reaches mechanism" in role else "dead end"
    for key in ("stopper", "support", "falling"):
        if key in role:
            return key
    return "none"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worlds", nargs="+")
    parser.add_argument("--out", help="folder with the saved ablation results")
    parser.add_argument("--predict", action="store_true", help="score the roles (needs --out)")
    parser.add_argument("--reads", action="store_true", help="with --predict: also the read roles")
    parser.add_argument("--json", help="write every read of the run (one world)")
    parser.add_argument("--list", action="store_true", help="print the roles per block")
    args = parser.parse_args()
    total: Counter[tuple[str, str]] = Counter()
    total_reads: Counter[tuple[str, bool]] = Counter()
    for name in args.worlds:
        path = corpus.find(name)
        slug = corpus.parse_name(path).slug
        if args.predict:
            with open(f"{args.out}/{slug}.json") as handle:
                saved = json.load(handle)["results"]
            glass = {tuple(r["pos"]): r["result"] for r in saved if r["change"] == "glass"}
            cells = sorted(glass, key=lambda q: (q[1], q[2], q[0]))
            role_of = predict(path, cells)
            score: Counter[tuple[str, str]] = Counter()
            for p, res in glass.items():
                score[(verdict(role_of[p]), _outcome(res))] += 1
            total.update(score)
            print(f"{slug}: " + _table(score))
            if args.list:
                for p in cells:
                    res = glass[p]
                    wrong = (verdict(role_of[p]) in ("read", "stopper", "support", "falling")) != (
                        _outcome(res) == "breaks"
                    )
                    mark = "  <-- wrong" if wrong else ""
                    print(f"  {p[0]} {p[1]} {p[2]}: {role_of[p]} -> {res}{mark}")
            if args.reads:
                read_role, _ = roles(path, cells)
                rs: Counter[tuple[str, bool]] = Counter()
                for p, res in glass.items():
                    rs[(group(read_role[p]), res in ("breaks", "timing"))] += 1
                total_reads.update(rs)
                print("  reads: " + _line(rs))
            continue
        doc = canonical.rebuild(canonical.from_file(path))
        reads = trace_reads(doc)
        kinds = Counter(r.kind for r in reads)
        decisive = Counter(r.kind for r in reads if r.decisive)
        targets = {r.origin for r in reads if r.conductor}
        decisive_targets = {r.origin for r in reads if r.conductor and r.decisive}
        print(
            f"{slug}: {len(reads)} reads, {len(targets)} conductors read, "
            f"{len(decisive_targets)} of them decisively; readers: "
            + ", ".join(f"{k} {decisive[k]}/{n}" for k, n in kinds.most_common())
        )
        if args.json:
            with open(args.json, "w") as handle:
                json.dump([r.to_json() for r in reads], handle, indent=0)
    if args.predict and len(args.worlds) > 1:
        print("total: " + _table(total))
        if args.reads:
            print("  reads: " + _line(total_reads))


def _outcome(result: str) -> str:
    return "breaks" if result in ("breaks", "timing") else result


def _table(score: Counter[tuple[str, str]]) -> str:
    """Per predicted class: how many variants broke the door, changed only other blocks
    (internal) or changed nothing (inert)."""
    parts = []
    for key in ("read", "dead end", "stopper", "support", "falling", "none"):
        n = sum(v for (k, _), v in score.items() if k == key)
        if n:
            parts.append(
                f"{key} {n}: {score[(key, 'breaks')]} break, "
                f"{score[(key, 'internal')]} internal, {score[(key, 'inert')]} inert"
            )
    return "; ".join(parts)


def _line(score: Counter[tuple[str, bool]]) -> str:
    return ", ".join(
        f"{k} {score[(k, True)]} of {score[(k, True)] + score[(k, False)]} break"
        for k in GROUPS
        if score[(k, True)] + score[(k, False)]
    )


if __name__ == "__main__":
    main()
