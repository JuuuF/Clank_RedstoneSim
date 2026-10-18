"""The mechanisms each world uses, counted from its replay
(``python -m tools.doorlab.patterns``: prints the table of doc/redstone/doors/patterns.md).

Per world, from ``analysis.analyze``:

- **speed**: ticks from each lever action to the next fully closed / fully open doorway;
- **size**: doorway cells, the box above the floor (volume), pistons that fire;
- **spits**: retracts that ended an extension early and left the block (short pulses);
- **QC**: extensions powered only through the block above the piston;
- **landings**: extensions of a piston that another piston had just moved (it lands next
  to power and extends by itself: the landing check);
- **switches / sliders / rb**: pistons moving a conductor that powers another piston,
  moved observers, moved redstone blocks;
- **slime**: moved slime or honey blocks;
- **depth**: the most pistons that move one door block (an extender's stages plus the
  pistons that hand it on);
- **moves**: the most moves of one door block.
"""

from __future__ import annotations

import json
from typing import Any

from tools.doorlab import analysis, corpus, interactions


def _times(a: dict[str, Any]) -> list[str]:
    """For each action: how long until the doorway reaches a full end state."""
    frames = a["frames"]
    out = []
    for action in a["actions"]:
        t0 = action["tick"]
        for t in range(t0 + 1, len(frames)):
            if frames[t] != frames[t0] and set(frames[t]) in ({"#"}, {"."}):
                out.append(f"{'closed' if frames[t][0] == '#' else 'open'} {t - t0}")
                break
        else:
            out.append("—")
    return out


def row(a: dict[str, Any], census: dict[str, Any]) -> dict[str, Any]:
    events = a["events"]
    moved_pistons: set[tuple[int, int, int]] = set()
    landings = 0
    for e in events:
        if e["kind"] == "extend" and tuple(e["piston"]) in moved_pistons:
            landings += 1
        for m in e["moved"]:
            if interactions.block_id(m["state"]) in ("piston", "sticky_piston"):
                moved_pistons.add(tuple(m["to"]))
    moved = [interactions.block_id(m["state"]) for e in events for m in e["moved"]]
    return {
        "world": a["world"],
        "door": f"{a['doorway']['width']}x{a['doorway']['height']}",
        "volume": census["volume"],
        "fire": sum(1 for p in a["pistons"] if p["fires"]),
        "times": _times(a),
        "extensions": sum(1 for e in events if e["kind"] == "extend"),
        "spits": sum(1 for e in events if e["outcome"] == "spat"),
        "qc": sum(1 for e in events if e.get("power", {}).get("quasi")),
        "landings": landings,
        "switches": a["piston_roles"].get("power switch", 0),
        "observers_moved": moved.count("observer"),
        "rb_moved": moved.count("redstone_block"),
        "slime_moved": sum(1 for m in moved if m in ("slime_block", "honey_block")),
        "depth": max((len(b["pistons"]) for b in a["door_blocks"]), default=0),
        "moves": max((b["moves"] for b in a["door_blocks"]), default=0),
        "groups": {g["exit"]: g["blocks"] for g in a["groups"]},
    }


def table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| world | door | volume | pistons firing | lever → state | ext | spits | QC | "
        "landings | switches | observers moved | redstone blocks moved | slime/honey moved |"
        " depth | moves |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['world']}` | {r['door']} | {r['volume']} | {r['fire']} | "
            f"{'; '.join(r['times'])} | {r['extensions']} | {r['spits']} | {r['qc']} | "
            f"{r['landings']} | {r['switches']} | {r['observers_moved']} | {r['rb_moved']} | "
            f"{r['slime_moved']} | {r['depth']} | {r['moves']} |"
        )
    return "\n".join(lines)


def main() -> None:
    rows = []
    for path in corpus.world_files():
        session = corpus.open_world(path)
        session.doc.seek_tick(0)
        census = interactions.census(session.doc.level)
        session.close()
        rows.append(row(analysis.analyze(path), census))
    print(table(rows))
    out = corpus.ROOT / "experiments" / "doors" / "patterns.json"
    out.write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
