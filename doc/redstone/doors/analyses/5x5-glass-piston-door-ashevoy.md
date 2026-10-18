# Glass Piston Door by ashevoy

World: `piston_doors/5x5 Glass Piston Door By ashevoy.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 5×5 in the plane x = 0; 1 more output cells outside it.
- Timeline: use lever at 1, use lever at 43; markers Closing 1, Closed 42, Opening 43, Opened 101
- Reference states: closed at tick 42, open at tick 101. Fully closed at ticks 37-43, 46, 49, 52, 55; fully open at 0-15, 80-115.
- Pistons by role: door 98, fires, moves nothing 2, helper 27, idle 21, power mover 22, power switch 8, stack 33
- How extensions were powered (block giving the signal; QC = through the block above the piston): wire 55, block←wire 54, block←repeater 40, target 33, block←wire (QC) 27, wire (QC) 25, block←observer 15, repeater (QC) 13, observer 12, repeater 8, target (QC) 7, block←observer+wire (QC) 6, block←observer+wire 6, block←repeater (QC) 6, redstone_block 3, redstone_block (QC) 3, block←observer (QC) 3, comparator 1, bud (QC) 1, bud 1
- Phases (bursts of piston events): 2–40 (305 events, 103 pistons); 44–84 (499 events, 161 pistons); 88–90 (4 events, 4 pistons); 98–98 (1 events, 1 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
    0     16     18     26     27     28     29     31     32     34
.....  .....  .....  .....  ~...~  ~...~  #...#  #...#  #...#  #...#
.....  .....  .....  .....  ~...~  ~...~  #...#  #...#  #~~~#  #####
.....  .....  .....  .....  ~...~  ~...~  #~~~#  #####  #~~~#  #####
.....  .....  .....  .~~~.  ~~~~~  ~###~  #~~~#  #####  #~~~#  #####
.....  .~~~.  .###.  .~~~.  ~~~~~  ~###~  #~~~#  #####  #~~~#  #####

   35     37     44     46     47     49     50     52     53     55
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #####  #####
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #####  #####
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####
#~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####  #~~~#  #####

   56     58     60     62     63     64     66     68     71     72
#####  #####  .~~~.  .###.  .###.  .~~~.  .###.  .....  .~~~.  .~~~.
#~~~#  #####  .....  .....  .~~~.  .~~~.  .###.  .###.  .###.  .....
#~~~#  #####  .###.  .###.  .###.  .....  .....  .....  .....  .....
#...#  #...#  .....  .....  .....  .....  .....  .....  .....  .....
#####  #####  .###.  .....  .....  .....  .....  .....  .....  .....

   74     80
.###.  .....
.....  .....
.....  .....
.....  .....
.....  .....

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 15 | 52 | 8×6, 12×3, 18×6 | down 4, east 1, south 4 (3), down 5, south 4 (3), down 4 (9) |
| above | 6 | 18 | 6×3, 8×3 | stays (6) |
| north | 5 | 20 | 6×5 | east 1, north 2 (5) |
| south | 5 | 20 | 6×5 | east 1, south 2 (5) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -3 9 -3 | east | door | 4+2→spat, 58+2→spat | target 2 |
| -3 9 -2 | east | door | 4+2→spat, 58+2→spat | target 2 |
| -3 9 -1 | east | door | 4+2→spat, 58+2→spat | target 2 |
| -2 11 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | block←wire (QC) 3 |
| -2 11 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | block←wire (QC) 3 |
| -2 12 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | block←wire 3 |
| -2 12 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | block←wire 3 |
| -2 13 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire 3 |
| -2 13 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire 3 |
| -2 14 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire (QC) 3 |
| -2 14 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire (QC) 3 |
| -2 15 -6 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire 3 |
| -2 15 2 S | east | door | 23+2→spat, 50+2→pulled, 72+2→spat | wire 3 |
| 0 1 -3 | up | door | 26+2→spat | block←wire 1 |
| 0 1 -2 | up | door | 26+2→spat | block←wire 1 |
| 0 1 -1 | up | door | 26+2→spat | block←wire 1 |
| 0 3 -3 | up | door | 29+1→spat | block←wire 1 |
| 0 3 -2 | up | door | 29+1→spat | block←wire 1 |
| 0 3 -1 | up | door | 29+1→spat | block←wire 1 |
| 0 5 -3 | up | door | 32+4→retracted | block←wire 1 |
| 0 5 -2 | up | door | 32+4→retracted | block←wire 1 |
| 0 5 -1 | up | door | 32+4→retracted | block←wire 1 |
| 0 7 -3 | up | door | 35+5→retracted | target 1 |
| 0 7 -2 | up | door | 35+5→retracted | target 1 |
| 0 7 -1 | up | door | 35+5→retracted | target 1 |
| 0 9 -3 S | up | door | 16+2→spat, 61+1→pulled | block←observer 2 |
| 0 9 -2 S | up | door | 16+2→spat, 61+1→pulled | block←observer 2 |
| 0 9 -1 S | up | door | 16+2→spat, 61+1→pulled | block←observer 2 |
| 0 10 -12 | south | door | 68+8→retracted | target 1 |
| 0 10 -10 | south | door | 71+7→retracted | block←repeater 1 |
| 0 10 -8 | south | door | 74+6→retracted | block←repeater 1 |
| 0 10 -6 | south | door | 77+5→retracted | block←repeater 1 |
| 0 10 2 | north | door | 11+3→retracted, 50+6→retracted | block←repeater 2 |
| 0 10 4 | north | door | 8+4→retracted, 48+6→retracted | block←repeater 2 |
| 0 10 6 | north | door | 5+5→retracted, 46+6→retracted | block←repeater 2 |
| 0 10 8 | north | door | 2+7→retracted, 44+6→retracted | target 2 |
| 0 11 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | block←observer+wire (QC) 2, block←wire (QC) 4 |
| 0 11 -6 S | south | door | 59+1→pulled | target (QC) 1 |
| 0 11 2 S | north | door | 58+2→pulled | target (QC) 1 |
| 0 11 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | block←observer+wire (QC) 2, block←wire (QC) 4 |
| 0 12 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | block←observer+wire 2, block←wire 4 |
| 0 12 -6 S | south | door | 59+1→pulled | target 1 |
| 0 12 2 S | north | door | 58+2→pulled | target 1 |
| 0 12 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | block←observer+wire 2, block←wire 4 |
| 0 13 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire 6 |
| 0 13 -6 S | south | door | 59+1→pulled | target (QC) 1 |
| 0 13 2 S | north | door | 58+2→pulled | target (QC) 1 |
| 0 13 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire 6 |
| 0 14 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire (QC) 6 |
| 0 14 -6 S | south | door | 59+1→pulled | target 1 |
| 0 14 -3 S | down | door | 53+3→pulled | block←observer (QC) 1 |
| 0 14 -2 S | down | door | 53+3→pulled | block←observer (QC) 1 |
| 0 14 -1 S | down | door | 53+3→pulled | block←observer (QC) 1 |
| 0 14 2 S | north | door | 58+2→pulled | target 1 |
| 0 14 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire (QC) 6 |
| 0 15 -7 S | south | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire 6 |
| 0 15 -6 S | south | door | 59+1→pulled | target (QC) 1 |
| 0 15 -3 S | down | door | 63+1→pulled, 68+None→held | block←wire (QC) 2, block←observer 1 |
| 0 15 -2 S | down | door | 63+1→pulled, 68+None→held | block←wire (QC) 2, block←observer 1 |
| 0 15 -1 S | down | door | 63+1→pulled, 68+None→held | block←observer 1, block←wire (QC) 1 |
| 0 15 2 S | north | door | 58+2→pulled | target (QC) 1 |
| 0 15 3 S | north | door | 11+2→pulled, 20+1→spat, 27+2→spat, 46+2→pulled, 67+1→pulled, 76+2→spat | wire 6 |
| 0 16 -3 S | down | door | 50+10→pulled, 71+1→pulled | block←wire 2 |
| 0 16 -2 S | down | door | 50+10→pulled, 71+1→pulled | block←wire 2 |
| 0 16 -1 S | down | door | 50+10→pulled, 71+1→pulled | block←wire 2 |
| 0 17 -3 S | down | door | 68+0→pulled, 79+1→pulled | wire 2 |
| 0 17 -2 S | down | door | 68+0→pulled, 79+1→pulled | wire 2 |
| 0 17 -1 S | down | door | 68+0→pulled, 79+1→pulled | wire 2 |
| 0 18 -3 S | down | door | 47+18→pulled, 75+1→pulled | wire (QC) 1, observer 1 |
| 0 18 -2 S | down | door | 47+18→pulled, 75+1→pulled | wire (QC) 1, observer 1 |
| 0 18 -1 S | down | door | 47+18→pulled, 75+1→pulled | wire (QC) 1, observer 1 |
| 0 20 -3 S | down | door | 44+24→pulled | block←wire 1 |
| 0 20 -2 S | down | door | 44+24→pulled | bud 1 |
| 0 20 -1 S | down | door | 44+24→pulled | block←wire 1 |
| 1 10 -12 | south | door | 68+8→retracted | target 1 |
| 1 10 -10 | south | door | 71+7→retracted | block←repeater 1 |
| 1 10 -8 | south | door | 74+6→retracted | block←repeater 1 |
| 1 10 -6 | south | door | 77+5→retracted | block←repeater 1 |
| 1 10 2 | north | door | 11+3→retracted, 50+6→retracted, 59+3→retracted | block←repeater 2, target (QC) 1 |
| 1 10 4 | north | door | 8+4→retracted, 48+6→retracted | block←repeater 2 |
| 1 10 6 | north | door | 5+5→retracted, 46+6→retracted | block←repeater 2 |
| 1 10 8 | north | door | 2+7→retracted, 44+6→retracted | target 2 |
| 2 10 -3 S | west | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 2 10 -2 S | west | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 2 10 -1 S | west | door | 20+2→spat, 56+2→pulled | block←observer 2 |
| 3 11 -6 | west | door | 17+2→spat | block←observer+wire (QC) 1 |
| 3 11 2 | west | door | 17+2→spat | block←observer+wire (QC) 1 |
| 3 12 -6 | west | door | 17+2→spat | block←observer+wire 1 |
| 3 12 2 | west | door | 17+2→spat | block←observer+wire 1 |
| 3 13 -6 | west | door | 17+2→spat | wire 1 |
| 3 13 2 | west | door | 17+2→spat | wire 1 |
| 3 14 -6 | west | door | 17+2→spat | wire (QC) 1 |
| 3 14 2 | west | door | 17+2→spat | wire (QC) 1 |
| 3 15 -6 | west | door | 17+2→spat | wire 1 |
| 3 15 2 | west | door | 17+2→spat | wire 1 |
| 5 9 -3 | west | door | 22+2→spat, 70+2→spat | target 2 |
| 5 9 -2 | west | door | 22+2→spat, 70+2→spat | target 2 |
| 5 9 -1 | west | door | 22+2→spat, 70+2→spat | target 2 |
| -4 19 -4 | south | fires, moves nothing | 70+8→retracted | block←wire 1 |
| -4 19 0 | north | fires, moves nothing | 70+8→retracted | block←wire 1 |
| -6 4 0 S | up | helper | 2+42→pulled | block←wire 1 |
| -6 13 -11 S | north | helper | 5+39→pulled | target 1 |
| -6 13 7 S | south | helper | 5+39→pulled | target 1 |
| -6 15 3 S | up | helper | 68+22→pulled | repeater (QC) 1 |
| -6 21 6 S | up | helper | 60+24→pulled | repeater (QC) 1 |
| -5 18 2 S | up | helper | 58+22→pulled | block←wire 1 |
| -5 23 1 S | north | helper | 74+24→pulled | repeater 1 |
| -4 6 9 S | south | helper | 6+42→pulled | block←repeater 1 |
| -4 17 2 S | east | helper | 68+22→pulled | comparator 1 |
| -4 22 -8 S | east | helper | 52+24→pulled | repeater (QC) 1 |
| -3 17 -4 S | east | helper | 66+6→pulled | block←wire 1 |
| -3 17 -3 S | east | helper | 66+6→pulled | block←wire 1 |
| -3 17 0 S | east | helper | 66+6→pulled | block←wire 1 |
| -3 19 -4 S | east | helper | 70+8→pulled | block←wire (QC) 1 |
| -3 19 -1 S | east | helper | 70+8→pulled | block←wire (QC) 1 |
| -3 19 0 S | east | helper | 70+8→pulled | block←wire (QC) 1 |
| -3 21 3 S | east | helper | 62+22→pulled | block←repeater 1 |
| -2 3 8 S | south | helper | 2+42→pulled | wire 1 |
| -2 4 4 S | up | helper | pulled at 14, 56+None→held | repeater (QC) 1 |
| -2 7 -13 S | up | helper | pulled at 18, 60+None→held | repeater (QC) 1 |
| 0 4 7 S | up | helper | pulled at 4, 46+None→held | block←wire 1 |
| 1 20 -8 S | up | helper | 44+11→pulled | block←wire 1 |
| 2 17 7 S | up | helper | 64+24→pulled | repeater (QC) 1 |
| 2 20 1 S | up | helper | 66+24→pulled | repeater (QC) 1 |
| 2 23 6 S | west | helper | 2+42→pulled | block←wire 1 |
| 4 17 -9 S | up | helper | 8+42→pulled | repeater (QC) 1 |
| 5 4 -10 S | up | helper | pulled at 26, 68+None→held | repeater (QC) 1 |
| -9 6 9 S | east | power mover | 2+0→spat, 8+36→pulled | block←wire 2 |
| -6 3 -5 S | up | power mover | 8+42→pulled | block←wire 1 |
| -6 9 -4 S | north | power mover | 2+42→pulled | wire 1 |
| -6 19 -2 S | down | power mover | 74+8→pulled | repeater (QC) 1 |
| -5 8 7 S | east | power mover | 2+42→pulled | block←wire 1 |
| -5 10 -8 S | east | power mover | 5+39→pulled | block←wire 1 |
| -5 10 4 S | east | power mover | 5+39→pulled | block←wire 1 |
| -5 22 -3 S | east | power mover | 70+8→pulled | wire 1 |
| -3 2 -5 S | south | power mover | 22+42→pulled | repeater 1 |
| -3 21 11 S | east | power mover | 2+0→spat, 8+36→pulled | target 2 |
| -1 8 -5 | south | power mover | 12+2→spat | block←wire 1 |
| -1 8 1 | north | power mover | 56+6→retracted | wire 1 |
| -1 20 11 S | west | power mover | pulled at 2, 5+39→pulled, 47+None→held | redstone_block 1, redstone_block (QC) 1 |
| -1 22 4 S | down | power mover | 44+24→pulled | block←wire 1 |
| 0 23 -4 S | north | power mover | 44+0→spat, 50+18→pulled | block←wire 2 |
| 1 18 -3 S | down | power mover | 48+2→spat, 60+6→pulled | repeater 2 |
| 1 18 -2 S | down | power mover | 48+2→spat, 60+6→pulled | repeater 2 |
| 1 18 -1 S | down | power mover | 48+2→spat, 60+6→pulled | repeater 2 |
| 2 8 -5 | south | power mover | 16+2→spat | block←repeater 1 |
| 2 8 1 | north | power mover | 52+6→retracted | block←wire 1 |
| 3 18 3 S | north | power mover | 72+6→pulled | block←repeater 1 |
| 5 2 -7 S | up | power mover | 18+42→pulled | wire 1 |
| -7 5 9 S | west | power switch | pulled at 2, 5+39→pulled, 47+None→held | redstone_block 1, redstone_block (QC) 1 |
| 0 22 -6 S | south | power switch | pulled at 44, 47+21→pulled, 71+None→held | redstone_block 1, redstone_block (QC) 1 |
| 1 8 -3 S | up | power switch | 28+2→spat, 50+2→pulled | observer 2 |
| 1 8 -2 S | up | power switch | 28+2→spat, 50+2→pulled | observer 2 |
| 1 8 -1 S | up | power switch | 28+2→spat, 50+2→pulled | observer 2 |
| 1 17 -3 S | down | power switch | 79+1→pulled | repeater (QC) 1 |
| 1 17 -2 S | down | power switch | 79+1→pulled | repeater (QC) 1 |
| 1 17 -1 S | down | power switch | 79+1→pulled | repeater (QC) 1 |
| 0 11 -8 S | south | stack | 56+8→pulled | block←wire (QC) 1 |
| 0 11 4 S | north | stack | 54+10→pulled | block←wire (QC) 1 |
| 0 12 -8 S | south | stack | 56+8→pulled | block←wire 1 |
| 0 12 4 S | north | stack | 54+2→retracted, pulled at 64 | block←wire 1 |
| 0 13 -8 S | south | stack | 56+8→pulled | wire 1 |
| 0 13 4 S | north | stack | 54+2→retracted, pulled at 64 | wire 1 |
| 0 14 -8 S | south | stack | 56+8→pulled | wire (QC) 1 |
| 0 14 4 S | north | stack | 54+2→retracted, pulled at 64 | wire (QC) 1 |
| 0 15 -8 S | south | stack | 56+8→pulled | wire 1 |
| 0 15 4 S | north | stack | 54+2→retracted, pulled at 64 | wire 1 |
| 0 19 -3 S | down | stack | 71+1→pulled | block←wire (QC) 1, observer 1 |
| 0 19 -2 S | down | stack | 71+1→pulled | bud (QC) 1, observer 1 |
| 0 19 -1 S | down | stack | 71+1→pulled | observer 1 |
| 1 17 -9 | south | stack | 12+4→retracted | block←repeater (QC) 1 |
| 1 17 -7 | south | stack | 15+3→retracted | block←repeater (QC) 1 |
| 1 17 -5 | south | stack | 18+4→retracted | block←repeater (QC) 1 |
| 1 17 1 | north | stack | 76+6→retracted | block←repeater (QC) 1 |
| 1 17 3 | north | stack | 73+5→retracted | block←repeater (QC) 1 |
| 1 17 5 | north | stack | 70+6→retracted | block←repeater (QC) 1 |
| 1 18 -9 | south | stack | 12+4→retracted | block←repeater 1 |
| 1 18 -7 | south | stack | 15+3→retracted | block←repeater 1 |
| 1 18 -5 S | down | stack | 18+4→retracted, 50+15→retracted | block←repeater 1, block←wire (QC) 2 |
| 1 18 1 | north | stack | 76+6→retracted | block←repeater 1 |
| 1 18 3 | north | stack | 73+5→retracted | block←repeater 1 |
| 1 18 5 | north | stack | 70+6→retracted | block←repeater 1 |
| 2 10 -12 | south | stack | 26+7→retracted, 68+8→retracted | target 2 |
| 2 10 -10 | south | stack | 29+6→retracted, 71+7→retracted | block←repeater 2 |
| 2 10 -8 | south | stack | 32+5→retracted, 74+6→retracted | block←repeater 2 |
| 2 10 -6 | south | stack | 35+4→retracted, 77+5→retracted | block←repeater 2 |
| 2 10 2 S | west | stack | 11+3→retracted, 53+3→retracted | block←repeater 2 |
| 2 10 4 | north | stack | 8+4→retracted, 50+4→retracted | block←repeater 2 |
| 2 10 6 | north | stack | 5+5→retracted, 47+5→retracted | block←repeater 2 |
| 2 10 8 | north | stack | 2+7→retracted, 44+6→retracted | target 2 |

<!-- end generated -->
