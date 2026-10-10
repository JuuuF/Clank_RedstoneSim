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
pip install -e . --no-deps            # once: provides the `redsim` command
redsim examples/showcase.redsim.json  # open the example world (guided tour: doc/tour.md)
python -m pytest                      # run the test suite (~2 s)
python -m tools.gameserver.run        # optional: compare against a sandboxed 26.3 server
                                      # (needs Java 25 and the JARs in data/)
```

Without conda: Python 3.12 with `pip install -e .[dev]`.

## Documentation

All design notes, mechanics research (with source references) and experiment results live
in [`doc/`](doc/README.md), which is also an Obsidian vault.

## Editor controls

WASD/Space/Shift fly (Ctrl faster) · right-drag look · left click break · right click place
or use · Shift+right click place · middle click pick · Ctrl+click inspect · 1–9 hotbar ·
P run/pause · T step tick · E step event · Shift+T tick back · Shift+E step back · timeline
slider to rewind/replay · B mark selection corners · Ctrl+C/Ctrl+V copy/paste · R rotate
clipboard · Del clear selection · Ctrl+Z/Ctrl+Y undo/redo (rewinds to before the last edit) ·
F1 help.
