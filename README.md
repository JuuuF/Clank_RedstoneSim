# Redstone Simulator

A reverse-engineered redstone simulator for testing and debugging redstone systems in
Minecraft **Java Edition 26.3**. The simulation core is a faithful Python port of the
game's server-side update logic (neighbor updates, scheduled ticks, block events, block
entities) and is checked tick by tick against the real game.

Status: simulation core and the first components (lever, buttons, lamp, torch, wire) are
done and verified. The 3D editor is next. Details: [`doc/project-state.md`](doc/project-state.md).

## Quick start

Requires Python 3.12 with numpy and PySide6 (`pip install -e .[dev]` installs everything).

```sh
python -m pytest                      # run the test suite (~1 s)
python -m tools.gameserver.run        # optional: compare against a sandboxed 26.3 server
                                      # (needs Java 25 and the JARs in data/; PYTHONPATH=src)
```

## Documentation

All design notes, mechanics research (with source references) and experiment results live
in [`doc/`](doc/README.md), which is also an Obsidian vault.
