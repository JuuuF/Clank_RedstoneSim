"""Run a whole world file on the sandboxed server and compare it with the simulator.

The world's build (tick 0) is rebuilt with ``/setblock … strict`` (no updates, no
``onPlace``: every block exactly as saved, like a world that loads), then its recorded lever
pulls are replayed and every block that is there or changes is compared after every tick.

A build with pending scheduled ticks or block events is first settled (the editor's
``settle``: simulated alone until quiet), since a strict build cannot hold them.

A lever needs a player, which the server does not have: each wall lever with recorded
pulls is replaced by a repeater pointing into the lever's block (it powers that block
strongly and updates the blocks around it, as the lever does, 2 ticks later) with a
redstone block behind it that the pulls put and remove; a repeater needs a sturdy block
below, so glass goes there if it is air. Both sides run that same build. Recorded
``/setblock`` edits (``at T set …``) run as the same command on both sides; other recorded
edits are not supported.

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

from redsim.core.direction import Direction
from redsim.core.pos import Pos, below, offset
from redsim.editor.document import Document
from redsim.world.properties import ATTACH_FACE, HORIZONTAL_FACING, POWERED
from tools.gameserver.compare import Scenario, compare, run_sim
from tools.gameserver.server import REPO_ROOT, GameServer

OUT_DIR = REPO_ROOT / ".sandbox" / "worlds"
RB = "minecraft:redstone_block"
AIR = "minecraft:air"


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

    # The lever pulls become a repeater and a redstone block behind it.
    flips: dict[int, list[tuple[Pos, str]]] = {}
    replaced: dict[Pos, str] = {}
    lever_on: dict[Pos, bool] = {}
    for tick, action in edits:
        if action.kind == "setblock" and action.state and not action.payload:
            # A recorded /setblock (e.g. a redstone block switching a stand-in input):
            # both sides run the same command.
            flips.setdefault(tick, []).append((rel(action.pos), action.state))
            continue
        state = states.get(action.pos)
        if action.kind != "use" or state is None or state.block.id != "minecraft:lever":
            raise SystemExit(
                f"unsupported recorded edit at tick {tick}: {action.kind} {action.pos}"
            )
        if state.get(ATTACH_FACE) != "wall":
            raise SystemExit(f"the lever at {action.pos} is not on a wall")
        facing: Direction = state.get(HORIZONTAL_FACING)
        behind = offset(action.pos, facing)
        if action.pos not in replaced:
            powered = bool(state.get(POWERED))
            replaced[action.pos] = (
                f"minecraft:repeater[facing={facing.serialized},delay=1,locked=false,"
                f"powered={str(powered).lower()}]"
            )
            if behind in states:
                raise SystemExit(f"no room behind the lever at {action.pos}")
            if powered:
                replaced[behind] = RB
            support = below(action.pos)
            if support not in states:
                replaced[support] = "minecraft:glass"
            elif not states[support].is_face_sturdy(level, support, Direction.UP):
                raise SystemExit(f"the block under the lever at {action.pos} holds no repeater")
            lever_on[action.pos] = powered
        lever_on[action.pos] = not lever_on[action.pos]
        flips.setdefault(tick, []).append((rel(behind), RB if lever_on[action.pos] else AIR))

    setup: list[tuple[Any, ...]] = []
    for pos, state in sorted(states.items(), key=lambda item: (item[0][1], item[0][2], item[0][0])):
        if not (x0 <= pos[0] <= x1 and z0 <= pos[2] <= z1) or pos in replaced:
            continue
        entity = level.get_block_entity(pos, create=False)
        data = entity.to_json() if entity is not None else {}
        setup.append((rel(pos), repr(state), data) if data else (rel(pos), repr(state)))
    setup += [(rel(pos), text) for pos, text in replaced.items()]
    end = max([0, *flips]) + 60 if ticks is None else ticks
    size = (x1 - x0 + 1, z1 - z0 + 1)
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
