"""Door lab: reverse-engineering the piston contraptions of ``data/redstone_learning``.

The worlds there are third-party designs (not committed); this package reads them without
ever writing to them and derives everything from the simulator itself:

- ``corpus``: find the worlds, parse their names (size, title, creator), open them read-only.
- ``canonical``: layer 1, the exact world (blocks, block entities, sections, timeline,
  markers) as plain data that round-trips losslessly.
- ``interactions``: layer 2, what the blocks can do to each other (pistons and what they
  push, power access, slime groups, door cells), derived from layer 1.
- ``replay``: the timeline played back tick by tick: door-cell frames, piston events,
  movement phases, checked against the world's markers.
- ``inventory``: the machine-readable catalog (``python -m tools.doorlab.inventory``).

Knowledge built with it: doc/redstone/doors/README.md.
"""
