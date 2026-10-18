# Work in progress: instant wire, both edges (backlog Q17)

**Done 2026-10-18:** the module is `examples/circuits/instant_edges` (contract in
doc/redstone/circuits.md, "Instant wire, both edges").

| File | Status | What it shows |
|---|---|---|
| `01-prototype-D20.redsim.json` | works | the first build: chain R (row z=0) removes the cut A, chain F (row z=-4) removes the source B; F's head is powered by IN or by D (NOT IN, 20 ticks late), so F re-arms by itself after R. IN must stay off 30 ticks |
| `02-D8.redsim.json` | works | D shortened to 8 ticks: IN on >= 7, off >= 18 (`scripts/sweep.py WORLD` prints every pulse and gap of 1..30) |

The old note in circuits.md said two instant chains could not be combined at the output
(both are down just after either edge). That holds only if both chains re-arm on IN; the
falling-edge chain that re-arms by itself (D) is the way around it, no latch needed.
