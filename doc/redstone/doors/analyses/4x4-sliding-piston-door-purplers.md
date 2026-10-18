# Sliding Piston Door by Purplers

World: `piston_doors_with_slime/4x4 Sliding Piston Door by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 4×4 in the plane z = -2; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 13; markers Closing 1, Closed 12, Opening 13, Opened 22
- Reference states: closed at tick 12, open at tick 22. Fully closed at ticks 10-13; fully open at 0-4, 17-53.
- Pistons by role: door 8, fires, moves nothing 4, helper 22, idle 4, power mover 20, power switch 8, stack 4
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 28, redstone_block 14, redstone_block (QC) 12, wire 8, block←wire (QC) 6, block←comparator (QC) 4, wire (QC) 4, block←repeater (QC) 2
- Phases (bursts of piston events): 2–20 (162 events, 66 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
   0     5     7     8    10    14    16    17
....  ~..~  #..#  ~~~~  ####  ~..~  #..#  ....
....  ~..~  #..#  ~~~~  ####  ~..~  #..#  ....
....  ~..~  #..#  ~~~~  ####  ~..~  #..#  ....
....  ~..~  #..#  ~~~~  ####  ~..~  #..#  ....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| east | 8 | 4 | 4×8 | east 2 (8) |
| west | 8 | 4 | 4×8 | west 2 (8) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -5 5 -2 S | east | door | 5+12→pulled | redstone_block (QC) 1 |
| -5 6 -2 S | east | door | 5+12→pulled | redstone_block 1 |
| -4 4 -2 S | east | door | 8+6→pulled | redstone_block 1 |
| -4 7 -2 S | east | door | 8+6→pulled | redstone_block (QC) 1 |
| 3 4 -2 S | west | door | 8+6→pulled | redstone_block 1 |
| 3 7 -2 S | west | door | 8+6→pulled | redstone_block (QC) 1 |
| 4 5 -2 S | west | door | 5+12→pulled | redstone_block (QC) 1 |
| 4 6 -2 S | west | door | 5+12→pulled | redstone_block 1 |
| -5 8 -2 | east | fires, moves nothing | 2+12→retracted | block←wire (QC) 1 |
| -5 9 -2 | up | fires, moves nothing | 2+12→retracted | block←wire 1 |
| 4 8 -2 | west | fires, moves nothing | 2+12→retracted | block←wire (QC) 1 |
| 4 9 -2 | up | fires, moves nothing | 2+12→retracted | block←wire 1 |
| -10 1 -2 S | up | helper | 2+15→pulled | block←wire 1 |
| -5 5 -1 | east | helper | 5+12→retracted | wire (QC) 1 |
| -5 6 -1 | east | helper | 5+12→retracted | wire 1 |
| -4 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| -4 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| -3 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| -3 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| -2 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| -2 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| -1 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire (QC) 1 |
| -1 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire (QC) 1 |
| 0 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire (QC) 1 |
| 0 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire (QC) 1 |
| 1 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| 1 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| 2 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| 2 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| 3 1 -2 S | up | helper | pulled at 2, 17+None→held | block←wire 1 |
| 3 10 -2 S | down | helper | pulled at 2, 17+None→held | block←wire 1 |
| 4 5 -1 | west | helper | 5+12→retracted | wire (QC) 1 |
| 4 6 -1 | west | helper | 5+12→retracted | wire 1 |
| 9 1 -2 S | up | helper | 2+15→pulled | block←wire 1 |
| -9 1 -3 S | south | power mover | pulled at 2, 17+None→held | block←wire 1 |
| -9 5 -3 S | east | power mover | 5+0→spat, 11+6→pulled | block←wire 2 |
| -8 2 -2 S | east | power mover | 2+12→pulled | redstone_block (QC) 1 |
| -8 9 -3 S | east | power mover | 5+12→pulled | wire 1 |
| -8 10 -3 S | west | power mover | pulled at 2, 17+None→held | block←repeater (QC) 1 |
| -7 6 -3 S | east | power mover | 5+0→spat, 11+6→pulled | redstone_block 2 |
| -6 3 -2 S | east | power mover | 5+9→pulled | redstone_block 1 |
| -6 3 -1 S | west | power mover | 2+0→spat, 8+6→pulled | block←wire 2 |
| -5 5 -3 S | west | power mover | pulled at 5, 8+9→retracted, 20+None→held | redstone_block 1, redstone_block (QC) 1 |
| -4 10 -1 S | down | power mover | 2+12→pulled | wire 1 |
| 3 10 -1 S | down | power mover | 2+12→pulled | wire 1 |
| 4 5 -3 S | east | power mover | pulled at 5, 8+9→retracted, 20+None→held | redstone_block 1, redstone_block (QC) 1 |
| 5 3 -2 S | west | power mover | 5+9→pulled | redstone_block 1 |
| 5 3 -1 S | east | power mover | 2+0→spat, 8+6→pulled | block←wire 2 |
| 6 6 -3 S | west | power mover | 5+0→spat, 11+6→pulled | redstone_block 2 |
| 7 2 -2 S | west | power mover | 2+12→pulled | redstone_block (QC) 1 |
| 7 9 -3 S | west | power mover | 5+12→pulled | wire 1 |
| 7 10 -3 S | east | power mover | pulled at 2, 17+None→held | block←repeater (QC) 1 |
| 8 1 -3 S | south | power mover | pulled at 2, 17+None→held | block←wire 1 |
| 8 5 -3 S | west | power mover | 5+0→spat, 11+6→pulled | block←wire 2 |
| -8 2 -1 S | east | power switch | pulled at 2, 5+9→pulled, 17+None→held | redstone_block 1, redstone_block (QC) 1 |
| -8 11 -1 S | north | power switch | 2+12→pulled | wire 1 |
| -7 4 -3 S | west | power switch | pulled at 5, 8+9→pulled, 20+None→held | block←comparator (QC) 1, redstone_block (QC) 1 |
| -7 7 -2 S | down | power switch | 5+12→pulled | block←wire 1 |
| 6 4 -3 S | east | power switch | pulled at 5, 8+9→pulled, 20+None→held | block←comparator (QC) 1, redstone_block (QC) 1 |
| 6 7 -2 S | down | power switch | 5+12→pulled | block←wire 1 |
| 7 2 -1 S | west | power switch | pulled at 2, 5+9→pulled, 17+None→held | redstone_block 1, redstone_block (QC) 1 |
| 7 11 -1 S | north | power switch | 2+12→pulled | wire 1 |
| -6 4 -2 S | east | stack | 8+9→pulled | block←comparator (QC) 1 |
| -6 7 -2 S | east | stack | 8+9→pulled | wire (QC) 1 |
| 5 4 -2 S | west | stack | 8+9→pulled | block←comparator (QC) 1 |
| 5 7 -2 S | west | stack | 8+9→pulled | wire (QC) 1 |

<!-- end generated -->
