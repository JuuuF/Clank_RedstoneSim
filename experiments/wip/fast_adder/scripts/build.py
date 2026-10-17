import sys
sys.path.insert(0, "/home/justin/.claude/jobs/7b97722e/tmp/cca")
from pchk import Grid, check, check_weak
from router import Router
import design
Z0, Z1 = -14, 16
def base():
    g = Grid()
    for x in range(3):
        for z in range(Z0, Z1+1): g.put((x,0,z), "stone")
    design.core(g)
    P = g.put
    # NAB endpoint: glass under, stone, on top of GB (0,5,-1)
    P((0,5,0),"glass"); P((0,6,0),"stone")
    # south front end components
    P((1,8,9),"stone"); P((1,8,10),"wtorch","NAB","south")     # notA on Q_A
    P((1,4,9),"stone"); P((1,4,10),"wtorch","NAB","south")     # notB on Q_B
    P((1,6,12),"stone"); P((1,6,13),"wtorch","nH","south")     # G_n on Q_N
    P((1,4,5),"stone"); P((1,5,5),"rep","nH","south")          # X' reads X dust (1,5,4)
    P((1,8,3),"stone"); P((1,9,3),"rep","nH'","north")         # notH' repeater on top, rear (1,9,4)
    P((1,4,4),"stone"); P((1,5,4),"dust","X")
    return g
inp = {(0,3,0):"G", (1,3,2):"K", (1,3,-1):"C", (2,3,-3):"C", (0,3,-5):"nH'", (1,3,-7):"nH'",
       (0,5,-1):"NAB", (2,5,5):"AB", (1,8,9):"A", (1,4,9):"B", (1,6,12):"NAB"}
if __name__ == "__main__":
    g = base(); r = Router(g)
    r.air |= {(2,4,-1), (2,6,-1), (2,6,4), (1,9,10), (1,5,10), (1,7,13), (0,7,-1), (1,5,-4)}
    box = ((0,2),(1,11),(Z0,Z1))
    plan = [("NAB", (1,8,11), (1,4,11)), ("NAB", None, (0,6,-1)), ("NAB", None, (1,7,12)),
            ("A", (1,6,16), (1,9,9)), ("A", None, (2,5,7)),
            ("B", (1,3,16), (1,5,9)), ("B", None, (2,6,5)),
            ("nH", (1,5,6), (1,6,14)), ("nH", None, (1,2,-10)),
            ("S", (1,4,-4), (1,5,-13))]
    for net, a, b in plan:
        res = r.route(net, a, b, box)
        print(net, a, "->", b, "ok" if res is not None else "FAILED")
        if res is None: break
    check(g); check_weak(g, inp)
