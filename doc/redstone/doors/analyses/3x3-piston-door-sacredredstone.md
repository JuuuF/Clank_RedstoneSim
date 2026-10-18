# piston door by SacredRedstone

World: `piston_doors/3x3 piston door by SacredRedstone.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(Hand-written 2026-10-19 from the replay, `why` traces and the ablation;
[[../robustness]], [[../metrics]].)

**The whole door is one vertical plane.** Every piston, observer, repeater, lamp and
door block is at x = 4, in the wall of the doorway; only the lever sticks out (x = 3).
That is why it is the smallest door in the dataset: a 2 × 8 × 7 box, 48 blocks above
the floor, and the trim finds no block whose removal changes nothing.

**Open, the nine blocks form a ring around the doorway, in the same plane:** two above
(y 9), two north (z −2), three south (z 2), two below (y 5). Closing moves each one cell
in; the center column is filled from below. Most moves are 2-tick observer pulses into
sticky pistons, which push and leave the block (spits, [[../patterns]]).

Closing (lever on at 2; ticks of the doorway):

| tick | what moves |
|---|---|
| 3 | the lever's block powers the two top pistons directly: the top-left block down; a two-piston stack lowers its second piston and pushes the top-center block down |
| 8 | the two north blocks, pushed in by the pistons two cells out (z −3) |
| 13 | the two upper south blocks |
| 14 | the piston under the center (4 4 0) pushes the first lower block up one |
| 18 | the lower south corner (4 6 1) |
| 19–23 | the lowered top piston, powered by quasi-connectivity (a repeater powers the cell above it), pushes the top-center block down into the center and pulls it back. For ticks 21–22 its head is a door block: the doorway is first fully closed then |
| 20 | the second lower block shifts under the center column (piston 4 5 2) |
| 24 | the piston under the center pushes the column of two up: the center is filled; fully closed from 26 |
| 30–38 | the lower south corner is pulled out and pushed back in (below) |

Opening (lever off at 43) runs the stages back, with the same corner blink, and is
done at 85.

**The controller is a chain of observers.** 27 of the 39 extensions are powered by
observers, directly or through a block (some by quasi-connectivity). The observers
watch what earlier stages change (the bottom row's the center piston, the corner's a
lamp), so a stage starts the next one 2 ticks later; four repeaters (delays 1–4) sit
in the chain. The bottom row
(y 4) is one such chain: observers at z −2, −1 and 1 around the center piston, all
facing north.

**The corner blink is a 0-tick lamp flicker.** The corner piston (4 6 3) is powered by
an observer (4 5 3) that watches a redstone lamp (4 4 3). The lamp is lit through a
wool block by the bottom chain's observer at 4 4 1, which pulses every time the center
piston moves. One pulse ends at 22 and the next starts at 26: 4 ticks, exactly the
lamp's turn-off delay. At tick
26 the lamp's own scheduled turn-off (from 22) runs before the observer's new pulse
(scheduled at 24) relights it: the lamp goes off and on within one tick. No frame
shows it, but the corner observer sees two changes and fires (`why` from 4 5 3 at 28;
the rule: [[../../records/R-028-lamp-flicker]]).
Its piston pulls the corner block out at 28. The lamp's real turn-off at 36 fires the
observer again and pushes the block back at 38. The door still ends right, but it is
fully closed at 26–29, open at one corner for 8 ticks, and settled only at 40. The
same happens in the opening (59, 69, 79). The game does the same: the whole door
matches the simulator at every tick (EXP-075).

**The door needs the flicker** (inferred from the pulse table, not tested by a
change). Each pulse of the corner piston is 2 ticks long, so what it does depends on
where the block is. Next to the head's cell, a pulse pushes the block in and leaves
it. One cell further, the head extends into the empty cell and, retracting, pulls the
block back out. Closing gives in, out, in (18 spat, 28 pulled, 38 spat), opening out,
in, out (59, 69, 79). With only the lamp's two visible changes there would be two
pulses per half-cycle. Closing would end with the corner pulled out again at 38, and
opening with it pushed back in at 79. The third pulse, the flicker's, makes the count
odd and the corner end right.

Lessons:

- A single-plane layout is the most compact way to build a 3x3 flush door: storage,
  pistons and logic share the doorway's wall.
- A lamp used as a pulse stretcher can flicker within a tick when two pulses come
  exactly its delay apart. An observer on it sees the flicker, though no frame does
  ([[../../records/R-028-lamp-flicker]]). Here the design depends on it: a timing
  that works by an in-tick order no frame shows is fragile to any change of one tick.
- "Fully closed" is not "done": Sacred's doorway is first full at tick 21 with a piston
  head in it, and the door settles at 40 ([[../metrics]] reports both).

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane x = 4; 0 more output cells outside it.
- Timeline: use lever at 2, use lever at 43; markers Closing 1, Closed 42, Opening 43, Opened 87
- Reference states: closed at tick 42, open at tick 87. Fully closed at ticks 21-22, 26-29, 40-43; fully open at 0-2, 85-116.
- Pistons by role: door 11
- How extensions were powered (block giving the signal; QC = through the block above the piston): observer 12, block←observer 9, block←observer (QC) 4, block←wire 4, observer (QC) 2, block←lever+wire 2, repeater 2, repeater (QC) 2, block←lever+wire (QC) 1, block←wire (QC) 1
- Phases (bursts of piston events): 1–3 (5 events, 3 pistons); 8–32 (35 events, 8 pistons); 38–40 (3 events, 1 pistons); 44–44 (2 events, 2 pistons); 49–81 (63 events, 11 pistons); 85–85 (1 events, 1 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    8   10   13   14   15   16   18   19   20   21   23
...  ~~.  ##.  ##.  ##.  ##~  ##~  ###  ###  ###  #~#  #~#  ###  #~#
...  ...  ...  ~..  #..  #.~  #.~  #.#  #.#  #.#  #~#  #~#  ###  #.#
...  ...  ...  ~..  #..  #..  #~.  #~.  ##.  ##~  ##~  ###  ###  ###

 24   25   26   30   38   40   44   51   56   57   59   60   61   62
#~#  ###  ###  ###  ###  ###  .##  .##  .#.  ~#.  ##.  #~.  #~.  ##.
#~#  #~#  ###  ###  ###  ###  ###  .##  .#.  .#.  .#.  .~.  .~.  .#.
#~#  #~#  ###  ##.  ##~  ###  ###  .##  .##  ..#  ..#  .~#  .~.  .#.

 64   66   67   69   71   77   81   83   85
#~.  ##.  .#~  .##  .##  ...  .~.  .#.  ...
...  ...  ..~  ..#  ..#  ...  ...  ...  ...
.#.  .#.  ...  ..~  ..#  ..#  ...  ...  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| south | 3 | 3 | 4×2, 6×1 | south 1 (3) |
| above | 2 | 4 | 4×1, 8×1 | up 1 (2) |
| north | 2 | 2 | 2×2 | north 1 (2) |
| below | 2 | 3 | 4×2 | down 2 (1), down 1, south 1 (1) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 4 4 0 S | up | door | 14+2→spat, 24+2→spat, 55+2→pulled, 65+2→pulled | observer 4 |
| 4 5 2 S | north | door | 20+2→spat, 26+2→spat, 31+1→spat, 57+2→spat, 62+1→pulled | block←observer 5 |
| 4 6 -3 S | south | door | 8+2→spat, 49+2→pulled | observer (QC) 2 |
| 4 6 3 S | north | door | 18+2→spat, 28+2→pulled, 38+2→spat, 59+2→pulled, 69+2→spat, 79+2→pulled | observer 6 |
| 4 7 -3 S | south | door | 8+2→spat, 49+2→pulled | observer 2 |
| 4 7 3 S | north | door | 13+2→spat, 54+2→pulled, 67+2→spat, 75+2→pulled | block←observer (QC) 4 |
| 4 8 3 S | north | door | 13+2→spat, 54+2→pulled, 67+2→spat, 75+2→pulled | block←observer 4 |
| 4 9 0 S | down | door | 19+4→pulled, 60+4→pulled | repeater (QC) 2 |
| 4 10 -1 S | down | door | 3+41→pulled, 57+2→spat, 65+2→pulled | block←lever+wire 1, block←wire 2 |
| 4 10 0 S | down | door | 73+4→pulled, 81+4→pulled | block←lever+wire (QC) 1, block←wire (QC) 1, repeater 2 |
| 4 11 0 S | down | door | 3+41→pulled, 57+2→spat, 65+2→pulled | block←lever+wire 1, block←wire 2 |

<!-- end generated -->
