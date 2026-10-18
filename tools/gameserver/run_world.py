"""Run a whole world file on the sandboxed server and compare it with the simulator.

The world's build (tick 0) is rebuilt with ``/setblock … strict`` (no updates, no
``onPlace``: every block exactly as saved, like a world that loads), then its recorded lever
pulls are replayed and every block that is there or changes is compared after every tick.

A build with pending scheduled ticks or block events is first settled (the editor's
``settle``: simulated alone until quiet), since a strict build cannot hold them.

A lever or button needs a player, which the server does not have. Each input with
recorded uses gets a stand-in that both sides run: a repeater pointing into the block
the input is on (it powers that block strongly and updates the blocks around it, as the
input does, a tick later) with a redstone block behind it that the edges put and
remove (for a wall input the repeater takes the input's place; a repeater needs a
sturdy block below, so glass goes there if it is air), or a redstone block in the
input's own place while it is on (it powers the input's neighbors but not the block it
is on). A button is on for its press time. The candidates are tried in that order, each
checked in the simulator first: the stand-in build must change every other block
exactly as the world with its real input does (shifted by the stand-in's delay, 0–3
ticks); the
first one that does is used, and the summary says if none did. Recorded ``/setblock``
edits (``at T set …``) run as the same command on both sides; other recorded edits are
not supported.

Usage (from the repository root)::

    python -m tools.gameserver.run_world WORLD.redsim.json [--ticks N] [--name NAME]
        [--origin X,Y,Z]

Results go to ``.sandbox/worlds/NAME.json`` (third-party worlds stay out of the
repository); the summary names the first mismatching ticks and positions.
"""

from __future__ import annotations

import argparse
import dataclasses
import re
import sys
from pathlib import Path
from typing import Any

from redsim.core.direction import HORIZONTAL, Direction
from redsim.core.pos import Pos, below, offset
from redsim.editor.document import Document
from redsim.world.blocks.attached import ButtonBlock, LeverBlock
from redsim.world.properties import ATTACH_FACE, HORIZONTAL_FACING, POWERED
from tools.gameserver.compare import Scenario, compare, run_sim
from tools.gameserver.server import REPO_ROOT, GameServer

OUT_DIR = REPO_ROOT / ".sandbox" / "worlds"
RB = "minecraft:redstone_block"
AIR = "minecraft:air"
GLASS = "minecraft:glass"


def _is_input(state: Any) -> bool:
    return isinstance(state.block, (LeverBlock, ButtonBlock))


def _transitions(state: Any, ticks: list[int], release: int = 0) -> list[tuple[int, bool]]:
    """When the input turns on / off: a lever flips at each use; a button is pressed for
    its time (a press while it is still pressed does nothing). ``release``: ticks added
    to a button's release (it happens inside a tick, an edit between two)."""
    on = bool(state.get(POWERED))
    out: list[tuple[int, bool]] = []
    if isinstance(state.block, LeverBlock):
        for t in ticks:
            on = not on
            out.append((t, on))
        return out
    until = -1
    for t in ticks:
        if t >= until:
            until = t + state.block.ticks_to_stay_pressed
            out += [(t, True), (until + release, False)]
    return out


def _stand_ins(
    pos: Pos,
    state: Any,
    ticks: list[int],
    states: dict[Pos, Any],
    level: Any,
    after: Any = None,
) -> list[Any]:
    """Candidate stand-ins for one input, best first: (label, replaced blocks, the
    /setblock edges by tick)."""
    changes = _transitions(state, ticks)
    on0 = bool(state.get(POWERED))
    off = repr(state.with_(POWERED, False))
    face = state.get(ATTACH_FACE)
    facing: Direction = state.get(HORIZONTAL_FACING)
    side = {"floor": Direction.DOWN, "ceiling": Direction.UP}.get(face, facing.opposite)
    attached = offset(pos, side)

    def repeater(d: Direction) -> Any:
        at, behind = offset(attached, d), offset(attached, d, 2)
        if (at != pos and at in states) or behind in states:
            return None
        extra: dict[Pos, str] = {}
        support = below(at)
        if support not in states:
            extra[support] = GLASS
        elif not states[support].is_face_sturdy(level, support, Direction.UP):
            return None
        extra[at] = (
            f"minecraft:repeater[facing={d.serialized},delay=1,locked=false,"
            f"powered={str(on0).lower()}]"
        )
        if on0:
            extra[behind] = RB
            if at != pos:
                extra[pos] = off
        edges = [(t, behind, RB if on else AIR) for t, on in changes]
        return (f"a repeater into {attached} from the {d.serialized}", extra, edges)

    # /setblock of the input itself acts between ticks, like a player, but updates only
    # its own neighbors (the input's ``updateNeighbours`` also updates those of the
    # block it is on). So the block it is on is set to another conductor and back in
    # the same moment.
    on_state = repr(state.with_(POWERED, True))
    base = states.get(attached)

    def swaps(t: int) -> list[tuple[Any, ...]]:
        # Back to the state the block has right after the real input's change (a
        # dropper it is on is triggered): ``after`` reads the simulator's reference run.
        if base is None:
            return []
        other = "minecraft:stone" if base.block.id != "minecraft:stone" else "minecraft:cobblestone"
        back = (after(t, attached) if after else None) or repr(base)
        entity = level.get_block_entity(attached, create=False)
        data = entity.to_json() if entity is not None else {}
        return [(t, attached, other), (t, attached, back, data) if data else (t, attached, back)]

    commands = []
    button = isinstance(state.block, ButtonBlock)
    for release in (-1, 0) if button else (0,):
        moves = _transitions(state, ticks, release)
        note = f" (released {-release} tick early)" if release else ""
        if base is not None:
            commands.append((
                f"/setblock of the input, the block it is on swapped and back{note}",
                {},
                [e for t, on in moves for e in [(t, pos, on_state if on else off), *swaps(t)]],
            ))  # fmt: skip
        commands.append(
            (f"/setblock of the input{note}", {},
             [(t, pos, on_state if on else off) for t, on in moves])
        )  # fmt: skip
    block = (
        "a redstone block in its place while it is on",
        {pos: RB} if on0 else {},
        [(t, pos, RB if on else off) for t, on in changes],
    )
    sides = [d for d in HORIZONTAL if not (face == "wall" and d == facing)]
    candidates = [*commands]
    candidates += [repeater(facing)] if face == "wall" else []
    candidates += [block, *(repeater(d) for d in sides)]
    return [c for c in candidates if c is not None]


