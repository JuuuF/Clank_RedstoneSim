# Seamless Glass Door by Nile

World: `piston_doors/3x3 Seamless Glass Door by Nile` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane z = -3; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 46; markers Opening 1, Opened 45, Closing 46, Closed 83
- Reference states: closed at tick 83, open at tick 45. Fully closed at ticks 0-9, 12-13, 16-17, 20, 23, 73-76, 79-116; fully open at 40-53.
- Pistons by role: door 30, fires, moves nothing 9, helper 2, idle 3, power mover 9, stack 3
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 57, block←wire (QC) 23, observer 6, redstone_block (QC) 6, target (QC) 5, target 5, observer (QC) 4, repeater 3, block←observer 2, block←repeater (QC) 1, block←observer+wire 1, block←observer (QC) 1, bud 1, block←lever (QC) 1, block←lever 1
- Phases (bursts of piston events): 1–2 (3 events, 2 pistons); 6–42 (126 events, 27 pistons); 47–47 (2 events, 2 pistons); 51–80 (166 events, 24 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0   10   12   14   16   18   20   21   23   24   26   28   31   32
###  ~~~  ###  ~~~  ###  ~~~  ###  ###  ###  ~~~  ###  ...  ~~~  ~~~
###  ~~~  ###  ~~~  ###  ~~~  ###  ~~~  ###  ~~~  ###  ###  ###  ...
###  ~~~  ###  ~~~  ###  ~~~  ###  ~~~  ###  ...  ...  ...  ...  ...

 34   40   54   56   62   64   71   73   77   79
###  ...  ...  ...  ...  ...  ~~~  ###  ~~~  ###
...  ...  ...  ...  ~~~  ###  ~~~  ###  ~~~  ###
...  ...  ~~~  ###  ~~~  ###  ~~~  ###  ~~~  ###

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 12 | 24 | 8×12 | down 4 (12) |
| above | 6 | 21 | 6×3, 8×3 | down 1 (6) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 0 1 -3 | up | door | 54+0→spat | block←wire 1 |
| 0 2 -3 | up | door | 62+3→retracted, retracted at 65, 68+None→held | block←wire 2 |
| 0 3 -3 S | down | door | 59+0→pulled, 71+0→spat, 74+None→held | block←wire 4 |
| 0 4 -3 | up | door | 68+0→pulled, 77+0→spat | block←wire 3 |
| 0 10 -3 S | down | door | 21+3→pulled | block←wire (QC) 1 |
| 0 11 -3 S | down | door | 31+1→pulled | block←wire 1 |
| 0 12 -3 S | down | door | 18+2→spat, 26+2→pulled, 39+1→pulled | block←wire (QC) 3 |
| 0 13 -3 S | down | door | 35+1→pulled, 39+None→held | block←wire 2 |
| 0 14 -3 S | down | door | 14+2→spat, 30+2→pulled | block←wire (QC) 2 |
| 0 16 -3 | down | door | 10+2→spat | observer 1 |
| 1 1 -3 | up | door | 54+0→spat, 59+None→held | block←wire 1, block←wire (QC) 1 |
| 1 2 -3 | up | door | 62+3→retracted, retracted at 65, 68+None→held | block←wire 2 |
| 1 3 -3 S | down | door | 59+0→pulled, 71+0→spat, 74+None→held | block←wire 4 |
| 1 4 -3 | up | door | 68+0→pulled, 77+0→spat | block←wire 3 |
| 1 10 -3 S | down | door | 21+3→pulled | block←wire (QC) 1 |
| 1 11 -3 S | down | door | 31+1→pulled | block←wire 1 |
| 1 12 -3 S | down | door | 18+2→spat, 26+2→pulled, 39+1→pulled | block←wire (QC) 3 |
| 1 13 -3 S | down | door | 35+1→pulled, 39+None→held | block←wire 2 |
| 1 14 -3 S | down | door | 14+2→spat, 30+2→pulled | block←wire (QC) 2 |
| 1 16 -3 | down | door | 10+2→spat, 18+2→spat | observer 2 |
| 2 1 -3 | up | door | 54+0→spat, 59+None→held | block←wire 1, block←wire (QC) 1 |
| 2 2 -3 | up | door | 62+3→retracted, retracted at 65, 68+None→held | block←wire 2 |
| 2 3 -3 S | down | door | 59+0→pulled, 71+0→spat, 74+None→held | block←wire 4 |
| 2 4 -3 | up | door | 68+0→pulled, 77+0→spat | block←wire (QC) 3 |
| 2 10 -3 S | down | door | 21+3→pulled | block←wire (QC) 1 |
| 2 11 -3 S | down | door | 31+1→pulled | block←wire 1 |
| 2 12 -3 S | down | door | 18+2→spat, 26+2→pulled, 39+1→pulled | block←wire (QC) 3 |
| 2 13 -3 S | down | door | 35+1→pulled, 39+None→held | block←wire 2 |
| 2 14 -3 S | down | door | 14+2→spat, 30+2→pulled | block←wire (QC) 2 |
| 2 16 -3 | down | door | 10+2→spat, 18+2→spat | observer 2 |
| -2 13 -4 | east | fires, moves nothing | 28+2→spat | block←repeater (QC) 1 |
| -1 13 -3 | down | fires, moves nothing | 18+2→spat, 26+4→retracted, 34+2→spat, 39+1→spat | block←wire 4 |
| -1 15 -3 | down | fires, moves nothing | 14+2→spat, 30+2→spat | block←wire 2 |
| 0 15 -3 S | down | fires, moves nothing |  | observer (QC) 1 |
| 1 15 -3 S | down | fires, moves nothing |  | observer (QC) 1 |
| 2 1 -2 | east | fires, moves nothing | 59+0→spat, 62+0→spat, 65+0→spat, 68+0→spat, 71+0→spat, 74+0→spat, 77+0→spat | block←wire 7 |
| 2 15 -3 S | down | fires, moves nothing |  | observer (QC) 1 |
| 4 7 -2 | up | fires, moves nothing | 56+0→spat, 62+0→spat, 68+0→spat, 74+0→spat, 80+0→spat | target 5 |
| 5 1 -3 | north | fires, moves nothing | 54+0→spat | block←wire 1 |
| 1 12 -4 S | west | helper | 26+2→spat | observer 1 |
| 3 7 -2 S | down | helper | 55+2→pulled, 75+2→spat | block←observer (QC) 1, bud 1 |
| -1 16 -4 | east | power mover | 14+2→spat, 20+6→retracted, 30+2→spat, 36+6→retracted | block←wire 1, repeater 2, block←observer+wire 1 |
| 3 2 -3 S | up | power mover | 61+8→pulled | repeater 1 |
| 4 1 -2 | up | power mover | 53+1→spat, 59+0→spat, 65+0→spat, 71+0→spat, 77+0→spat | redstone_block (QC) 5 |
| 4 6 -2 | down | power mover | 56+0→spat, 62+0→spat, 68+0→spat, 74+0→spat, 80+0→spat | target (QC) 5 |
| 4 16 -4 | west | power mover | 6+2→spat | block←observer 1 |
| 5 1 -2 S | up | power mover | 54+0→spat, 58+2→pulled | redstone_block (QC) 1, observer (QC) 1 |
| 5 13 -2 | down | power mover | 51+2→spat | block←observer 1 |
| 5 14 -2 S | north | power mover | 2+45→pulled | block←lever (QC) 1 |
| 5 15 -2 S | north | power mover | 2+45→pulled | block←lever 1 |
| 0 5 -3 S | down | stack | 74+0→pulled | block←wire 2 |
| 1 5 -3 S | down | stack | 74+0→pulled | block←wire 2 |
| 2 5 -3 S | down | stack | 74+0→pulled | block←wire 2 |

<!-- end generated -->
