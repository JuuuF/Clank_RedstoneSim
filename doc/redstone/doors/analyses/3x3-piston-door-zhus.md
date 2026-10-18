# piston door by Zhus

World: `piston_doors/3x3 piston door by Zhus.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane x = 2; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 18; markers Closed 17, Opening 18, Opened 35
- Reference states: closed at tick 17, open at tick 35. Fully closed at ticks 15-18; fully open at 0-1, 32-35.
- Pistons by role: door 10, fires, moves nothing 1, stack 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): observer 7, block←wire 5, block←wire (QC) 4, block←observer 2, dropper (QC) 1, dropper 1, repeater (QC) 1, wire 1, repeater 1
- Phases (bursts of piston events): 2–15 (32 events, 12 pistons); 19–32 (29 events, 12 pistons)

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
| below | 3 | 4 | 2×1, 4×2 | down 1 (1), down 2 (1), down 1, north 1 (1) |
| north | 3 | 3 | 2×3 | north 1 (3) |
| south | 2 | 2 | 2×2 | south 1 (2) |
| above | 1 | 2 | 4×1 | up 1 (1) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 2 2 -4 S | up | door | 6+2→spat, 12+2→spat, 29+2→pulled | block←observer 1, observer 2 |
| 2 2 -3 S | up | door | 4+2→spat, 21+2→pulled | block←wire (QC) 2 |
| 2 3 -6 S | south | door | 10+2→spat, 27+2→pulled | observer 2 |
| 2 4 -7 S | south | door | 10+2→spat, 27+2→pulled | observer 2 |
| 2 5 -7 S | south | door | 13+2→spat, 30+2→pulled | block←wire (QC) 2 |
| 2 5 -1 S | north | door | 2+17→pulled | dropper (QC) 1 |
| 2 6 -7 S | south | door | 13+2→spat, 30+2→pulled | block←wire 2 |
| 2 6 -1 S | north | door | 2+17→pulled | dropper 1 |
| 2 7 -4 S | down | door | 20+4→pulled | block←wire 1, block←observer 1 |
| 2 8 -4 S | down | door | 5+2→spat, 31+1→pulled | observer 1, repeater (QC) 1, wire 1 |
| 2 2 -2 | down | fires, moves nothing | 4+2→spat, 21+2→spat | block←wire 2 |
| 2 9 -4 S | down | stack | 11+17→pulled | repeater 1 |

<!-- end generated -->
