# Robustness: what a door tolerates

Counterfactual experiments on the dataset's doors (mission section 8): one controlled
change at a time, replayed and compared with the original tick by tick. Two tools
(2026-10-18/19; results for the third-party designs in `.sandbox/doors/`, not
committed):

- `python -m tools.doorlab.ablation WORLD --trim`: every block above the floor removed
  (a piston head only with its piston), every conducting block replaced by glass, every
  repeater set to each other delay; then all the blocks whose removal changed nothing
  removed **together**;
- `python -m tools.doorlab.inputs WORLD --max 70 --out DIR`: the second input flip after
  every gap from 1 to 70 ticks; `--recover`: after each gap that did not end clean, one
  more designed cycle; `--repeat`: the designed cycle run twice.

Classes of a variant (against the original replay):

| Class | Meaning |
|---|---|
| breaks | the world's markers no longer hold: the door does not close or open |
| timing | the markers hold, but the doorway moves differently in between |
| internal | the doorway frames are identical; other blocks change differently |
| inert | every block at every tick as in the original |

## Which blocks matter (ablation)

| world | variants | breaks | timing | internal | inert | glass ok | delays ok | blocks (trim) | box (trim) |
|---|---|---|---|---|---|---|---|---|---|
| `1-wide-hidden-staircase-purplers` | 191 | 78 | 31 | 6 | 76 | 45 of 61 | 18 of 27 | 107 → 71 | 168 → 144 |
| `3x3-flush-enchanting-table-door-purplers` | 297 | 189 | 1 | 31 | 76 | 32 of 49 | 15 of 33 | 220 → 172 | 360 → 360 |
| `3x3-piston-door-monchicarp` | 80 | 63 | 0 | 9 | 8 | 14 of 21 | 0 of 6 | 53 → 50 | 126 → 126 |
| `3x3-piston-door-mumbo-jumbo` | 141 | 97 | 0 | 13 | 31 | 31 of 46 | 0 of 9 | 87 → 78 | 189 → 189 |
| `3x3-piston-door-rubik` | 94 | 67 | 0 | 8 | 19 | 22 of 27 | 0 of 6 | 61 → 56 | 180 → 180 |
| `3x3-piston-door-sacredredstone` | 77 | 61 | 1 | 12 | 3 | 13 of 17 | 1 of 12 | 48 → 48 | 112 → 112 |
| `3x3-piston-door-zhus` | 76 | 63 | 0 | 9 | 4 | 12 of 19 | 0 of 6 | 51 → 50 | 126 → 126 |
| `3x3-seamless-glass-door-nile` | 355 | 233 | 21 | 37 | 64 | 51 of 85 | 10 of 18 | 252 → 225 | 512 → 512 |
| `3x3-spiral-piston-door-purplers` | 123 | 87 | 1 | 9 | 26 | 24 of 33 | 1 of 9 | 81 → 70 | 168 → 168 |
| `3x3-spiral-vault-door-lutal` | 357 | 169 | 13 | 18 | 157 | 114 of 125 | 13 of 27 | 205 → 145 | 880 → 640 |
| `3x4-piston-door-pal1` | 140 | 118 | 1 | 11 | 10 | 17 of 33 | 1 of 15 | 92 → 89 | 280 → 280 |
| `4x4-piston-door-kwipla` | 242 | 164 | 1 | 25 | 52 | 52 of 69 | 1 of 15 | 158 → 140 | 1080 → 1080 |
| `4x4-piston-door-sydney600mc` | 199 | 155 | 4 | 14 | 26 | 28 of 50 | 4 of 24 | 125 → 113 | 270 → 270 |
| `4x4-sliding-piston-door-purplers` | 519 | 294 | 0 | 163 | 62 | 105 of 138 | 6 of 6 | 401 → 381 | 880 → 880 |
| `5x5-vault-door-nile` | 589 | 232 | 31 | 229 | 97 | 120 of 144 | 25 of 27 | 425 → 386 | 1050 → 1050 |
| `5x5-vault-lamp-door-purplers` | 622 | 272 | 11 | 183 | 156 | 150 of 195 | 48 of 57 | 373 → 322 | 660 → 660 |
| `3x3-flush-door-redsim` (ours, `door_3x3`) | 420 | 229 | 17 | 79 | 95 | 96 of 108 | 36 of 96 | 225 → 209 | 1768 → 1632 |

Columns: variants run; their classes; conducting blocks that can be glass without
changing the doorway (inert or internal); repeater delay changes that keep the door
working (timing, internal or inert); blocks above the floor and the box around them,
before and after the trim.

What the ablation shows:

