"""v18 bullet figures and the no-copy-error table. Usage: v18_extra.py <dir>"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from v18 import load
root = Path(sys.argv[1])
D = {r: load(root / f"{r}.tsv") for r in ["m195_s1", "m195_s2", "t2_s1", "t3_s1", "nomut_s1", "nomut_s2"]}
T = list(range(50000, 500001, 50000))
for r in ["m195_s1", "m195_s2", "t2_s1", "t3_s1"]:
    d = D[r]
    per = [int(d[t]["fidcopy"]["rep"]["births"]) / int(d[t]["lineage"]["rep_sites"]) for t in (50000, 500000)]
    oex = []
    for t in T:
        o = d[t]["fidcopy"]["other"]; n = int(o["births"]); oex.append(100 * o["cls"]["exact"][0] / n if n else float("nan"))
    print(r, f"rep copies per strict site per window 50k {per[0]:.2f} 500k {per[1]:.2f}", "other exact% range", f"{min(oex):.0f}-{max(oex):.0f}")
print("\n| tick | strict sites | `other` sites | strict sites filled % | strict children of strict parents % | env copies per window | copies by `other` (exact %) | re-ignited strict % |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for t in (50000, 100000, 200000, 300000, 400000, 500000):
    c = []
    for r in ("nomut_s1", "nomut_s2"):
        e = D[r][t]; l = e["lineage"]; f = e["fidcopy"]["rep"]; o = e["fidcopy"]["other"]
        on = int(o["births"]); ox = o["cls"]["exact"][0]
        c.append(dict(rs=l["rep_sites"], os=l["other_sites"], fp=f"{100*int(l['rep_filled'])/int(l['rep_sites']):.0f}",
                      cs=f"{float(f['child_strict%']):.1f}", env=str(f["cls"]["env"][0]),
                      oc=f"{on}" + (f" ({100*ox/on:.0f})" if on >= 100 else ""), ri=f"{float(e['fidreig']['child_strict%']):.0f}"))
    j = lambda k: f"{c[0][k]} / {c[1][k]}"
    print(f"| {t//1000}k | {j('rs')} | {j('os')} | {j('fp')} | {j('cs')} | {j('env')} | {j('oc')} | {j('ri')} |")
for r in ("nomut_s1", "nomut_s2"):
    d = D[r]
    gaps = [D[r][t]["fidcopy"]["rep"]["cls"]["gap"][0] for t in T]
    f = d[500000]["fidcopy"]["rep"]; n = int(f["births"])
    loss = sum(f["cls"][k][0] - f["cls"][k][1] for k in ["exact", "point", "gap", "multi", "env"])
    parts = {k: f["cls"][k][0] - f["cls"][k][1] for k in ["point", "gap", "multi", "env"]}
    print(r, "gap max", max(gaps), "loss at 500k", f"{100*loss/n:.1f}%", parts, "len", d[50000]["fidcopy"]["rep"]["parent_len"], d[500000]["fidcopy"]["rep"]["parent_len"],
          "no_mass", [d[t]["fidelity"]["no_mass"] for t in T])
