# Circuit library

Validated circuit building blocks, each with a contract: what it takes, what it gives,
latency, state, reset, the input sequences it was tested with and how it fails. Every
entry has a script in `examples/circuits/NAME.cli.txt` that builds it in a fresh world
and checks its contract (`tests/cli/test_research.py`), and the built world next to it
(`NAME.redsim.json`) to open in the editor or copy with `prefab`.

Conventions: inputs are labeled `@A`, `@B`, … (or `@IN`), outputs `@OUT` (or `@Q`);
latencies in game ticks from the input change to the output change ([[timing]]).
Evidence labels: [[redstone/README#Scope and trust]].

## Primitives

*None contracted yet.* The guide's examples in `examples/cli/` (an AND gate, an RS latch,
a D latch, an observer clock, a piston door) work and have targets, but have not been
given contracts here yet.

## Composition rules

To be filled as primitives are combined: how far apart modules must be, which outputs
may drive which inputs, timing budgets.