- **Every piston matters in the compact doors.** Removing any one piston breaks 11 of
  the 16 doors: all the 3x3, 3x4 and 4x4 piston doors but the sliding door. The five
  others have pistons whose removal leaves the door working: the staircase 5 of 13
  (all door pistons; "timing": it still closes and opens at the marker ticks but moves
  differently in between), the seamless door 3 of 35, the
  sliding door 2 of 66, the vault lamp door 4 of 46 and Nile's 5x5 vault 27 of 69.
  The classes compare the cells the world marks as its output. Two of the vault's
  "internal" door pistons were checked: everything they change is in the vault's back
  layer (z −3, behind the marked doorway plane), so there "internal" is still a
  visible change.
- **Wire is not redundant in the compact doors either.** At most 4 wire pieces can go
  in 13 of the 16 doors (none in 8). The three big builds have spare wire: the sliding
  door 21 of 80, Nile's 5x5 vault 26 of 59, the vault lamp door 21 of 74.
- **Where a repeater is a delay, the delay is exact.** In the nine compact piston doors
  (Mumbo Jumbo, Zhus, monchiCARP, Rubik, Sacred, the spiral, pal1, Kwipla, Sydney) 0–4
  of 6–24 other delays keep the door working, and only as a timing change: a door's
  timing is a set of exact delays, not ranges ([[patterns]]). The larger builds use
  many repeaters where the delay does not matter (diodes, signal refreshers, the delay
  line at the input of Lutal's vault and the staircase, which only shifts the whole
  sequence): 13 of 27 (Lutal) up to 48 of 57 (the vault lamp door, all with identical
  doorway frames).
- **Most conductors carry no signal.** Between 52% (pal1) and 91% (Lutal) of the
  conducting blocks above the floor can each be glass without changing the doorway.
  They hold wire, give pistons something to stand on, or are decoration. The rest are
  the power paths (quasi-connectivity blocks, blocks that repeaters power).
- **Slack is small in the compact doors and large in the showpieces.** The trim removes
  all individually inert blocks together and re-checks each combination. It never
  found two removals that conflict: every inert block was also removable with all the
  others. From the 3x3 and 3x4 piston doors it removes 0–11 blocks (Sacred none, Zhus
  1, monchiCARP and pal1 3, Rubik 5, Mumbo Jumbo 9, the spiral 11). From the larger
  builds it removes 12 (Sydney) to 60 (Lutal's 205, the vault's frame). Only two boxes
  shrink: Lutal's (880 → 640) and the staircase's (168 → 144).
- **Piston heads are not candidates.** Removing the head of a piston that stays
  extended for the whole run changes nothing: the base stays extended without it. But
  a headless piston is not a smaller door. The first trims counted such heads
  (1 to 20 per door, in six doors); the ablation leaves heads out since 2026-10-18.
- **The trim is game-verified** for Mumbo Jumbo's door and the staircase: the trimmed
  builds run tick for tick as in the simulator (EXP-071), so the removed blocks are
  slack in the game too.

## Input timing

<!-- input table -->

Columns: the gap the world's own timeline uses; the shortest gap from which every
longer gap ends **clean** (the whole build in the designed run's rest state); the gaps
that leave the door **stuck** (the doorway does not come back); the gaps where the
doorway comes back but internal state differs; blocks whose rest state differs from the
saved build. The last column is the whole sweep, gap 1 first: `#` clean, `+` doorway
back, `.` stuck.

<!-- input notes -->

## Two cycles

`inputs --repeat` runs the designed cycle twice, the second from the rest state the
first one left. 15 of the 19 worlds run the second cycle identically to the first. The
four others:

- **Nile's seamless glass door alternates between two rest states**: a white stained
  glass block behind the doorway (0 12 −4) is one cell west (−1 12 −4) after the first
  cycle and back after the second. The doorway is the same in both cycles, so the door
  works; it is just never in its build state after an odd number of cycles. The game
  does the same (two cycles on the server, EXP-073).
- **Purplers' enchanting-table door** recycles one redstone dust: a dropper throws it
  out and a hopper below picks it up again. The simulator has no item entities
  ([[../../differences]]), so the dust is lost after the first cycle and the second
  cycle runs without it (it differs from 30 ticks in). This is a simulator limit, not
  the design (backlog D9).
- **LegDen's 7x7 and 8x8** stop part-way in the first cycle already (EXP-068, backlog
  D3); their second cycles start from that jammed state.

## Design lessons

- A door's controller is a set of **exact delays**; a robust design states them (the
  contract, [[mechanism]]) and keeps the slack outside the timing paths.
- **Input safety is a design feature.** Most dataset doors assume the user waits for the
  door to finish; a short gap can jam them for good. A lockout (the project's
  `door_3x3`, [[demonstration]]) costs a few ticks and blocks and makes every gap safe.
- **Doors leave state behind.** A door is only repeatable if every cycle ends where it
  started; the repeat test finds the exceptions (a glass block that alternates, items
  that move).
