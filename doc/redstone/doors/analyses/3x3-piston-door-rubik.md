# piston door by Rubik

World: `piston_doors/3x3 piston door by Rubik.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane z = -4; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 26; markers Closing 1, Closed 25, Opening 26, Opened 54
- Reference states: closed at tick 25, open at tick 54. Fully closed at ticks 15-29; fully open at 0-2, 52-68.
- Pistons by role: door 11
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 6, wire 4, block←wire (QC) 4, block←observer 3, repeater 2, observer 2, block←observer (QC) 1
- Phases (bursts of piston events): 3–9 (27 events, 9 pistons); 13–13 (1 events, 1 pistons); 21–21 (1 events, 1 pistons); 28–34 (27 events, 9 pistons); 38–42 (4 events, 2 pistons); 46–52 (3 events, 2 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    7    9   13   15   30   32   34   41   42   44   52
...  ...  ...  ~~~  ###  ###  ###  ###  ###  ...  ...  ...  ...  ...
...  ...  ...  ~.~  #.#  #~#  ###  ###  ###  .#.  .#.  ...  ...  ...
...  .~.  ~#.  ##~  ###  #~#  ###  #.#  ..#  ...  .~.  .~.  .#.  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| west | 3 | 3 | 2×3 | west 1 (3) |
| below | 2 | 4 | 4×2 | down 2 (1), down 1, east 1 (1) |
| above | 2 | 2 | 2×2 | up 1 (2) |
| east | 2 | 2 | 2×2 | east 1 (2) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -12 -54 -4 S | east | door | 5+2→spat, 30+2→pulled | wire 2 |
| -12 -53 -4 S | east | door | 7+2→spat, 32+2→pulled | block←wire (QC) 2 |
| -12 -52 -4 S | east | door | 7+2→spat, 32+2→pulled | block←wire 2 |
| -9 -57 -4 S | up | door | 13+8→pulled, 38+8→pulled | repeater 2 |
| -9 -56 -4 S | up | door | 3+2→spat, 28+2→pulled, 49+3→pulled | block←observer 2, block←observer (QC) 1 |
| -9 -55 -4 S | up | door | 41+1→pulled | block←observer 1 |
| -9 -50 -4 S | down | door | 7+2→spat, 32+2→pulled | block←wire 2 |
| -8 -50 -4 S | down | door | 7+2→spat, 32+2→pulled | wire 2 |
| -7 -55 -4 S | west | door | 7+2→spat, 32+2→pulled | observer 2 |
| -6 -54 -4 S | west | door | 7+2→spat, 32+2→pulled | block←wire (QC) 2 |
| -6 -53 -4 S | west | door | 7+2→spat, 32+2→pulled | block←wire 2 |

<!-- end generated -->
