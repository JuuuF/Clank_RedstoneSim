"""Check a world written by File → Save as Minecraft world… in the real game.

Opens a save (default: the example save), edits it like a user would (a repeater with a
pending tick, a sign with text, a removed redstone wire), writes it as a copy into its own
sandbox folder (``.sandbox/worldcheck/world``), starts the sandboxed dedicated server on
that copy and checks: the edited blocks are there, the sign's text was kept, and the
pending tick runs (the repeater turns on after its delay).

Usage (from the repository root)::

    python -m tools.gameserver.check_world_copy [save folder]
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from redsim.mcworld.importer import open_world
from redsim.mcworld.writer import save_world_copy
from redsim.world import blocks
from tools.gameserver.server import REPO_ROOT, GameServer

SANDBOX = REPO_ROOT / ".sandbox" / "worldcheck"
DEFAULT_SAVE = REPO_ROOT / "data" / "minecraft_saves" / "Redstone"


def main(argv: list[str]) -> int:
    save = Path(argv[0]) if argv else DEFAULT_SAVE
    opened = open_world(save, radius=2)
    doc = opened.document
    assert opened.info.player_pos is not None
    x, y, z = (int(v) for v in opened.info.player_pos)
    y += 6  # in the air above the player
    stone, repeater, source = (x, y, z), (x, y + 1, z), (x + 1, y + 1, z)
    sign_support, sign = (x + 3, y, z), (x + 3, y + 1, z)
    doc.setblock(stone, blocks.STONE.default_state)
    doc.setblock(repeater, blocks.parse_state("repeater[facing=east,delay=4]"))
    doc.setblock(source, blocks.REDSTONE_BLOCK.default_state)  # the repeater's input
    doc.setblock(sign_support, blocks.STONE.default_state)
    doc.setblock(sign, blocks.parse_state("oak_sign[rotation=8]"))
    doc.set_sign_text(sign, "front", ["redsim", "check"])
    wire = next(p for p, s in doc.level.blocks.items() if s.is_(blocks.REDSTONE_WIRE))
    doc.break_block(wire)
    pending = [t for t in doc.level.block_ticks.pending() if t.pos == repeater]
    delay = pending[0].trigger_tick - doc.level.game_time if pending else None
    print(f"edits near {x} {y} {z}; repeater tick in {delay} ticks; wire removed at {wire}")
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)
    report = save_world_copy(doc, SANDBOX / "world")
    print(f"written: {report.blocks} blocks in {report.chunks} chunks")

    failures = []
    with GameServer(sandbox=SANDBOX) as server:
        for pos in (stone, sign, wire):
            server.command(f"forceload add {pos[0]} {pos[2]}")
        expected = {
            stone: "minecraft:stone",
            repeater: "minecraft:repeater[facing=east,delay=4,powered=false]",
            source: "minecraft:redstone_block",
            sign: "minecraft:oak_sign[rotation=8]",
            wire: "minecraft:air",
        }
        verdicts = server.test_blocks(list(expected.items()))
        for (pos, state), ok in zip(expected.items(), verdicts, strict=True):
            print(f"{'ok  ' if ok else 'FAIL'} {pos} {state}")
            if not ok:
                failures.append(f"{pos} is not {state}")
        text = server.command(
            f"data get block {sign[0]} {sign[1]} {sign[2]} front_text.messages[0]"
        ).text
        ok = "redsim" in text
        print(f"{'ok  ' if ok else 'FAIL'} sign text: {text.strip()[-60:]}")
        if not ok:
            failures.append("sign text lost")
        if delay is not None:
            server.step(delay)
            powered = server.test_blocks([(repeater, "minecraft:repeater[powered=true]")])[0]
            print(f"{'ok  ' if powered else 'FAIL'} the pending tick ran after {delay} ticks")
            if not powered:
                failures.append("pending tick did not run")
    print("MATCH" if not failures else "MISMATCH: " + "; ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
