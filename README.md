# Redstone Simulator

A reverse-engineered redstone simulator for testing and debugging redstone systems in
Minecraft **Java Edition 26.3**. The simulation core is a faithful Python port of the
game's server-side update logic (neighbor updates, scheduled ticks, block events, block
entities) and is checked tick by tick against the real game.

Status: simulation core, the core components (lever, buttons, lamp, torch, wire, repeater,
comparator) and a 3D editor work; behavior is verified tick by tick against the real game.
Pistons are next. Details: [`doc/project-state.md`](doc/project-state.md).

## Quick start

Requires Python 3.12 with numpy and PySide6 (`pip install -e .[dev]` installs everything).

```sh
python -m redsim                      # start the editor (PYTHONPATH=src unless installed)
python -m pytest                      # run the test suite (~2 s)
python -m tools.gameserver.run        # optional: compare against a sandboxed 26.3 server
                                      # (needs Java 25 and the JARs in data/; PYTHONPATH=src)
```

## Documentation

All design notes, mechanics research (with source references) and experiment results live
in [`doc/`](doc/README.md), which is also an Obsidian vault.

## Editor controls

WASD/Space/Shift fly (Ctrl faster) · right-drag look · left click break · right click place
or use · Shift+right click place · middle click pick · Ctrl+click inspect · 1–9 hotbar ·
P run/pause · T step tick · E step event · Ctrl+Z/Ctrl+Y undo/redo · F1 help.
