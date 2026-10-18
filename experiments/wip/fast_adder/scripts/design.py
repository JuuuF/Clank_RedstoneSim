import sys
from pchk import Grid, check
LINE_CIN = {(2,4,0),(2,5,0),(2,4,2),(2,5,2),(3,4,2),(3,5,2),(3,5,-1),(2,5,-1),(2,4,3),(2,5,3),(2,5,5),(2,5,4)}
LINE_LAST = {(0,3,0),(0,4,0),(1,3,2),(1,4,2),(1,2,0),(1,3,0),(1,2,1),(1,3,1),(2,2,0),(2,3,0)}
def core(g):
    P = g.put
    # G line z=0, K line z=2 (K shifted +1)
    P((0,3,0),"stone"); P((0,4,0),"dust","G")
    P((1,4,0),"glass"); P((1,5,0),"dust","G")
    P((2,4,0),"stone"); P((2,5,0),"dust","G")
    P((1,3,2),"stone"); P((1,4,2),"dust","K")
    P((2,4,2),"glass"); P((2,5,2),"dust","K")
    P((3,4,2),"stone"); P((3,5,2),"dust","K")
    # read R, spur, C path
    P((1,2,0),"stone"); P((1,3,0),"cmp","C","east")
    P((1,2,1),"stone"); P((1,3,1),"dust","K")
    P((2,2,0),"stone"); P((2,3,0),"dust","C")
    P((2,2,-1),"stone"); P((2,3,-1),"dust","C")
    P((1,3,-1),"stone"); P((1,4,-1),"dust","C"); P((1,5,-1),"stone")
    P((2,2,-2),"stone"); P((2,3,-2),"dust","C"); P((2,3,-3),"stone")
    P((1,2,-2),"stone"); P((1,3,-2),"rep","C","north")
    P((1,2,-3),"stone"); P((1,3,-3),"cmp","S","north")
    P((0,2,-3),"stone"); P((0,3,-3),"dust","H")
    P((0,3,-5),"stone"); P((0,3,-4),"wtorch","H","south")   # H torch 2 on (0,3,-5)
    P((1,3,-4),"stone"); P((1,4,-4),"dust","S")
    P((2,2,-4),"stone"); P((2,3,-4),"rep","Cr","north")
    P((1,2,-5),"stone"); P((1,3,-5),"cmp","S","south")
    P((2,2,-5),"stone"); P((2,3,-5),"dust","Cr")
    P((1,3,-7),"stone"); P((1,3,-6),"wtorch","H","south")   # H torch 1 on (1,3,-7)
    # injections
    P((3,5,-1),"stone")                      # GB: the next slice's corner cell
    P((2,5,-1),"wtorch","G","west")         # G torch (attached east) powers Gs
    P((2,4,3),"stone"); P((2,5,3),"rep","K","north")   # K injection repeater into Ki
    P((2,5,5),"stone"); P((2,5,4),"wtorch","X","north") # X = NOR(A,B), rear of the K repeater
class Raw:
    """Unwrapped cells for one bit at offset x0 (no periodic folding)."""
    def __init__(s): s.c = {}
    def put(s, p, t, net=None, f=None): s.c[p] = (t, net, f)
def emit(nbits, parts=(core,)):
    """CLI lines for bits -1..nbits (bit -1: CIN pieces, bit nbits: the last read)."""
    cells = {}
    for j in range(-1, nbits+1):
        r = Raw()
        for fn in parts: fn(r)
        for p, c in r.c.items():
            if j == -1 and p not in LINE_CIN: continue
            if j == nbits and p not in LINE_LAST: continue
            q = (p[0]+3*j, p[1], p[2])
            if q in cells and cells[q] != c: raise ValueError(f"overlap {q}: {cells[q]} vs {c}")
            cells[q] = c
    blocks = [f"set {x} {y} {z} {t}" for (x,y,z),(t,n,f) in sorted(cells.items(), key=lambda i: i[0][1]) if t in ("stone","glass")]
    comp = []
    for (x,y,z),(t,n,f) in sorted(cells.items(), key=lambda i: i[0][1]):
        if t == "dust": comp.append(f"place {x} {y} {z} redstone_wire")
        elif t == "rep": comp.append(f"place {x} {y} {z} repeater out={f}")
        elif t == "cmp": comp.append(f"place {x} {y} {z} comparator out={f} mode=subtract")
        elif t == "torch": comp.append(f"place {x} {y} {z} redstone_torch")
        elif t == "wtorch": comp.append(f"place {x} {y} {z} redstone_wall_torch facing={f}")
    return blocks + comp, cells
if __name__ == "__main__":
    g = Grid(); core(g); check(g)
