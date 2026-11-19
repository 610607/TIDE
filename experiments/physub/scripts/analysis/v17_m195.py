"""v17 uniform form M table: replicators, polite intact, copy-born nonrep % active, exact %, reign %, rep length."""
import sys, pathlib
D = pathlib.Path(sys.argv[1])
def load(p):
    rows, cen, cls = {}, {}, {}
    for l in open(p):
        if l.startswith("# census "):
            kv = dict(x.split("=", 1) for x in l[9:].split()); cen[int(kv["tick"])] = kv
        elif l.startswith("# classes "):
            kv = dict(x.split("=", 1) for x in l[10:].split() if "=" in x)
            if kv["table"] == "1": cls[int(kv["tick"])] = kv
        elif l[0].isdigit():
            f = l.split("\t"); rows[int(f[0])] = f
    return rows, cen, cls
R = [load(D / f"m195_s{s}.tsv") for s in (1, 2)]
print("| tick | replicators s1 / s2 | polite region intact | copy-born non-rep (% of active) | exact births % | re-ignitions (% of births) | replicator length |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for tk in sorted(R[0][1]):
    c = [r[1][tk] for r in R]; w = [r[0][tk] for r in R]; k = [r[2][tk] for r in R]
    j = lambda xs: " / ".join(xs)
    print(f"| {tk//1000}k | {j([x['replicators'] for x in c])} | {j([x['pfx_replicators'] for x in c])} | "
          f"{j([f'{100*int(x['nonrep_self/copy/reignite'].split('/')[1])/int(x['active']):.0f}%' for x in c])} | "
          f"{j([f'{float(x[3]):.0f}' for x in w])} | {j([f'{100*int(x[9])/int(x[2]):.0f}%' for x in w])} | "
          f"{j([f'{float(x['rep_len']):.1f}' for x in k])} |")
