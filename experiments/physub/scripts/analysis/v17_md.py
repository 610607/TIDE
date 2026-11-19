"""v17 README tables and bullet figures. Usage: v17_md.py <runs dir>"""
import sys, pathlib, statistics as st
D = pathlib.Path(sys.argv[1])
def parse(path):
    cls, cen = {}, {}
    for l in open(path):
        if l.startswith("# classes "):
            kv = dict(x.split("=", 1) for x in l[10:].split() if "=" in x)
            cls[(int(kv["tick"]), int(kv["table"]))] = kv
        elif l.startswith("# census "):
            kv = dict(x.split("=", 1) for x in l[9:].split())
            cen[int(kv["tick"])] = kv
    return cls, cen
names = [f"t{t}_s{s}" for t in (1,2,3,4) for s in (1,2)]
R = {n: parse(D / f"{n}.tsv") for n in names + ["m195_s1", "m195_s2"]}
T = list(range(50000, 500001, 50000))
g = lambda n, tk, t, k: float(R[n][0][(tk, t)][k])
def tt(n): return int(n[1]), "m195_s" + n[-1]
def shift(n, tk, k):
    t, c = tt(n); return g(n, tk, t, k) - g(c, tk, t, k)
def haz(n, tk):
    t, c = tt(n); return 100 * (g(n, tk, t, "rep_h") / g(c, tk, t, "rep_h") - 1)
def table(title, f, fmt, mfmt):
    print(f"\n{title}\n")
    print("| tick | " + " | ".join(names) + " | mean |")
    print("| --- |" + " --- |" * (len(names) + 1))
    M = {}
    for tk in T:
        v = [f(n, tk) for n in names]; M[tk] = v
        print(f"| {tk//1000}k | " + " | ".join(fmt(x) for x in v) + f" | {mfmt(st.mean(v))} |")
    return M
DS = table("data shift", lambda n, tk: shift(n, tk, "rep_data_fast%"), lambda x: f"{x:+.2f}", lambda x: f"{x:+.2f}")
HZ = table("hazard", haz, lambda x: f"{x:+.1f}", lambda x: f"{x:+.2f}")
OP = {tk: [shift(n, tk, "rep_op_fast%") for n in names] for tk in T}
print("\n## bullets")
print("data shift mean", {tk//1000: round(st.mean(v), 2) for tk, v in DS.items()})
print("data shift runs at 500k", min(DS[500000]), max(DS[500000]))
print("data shift: ticks where any run >= 0:", [(tk//1000, n) for tk in T for n, x in zip(names, DS[tk]) if x >= 0])
mv = [(abs(DS[T[i+1]][j] - DS[T[i]][j]), names[j], T[i+1]//1000) for i in range(3, 9) for j in range(8)]
print("max point-to-point move after 200k", sorted(mv)[-3:])
for t in (1, 2, 3, 4):
    a = [g(f"m195_s{s}", 50000, t, "rep_data_fast%") for s in (1, 2)]; b = [g(f"m195_s{s}", 500000, t, "rep_data_fast%") for s in (1, 2)]
    print(f"control table {t} data fast {min(a):.1f}-{max(a):.1f} -> {min(b):.1f}-{max(b):.1f}")
print("hazard mean", {tk//1000: round(st.mean(v), 2) for tk, v in HZ.items()})
print("hazard runs at 500k", round(min(HZ[500000]), 1), round(max(HZ[500000]), 1))
print("hazard >= 0:", [(tk//1000, n, round(x, 1)) for tk in T for n, x in zip(names, HZ[tk]) if x >= 0])
for n in names + ["m195_s1", "m195_s2"]:
    t = int(n[1]) if n[0] == "t" else None
    tabs = [t] if t else [1, 2, 3, 4]
    for tb in tabs:
        h0, h1 = g(n, 50000, tb, "rep_h"), g(n, 500000, tb, "rep_h")
        print(f"abs hazard {n} table {tb}: {100*(h1/h0-1):+.1f}%  len {g(n,50000,tb,'rep_len'):.1f} -> {g(n,500000,tb,'rep_len'):.1f}")
print("opcode shift after 300k extremes", sorted([(round(x, 2), n, tk//1000) for tk in T if tk > 300000 for n, x in zip(names, OP[tk])])[:3],
      sorted([(round(x, 2), n, tk//1000) for tk in T if tk > 300000 for n, x in zip(names, OP[tk])])[-3:])
for n in names + ["m195_s1", "m195_s2"]:
    c = R[n][1]
    rep = [int(c[tk]["replicators"]) for tk in T]
    cb = 100 * int(c[500000]["nonrep_self/copy/reignite"].split("/")[1]) / int(c[500000]["active"])
    print(f"pop {n}: replicators 50k {rep[0]} 500k {rep[-1]} min {min(rep)}; copy-born nonrep 500k {cb:.0f}%")
