"""v16 analysis: identity checks, census table, class shares and substitutions, treatment vs m195."""
import sys, pathlib, re
D = pathlib.Path(sys.argv[1]); V15 = pathlib.Path(sys.argv[2])

def lines(p): return p.read_text().splitlines()
def strip(ls): return [l for l in ls if not (l.startswith("# classes") or l.startswith("# subst"))]

print("## identity")
for s in (1, 2):
    ref = (V15 / f"m195_s{s}.tsv").read_bytes()
    for t in (1, 2, 3, 4):
        p = D / f"r1_t{t}_s{s}.tsv"
        print(p.stem, "identical to v15 m195" if p.read_bytes() == ref else "DIFFERS")
    p = D / f"m195_s{s}.tsv"
    print(p.stem, "stripped identical to v15" if strip(lines(p)) == ref.decode().splitlines() else "DIFFERS")

def kvs(ls, tag):
    out = {}
    for l in ls:
        if l.startswith(tag):
            kv = dict(x.split("=", 1) for x in l[len(tag):].split() if "=" in x)
            out.setdefault(int(kv["tick"]), {})[int(kv.get("table", 0))] = (kv, l)
    return out

print("\n## census (100k)")
print("| run | replicator peak | active | replicators | polite region intact | non-rep copy-born (% of active) | re-ignited | age rep / non-rep | replicator genotypes |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
names = [f"t{t}_s{s}" for t in (1, 2, 3, 4) for s in (1, 2)] + ["m195_s1", "m195_s2"]
for n in names:
    ls = lines(D / f"{n}.tsv")
    cen = {k: v[0][0] for k, v in kvs(ls, "# census ").items()}
    fin = next((l for l in ls if l.startswith("final")), "")
    if 100000 not in cen:
        print(f"| {n} | | {fin} |"); continue
    pk = max(cen.items(), key=lambda kv: int(kv[1]["replicators"]))
    c = cen[100000]
    _, cb, ri = c["nonrep_self/copy/reignite"].split("/")
    a1, a0 = c["mean_age_rep/nonrep"].split("/")
    act = int(c["active"])
    print(f"| {n} | {pk[1]['replicators']} ({pk[0]//1000}k) | {act} | {c['replicators']} | {c['pfx_replicators']} | {cb} ({100*int(cb)/act:.0f}%) | {ri} | {a1} / {a0} | {c['replicator_genotypes']} |")

print("\n## classes: own table in treatment vs the same table in m195 (same seed)")
cols = ["rep_fast%", "rep_op_fast%", "rep_data_fast%", "rep_len", "rep_op_len", "rep_data_len", "nonrep_fast%", "code_fast%", "rep_h", "nonrep_h"]
for t in (1, 2, 3, 4):
    for s in (1, 2):
        a = kvs(lines(D / f"t{t}_s{s}.tsv"), "# classes ")
        b = kvs(lines(D / f"m195_s{s}.tsv"), "# classes ")
        for tick in (10000, 30000, 50000, 100000):
            if tick not in a or tick not in b: continue
            x = a[tick][t][0]; y = b[tick][t][0]
            print(f"t{t}_s{s} {tick//1000:3d}k " + " ".join(f"{c}={float(x[c]):.3g}|{float(y[c]):.3g}" for c in cols))
print("\n## subst at polite offsets per replicator site (treatment | m195), own table")
for t in (1, 2, 3, 4):
    for s in (1, 2):
        a = kvs(lines(D / f"t{t}_s{s}.tsv"), "# subst ")
        b = kvs(lines(D / f"m195_s{s}.tsv"), "# subst ")
        for tick in (50000, 100000):
            if tick not in a or tick not in b: continue
            la = a[tick][t][1]; lb = b[tick][t][1]
            def parse(l):
                op = dict(x.split("=") for x in l.split(" op: ")[1].split(" data: ")[0].split())
                da = dict(x.split("=") for x in l.split(" data: ")[1].split())
                return op, da
            (oa, da), (ob, db) = parse(la), parse(lb)
            f = lambda d, k: float(d[k])
            print(f"t{t}_s{s} {tick//1000}k op f2s/s2f {f(oa,'f2s'):.3f}/{f(oa,'s2f'):.3f} | {f(ob,'f2s'):.3f}/{f(ob,'s2f'):.3f}   data f2s/s2f {f(da,'f2s'):.3f}/{f(da,'s2f'):.3f} | {f(db,'f2s'):.3f}/{f(db,'s2f'):.3f}   data s2s/f2f {f(da,'s2s'):.3f}/{f(da,'f2f'):.3f} | {f(db,'s2s'):.3f}/{f(db,'f2f'):.3f}")
