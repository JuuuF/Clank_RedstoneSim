# piston door by Sydney600mc

World: `piston_doors/4x4 piston door by Sydney600mc.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 4×4 in the plane x = 2; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 31; markers Closing 1, Closed 30, Opening 31, Opened 60
- Reference states: closed at tick 30, open at tick 60. Fully closed at ticks 17-36; fully open at 0-4, 57-71.
- Pistons by role: door 24, fires, moves nothing 2, power mover 2
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←observer 14, dropper (QC) 8, wire 8, block←repeater 4, block←observer+wire 4, dropper 4, block←observer (QC) 4, block←wire 4, observer 2
- Phases (bursts of piston events): 3–11 (52 events, 20 pistons); 15–15 (4 events, 4 pistons); 22–22 (4 events, 4 pistons); 33–41 (52 events, 20 pistons); 45–57 (32 events, 12 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
   0     5     7     9    11    15    17    37    41    48    49    51
....  ....  ....  ~~~~  ####  ####  ####  ####  ....  ....  ....  ....
....  ~..~  #..#  #..#  #..#  ~~~~  ####  .##.  .##.  ~##~  ~..~  #..#
....  ~..~  #..#  #..#  #..#  ~~~~  ####  .##.  .##.  ~##~  ~..~  #..#
....  ....  ....  ~~~~  ####  ####  ####  ####  ....  ....  ....  ....

  57
....
....
....
....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| north | 4 | 8 | 4×4 | north 2 (2), down 1, north 1 (1), up 1, north 1 (1) |
| south | 4 | 8 | 4×4 | south 2 (2), down 1, south 1 (1), up 1, south 1 (1) |
| above | 4 | 4 | 2×4 | up 1 (4) |
| below | 4 | 4 | 2×4 | down 1 (4) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 2 2 -3 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 2 -2 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 2 -1 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 2 0 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 3 -4 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 3 1 S | up | door | 9+2→spat, 39+2→pulled | block←observer 2 |
| 2 5 -6 S | south | door | 15+7→pulled, 45+7→pulled | dropper (QC) 2 |
| 2 5 -5 S | south | door | 5+2→spat, 35+2→pulled, 55+2→pulled | block←observer+wire 2, observer 1 |
| 2 5 -4 S | south | door | 48+1→pulled | block←observer (QC) 1 |
| 2 5 1 S | north | door | 48+1→pulled | block←observer (QC) 1 |
| 2 5 2 S | north | door | 5+2→spat, 35+2→pulled, 55+2→pulled | block←observer+wire 2, observer 1 |
| 2 5 3 S | north | door | 15+7→pulled, 45+7→pulled | dropper (QC) 2 |
| 2 6 -6 S | south | door | 15+7→pulled, 45+7→pulled | dropper 2 |
| 2 6 -5 S | south | door | 5+2→spat, 35+2→pulled, 55+2→pulled | wire 2, block←observer (QC) 1 |
| 2 6 -4 S | south | door | 48+1→pulled | block←observer 1 |
| 2 6 1 S | north | door | 48+1→pulled | block←observer 1 |
| 2 6 2 S | north | door | 5+2→spat, 35+2→pulled, 55+2→pulled | wire 2, block←observer (QC) 1 |
| 2 6 3 S | north | door | 15+7→pulled, 45+7→pulled | dropper 2 |
| 2 8 -4 S | down | door | 9+2→spat, 39+2→pulled | dropper (QC) 2 |
| 2 8 1 S | down | door | 9+2→spat, 39+2→pulled | dropper (QC) 2 |
| 2 9 -3 S | down | door | 9+2→spat, 39+2→pulled | wire 2 |
| 2 9 -2 S | down | door | 9+2→spat, 39+2→pulled | block←wire 2 |
| 2 9 -1 S | down | door | 9+2→spat, 39+2→pulled | block←wire 2 |
| 2 9 0 S | down | door | 9+2→spat, 39+2→pulled | wire 2 |
| 1 3 -4 | north | fires, moves nothing | 3+30→retracted | block←repeater 1 |
| 1 3 1 | south | fires, moves nothing | 3+30→retracted | block←repeater 1 |
| 2 2 -6 S | up | power mover | 7+30→pulled | block←repeater 1 |
| 2 2 3 S | up | power mover | 7+30→pulled | block←repeater 1 |

<!-- end generated -->
