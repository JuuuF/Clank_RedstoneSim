# Robustness: what a door tolerates

Counterfactual experiments on the dataset's doors (mission section 8): one controlled
change at a time, replayed and compared with the original tick by tick. Two tools
(2026-10-18/19; results for the third-party designs in `.sandbox/doors/`, not
committed):

- `python -m tools.doorlab.ablation WORLD --trim`: every block above the floor removed
  (a piston head only with its piston), every conducting block replaced by glass, every
  repeater set to each other delay; then all the blocks whose removal changed nothing
  removed **together**; `--turn`: every retracted piston turned to each other facing;
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
| `4x4-piston-door-kwipla` | 242 | 164 | 1 | 25 | 52 | 52 of 69 | 1 of 15 | 158 → 142 | 1080 → 1080 |
| `4x4-piston-door-sydney600mc` | 199 | 155 | 4 | 14 | 26 | 28 of 50 | 4 of 24 | 125 → 113 | 270 → 270 |
| `4x4-sliding-piston-door-purplers` | 519 | 294 | 0 | 163 | 62 | 105 of 138 | 6 of 6 | 401 → 381 | 880 → 880 |
| `5x5-vault-door-nile` | 589 | 232 | 31 | 229 | 97 | 120 of 144 | 25 of 27 | 425 → 387 | 1050 → 1050 |
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
- **A piston's direction is exact too.** `ablation --turn` set every retracted piston to
  each of its other five facings: 1810 variants in 16 doors (2026-10-19). In the ten
  compact doors every turn breaks the door (Mumbo Jumbo, Zhus, monchiCARP, Rubik,
  Sacred, the spiral, pal1, Kwipla, Sydney, the enchanting-table door). Turns that keep
  the door working exist only in the six larger builds: the staircase 9 of 45 (timing
  only), the seamless door 22 of 175, Lutal's vault 2 of 95, the sliding door 6 of 200,
  the vault lamp door 16 of 215, Nile's 5x5 vault 91 of 310 (82 of them "internal": the
  marked doorway cells unchanged, as for many of its removals above).
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
- **Layer 2 predicts the harmless ones exactly.** A conductor that never receives power
  in the designed run, cuts no wire step and is not an immovable stopper never broke
  any door when turned to glass: 0 of 359 ([[representation]]). The wire cutters break
  11 of 12 times. Of the powered ones only 270 of 736 matter.
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
- **Nor are blocks that something stands on.** Removing the block under a button
  changes nothing in a run, because no update reaches the button. But a door built
  that way cannot be built, and the button breaks at the first update. The trim keeps
  such supports since 2026-10-19 (Kwipla's 4x4: 2 blocks, Nile's 5x5 vault: 1). After
  the trim, every block of the 17 trimmed builds can stay where it is
  (`can_survive`).
- **The trim is game-verified** for Mumbo Jumbo's door, the staircase and Lutal's
  vault (the largest trim: 205 → 145 blocks, box 880 → 640). The trimmed builds run
  tick for tick as in the simulator, with an input stand-in that acts exactly like the
  player's input (EXP-071, EXP-074), so the removed blocks are slack in the game too.

## Input timing

