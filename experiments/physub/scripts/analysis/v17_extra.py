"""v17 extra figures: opcode shift mean, control drift per seed, polite intact at 500k, copy births."""
import sys, pathlib, statistics as st
D = pathlib.Path(sys.argv[1])
def parse(path):
    cls, cen, rows = {}, {}, {}
    for l in open(path):
        if l.startswith("# classes "):
            kv = dict(x.split("=", 1) for x in l[10:].split() if "=" in x)
            cls[(int(kv["tick"]), int(kv["table"]))] = kv
        elif l.startswith("# census "):
            kv = dict(x.split("=", 1) for x in l[9:].split()); cen[int(kv["tick"])] = kv
        elif l[0].isdigit():
            f = l.split("\t"); rows[int(f[0])] = f
    return cls, cen, rows
names = [f"t{t}_s{s}" for t in (1,2,3,4) for s in (1,2)]
R = {n: parse(D / f"{n}.tsv") for n in names + ["m195_s1", "m195_s2"]}
T = list(range(50000, 500001, 50000))
g = lambda n, tk, t, k: float(R[n][0][(tk, t)][k])
def sh(n, tk, k):
    t = int(n[1]); c = "m195_s" + n[-1]; return g(n, tk, t, k) - g(c, tk, t, k)
print("opcode shift mean", {tk//1000: round(st.mean(sh(n, tk, "rep_op_fast%") for n in names), 2) for tk in T})
print("opcode shift runs", {tk//1000: (round(min(sh(n, tk, "rep_op_fast%") for n in names),2), round(max(sh(n, tk, "rep_op_fast%") for n in names),2)) for tk in T})
for t in (1,2,3,4):
    print("control drift table", t, [round(g(f"m195_s{s}", 500000, t, "rep_data_fast%") - g(f"m195_s{s}", 50000, t, "rep_data_fast%"), 2) for s in (1,2)])
for n in names + ["m195_s1", "m195_s2"]:
    c = R[n][1][500000]; r = R[n][2]
    cb = [int(r[tk][8]) for tk in T]
    print(n, "pfx_rep 500k", c["pfx_replicators"], "active", c["active"], "copies/50k", min(cb), max(cb))
