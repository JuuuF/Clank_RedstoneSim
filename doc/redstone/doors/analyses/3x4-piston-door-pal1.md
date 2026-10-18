# piston door by pal1_

World: `piston_doors/3x4 piston door by pal1_.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×4 in the plane z = -3; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 38; markers Closing 1, Closed 37, Opening 38, Opened 85
- Reference states: closed at tick 37, open at tick 85. Fully closed at ticks 29-41; fully open at 0-2, 82-97.
- Pistons by role: door 16, power mover 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←observer 9, wire 6, observer 5, wire (QC) 5, repeater 4, block←observer (QC) 3, block←observer+wire 2, repeater (QC) 2
- Phases (bursts of piston events): 3–13 (31 events, 11 pistons); 17–23 (10 events, 4 pistons); 27–27 (2 events, 2 pistons); 35–35 (1 events, 1 pistons); 40–68 (51 events, 17 pistons); 72–72 (1 events, 1 pistons); 80–82 (3 events, 1 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    7    9   11   13   15   17   19   27   29   42   46
...  ...  ...  ...  ..~  ~.#  #.#  #.#  #~#  ###  #~#  ###  ###  ###
...  ...  ...  ...  ..~  ~.#  #.#  #.#  #.#  #.#  #~#  ###  ###  ###
...  ...  ...  ..~  ~.#  #.#  #~#  ###  ###  ###  ###  ###  ###  ##.
...  .~.  .#.  .#~  ~##  ###  #~#  ###  ###  ###  ###  ###  #.#  #..

 48   50   53   54   56   64   67   68   70   82
##.  .#.  .#.  .#.  ...  ...  .~.  .~.  .#.  ...
##.  .#.  .#.  .#.  .#.  .#.  .#.  ...  ...  ...
.#.  .#.  .#.  ...  ...  ...  ...  ...  ...  ...
...  ...  .~.  .~.  .#.  ...  ...  ...  ...  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| east | 4 | 4 | 2×4 | east 1 (4) |
| west | 4 | 4 | 2×4 | west 1 (4) |
| below | 2 | 4 | 4×2 | down 2 (1), down 1, west 1 (1) |
| above | 2 | 4 | 4×2 | up 2 (1), up 1, east 1 (1) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 2 5 -3 S | east | door | 9+2→spat, 46+2→pulled | block←observer+wire 2 |
| 2 6 -3 S | east | door | 9+2→spat, 46+2→pulled | wire 2 |
| 2 7 -3 S | east | door | 11+2→spat, 48+2→pulled | block←observer (QC) 2 |
| 2 8 -3 S | east | door | 11+2→spat, 48+2→pulled | block←observer 2 |
| 3 4 -3 S | east | door | 7+2→spat, 44+2→pulled | observer 2 |
| 5 2 -3 S | up | door | 13+8→pulled, 50+8→pulled | repeater 2 |
| 5 3 -3 S | up | door | 3+2→spat, 40+2→pulled, 61+3→pulled | block←observer 2, block←observer (QC) 1 |
| 5 4 -3 S | up | door | 53+1→pulled | block←observer 1 |
| 5 9 -3 S | down | door | 67+1→pulled | block←observer 1 |
| 5 10 -3 S | down | door | 17+2→spat, 54+2→pulled, 80+2→pulled | block←observer 3, repeater (QC) 2 |
| 5 11 -3 S | down | door | 27+8→pulled, 64+8→pulled | repeater 2 |
| 7 9 -3 S | west | door | 21+2→spat, 56+2→retracted, pulled at 60 | observer 1, wire (QC) 1 |
| 8 5 -3 S | west | door | 7+2→spat, 44+2→pulled | wire (QC) 2 |
| 8 6 -3 S | west | door | 7+2→spat, 44+2→pulled | wire 2 |
| 8 7 -3 S | west | door | 9+2→spat, 46+2→pulled | wire (QC) 2 |
| 8 8 -3 S | west | door | 9+2→spat, 46+2→pulled | wire 2 |
| 2 12 -3 S | west | power mover | 17+2→pulled, 54+2→spat | observer 2 |

<!-- end generated -->
