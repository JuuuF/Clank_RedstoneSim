# Redstone Simulator

A reverse-engineered redstone simulator for testing and debugging redstone systems in
Minecraft **Java Edition 26.3**. The simulation core is a faithful Python port of the
game's server-side update logic (neighbor updates, scheduled ticks, block events, block
entities) and is checked tick by tick against the real game.

Status: the simulation core and most redstone components work (lever, buttons, lamp,
torch, wire, repeater, comparator, pistons with slime/honey, observers, rails, target
blocks, hoppers, barrels, lecterns, note blocks, copper bulbs, droppers, dispensers,
chests, pressure plates), with a 3D editor (rewind/replay, copy/paste, prefabs, the game's
own textures) that can also open Minecraft Java saves and stream their chunks around the
camera. Behavior is verified tick by tick against the real game (46 named scenarios and 40
random circuits). Details and next steps: [`doc/project-state.md`](doc/project-state.md).

## Quick start

```sh
conda env create -f environment.yml   # once: Python 3.12 + PySide6 6.9.2, numpy, dev tools
conda activate redsim
python -m pip install -e . --no-deps  # once: provides the `redsim` command (the env's pip)
redsim examples/showcase.redsim.json  # open the example world (guided tour: doc/tour.md)
python -m pytest                      # run the test suite (~2 s)
python -m tools.gameserver.run        # optional: compare against a sandboxed 26.3 server
                                      # (needs Java 25 and the JARs in data/)
```

Without conda: Python 3.12 with `python -m pip install -e .[dev]`.

If `redsim` is not found afterwards (macOS): `pip` may have been another Python's
(check `pip -V`), so use `python -m pip …` as above; in zsh run `rehash` once. `python -m
redsim` always works in the environment.

## Documentation

All design notes, mechanics research (with source references) and experiment results live
in [`doc/`](doc/README.md), which is also an Obsidian vault.

## Editor controls

Modes: **Esc** NORMAL (left click inspects, right click uses levers etc.), **B** BUILD (left
places, right removes), **V** SELECT (click or drag boxes). **E** over a block opens its
inspector as a popup. Camera: middle-drag orbits around the pivot, Shift+middle-drag pans,
the wheel zooms, Shift+wheel moves the pivot up/down, WASD moves the pivot, F focuses the
block under the cursor. Space runs/pauses, → / ← step a tick forward/back. All bindings are
rebindable (Settings → Keymap…); macOS gets a few extra defaults. Full list:
[`doc/controls.md`](doc/controls.md); in the app: F1.
