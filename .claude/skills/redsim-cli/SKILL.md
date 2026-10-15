---
name: redsim-cli
description: Build, run, inspect and test Minecraft Java redstone contraptions with the simulator's command line (redsim-cli) in this repository. Use when asked to design, build, debug or verify redstone circuits, or to work with .redsim.json worlds, schematics or Minecraft saves from the terminal.
---

# Using redsim-cli

The simulator's command line works on `.redsim.json` world files: every command opens the
world, acts and saves it. Read **doc/cli.md** (the guide) before building and
**doc/cli-reference.md** for exact command syntax (`redsim-cli help COMMAND` prints the
same text). Run it as `redsim-cli WORLD …` (installed) or
`PYTHONPATH=src python -m redsim.cli WORLD …` from the repository root.

Workflow:

1. `redsim-cli W new` (a stone floor at y=0; build from y=1).
2. Label the inputs and outputs (`label A x y z "what it is"`), write a target
   (`target new NAME "…"`, then `target NAME truth @A @B -> @OUT rows 00:0 …` or
   `target NAME do …` / `target NAME expect @OUT lit=true at 7`).
3. Build with `place` (components; `out=DIRECTION` for repeaters, comparators, observers)
   and `fill`/`set` (structure), in one script: `redsim-cli W < build.cli.txt`.
4. `settle`, then `show` (text maps: upper case = on; legend under the map), `check`.
5. Debug failing cases: `target NAME load CASE`, `run N`, `waves`, `inspect POS`
   (`faces`: which way it works), `effects @INPUT` (where the signal goes and where it
   stops), `why POS` (where a change came from), `changes POS`, `step` / `step back`.
6. Leave a `note`. Optional: `export FILE.litematic` for Minecraft.

Rules: building commands change the build (tick 0) wherever the view is; `at T COMMAND`
records an edit on the timeline at tick T; ticks are game ticks (a repeater's delay 1 is
2 ticks). What the simulator cannot do (water, items, mobs, random outcomes):
doc/differences.md.
