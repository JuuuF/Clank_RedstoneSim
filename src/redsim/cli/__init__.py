"""``redsim-cli``: the simulator on the command line, for AI agents and people alike.

User documentation: doc/cli.md (concepts, workflows) and doc/cli-reference.md (every
command, generated from the registry). Developer documentation: doc/cli-internals.md.

Modules:

* ``main``: the program (options, one command, ``-c``, standard input, help);
* ``language``: words, positions, labels, blocks, ticks (the command language);
* ``registry``: the command registry and the help/reference text;
* ``session``: opening a world, running commands, edits at the build or ``at T``, saving,
  the undo file;
* ``views``: text renderings (maps, signal timelines, block descriptions);
* ``targets``: acceptance tests (model and checker);
* ``commands``: the commands, one module per reference chapter.

Nothing here imports Qt: the command line runs without a display.
"""
