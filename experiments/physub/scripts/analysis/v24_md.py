"""v24 README tables. Usage: v24_md.py <dir with zero_s1 zero_s2 fail_s1 fail_s2 .tsv>
(EARLY / LATE as in v24_decomp)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from v24_routes import load, ledger, ROUTES, CLS
from v24_decomp import rates, PUSH, EARLY, LATE
D = sys.argv[1]
RUNS = ["zero_s1", "zero_s2", "fail_s1", "fail_s2"]
W = {r: load(f"{D}/{r}.tsv") for r in RUNS}
rng = lambda xs, f="{:.3f}": f.format(min(xs)) if f.format(min(xs)) == f.format(max(xs)) else f"{f.format(min(xs))}-{f.format(max(xs))}"
# 1. rate decomposition
R = {}
for r in RUNS:
    e, l = rates(W[r], EARLY), rates(W[r], LATE)
    push = {t: s * (l[t] - e[t]) for t, s in PUSH.items()}
    R[r] = (e, l, push, sum(push.values()))
LABEL = {"P": "copies by strict parents (all)", "delta": "strict copies by other parents",
         "reig0": "strict re-ignitions at 0", "gain": "gains in place",
         "decay": "whole decay", "wick": "wick ends",
         "L_f30_mov15": "in place: fill of 30 by the MOV at 15", "L_f30_other": "in place: fill of 30, other instruction",
         "L_f_ptr": "in place: foreign, pointers 34-40 only", "L_f_tail": "in place: foreign, tail 46-63 only",
         "L_f_other": "in place: foreign, other", "L_self_0": "in place: self, offset 0", "L_self_other": "in place: self, other",
         "N_point": "non-strict children: point", "N_gap": "non-strict children: gap", "N_multi": "non-strict children: multi",
         "N_env": "non-strict children: env", "dS": "net change"}
print("| term | early | late | share of the rise (zero s1 / s2; fail s1 / s2) |")
print("| --- | --- | --- | --- |")
for t in LABEL:
    e = [R[r][0][t] for r in RUNS]; l = [R[r][1][t] for r in RUNS]
    sh = " / ".join(f"{100*R[r][2][t]/R[r][3]:+.0f}" for r in RUNS) if t in PUSH else ""
    print(f"| {LABEL[t]} | {rng(e)} | {rng(l)} | {sh} |")
print("D", {r: round(R[r][3], 3) for r in RUNS})
groups = {"fill of 30 in place": ["L_f30_mov15", "L_f30_other"], "other in-place": ["L_f_ptr", "L_f_tail", "L_f_other", "L_self_0", "L_self_other"],
          "gap": ["N_gap"], "env": ["N_env"], "multi": ["N_multi"], "point": ["N_point"], "decay": ["decay"], "wick": ["wick"],
          "reig0": ["reig0"], "gain+delta": ["gain", "delta"]}
for g, ts in groups.items():
    print(f"group {g}: " + " / ".join(f"{100*sum(R[r][2][t] for t in ts)/R[r][3]:.1f}" for r in RUNS))
# 2. in-place loss composition, late windows, entry 0
print("\nin-place (entry 0, late windows):")
for r in RUNS:
    tot = {k: [0, 0] for k in ROUTES}
    for tk in LATE:
        if tk not in W[r]: continue
        for k in ROUTES:
            for i in (0, 1): tot[k][i] += W[r][tk]["e0"]["loss"][k][i]
    n = sum(sum(v) for v in tot.values())
    f30 = sum(tot["f30_mov15"])
    print(r, "n", n, "f30_mov15 %", round(100*f30/n, 1), "past48 of f30_mov15 %", round(100*tot["f30_mov15"][1]/f30, 1),
          "f30_other %", round(100*sum(tot["f30_other"])/n, 1), "ptr %", round(100*sum(tot["f_ptr"])/n, 1))
# 3. env composition
print("\nenv non-strict children (entry-0 strict parents), late windows:")
for r in RUNS:
    a = {k: sum(W[r][tk]["env"][k] for tk in LATE if tk in W[r]) for k in ("n", "only30", "has30", "residue_only")}
    print(r, a, {k: round(100*a[k]/a["n"], 1) for k in ("only30", "has30", "residue_only")})
# 4. off-entry
print("\noff entry per window (born / ends+losses / via filled_36_38, filled_ref, inert, dest_32, other, not_ignite as % of off-entry strict births by all igniters):")
for r in RUNS:
    for tk in sorted(W[r]):
        w = W[r][tk]
        if "eo" not in w: continue
        o = w["eo"]; born = sum(o["born"]); out = sum(o["end"]) + sum(sum(v) for v in o["loss"].values())
        via = [sum(w["via"][k][i] for k in w["via"]) for i in range(6)]
        tv = sum(via)
        print(r, tk//1000, "born", born, "out", out, "net", born - out + o["gain"] + o["found"], "self_0", sum(o["loss"]["self_0"]),
              "via%", [round(100*x/tv) if tv else 0 for x in via], "by other%", round(100*sum(w['via']['other'])/tv) if tv else 0)
# 5. depletion and matter
print("\nmatter / refusals:")
for r in RUNS:
    for tk in sorted(W[r]):
        m = W[r][tk].get("mass")
        if not m: continue
        print(r, tk//1000, "no_mass", W[r][tk]["no_mass"], "free", m["free"], "wall", m["wall"], "active_bytes", m["active_bytes(rep/loose/prop/other)"], "inactive_bytes", m["inactive_bytes"])
