"""Periodic-slice checker: one bit slice x in {0,1,2}; x wraps (x=2's +x neighbour is x=0 of the next bit).
cells: {(x,y,z): (type, net, facing)}; types: stone glass dust torch wtorch rep cmp air.
Wall torch facing = direction it points (attached to the opposite side)."""
from collections import defaultdict
HD = {"north":(0,-1),"south":(0,1),"east":(1,0),"west":(-1,0)}
H = list(HD.values())
def W(x): return x % 3
class Grid:
    def __init__(s): s.c = {}
    def get(s, p): return s.c.get((W(p[0]), p[1], p[2]))
    def put(s, p, t, net=None, f=None):
        k = (W(p[0]), p[1], p[2])
        if k in s.c and s.c[k] != (t, net, f):
            raise ValueError(f"cell {p} has {s.c[k]}, wanted {(t, net, f)}")
        s.c[k] = (t, net, f)
def cond(c): return c is not None and c[0] == "stone"
def isdust(c): return c is not None and c[0] == "dust"
def check(g, show=12):
    iss = []
    for (x,y,z), c in list(g.c.items()):
        if c[0] != "dust": continue
        for dx,dz in H:
            q = (x+dx,y,z+dz); cq = g.get(q)
            if isdust(cq) and cq[1] != c[1]: iss.append(f"same-level {c[1]}@{(x,y,z)} ~ {cq[1]}@{q}")
            u = (x+dx,y+1,z+dz); cu = g.get(u)
            if isdust(cu) and cu[1] != c[1] and not cond(g.get((x,y+1,z))):
                iss.append(f"diag {c[1]}@{(x,y,z)} (lower) ~ {cu[1]}@{u}")
        b = g.get((x,y-1,z))
        if not (b and b[0] in ("stone","glass")): iss.append(f"dust {(x,y,z)} unsupported")
    for (x,y,z), c in list(g.c.items()):
        t, net, f = c
        direct, strong = [], []
        if t in ("torch","wtorch"):
            att = None
            if t == "wtorch":
                dx,dz = HD[f]; att = (x-dx,y,z-dz)
                if not cond(g.get(att)): iss.append(f"wtorch {(x,y,z)} no wall")
                direct.append((x,y-1,z))
            elif not cond(g.get((x,y-1,z))): iss.append(f"torch {(x,y,z)} no block")
            for dx,dz in H:
                q = (x+dx,y,z+dz)
                if att is None or (W(q[0]),q[1],q[2]) != (W(att[0]),att[1],att[2]): direct.append(q)
            strong.append((x,y+1,z))
        if t in ("rep","cmp"):
            dx,dz = HD[f]; direct.append((x+dx,y,z+dz)); strong.append((x+dx,y,z+dz))
            b = g.get((x,y-1,z))
            if not (b and b[0] in ("stone","glass")): iss.append(f"{t} {(x,y,z)} unsupported")
        for q in direct:
            cq = g.get(q)
            if isdust(cq) and cq[1] != net: iss.append(f"{t} {net}@{(x,y,z)} powers {cq[1]}@{q}")
        for b in strong:
            if cond(g.get(b)):
                bx,by,bz = b
                for q in [(bx+1,by,bz),(bx-1,by,bz),(bx,by+1,bz),(bx,by-1,bz),(bx,by,bz+1),(bx,by,bz-1)]:
                    cq = g.get(q)
                    if isdust(cq) and cq[1] != net: iss.append(f"{t} {net}@{(x,y,z)} strong {b} -> {cq[1]}@{q}")
    for i in iss[:show]: print("  ", i)
    print(f"  {len(iss)} issues")
    return iss

def shape(g, p):
    """Directions (dx,dz) dust at p points into (Java wire shape)."""
    x, y, z = p
    conn = []
    above = g.get((x, y+1, z))
    for dx, dz in H:
        q = (x+dx, y, z+dz); c = g.get(q)
        hit = False
        if c is not None:
            if c[0] == "dust": hit = True
            elif c[0] in ("torch", "wtorch", "cmp", "lever"): hit = True
            elif c[0] == "rep" and HD[c[2]] in ((dx, dz), (-dx, -dz)): hit = True
        if not hit and not cond(above) and isdust(g.get((x+dx, y+1, z+dz))): hit = True
        if not hit and not cond(c) and isdust(g.get((x+dx, y-1, z+dz))): hit = True
        if hit: conn.append((dx, dz))
    if not conn: return list(H)
    if len(conn) == 1: return [conn[0], (-conn[0][0], -conn[0][1])]
    return conn
def check_weak(g, inp, show=12):
    """inp: {block cell: net allowed to power it weakly}. Reports dust weakly powering a read block."""
    iss = []
    for (x, y, z), c in list(g.c.items()):
        if c[0] != "dust": continue
        targets = [(x, y-1, z)] + [(x+dx, y, z+dz) for dx, dz in shape(g, (x, y, z))]
        for b in targets:
            kb = (W(b[0]), b[1], b[2])
            if kb in inp and inp[kb] != c[1] and cond(g.get(b)):
                iss.append(f"weak {c[1]}@{(x,y,z)} -> read block {b}[{inp[kb]}]")
    for i in iss[:show]: print("  ", i)
    print(f"  {len(iss)} weak issues")
    return iss
