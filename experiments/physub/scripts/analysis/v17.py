"""v17: time series every 50k of T - C (own table) for data/opcode fast share, hazard, census."""
import sys, pathlib
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
runs = {n: parse(D / f"{n}.tsv") for n in [f"t{t}_s{s}" for t in (1,2,3,4) for s in (1,2)] + ["m195_s1", "m195_s2"] if (D / f"{n}.tsv").exists()}
ticks = sorted({k[0] for r in runs.values() for k in r[0]})
cols = [(t, s) for t in (1,2,3,4) for s in (1,2)]
def table(title, f, fmt):
    print(f"\n{title}\n")
    print("| tick | " + " | ".join(f"t{t}_s{s}" for t, s in cols) + " |")
    print("| --- |" + " --- |" * len(cols))
    for tk in ticks:
        cells = []
        for t, s in cols:
            a = runs.get(f"t{t}_s{s}"); b = runs.get(f"m195_s{s}")
            try: cells.append(fmt(f(a, b, tk, t)))
            except (KeyError, TypeError, ZeroDivisionError): cells.append("")
        print(f"| {tk//1000}k | " + " | ".join(cells) + " |")
g = lambda r, tk, t, k: float(r[0][(tk, t)][k])
table("Replicator data bytes, fast share T - C (points)", lambda a, b, tk, t: g(a,tk,t,"rep_data_fast%") - g(b,tk,t,"rep_data_fast%"), lambda x: f"{x:+.2f}")
table("Replicator opcode bytes, fast share T - C (points)", lambda a, b, tk, t: g(a,tk,t,"rep_op_fast%") - g(b,tk,t,"rep_op_fast%"), lambda x: f"{x:+.2f}")
table("Replicator hazard, T / C - 1 (%)", lambda a, b, tk, t: 100*(g(a,tk,t,"rep_h")/g(b,tk,t,"rep_h") - 1), lambda x: f"{x:+.1f}")
table("Replicator hazard T (1e-5 per tick)", lambda a, b, tk, t: 1e5*g(a,tk,t,"rep_h"), lambda x: f"{x:.2f}")
table("Replicator length T - C (bytes)", lambda a, b, tk, t: g(a,tk,t,"rep_len") - g(b,tk,t,"rep_len"), lambda x: f"{x:+.2f}")
table("Non-replicators, fast share T - C (points)", lambda a, b, tk, t: g(a,tk,t,"nonrep_fast%") - g(b,tk,t,"nonrep_fast%"), lambda x: f"{x:+.2f}")
table("Replicators T (C)", lambda a, b, tk, t: (a[1][tk]["replicators"], b[1][tk]["replicators"]), lambda x: f"{x[0]} ({x[1]})")
table("Data fast share T / C (%)", lambda a, b, tk, t: (g(a,tk,t,"rep_data_fast%"), g(b,tk,t,"rep_data_fast%")), lambda x: f"{x[0]:.1f} / {x[1]:.1f}")
print("\nfinal census")
for n, (cls, cen) in runs.items():
    if cen:
        tk = max(cen); c = cen[tk]
        print(n, tk, c["active"], c["replicators"], c["pfx_replicators"], c["nonrep_self/copy/reignite"], c["mean_age_rep/nonrep"], c["replicator_genotypes"], c["genotypes"])
