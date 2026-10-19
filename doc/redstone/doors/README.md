# Piston doors: reverse-engineering the dataset

The second research track of the knowledge base ([[../README]]): learning piston-door
engineering from human designs. The mission is [[mission]] (the owner gave it as
`data/redstone_learning/PROMPT.md`, not committed, like the worlds); this folder is
where its results live. Working rules: [[../../agents/README]]. Minecraft Java 26.3.

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
| [[mission]] | The mission's brief (tracked copy of the owner's `data/redstone_learning/PROMPT.md`); section 13 is the status and handoff |
| [[inventory]] | The catalog: every world, its creator, doorway, parts, timeline, replay summary (generated) |
| [[guide-5x5]] | MYuen222's 5x5 guide: the engineering process (layout → sequence → powering → input → wiring), its vocabulary, its claims and their test status |
| [[representation]] | The three layers (canonical world, interactions, knowledge) and how they are validated |
| [[analyses/README]] | One page per door: generated facts (frames, groups, pistons, power) and hand-written explanations; the Zhus / monchiCARP comparison |
| [[patterns]] | Mechanisms found in the corpus (singles, floor storage, extenders, spits, power switches, QC, landing checks, sliders, slime) with counts, and design principles |
| [[symmetry]] | Counterfactual: every door turned, mirrored and moved; directional and locational designs |
| [[mechanism]] | Mechanism and controller: a door's contract (pulses per piston + same-tick order), tested by driving the stripped mechanism with editor pulses |
| [[robustness]] | Counterfactuals per block (remove, glass, repeater delay), the combined trim, input timing (every gap between the two pulls) and the two-cycle test |
| [[metrics]] | The optimization goals measured per door (size, components, speed, robustness), kept separate; which doors another door of the same size dominates |
| [[demonstration]] | The whole pipeline on the project's own 3x3 flush door (`door_3x3`), compared with Mumbo Jumbo's |

## Tools

`tools/doorlab/` (tests: `tests/doorlab/`):

| Module | Layer | What it does |
|---|---|---|
| `corpus` | — | finds the worlds, parses their names (size, title, creator), opens them read-only |
| `canonical` | 1 | the exact world as sorted plain data (blocks, block entities, pending engine state, timeline, annotations); `to_save` / `rebuild` round-trip losslessly |
| `interactions` | 2 (static) | roles, simulator facts per block (conductor, push reaction), pistons with what they would move and who can power them (quasi-connectivity included), the doorway |
| `replay` | 2 (dynamic) | the timeline step by step: piston block events with what each moved (or why an extension failed: unpowered, an immovable or moving block, more than 12 blocks), where each extension's power came from, causal links between block changes, doorway frames, marker checks |
| `analysis` | 3 | door-block trajectories (tokens), exit groups, piston roles, pulses, power access, phases |
| `report` | — | `python -m tools.doorlab.report SLUG`: the facts part of an analysis page |
| `compare` | 3 | two builds up to rotation/mirror at three levels, and their behavior |
| `transform`, `symmetry` | 1, 3 | a world turned / mirrored / moved as a whole; does every copy do the same? |
| `patterns` | 3 | the mechanism census ([[patterns]]) |
| `inventory` | — | `python -m tools.doorlab.inventory`: writes `experiments/doors/inventory.json` and [[inventory]] |
| `mechanism` | 3 | the mechanism / controller split, the contract, the stripped door ([[mechanism]]) |
| `power` | 2 (dynamic) | who reads whose power: every positive signal read of the run with its asker (from the call stack), its alternatives and context, following moved blocks (`Level.signal_probe`); the glass counterfactual at every tick boundary; `--predict` scores it against the ablation ([[representation]]) |
| `ablation` | 3 | one change per block (remove, glass, delay), classified breaks / timing / internal / inert; `--trim` (keeps supports); `--turn` (piston facings); `--predict`: layer 2's role of each glass variant against the result ([[robustness]], [[representation]]) |
| `inputs` | 3 | every gap between the two input flips; `--recover`: one more designed cycle after each gap that did not end clean; `--repeat`: the designed cycle twice ([[robustness]]) |
| `metrics` | 3 | `python -m tools.doorlab.metrics`: the objectives per door and the dominance per doorway size; writes `experiments/doors/metrics.json` and [[metrics]] |

`experiments/doors/door_3x3/` (`annotate.py`, `lab.py`) runs every tool on the project's
own door; its results and derived worlds are committed there. Results for the dataset's
designs stay in `.sandbox/doors/` (not committed).

## Status and roadmap

The mission's deliverables (2026-10-19):

