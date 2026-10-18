"""The machine-readable catalog of the dataset.

    python -m tools.doorlab.inventory            # writes experiments/doors/inventory.json
                                                 # and doc/redstone/doors/inventory.md

Per world: where it is, who made it, what the file says (sections, timeline, markers,
notes), what it is made of (census), its doorway, and what a replay of its own timeline
shows (when the doorway is closed and open, the marker checks, the piston events). The
designs themselves stay in data/ (not committed); the catalog only holds facts about them.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from tools.doorlab import canonical, corpus, interactions, replay

OUT_JSON = corpus.ROOT / "experiments" / "doors" / "inventory.json"
OUT_MD = corpus.ROOT / "doc" / "redstone" / "doors" / "inventory.md"


def _positions(section: dict[str, Any] | None) -> list[tuple[int, int, int]]:
    if not section:
        return []
    return [tuple(p) for p in section.get("positions", [])]  # type: ignore[misc]


def entry(path: Path) -> dict[str, Any]:
    name = corpus.parse_name(path)
    started = time.perf_counter()
    session = corpus.open_world(path)
    doc = session.doc
    try:
        canon = canonical.from_document(doc)
        sections = canon["annotations"].get("sections", {})
        inputs = _positions(sections.get("input"))
        outputs = _positions(sections.get("output"))
        other_sections = {
            k: len(v.get("positions", []))
            for k, v in sections.items()
            if k not in ("input", "output") and v.get("positions")
        }
        base_level = doc.level
        doc.seek_tick(0)
        census = interactions.census(doc.level)
        way = interactions.doorway(outputs)
        inputs_info = [
            {"pos": list(p), "block": replay.short(repr(doc.level.get_block_state(p)))}
            for p in inputs
        ]
        build_cells = {p: replay.short(repr(doc.level.get_block_state(p))) for p in way.cells}
        materials = sorted({interactions.block_id(s) for s in build_cells.values()})
        runtime = canon["engine_runtime"]
        pending = {
            k: len(runtime[k])
            for k in ("scheduled_ticks", "block_events", "entities")
            if runtime.get(k)
        }
        rec = replay.record(doc)
        markers = {int(t): n for t, n in canon["annotations"].get("markers", {}).items()}
        summary = replay.doorway_summary(rec, way.cells)
        checks = replay.check_markers(rec, way.cells, markers)
        pistons_moving = sorted({e.piston for e in rec.events})
        actions = canon["timeline"]["actions"]
        result = {
            "id": name.slug,
            "file": str(path.relative_to(corpus.DATASET)),
            "category": corpus.category_of(path),
            "title": name.title,
            "creator": name.creator,
            "nominal_size": name.size,
            "broken_sim_in_name": name.broken_sim,
            "sha256": corpus.sha256(path),
            "bytes": path.stat().st_size,
            "game_version": canon["game_version"],
            "census": census,
            "inputs": inputs_info,
            "outputs": len(outputs),
            "other_sections": other_sections,
            "doorway": {
                **way.to_json(),
                "cells": len(way.cells),
                "materials_at_build": materials,
                "build_state": "closed"
                if all(replay.solid(s) for s in build_cells.values())
                else "open"
                if not any(replay.solid(s) for s in build_cells.values())
                else "partial",
            },
            "timeline": [
                {"tick": a["tick"], "kind": a["kind"], "pos": a.get("pos"), "label": a.get("label")}
                for a in actions
            ],
            "end_tick": canon["timeline"]["end_tick"],
            "markers": {str(t): n for t, n in sorted(markers.items())},
            "notes": canon["annotations"].get("notes", []),
            "build_pending": pending,
            "replay": {
                "piston_events": len(rec.events),
                "pistons_that_fire": len(pistons_moving),
                "pistons_total": census["kinds"].get("piston", 0)
                + census["kinds"].get("sticky_piston", 0),
                "outcomes": _count(e.outcome for e in rec.events),
                "quasi_connected_extensions": sum(
                    1 for e in rec.events if e.power and e.power.get("quasi")
                ),
                "closed_runs": _runs(summary["closed_ticks"]),
                "open_runs": _runs(summary["open_ticks"]),
                "marker_checks": [{k: v for k, v in c.items() if k != "frame"} for c in checks],
                "markers_ok": all(c.get("ok", True) for c in checks),
            },
            "seconds": round(time.perf_counter() - started, 2),
        }
        del base_level
        return result
    finally:
        session.close()


def _count(values: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


def _runs(ticks: list[int]) -> list[list[int]]:
    """[3, 4, 5, 9] → [[3, 5], [9, 9]]."""
    runs: list[list[int]] = []
    for t in ticks:
        if runs and runs[-1][1] == t - 1:
            runs[-1][1] = t
        else:
            runs.append([t, t])
    return runs


def markdown(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# The dataset: inventory",
        "",
        "Generated by `python -m tools.doorlab.inventory` from `data/redstone_learning/`",
        "(the worlds themselves are third-party designs and not committed; this page and",
        "`experiments/doors/inventory.json` hold facts about them). Minecraft Java 26.3.",
        "",
        "Columns: **doorway** = the output section read as a door (width × height, the",
        "axis across it); **box** = the blocks above the floor; **P/S** = pistons / sticky",
        "pistons; **fire** = pistons that receive a block event during the world's own",
        "timeline; **QC** = extensions powered only through quasi-connectivity; **closed**",
        "/ **open** = the ticks at which every doorway cell is solid / empty in the replay;",
        '**markers** = the world\'s own markers ("Closed", "Opened") agree with the',
        "replay.",
        "",
        "| world | creator | doorway | box | P/S | fire | QC | closed | open | markers |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        way = e["doorway"]
        kinds = e["census"]["kinds"]
        size = "×".join(str(v) for v in e["census"]["size"])
        door = f"{way['width']}×{way['height']} ({way['normal']})" if way["cells"] else "—"
        if way["extra_cells"]:
            door += f" +{len(way['extra_cells'])}"
        rp = e["replay"]
        closed = ", ".join(f"{a}–{b}" if a != b else str(a) for a, b in rp["closed_runs"])
        open_ = ", ".join(f"{a}–{b}" if a != b else str(a) for a, b in rp["open_runs"])
        ok = "yes" if rp["markers_ok"] else "**no**"
        lines.append(
            f"| {e['title']}{' ' + e['nominal_size'] if e['nominal_size'] else ''} "
            f"(`{e['id']}`) | {e['creator']} | {door} | {size} | "
            f"{kinds.get('piston', 0)}/{kinds.get('sticky_piston', 0)} | "
            f"{rp['pistons_that_fire']} | {rp['quasi_connected_extensions']} | {closed or '—'} "
            f"| {open_ or '—'} | {ok} |"
        )
    lines += ["", "## Per world", ""]
    for e in entries:
        lines.append(f"### {e['title']} by {e['creator']} (`{e['id']}`)")
        lines.append("")
        lines.append(f"- file: `{e['file']}` ({e['category']}), sha256 `{e['sha256'][:12]}…`")
        inputs = (
            ", ".join(
                f"{i['block'].split('[')[0]} at {' '.join(map(str, i['pos']))}" for i in e["inputs"]
            )
            or "none designated"
        )
        lines.append(
            f"- input: {inputs}; outputs: {e['outputs']} cells"
            + (f"; other sections: {e['other_sections']}" if e["other_sections"] else "")
        )
        way = e["doorway"]
        lines.append(
            f"- doorway at build: {way['build_state']}, made of "
            f"{', '.join(way['materials_at_build'])}"
        )
        tl = "; ".join(f"{a['label'] or a['kind']} at {a['tick']}" for a in e["timeline"])
        lines.append(
            f"- timeline: {tl}; markers: " + ", ".join(f"{n} {t}" for t, n in e["markers"].items())
        )
        roles = e["census"]["roles"]
        lines.append("- parts: " + ", ".join(f"{k} {v}" for k, v in roles.items()))
        if e["census"]["foreign"]:
            lines.append(f"- **not simulated** (foreign): {e['census']['foreign']}")
        if e["build_pending"]:
            lines.append(f"- build not settled: pending at tick 0: {e['build_pending']}")
        if e["broken_sim_in_name"]:
            lines.append(
                "- named `[broken sim]` by the owner (reported as simulated wrongly "
                "at some point; see doc/experiments/index.md EXP-068)"
            )
        rp = e["replay"]
        lines.append(f"- replay: {rp['piston_events']} piston events, outcomes {rp['outcomes']}")
        bad = [c for c in rp["marker_checks"] if c.get("checked") and not c.get("ok")]
        if bad:
            lines.append(f"- **marker mismatch**: {bad}")
        for note in e["notes"]:
            lines.append(f"- note in the world: {note}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="one world (slug or file name part)")
    args = parser.parse_args()
    files = [corpus.find(args.only)] if args.only else corpus.world_files()
    entries = []
    for path in files:
        e = entry(path)
        print(f"{e['id']}: {e['seconds']}s, markers ok: {e['replay']['markers_ok']}")
        entries.append(e)
    if args.only:
        print(json.dumps(entries[0], indent=1)[:3000])
        return
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"schema": "doorlab.inventory/1", "worlds": entries}, indent=1) + "\n"
    )
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown(entries) + "\n")
    print(f"wrote {OUT_JSON.relative_to(corpus.ROOT)} and {OUT_MD.relative_to(corpus.ROOT)}")


if __name__ == "__main__":
    main()
