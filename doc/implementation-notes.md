# Implementation notes

Practical notes for working on the code. Design rationale lives in [[decisions]].

## Environment

- Python 3.12 (Anaconda base interpreter); PySide6 6.9.2, numpy, pytest, ruff, mypy are
  already installed there, so no virtual environment or extra dependency is required.
- Under Wayland, the app sets `QT_QPA_PLATFORM=xcb` unless the variable is already set,
  because this PySide6 build cannot create an OpenGL context with the native Wayland plugin
  ([[research/repository-report]]).
- Headless rendering for tests: `QT_QPA_PLATFORM=offscreen`.

## Conventions

- Source citations use paths relative to `data/minecraft_src/client-src/` plus class, method
  and decompile line, e.g. `CollectingNeighborUpdater.addAndRun` L68.
- Python methods that port a Java method say so in their docstring
  (`Port of DiodeBlock.checkTickOnNeighbor`).
- Never import Qt in `redsim.core`, `redsim.world`, `redsim.sim` or `redsim.io`.
