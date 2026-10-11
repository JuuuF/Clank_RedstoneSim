"""Run comparison scenarios against the sandboxed server.

Usage (from the repository root)::

    python -m tools.gameserver.run            # all scenarios
    python -m tools.gameserver.run and_gate   # selected scenarios
    python -m tools.gameserver.run fuzz_1 fuzz_2   # random circuits (tools.gameserver.fuzz)

Results are written to ``experiments/results/<scenario>.json``.
"""

from __future__ import annotations

import sys

from tools.gameserver import scenarios
from tools.gameserver.compare import compare
from tools.gameserver.server import GameServer

SPACING = 24  # blocks between scenario origins (distinct coordinates, no interference)


def main(argv: list[str]) -> int:
    selected = [scenarios.lookup(name) for name in argv] if argv else list(scenarios.ALL)
    failures = 0
    with GameServer(fresh_world=True) as server:
        # Force-load every scenario area (each ≤ 18 blocks wide, spaced SPACING apart).
        max_x = len(selected) * SPACING + 32
        for x0 in range(-16, max_x, 256):
            server.command(f"forceload add {x0} -16 {min(x0 + 255, max_x)} 47")
        for index, scenario in enumerate(selected):
            origin = (index * SPACING, 0, 0)
            result = compare(server, scenario, origin)
            verdict = "MATCH" if result["match"] else "MISMATCH"
            print(f"{scenario.name:24s} {verdict}  ticks={scenario.ticks}")
            if not result["match"]:
                failures += 1
                for frame in result["frames"]:
                    for key in frame["mismatches"]:
                        print(
                            f"    tick {frame['tick']:3d} {key}: sim={frame['sim'][key]} "
                            f"game={frame['game'][key]}"
                        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
