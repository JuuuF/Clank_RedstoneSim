# Piston doors: reverse-engineering the dataset

The second research track of the knowledge base ([[../README]]): learning piston-door
engineering from human designs. The mission is `data/redstone_learning/PROMPT.md` (not
committed, like the worlds); this folder is where its results live. Minecraft Java 26.3.

**The dataset** is `data/redstone_learning/`: 19 worlds (third-party designs imported by
the owner, not committed) in four folders (`piston_doors`, `piston_doors_with_slime`,
`other_piston_contraptions`, `guides`), each with an `input` section (the lever), an
`output` section (the door cells), a two-action timeline (lever on, lever off) and
markers naming the states ("Closing", "Closed", "Opening", "Opened"). See
[[inventory]] for the catalog. The designs are never changed: every tool opens them
read-only and experiments work on copies.

## Pages

| Page | What it holds |
|---|---|
| [[inventory]] | The catalog: every world, its creator, doorway, parts, timeline, replay summary (generated) |
| [[guide-5x5]] | MYuen222's 5x5 guide: the engineering process (layout → sequence → powering → input → wiring), its vocabulary, its claims and their test status |
| [[representation]] | The three layers (canonical world, interactions, knowledge) and how they are validated |
| [[analyses/README]] | One page per door: generated facts (frames, groups, pistons, power) and hand-written explanations; the Zhus / monchiCARP comparison |
| [[patterns]] | Mechanisms found in the corpus (singles, floor storage, extenders, spits, power switches, QC, landing checks, sliders, slime) with counts, and design principles |
| [[symmetry]] | Counterfactual: every door turned, mirrored and moved; directional and locational designs |

## Tools

`tools/doorlab/` (tests: `tests/doorlab/`):

| Module | Layer | What it does |
|---|---|---|
| `corpus` | — | finds the worlds, parses their names (size, title, creator), opens them read-only |
| `canonical` | 1 | the exact world as sorted plain data (blocks, block entities, pending engine state, timeline, annotations); `to_save` / `rebuild` round-trip losslessly |
| `interactions` | 2 (static) | roles, simulator facts per block (conductor, push reaction), pistons with what they would move and who can power them (quasi-connectivity included), the doorway |
| `replay` | 2 (dynamic) | the timeline step by step: piston block events with what each moved, where each extension's power came from, causal links between block changes, doorway frames, marker checks |
| `analysis` | 3 | door-block trajectories (tokens), exit groups, piston roles, pulses, power access, phases |
| `report` | — | `python -m tools.doorlab.report SLUG`: the facts part of an analysis page |
| `compare` | 3 | two builds up to rotation/mirror at three levels, and their behavior |
| `transform`, `symmetry` | 1, 3 | a world turned / mirrored / moved as a whole; does every copy do the same? |
| `patterns` | 3 | the mechanism census ([[patterns]]) |
| `inventory` | — | `python -m tools.doorlab.inventory`: writes `experiments/doors/inventory.json` and [[inventory]] |
