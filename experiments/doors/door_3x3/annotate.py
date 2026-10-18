"""The project's own 3x3 flush door (``examples/circuits/door_3x3``) as a door-lab world.

The example has labels and targets but no sections or recorded timeline; the door lab reads
those. This writes a copy with the input section (the test lever @L), the output section
(the nine cells @D00..@D22), the lever pulled at 5 and 60 (the ``lever`` target's case) and
markers at the ticks that target checks: open from 37, closed from 77.

    PYTHONPATH=src python experiments/doors/door_3x3/annotate.py
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.doorlab import canonical

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "examples/circuits/door_3x3.redsim.json"
OUT = Path(__file__).resolve().parent / "3x3 flush door by redsim.redsim.json"


def annotated() -> dict:
    canon = canonical.from_file(SOURCE)
    labels = canon["annotations"]["labels"]
    lever = labels["L"]["pos"]
    cells = [labels[f"D{x}{row}"]["pos"] for x in range(3) for row in range(3)]
    sections = canon["annotations"]["sections"]
    sections["input"]["positions"] = [lever]
    sections["output"]["positions"] = cells
    use = {"kind": "use", "pos": lever, "state": None, "flags": 3, "payload": None}
    canon["timeline"] = {
        "end_tick": 100,
        "actions": [{"tick": t, **use, "label": "use lever"} for t in (5, 60)],
    }
    canon["annotations"]["markers"] = {
        "5": "Opening",
        "37": "Opened",
        "60": "Closing",
        "77": "Closed",
    }
    canon["source"] = {"file": "examples/circuits/door_3x3.redsim.json", "creator": "redsim"}
    return canon


def main() -> None:
    with OUT.open("w") as handle:
        json.dump(canonical.to_save(annotated()), handle)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
