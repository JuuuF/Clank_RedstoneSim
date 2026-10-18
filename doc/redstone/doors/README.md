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

## Tools

`tools/doorlab/` (tests: `tests/doorlab/`):

| Module | Layer | What it does |
|---|---|---|
| `corpus` | — | finds the worlds, parses their names (size, title, creator), opens them read-only |
| `canonical` | 1 | the exact world as sorted plain data (blocks, block entities, pending engine state, timeline, annotations); `to_save` / `rebuild` round-trip losslessly |
| `interactions` | 2 (static) | roles, simulator facts per block (conductor, push reaction), pistons with what they would move and who can power them (quasi-connectivity included), the doorway |
| `replay` | 2 (dynamic) | the timeline step by step: piston block events with what each moved, where each extension's power came from, causal links between block changes, doorway frames, marker checks |
| `inventory` | — | `python -m tools.doorlab.inventory`: writes `experiments/doors/inventory.json` and [[inventory]] |
