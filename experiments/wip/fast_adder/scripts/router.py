"""Route dust nets in a periodic 3-wide slice (pchk rules). route(g, net, src, dst, box)."""
from collections import deque
from pchk import W, HD, cond, isdust
H = list(HD.values())
def key(p): return (W(p[0]), p[1], p[2])
class Router:
    def __init__(s, g):
        s.g = g; s.air = set()          # cells that must stay non-conductors
    def cell(s, p, add):
        k = key(p)
        return add.get(k, s.g.c.get(k))
    def ok_dust(s, net, d, add, air):
        """Can net put dust at d given pending additions? returns list of extra (cell,type) or None."""
        g = s.cell
        if g(d, add) is not None: return None
        extra = []
        sup = (d[0], d[1]-1, d[2]); cs = g(sup, add)
        if cs is None:
            if key(sup) in air or key(sup) in s.air: return None
            extra.append((sup, "stone"))
        elif cs[0] not in ("stone", "glass"): return None
        add2 = dict(add); add2.update({key(c): (t, None, None) for c, t in extra})
        x, y, z = d
        for dx, dz in H:
            q = (x+dx, y, z+dz); cq = g(q, add2)
            if isdust(cq) and cq[1] != net: return None
            # other-net dust one up beside: need conductor above d
            u = (x+dx, y+1, z+dz); cu = g(u, add2)
            if isdust(cu) and cu[1] != net:
                a = (x, y+1, z); ca = g(a, add2)
                if not cond(ca):
                    if ca is None and key(a) not in air and key(a) not in s.air:
                        extra.append((a, "stone")); add2[key(a)] = ("stone", None, None)
                    else: return None
            # other-net dust one down beside: need conductor at q
            l = (x+dx, y-1, z+dz); cl = g(l, add2)
            if isdust(cl) and cl[1] != net and not cond(cq):
                if cq is None and key(q) not in air and key(q) not in s.air:
                    extra.append((q, "stone")); add2[key(q)] = ("stone", None, None)
                else: return None
        direct, strong = s.effects(net)
        if key(d) in direct: return None
        for c, t in extra:
            if key(c) in strong: return None
        for q in [(x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z),(x,y,z+1),(x,y,z-1)]:
            if key(q) in strong and cond(g(q, add2)): return None
        return extra
    def effects(s, net):
        """Cells powered directly / strong targets by sources of other nets."""
        if getattr(s, "_eff", None) and s._eff[0] == (net, len(s.g.c)): return s._eff[1]
        direct, strong = set(), set()
        for (x, y, z), c in s.g.c.items():
            t, n, f = c
            if n == net: continue
            if t in ("torch", "wtorch"):
                att = None
                if t == "wtorch":
                    dx, dz = HD[f]; att = key((x-dx, y, z-dz)); direct.add(key((x, y-1, z)))
                for dx, dz in H:
                    q = key((x+dx, y, z+dz))
                    if q != att: direct.add(q)
                direct.add(key((x, y+1, z))); strong.add(key((x, y+1, z)))
            if t in ("rep", "cmp"):
                dx, dz = HD[f]; direct.add(key((x+dx, y, z+dz))); strong.add(key((x+dx, y, z+dz)))
        s._eff = ((net, len(s.g.c)), (direct, strong))
        return direct, strong
    def sources_hit(s, net, cells_add):
        return False
    def route(s, net, src, dst, box, maxn=200000, maxlen=14):
        """src: a start cell (dust of net, or a cell to create) or None = all dust of net; dst: target cell."""
        starts = [key(src)] if src is not None else [k for k, c in s.g.c.items() if c[0] == "dust" and c[1] == net]
        prev, info, dq, depth = {}, {}, deque(), {}
        for st in starts:
            add = {}
            if s.g.c.get(st) is None:
                ex = s.ok_dust(net, st, {}, set())
                if ex is None: continue
                add = {key(c): (t, None, None) for c, t in ex}; add[st] = ("dust", net, None)
            prev[st] = None; info[st] = (add, set()); dq.append(st); depth[st] = 0
        tgt = key(dst)
        while dq:
            p = dq.popleft()
            if p == tgt: break
            add, air = info[p]
            if depth[p] >= maxlen: continue
            for dx, dz in H:
                for dy in (0, 1, -1):
                    d = (p[0]+dx, p[1]+dy, p[2]+dz); kd = key(d)
                    if kd in prev: continue
                    (x0, x1), (y0, y1), (z0, z1) = box
                    if not (y0 <= d[1] <= y1 and z0 <= d[2] <= z1): continue
                    a2 = dict(add); r2 = set(air)
                    if dy == 1:   # cell above p must be non-conductor
                        ab = key((p[0], p[1]+1, p[2]))
                        if cond(s.cell(ab, a2)) or s.cell(ab, a2) is not None: continue
                        r2.add(ab)
                    if dy == -1:  # p's support conductor, cell above d non-conductor
                        if not cond(s.cell((p[0], p[1]-1, p[2]), a2)): continue
                        ab = key((d[0], d[1]+1, d[2]))
                        if s.cell(ab, a2) is not None: continue
                        r2.add(ab)
                    if kd == tgt and isdust(s.cell(kd, a2)) and s.cell(kd, a2)[1] == net:
                        ex = []
                    else:
                        ex = s.ok_dust(net, kd, a2, r2)
                        if ex is None: continue
                    for c, t in ex: a2[key(c)] = (t, None, None)
                    a2[kd] = ("dust", net, None)
                    prev[kd] = p; info[kd] = (a2, r2); dq.append(kd); depth[kd] = depth[p] + 1
        if tgt not in prev: return None
        add, air = info[tgt]
        for k, v in add.items():
            if k not in s.g.c: s.g.c[k] = v
        s.air |= air
        return add
