# piston door by Kwipla

World: `piston_doors/4x4 piston door by Kwipla.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 4×4 in the plane x = 0; 0 more output cells outside it.
- Timeline: use stone_button at 1, use stone_button at 37; markers Closing 1, Closed 36, Opening 37, Opened 78
- Reference states: closed at tick 36, open at tick 78. Fully closed at ticks 28-45; fully open at 0-9, 76-115.
- Pistons by role: door 24, fires, moves nothing 4, helper 2, power mover 2
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 19, observer (QC) 12, wire 11, observer 10, block←observer 8, block←observer+wire 6, block←wire (QC) 3, block←repeater+wire 1
- Phases (bursts of piston events): 2–2 (1 events, 1 pistons); 6–22 (54 events, 24 pistons); 26–28 (12 events, 4 pistons); 34–38 (13 events, 5 pistons); 42–58 (60 events, 24 pistons); 62–76 (60 events, 14 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
   0    10    12    14    16    18    20    22    26    28    46    52
....  ....  ....  ....  ....  ~..~  #~~#  ####  ####  ####  ####  ####
....  ....  ....  ~..~  #..#  #..#  #..#  #..#  ~~~~  ####  ####  .##.
....  ....  ....  ~..~  #..#  #..#  #..#  #..#  ~~~~  ####  ####  .##.
....  ~~~~  ####  ####  ####  ####  ####  ####  ####  ####  ....  ....

  56    58    66    68    70    76
.##.  ....  ....  ....  ....  ....
.##.  .##.  ~##~  ~..~  #..#  ....
.##.  .##.  ~##~  ~..~  #..#  ....
....  ....  ....  ....  ....  ....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 4 | 4 | 2×4 | down 1 (4) |
| south | 4 | 8 | 4×4 | south 2 (2), up 1, south 1 (1), down 1, south 1 (1) |
| north | 4 | 8 | 4×4 | north 2 (2), up 1, north 1 (1), down 1, north 1 (1) |
| above | 4 | 4 | 2×4 | up 1 (4) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 0 6 -3 S | up | door | 10+36→pulled | block←wire 1 |
| 0 6 -2 S | up | door | 10+36→pulled | wire 1 |
| 0 6 -1 S | up | door | 10+36→pulled | block←repeater+wire 1 |
| 0 6 0 S | up | door | 10+36→pulled | wire 1 |
| 0 7 -4 S | up | door | 18+2→spat, 48+2→retracted, retracted at 52, 55+1→pulled | observer (QC) 2, wire 1 |
| 0 7 1 S | up | door | 18+2→spat, 48+2→retracted, retracted at 52, 55+1→pulled | observer (QC) 2, wire 1 |
| 0 9 -6 S | south | door | 26+2→spat, 34+2→pulled, 62+2→spat, 70+2→pulled | observer (QC) 4 |
| 0 9 -5 S | south | door | 14+2→spat, 50+2→pulled, 75+1→pulled | block←observer+wire 3 |
| 0 9 -4 S | south | door | 66+2→pulled | block←wire (QC) 1 |
| 0 9 1 S | north | door | 66+2→pulled | block←wire (QC) 1 |
| 0 9 2 S | north | door | 14+2→spat, 50+2→pulled, 75+1→pulled | block←observer+wire 3 |
| 0 9 3 S | north | door | 26+2→spat, 34+2→pulled, 62+2→spat, 70+2→pulled | observer (QC) 4 |
| 0 10 -6 S | south | door | 26+2→spat, 34+2→pulled, 62+2→spat, 70+2→pulled | observer 4 |
| 0 10 -5 S | south | door | 14+2→spat, 50+2→pulled, 75+1→pulled | wire 3 |
| 0 10 -4 S | south | door | 66+2→pulled | block←wire 1 |
| 0 10 1 S | north | door | 66+2→pulled | block←wire 1 |
| 0 10 2 S | north | door | 14+2→spat, 50+2→pulled, 75+1→pulled | wire 3 |
| 0 10 3 S | north | door | 26+2→spat, 34+2→pulled, 62+2→spat, 70+2→pulled | observer 4 |
| 0 12 -4 S | down | door | 18+2→spat, 54+2→pulled | block←wire 2 |
| 0 12 1 S | down | door | 18+2→spat, 54+2→pulled | block←wire 2 |
| 0 13 -3 S | down | door | 18+2→spat, 54+2→pulled | block←wire 2 |
| 0 13 -2 S | down | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 0 13 -1 S | down | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 0 13 0 S | down | door | 18+2→spat, 54+2→pulled | block←wire 2 |
| 0 8 -6 | east | fires, moves nothing | 12+2→spat, 48+2→spat | block←wire 2 |
| 0 8 3 | east | fires, moves nothing | 12+2→spat, 48+2→spat | block←wire 2 |
| 1 6 -4 | up | fires, moves nothing | 10+36→retracted, 62+2→spat, 70+2→spat | block←wire 1, block←observer 2 |
| 1 6 1 | up | fires, moves nothing | 10+36→retracted, 62+2→spat, 70+2→spat | wire 1, block←observer 2 |
| 0 5 -3 S | north | helper | 10+36→pulled | block←wire (QC) 1 |
| 0 5 0 S | south | helper | 10+36→pulled | block←wire 1 |
| 3 6 -6 S | south | power mover | 2+19→pulled, 38+19→pulled | block←wire 2 |
| 3 6 -3 S | south | power mover | 6+2→spat, 42+2→pulled | observer 2 |

<!-- end generated -->
