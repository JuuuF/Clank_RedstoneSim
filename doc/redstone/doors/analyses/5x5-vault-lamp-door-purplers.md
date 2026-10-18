# vault lamp door by Purplers

World: `piston_doors/5x5 vault lamp door by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 5×5 in the plane x = 2; 17 more output cells outside it.
- Timeline: use lever at 1, use lever at 14; markers Closing 1, Closed 13, Opening 14, Opened 40
- Reference states: closed at tick 13, open at tick 40. Fully closed at ticks 8-15; fully open at 0-2, 16-41.
- Pistons by role: door 44, helper 5, power mover 4, power switch 2, stack 2
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 35, block←wire (QC) 8, wire (QC) 5, torch 5, repeater 3, block←torch 2, block←repeater (QC) 2, block←repeater 2, block←repeater+wire 2, redstone_block 2, block←torch+wire 2, repeater (QC) 1, torch (QC) 1
- Phases (bursts of piston events): 3–10 (55 events, 51 pistons); 16–32 (94 events, 56 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
    0      3      5      6      8     16
  .      ~      #      #      #      .
 . .    . .    . .    ~ ~    # #    . .
.   .  ~   ~  #   #  #   #  #   #  .   .
 . .    . .    . .    ~ ~    # #    . .
  .      ~      #      #      #      .

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| south | 7 | 13 | 2×4, 4×3 | south 2 (3), south 1 (4) |
| north | 7 | 13 | 2×4, 4×3 | north 1 (4), north 2 (3) |
| above | 7 | 12 | 2×5, 4×1, 6×1 | up 2 (1), up 1 (5), up 3 (1) |
| below | 4 | 6 | 2×3, 4×1 | down 2 (1), down 1 (3) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 0 8 -1 S | down | door | 9+7→pulled | block←wire (QC) 1 |
| 0 9 -1 S | down | door | 23+1→pulled | block←wire 2 |
| 0 10 -1 S | down | door | 6+14→pulled, 31+1→pulled | repeater (QC) 1, block←repeater 1 |
| 0 12 -1 S | down | door | 3+13→retracted, 22+2→pulled | block←wire 2 |
| 1 1 -1 S | up | door | 3+17→pulled, 23+None→held | torch (QC) 1, block←repeater (QC) 1 |
| 1 2 -1 S | up | door | 23+1→pulled | torch 1, block←repeater 1 |
| 1 3 -1 S | up | door | 6+10→pulled | block←torch 1 |
| 1 6 -6 S | south | door | 3+17→pulled | block←wire 1 |
| 1 6 -5 S | south | door | 23+1→pulled | wire (QC) 1 |
| 1 6 -4 S | south | door | 6+10→pulled | block←wire (QC) 1 |
| 1 6 2 S | north | door | 6+10→pulled | redstone_block 1 |
| 1 6 3 S | north | door | 23+1→pulled | wire (QC) 1 |
| 1 6 4 S | north | door | 3+17→pulled | block←wire 1 |
| 1 9 -1 S | down | door | 6+10→pulled | block←wire 1 |
| 1 10 -1 S | down | door | 23+1→pulled | block←wire 1 |
| 1 11 -1 S | down | door | 3+17→pulled | block←wire 1 |
| 2 2 -1 S | up | door | 3+13→pulled | torch 1 |
| 2 5 -6 S | south | door | 3+17→pulled | block←wire 1 |
| 2 5 -5 S | south | door | 23+1→pulled | block←wire (QC) 1, repeater 1 |
| 2 5 -4 S | south | door | 6+10→pulled | block←wire 1 |
| 2 5 2 S | north | door | 6+10→pulled | block←wire 1 |
| 2 5 3 S | north | door | 23+1→pulled | block←wire (QC) 1, repeater 1 |
| 2 5 4 S | north | door | 3+17→pulled | block←wire 1 |
| 2 6 -5 S | south | door | 3+13→pulled | block←wire 1 |
| 2 6 3 S | north | door | 3+13→pulled | block←wire 1 |
| 2 7 -6 S | south | door | 3+17→pulled | block←wire 1 |
| 2 7 -5 S | south | door | 23+1→pulled | block←wire (QC) 1, wire (QC) 1 |
| 2 7 -4 S | south | door | 6+10→pulled | block←wire 1 |
| 2 7 2 S | north | door | 6+10→pulled | block←wire 1 |
| 2 7 3 S | north | door | 23+1→pulled | wire (QC) 1 |
| 2 7 4 S | north | door | 3+17→pulled | block←wire 1 |
| 2 10 -1 S | down | door | 3+13→pulled | block←wire 1 |
| 3 2 -2 S | up | door | 3+13→pulled | torch 1 |
| 3 2 0 S | up | door | 3+13→pulled | torch 1 |
| 3 5 -5 S | south | door | 3+13→pulled | block←wire 1 |
| 3 5 3 S | north | door | 3+13→pulled | block←wire 1 |
| 3 7 -5 S | south | door | 3+13→pulled | block←wire 1 |
| 3 7 3 S | north | door | 3+13→pulled | block←wire 1 |
| 3 10 -2 S | down | door | 3+13→pulled | block←wire 1 |
| 3 10 0 S | down | door | 3+13→pulled | block←wire (QC) 1 |
| 4 4 -5 S | south | door | 3+13→pulled | block←torch+wire 1 |
| 4 4 3 S | north | door | 3+13→pulled | block←torch+wire 1 |
| 4 10 -3 S | down | door | 3+13→pulled | block←wire 1 |
| 4 10 1 S | down | door | 3+13→pulled | block←wire 1 |
| 0 12 3 S | down | helper | 5+13→pulled, 22+2→spat | block←wire 2 |
| 1 1 -4 S | up | helper | pulled at 7, 20+None→held | block←wire 1 |
| 1 10 2 S | east | helper | 5+17→retracted, pulled at 24 | block←wire 1 |
| 1 12 -6 S | down | helper | 5+15→pulled, 26+2→spat | block←repeater+wire 2 |
| 3 11 0 S | west | helper | 3+13→pulled | block←wire 1 |
| 0 6 -6 S | south | power mover | pulled at 5, 18+None→held | block←torch 1 |
| 0 6 2 S | north | power mover | 10+6→pulled | block←wire (QC) 1 |
| 0 6 3 S | north | power mover | 23+1→pulled | wire (QC) 1 |
| 4 11 4 S | west | power mover | 3+0→spat, 9+7→pulled | block←wire 2 |
| 0 9 4 S | down | power switch | 7+13→pulled | block←wire 1 |
| 2 10 4 S | east | power switch | pulled at 3, 6+None→held | redstone_block 1 |
| 0 6 4 S | north | stack | 7+13→pulled, 23+None→held | torch 1, block←repeater (QC) 1 |
| 0 11 -1 S | down | stack | 27+1→pulled | block←wire (QC) 1, repeater 1 |

<!-- end generated -->