| world | designed gap | safe gap | no-overlap gap | stuck | door ok | recovers | rest ≠ build | sweep with recovery |
|---|---|---|---|---|---|---|---|---|
| `1-wide-hidden-staircase-purplers` | 27 | 10 | 18 | 8–9 | – | 8–9 | 0 | `#######11#############################################################` |
| `3x3-flush-enchanting-table-door-purplers` | 62 | 55 | 57 | 30–33, 35, 44–45 (ignored: 1–29) | 54 | – | 1 | `-----------------------------xxxx#x########xx########x################` |
| `3x3-piston-door-monchicarp` | 17 | 11 | 16 | 1–10 | – | 2–10 | 0 | `x222221111############################################################` |
| `3x3-piston-door-mumbo-jumbo` | 12 | 10 | 10 | 2–9 | – | 2, 7–9 | 0 | `#1wwww111#############################################################` |
| `3x3-piston-door-rubik` | 25 | 20 | 21 | 1–19 | – | 10–11, 14–15 | 0 | `wwwxxxxxx11xx11xxxx###################################################` |
| `3x3-piston-door-sacredredstone` | 41 | 21 | 40 | 1–20 | – | 11, 13–16, 18–19 | 0 | `xxxxxxxxxx1x1111x11x##################################################` |
| `3x3-piston-door-zhus` | 17 | 11 | 16 | 1–10 | – | 2–10 | 0 | `x222221111############################################################` |
| `3x3-seamless-glass-door-nile` | 45 | 16 | 43 | 1–2, 5–15 | 3–4 | 1–5, 7 | 3 | `11111w1wwwwwwww#######################################################` |
| `3x3-spiral-piston-door-purplers` | 22 | 12 | 21 | 1–8, 11 | – | 7 | 1 | `wxxxxx1x##x###########################################################` |
| `3x3-spiral-vault-door-lutal` | 21 | 17 | 21 | 1–4 | 5–16 | – | 0 | `xxxxwwwwwwwwwwww######################################################` |
| `3x4-piston-door-pal1` | 37 | 20 | 35 | 1–19 | – | 10–11 | 1 | `wwwxxxxxx11xxxxxxxx###################################################` |
| `4x4-piston-door-kwipla` | 36 | 25 | 37 | 20–24 (ignored: 1–19) | – | – | 0 | `-------------------wwwxx##############################################` |
| `4x4-piston-door-sydney600mc` | 30 | 19 | 22 | 1–18 | – | 6, 8–11 | 0 | `xxxxx1x1111xxxxxxx####################################################` |
| `4x4-sliding-piston-door-purplers` | 12 | 9 | 12 | 1–8 | – | 1–8 | 0 | `11111111##############################################################` |
| `5x5-glass-piston-door-ashevoy` | 42 | 38 | 41 | 1–37 | – | 1–6, 37 | 0 | `111111wwxxxxwwwwwwwwwwwwwwwwwwwwwwww1#################################` |
| `5x5-vault-door-nile` | 17 | 13 | 16 | 1–12 | – | – | 1 | `wwwwwwwwwwww##########################################################` |
| `5x5-vault-lamp-door-purplers` | 13 | 10 | 10 | 2–6 | 7–9 | 2–9 | 0 | `#11111111#############################################################` |
| `3x3-flush-door-redsim` (ours, `door_3x3`) | 55 | 1 | 27 | – | – | – | 0 | `######################################################################` |

Columns: the gap the world's own timeline uses; the **safe gap**, the shortest gap from
which every longer gap ends **clean** (the whole build in the designed run's rest
state); the **no-overlap gap** (below); the gaps that leave the door **stuck** (the
doorway does not come back); the gaps where the doorway comes back but some other block
differs (**door ok**); the bad gaps (stuck or door ok) that one or two more inputs
**recover** (the whole build, the input included, back in a normal rest state); blocks
whose rest state differs from the saved build (stale saved shapes that the first update
corrects). The last column is the whole sweep, gap 1 first: `#` clean; `-` the second press
is ignored (a button is still pressed: stone 20 ticks, wood 30); after a bad gap and one
or two more inputs, `1` / `2` recovered after that many, `w` the doorway works again but
some block stays off, `x` the doorway is still wrong.

What the sweep shows (2026-10-19):

- **Every dataset door needs a minimum gap between the two flips.** It runs from 9
  ticks (Purplers' sliding door) to 38 (Ashevoy's glass door). The enchanting-table
  door's 55 is not evidence: its run depends on an item the simulator does not have
  (below). Every world's own timeline waits 2–29 ticks longer than its safe gap. Below
  the safe gap, every dataset door has gaps that leave the doorway wrong. For the two
  button doors, a second press while the button is still down (stone 20 ticks, wood
  30) is no input at all: Kwipla's gaps 1–19 and the enchanting-table door's 1–29 are
  ignored presses, and the door just finishes its first sequence. The
  project's `door_3x3` is clean at every gap: its lockout ignores the second flip until
  the sequence is done ([[demonstration]]).
