"""v18 balance estimate per 50k interval. Usage: v18_bal.py <dir> run..."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from v18 import load
root = Path(sys.argv[1]); runs = sys.argv[2:]
P = 1.95e-6
for r in runs:
    d = load(root / f"{r}.tsv")
    cls = {}
    for l in open(root / f"{r}.tsv"):
        if l.startswith("# classes ") and " table=1 " in l:
            kv = dict(x.split("=", 1) for x in l[10:].split() if "=" in x); cls[int(kv["tick"])] = float(kv["rep_len"])
        if l.startswith("# census "):
            kv = dict(x.split("=", 1) for x in l[9:].split()); cls.setdefault(("cen", int(kv["tick"])), kv)
    T = sorted(t for t in d if t % 50000 == 0 and "lineage" in d[t])
    out = []
    def births(t):
        fc = d[t]["fidcopy"]
        cp = sum(int(fc[k]["births"]) * float(fc[k]["child_strict%"]) / 100 for k in fc)
        ri = int(d[t]["fidelity"]["self/copy/reignite"].split("/")[2]) * float(d[t]["fidreig"]["child_strict%"]) / 100
        return cp + ri
    def plen(t):
        return cls[t] if t in cls else float(d[t]["fidcopy"]["rep"]["parent_len"])
    for a, b in zip(T, T[1:]):
        s0, s1 = int(d[a]["lineage"]["rep_sites"]), int(d[b]["lineage"]["rep_sites"])
        bt = (births(a) + births(b)) / 2 * 10
        m = (s0 + s1) / 2
        L = (plen(a) + plen(b)) / 2
        dec = m * L * P * 50000
        short = s0 + bt - dec - s1
        out.append((b // 1000, short / m / 10, dec / m / 10))
    print(r, " ".join(f"{t}k:{x:+.2f}" for t, x, _ in out), "| decay/site/5k", f"{min(y for *_, y in out):.2f}-{max(y for *_, y in out):.2f}")
