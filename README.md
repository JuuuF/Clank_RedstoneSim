# Redstone Simulator

A reverse-engineered redstone simulator for testing and debugging redstone systems in
Minecraft **Java Edition 26.3**. The simulation core is a faithful Python port of the
game's server-side update logic (neighbor updates, scheduled ticks, block events, block
entities) and is checked tick by tick against the real game.

Status: simulation core, the core components (lever, buttons, lamp, torch, wire, repeater,
comparator), pistons (with slime/honey) and a 3D editor with rewind/replay, copy/paste and
prefabs work; behavior is verified tick by tick against the real game (22 scenarios).
Details: [`doc/project-state.md`](doc/project-state.md).

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
breaks, right places), **V** SELECT (click or drag boxes). Camera: middle-drag orbits around
the pivot, Shift+middle-drag pans, Ctrl+wheel moves the pivot up/down, wheel zooms, WASD
moves the pivot, F focuses the block under the cursor. Space runs/pauses, → / ← step a tick
forward/back. All bindings are rebindable (Settings → Edit keymap file). Full list:
[`doc/controls.md`](doc/controls.md); in the app: F1.
