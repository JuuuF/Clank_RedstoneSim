# 1 Wide Hidden Staircase by Purplers

World: `other_piston_contraptions/1 Wide Hidden Staircase by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 4×4 in the plane x = 0; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 28; markers Closing 1, Closed 27, Opening 28, Opened 56
- Reference states: closed at tick 27, open at tick 56. Fully closed at ticks 26-35; fully open at never.
- Pistons by role: door 12, idle 2, stack 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←wire 5, block←repeater 2, block←repeater+wire 2, wire 2, block←torch 1, block←wire (QC) 1, torch 1
- Phases (bursts of piston events): 3–5 (4 events, 4 pistons); 9–16 (7 events, 7 pistons); 21–24 (3 events, 3 pistons); 36–44 (6 events, 6 pistons); 48–53 (8 events, 8 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
   0     5    12    13    14    15    16    18    24    26    36    38
#...  ....  ~...  ~...  #...  #...  #~~.  ###.  ###~  ####  ##.#  .#.#
 #     #     #     ~     ~     #     ~     #     #     #     #     #
  #     #     #     ~     ~     #     #     #     #     #     ~     #
   #     #     #     #     #     #     #     #     #     #     #     #

  42    44    50    52    53    55
...#  ....  ....  ....  ~...  #...
 ~     #     ~     #     #     #
  #     #     ~     #     #     #
   #     #     #     #     #     #

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| recess | 5 | 12 | 2×1, 4×4 | down 1, east 1 (4), east 1 (1) |
| stays in the doorway | 3 | 7 | 2×2, 4×1 | up 1, east 1 (1), east 1 (2) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -2 2 -1 | east | door | retracted at 3, 50+None→held | block←wire 1 |
| -2 3 -3 | east | door | retracted at 3, 50+None→held | block←torch 1 |
| -2 3 -2 | east | door | retracted at 3, 50+None→held | block←wire 1 |
| 0 2 -3 S | up | door | pulled at 5, 12+26→pulled, 53+None→held | block←repeater 2 |
| 0 2 -2 S | up | door | 16+26→pulled | block←repeater+wire 1 |
| 0 2 -1 S | up | door | 16+20→pulled | block←wire 1 |
| 0 2 0 S | up | door | 24+20→pulled | block←wire 1 |
| 2 2 -1 | west | door | 13+35→retracted | block←wire (QC) 1 |
| 2 3 -3 | west | door | 9+31→retracted | torch 1 |
| 2 3 -2 | west | door | 13+27→retracted | wire 1 |
| 2 3 -1 S | west | door | 13+35→pulled | block←wire 1 |
| 2 3 0 S | west | door | 21+27→pulled | wire 1 |
| 2 2 0 S | west | stack | 21+27→pulled | block←repeater+wire 1 |

<!-- end generated -->
