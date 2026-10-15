"""The commands of ``redsim-cli``, one module per chapter of the reference (importing
this package registers them all, in the reference's order)."""

from redsim.cli.commands import (  # noqa: F401
    annotate,
    build,
    inspect,
    io,
    meta,
    targets,
    time,
    world,
)
