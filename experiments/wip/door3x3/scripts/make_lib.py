"""Write examples/circuits/door_3x3.cli.txt from door.py (stage "safe") plus header, harness and targets.

Run from experiments/wip/door3x3/scripts/: python make_lib.py [--probe]
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
body = subprocess.run([sys.executable, os.path.join(HERE, "door.py"), "safe"], capture_output=True, text=True, check=True).stdout
lines = [l for l in body.rstrip("\n").split("\n") if not l.startswith("note ")]
i = lines.index("settle")
lines[i:i] = ["# harness: a stone button and an oak button on the input block's sides (the lever is on top)",
              "place 8 2 12 stone_button face=wall facing=south",
              "place 7 2 11 oak_button face=wall facing=west",
              'label SB 8 2 12 "test stone button (20 ticks)"',
              'label OB 7 2 11 "test oak button (30 ticks)"']
lines.insert(1, 'note "3x3 flush piston door: power the input block @IN to open (test lever @L on top); clear 32 ticks after the input goes on, solid 17 after it goes off; input-safe (any timing)"')
head = open(os.path.join(HERE, "lib_header.txt")).read()
cells = [f"D{x}{r}" for x in range(3) for r in range(3)]
def ex(t, cond, when, which=cells):
    return "\n".join(f"target {t} expect @{c} block={cond} {when}" for c in which)
toggles = lambda t, n, start: "\n".join(f"target {t} do at {start + 3 * k} use @L" for k in range(n))
tail = f"""prefab save door_3x3 0 1 0 16 8 12
group door_3x3 0 1 0 16 8 12 in @IN IN out @D11 C

target new lever "open: side cells clear 8 ticks after the lever, all nine 32 after; close: solid 17 ticks after"
target lever do at 5 use @L
target lever do at 60 use @L
{ex("lever", "smooth_stone", "during 0..12")}
{ex("lever", "air", "during 37..67")}
{ex("lever", "smooth_stone", "during 77..95")}
target lever expect 8 3 2 block=smooth_stone at 60
target lever expect 9 3 2 block=smooth_stone at 60

target new stone "a stone button (20 ticks): the lockout lets the open finish, then the door closes"
target stone do at 5 use @SB
{ex("stone", "air", "during 37..42")}
{ex("stone", "smooth_stone", "during 52..70")}

target new spam "a lever flipped every 3 ticks, 9 times (ends on): the door ends open; off at 150: closed again"
{toggles("spam", 9, 5)}
target spam do at 150 use @L
{ex("spam", "air", "at 140")}
{ex("spam", "smooth_stone", "at 190")}

target new reopen "close at 60, re-open 12 ticks later, re-close 12 after that: ends closed, then cycles (with lock delays of 8 and 24 this stuck)"
target reopen do at 5 use @L
target reopen do at 60 use @L
target reopen do at 72 use @L
target reopen do at 84 use @L
target reopen do at 200 use @L
target reopen do at 260 use @L
{ex("reopen", "smooth_stone", "at 199")}
{ex("reopen", "air", "at 245")}
{ex("reopen", "smooth_stone", "at 290")}

target new burnout "failure case: 16 flips within 48 ticks burn out the input torch (8 turn-offs in 60 ticks, R-007): the door opens and stays open until the torch relights"
{toggles("burnout", 16, 5)}
target burnout expect @D11 block=air during 69..221
target burnout expect @D11 block=smooth_stone at 230

check
"""
if "--probe" in sys.argv:
    tail = tail.replace("\ncheck\n", "\n")
out = os.path.join(ROOT, "examples", "circuits", "door_3x3.cli.txt")
open(out, "w").write(head + "\n".join(lines) + "\n" + tail)
print("wrote", out)
