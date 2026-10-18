# Work in progress: a 7-segment lamp display (backlog Q20)

**Done 2026-10-18:** the composition is `examples/circuits/seg7_display` (generator
`tools/circuitgen/display7.py`, contract in doc/redstone/circuits.md, "7-segment display").

| File | Status | What it shows |
|---|---|---|
| `01-digit-ideal-pulses.redsim.json` | works (7/7) | the lamp digit alone, each segment fed by an ideal pulse at its feed wire: each lights only its own two lamps |

The routing from the decoder into the digit worked on the first build (all 16 digits, both
lamps of every segment); the generator's docstring explains the two rules that made it
crossing-free: the decoder's columns in the order f e a g d b c, and the sideways shifts in
the order a/d, e/b, f/c.
