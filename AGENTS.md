# For AI agents

This repository is a Minecraft Java Edition 26.3 redstone simulator: a port of the game's
server code, checked tick by tick against the real game. Agents use it through the command
line **`redsim-cli`**: build a contraption in a world file, run it, look at maps, signal
timelines and cause chains, and test it with targets. The world file is the same one the
editor (`redsim`) opens, so people see exactly what you built.

Start here:

1. **[doc/cli.md](doc/cli.md)**: the guide (concepts, the rules for time, map codes,
   targets, workflows). Read sections 4 (positions, facing) and 5 (time) before building.
2. **[doc/cli-reference.md](doc/cli-reference.md)**: every command; the same text as
   `redsim-cli help COMMAND`.
3. **[doc/differences.md](doc/differences.md)**: what the simulator does not do like the
   game (water, items, mobs, random outcomes).

Running it: `redsim-cli WORLD COMMAND …` after `pip install -e .`, or
`PYTHONPATH=src python -m redsim.cli WORLD COMMAND …` from the repository root. Scripts:
`redsim-cli WORLD < script.cli.txt`. Examples with tests: `examples/cli/`.

The habits that matter most:

- Building commands (`place`, `set`, …) change the **build** (tick 0) wherever the view
  is; record actions during a run with **`at T COMMAND`** or **`pulse`**.
- **`settle`** after building, before testing.
- **Label** inputs and outputs (`label OUT x y z`), write a **target**, and run **`check`**
  until it passes. Debug with `waves`, `inspect` (its `faces` line: which way a block
  works), `effects` (where a signal goes), `why` (where it came from), `changes`,
  `step` / `step back`.
- Repeaters, comparators and observers face their input: write **`out=DIRECTION`**.
- Leave a `note` saying what you built and what is left.

Working on the simulator's code instead: start at [doc/README.md](doc/README.md); the
CLI's own code is explained in [doc/cli-internals.md](doc/cli-internals.md). Every change
to simulated behavior must match the game exactly (ported from the decompiled source,
compared on the test server), and anything that does not is written down in
doc/differences.md and marked `Not as in the game:` in the code.