- **"Wait until the doorway has settled" does not give the safe gap.** In 8 of 17
  doors the safe gap is shorter than the time the first sequence takes to settle the
  doorway (the staircase 10 vs 25, the seamless door 16 vs 39, Sacred 21 vs 38). In 2
  it is equal (Mumbo Jumbo, the sliding door). In 7 it is longer: the mechanism keeps
  moving behind a doorway that already looks done (Rubik 20 vs 14, Sydney 19 vs 16,
  Nile's vault 13 vs 9, the vault lamp door 10 vs 7).
- **The no-overlap gap is an upper bound in all 17 doors.** It is the smallest gap at
  which the second sequence's first piston event comes after the first sequence's
  last moving block has come to rest (its last piston event + 2 ticks of motion). No
  door needs more. Mumbo Jumbo's door and the vault lamp door need exactly that. Six
  more are within 3 ticks: the enchanting-table door, Rubik, Sydney, the sliding door,
  Ashevoy, Nile's vault. The other nine accept the second flip while the first
  sequence still moves, because its last moves are not in the way of the second
  sequence's first ones: Sacred at 21 instead of 40, the seamless door 16 instead of
  43, pal1 20 / 35, Kwipla 25 / 37, the spiral 12 / 21, the staircase 10 / 18, Zhus and
  monchiCARP 11 / 16, Lutal 17 / 21. So the safe gap depends on how the two sequences
  interleave and has to be measured. Waiting for the no-overlap gap is the safe rule
  for a user or a lockout that knows only the piston events.
- **The window is not always monotonic.** Purplers' spiral door is clean at 9–10, stuck
  at 11 and clean from 12. Mumbo Jumbo's door and the vault lamp door are clean at gap 1:
  a 1-tick input. The vault lamp door does not move at all; Mumbo Jumbo's doorway
  moves and comes back. The staircase is clean at 1–7 and stuck only at 8–9 (its
  stairs move and come back).
- **Recovery: one or two more inputs restore the whole build after 72 of the 224 bad
  gaps** (62 after one, 10 after two; ignored presses not counted). In 73 more the
  doorway works again but some other block stays off; in 79 the doorway stays wrong.
  By door:
  - every bad gap recovers: the sliding door, the vault lamp door, the staircase (one
    more input each);
  - almost every one: Zhus and monchiCARP (gaps 2–6 after two more inputs, 7–10 after
    one, gap 1 not; the mirror twins behave the same);
  - Kwipla's 4x4: after its 5 real bad gaps the doorway works again (20–22) or stays
    wrong (23–24);
  - the doorway always works again, but some gaps leave a block off: the seamless door
    (6 recover, 9 work), Nile's 5x5 vault (all 12 work), Mumbo Jumbo's door (2 and 7–9
    recover, 3–6 work), Lutal's vault (5–16 work: a sea lantern of the vault's frame
    ends two cells off, 4 5 −2 instead of 4 5 −4, and stays there; 1–4 stay wrong);
  - most bad gaps leave the doorway wrong: Sacred 13 of 20, pal1 14 of 19, Sydney 13 of
    18, Rubik 12 of 19, the spiral 7 of 9. Ashevoy's door: 7 recover, 26 work, 4 stay
    wrong. The enchanting-table door: none of its 8 real bad gaps recovers
    (simulator-only, below).
- **A button ignores a press while it is still down.** At first this looked like a
  controller out of step (an earlier version of this page said so). In Kwipla's door,
  after a second press at gap 12, the next designed cycle leaves it mostly open after
  the "close" press and closed after the "open" press. The trace shows why: the second
  press came while the stone button was still pressed, so it did nothing. The door
  closed, stayed closed, and every later press is simply one behind. Kwipla's memory is
  a redstone block that a sticky piston toggles between two cells with 2-tick pulses
  (pushed and left at 6, pulled back at 44); it toggles once per registered press. For
  a lever door, "after one" means one more flip brings the build to the closed rest
  state.
- **Lasting jams are door blocks left behind** (backlog D10). Where the doorway stays
  wrong, a few door blocks stay in wrong cells, most of them in the doorway: Sacred 4
  smooth stone (gap 5), pal1 2 gold blocks (gap 6, 3 before the extra inputs), Sydney
  12 iron blocks (gap 3). Their number stays the same through four more inputs while
  the rest of the door cycles around them. The second input cuts the first sequence
  short (Sacred, gap 5: 13 pulls instead of 20, 11 plain extensions instead of 18), and
  the blocks it would have moved are never moved back.
