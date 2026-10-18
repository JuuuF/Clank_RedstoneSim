# Piston Door by LegDen

World: `piston_doors/8x8 Piston Door by LegDen [broken sim].redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 8×8 in the plane z = -3; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 34; markers Closing 1, Closed 31, Opening 34, Opened 73
- Reference states: closed at tick 31, open at tick 73. Fully closed at ticks 22-34; fully open at 0-1.
- Pistons by role: door 63, fires, moves nothing 61, helper 34, idle 66, power mover 96, power switch 8, stack 89
- How extensions were powered (block giving the signal; QC = through the block above the piston): observer 118, block←observer 96, target 86, wire 84, wire (QC) 76, observer (QC) 60, target (QC) 59, block←wire (QC) 55, block←observer (QC) 53, block←wire 50, redstone_block (QC) 33, redstone_block 28, bud 13, repeater 13, block←repeater (QC) 12, repeater (QC) 10, block←repeater 9, block←comparator (QC) 8, block←comparator 7, bud (QC) 5, comparator 4, comparator (QC) 3, lamp (QC) 1, dropper 1, torch 1
- Phases (bursts of piston events): 2–26 (712 events, 231 pistons); 35–71 (1718 events, 329 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
       0         2         4         5         7         8        10
........  ########  ########  ########  ########  ########  ########
........  ~.......  #.......  ~~......  ##......  ~~~.....  ###.....
........  ~.......  #.......  ~~......  ##......  ~~~.....  ###.....
........  ~.......  #.......  ~~......  ##......  ~~~.....  ###.....
........  ~.......  #.......  ~~......  ##......  ~~~.....  ###.....
........  ~.......  #.......  ~~......  ##......  ~~~.....  ###.....
........  ~.......  #.......  ~~......  ##......  ~~~.....  ###.....
........  ########  ########  ########  ########  ########  ########

      11        13        14        16        17        19        20
########  ########  ########  ########  ########  ########  ########
~~~~....  ####....  ~~~~~...  #####...  ~~~~~~..  ######..  #~~~~~~~
~~~~....  ####....  ~~~~~...  #####...  ~~~~~~..  ######..  #~~~~~~~
~~~~....  ####....  ~~~~~...  #####...  ~~~~~~..  ######..  #~~~~~~~
~~~~....  ####....  ~~~~~...  #####...  ~~~~~~..  ######..  #~~~~~~~
~~~~....  ####....  ~~~~~...  #####...  ~~~~~~..  ######..  #~~~~~~~
~~~~....  ####....  ~~~~~...  #####...  ~~~~~~..  ######..  #~~~~~~~
########  ########  ########  ########  ########  ########  ########

      22        35        37        38        40        53        55
########  ........  ........  ........  ........  ........  ........
########  ~~~~~~~~  ########  ~~~~~~~~  ########  #####.~~  ~~~~~~##
########  ~~~~~~~~  ########  ~~~~~~~~  ########  #####.~~  #####.##
########  ~~~~~~~~  ########  ~~~~~~~~  ########  #####.~~  #####.##
########  ~~~~~~~~  ########  ~~~~~~~~  ########  #####.~~  #####.##
########  ~~~~~~~~  ########  ~~~~~~~~  ########  #####.~~  #####.##
########  ~~~~~~~~  ########  ~~~~~~~~  ########  #####.~~  #####.##
########  ........  ........  ........  ........  ........  ........

      56        57        58        59
........  ........  ........  ........
~~~~~~.~  ######.~  ######.#  ######..
#####..~  #####..~  #####..#  #####...
#####..~  #####..~  #####..#  #####...
#####..~  #####..~  #####..#  #####...
#####..~  #####..~  #####..#  #####...
#####..~  #####..~  #####..#  #####...
........  ........  ........  ........

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| stays in the doorway | 31 | 38 | 9×25, 10×5, 11×1 | west 2 (25), west 1 (5), up 1, west 1 (1) |
| east | 18 | 18 | 6×18 | east 1 (18) |
| west | 11 | 41 | 11×10, 12×1 | west 2 (10), west 1 (1) |
| below | 8 | 8 | 2×8 | down 1 (8) |
| above | 8 | 8 | 2×8 | up 1 (8) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -11 6 -3 S | east | door | 2+0→spat, 5+3→pulled, 11+24→pulled | block←wire (QC) 3 |
| -11 7 -3 S | east | door | 2+0→spat, 5+3→pulled, 11+24→pulled | block←wire 3 |
| -11 8 -3 S | east | door | 2+0→spat, 5+3→pulled, 11+24→pulled | block←wire (QC) 3 |
| -11 9 -3 S | east | door | 2+0→spat, 5+3→pulled, 11+24→pulled | block←wire 3 |
| -11 10 -3 S | east | door | 2+0→spat, 5+3→pulled, 11+24→pulled | block←wire (QC) 3 |
| -11 11 -3 S | east | door | 2+0→spat, 5+3→pulled, 11+24→pulled | block←wire 3 |
| -8 6 -3 S | east | door | 8+0→spat, 14+6→retracted, 44+0→pulled | wire (QC) 3 |
| -8 7 -3 S | east | door | 8+0→spat, 14+6→retracted, 44+0→pulled | wire 3 |
| -8 8 -3 S | east | door | 8+0→spat, 14+6→retracted, 44+0→pulled | wire (QC) 3 |
| -8 9 -3 S | east | door | 8+0→spat, 14+6→retracted, 44+0→pulled | wire 3 |
| -8 10 -3 S | east | door | 8+0→spat, 14+6→retracted, 44+0→pulled | wire (QC) 3 |
| -8 11 -3 S | east | door | 8+0→spat, 14+6→retracted, 44+0→pulled | wire 3 |
| -7 11 -3 S | east | door | 55+2→spat | observer (QC) 1 |
| -6 6 -3 S | east | door | 17+0→spat, 23+12→pulled | observer (QC) 1, block←wire (QC) 1 |
| -6 7 -3 S | east | door | 17+0→spat, 23+12→pulled | observer 1, block←wire 1 |
| -6 8 -3 S | east | door | 17+0→spat, 23+12→pulled | observer (QC) 1, block←wire (QC) 1 |
| -6 9 -3 S | east | door | 17+0→spat, 23+12→pulled | observer 1, block←wire 1 |
| -6 10 -3 S | east | door | 17+0→spat, 23+12→pulled | observer (QC) 1, block←wire (QC) 1 |
| -6 11 -3 S | east | door | 17+0→spat, 23+12→pulled | observer 1, block←wire 1 |
| -4 3 -3 | up | door | 50+2→spat | observer 1 |
| -4 6 -3 S | east | door | 20+0→spat | observer 1 |
| -4 7 -3 S | east | door | 20+0→spat | observer (QC) 1 |
| -4 8 -3 S | east | door | 20+0→spat | observer 1 |
| -4 9 -3 S | east | door | 20+0→spat | observer (QC) 1 |
| -4 10 -3 S | east | door | 20+0→spat | observer 1 |
| -4 11 -3 S | east | door | 20+0→spat | observer (QC) 1 |
| -4 13 -3 | down | door | 6+2→spat, 14+2→retracted, retracted at 20, 39+2→spat, 44+1→spat, 59+2→spat | wire (QC) 5 |
| -3 3 -3 | up | door | 50+2→spat | observer 1 |
| -3 14 -3 | down | door | 6+2→spat, 14+2→spat, 19+1→spat, 39+2→spat, 44+1→spat, 59+2→spat | wire 6 |
| -2 3 -3 S | up | door | 2+0→spat, 35+0→pulled | target 2 |
| -2 14 -3 S | down | door | 2+0→spat, 35+0→pulled | block←wire (QC) 2 |
| -1 3 -3 S | up | door | 2+0→spat, 35+0→pulled | target 2 |
| -1 14 -3 S | down | door | 2+0→spat, 35+0→pulled | block←wire 2 |
| 0 3 -3 S | up | door | 2+0→spat, 35+0→pulled | target 2 |
| 0 14 -3 S | down | door | 2+0→spat, 35+0→pulled | wire 2 |
| 1 3 -3 S | up | door | 2+0→spat, 35+0→pulled | target 2 |
| 1 14 -3 S | down | door | 2+0→spat, 35+0→pulled | wire 2 |
| 2 3 -3 S | up | door | 2+0→spat, 35+0→pulled | target 2 |
| 2 14 -3 S | down | door | 2+0→spat, 35+0→pulled | wire 2 |
| 3 3 -3 S | up | door | 2+0→spat, 35+0→pulled | target 2 |
| 3 14 -3 S | down | door | 2+0→spat, 35+0→pulled | wire 2 |
| 4 3 -3 S | up | door | 2+0→spat, 35+0→pulled | wire 2 |
| 4 14 -3 S | down | door | 2+0→spat, 35+0→pulled | wire 2 |
| 5 3 -3 S | up | door | 2+0→spat, 35+0→pulled | target 2 |
| 5 14 -3 S | down | door | 2+0→spat, 35+0→pulled | wire (QC) 2 |
| 9 6 -3 S | west | door | 38+0→spat, 53+0→pulled | block←observer (QC) 2 |
| 9 7 -3 S | west | door | 38+0→spat, 53+0→pulled | block←observer 2 |
| 9 8 -3 S | west | door | 38+0→spat, 53+0→pulled | block←observer (QC) 2 |
| 9 9 -3 S | west | door | 38+0→spat, 53+0→pulled | block←observer 2 |
| 9 10 -3 S | west | door | 38+0→spat, 53+0→pulled | block←observer (QC) 2 |
| 9 11 -3 S | west | door | 38+0→spat, 53+0→pulled | block←observer 2 |
| 10 6 -3 S | west | door | 35+0→spat, 56+0→pulled | wire 3 |
| 10 7 -3 S | west | door | 35+0→spat, 56+0→pulled | wire (QC) 3 |
| 10 8 -3 S | west | door | 35+0→spat, 56+0→pulled | wire 3 |
| 10 9 -3 S | west | door | 35+0→spat, 56+0→pulled | wire (QC) 3 |
| 10 10 -3 S | west | door | 35+0→spat, 56+0→pulled | wire 3 |
| 10 11 -3 S | west | door | 35+0→spat, 56+0→pulled | wire (QC) 3 |
| 11 6 -3 S | west | door | 20+0→spat, 59+0→pulled | block←observer (QC) 1, target 1 |
| 11 7 -3 S | west | door | 20+0→spat, 59+0→pulled | block←observer 1, target (QC) 1 |
| 11 8 -3 S | west | door | 20+0→spat, 59+0→pulled | block←observer (QC) 1, target 1 |
| 11 9 -3 S | west | door | 20+0→spat, 59+0→pulled | block←observer 1, target (QC) 1 |
| 11 10 -3 S | west | door | 20+0→spat, 59+0→pulled | block←observer (QC) 1, target 1 |
| 11 11 -3 S | west | door | 20+0→spat, 59+0→pulled | block←observer 1, target (QC) 1 |
| -11 2 0 | down | fires, moves nothing | retracted at 35, 38+0→spat, 41+0→spat, 44+0→spat, 47+12→retracted, 62+None→held | wire 5 |
| -11 4 0 | south | fires, moves nothing | 8+2→spat, 45+2→spat, 51+2→spat, 61+2→spat, 66+1→spat | observer 5 |
| -11 5 -1 | up | fires, moves nothing | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 47+3→retracted, 59+0→spat | block←wire 5, block←wire (QC) 2 |
| -11 14 -3 | up | fires, moves nothing | 2+33→retracted | block←wire 1 |
| -10 6 -6 | south | fires, moves nothing | 10+2→spat, 51+2→spat | block←observer 2 |
| -9 2 -4 | up | fires, moves nothing | retracted at 2, 38+None→held | wire 1, redstone_block 1 |
| -9 3 -6 | down | fires, moves nothing | 8+0→spat, 14+6→retracted, 44+0→spat | block←comparator (QC) 3 |
| -9 4 -6 | up | fires, moves nothing | 8+0→spat, 14+6→retracted, 44+0→spat | block←comparator 3 |
| -9 6 0 | up | fires, moves nothing | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 59+0→spat | wire 5 |
| -8 1 -5 | east | fires, moves nothing | 10+2→spat, 16+33→retracted | bud 1, comparator (QC) 1 |
| -8 1 1 | north | fires, moves nothing | 2+33→retracted, 49+2→spat | block←wire 1, observer 1 |
| -8 2 -4 | east | fires, moves nothing | 17+0→spat | block←observer (QC) 1 |
| -8 3 -4 | west | fires, moves nothing | 17+0→spat | block←observer 1 |
| -8 13 -2 | up | fires, moves nothing | retracted at 2, 5+None→held | redstone_block (QC) 1 |
| -7 2 -5 | down | fires, moves nothing | 9+0→spat, 56+None→held | block←observer 1, block←observer (QC) 1 |
| -7 13 -4 | west | fires, moves nothing | 4+2→spat, 9+2→spat, 50+2→spat | block←observer (QC) 2, bud 1 |
| -7 13 -2 | east | fires, moves nothing | 50+2→spat | block←wire (QC) 1 |
| -6 2 -2 | north | fires, moves nothing | 56+2→spat | target (QC) 1 |
| -6 3 -2 | up | fires, moves nothing | 56+2→spat, 61+None→held | target 1, target (QC) 1 |
| -6 11 -2 S | east | fires, moves nothing | 55+None→held | block←observer 1 |
| -6 15 1 | up | fires, moves nothing | 8+2→spat, 14+2→spat, 41+2→spat, 47+2→spat | block←observer 4 |
| -5 2 -6 | down | fires, moves nothing | 48+0→spat, 54+0→spat | block←repeater (QC) 3 |
| -5 3 -6 | east | fires, moves nothing | 6+2→spat, 23+12→retracted, 39+2→spat, 48+0→spat, 54+0→spat | observer (QC) 2, block←repeater 3 |
| -5 11 -3 S | east | fires, moves nothing |  | block←observer 1 |
| -4 1 -6 | west | fires, moves nothing | 18+17→retracted | block←repeater (QC) 1 |
| -3 1 -4 | west | fires, moves nothing | 21+2→spat, 53+0→spat | block←observer (QC) 2 |
| -3 2 -4 | east | fires, moves nothing | 21+2→spat, 53+0→spat | block←observer 2 |
| -3 2 0 | down | fires, moves nothing | 2+33→retracted, 38+0→spat, 44+0→spat, 53+0→spat, 59+0→spat | wire 1, target 4 |
| -3 3 -2 S | up | fires, moves nothing | retracted at 61 |  |
| -3 4 -4 | north | fires, moves nothing | 20+0→spat | block←observer 1 |
| -1 16 -4 | south | fires, moves nothing | 4+2→spat | observer 1 |
| 0 1 -4 | up | fires, moves nothing | 45+2→spat | block←observer 1 |
| 0 2 -3 | east | fires, moves nothing | 4+2→spat, 35+None→held | target (QC) 2, observer 1 |
| 1 15 0 | west | fires, moves nothing | 2+0→spat, 35+0→spat | target 2 |
| 2 3 -1 | down | fires, moves nothing | 4+4→retracted, 37+4→retracted | observer 2 |
| 2 15 1 | down | fires, moves nothing | 2+0→spat, 35+0→spat | target 2 |
| 4 2 -1 | east | fires, moves nothing | 2+0→spat, 35+0→spat | target 2 |
| 4 16 1 | down | fires, moves nothing | 6+2→spat, 14+2→spat, 39+2→spat, 45+2→spat | observer 4 |
| 5 16 -4 | north | fires, moves nothing | 4+2→spat | observer 1 |
| 6 2 -3 | down | fires, moves nothing | retracted at 35, 38+0→spat, 44+0→spat, 53+0→spat, 59+None→held | target 4 |
| 6 3 -6 | down | fires, moves nothing | 44+0→spat | redstone_block (QC) 1 |
| 7 1 -6 | east | fires, moves nothing | 4+2→spat, 16+2→spat, 21+1→spat, 37+2→spat, 49+2→spat, 54+1→spat, 59+2→spat | observer 7 |
| 7 3 -5 | west | fires, moves nothing | 5+2→spat, 19+2→spat, 38+2→spat, 44+0→spat, 52+2→spat, 58+2→spat | block←observer 5, redstone_block (QC) 1 |
| 7 5 -5 | down | fires, moves nothing | retracted at 41, 44+0→spat, 47+3→retracted, 53+0→spat, 56+None→held | redstone_block (QC) 2, redstone_block 2 |
| 8 2 0 | north | fires, moves nothing | 45+2→spat | observer (QC) 1 |
| 8 4 -5 | down | fires, moves nothing | 41+0→spat, 56+0→spat | redstone_block (QC) 2 |
| 8 7 0 | down | fires, moves nothing | 6+2→spat, 39+2→spat | observer 2 |
| 9 8 0 | down | fires, moves nothing | 2+33→retracted, 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 50+0→spat, 53+0→spat, 56+0→spat, 59+0→spat | block←wire (QC) 9 |
| 9 12 -2 | west | fires, moves nothing | 10+2→spat, 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 50+0→spat, 53+0→spat, 56+0→spat, 59+0→spat | block←observer 3, target (QC) 7 |
| 9 12 0 | down | fires, moves nothing | 2+33→retracted, 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 50+0→spat, 53+0→spat, 56+0→spat, 59+0→spat | block←wire (QC) 1, target (QC) 8 |
| 10 3 -3 | west | fires, moves nothing | 46+2→spat, 52+2→spat | observer 2 |
| 10 4 -5 | west | fires, moves nothing | 14+2→spat, 22+0→spat, 59+2→spat | block←observer 3 |
| 11 1 0 | up | fires, moves nothing | retracted at 35, 38+None→held | torch 1 |
| 11 3 1 | down | fires, moves nothing | retracted at 35, 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 50+0→spat, 53+0→spat, 56+0→spat, 59+0→spat, 62+None→held | wire 9 |
| 11 4 -3 | down | fires, moves nothing | 20+0→spat, 35+0→spat, 41+0→spat, 50+0→spat | block←observer (QC) 1, target (QC) 3 |
| 11 5 -3 | west | fires, moves nothing | 20+0→spat, 35+0→spat, 41+0→spat, 50+0→spat, 59+0→spat | block←observer 1, target 7, target (QC) 1 |
| 11 5 1 | north | fires, moves nothing | 61+2→spat, 69+2→spat | observer (QC) 2 |
| 11 7 0 | west | fires, moves nothing | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 50+0→spat, 53+0→spat, 56+0→spat, 59+0→spat | block←wire 9 |
| 11 12 -1 | north | fires, moves nothing | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 50+0→spat, 53+0→spat | target 7 |
| 11 14 -2 | up | fires, moves nothing | 14+4→retracted | repeater 1 |
| 11 16 -2 | north | fires, moves nothing | 6+2→spat, 48+2→spat | observer 1, block←observer 1 |
| -11 1 -4 S | north | helper | 2+33→pulled | block←wire 1 |
| -11 1 -1 S | up | helper | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 59+0→spat | target (QC) 5 |
| -11 4 -1 | down | helper | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 59+0→spat | block←wire (QC) 5 |
| -11 12 -1 S | north | helper | pulled at 2, 5+30→pulled, 38+None→held | redstone_block 1, redstone_block (QC) 1 |
| -10 1 -5 S | up | helper | 10+2→pulled, 47+2→spat | bud 2 |
| -10 16 1 S | down | helper | 2+33→pulled | target 1 |
| -9 1 1 S | west | helper | 2+33→pulled, 57+2→spat | block←wire (QC) 1, block←observer 1 |
| -9 16 -4 S | north | helper | pulled at 2, 6+2→spat, 38+None→held | block←repeater 1, redstone_block 1 |
| -8 5 1 | up | helper | 6+2→spat, 39+2→spat | block←observer 2 |
| -8 13 1 | down | helper | 35+2→spat, 55+2→spat | comparator (QC) 2, observer 1 |
| -7 16 0 S | west | helper | 41+2→spat | block←observer 1 |
| -6 16 0 S | east | helper | 8+2→spat, 14+2→pulled, 41+2→spat, 47+2→pulled | block←observer 4 |
| -5 4 -6 | up | helper | 6+2→spat, 39+2→spat | observer 2 |
| -5 14 -6 | down | helper | 16+2→spat | block←wire 1 |
| -4 1 0 S | up | helper | 2+33→pulled | block←wire (QC) 1 |
| -4 16 -3 S | west | helper | 8+2→spat | observer 1 |
| -3 14 -2 S | down | helper | pulled at 35, 59+None→held | redstone_block (QC) 1 |
| -2 16 -6 S | west | helper | 2+0→spat, 35+0→pulled | block←wire 2 |
| 1 3 -2 S | west | helper | 16+2→pulled, 21+1→spat, 55+2→pulled | observer 3 |
| 3 2 -6 S | west | helper | 35+0→spat | target (QC) 1 |
| 5 1 -5 S | east | helper | 2+0→spat, 14+2→pulled, 35+0→spat, 47+2→pulled, 53+2→spat | block←wire (QC) 2, observer 3 |
| 5 15 -1 S | west | helper | 7+2→pulled, 42+2→spat | repeater 2 |
| 6 3 -3 S | up | helper | pulled at 35, 59+None→held | redstone_block 1 |
| 6 14 -3 S | down | helper | pulled at 35, 59+None→held | block←comparator (QC) 1 |
| 6 16 -4 S | east | helper | pulled at 35, 48+2→spat, 59+None→held | dropper 1, block←comparator 1 |
| 7 6 0 | up | helper | 12+2→spat, 45+2→spat | block←observer 2 |
| 7 13 0 | down | helper | 39+2→spat | observer 1 |
| 8 4 0 S | east | helper | 2+39→pulled, 45+2→spat | block←wire 1, observer (QC) 1 |
| 8 13 0 S | north | helper | 2+33→pulled | wire 1 |
| 9 4 1 S | down | helper | 2+33→pulled | block←wire 1 |
| 9 16 -1 S | down | helper | 4+33→pulled, 44+2→spat | repeater 1, block←observer 1 |
| 11 1 -3 S | north | helper | pulled at 35, 43+2→spat, 48+8→pulled, 59+1→spat, 63+None→held | observer (QC) 2, redstone_block (QC) 2 |
| 11 10 -1 S | south | helper | 35+0→spat, 38+0→pulled, 41+0→spat, 44+1→pulled, 50+0→spat, 53+1→pulled, 59+0→spat, 62+1→pulled | target 5, observer 3 |
| 11 15 -1 S | south | helper | 39+2→spat | observer (QC) 1 |
| -11 2 1 S | up | power mover | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 59+0→spat | wire (QC) 5 |
| -11 5 0 | up | power mover | 37+2→spat, 42+2→spat, 47+1→spat, 61+2→spat | observer (QC) 4 |
| -11 5 1 S | down | power mover | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 59+0→spat | target (QC) 5 |
| -11 13 -6 S | up | power mover | 2+33→pulled | wire 1 |
| -11 13 -3 S | south | power mover | 2+33→pulled | block←wire (QC) 1 |
| -11 13 0 | down | power mover | 5+30→retracted | redstone_block 1 |
| -11 13 1 | down | power mover | 45+2→spat | block←observer 1 |
| -11 16 -3 S | north | power mover | 4+2→spat, 37+2→pulled | observer 2 |
| -10 4 -4 | up | power mover | 41+2→spat | observer 1 |
| -10 12 -6 S | up | power mover | 10+2→pulled, 43+2→spat | observer 2 |
| -10 13 -4 | down | power mover | 4+33→retracted | repeater (QC) 1 |
| -10 14 -1 S | east | power mover | 2+33→pulled | bud 1 |
| -10 15 0 S | down | power mover | 2+33→pulled | target 1 |
| -9 6 -6 | up | power mover | 10+2→spat, 15+5→retracted, 44+0→spat, 51+2→spat | block←observer (QC) 2, redstone_block (QC) 2 |
| -9 11 0 S | down | power mover | 10+2→pulled, 41+2→spat | bud 2 |
| -9 15 -6 | down | power mover | 6+2→spat, 47+2→spat | block←observer 2 |
| -9 15 -5 S | south | power mover | 2+0→spat, 8+27→pulled | block←wire 2 |
| -8 2 -6 | up | power mover | 8+0→spat, 20+0→spat, 44+0→spat | block←comparator (QC) 3 |
| -8 2 -3 S | west | power mover | 2+0→spat, 8+27→pulled | block←wire (QC) 2 |
| -8 13 -6 | down | power mover | 5+2→spat, 11+9→retracted, 41+2→spat | observer (QC) 2, block←repeater 1 |
| -7 2 -6 | up | power mover | 9+0→spat, 14+2→spat, 20+2→spat, 25+10→retracted, 51+2→spat | block←observer (QC) 1, block←observer 3, block←repeater (QC) 1 |
| -7 15 -6 | down | power mover | 5+2→spat, 38+2→spat | block←observer 2 |
| -7 16 -1 S | north | power mover | 21+2→pulled, 46+2→spat | observer 2 |
| -6 1 -6 | up | power mover | 14+2→spat, 35+3→retracted, 48+0→spat, 54+0→spat | block←observer 3, block←repeater (QC) 3 |
| -6 2 -4 | up | power mover | 17+0→spat, 56+2→spat | block←observer (QC) 1, target (QC) 1 |
| -6 3 1 | up | power mover | 7+3→retracted, 38+3→retracted | block←observer (QC) 2 |
| -6 13 -4 | down | power mover | 13+2→spat, 50+2→spat | observer (QC) 1, bud (QC) 1 |
| -6 14 -6 | down | power mover | 20+2→spat, 45+2→spat, 51+2→spat | wire (QC) 3 |
| -6 14 1 | down | power mover | 14+2→spat, 41+2→spat, 47+2→spat | block←observer (QC) 3 |
| -5 1 0 S | up | power mover | 16+2→spat, 53+2→pulled | observer 2 |
| -5 4 1 | up | power mover | 4+2→spat, 37+2→spat | observer 2 |
| -5 6 -4 S | west | power mover | 20+21→pulled | comparator 1 |
| -5 8 -4 S | west | power mover | 20+21→pulled | comparator 1 |
| -5 10 -4 S | west | power mover | 20+21→pulled | comparator 1 |
| -5 12 -4 S | west | power mover | 20+21→pulled | comparator 1 |
| -5 13 1 | down | power mover | 50+2→spat | observer (QC) 1 |
| -4 4 -4 | up | power mover | 20+0→spat | block←observer (QC) 1 |
| -4 4 1 | up | power mover | 14+2→spat, 47+2→spat | observer (QC) 2 |
| -4 13 0 S | north | power mover | 12+2→spat, 45+2→pulled | repeater (QC) 2 |
| -4 13 1 | down | power mover | 8+2→spat, 41+2→spat | block←repeater (QC) 2 |
| -4 14 -4 | down | power mover | 16+2→spat | wire 1 |
| -3 1 -1 | up | power mover | 2+33→retracted, 38+0→spat, 44+0→spat, 53+0→spat, 59+0→spat | target (QC) 1, wire (QC) 4 |
| -3 14 -1 | down | power mover | 35+0→spat, 41+2→spat, 50+2→spat, 56+2→spat | wire 4 |
| -2 2 1 S | east | power mover | pulled at 2, 5+30→pulled, 38+None→held | redstone_block 1, redstone_block (QC) 1 |
| -2 15 1 S | west | power mover | 9+2→pulled, 44+2→spat | observer 2 |
| -1 16 -2 S | west | power mover | 2+33→pulled, 57+2→spat | block←comparator 1, observer 1 |
| 0 2 -1 S | east | power mover | 2+0→spat, 35+0→spat | redstone_block 2 |
| 0 3 -6 S | east | power mover | 2+0→spat, 35+0→pulled | target 2 |
| 0 3 1 S | west | power mover | 2+0→spat, 8+27→pulled | target 2 |
| 1 14 -6 S | west | power mover | 2+0→spat, 35+0→pulled | block←wire 2 |
| 2 1 -6 S | south | power mover | 8+2→pulled, 41+2→spat | observer 2, target (QC) 1 |
| 2 1 -3 S | west | power mover | 2+0→spat, 35+0→pulled | target (QC) 2 |
| 2 1 -1 S | west | power mover | pulled at 2, 5+30→pulled, 38+None→held | redstone_block (QC) 2 |
| 2 16 -4 S | west | power mover | 2+0→spat, 35+0→pulled | target 2 |
| 2 16 -2 S | west | power mover | 22+2→pulled, 53+2→spat | repeater 2 |
| 3 2 -1 S | west | power mover | 2+0→spat, 35+0→spat | target (QC) 2 |
| 3 3 1 S | east | power mover | 2+0→spat, 8+27→pulled | target 2 |
| 3 15 1 S | east | power mover | 2+0→spat, 35+0→spat | target (QC) 2 |
| 4 14 -4 S | up | power mover | 2+0→spat, 35+0→pulled | target (QC) 2 |
| 4 14 1 S | east | power mover | pulled at 2, 5+30→pulled, 38+None→held | redstone_block (QC) 2 |
| 5 2 1 S | west | power mover | pulled at 2, 5+30→pulled, 38+None→held | redstone_block 1, redstone_block (QC) 1 |
| 6 1 -4 | up | power mover | 38+0→spat, 44+0→spat, 53+0→spat, 59+3→retracted | wire (QC) 4 |
| 6 1 -2 | up | power mover | 2+33→retracted, 38+0→spat, 44+0→spat, 53+0→spat, 59+3→retracted | block←wire 1, wire (QC) 4 |
| 6 14 -4 | down | power mover | 35+2→spat, 41+2→spat, 50+2→spat, 56+2→spat | wire (QC) 2, repeater (QC) 1, block←observer 1 |
| 6 14 -2 | down | power mover | 35+0→spat, 41+2→spat, 50+2→spat, 56+2→spat | block←wire 1, repeater 1, observer (QC) 2 |
| 6 15 1 S | west | power mover | 2+0→spat, 35+0→spat | redstone_block 2 |
| 7 2 -6 | up | power mover | 44+0→spat, 53+1→spat | redstone_block (QC) 2 |
| 7 3 -1 S | north | power mover | 2+33→pulled, 57+2→spat | block←wire 1, observer 1 |
| 7 4 -3 S | east | power mover | pulled at 35, 59+None→held | redstone_block 1 |
| 7 13 -6 | down | power mover | 41+2→spat, 50+2→spat | block←observer (QC) 2 |
| 7 14 1 S | down | power mover | pulled at 35, 41+None→held | redstone_block 1 |
| 7 16 -6 S | west | power mover | 42+2→pulled, 57+2→spat | observer 2 |
| 8 3 -6 | up | power mover | 41+0→spat, 44+0→spat, 56+0→spat | redstone_block (QC) 3 |
| 8 5 -1 | up | power mover | 37+2→spat, 45+2→spat | observer 1, block←observer 1 |
| 8 12 -1 | down | power mover | 2+33→retracted, 41+0→spat, 50+0→spat, 59+0→spat | wire 1, target (QC) 6 |
| 8 14 0 S | up | power mover | 53+2→spat, 61+2→pulled | observer (QC) 2 |
| 8 16 -6 | down | power mover | 38+2→spat, 53+2→spat | block←observer 2 |
| 9 1 -1 S | north | power mover | 6+31→pulled | repeater (QC) 1 |
| 9 2 -1 | up | power mover | 6+31→retracted, 48+2→spat | repeater 1, observer (QC) 1 |
| 9 12 -1 | down | power mover | 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 53+0→spat, 56+0→spat, 59+0→spat | target 7 |
| 10 1 -1 S | north | power mover | 5+30→pulled | block←wire (QC) 1 |
| 10 7 1 S | up | power mover | 12+2→spat, 45+2→pulled | observer 2 |
| 10 10 1 S | up | power mover | 2+33→pulled | wire 1 |
| 10 16 -4 S | down | power mover | 49+2→spat, 54+2→pulled | observer 1, repeater 1 |
| 11 1 -6 | up | power mover | 35+10→retracted, 56+5→retracted | redstone_block (QC) 2 |
| 11 2 -3 S | north | power mover | 12+2→spat, 43+2→pulled, 54+2→spat, 59+1→pulled | observer 4 |
| 11 3 -4 | up | power mover | retracted at 12, 20+0→spat, 48+6→retracted, 63+None→held | block←observer (QC) 1, redstone_block 2 |
| 11 3 -2 | up | power mover | 55+8→retracted | repeater (QC) 1 |
| 11 3 0 S | up | power mover | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 50+0→spat, 53+0→spat, 56+0→spat, 59+0→spat | wire (QC) 9 |
| 11 4 -5 | up | power mover | 22+0→spat, 59+2→spat | block←observer (QC) 2 |
| 11 6 0 S | down | power mover | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 47+0→spat, 50+0→spat, 53+0→spat, 56+0→spat, 59+0→spat | block←wire (QC) 9 |
| 11 13 -5 | down | power mover | 18+2→spat, 55+2→spat | observer 2 |
| 11 13 -2 | down | power mover | 14+4→retracted | repeater (QC) 1 |
| 11 14 -4 | down | power mover | 16+2→spat | block←observer 1 |
| 11 15 -6 | down | power mover | 10+2→spat, 52+2→spat | observer (QC) 2 |
| 11 16 1 S | north | power mover | 2+33→pulled | target 1 |
| -11 4 -4 | up | power switch | 8+2→spat | observer (QC) 1 |
| -11 14 -4 | down | power switch | 2+2→spat | target (QC) 1 |
| -9 3 -3 S | east | power switch | pulled at 2, 6+2→spat, 35+0→pulled, 38+None→held | observer 1, block←wire 1, redstone_block 1 |
| -9 14 -3 S | north | power switch | pulled at 2, 5+30→pulled, 38+None→held | redstone_block 1, redstone_block (QC) 1 |
| 1 16 -1 S | west | power switch | 2+0→spat, 35+0→pulled | target 2 |
| 6 16 -1 S | north | power switch | 2+33→pulled, 57+2→spat | target 2 |
| 9 4 -6 | up | power switch | 16+2→spat, 58+2→spat | repeater (QC) 2 |
| 9 15 -6 | down | power switch | 38+2→spat, 53+2→spat | block←observer 2 |
| -11 6 1 | up | stack | 35+0→spat, 38+0→spat, 41+0→spat, 44+0→spat, 49+4→retracted, 59+0→spat | target 5, block←repeater (QC) 1 |
| -11 15 1 | down | stack | 2+33→retracted | target 1 |
| -10 6 -3 S | east | stack | 45+2→pulled | observer (QC) 1 |
| -10 6 -1 S | north | stack | 4+1→spat, 47+2→spat, 52+1→pulled | block←wire (QC) 4 |
| -10 7 -3 S | east | stack | 45+2→pulled | observer 1 |
| -10 7 -1 S | north | stack | 4+1→spat, 37+0→spat, 47+2→spat, 52+1→pulled | block←wire 4 |
| -10 8 -3 S | east | stack | 45+2→pulled | observer (QC) 1 |
| -10 8 -1 S | north | stack | 4+1→spat, 47+2→spat, 52+1→pulled | wire 3 |
| -10 9 -3 S | east | stack | 45+2→pulled | observer 1 |
| -10 9 -1 S | north | stack | 4+1→spat, 47+2→spat, 52+1→pulled | block←observer 3 |
| -10 10 -3 S | east | stack | 45+2→pulled | observer (QC) 1 |
| -10 10 -1 S | north | stack | 4+1→spat, 37+0→spat, 47+2→spat, 52+1→pulled | block←observer (QC) 4 |
| -10 11 -3 S | east | stack | 45+2→pulled | observer 1 |
| -10 11 -1 S | north | stack | 4+1→spat, 37+0→spat, 47+2→spat, 52+1→pulled | block←observer 4 |
| -9 6 -5 S | south | stack | 10+0→spat, 51+0→pulled | observer (QC) 2 |
| -9 7 -5 S | south | stack | 10+0→spat, 51+0→pulled | observer 2 |
| -9 8 -5 S | south | stack | 10+0→spat, 51+0→pulled | observer 2 |
| -9 9 -5 S | south | stack | 10+0→spat, 51+0→pulled | observer (QC) 2 |
| -9 10 -5 S | south | stack | 10+0→spat, 51+0→pulled | observer 2 |
| -9 11 -5 S | south | stack | 10+0→spat, 51+0→pulled | observer 2 |
| -7 5 -5 | up | stack | 22+2→spat, 55+2→spat | observer 2 |
| -7 5 -3 | east | stack | 16+2→spat, 23+1→retracted, retracted at 26, 40+1→spat, 53+2→spat, 59+2→spat | repeater 4, observer (QC) 1 |
| -7 6 -5 S | south | stack | 9+0→spat, 42+2→spat | observer (QC) 2 |
| -7 6 -2 S | east | stack | 35+0→spat, 38+0→spat, 59+0→spat | wire (QC) 3 |
| -7 6 -1 S | east | stack | 38+0→pulled, 44+0→spat | target 3 |
| -7 7 -5 S | south | stack | 9+0→spat, 42+2→spat | observer 2, observer (QC) 1 |
| -7 7 -2 S | east | stack | 35+0→spat, 38+0→spat, 59+0→spat | wire 3 |
| -7 7 -1 S | east | stack | 38+0→pulled, 44+0→spat | wire (QC) 3 |
| -7 8 -5 S | south | stack | 9+0→spat, 42+2→spat | observer (QC) 2, observer 1 |
| -7 8 -2 S | east | stack | 35+0→spat, 38+0→spat, 59+0→spat | wire (QC) 3 |
| -7 8 -1 S | east | stack | 38+0→pulled, 44+0→spat | wire 3 |
| -7 9 -5 S | south | stack | 9+0→spat, 42+2→spat | observer 2, observer (QC) 1 |
| -7 9 -2 S | east | stack | 35+0→spat, 38+0→spat, 59+0→spat | wire 3 |
| -7 9 -1 S | east | stack | 38+0→pulled, 44+0→spat | wire (QC) 3 |
| -7 10 -5 S | south | stack | 9+0→spat, 42+2→spat | observer (QC) 2, observer 1 |
| -7 10 -2 S | east | stack | 35+0→spat, 38+0→spat, 59+0→spat | wire (QC) 3 |
| -7 10 -1 S | east | stack | 38+0→pulled, 44+0→spat | wire 3 |
| -7 11 -5 S | south | stack | 9+0→spat, 42+2→spat | observer 2, observer (QC) 1 |
| -7 11 -2 S | east | stack | 35+0→spat, 38+0→spat, 59+0→spat | wire 3 |
| -7 11 -1 S | east | stack | 38+0→pulled, 44+0→spat | wire (QC) 3 |
| -7 12 -3 S | east | stack | 24+2→pulled, 55+2→pulled | observer 2, block←wire (QC) 1 |
| -7 15 -5 | down | stack | 5+2→spat, 38+2→spat | block←observer (QC) 2 |
| -6 5 -1 | up | stack | 6+2→spat, 41+None→held | observer 2 |
| -6 6 0 S | north | stack | 38+0→spat, 41+0→spat, 57+2→pulled | block←observer 2, bud 2 |
| -6 7 0 S | north | stack | 38+0→spat, 41+0→spat, 57+2→pulled | bud (QC) 2, block←observer (QC) 1 |
| -6 8 0 S | north | stack | 38+0→spat, 41+0→spat, 57+2→pulled | bud 2, block←observer 1 |
| -6 9 0 S | north | stack | 38+0→spat, 41+0→spat, 57+2→pulled | bud (QC) 2, block←observer (QC) 1 |
| -6 10 0 S | north | stack | 38+0→spat, 41+0→spat, 57+2→pulled | bud 2, block←observer 1 |
| -6 11 0 S | north | stack | 38+0→spat, 41+0→spat, 57+2→pulled | block←observer (QC) 3 |
| -6 13 -3 | down | stack | 20+4→retracted, 50+2→spat | block←repeater (QC) 1, block←wire (QC) 1 |
| -6 13 -1 | down | stack | 35+2→spat | block←comparator 2 |
| -5 1 -4 | up | stack | 46+2→spat, 53+0→spat | block←observer 1, block←observer (QC) 1 |
| -5 1 -1 | up | stack | 2+33→retracted, 59+2→spat | block←wire 1, observer (QC) 1 |
| -5 4 -3 | up | stack | 5+2→spat, 11+2→spat, 38+2→spat, 43+2→spat, 59+2→spat | observer 4, target 1 |
| -5 6 0 S | north | stack | 54+2→pulled | observer 1 |
| -5 7 0 S | north | stack | 54+2→pulled | observer (QC) 1 |
| -5 8 0 S | north | stack | 54+2→pulled | observer 1 |
| -5 9 0 S | north | stack | 54+2→pulled | observer (QC) 1 |
| -5 10 0 S | north | stack | 54+2→pulled | observer 1 |
| -5 11 0 S | north | stack | 54+2→pulled | observer 1 |
| -5 13 -1 | down | stack | 35+2→spat, 45+2→spat | block←comparator (QC) 1, lamp (QC) 1 |
| -5 14 -3 S | down | stack | 45+2→pulled, 53+2→spat | observer (QC) 2 |
| -5 15 -4 | down | stack | 16+8→retracted, 43+2→spat, 49+2→spat | repeater (QC) 1, block←observer (QC) 2 |
| 7 4 -4 | up | stack | 5+2→spat, 19+2→spat, 38+2→spat, 52+2→spat, 59+1→spat | block←observer 5 |
| 7 13 -4 | down | stack | 14+2→spat, 35+2→spat, 41+2→spat, 50+2→spat, 56+2→spat | target (QC) 1, wire (QC) 2, block←observer (QC) 2 |
| 8 3 -4 | up | stack | 5+2→spat, 18+4→retracted, 38+3→retracted, 52+2→spat, 59+4→retracted | block←observer 4, block←repeater 1 |
| 8 6 -5 S | south | stack | 41+0→spat, 44+9→pulled | redstone_block 2, redstone_block (QC) 1 |
| 8 7 -5 S | south | stack | 41+0→spat, 44+9→pulled | redstone_block 1, redstone_block (QC) 1 |
| 8 8 -5 S | south | stack | 41+0→spat, 44+9→pulled | redstone_block 2, redstone_block (QC) 1 |
| 8 9 -5 S | south | stack | 41+0→spat, 44+9→pulled | redstone_block 1, redstone_block (QC) 1 |
| 8 10 -5 S | south | stack | 41+0→spat, 44+9→pulled | redstone_block 2, redstone_block (QC) 1 |
| 8 11 -5 S | south | stack | 41+0→spat, 44+9→pulled | redstone_block 1, redstone_block (QC) 1 |
| 8 13 -4 | down | stack | 14+2→spat, 35+2→spat, 56+2→spat | target 3 |
| 9 4 -4 | up | stack | 18+4→retracted, 59+4→retracted | block←repeater 2 |
| 9 6 -5 S | south | stack | 38+0→spat, 54+2→pulled | block←observer (QC) 2 |
| 9 7 -5 S | south | stack | 38+0→spat, 54+2→pulled | block←observer 2 |
| 9 8 -5 S | south | stack | 38+0→spat, 54+2→pulled | block←observer (QC) 2 |
| 9 9 -5 S | south | stack | 38+0→spat, 54+2→pulled | block←observer 2 |
| 9 10 -5 S | south | stack | 38+0→spat, 54+2→pulled | block←observer (QC) 2 |
| 9 11 -5 S | south | stack | 38+0→spat, 54+2→pulled | block←observer 2 |
| 9 13 -4 | down | stack | 14+2→spat, 35+2→spat, 56+2→spat | target (QC) 3 |
| 10 3 -4 | up | stack | 18+4→retracted, 59+4→retracted | block←observer 2, block←repeater 1 |
| 10 6 -5 S | south | stack | 22+0→spat, 59+0→pulled | block←observer 2 |
| 10 7 -5 S | south | stack | 22+0→spat, 59+0→pulled | observer (QC) 2 |
| 10 8 -5 S | south | stack | 22+0→spat, 59+0→pulled | observer 2 |
| 10 9 -5 S | south | stack | 22+0→spat, 59+0→pulled | observer (QC) 2 |
| 10 10 -5 S | south | stack | 22+0→spat, 59+0→pulled | observer 2 |
| 10 11 -5 S | south | stack | 22+0→spat, 59+0→pulled | observer 2 |
| 10 13 -4 | down | stack | 14+2→spat | block←wire 1 |

<!-- end generated -->
