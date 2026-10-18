# Vault Door by Nile

World: `piston_doors/5x5 Vault Door by Nile [broken sim].redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 5×5 in the plane z = -3; 9 more output cells outside it.
- Timeline: use lever at 1, use lever at 18; markers Closing 1, Closed 17, Opening 18, Opened 34
- Reference states: closed at tick 17, open at tick 34. Fully closed at ticks 10-18; fully open at 0-6, 27-36.
- Pistons by role: door 29, fires, moves nothing 10, helper 13, idle 3, power mover 16, power switch 3
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 19, wire 17, target 15, wire (QC) 14, observer 12, block←wire (QC) 8, block←observer (QC) 8, target (QC) 7, block←observer 7, redstone_block (QC) 6, observer (QC) 5, redstone_block 4, block←repeater 3, block←comparator (QC) 2, bud 2
- Phases (bursts of piston events): 2–15 (160 events, 69 pistons); 19–31 (179 events, 71 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
    0      7      8      9     10     19     26     27
.....  ....~  ~~~~~  ~~~~#  #####  #####  ####.  .....
.   .  .   ~  ~   ~  ~   #  #   #  #   #  #   .  .   .
.   .  .   ~  ~   ~  ~   #  #   #  #   #  #   .  .   .
.   .  .   ~  ~   ~  ~   #  #   #  #   #  #   .  .   .
.....  ....~  ~~~~~  ~~~~#  #####  #...#  #....  .....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| above | 7 | 9 | 2×3, 6×4 | up 3 (1), up 2 (3), up 1 (3) |
| west | 6 | 8 | 2×5, 4×1 | west 2 (1), west 1 (5) |
| east | 6 | 8 | 2×5, 4×1 | east 2 (1), east 1 (5) |
| below | 6 | 4 | 4×6 | down 2 (3), down 1 (3) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -5 7 -2 S | east | door | 5+17→pulled | target 1 |
| -4 4 -3 | east | door | 22+2→spat | block←observer 1 |
| -4 5 -3 S | east | door | 8+2→spat, 25+2→pulled | block←wire (QC) 2 |
| -4 6 -3 S | east | door | 8+2→spat, 25+2→pulled | block←wire 2 |
| -4 7 -3 S | east | door | 8+2→spat, 25+2→pulled | wire 2 |
| -4 7 -2 S | east | door | 25+1→pulled | wire (QC) 2 |
| -4 8 -3 S | east | door | 8+2→spat, 25+2→pulled | observer (QC) 2 |
| -4 9 -3 S | east | door | 8+2→spat, 25+2→pulled | observer 2 |
| -3 7 -2 S | east | door | 8+11→pulled | block←wire 1 |
| -1 11 -3 S | down | door | 8+2→spat, 25+2→pulled | wire (QC) 2 |
| -1 11 -1 S | down | door | 5+14→retracted, 22+1→pulled | block←wire 2 |
| -1 12 -2 | down | door | 13+2→spat, 29+2→spat | wire (QC) 2 |
| 0 2 -2 S | up | door | 5+17→pulled | target 1 |
| 0 11 -3 S | down | door | 8+2→spat, 25+2→pulled | wire 2 |
| 0 12 -2 | down | door | 13+2→spat, 29+2→spat | wire 2 |
| 0 12 -1 S | down | door | 2+17→retracted, 24+2→pulled | block←wire 1, observer (QC) 1 |
| 1 3 -2 S | up | door | 8+11→pulled | block←wire 1 |
| 1 10 -1 S | down | door | 8+11→pulled | redstone_block (QC) 1 |
| 1 11 -3 S | down | door | 8+2→spat, 25+2→pulled | wire (QC) 2 |
| 1 12 -2 | down | door | 13+2→spat, 29+2→spat | wire (QC) 2 |
| 3 7 -2 S | west | door | 8+11→pulled | block←wire 1 |
| 4 4 -3 | west | door | 10+4→retracted, 25+4→retracted | block←repeater 2 |
| 4 5 -3 S | west | door | 7+2→spat, 24+2→pulled | block←observer (QC) 2 |
| 4 6 -3 S | west | door | 7+2→spat, 24+2→pulled | block←observer 2 |
| 4 7 -3 S | west | door | 7+2→spat, 24+2→pulled | wire 2 |
| 4 7 -2 S | west | door | 25+1→pulled | block←observer 1 |
| 4 8 -3 S | west | door | 7+2→spat, 24+2→pulled | observer (QC) 2 |
| 4 9 -3 S | west | door | 7+2→spat, 24+2→pulled | observer 2 |
| 5 7 -2 S | west | door | 5+17→pulled | target 1 |
| -6 12 -3 | east | fires, moves nothing | 4+10→retracted, 21+10→retracted | observer 2 |
| -5 1 -1 | up | fires, moves nothing | 5+14→retracted | block←wire 1 |
| -5 10 -2 | south | fires, moves nothing | retracted at 2, 5+14→retracted, 22+None→held | redstone_block (QC) 2 |
| -5 14 -3 | west | fires, moves nothing | 2+0→spat, 19+0→spat | target 2 |
| -3 11 -3 | west | fires, moves nothing | 8+2→spat, 25+2→spat | observer 2 |
| 4 11 -1 | south | fires, moves nothing | 5+14→retracted | wire 1, target (QC) 1 |
| 5 9 -1 | down | fires, moves nothing | 2+0→spat, 10+2→spat, 19+0→spat, 25+2→spat | block←wire 2, block←observer (QC) 2 |
| 5 14 -2 | south | fires, moves nothing | retracted at 2, 5+14→retracted, 22+None→held | target 2 |
| 6 11 0 | down | fires, moves nothing | 2+0→spat, 19+0→spat | target 2 |
| 7 11 -2 | down | fires, moves nothing | 2+0→spat, 19+0→spat | wire (QC) 2 |
| -7 9 -1 S | east | helper | 2+17→pulled | block←comparator (QC) 1 |
| -6 2 -1 S | north | helper | 5+14→pulled | block←wire 1 |
| -4 4 -1 | east | helper | 7+2→spat, 21+2→spat | block←observer 2 |
| -4 9 0 S | down | helper | 2+17→pulled | wire 1 |
| -4 10 -1 S | east | helper | 2+0→pulled, 10+2→spat, 19+0→pulled, 27+2→spat | block←wire (QC) 2, bud 2 |
| -4 10 0 | east | helper | 4+2→spat, 21+2→spat | block←observer (QC) 2 |
| -2 2 -2 S | up | helper | pulled at 5, 25+None→held | target 1 |
| 2 2 -2 S | up | helper | pulled at 5, 25+None→held | redstone_block 1 |
| 4 4 -1 | west | helper | 10+5→retracted, 25+4→retracted | block←repeater 1, target 1 |
| 4 9 0 S | down | helper | 2+17→pulled, 22+1→spat, 26+1→pulled | wire 3 |
| 4 10 -1 S | west | helper | 2+0→pulled, 10+2→spat, 19+0→pulled, 27+2→spat | block←wire 2, observer 2 |
| 4 10 0 | west | helper | 8+11→retracted, 25+2→spat | block←wire (QC) 1, block←observer 1 |
| 7 11 -1 S | down | helper | 2+0→spat, 19+0→pulled | wire 2 |
| -7 7 0 S | down | power mover | 2+17→pulled | block←wire 1 |
| -5 10 -3 S | up | power mover | 2+0→spat, 19+0→spat | wire (QC) 2 |
| -5 13 -3 S | down | power mover | 2+0→spat, 19+0→spat | target (QC) 2 |
| -4 3 0 S | east | power mover | 5+0→spat, 11+8→pulled | target 2 |
| -4 12 0 S | east | power mover | 2+0→spat, 19+0→pulled | block←wire 2 |
| -2 2 0 S | west | power mover | pulled at 5, 8+11→pulled, 22+None→held | redstone_block 1, redstone_block (QC) 1 |
| 0 3 0 S | east | power mover | 5+14→pulled | wire 1 |
| 0 14 -2 S | east | power mover | 2+0→spat, 19+0→pulled | target 2 |
| 1 2 -3 S | west | power mover | pulled at 5, 22+None→held | redstone_block 1 |
| 2 1 -3 S | west | power mover | 5+14→pulled | block←wire (QC) 1 |
| 3 11 0 S | west | power mover | 5+14→pulled | block←comparator (QC) 1 |
| 5 2 -2 S | west | power mover | pulled at 5, 22+None→held | redstone_block 1 |
| 5 9 -2 | up | power mover | 2+0→spat, 5+1→spat, 19+0→spat, 22+1→spat | redstone_block (QC) 2, block←observer (QC) 2 |
| 5 13 -2 S | down | power mover | 2+0→spat, 19+0→spat, 22+None→held | target (QC) 4 |
| 6 1 -2 S | west | power mover | 5+14→pulled | block←wire (QC) 1 |
| 7 6 0 S | down | power mover | 2+17→pulled | block←wire (QC) 1 |
| -7 4 -3 S | east | power switch | 12+2→spat, 27+2→pulled | observer 2 |
| -7 12 0 S | down | power switch | 2+0→spat, 19+0→pulled | block←wire 2 |
| 1 13 0 S | east | power switch | 2+17→pulled | wire 1 |

<!-- end generated -->
