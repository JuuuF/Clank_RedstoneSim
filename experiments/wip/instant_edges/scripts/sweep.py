import re, subprocess, sys
R = "/home/justin/anaconda3/envs/redsim/bin/redsim-cli"; W = sys.argv[1]
def wave(flips, end):
    out = subprocess.run([R, W, "--dry-run", "-c", "; ".join([f"at {t} use @L" for t in flips] + [f"run {end}", f"waves @OUT ticks 0..{end}"])], capture_output=True, text=True).stdout
    line = [l for l in out.splitlines() if "@OUT" in l and "|" in l]
    return out
def ok(flips, end):
    # expected: OUT on during (flip_i + 1 .. flip_{i+1}) for odd segments
    out = subprocess.run([R, W, "--dry-run", "-c", "; ".join([f"at {t} use @L" for t in flips] + [f"run {end}", "changes @OUT"])], capture_output=True, text=True).stdout
    ev = [int(m[1]) for m in re.finditer(r"tick (\d+)\s+redstone_wire", out)][1:]
    return ev == [t + 1 for t in flips], ev
for N in list(range(1, 21)):
    good, ev = ok([10, 10 + N, 60], 100)
    bad = "" if good else f" got {ev}"
    print(f"on{N}:{'ok' if good else 'X'}{bad}", end="  ")
print()
for N in list(range(1, 31)):
    good, ev = ok([10, 40, 40 + N, 90], 130)
    print(f"off{N}:{'ok' if good else 'X'}", end="  ")
print()
