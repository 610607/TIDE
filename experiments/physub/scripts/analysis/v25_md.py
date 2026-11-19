"""Markdown tables for the v25 README entry: python3 v25_md.py runs/v25"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from v25_len import load, CATS, TSRC, ISRC, ZBINS
D = sys.argv[1]
CE = ["zero_s1", "zero_s2", "fail_s1", "fail_s2"]; NM = ["zero_nomut_s1", "fail_nomut_s1"]
RUNS = [r for r in CE + NM if os.path.exists(f"{D}/{r}.tsv")]
W = {r: load(f"{D}/{r}.tsv") for r in RUNS}
P = 1.95e-6
PTR = [34, 36, 38, 40]; TAIL = list(range(46, 64))
def rng(vals, n=1, pct=False):
    vals = [v * (100 if pct else 1) for v in vals]
    a, b = min(vals), max(vals)
    fa, fb = f"{a:,.{n}f}", f"{b:,.{n}f}"
    return fa if fa == fb else f"{fa} to {fb}" if a < 0 else f"{fa}-{fb}"
def lst(vals, n=1, pct=False):
    return " / ".join(f"{v*(100 if pct else 1):,.{n}f}" for v in vals)
def wins(r, a, b): return [t for t in sorted(W[r]) if a <= t <= b]
# A. mean z by tick
print("A. mean z of strict entry-0 activations (z0=40 at tick 0)")
print("| tick | " + " | ".join(RUNS) + " |")
for t in sorted(W[RUNS[0]]):
    print(f"| {t//1000}k | " + " | ".join(f"{W[r][t]['mean'][1]:.1f} ({W[r][t]['n'][1]:,})" if t in W[r] else "" for r in RUNS) + " |")
# B. decomposition 0 -> end
print("\nB. change of the mean, 0 -> last tick, by credit")
groups = {
  "in place, foreign (strict kept)": lambda w, c: c["inplace_f"],
  "in place, self": lambda w, c: c["inplace_s"],
  "transmission (child - parent)": lambda w, c: w["trans"],
  "parent's place (z_parent - m)": lambda w, c: c["copy_sp"] - w["trans"],
  "re-ignitions": lambda w, c: c["reignite"],
  "copies by other parents": lambda w, c: c["copy_op"],
  "gains in place and found": lambda w, c: c["gain"] + c["found"] + c["self"],
  "whole decay": lambda w, c: c["decay"],
  "loss in place, foreign": lambda w, c: c["loss_f"],
  "loss in place, self": lambda w, c: c["loss_s"],
  "wick": lambda w, c: c["wick"],
}
print("| credit | " + " | ".join(RUNS) + " |")
tot = {r: 0 for r in RUNS}
for g, fn in groups.items():
    row = []
    for r in RUNS:
        s = sum(fn(W[r][t], {k: v[2] for k, v in W[r][t]["cat"].items()}) for t in W[r])
        tot[r] += s; row.append(f"{s:+.2f}")
    print(f"| {g} | " + " | ".join(row) + " |")
print("| sum = change of the mean | " + " | ".join(f"{tot[r]:+.2f}" for r in RUNS) + " |")
print("check:", [round(W[r][max(W[r])]['mean'][1] - 40 - tot[r], 9) for r in RUNS])
# mean z of entries/exits by category, pooled
print("\nB2. mean z by category (pooled over the run)")
for cat in ["copy_sp", "reignite", "copy_op", "gain", "decay", "loss_f", "loss_s", "wick"]:
    vals = []
    for r in RUNS:
        n = sum(W[r][t]["cat"][cat][0] for t in W[r]); z = sum(W[r][t]["cat"][cat][1] for t in W[r])
        if cat == "copy_sp":
            zp = sum(W[r][t]["zp"] for t in W[r]); vals.append(f"parent {zp/max(1,n):.1f}, child-parent {z/max(1,n):+.3f}, n={n}")
        else:
            vals.append(f"{z/max(1,n):.1f} (n={n})")
    print(f"  {cat}: " + " | ".join(vals))
# C. sources of bytes
print("\nC. bytes added to / removed from strict entry-0 keys, whole run")
print("| source | " + " | ".join(RUNS) + " |")
def pooled(r, key, k):
    return sum((W[r][t][key][k][0] if isinstance(W[r][t][key][k], tuple) else W[r][t][key][k]) for t in W[r])
rows = [("in place: foreign MOV@15, shifted", "isrc", "add_mov15_shift"), ("in place: foreign MOV@15, aligned", "isrc", "add_mov15_aligned"),
        ("in place: foreign MOV@15, source in a neighbor", "isrc", "add_mov15_nbrsrc"), ("in place: other foreign instruction", "isrc", "add_foreign_other"),
        ("in place: own write", "isrc", "add_self"), ("in place: erased by own write", "isrc", "rem_self"), ("in place: erased by foreign write", "isrc", "rem_foreign"),
        ("copy: added, foreign write", "tsrc", "add_foreign"), ("copy: added, residue", "tsrc", "add_residue"), ("copy: added, parent write", "tsrc", "add_parent"),
        ("copy: lost, not written", "tsrc", "lost_gap"), ("copy: lost, parent write", "tsrc", "lost_parent"), ("copy: lost, foreign write", "tsrc", "lost_foreign")]
for lab, key, k in rows:
    print(f"| {lab} | " + " | ".join(f"{pooled(r, key, k):,}" for r in RUNS) + " |")
print("| copy: substitutions (z unchanged) | " + " | ".join(f"{sum(W[r][t]['subs'] for t in W[r]):,}" for r in RUNS) + " |")
addin = {r: sum(pooled(r, "isrc", k) for k in ISRC[:5]) for r in RUNS}
addtr = {r: sum(pooled(r, "tsrc", k) for k in TSRC[:3]) for r in RUNS}
print("in-place share of all added bytes:", lst([addin[r] / (addin[r] + addtr[r]) for r in RUNS], 1, True))
print("shares of in-place adds (aligned/shift/nbrsrc/other_foreign/self):")
for r in RUNS:
    print("  ", r, [f"{pooled(r,'isrc',k)/addin[r]*100:.1f}" for k in ISRC[:5]])
iwc = {r: [sum(W[r][t]["iwc"][i] for t in W[r]) for i in range(6)] for r in RUNS}
print("foreign add writer shares rep/loose/prop/other/self/none:", {r: [f"{x/sum(iwc[r])*100:.1f}" for x in iwc[r]] for r in RUNS})
# offsets
print("\nC2. in-place additions by offset group (share of in-place adds) and transmission adds")
for r in RUNS:
    io = {}
    for t in W[r]:
        for k, v in W[r][t]["ioff"].items(): io[k] = [a + b for a, b in zip(io.get(k, [0]*7), v)]
    g = {name: sum(sum(io[k][:5]) for k in ks if k in io) for name, ks in [("30", [30]), ("34", [34]), ("36/38/40", [36, 38, 40]), ("tail", TAIL), ("rest", ["rest"])]}
    tt = sum(g.values())
    print("  ", r, {k: f"{v/tt*100:.1f}" for k, v in g.items()})
# standing composition
print("\nC3. standing: share of live strict entry-0 with offset filled / mean filled tail bytes")
print("| tick | 34 filled (%) | 36 | 38 | 40 | tail bytes per site |")
for t in sorted(W[RUNS[0]]):
    def v(fn): return rng([fn(W[r][t]) for r in CE if t in W[r]], 1)
    print(f"| {t//1000}k | " + " | ".join([v(lambda w, k=k: w['alive'][k] / w['alive_n'] * 100) for k in PTR]) + f" | {v(lambda w: sum(w['alive'][k] for k in TAIL) / w['alive_n'])} |")
# use at exits
print("\nD. use at exits (pooled): filled / executed / control")
for r in RUNS:
    ex = {}
    for t in W[r]:
        for k, vv in W[r][t]["ex"].items(): ex[k] = [a + b for a, b in zip(ex.get(k, [0, 0, 0]), vv)]
    out = []
    for name, ks in [("34", [34]), ("36/38/40", [36, 38, 40]), ("tail", TAIL)]:
        n = sum(ex[k][0] for k in ks); e = sum(ex[k][1] for k in ks); c = sum(ex[k][2] for k in ks)
        out.append(f"{name}: {n:,} exec {e/max(1,n)*100:.1f}% ctl {c/max(1,n)*100:.1f}%")
    print("  ", r, "; ".join(out))
# E. bins
for lab, (a, b) in [("early 50k-150k", (50000, 150000)), ("late 350k-500k", (350000, 500000))]:
    print(f"\nE. by z bin, {lab} (ranges over the copy-error runs; then nomut)")
    print("| z | exposure share (%) | copies per site per 5k | strict children (%) | exact children (%) | whole decay per 5k | n_eff | foreign losses in place per 5k | strict children - exits per 5k |")
    for grp in [CE, NM]:
        rr = [r for r in grp if r in W and wins(r, a, b)]
        if not rr: continue
        for bn in ZBINS:
            cols = [[] for _ in range(8)]
            for r in rr:
                ts = wins(r, a, b)
                v = [sum(W[r][t]["bins"][bn][i] for t in ts) for i in range(8)]
                te = sum(W[r][t]["bins"][x][0] for t in ts for x in ZBINS)
                e = v[0]
                if e < 2e5: continue
                de = v[4] / e
                cols[0].append(e / te); cols[1].append(v[1] / e * 5000); cols[2].append(v[2] / max(1, v[1])); cols[3].append(v[3] / max(1, v[1]))
                cols[4].append(de * 5000); cols[5].append(-math.log(1 - de) / -math.log(1 - P)); cols[6].append(v[6] / e * 5000)
                cols[7].append((v[2] - v[4] - v[5] - v[6] - v[7]) / e * 5000)
            if not cols[0]: continue
            print(f"| {bn}{' (nomut)' if grp is NM else ''} | {rng(cols[0],1,True)} | {rng(cols[1],3)} | {rng(cols[2],0,True)} | {rng(cols[3],0,True)} | {rng(cols[4],3)} | {rng(cols[5],1)} | {rng(cols[6],3)} | {rng(cols[7],3)} |")
# F. pointer state
print("\nF. pointer state, whole run (ranges over copy-error runs)")
names = ["none_in", "none_off", "f36_in", "f36_off", "f38_in", "f38_off", "both_in", "both_off"]
print("| state | copies by such parents (% of all) | strict children (%) | share of all multi children (%) | share of MOV@15 additions in place (%) |")
for grp in [CE, NM]:
    rr = [r for r in grp if r in W and "ptr" in W[r][min(W[r])]]
    for n in names:
        c1, c2, c3, c4 = [], [], [], []
        for r in rr:
            totb = sum(W[r][t]["ptr"][m][1][0] for t in W[r] for m in names)
            totm = sum(W[r][t]["ptr"][m][1][3] for t in W[r] for m in names)
            totw = sum(W[r][t]["ptr"][m][2][0] for t in W[r] for m in names)
            pb = [sum(W[r][t]["ptr"][n][1][i] for t in W[r]) for i in range(5)]
            pw = sum(W[r][t]["ptr"][n][2][0] for t in W[r])
            c1.append(pb[0] / max(1, totb)); c2.append(pb[1] / max(1, pb[0])); c3.append(pb[3] / max(1, totm)); c4.append(pw / max(1, totw))
        if rr: print(f"| {n}{' (nomut)' if grp is NM else ''} | {rng(c1,1,True)} | {rng(c2,0,True)} | {rng(c3,0,True)} | {rng(c4,0,True)} |")
    for r in rr:
        sh = {}
        for t in W[r]:
            for k, v in W[r][t]["shift"].items(): sh[k] = sh.get(k, 0) + v
        tt = sum(sh.values())
        print("  shift top", r, [(k, f"{v/tt*100:.0f}%") for k, v in sorted(sh.items(), key=lambda kv: -kv[1])[:6]], tt)
