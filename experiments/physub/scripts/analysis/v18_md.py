"""v18 README tables T1, T2, T4 and T5. Usage: v18_md.py <v18 dir>"""
import os, sys, re, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v18 import load, RUNS
from pathlib import Path
root = Path(sys.argv[1])
D = {r: load(root / f"{r}.tsv") for r in RUNS}
T = list(range(50000, 500001, 50000))
def rep(r, t): return D[r][t]["fidcopy"]["rep"]
def mr(vals, f="{:.1f}"):
    return f"{f.format(statistics.mean(vals))} ({f.format(min(vals))}-{f.format(max(vals))})"
print("T1")
print("| tick | m195_s1 | m195_s2 | t2_s1 | t3_s1 |")
print("| --- | --- | --- | --- | --- |")
for t in T:
    print(f"| {t//1000}k | " + " | ".join(f"{rep(r,t)['births']} / {float(rep(r,t)['child_strict%']):.1f}" for r in RUNS) + " |")
print("T2")
print("| tick | point | gap | multi | env | total | foreign / residue per copy | no-mass writes |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for t in T:
    L = {k: [] for k in ["point","gap","multi","env","total"]}; fo=[]; re_=[]; nm=[]
    for r in RUNS:
        f = rep(r,t); c=f["cls"]; n=int(f["births"])
        tot=0
        for k in ["point","gap","multi","env"]:
            v=100*(c[k][0]-c[k][1])/n; L[k].append(v); tot+=v
        L["total"].append(tot)
        tail = f_line = None
    for r in RUNS:
        line=[l for l in open(root/f"{r}.tsv") if l.startswith(f"# fidcopy tick={t} parent=rep ")][0]
        fo.append(float(re.search(r"foreign=(\S+)",line).group(1))); re_.append(float(re.search(r"residue=(\S+)",line).group(1)))
        nm.append(int(D[r][t]["fidelity"]["no_mass"]))
    print(f"| {t//1000}k | " + " | ".join(mr(L[k]) for k in ["point","gap","multi","env","total"]) +
          f" | {statistics.mean(fo):.2f} / {statistics.mean(re_):.2f} | {min(nm)}-{max(nm)} |")
print("T4")
print("| tick | strict-rep sites | filled % | other sites | filled % | copies by other parents (strict %) | re-ignitions | re-ignited strict % | igniter strict-rep % | genotype median strict % |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for t in T:
    rs=[];rf=[];os_=[];of=[];oc=[];ocs=[];ri=[];ris=[];ig=[];gm=[]
    for r in RUNS:
        l=D[r][t]["lineage"]; rs.append(int(l["rep_sites"])); rf.append(100*int(l["rep_filled"])/int(l["rep_sites"]))
        os_.append(int(l["other_sites"])); of.append(100*int(l["other_filled"])/int(l["other_sites"]))
        o=D[r][t]["fidcopy"]["other"]; oc.append(int(o["births"])); ocs.append(float(o["child_strict%"]))
        ri.append(int(D[r][t]["fidelity"]["self/copy/reignite"].split("/")[2]))
        ris.append(float(D[r][t]["fidreig"]["child_strict%"])); ig.append(float(D[r][t]["fidreig"]["igniter_rep%"]))
        gm.append(float(D[r][t]["fidgeno"]["child_strict%_q25/q50/q75"].split("/")[1]))
    rng=lambda v,f="{:.0f}": f"{f.format(min(v))}-{f.format(max(v))}"
    print(f"| {t//1000}k | {rng(rs)} | {rng(rf)} | {rng(os_)} | {rng(of)} | {rng(oc)} ({rng(ocs,'{:.1f}')}) | {rng(ri)} | {rng(ris,'{:.1f}')} | {rng(ig,'{:.1f}')} | {rng(gm)} |")
print("T5 share of copies by strict parents")
for t in T:
    v=[]
    for r in RUNS:
        fc=D[r][t]["fidcopy"]; tot=sum(int(fc[k]["births"]) for k in fc); v.append(100*int(fc["rep"]["births"])/tot)
    print(t//1000, f"{min(v):.0f}-{max(v):.0f}", "len", " ".join(f"{float(rep(r,t)['parent_len']):.1f}" for r in RUNS))