| # | Deliverable | Where | State |
|---|---|---|---|
| 1 | Machine-readable inventory with creators | `experiments/doors/inventory.json`, [[inventory]] | done (19 worlds) |
| 2 | Evidence-backed door analyses | [[analyses/README]] | facts for all 19; hand-written explanations for 12: Mumbo Jumbo's, Zhus's / monchiCARP's, SacredRedstone's, Rubik's and Nile's seamless 3x3s, Purplers' spiral and Lutal's vault, Kwipla's and Sydney600mc's 4x4s, Purplers' sliding 4x4 and vault lamp door (2026-10-19) |
| 3 | 5x5 guide understanding | [[guide-5x5]] | process, vocabulary, 8 claims: 4 verified (G1–G4), 2 implied by the corpus, 2 untested (G6, G7) |
| 4 | Canonical representation + interaction model | [[representation]], `canonical`, `interactions`, `replay` | done; lossless round trip and identical replay for all 19; layer 2 predicts the harmless glass replacements exactly (0 of 359 break) |
| 5 | Pattern library with sources | [[patterns]] | 12 mechanisms with the worlds that use them, a per-world census, 9 design principles (timing, slack, input safety, how doors jam) |
| 6 | Round-trip / replay / counterfactual tests | `tests/doorlab/`, [[symmetry]], [[mechanism]], [[robustness]] | done: ablation (remove, glass, delay, piston turns) and trim of 16 doors, input sweep (gaps 1–70) with recovery for 17, two cycles for 19; game checks EXP-068, EXP-070–EXP-076 |
| 7 | A demonstrated analysis / construction | [[demonstration]], [[metrics]] | the pipeline on `door_3x3`; trimmed builds (EXP-071); the optimization goals measured for all 20 builds, with the dominance per doorway size |
| 8 | Roadmap | this section | — |

Open items (D-numbers are cited from the pages):

- ~~D1~~ Mumbo Jumbo's helper piston (4 3 −3) is a wire cutter: it puts a block above a
  wire step and so gates when one repeater's output reaches P1
  ([[analyses/3x3-piston-door-mumbo-jumbo]]). Closed.
- ~~D2~~ The same-tick double-extender race: [[../records/R-027-double-extender-order]],
  game EXP-072 (match). Closed; the vault lamp door's own jam in its 90° copy is
  game-verified too, with `run_world`'s exact lever stand-in (EXP-074).
- ~~D3~~ LegDen's 7x7 and 8x8 stop part-way (the game does the same, EXP-068). The owner
  takes them out of the pool to check the worlds themselves (2026-10-18): do not
  investigate further. What was found, for that check: the stop is deterministic (the
  same at 57 and 64 positions and in all 8 orientations); 69 and 40 extensions move
  nothing (working doors: 0–12), 36 and 25 of them because a 0-tick pulse ends before the
  piston's event runs, 24 and 6 because the push line holds a block that is still
  moving. The 7x7's first is at tick 75: the column pusher −4 2 −1 fires after two
  12-block pushes in the same tick moved blocks out of its column.
- **D4** Mechanism split refinements ([[mechanism]]): slime-carried redstone blocks
  belong to the mechanism; stacked pistons need side power (an editor pulse also
  quasi-powers the piston below); then a same-tick order in the contract.
- **D5** Guide claims G6, G7 ([[guide-5x5]]): build and measure them (G4 is R-015, verified).
- **D6** Input safety ([[robustness]]): every dataset door jams on a too-short gap
  between the flips (Mumbo Jumbo: gaps 2–9; after 3–6 one or two more flips leave
  other blocks off). Put a lockout like `door_3x3`'s in front of one of them, using its contract
  as the specification and the no-overlap gap as its hold time.
- ~~D7~~ Server checks of the remaining trimmed builds: `run_world` now gives every
  lever and button a stand-in that the simulator first confirms to act exactly like
  the player's input (EXP-074). Trimmed Lutal and Kwipla match the game, and so do
  Mumbo Jumbo's and the staircase's again with the exact stand-in. Closed.
- ~~D8~~ Nile's seamless glass door alternates between two rest states (a glass block
  behind the doorway moves one cell and back, cycle by cycle): game EXP-073 (match).
  Closed.
- **D9** Purplers' enchanting-table door recycles one redstone dust through droppers, the
  ground and a hopper; the simulator has no item entities ([[../../differences]]), so
  the dust is lost after the first cycle and later cycles in the simulator are not
  evidence ([[robustness]]). Needs item entities, or a game run of the first cycle.
  `run_world` has no exact stand-in for its button yet: the button sits on a dropper,
  and observers watching the dropper see the stand-in's swap (EXP-074).
- ~~D10~~ Lasting jams ([[robustness]] "Why lasting jams last"): the blocks left behind
  are moved in anti-phase by every later cycle (edge-pulse toggles do not self-correct)
  or accumulate in a storage column; a second deliberately short cycle re-syncs Sacred's
  and Rubik's doors, nothing in 1–40 repairs pal1's and Sydney's. Closed 2026-10-19.
- ~~D12~~ Which powered conductors matter ([[representation]]): `power.py` records who
  reads whose power (the simulator's `Level.signal_probe`) and predicts a glass change by
  a local counterfactual at every tick boundary (plus a retracted piston's update read):
  281 of the 282 breaking glass changes are predicted, "none" stays exact (1 of 761), and
  59 predicted changes never reach the doorway. Found on the way: a conductor's role
  follows the block a piston moves, a wire step has two carriers, a read does not name
  its asker (quasi-connectivity), mid-tick reads decide pistons. Closed 2026-10-19.
- **D13** The reach from a reader whose input changes to the mechanism, to turn "changes
  something" (59 of 347) into "breaks the door"; the same probe can answer D11 (which
  first-sequence reads the second input cuts).
- ~~D11~~ A door's real input contract ([[robustness]] "What the second flip waits
  for"): one event pair per door; 5 doors wait for a push to land before the cut (a drop
  spits), 4 for a short pulse to still be on one tick after a lowered piston lands
  (R-026), the rest for a tail event or a veto block. Closed 2026-10-19.
