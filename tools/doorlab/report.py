"""A door's analysis as a Markdown page (``python -m tools.doorlab.report WORLD``).

The generated part of doc/redstone/doors/analyses/*.md: the facts (frames, groups, pistons,
power access, phases) from ``analysis.analyze``. The engineering explanation above them is
written by hand from these facts and kept between the markers ``<!-- generated -->`` and
``<!-- end generated -->``, so regenerating keeps it.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tools.doorlab import analysis, corpus, interactions

OUT = corpus.ROOT / "doc" / "redstone" / "doors" / "analyses"
BEGIN, END = "<!-- generated -->", "<!-- end generated -->"


def _grids(a: dict[str, Any], way: interactions.Doorway, limit: int = 40) -> list[str]:
    """The doorway at the ticks where it changes, side by side (``Doorway.grid``)."""
    frames = a["frames"]
    if not frames:
        return []
    ticks = [0] + [t for t in range(1, len(frames)) if frames[t] != frames[t - 1]]
    ticks = ticks[:limit]
    blocks = []
    for t in ticks:
        fill = dict(zip(way.cells, frames[t], strict=True))
        grid = way.grid(fill)
        blocks.append([f"{t:>{way.width}}"[: max(way.width, len(str(t)))]] + grid)
    out = []
    per_line = max(1, 72 // (max(way.width, 3) + 2))
    for start in range(0, len(blocks), per_line):
        chunk = blocks[start : start + per_line]
        width = max(len(b[0]) for b in chunk)
        for row in range(len(chunk[0])):
            out.append("  ".join(b[row].ljust(width) for b in chunk).rstrip())
        out.append("")
    return out


def generated(a: dict[str, Any]) -> str:
    cells = [tuple(c) for c in a["doorway"]["cells"]]
    way = interactions.doorway(cells)
    ref = a["reference_ticks"]
    lines = [BEGIN, "", "### Facts from the replay (generated)", ""]
    lines.append(
        f"- Doorway: {way.width}×{way.height} in the plane {way.normal} = "
        f"{way.plane}; {len(a['doorway']['extra_cells'])} more output cells "
        "outside it."
    )
    lines.append(
        "- Timeline: "
        + ", ".join(f"{x['what']} at {x['tick']}" for x in a["actions"])
        + "; markers "
        + ", ".join(f"{n} {t}" for t, n in a["markers"].items())
    )
    lines.append(
        f"- Reference states: closed at tick {ref['closed']}, open at tick "
        f"{ref['open']}. Fully closed at ticks {analysis._runs(a['closed_ticks'])}; "
        f"fully open at {analysis._runs(a['open_ticks'])}."
    )
    lines.append(
        "- Pistons by role: " + ", ".join(f"{k} {v}" for k, v in sorted(a["piston_roles"].items()))
    )
    lines.append(
        "- How extensions were powered (block giving the signal; QC = through the "
        "block above the piston): " + ", ".join(f"{k} {v}" for k, v in a["power_access"].items())
    )
    lines.append(
        "- Phases (bursts of piston events): "
        + "; ".join(
            f"{p['from']}–{p['to']} ({p['events']} events, {p['pistons']} pistons)"
            for p in a["phases"]
        )
    )
    lines += [
        "",
        "Doorway frames when they change (`#` solid, `.` open, `~` moving; tick "
        "above each; columns north → south for a door across x, west → east across z):",
        "",
        "```",
    ]
    lines += _grids(a, way)
    lines += [
        "```",
        "",
        "Groups (door blocks by the side they leave through):",
        "",
        "| exit | blocks | pistons | moves per block | closed → open |",
        "|---|---|---|---|---|",
    ]
    for g in a["groups"]:
        moves = ", ".join(f"{k}×{v}" for k, v in sorted(g["moves_per_block"].items()))
        dirs = ", ".join(f"{k} ({v})" for k, v in g["closed_to_open"].items())
        lines.append(f"| {g['exit']} | {g['blocks']} | {len(g['pistons'])} | {moves} | {dirs} |")
    lines += [
        "",
        "Pistons that fire (role, pulses as start+length → end):",
        "",
        "| piston | facing | role | pulses | power |",
        "|---|---|---|---|---|",
    ]
    for p in a["pistons"]:
        if not p["fires"]:
            continue
        pulses = ", ".join(
            f"{q['start']}+{q['length']}→{q['end']}"
            if q.get("start") is not None
            else f"{q['end']} at {q.get('at')}"
            for q in p["pulses"]
        )
        power = ", ".join(f"{k} {v}" for k, v in p["power"].items())
        pos = " ".join(map(str, p["pos"]))
        lines.append(
            f"| {pos}{' S' if p['sticky'] else ''} | {p['facing']} | {p['role']} | "
            f"{pulses} | {power} |"
        )
    lines += ["", END]
    return "\n".join(lines)


def write(path: Path, a: dict[str, Any]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{a['world']}.md"
    body = generated(a)
    if target.exists():
        text = target.read_text()
        if BEGIN in text and END in text:
            head, rest = text.split(BEGIN, 1)
            tail = rest.split(END, 1)[1]
            target.write_text(head + body + tail)
            return target
    title = f"# {a['title']} by {a['creator']}"
    intro = (
        f"\nWorld: `{path.relative_to(corpus.DATASET)}` (not committed). Analysis by "
        "`python -m tools.doorlab.report` (facts) and by hand (explanation).\n\n"
        "## How it works\n\n(to be written)\n\n"
    )
    target.write_text(title + "\n" + intro + body + "\n")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worlds", nargs="+", help="slugs or file-name parts")
    args = parser.parse_args()
    for name in args.worlds:
        path = corpus.find(name)
        target = write(path, analysis.analyze(path))
        print(f"wrote {target.relative_to(corpus.ROOT)}")


if __name__ == "__main__":
    main()