- **What goes wrong at the boundary** (each door's last bad gap; backlog D11). In 7
  doors, extensions are lost: queued while powered, but the power is gone when the
  event runs (Rubik, Sacred, seamless, the spiral, Lutal, pal1, Sydney). In 3 doors, a
  push hits a sticky piston that is still extended (the enchanting-table door, Kwipla,
  Ashevoy). In the other 7, no extension fails at all: the second sequence only runs in
  another order (the staircase, monchiCARP, Mumbo Jumbo, Zhus, the sliding door, Nile's
  vault, the vault lamp door).
- **The enchanting-table door** recycles one redstone dust through a dropper, the
  ground and a hopper; the simulator has no item entities ([[../../differences]]).
  Its sweep is simulator-only and assumes the dust is not needed twice within one run
  (the two-cycle test shows it is needed again 30 ticks into the second cycle, D9).


### What the second flip waits for (D11, 2026-10-19)

`python -m tools.doorlab.inputs --explain WORLD` replays the last bad gap (the safe gap − 1)
and the safe gap and finds the first piston event that is in one run and not in the
other (each event matched at the same tick, the first sequence, or one tick later, the
second), with what it ran into. The binding constraint per door (ticks after the flips):

| door | safe gap | the event that breaks at safe − 1 | the first-sequence move it waits for | kind |
|---|---|---|---|---|
| Mumbo Jumbo | 10 | the center piston 5 3 −2 is cut at flip2+1 while pushing B and C (drop → spit) | its own push at flip1+8, landing at +10 | push dropped |
| vault lamp | 10 | the south carrier's front 0 6 2 is cut at flip2+2 while pushing the redstone block | its push at flip1+9, landing +11 | push dropped |
| Zhus, monchiCARP | 11 | the top piston 3 7 0 / 2 7 −4 is cut at flip2+6 while pushing | the column push by 3 2 0 at flip1+11 and the top piston's own push at +15/16 | push dropped |
| Lutal | 17 | the hub piston 4 5 −5: at the safe gap the second flip's retract meets its push and spits (flip2+7), one tick earlier it retracts after the landing and the lantern ends two cells off | the hub stack's push at flip1+13 | spit must coincide |
| Rubik | 20 | the lowered center piston −9 −56 −4 extends at flip1+23 (one tick after landing, R-026) and the second sequence's 2-tick pulse must still be on then; at safe − 1 it is "unpowered" | the stack's lowering at flip1+20 | pulse must cover landing+1 |
| pal1 | 20 | the same: 5 3 −3 lowered at flip1+20, its extension at +23 unpowered | the lowering | pulse must cover landing+1 |
| Sydney600mc | 19 | the stacks' pulled-back side pistons extend at flip1+24 (4 of them unpowered at safe − 1) | the stacks' return | pulse must cover landing+1 |
| Purplers' spiral | 12 | the center piston −1 2 0 retracts at 14–16 and its event runs at 17; the first opening pulse (flip2+4..5) is over by then at gap 11 (gaps 9–10 merge the pulses harmlessly: the non-monotonic window) | its own retraction | pulse must cover landing+1 |
| sliding door | 9 | the east carried piston 5 3 −1 is told to retract at flip2+1 while it is still being carried (its event is skipped) | the first stroke at flip1+9, landing +11 | moved piston not landed |
| seamless | 16 | the inchworm's first push 2 1 −3 at flip2+8 runs in the same tick as the tidy pulls of 0..2 10 −3 at flip1+23, which take its power away (unpowered); one tick later it pushes | the last tidy pull at flip1+23 | tail event changes the power |
| Sacred | 21 | the lever's second flip retracts the top piston 4 10 −1 at flip2+1 and, one tick early, pulls the center block up with it instead of leaving it | the lowered top piston's last pull-back at flip1+22 | tail event changes what is pulled |
| Kwipla | 25 | the stack 1 6 1 returns two ticks earlier (the observer clock moves in 2-tick steps) and lands in the same tick as the inner pulls 0 6 −1 / 0 6 0 / 0 5 0 | the inner pulls at flip2+9 must precede the stack's return | same-tick order |
| Ashevoy | 38 | the chain push 0 18 −2 at flip2+4 moves other blocks than at the safe gap | the first sequence's last landing at flip1+41 | tail landing |
| staircase | 10 | the step piston −2 3 −2 at flip2+2 extends where it must be vetoed by a block in its way | the step placed at flip1+8..10 | a veto block must be in place |
| Nile's vault | 13 | no piston event differs: the leftover is a controller state (one block off, the doorway works) | — | controller state |

So the "real input contract" is one pair of events per door: in 5 doors the second flip's
power cut reaches a piston whose push has not landed (a drop spits the block: the cut
must come at landing + 1 or later); in 4 the opening's short pulse must still be on one
tick after a lowered or carried piston lands (R-026: a piston that lands next to power
acts one tick after landing); in the others a tail event of the first sequence (a tidy
pull, a landing, a stack's return) must precede the second sequence's first move, or a
veto block must be in place. The no-overlap gap is an upper bound because it waits for
the last move of all; the safe gap waits only for the move the second sequence touches.

### Why lasting jams last (D10, 2026-10-19)

`python -m tools.doorlab.inputs --jam --gap G WORLD` runs the jam and two more designed
cycles and follows every door block (layer 3 tokens): which blocks end in a wrong cell,
which designed moves the jammed cycle did not make, and what the later cycles do with
them. `--repair --gap G` then tries every second-cycle gap 1–40.

- **Sacred, gap 5** (4 smooth stone off): the two south blocks 4 8 2 / 4 7 2 missed one
  pulse and are thereafter moved in **anti-phase**: pulled out when the door closes
  (tick 140) and pushed in when it opens (258). Their pistons get the same 2-tick observer
  pulse on both lever edges, which spits the block in when the cell is empty and pulls it
  out when it is full: a **toggle**, with no absolute position. The two lower blocks
  4 5 0 / 4 5 1 were pushed up the center column and the later cycles push more in
  (4 7 0, 4 6 0): an **accumulation**. Repair: a second cycle with gap 4 or 5 (the same
  jam again) brings the whole build back: the toggles miss a pulse once more and are in
  phase again. **Game-verified**: the jam timeline (lever at 2, 7, 127, 247) run whole
  on the 26.3 server matches the simulator at every one of its 370 ticks (EXP-078).
- **pal1, gap 6** (2 gold blocks off): both center blocks end up the column (5 6 −3,
  5 5 −3): the jammed cycle missed the stack's push at 13 and the pulls at 54 / 64; the
  later cycles pull them one cell and push them back up. No second-cycle gap 1–40 repairs.
- **Sydney600mc, gap 3** (14 iron blocks off): the opening edge is swallowed by observers
  still in their closing pulse, so whole groups miss their pulses; afterwards the side
  blocks move in anti-phase (pulled out at 130–142 on the closing flip, pushed in at
  248–258 on the opening one) and the top row stays one cell down. No second-cycle gap
  1–40 repairs.
- **Rubik, gap 5**: repaired by a second cycle with gap 10, 11, 12 or 18.

Lesson: **edge-pulse toggles do not self-correct.** A piston driven by one pulse on both
edges moves its block to the other cell each time; a lost pulse inverts the block for
good, and every normal cycle keeps it inverted. Level-driven pistons (held while a line
is on: Mumbo Jumbo, the vault lamp door, the sliding door, the staircase) come back
after one more input ([[#input-timing]]). A second deliberately short cycle can re-sync
a toggle door (Sacred, Rubik) but not a column that has accumulated blocks (pal1,
Sydney).

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
- **Input safety is a design feature.** Every dataset door assumes its user waits. A
  shorter gap leaves the doorway wrong, and in 152 of the 224 bad gaps one or two more
  inputs do not restore the build (in 79 the doorway itself stays wrong). A button
  only hides the problem for its press time. A lockout (the project's `door_3x3`, [[demonstration]])
  costs a few ticks and blocks and makes every gap safe. Without one, the no-overlap
  gap is a safe waiting time.
- **Doors leave state behind.** A door is only repeatable if every cycle ends where it
  started; the repeat test finds the exceptions (a glass block that alternates, items
  that move).
