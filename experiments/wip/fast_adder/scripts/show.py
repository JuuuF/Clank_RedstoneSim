def render(g, Z0, Z1, ylo=1, yhi=11):
    sym = {"stone":"#","glass":"g","torch":"t","wtorch":"t","rep":"r","cmp":"c"}
    for x in range(3):
        print(f"x={x}  z {Z0}..{Z1}")
        for y in range(yhi, ylo-1, -1):
            row = ""
            for z in range(Z0, Z1+1):
                c = g.c.get((x,y,z))
                if c is None: row += "."
                elif c[0] == "dust": row += (c[1] or "?")[0].lower() if c[1] not in ("nH","nH'","NAB") else {"nH":"h","nH'":"'","NAB":"n"}[c[1]]
                else: row += sym.get(c[0], "?")
            print(f"{y:2d} {row}")
