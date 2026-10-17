"""Run a CLI script text in-process; print filtered output."""
import io, sys
sys.path.insert(0, "/home/justin/Documents/Programming/redstone-sim/src")
from redsim.cli.main import main

class _Stdin(io.StringIO):
    def isatty(self): return False

def run(text, world="/home/justin/.claude/jobs/7b97722e/tmp/cca/w.redsim.json"):
    out = io.StringIO()
    main([world], stdin=_Stdin(text), out=out)
    return out.getvalue()

if __name__ == "__main__":
    text = open(sys.argv[1]).read()
    o = run(text, sys.argv[2] if len(sys.argv) > 2 else "/home/justin/.claude/jobs/7b97722e/tmp/cca/w.redsim.json")
    for line in o.splitlines():
        if line.startswith(("placed", "set ", "> place", "> set", "> label", "@", "> fill", "filled")):
            continue
        print(line)
