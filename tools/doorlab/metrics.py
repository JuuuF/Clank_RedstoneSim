"""Measured design metrics per door and their trade-offs (``python -m tools.doorlab.metrics``).

The mission's optimization goals (size, speed, component use, robustness) as numbers,
kept separate, with no combined score:

- **size**: the box around the contraption above the floor (x × y × z, volume), the blocks
  in it (occupied volume), and the blocks left after the trim (``ablation --trim``: what
  the door needs at the most);
- **components**: pistons, wire, repeaters, comparators, observers, torches and other
  logic, from the build's roles;
- **speed**: ticks from each input flip until the doorway is closed / open for good (and
  until it is first fully closed / open);
- **robustness**: the shortest gap between the two pulls from which every gap ends clean
  (``inputs``), and in how many of the 8 orientations the door works (``symmetry``).

The results of the slow tools are read from ``.sandbox/doors/`` (``inputs/``,
``ablation/``, ``symmetry.json``); a door without them gets "–". Doors of one doorway size
are compared: a door is **dominated** when another one is at least as good in every
objective and better in one (smaller box, fewer blocks, faster close, faster open,
shorter safe gap, more orientations that work). Writes ``experiments/doors/metrics.json``
and the table in ``doc/redstone/doors/metrics.md`` (between its ``generated`` markers).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.doorlab import analysis, corpus, interactions

SANDBOX = corpus.ROOT / ".sandbox" / "doors"
OUT_JSON = corpus.ROOT / "experiments" / "doors" / "metrics.json"
OUT_DOC = corpus.ROOT / "doc" / "redstone" / "doors" / "metrics.md"
COMPONENTS = ("piston", "wire", "repeater", "comparator", "observer", "torch")
SHOWPIECE_WORDS = ("spiral", "vault", "staircase", "seamless", "enchanting", "lamp", "glass")


def _load(path: Path) -> Any:
    return json.loads(path.read_text()) if path.exists() else None


def _speeds(a: dict[str, Any]) -> list[tuple[str, int, int]]:
    """Per action whose doorway ends full (closed or open): (state, first, settled).

    ``first``: ticks until the doorway first reaches that state; ``settled``: ticks
    until its last change before the next action (some doors reach the state, then
    move blocks through the doorway again: Sacred's closes at 19 and settles at 38).
    """
    frames, ticks = a["frames"], [x["tick"] for x in a["actions"]]
    out = []
    for i, t0 in enumerate(ticks):
        t1 = ticks[i + 1] if i + 1 < len(ticks) else len(frames)
        end = frames[t1 - 1]
        if end == frames[t0] or set(end) not in ({"#"}, {"."}):
            continue
        first = next(t for t in range(t0 + 1, t1) if frames[t] == end)
        settled = max(t for t in range(t0 + 1, t1) if frames[t] != frames[t - 1])
        out.append(("closed" if end[0] == "#" else "open", first - t0, settled - t0))
    return out


def measure(path: Path, a: dict[str, Any] | None = None) -> dict[str, Any]:
    """The metrics of one world (``a``: its analysis, if already computed)."""
    name = corpus.parse_name(path)
    if a is None:
        cached = _load(SANDBOX / f"{name.slug}.json")
        a = cached if cached is not None else analysis.analyze(path)
    session = corpus.open_world(path)
    session.doc.seek_tick(0)
    census = interactions.census(session.doc.level)
    roles = census["roles"]
    speeds = _speeds(a)
    closes = [(f, t) for state, f, t in speeds if state == "closed"]
    opens = [(f, t) for state, f, t in speeds if state == "open"]
    inputs = _load(SANDBOX / "inputs" / f"{name.slug}.json")
    trim = _load(SANDBOX / "ablation" / f"{name.slug}-trim.json")
    if trim is None:
        trim = (_load(SANDBOX / "ablation" / f"{name.slug}.json") or {}).get("trim")
    sym = next((r for r in _load(SANDBOX / "symmetry.json") or [] if r["world"] == name.slug), None)
    # A world of our own keeps its results next to it (experiments/doors/door_3x3).
    own = _load(path.parent / "results.json")
    if own is not None and own.get("world") == path.name:
        inputs, trim, sym = own["inputs"], own["trim"], own["symmetry"]
    logic = sum(n for r, n in roles.items() if r in interactions.LOGIC_ROLES)
    return {
        "world": name.slug,
        "creator": name.creator,
        "door": f"{a['doorway']['width']}x{a['doorway']['height']}",
        "intent": "showpiece"
        if any(w in name.title.lower() for w in SHOWPIECE_WORDS)
        else "functional",
        "size": census["size"],
        "volume": census["volume"],
        "blocks": census["blocks"],
        "blocks_needed": trim["blocks_after"] if trim else None,
        "components": {c: roles.get(c, 0) for c in COMPONENTS},
        "logic": logic,
        "close_ticks": closes[0][1] if closes else None,
        "open_ticks": opens[0][1] if opens else None,
        "first_closed": closes[0][0] if closes else None,
        "first_open": opens[0][0] if opens else None,
        "safe_gap": None if inputs is None else inputs.get("clean_from"),
        "designed_gap": None if inputs is None else inputs.get("designed_gap"),
        "orientations_ok": None
        if sym is None
        else 1
        + sum(
            1 for o in sym["orientations"] if o["markers_ok"] and "shifted" not in o["orientation"]
        ),
    }


OBJECTIVES = ("volume", "blocks", "close_ticks", "open_ticks", "safe_gap")  # lower is better
HIGHER = ("orientations_ok",)  # higher is better


def _neg(v: int | None) -> int | None:
    return None if v is None else -v


def dominated(rows: list[dict[str, Any]]) -> dict[str, str | None]:
    """For each door: the door of the same size that dominates it, or None."""
    out: dict[str, str | None] = {}
    for r in rows:
        out[r["world"]] = None
        for other in rows:
            if other is r or other["door"] != r["door"]:
                continue
            pairs = [(other.get(k), r.get(k)) for k in OBJECTIVES]
            pairs += [(_neg(other.get(k)), _neg(r.get(k))) for k in HIGHER]
            if any(x is None or y is None for x, y in pairs):
                continue
            if all(x <= y for x, y in pairs) and any(x < y for x, y in pairs):
                out[r["world"]] = other["world"]
                break
    return out


def table(rows: list[dict[str, Any]]) -> str:
    dom = dominated(rows)
    head = (
        "| world | door | intent | box | volume | blocks | needed | pistons | logic | "
        "close | open | safe gap | orientations | dominated by |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )

    def cell(v: Any) -> str:
        return "–" if v is None else str(v)

    def speed(r: dict[str, Any], key: str, state: str) -> str:
        settled, first = r[f"{key}_ticks"], r[f"first_{state}"]
        return cell(settled) if first == settled else f"{settled} ({first})"

    def by(world: str) -> str:
        return f"`{dom[world]}`" if dom[world] else "–"

    lines = []
    for r in sorted(rows, key=lambda r: (r["door"], r["volume"])):
        lines.append(
            f"| `{r['world']}` | {r['door']} | {r['intent']} | {'×'.join(map(str, r['size']))} "
            f"| {r['volume']} | {r['blocks']} | {cell(r['blocks_needed'])} "
            f"| {r['components']['piston']} | {r['logic']} | {speed(r, 'close', 'closed')} "
            f"| {speed(r, 'open', 'open')} | {cell(r['safe_gap'])} "
            f"| {cell(r['orientations_ok'])} | {by(r['world'])} |"
        )
    return head + "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extra", nargs="*", default=[], help="more worlds (not in the dataset)")
    args = parser.parse_args()
    rows = [measure(p) for p in corpus.world_files()]
    rows += [measure(Path(p)) for p in args.extra]
    OUT_JSON.write_text(json.dumps(rows, indent=1) + "\n")
    begin, end = "<!-- generated -->", "<!-- end generated -->"
    text = OUT_DOC.read_text() if OUT_DOC.exists() else f"{begin}\n{end}\n"
    i, j = text.index(begin) + len(begin), text.index(end)
    OUT_DOC.write_text(text[:i] + "\n" + table(rows) + text[j:])
    print(f"{len(rows)} worlds: {OUT_JSON.relative_to(corpus.ROOT)}, ", end="")
    print(OUT_DOC.relative_to(corpus.ROOT))


if __name__ == "__main__":
    main()
