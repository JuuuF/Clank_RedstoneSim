# piston door by monchiCARP

World: `piston_doors/3x3 piston door by monchiCARP.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane z = 0; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 18; markers Closing 1, Closed 17, Opening 18, Opened 34
- Reference states: closed at tick 17, open at tick 34. Fully closed at ticks 15-18; fully open at 0-1, 32-35.
- Pistons by role: door 10, fires, moves nothing 1, stack 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): observer 5, block←observer 4, block←wire (QC) 4, block←wire 4, repeater (QC) 1, wire 1, repeater 1, dropper (QC) 1, dropper 1
- Phases (bursts of piston events): 2–15 (31 events, 11 pistons); 19–32 (29 events, 12 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    2    4    5    6    7    8   10   12   13   14   15   19   20
...  ..~  ..#  .~#  .~#  .##  .##  .##  .##  ~##  ~##  ###  ##.  #~.
...  ..~  ..#  ..#  ..#  ..#  ..#  ..#  .~#  ~~#  ~##  ###  ##.  #~.
...  ...  ..~  ..~  .~#  .~#  .##  ~##  #~#  #~#  ###  ###  ###  #~#

 22   23   24   26   29   31   32
##.  ##.  #~.  ##.  ##.  ##.  ...
##.  ##.  #..  #..  #..  #..  ...
###  ##.  ##.  ##.  .#.  ...  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 3 | 4 | 2×1, 4×2 | down 1 (1), down 2 (1), down 1, west 1 (1) |
| west | 3 | 3 | 2×3 | west 1 (3) |
| east | 2 | 2 | 2×2 | east 1 (2) |
| above | 1 | 2 | 4×1 | up 1 (1) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 0 4 0 S | east | door | 10+2→spat, 27+2→pulled | block←observer 2 |
| 0 5 0 S | east | door | 13+2→spat, 30+2→pulled | block←wire (QC) 2 |
| 0 6 0 S | east | door | 13+2→spat, 30+2→pulled | block←wire 2 |
| 1 3 0 S | east | door | 10+2→spat, 27+2→pulled | observer 2 |
| 3 2 0 S | up | door | 6+2→spat, 12+2→spat, 29+2→pulled | block←observer 1, observer 2 |
| 3 7 0 S | down | door | 20+4→pulled | block←observer 1 |
| 3 8 0 S | down | door | 5+2→spat, 31+1→pulled | observer 1, repeater (QC) 1, wire 1 |
| 4 2 0 S | up | door | 4+2→spat, 21+2→pulled | block←wire (QC) 2 |
| 6 5 0 S | west | door | 2+17→pulled | dropper (QC) 1 |
| 6 6 0 S | west | door | 2+17→pulled | dropper 1 |
| 5 2 0 | down | fires, moves nothing | 4+2→spat, 21+2→spat | block←wire 2 |
| 3 9 0 S | down | stack | 11+17→pulled | repeater 1 |

<!-- end generated -->