def build_scenario(path: Path, name: str, ticks: int | None = None) -> Scenario:
    doc = Document.open(path)
    edits = [(doc.edit_ticks.get(i, 0), doc.history.inputs[i]) for i in sorted(doc.history.inputs)]
    doc.seek_tick(0)
    level = doc.level
    if level.block_ticks.pending() or level.block_events or level.entities:
        # A strict build cannot hold pending ticks: settle it first (the editor's
        # ``settle``; the recorded pulls keep their ticks).
        settled = doc.settle_build()
        if settled is None:
            raise SystemExit("the build has pending activity and does not settle")
        print(f"{path.name}: the build settled first ({settled} ticks)")
        doc.seek_tick(0)
        level = doc.level
    states = {pos: state for pos, state in level.iter_blocks() if not state.is_air}
    above = [pos for pos in states if pos[1] >= 1]
    x0, x1 = min(p[0] for p in above) - 1, max(p[0] for p in above) + 1
    z0, z1 = min(p[2] for p in above) - 1, max(p[2] for p in above) + 1
    corner = (x0, 0, z0)

    def rel(pos: Pos) -> Pos:
        return (pos[0] - corner[0], pos[1], pos[2] - corner[2])

    # Each lever or button with recorded uses gets a stand-in (see the module text).
    flips: dict[int, list[tuple[Any, ...]]] = {}
    replaced: dict[Pos, str] = {}
    inputs: dict[Pos, list[int]] = {}
    for tick, action in edits:
        if action.kind == "setblock" and action.state and not action.payload:
            # A recorded /setblock (e.g. a redstone block switching a stand-in input):
            # both sides run the same command.
            flips.setdefault(tick, []).append((rel(action.pos), action.state))
            continue
        state = states.get(action.pos)
        if action.kind != "use" or state is None or not _is_input(state):
            raise SystemExit(
                f"unsupported recorded edit at tick {tick}: {action.kind} {action.pos}"
            )
        inputs.setdefault(action.pos, []).append(tick)
    end = max([0, *flips, *(t for ticks_ in inputs.values() for t in ticks_)]) + 60
    end = end if ticks is None else ticks
    size = (x1 - x0 + 1, z1 - z0 + 1)
    top = max(p[1] for p in above) + 2
    box = [(x, y, z) for x in range(size[0]) for y in range(1, top) for z in range(size[1])]

    def setup_of(replaced_: dict[Pos, str]) -> list[tuple[Any, ...]]:
        out: list[tuple[Any, ...]] = []
        for pos, state in sorted(states.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            if not (x0 <= pos[0] <= x1 and z0 <= pos[2] <= z1) or pos in replaced_:
                continue
            entity = level.get_block_entity(pos, create=False)
            data = entity.to_json() if entity is not None else {}
            out.append((rel(pos), repr(state), data) if data else (rel(pos), repr(state)))
        return out + [(rel(pos), text) for pos, text in replaced_.items() if text != AIR]

    def frames_of(replaced_: dict[Pos, str], flips_: dict[int, list[tuple[Any, ...]]],
                  uses: dict[int, list[Pos]]) -> list[dict[str, str]]:  # fmt: skip
        trial = Scenario(name=name, description="", size=size, setup=setup_of(replaced_),
                         watch=box, ticks=end + 2, inputs=flips_, strict_setup=True)  # fmt: skip
        return run_sim(trial, (0, 0, 0), 0, uses)

    for pos, ticks_ in inputs.items():
        state = states[pos]
        uses_left = {t: [rel(p) for p, ts in inputs.items() if t in ts and p != pos]
                     for t in range(end)}  # fmt: skip
        reference = frames_of(replaced, flips, {t: [*uses_left[t], *([rel(pos)] * ticks_.count(t))]
                                                for t in range(end)})  # fmt: skip
        chosen = None

        def after(t: int, cell: Pos, reference: list[dict[str, str]] = reference) -> str | None:
            return reference[t + 1].get(str(rel(cell))) if t + 1 < len(reference) else None

        for label, extra, edges in _stand_ins(pos, state, ticks_, states, level, after):
            trial_flips = {t: list(v) for t, v in flips.items()}
            for t, cell, *text in edges:
                trial_flips.setdefault(t, []).append((rel(cell), *text))
            frames = frames_of({**replaced, **extra}, trial_flips, uses_left)
            skip = {str(rel(p)) for p in (*extra, pos, *(e[1] for e in edges))}
            # The delay of the stand-in: the first shift at which every other block
            # changes as with the real input.
            same = next(
                (
                    d
                    for d in range(4)
                    if all(
                        reference[t].get(k) == frames[t + d].get(k)
                        for t in range(len(reference) - d)
                        for k in set(reference[t]) | set(frames[t + d])
                        if k.split("#")[0] not in skip
                    )
                ),
                None,
            )
            if chosen is None or same is not None:
                chosen = (label, extra, trial_flips, same)
            if same is not None:
                break
        if chosen is None:
            raise SystemExit(f"no room for a stand-in of the input at {pos}")
        label, extra, flips, same = chosen
        replaced.update(extra)
        verdict = (
            f"behaves as the input, {same} ticks later,"
            if same is not None
            else "NOT as the input (no faithful stand-in)"
        )
        print(f"{path.name}: input at {pos}: {label}, {verdict} in the simulator")

    setup = setup_of(replaced)
    watch = sorted({rel(pos) for pos in states if pos[1] >= 1 and x0 <= pos[0] <= x1
                    and z0 <= pos[2] <= z1} | {e[0] for e in setup if e[0][1] >= 1})  # fmt: skip
    scenario = Scenario(
        name=name,
        description=f"{path.name}: the build by /setblock strict, lever pulls at {sorted(flips)}",
        size=size,
        setup=setup,
        watch=watch,
        ticks=end,
        inputs=flips,
        watch_entities=True,
        strict_setup=True,
    )
    # Also watch what changes in the simulator (blocks pushed into air, …).
    frames = run_sim(scenario, (0, 0, 0), 0)
    changed = {
        key for before, after in zip(frames, frames[1:], strict=False) for key in after
        if before.get(key) != after.get(key) and key.startswith("(") and "#" not in key
    }  # fmt: skip
    extra = {tuple(int(v) for v in key.strip("()").split(",")) for key in changed}
    watch = sorted(set(scenario.watch) | {(p[0], p[1], p[2]) for p in extra})
    return dataclasses.replace(scenario, watch=watch)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("world", type=Path)
    parser.add_argument("--ticks", type=int)
    parser.add_argument("--name")
    parser.add_argument(
        "--origin",
        default="0,0,0",
        help="X,Y,Z where the build's corner goes on both sides (default 0,0,0): to compare "
        "locational behavior, run the same world at two origins",
    )
    args = parser.parse_args(argv)
    origin = tuple(int(v) for v in args.origin.split(","))
    name = args.name or re.sub(r"[^a-z0-9]+", "_", args.world.stem.lower()).strip("_")
    scenario = build_scenario(args.world, name, args.ticks)
    print(f"{name}: {len(scenario.setup)} blocks, {len(scenario.watch)} watched, "
          f"{scenario.ticks} ticks")  # fmt: skip
    with GameServer(fresh_world=True) as server:
        ox, _, oz = origin
        server.command(f"forceload add {ox - 16} {oz - 16} {ox + 64} {oz + 64}")
        result = compare(server, scenario, origin, results_dir=OUT_DIR)
    verdict = "MATCH" if result["match"] else "MISMATCH"
    print(f"{name}: {verdict}; results in {OUT_DIR / (name + '.json')}")
    if not result["match"]:
        shown = 0
        for frame in result["frames"]:
            for key in frame["mismatches"]:
                if shown < 40:
                    print(f"  tick {frame['tick']:3d} {key}: sim={frame['sim'].get(key)} "
                          f"game={frame['game'].get(key)}")  # fmt: skip
                shown += 1
        print(f"  ({shown} mismatching values in all)")
    return 0 if result["match"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
